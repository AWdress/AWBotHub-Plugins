"""参考图的受限下载与规范化；不在磁盘保存用户图片。"""
from __future__ import annotations

import asyncio
import warnings
from io import BytesIO

MAX_REFERENCE_BYTES = 12 * 1024 * 1024
MAX_NORMALIZED_BYTES = 20 * 1024 * 1024
MAX_GENERATED_BYTES = 30 * 1024 * 1024
MAX_IMAGE_PIXELS = 32_000_000
_IMAGE_MIMES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class ImageInputError(RuntimeError):
    """可以直接展示的固定图片错误，不包含原始文件名或下载地址。"""


class _LimitedBuffer(BytesIO):
    def __init__(self, limit, error):
        super().__init__()
        self.limit, self.error = limit, error

    def write(self, data):
        if self.tell() + len(data) > self.limit:
            raise ImageInputError(self.error)
        return super().write(data)


def _normalize_image(data: bytes, *, reference: bool) -> bytes:
    """验证真实图片、转正方向并移除元数据，统一输出 PNG。"""
    from PIL import Image, ImageOps, UnidentifiedImageError

    limit = MAX_REFERENCE_BYTES if reference else MAX_GENERATED_BYTES
    if not isinstance(data, bytes) or not data or len(data) > limit:
        raise ImageInputError("参考图为空或超过 12MB，请换一张较小的图片" if reference else "生成的图片为空或超过 30MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(BytesIO(data)) as source:
                if source.format not in {"PNG", "JPEG", "WEBP", "GIF"}:
                    raise ImageInputError("仅支持 JPG、PNG、WebP 和 GIF 图片，GIF 使用第一帧")
                if min(source.size) <= 0 or source.width * source.height > MAX_IMAGE_PIXELS:
                    raise ImageInputError("图片分辨率过大，请缩小到 3200 万像素以内")
                if reference:
                    source.draft("RGB", (2048, 2048))
                source.seek(0)
                source.load()
                oriented = ImageOps.exif_transpose(source)
                if reference:
                    oriented.thumbnail((2048, 2048), Image.Resampling.LANCZOS)
                mode = "RGBA" if "A" in oriented.getbands() or "transparency" in oriented.info else "RGB"
                converted = oriented.convert(mode)
                # 新画布不继承 EXIF、定位信息、注释等元数据。
                clean = Image.new(mode, converted.size)
                clean.paste(converted)
                output_limit = MAX_NORMALIZED_BYTES if reference else MAX_GENERATED_BYTES
                with _LimitedBuffer(output_limit, "处理后的图片过大，请换一张较小的图片") as output:
                    clean.save(output, format="PNG")
                    return output.getvalue()
    except ImageInputError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ImageInputError("图片分辨率过大，请缩小到 3200 万像素以内") from exc
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError) as exc:
        raise ImageInputError("图片无法读取，请重新发送 JPG、PNG 或 WebP 原图") from exc


def normalize_generated_image(data: bytes) -> bytes:
    return _normalize_image(data, reference=False)


async def extract_reference_image(client, message) -> bytes:
    """下载一条明确指定的图片；任一失败都不得静默退回文字生图。"""
    photo, document = getattr(message, "photo", None), getattr(message, "document", None)
    if not photo and not document:
        raise ImageInputError("请回复一张图片，或发送图片时在说明中填写 /生图 修改要求")
    if not photo and str(getattr(document, "mime_type", "") or "").lower() not in _IMAGE_MIMES:
        raise ImageInputError("参考文件不是支持的图片，请发送 JPG、PNG、WebP 或 GIF")
    size = getattr(document, "size", None) if document else getattr(getattr(message, "file", None), "size", None)
    if isinstance(size, int) and size > MAX_REFERENCE_BYTES:
        raise ImageInputError("参考图超过 12MB，请换一张较小的图片")
    with _LimitedBuffer(MAX_REFERENCE_BYTES, "参考图超过 12MB，请换一张较小的图片") as output:
        try:
            result = await asyncio.wait_for(client.download_media(message, file=output), timeout=60)
            data = result if isinstance(result, bytes) else output.getvalue()
        except ImageInputError:
            raise
        except TimeoutError as exc:
            raise ImageInputError("参考图下载超时，请稍后重新发送命令；本次未调用生图") from exc
        except Exception as exc:
            raise ImageInputError("参考图下载失败，请重新发送图片；本次未调用生图") from exc
    return await asyncio.to_thread(_normalize_image, data, reference=True)
