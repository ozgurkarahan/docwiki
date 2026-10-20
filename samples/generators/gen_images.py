"""Site photos (JPG): the slab poured and the delivered pallets.

The photos are generator inputs under ``assets/photos`` (provenance in ``PROVENANCE.md`` there);
the bible names the asset of each photo (``facts.photos.<key>.asset`` for the document
``photo-<key>``). The generator draws the stamp as a small overlay caption, the only text in a
photo, and re-encodes the image without EXIF, ICC profile or comments.
"""

from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .common import STAMP
from .fonts import pil_font
from .world import REPO_ROOT, World

ASSET_DIR = Path(__file__).resolve().parent / "assets" / "photos"
MAX_WIDTH = 1600

Box = tuple[int, int, int, int]


def asset_path(w: World, doc_id: str) -> Path:
    """The asset of the document ``photo-<key>``, checked against the bible photo entry."""
    entry = w.facts["photos"][doc_id.removeprefix("photo-")]
    if str(entry["date"]) != str(w.doc(doc_id)["date"]):
        raise ValueError(f"{doc_id}: the photo date differs from the document date")
    source = (REPO_ROOT / str(entry["asset"])).resolve()
    if source.parent != ASSET_DIR or not source.is_file():
        raise FileNotFoundError(f"photo asset missing or outside {ASSET_DIR}: {source}")
    return source


def source_image(w: World, doc_id: str) -> Image.Image:
    """The photo asset of a document as a colour image, at most ``MAX_WIDTH`` pixels wide."""
    with Image.open(asset_path(w, doc_id)) as original:
        img = original.convert("RGB")
    if img.width > MAX_WIDTH:
        height = round(img.height * MAX_WIDTH / img.width)
        img = img.resize((MAX_WIDTH, height), Image.Resampling.LANCZOS)
    return img


def caption_layout(size: tuple[int, int]) -> tuple[Box, tuple[int, int], ImageFont.FreeTypeFont]:
    """Band box, text origin and font of the stamp caption (bottom-left corner)."""
    width, height = size
    font_size = max(14, round(width / 64))
    font = pil_font(font_size, "bold")
    left, top, right, bottom = font.getbbox(STAMP)
    pad = round(font_size * 0.55)
    margin = round(font_size * 0.8)
    box = (margin, height - margin - (bottom - top) - 2 * pad,
           margin + (right - left) + 2 * pad, height - margin)
    return box, (box[0] + pad - left, box[1] + pad - top), font


def _caption(img: Image.Image) -> Image.Image:
    """The stamp in white on a translucent dark band."""
    box, origin, font = caption_layout(img.size)
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    draw.rectangle(box, fill=(0, 0, 0, 150))
    draw.text(origin, STAMP, font=font, fill=(255, 255, 255, 235))
    return Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")


def _photo(w: World, doc_id: str) -> bytes:
    img = _caption(source_image(w, doc_id))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=86, optimize=True, subsampling=2)
    return buf.getvalue()


def photo_dalle(w: World) -> bytes:
    return _photo(w, "photo-dalle")


def photo_palettes(w: World) -> bytes:
    return _photo(w, "photo-palettes")
