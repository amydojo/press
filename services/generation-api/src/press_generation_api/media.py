from __future__ import annotations

import struct
import zlib
from io import BytesIO
from typing import Any

from press_generation_api.config import Settings
from press_generation_api.domain.models import ValidationResult

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def create_fixture_png(width: int = 1024, height: int = 1024) -> bytes:
    """Create a deterministic RGB PNG without adding a test-only image dependency."""

    rows = bytearray()
    for y in range(height):
        rows.append(0)
        for x in range(width):
            if 180 < x < 844 and 220 < y < 804:
                color = (98, 112, 106)
            elif (x - 512) ** 2 + (y - 512) ** 2 < 170**2:
                color = (193, 115, 92)
            else:
                color = (237, 231, 220)
            rows.extend(color)

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        _PNG_SIGNATURE
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(bytes(rows), level=9))
        + chunk(b"IEND", b"")
    )


def _png_fallback(data: bytes) -> tuple[str, int, int, bool]:
    if not data.startswith(_PNG_SIGNATURE):
        raise ValueError("not a PNG")
    offset = len(_PNG_SIGNATURE)
    width = height = 0
    idat = bytearray()
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height = struct.unpack(">II", payload[:8])
        elif kind == b"IDAT":
            idat.extend(payload)
        elif kind == b"IEND":
            break
    if width <= 0 or height <= 0 or not idat:
        raise ValueError("invalid PNG structure")
    decoded = zlib.decompress(bytes(idat))
    sample = decoded[: min(len(decoded), 256 * 1024)]
    non_blank = len(set(sample)) > 4
    return "image/png", width, height, non_blank


def _decode_with_pillow(data: bytes) -> tuple[str, int, int, bool]:
    try:
        from PIL import Image, ImageStat  # type: ignore[import-not-found]
    except ImportError:
        return _png_fallback(data)
    with Image.open(BytesIO(data)) as image:
        image.load()
        formats = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
        mime = formats.get(str(image.format).upper())
        if mime is None:
            raise ValueError("unsupported image format")
        width, height = image.size
        grayscale = image.convert("L").resize((64, 64))
        variance = float(ImageStat.Stat(grayscale).var[0])
        extrema: Any = grayscale.getextrema()
        non_blank = variance >= 1.0 and extrema[0] != extrema[1]
        return mime, width, height, non_blank


def validate_image_bytes(data: bytes, settings: Settings) -> ValidationResult:
    import hashlib

    checks: dict[str, bool] = {
        "bytesExist": bool(data),
        "fileSizeAllowed": 0 < len(data) <= settings.MAX_GENERATED_ASSET_BYTES,
    }
    errors: list[str] = []
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    if not checks["bytesExist"]:
        errors.append("asset bytes are empty")
    if not checks["fileSizeAllowed"]:
        errors.append("asset file size is outside the configured bounds")
    try:
        mime_type, width, height, non_blank = _decode_with_pillow(data)
        checks["fileDecodes"] = True
        checks["mimeAllowed"] = mime_type in {"image/png", "image/jpeg", "image/webp"}
        checks["minimumDimensions"] = (
            width >= settings.MIN_IMAGE_EDGE and height >= settings.MIN_IMAGE_EDGE
        )
        checks["maximumDimensions"] = (
            width <= settings.MAX_IMAGE_EDGE and height <= settings.MAX_IMAGE_EDGE
        )
        checks["notBlank"] = non_blank
        if not checks["mimeAllowed"]:
            errors.append("asset MIME type is unsupported")
        if not checks["minimumDimensions"]:
            errors.append("asset dimensions are below the configured minimum")
        if not checks["maximumDimensions"]:
            errors.append("asset dimensions exceed the configured maximum")
        if not checks["notBlank"]:
            errors.append("asset is blank or trivially empty")
    except (OSError, ValueError, zlib.error):
        checks.update(
            {
                "fileDecodes": False,
                "mimeAllowed": False,
                "minimumDimensions": False,
                "maximumDimensions": False,
                "notBlank": False,
            }
        )
        errors.append("asset could not be decoded as an image")
    digest = hashlib.sha256(data).hexdigest() if data else None
    return ValidationResult(
        valid=all(checks.values()),
        checks=checks,
        errors=errors,
        mime_type=mime_type,
        size_bytes=len(data),
        width=width,
        height=height,
        sha256=digest,
    )
