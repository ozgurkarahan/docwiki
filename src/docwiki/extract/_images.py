"""Image helpers: deterministic PNG encoding, safe decoding, crops (Pillow)."""

from __future__ import annotations

import io
import math
from collections.abc import Sequence

from PIL import Image, ImageOps

__all__ = [
    "MAX_IMAGE_SIDE",
    "MIN_EMBEDDED_SIDE",
    "ImageDecodeError",
    "crop_png",
    "decode_image",
    "embedded_png",
    "image_size",
    "png_bytes",
    "to_rgb",
]

MAX_IMAGE_SIDE = 4096
"""Longest side of page images and figure crops kept by DocWiki (larger images are downscaled)."""


class ImageDecodeError(ValueError):
    """The bytes are not an image Pillow can decode safely."""


def to_rgb(image: Image.Image) -> Image.Image:
    """RGB copy; transparent pixels are composited on white."""
    if image.mode == "RGB":
        return image
    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        background = Image.new("RGB", rgba.size, (255, 255, 255))
        background.paste(rgba, mask=rgba.getchannel("A"))
        return background
    return image.convert("RGB")


def _limit(image: Image.Image, max_side: int) -> Image.Image:
    width, height = image.size
    if max(width, height) <= max_side:
        return image
    scale = max_side / max(width, height)
    size = (max(1, round(width * scale)), max(1, round(height * scale)))
    return image.resize(size, Image.Resampling.LANCZOS)


def png_bytes(image: Image.Image, *, max_side: int = MAX_IMAGE_SIDE) -> bytes:
    """Deterministic PNG (RGB, no metadata chunks), downscaled to ``max_side``."""
    buffer = io.BytesIO()
    _limit(to_rgb(image), max_side).save(buffer, format="PNG", compress_level=6)
    return buffer.getvalue()


def decode_image(data: bytes) -> tuple[Image.Image, int]:
    """Decode the first frame (EXIF orientation applied) and return it with the frame count."""
    try:
        with Image.open(io.BytesIO(data)) as opened:
            frames = int(getattr(opened, "n_frames", 1) or 1)
            opened.seek(0)
            image = ImageOps.exif_transpose(opened)
            image.load()
            return image.copy(), frames
    except (Image.DecompressionBombError, OSError, ValueError, SyntaxError) as exc:
        raise ImageDecodeError(f"{type(exc).__name__}: {exc}") from exc


def image_size(png: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(png)) as image:
        return image.size


MIN_EMBEDDED_SIDE = 24
"""Embedded pictures smaller than this (spacers, bullets, icons) are not figures."""


def embedded_png(blob: bytes) -> bytes | None:
    """PNG of an embedded raster picture (Office media); None for vector or tiny images."""
    try:
        image, _frames = decode_image(blob)
    except ImageDecodeError:
        return None
    if min(image.size) < MIN_EMBEDDED_SIDE:
        return None
    return png_bytes(image)


def crop_png(png: bytes, bbox: Sequence[float], *, max_side: int = MAX_IMAGE_SIDE) -> bytes | None:
    """Crop a normalised ``[x0, y0, x1, y1]`` region of a PNG; None when the region is empty."""
    with Image.open(io.BytesIO(png)) as image:
        width, height = image.size
        x0, y0, x1, y1 = bbox
        box = (
            max(0, min(width, math.floor(x0 * width))),
            max(0, min(height, math.floor(y0 * height))),
            max(0, min(width, math.ceil(x1 * width))),
            max(0, min(height, math.ceil(y1 * height))),
        )
        if box[2] - box[0] < 2 or box[3] - box[1] < 2:
            return None
        return png_bytes(image.crop(box), max_side=max_side)
