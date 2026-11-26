"""Reference-image editing through the platform's authorized image route.

This adapter intentionally makes exactly one editing request.  A timeout or an
unusable response must not silently repeat a potentially billable generation.
The platform still owns provider credentials, permissions, HTTP and concurrency.
"""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import ipaddress
import socket
import time
from urllib.parse import urlsplit


MAX_IMAGE_BYTES = 30 * 1024 * 1024
MAX_JSON_BYTES = 64 * 1024 * 1024
_PNG = b"\x89PNG\r\n\x1a\n"


class ImageEditError(RuntimeError):
    """Only fixed, user-safe descriptions may leave this adapter."""


def _image_bytes(data: object) -> bytes:
    if not isinstance(data, bytes) or not data:
        raise ImageEditError("AI 服务未返回有效图片")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageEditError("生成图片超过 30 MiB，请减小图片尺寸后重试")
    if not (data.startswith(_PNG) or data.startswith(b"\xff\xd8\xff")
            or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")):
        raise ImageEditError("AI 服务返回的不是 PNG、JPEG 或 WebP 图片")
    return data


def _http_url(value: object) -> str:
    if not isinstance(value, str) or not value or any(ord(c) < 33 for c in value):
        raise ImageEditError("AI 服务返回的图片地址无效")
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme.lower() in {"http", "https"} and bool(parsed.hostname)
                 and parsed.username is None and parsed.password is None)
        _ = parsed.port
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise ImageEditError("AI 服务返回的图片地址无效")
    return value


async def _download_url(value: object, provider_url: str = "") -> str:
    """仅允许公开图片地址，或管理员明确配置的 AI 服务同源地址。"""
    url = _http_url(value)
    parsed = urlsplit(url)

    def origin(item):
        return (item.scheme.lower(), item.hostname, item.port or (443 if item.scheme.lower() == "https" else 80))

    try:
        if provider_url and origin(parsed) == origin(urlsplit(_http_url(provider_url))):
            return url  # 自建私网 AI 可下载自己的图片，仍不携带鉴权或跟随重定向。
        try:
            addresses = [ipaddress.ip_address(parsed.hostname)]
        except ValueError:
            records = await asyncio.wait_for(asyncio.to_thread(
                socket.getaddrinfo, parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80),
                type=socket.SOCK_STREAM,
            ), timeout=5)
            addresses = [ipaddress.ip_address(record[4][0]) for record in records]
        if not addresses or any(not address.is_global for address in addresses):
            raise ImageEditError("AI 返回的图片地址不是公开地址，已停止下载")
    except ImageEditError:
        raise
    except (OSError, ValueError, TypeError, TimeoutError):
        raise ImageEditError("AI 返回的图片地址无法安全解析，已停止下载") from None
    return url


def _http_error(status: int) -> ImageEditError:
    if status in {404, 405, 415, 501}:
        return ImageEditError("当前生图服务不支持参考图，请在平台选择支持图片编辑的模型")
    if status in {401, 403}:
        return ImageEditError("参考图生图鉴权失败，请检查平台 AI 服务授权")
    if status == 429:
        return ImageEditError("AI 服务请求过于频繁，请稍后重试")
    if status in {400, 422}:
        return ImageEditError("当前模型不接受参考图或所选参数，请检查平台生图模型配置")
    if status >= 500:
        return ImageEditError("AI 服务暂时异常；未自动重试，避免重复生成")
    return ImageEditError("参考图生图请求失败，请检查平台 AI 服务")


def _audit_call(owner, name: str, *args, **kwargs) -> bool:
    """Statistics must not turn a completed generation into a failed request."""
    try:
        getattr(owner, name)(*args, **kwargs)
        return True
    except Exception:
        return False


async def _result_bytes(service, body: dict, *, provider_url: str = "") -> bytes:
    values = body.get("data")
    if not isinstance(values, list) or not values or not isinstance(values[0], dict):
        raise ImageEditError("AI 服务未返回有效图片")
    item = values[0]
    encoded = item.get("b64_json")
    if encoded is not None:
        if not isinstance(encoded, str) or not encoded:
            raise ImageEditError("AI 服务返回的图片编码无效")
        if encoded.startswith("data:"):
            prefix, separator, encoded = encoded.partition(",")
            if not separator or prefix.lower() not in {
                "data:image/png;base64", "data:image/jpeg;base64", "data:image/webp;base64",
            }:
                raise ImageEditError("AI 服务返回的图片编码无效")
        if len(encoded) > 4 * ((MAX_IMAGE_BYTES + 2) // 3):
            raise ImageEditError("生成图片超过 30 MiB，请减小图片尺寸后重试")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (binascii.Error, ValueError):
            raise ImageEditError("AI 服务返回的图片编码无效") from None
        return _image_bytes(data)
    url = await _download_url(item.get("url"), provider_url)
    downloaded = bytearray()
    # Never forward the provider's Authorization header to image URLs.  A
    # redirect is not followed: its new destination has not been validated.
    async with service.http.stream("GET", url, timeout=180,
                                   follow_redirects=False) as response:
        if not 200 <= response.status_code < 300:
            raise ImageEditError("生成图片下载失败；未重新生成，请稍后重试")
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                too_large = int(content_length) > MAX_IMAGE_BYTES
            except (ValueError, TypeError):
                too_large = False
            if too_large:
                raise ImageEditError("生成图片超过 30 MiB，请减小图片尺寸后重试")
        async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
            if len(downloaded) + len(chunk) > MAX_IMAGE_BYTES:
                raise ImageEditError("生成图片超过 30 MiB，请减小图片尺寸后重试")
            downloaded.extend(chunk)
    return _image_bytes(bytes(downloaded))


async def edit_image(ctx, prompt: str, reference_image: bytes, *,
                     size: str = "1024x1024", quality: str = "auto") -> bytes:
    """Edit one normalized PNG without persisting credentials or input images."""
    if (not isinstance(reference_image, bytes) or not reference_image.startswith(_PNG)
            or len(reference_image) > MAX_IMAGE_BYTES):
        raise ImageEditError("参考图无效或超过 30 MiB，请重新发送图片")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ImageEditError("请填写参考图的修改要求")
    try:
        platform_ai = ctx.ai
        service = platform_ai.service
        plugin_id = platform_ai.plugin_id
        usage = service.usage
        if not isinstance(plugin_id, str) or not plugin_id:
            raise ValueError
    except Exception:
        raise ImageEditError("当前平台未提供参考图生图所需的 AI 服务") from None

    started = time.perf_counter()
    target = None
    tracking = _audit_call(usage, "begin")
    completed = False
    try:
        # 沿用平台的并发槽和代理，但流式接收 JSON，避免先缓冲无限正文。
        async with service._request_slot():
            # 在排队结束后按绑定身份重新核对授权，停用后的排队任务不能发送。
            try:
                details = service._resolve_details("image", plugin_id=plugin_id)
                if not isinstance(details, dict):
                    raise ValueError
                target = details
                base_url = str(target["base_url"]).rstrip("/")
                model = str(target["model"])
                api_key = target["api_key"]
                if not base_url or not model or not isinstance(api_key, str) or not api_key:
                    raise ValueError
            except PermissionError:
                raise ImageEditError("插件未获准使用平台 AI 生图能力") from None
            except Exception:
                raise ImageEditError("平台未配置可用的 AI 生图服务") from None

            data = {"model": model, "prompt": prompt, "size": str(size), "n": "1"}
            if quality and quality != "auto":
                data["quality"] = str(quality)
            _audit_call(service, "_log_started", "参考图生图", plugin_id, model, base_url)
            encoded_body = bytearray()
            async with service.http.stream(
                "POST", f"{base_url}/images/edits", headers={"Authorization": f"Bearer {api_key}"},
                data=data, files={"image": ("reference.png", reference_image, "image/png")},
                timeout=service._timeout("image"), follow_redirects=False,
            ) as response:
                if not 200 <= response.status_code < 300:
                    raise _http_error(response.status_code)
                try:
                    too_large = int(response.headers.get("content-length", "0")) > MAX_JSON_BYTES
                except (ValueError, TypeError):
                    too_large = False
                if too_large:
                    raise ImageEditError("AI 服务响应过大，已停止处理")
                async for chunk in response.aiter_bytes(chunk_size=64 * 1024):
                    if len(encoded_body) + len(chunk) > MAX_JSON_BYTES:
                        raise ImageEditError("AI 服务响应过大，已停止处理")
                    encoded_body.extend(chunk)
        try:
            body = json.loads(encoded_body)
        except (ValueError, TypeError):
            raise ImageEditError("AI 服务返回无效内容；未自动重试，避免重复生成") from None
        if not isinstance(body, dict):
            raise ImageEditError("AI 服务返回无效内容；未自动重试，避免重复生成")
        result = await _result_bytes(service, body, provider_url=base_url)
        _audit_call(service, "_log_succeeded", "参考图生图", plugin_id, model,
                    base_url, started, body)
        _audit_call(usage, "record_tokens", body)
        _audit_call(service, "_record_attempt", capability="image", plugin_id=plugin_id,
                    target=target, protocol="image_edits", started=started,
                    succeeded=True, data=body, used_fallback=False)
        completed = True
        return result
    except asyncio.CancelledError:
        if target:
            error = ImageEditError("参考图生图已取消；未自动重试")
            _audit_call(service, "_record_attempt", capability="image", plugin_id=plugin_id,
                        target=target, protocol="image_edits", started=started,
                        succeeded=False, exc=error, used_fallback=False)
        raise
    except Exception as exc:
        error = exc if isinstance(exc, ImageEditError) else ImageEditError(
            "参考图生图未完成；未自动重试，避免重复生成，请检查网络和平台 AI 服务")
        if target:
            _audit_call(service, "_log_failed", "参考图生图", plugin_id,
                        str(target.get("model", "")), str(target.get("base_url", "")),
                        started, error, False)
            _audit_call(service, "_record_attempt", capability="image", plugin_id=plugin_id,
                        target=target, protocol="image_edits", started=started,
                        succeeded=False, exc=error, used_fallback=False)
        raise error from None
    finally:
        if tracking:
            _audit_call(usage, "succeed" if completed else "fail")
