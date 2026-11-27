"""Short-lived, single-use file upload links bound to an authorised WeCom owner.

The fragment is a bearer capability, not proof of the visitor's identity. It is
never part of the request URL; only its digest is retained by the plugin.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import ipaddress
import json
import math
import re
import secrets
import time
from pathlib import Path
from urllib.parse import unquote, urlsplit

from starlette.responses import HTMLResponse, JSONResponse

from .chat import COLOR_LABELS, SIDE_LABELS, failure_reason
from .files import safe_name
from .queue import LABELS


LIFETIME = 10 * 60
MAX_SESSIONS = 256
MAX_OWNER_SESSIONS = 3
WEBHOOK_MAX_BYTES = 20 * 1024 * 1024
TOKEN_PATTERN = re.compile(r"Bearer ([A-Za-z0-9_-]{43})\Z")
HEADERS = {
    "Cache-Control": "no-store, max-age=0",
    "Pragma": "no-cache",
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
}


def _https_url(value, *, origin_only=False):
    """Validate configured URLs without trusting the incoming Host header."""
    if (not isinstance(value, str) or not value or any(char in value for char in "\\?#")
            or any(ord(char) <= 32 or ord(char) == 127 for char in value)):
        raise ValueError("请在远程打印设置中填写正确的平台外网 HTTPS 地址。")
    try:
        parsed = urlsplit(value)
        port = parsed.port
        host = parsed.hostname
        if (parsed.scheme != "https" or not host or parsed.username is not None
                or parsed.password is not None or parsed.query or parsed.fragment
                or (origin_only and parsed.path)):
            raise ValueError
        decoded_path = parsed.path
        for _ in range(4):
            decoded = unquote(decoded_path, encoding="utf-8", errors="strict")
            if decoded == decoded_path:
                break
            decoded_path = decoded
        if (any(part in {".", ".."} for part in decoded_path.split("/"))
                or "//" in decoded_path or any(char in decoded_path for char in "\\?#")
                or any(ord(char) <= 32 or ord(char) == 127 for char in decoded_path)
                or re.search(r"%[0-9a-fA-F]{2}", decoded_path)):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
            normalized_host = f"[{address.compressed}]" if address.version == 6 else address.compressed
        except ValueError:
            normalized_host = host.encode("idna").decode("ascii").lower()
            if (len(normalized_host) > 253 or any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                                                  for label in normalized_host.rstrip(".").split("."))):
                raise ValueError
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
        origin = "https://" + normalized_host + (f":{port}" if port not in (None, 443) else "")
        return origin, value.rstrip("/")
    except (ValueError, UnicodeError):
        raise ValueError("请在远程打印设置中填写正确的平台外网 HTTPS 地址。") from None


class PrintUploads:
    def __init__(self, service):
        self.service = service
        self.lock = asyncio.Lock()
        self.sessions = {}

    def _base(self):
        return _https_url(self.service.config()["public_base_url"])

    def _allowed(self, session):
        if session["generation"] != self.service.wecom_generation:
            raise ValueError("打印入口已更新，请回到聊天重新发送“打印文件”。")
        if session["base"] != self._base()[1]:
            raise ValueError("打印上传地址已更新，请回到聊天重新发送“打印文件”。")
        self.service.wecom_owner_allowed(session["owner"], session["identity"])

    def _purge(self, now):
        # In-flight work holds its own session reference and may safely finish.
        # Issuing another link never evicts a still-valid received-file result.
        for digest, session in list(self.sessions.items()):
            if session["expires"] <= now:
                del self.sessions[digest]

    async def issue(self, owner, identity):
        self.service.wecom_owner_allowed(owner, identity)
        _, base = self._base()
        if len((base + "/api/plugin/remote_print/upload#" + "x" * 43).encode("utf-8")) > 1400:
            raise ValueError("平台外网地址过长，请在远程打印设置中填写简短的 HTTPS 访问地址。")
        async with self.lock:
            self.service.wecom_owner_allowed(owner, identity)
            now = time.monotonic()
            self._purge(now)
            if len(self.sessions) >= MAX_SESSIONS:
                raise ValueError("当前上传链接较多，请稍后再发送“打印文件”。")
            if sum(session["state"] in {"ready", "processing"}
                   and session["owner"].casefold() == owner.casefold() and session["identity"] == identity
                   for session in self.sessions.values()) >= MAX_OWNER_SESSIONS:
                raise ValueError("你已有 3 个有效上传链接，请先使用已有链接，或 10 分钟后重新获取。")
            token = secrets.token_urlsafe(32)
            digest = hashlib.sha256(token.encode("ascii")).hexdigest()
            self.sessions[digest] = {
                "owner": owner, "identity": identity, "generation": self.service.wecom_generation, "base": base,
                "expires": now + LIFETIME, "state": "ready", "job_id": "", "message": "请选择 PDF 或图片。",
            }
        return base + "/api/plugin/remote_print/upload#" + token

    @staticmethod
    def _response(payload, status=200):
        return JSONResponse(payload, status_code=status, headers=HEADERS)

    def _error(self, message, status, *, state="invalid"):
        return self._response({"ok": False, "state": state, "message": message}, status)

    def _origin_allowed(self, request):
        origin = request.headers.get("origin")
        if origin is None:
            return True
        try:
            expected, _ = self._base()
            supplied, _ = _https_url(origin, origin_only=True)
            return supplied == expected
        except ValueError:
            return False

    def _lookup(self, request):
        match = TOKEN_PATTERN.fullmatch(str(request.headers.get("authorization", "")))
        if match is None:
            return None
        digest = hashlib.sha256(match[1].encode("ascii")).hexdigest()
        session = self.sessions.get(digest)
        if session is None or session["expires"] <= time.monotonic():
            return None
        try:
            self._allowed(session)
        except ValueError:
            return None
        return digest, session

    async def page(self, request):
        if request.method != "GET":
            return self._error("请打开聊天中的上传链接。", 405)
        source = await asyncio.to_thread(Path(__file__).with_name("upload_page.html").read_text, encoding="utf-8")
        directives = []
        for tag in ("script", "style"):
            blocks = re.findall(r"<" + tag + r"\b[^>]*>(.*?)</" + tag + r">", source, flags=re.I | re.S)
            hashes = ["'sha256-" + base64.b64encode(hashlib.sha256(block.encode("utf-8")).digest()).decode("ascii") + "'"
                      for block in blocks]
            directives.append(tag + "-src " + (" ".join(hashes) or "'none'"))
        headers = dict(HEADERS)
        headers["Content-Security-Policy"] = (
            "default-src 'none'; " + "; ".join(directives)
            + "; connect-src 'self'; img-src data:; form-action 'none'; base-uri 'none'; frame-ancestors 'none'"
        )
        return HTMLResponse(source, headers=headers)

    async def _snapshot(self, session):
        self._allowed(session)
        cfg = self.service.config()
        payload = {
            "ok": session["state"] != "failed", "state": session["state"], "message": session["message"],
            "expires_in": max(0, math.ceil(session["expires"] - time.monotonic())),
            "max_bytes": min(cfg["max_file_mb"] * 1024 * 1024, WEBHOOK_MAX_BYTES),
            "max_pages": cfg["max_pages"], "auto_print": cfg["auto_print"], "job_id": session["job_id"],
            "max_copies": cfg["max_copies"],
        }
        if session["job_id"]:
            job = await self.service.queue.get_job(
                session["job_id"], session["owner"], source_channel=session["identity"],
                permission_check=lambda: self._allowed(session),
            )
            # File reception is durable before the chat receipt is sent. A slow
            # WeCom API must not leave an already received PDF "uploading".
            if session["state"] == "processing" and job["status"] != "receiving":
                if job.get("pages"):
                    session.update(state="complete", message="文件已收到。")
                elif job["status"] in {"failed", "cancelled"}:
                    session.update(state="failed", message=failure_reason(job.get("message"))
                                   if job.get("message") else "文件未收取或已取消，请返回聊天查看任务。")
                payload.update(state=session["state"], ok=session["state"] != "failed", message=session["message"])
            payload.update({key: job.get(key) for key in ("filename", "pages", "status", "number", "number_batch", "copies")})
            payload.update(status_label=LABELS.get(job["status"], "待核查"),
                           sides_label=SIDE_LABELS.get(job.get("sides", "default"), "打印机默认"),
                           color_label=COLOR_LABELS.get(job.get("color_mode", "auto"), "打印机默认"))
            if session["state"] == "complete":
                status = job["status"]
                if status == "pending":
                    payload["message"] = "上传完成，请在下方选择单面或双面打印，也可返回聊天操作。"
                elif status in {"failed", "unknown"}:
                    payload["message"] = "文件已收到，打印状态：" + LABELS[status] + "。" + failure_reason(job.get("message"))
                else:
                    payload["message"] = "文件已收到，当前状态：" + LABELS.get(status, "请回到聊天查看进度") + "。"
        self._allowed(session)
        return payload

    async def action(self, request):
        """Operate only the fixed job attached to this unexpired capability."""
        if request.method != "POST":
            return self._error("请使用页面上的打印按钮。", 405)
        if not self._origin_allowed(request):
            return self._error("请使用聊天中的原始上传链接。", 403)
        async with self.lock:
            found = self._lookup(request)
            if found is None:
                return self._error("链接已失效或权限已变更，请返回聊天查看任务。", 403)
            digest, session = found

        def permission():
            if self.sessions.get(digest) is not session or session["expires"] <= time.monotonic():
                raise ValueError("链接已失效，请返回聊天查看任务。")
            self._allowed(session)

        try:
            permission()
            if not request.body or len(request.body) > 1024:
                return self._error("打印操作参数无效。", 400)
            try:
                data = json.loads(request.body)
            except (ValueError, UnicodeError):
                return self._error("打印操作参数无效。", 400)
            if not isinstance(data, dict) or set(data) - {"action", "sides", "copies"}:
                return self._error("打印操作参数无效。", 400)
            operation = data.get("action")
            if not isinstance(operation, str) or operation not in {"print", "cancel"} or (operation == "cancel" and set(data) != {"action"}):
                return self._error("请选择单面、双面打印或取消。", 400)
            sides = data.get("sides", "one-sided")
            copies = data.get("copies")
            if operation == "print" and (not isinstance(sides, str) or sides not in {
                    "one-sided", "two-sided-auto", "two-sided-long-edge", "two-sided-short-edge"}
                    or (copies is not None and (type(copies) is not int or not 1 <= copies <= self.service.config()["max_copies"]))):
                return self._error("打印方式或份数无效，请刷新状态后重新选择。", 400)
            if session["state"] != "complete" or not session["job_id"]:
                return self._error("文件尚未收取完成，请先刷新状态。", 409, state=session["state"])
            job = await self.service.queue.get_job(session["job_id"], session["owner"],
                source_channel=session["identity"], permission_check=permission)
            message = "任务已处理，不会重复打印。"
            try:
                if operation == "print" and job["status"] == "pending":
                    # Never hold the upload registry lock across printer I/O:
                    # status queries and other family uploads must stay usable.
                    mode = await self.service.check_sides(sides)
                    option_check = await self.service.automatic_option_check(mode)
                    await self.service.queue.confirm(session["job_id"], session["owner"], copies,
                        sides=mode, source_channel=session["identity"], permission_check=permission,
                        option_check=option_check)
                    self.service.request_dispatch()
                    self.service.ctx.log.info("网页已确认打印：任务 %s", session["job_id"])
                    message = "已确认打印。进入队列不代表已经出纸，请勿重复发送。"
                elif operation == "cancel" and job["status"] in {"pending", "queued", "leased"}:
                    await self.service.queue.cancel(session["job_id"], session["owner"],
                        source_channel=session["identity"], permission_check=permission)
                    message = "已取消此文件。"
                elif operation == "cancel":
                    message = "此任务已结束或已开始提交，不能保证远程取消，请查看打印机队列。"
            except ValueError as exc:
                permission()
                latest = await self.service.queue.get_job(session["job_id"], session["owner"],
                    source_channel=session["identity"], permission_check=permission)
                if latest["status"] == job["status"]:
                    result = await self._snapshot(session)
                    result.update(ok=False, action_message=failure_reason(str(exc)))
                    return self._response(result, 409)
                # Another browser tab or chat may have won the confirmation.
                message = "任务状态已更新，不会重复提交。"
            permission()
            result = await self._snapshot(session)
            result["action_message"] = message
            return self._response(result)
        except ValueError:
            return self._error("链接已失效或权限已变更，请返回聊天查看任务。", 403)

    async def info(self, request):
        if request.method != "POST":
            return self._error("请通过上传页面查看文件状态。", 405)
        if not self._origin_allowed(request):
            return self._error("请使用聊天中的原始上传链接。", 403)
        if request.body:
            return self._error("状态查询不需要提交文件。", 400)
        async with self.lock:
            found = self._lookup(request)
            if found is None:
                return self._error("链接已失效或打印权限已变更，请回到聊天重新发送“打印文件”。", 403)
            _, session = found
            try:
                return self._response(await self._snapshot(session))
            except ValueError:
                return self._error("链接已失效或打印权限已变更，请回到聊天重新发送“打印文件”。", 403)

    async def upload(self, request):
        if request.method != "POST":
            return self._error("请通过上传页面选择文件。", 405)
        if not self._origin_allowed(request):
            return self._error("请使用聊天中的原始上传链接。", 403)
        async with self.lock:
            found = self._lookup(request)
            if found is None:
                return self._error("链接已失效或打印权限已变更，请回到聊天重新发送“打印文件”。", 403)
            digest, session = found
            if session["state"] != "ready":
                # An uncertain HTTP result must only be queried, never resubmitted.
                try:
                    return self._response(await self._snapshot(session), 202 if session["state"] == "processing" else 200)
                except ValueError:
                    return self._error("打印权限已变更，请回到聊天查看进度。", 403)
            cfg = self.service.config()
            maximum = min(cfg["max_file_mb"] * 1024 * 1024, WEBHOOK_MAX_BYTES)
            if not request.body or len(request.body) > maximum:
                return self._error(f"文件为空或超过 {maximum // (1024 * 1024)} MB，请重新选择。", 400, state="ready")
            supplied = request.headers.get("x-print-filename", "")
            if not isinstance(supplied, str) or not supplied or len(supplied) > 2048 or re.search(r"%(?![0-9a-fA-F]{2})", supplied):
                return self._error("文件名无效，请重新选择文件。", 400, state="ready")
            try:
                filename = safe_name(unquote(supplied, encoding="utf-8", errors="strict"))
            except UnicodeError:
                return self._error("文件名无法读取，请重新选择文件。", 400, state="ready")
            if self.service.receiving >= 4:
                return self._error("正在收取其他文件，请稍后点击上传。", 429, state="ready")
            self._allowed(session)
            session.update(state="processing", work_started=False, message="正在检查并收取文件，请不要重复上传。")
            self.service.receiving += 1
            try:
                # Only the automatic-print option explicitly shown on this
                # page may authorise it. Later config changes cannot escalate
                # an upload that promised to wait for chat confirmation.
                allow_auto_print = request.headers.get("x-print-auto-print") == "true"
                task = self.service.spawn(self._process(digest, session, request.body, filename, allow_auto_print), "print_web_upload")
                if callable(getattr(task, "add_done_callback", None)):
                    def completed(_task):
                        # Cancelling a task before its coroutine first runs does
                        # not execute that coroutine's try/finally block.
                        if not session["work_started"]:
                            self.service.receiving -= 1
                            session.update(state="failed", message="文件处理未能开始，请回到聊天重新获取链接。")
                    task.add_done_callback(completed)
            except BaseException as exc:
                self.service.receiving -= 1
                session.update(state="failed", message="文件处理未能启动，请回到聊天重新获取链接。")
                if isinstance(exc, asyncio.CancelledError):
                    raise
                self.service.ctx.log.warning("网页打印文件处理未能启动（%s）", type(exc).__name__)
                return self._response(await self._snapshot(session), 503)
            return self._response(await self._snapshot(session), 202)

    async def _received_result(self, session, job):
        if job is None:
            return False
        # This is an internal lookup of the fixed reservation, not a response to
        # the capability holder. Public reads still recheck all permissions in
        # _snapshot. A concurrent permission change must not relabel a file
        # already committed to the print queue as an unsuccessful upload.
        latest = await self.service.queue.get_job(
            job["id"], session["owner"], source_channel=session["identity"],
        )
        if latest.get("pages") and latest["status"] != "receiving":
            session.update(state="complete", message="文件已收到，请回到聊天查看打印任务。")
            return True
        session.update(state="failed", message=failure_reason(latest.get("message"))
                       if latest.get("message") else "文件未收取，请回到聊天查看原因。")
        return False

    async def _process(self, digest, session, content, filename, allow_auto_print):
        session["work_started"] = True
        entered_receive = False
        job = None
        try:
            self._allowed(session)
            # Reserve and receive share one managed task, so a disconnected HTTP
            # request cannot leave a committed reservation without a downloader.
            job = await self.service.queue.reserve(
                f"wecom-upload:{session['identity']}:{session['owner'].rsplit(':', 1)[-1].casefold()}:{digest}",
                session["owner"], filename, "wecom", len(content), source_channel=session["identity"],
            )
            if job is None:
                raise ValueError("此链接已处理，不会重复收取；请回到聊天查看进度。")
            session["job_id"] = job["id"]
            self.service.ctx.log.info("网页打印文件已接收：任务 %s，%s 字节", job["id"], len(content))
            self._allowed(session)

            async def download(path, maximum):
                self._allowed(session)
                if not content or len(content) > min(maximum, WEBHOOK_MAX_BYTES):
                    raise ValueError("文件为空或超过当前大小上限。")
                await asyncio.to_thread(path.write_bytes, content)
                self._allowed(session)
                return filename

            entered_receive = True
            await self.service.receive(job, download, allow_auto_print=allow_auto_print)
            # A later printer-side failure is not an upload failure; never offer
            # to resubmit a file that has already entered the durable queue.
            await self._received_result(session, job)
        except asyncio.CancelledError:
            session.update(state="failed", message="文件处理已中断，请先回到聊天查看进度，不要重复打印。")
            if job is not None:
                try:
                    await self.service.queue.fail_receive(job["id"], "文件上传处理已中断，请先回到聊天查看进度")
                    await self._received_result(session, job)
                except Exception:
                    self.service.ctx.log.error("网页打印任务中断状态保存失败，请重载插件后检查队列")
            raise
        except Exception as exc:
            known_reasons = {
                "正在收取其他文件，请稍后重发": "文件收取繁忙，请稍后回到聊天重新获取上传链接。",
                "今日收件数量达到上限": "文件收取已达到今日上限，请稍后再试。",
                "此链接已处理，不会重复收取；请回到聊天查看进度。": "文件已处理，不会重复收取；请回到聊天查看进度。",
            }
            session.update(state="failed", message=known_reasons.get(str(exc), failure_reason(str(exc))) if isinstance(exc, ValueError)
                           else "文件处理未完成，请先回到聊天查看进度。")
            if job is not None and not entered_receive:
                try:
                    await self.service.queue.fail_receive(job["id"], session["message"])
                except Exception:
                    self.service.ctx.log.error("网页打印任务保存失败，请重载插件后检查队列")
            if job is not None:
                try:
                    await self._received_result(session, job)
                except Exception:
                    pass  # Preserve the non-retryable failure when state IO failed.
            self.service.ctx.log.warning("网页打印文件处理未完成（%s）", type(exc).__name__)
        finally:
            if not entered_receive:
                self.service.receiving -= 1
