"""Evidence images: page renders, highlight boxes for cited regions, crops."""

from __future__ import annotations

import io
import math
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from PIL import Image, ImageDraw

from docwiki.contracts import ExtractedDoc
from docwiki.extract._draft import Draft
from docwiki.extract._images import ImageDecodeError, png_bytes
from docwiki.extract.formats import detect_format
from docwiki.extract.local_image import load_page_image
from docwiki.extract.local_pdf import PdfOpenError, open_pdf, render_page_png

__all__ = ["DEFAULT_DPI", "HIGHLIGHT_FILL", "HIGHLIGHT_OUTLINE", "PageImages", "draw_highlights"]

DEFAULT_DPI = 150
HIGHLIGHT_FILL = (255, 214, 0, 72)
HIGHLIGHT_OUTLINE = (214, 120, 0, 255)


def draw_highlights(png: bytes, boxes: Iterable[Sequence[float]]) -> bytes:
    """Draw semi-transparent highlight rectangles (normalised ``[x0, y0, x1, y1]``) on a PNG."""
    unique = sorted({tuple(round(float(v), 4) for v in box) for box in boxes if len(box) == 4})
    with Image.open(io.BytesIO(png)) as source:
        base = source.convert("RGBA")
    if not unique:
        return png_bytes(base)
    width, height = base.size
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    stroke = max(2, round(min(width, height) / 400))
    pad = max(2, round(min(width, height) / 300))
    for x0, y0, x1, y1 in unique:
        rectangle = (
            max(0, math.floor(x0 * width) - pad),
            max(0, math.floor(y0 * height) - pad),
            min(width - 1, math.ceil(x1 * width) + pad),
            min(height - 1, math.ceil(y1 * height) + pad),
        )
        if rectangle[2] <= rectangle[0] or rectangle[3] <= rectangle[1]:
            continue
        draw.rectangle(rectangle, fill=HIGHLIGHT_FILL, outline=HIGHLIGHT_OUTLINE, width=stroke)
    return png_bytes(Image.alpha_composite(base, overlay))


class PageImages:
    """Page images of one source: the extract stage's renders, else rendered on demand."""

    def __init__(
        self,
        doc: ExtractedDoc,
        raw_file: Path,
        provided: Mapping[int, bytes] | None,
        *,
        dpi: int = DEFAULT_DPI,
    ) -> None:
        self._raw_file = raw_file
        self._provided = provided or {}
        self._dpi = dpi
        self._cache: dict[int, bytes | None] = {}
        self._data: bytes | None = None
        detected = detect_format(doc.source_path)
        self._family = detected[0] if detected else None

    def get(self, page: int) -> bytes | None:
        if page in self._provided:
            return self._provided[page]
        if page not in self._cache:
            self._cache[page] = self._render(page)
        return self._cache[page]

    def raw(self) -> bytes | None:
        """The original file bytes (read once), or None when unreadable."""
        if self._data is None:
            try:
                self._data = self._raw_file.read_bytes()
            except OSError:
                return None
        return self._data

    def _render(self, page: int) -> bytes | None:
        if self._family not in ("pdf", "image"):
            return None
        data = self.raw()
        if data is None:
            return None
        if self._family == "image":
            if page != 1:
                return None
            try:
                return load_page_image(data, Draft())
            except ImageDecodeError:
                return None
        try:
            with open_pdf(data) as pdf:
                if not 1 <= page <= len(pdf):
                    return None
                pdf_page = pdf[page - 1]
                try:
                    return render_page_png(pdf_page, self._dpi)
                finally:
                    pdf_page.close()
        except PdfOpenError:
            return None
