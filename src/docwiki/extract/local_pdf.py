"""PDF via pypdfium2: positioned text, embedded figures and page renders (local adapter).

PDFium is not thread-safe, so every call into it happens under :data:`PDFIUM_LOCK` (extractions
run in worker threads and may overlap).
"""

from __future__ import annotations

import ctypes
import hashlib
import itertools
import re
import statistics
import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date

import pypdfium2 as pdfium
import pypdfium2.raw as pdfium_c

from docwiki.contracts.enums import BlockKind
from docwiki.contracts.locators import PdfPageLocator
from docwiki.extract._draft import Draft, DraftBlock, DraftFigure, round_bbox
from docwiki.extract._images import MAX_IMAGE_SIDE, crop_png, png_bytes
from docwiki.extract._text import BULLET_RE, clean_text, lang_from_tag, one_line

__all__ = [
    "PDFIUM_LOCK",
    "PdfOpenError",
    "PdfPages",
    "extract_pdf",
    "open_pdf",
    "pdf_pages",
    "render_page_png",
]

PDFIUM_LOCK = threading.RLock()
_DEVICE = 1_000_000
MIN_FIGURE_AREA = 0.004
"""Images smaller than 0.4 % of the page (icons, bullets, rules) are not figures."""
MAX_FIGURE_AREA = 0.85
"""Images covering most of the page are page scans or backgrounds, not figures."""
DECORATIVE_PAGES = 3
"""The same image on this many pages (logo, watermark) is decoration, not a figure."""


class PdfOpenError(ValueError):
    """The bytes are not a PDF that PDFium can open (damaged, encrypted, not a PDF)."""


@contextmanager
def open_pdf(data: bytes) -> Iterator[pdfium.PdfDocument]:
    """Open a PDF under the PDFium lock (held until the context exits)."""
    with PDFIUM_LOCK:
        try:
            pdf = pdfium.PdfDocument(data)
        except pdfium.PdfiumError as exc:
            raise PdfOpenError(f"not a readable PDF (encrypted or damaged?): {exc}") from exc
        try:
            yield pdf
        finally:
            pdf.close()


class _Geometry:
    """Page space → normalised top-left coordinates of the displayed (rotated, cropped) page."""

    def __init__(self, page: pdfium.PdfPage) -> None:
        self._page = page

    def point(self, x: float, y: float) -> tuple[float, float]:
        dx, dy = ctypes.c_int(), ctypes.c_int()
        pdfium_c.FPDF_PageToDevice(self._page, 0, 0, _DEVICE, _DEVICE, 0, x, y, dx, dy)
        return dx.value / _DEVICE, dy.value / _DEVICE

    def box(self, left: float, bottom: float, right: float, top: float) -> list[float] | None:
        corners = [
            self.point(left, bottom),
            self.point(left, top),
            self.point(right, bottom),
            self.point(right, top),
        ]
        xs = [x for x, _ in corners]
        ys = [y for _, y in corners]
        return round_bbox((min(xs), min(ys), max(xs), max(ys)))


def render_page_png(page: pdfium.PdfPage, dpi: int) -> bytes:
    """Render one page to PNG at ``dpi`` (capped so that the longest side stays reasonable)."""
    width, height = page.get_size()
    scale = dpi / 72.0
    longest = max(width, height) * scale
    if longest > MAX_IMAGE_SIDE:
        scale *= MAX_IMAGE_SIDE / longest
    bitmap = page.render(scale=scale)
    try:
        return png_bytes(bitmap.to_pil())
    finally:
        bitmap.close()


@dataclass
class _Line:
    text: str
    box: tuple[float, float, float, float] | None
    size: float
    visible: int


@dataclass
class _Paragraph:
    lines: list[_Line] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(line.text for line in self.lines)

    @property
    def size(self) -> float:
        sizes = [line.size for line in self.lines if line.size > 0]
        return statistics.median(sizes) if sizes else 0.0

    @property
    def box(self) -> tuple[float, float, float, float] | None:
        boxes = [line.box for line in self.lines if line.box is not None]
        if not boxes:
            return None
        return (
            min(b[0] for b in boxes),
            min(b[1] for b in boxes),
            max(b[2] for b in boxes),
            max(b[3] for b in boxes),
        )


@dataclass
class _PageText:
    lines: list[_Line]
    visible: int
    unmapped: int


def _read_lines(textpage: pdfium.PdfTextPage) -> _PageText:
    count = textpage.count_chars()
    lines: list[_Line] = []
    units: list[str] = []
    boxes: list[tuple[float, float, float, float]] = []
    sizes: list[float] = []
    visible = unmapped = line_visible = 0

    def flush() -> None:
        nonlocal units, boxes, sizes, line_visible
        raw = "".join(units).encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")
        text = clean_text(raw)
        if text:
            box = (
                (
                    min(b[0] for b in boxes),
                    min(b[1] for b in boxes),
                    max(b[2] for b in boxes),
                    max(b[3] for b in boxes),
                )
                if boxes
                else None
            )
            size = statistics.median(sizes) if sizes else 0.0
            lines.append(_Line(text, box, size, line_visible))
        units, boxes, sizes, line_visible = [], [], [], 0

    for index in range(count):
        code = pdfium_c.FPDFText_GetUnicode(textpage, index)
        if code == 0x0D:
            continue
        if code == 0x0A:
            flush()
            continue
        if code == 0:
            unmapped += 1
            continue
        char = chr(code)
        units.append(char)
        if char.isspace() or pdfium_c.FPDFText_IsGenerated(textpage, index) == 1:
            continue
        visible += 1
        line_visible += 1
        if code == 0xFFFD:
            unmapped += 1
        try:
            left, bottom, right, top = textpage.get_charbox(index, loose=True)
        except pdfium.PdfiumError:
            pass
        else:
            if right > left and top > bottom:
                boxes.append((left, bottom, right, top))
                font_size = pdfium_c.FPDFText_GetFontSize(textpage, index)
                sizes.append(font_size if font_size > 1.5 else top - bottom)
    flush()
    return _PageText(lines, visible, unmapped)


def _body_size(lines: list[_Line]) -> float:
    weights: Counter[float] = Counter()
    for line in lines:
        if line.size > 0:
            weights[round(line.size * 2) / 2] += max(1, line.visible)
    if not weights:
        return 0.0
    return sorted(weights.items(), key=lambda item: (-item[1], item[0]))[0][0]


def _paragraphs(lines: list[_Line]) -> list[_Paragraph]:
    """Group lines into paragraphs using vertical gaps, font-size changes and bullets."""
    gaps: list[float] = []
    for previous, current in itertools.pairwise(lines):
        if previous.box and current.box:
            gap = previous.box[1] - current.box[3]
            height = min(previous.box[3] - previous.box[1], current.box[3] - current.box[1])
            if gap >= -0.5 * height and height > 0:
                gaps.append(max(0.0, gap) / height)
    typical = sorted(gaps)[len(gaps) // 4] if gaps else 0.0
    threshold = max(0.6, typical + 0.4)

    paragraphs: list[_Paragraph] = []
    for line in lines:
        if not paragraphs:
            paragraphs.append(_Paragraph([line]))
            continue
        previous = paragraphs[-1].lines[-1]
        new = bool(BULLET_RE.match(line.text))
        if previous.box and line.box:
            height = min(previous.box[3] - previous.box[1], line.box[3] - line.box[1])
            gap = previous.box[1] - line.box[3]
            if height <= 0 or gap < -0.5 * height or gap / height > threshold:
                new = True
        if previous.size > 0 and line.size > 0:
            ratio = max(previous.size, line.size) / min(previous.size, line.size)
            if ratio > 1.15:
                new = True
        if new:
            paragraphs.append(_Paragraph([line]))
        else:
            paragraphs[-1].lines.append(line)
    return paragraphs


def _heading_level(size: float, body: float, text: str, line_count: int) -> int | None:
    if body <= 0 or size <= 0 or len(text) > 200 or line_count > 3:
        return None
    ratio = size / body
    if ratio < 1.2:
        return None
    if ratio >= 1.75:
        return 1
    return 2 if ratio >= 1.4 else 3


@dataclass
class _FigureCandidate:
    page: int
    bbox: list[float]
    digest: str | None


@dataclass
class PdfPages:
    """Page-level facts shared by the local and Content Understanding adapters."""

    page_count: int
    extracted: int
    images: dict[int, bytes]
    text_layer: dict[int, bool]


def _catalog_lang(pdf: pdfium.PdfDocument) -> str | None:
    try:
        needed = pdfium_c.FPDFCatalog_GetLanguage(pdf, None, 0)
        if needed <= 2:
            return None
        buffer = ctypes.create_string_buffer(needed)
        pdfium_c.FPDFCatalog_GetLanguage(pdf, buffer, needed)
        return lang_from_tag(buffer.raw[: needed - 2].decode("utf-16-le", "ignore"))
    except (AttributeError, ctypes.ArgumentError):  # pragma: no cover - older PDFium builds
        return None


_PDF_DATE_RE = re.compile(r"^D:(\d{4})(\d{2})?(\d{2})?")
_FILENAME_TITLE_RE = re.compile(r"\.(?:docx?|pdf|pptx?|xlsx?|txt|md)$", re.IGNORECASE)


def _metadata(pdf: pdfium.PdfDocument, draft: Draft) -> None:
    try:
        meta = pdf.get_metadata_dict(skip_empty=True)
    except pdfium.PdfiumError:  # pragma: no cover - defensive
        meta = {}
    title = one_line(meta.get("Title", ""))
    if title and not _FILENAME_TITLE_RE.search(title) and title.lower() != "untitled":
        draft.title_hint = title[:200]
    match = _PDF_DATE_RE.match(meta.get("CreationDate", ""))
    if match:
        try:
            draft.authored = date(int(match[1]), int(match[2] or 1), int(match[3] or 1))
        except ValueError:
            draft.warn("pdf-metadata", "invalid creation date ignored")
    draft.lang = _catalog_lang(pdf)


def pdf_pages(data: bytes, *, max_pages: int, dpi: int, draft: Draft | None = None) -> PdfPages:
    """Render pages ``1..max_pages`` and report which ones have a text layer."""
    with open_pdf(data) as pdf:
        total = len(pdf)
        extracted = min(total, max_pages)
        images: dict[int, bytes] = {}
        text_layer: dict[int, bool] = {}
        for index in range(extracted):
            page = pdf[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range() if textpage.count_chars() > 0 else ""
                finally:
                    textpage.close()
                text_layer[index + 1] = any(not char.isspace() for char in text)
                images[index + 1] = render_page_png(page, dpi)
            finally:
                page.close()
        if draft is not None:
            _metadata(pdf, draft)
    return PdfPages(total, extracted, images, text_layer)


def extract_pdf(data: bytes, draft: Draft, *, max_pages: int, dpi: int) -> None:
    """Local PDF adapter: one block per paragraph with a ``pdf-page`` locator and bbox."""
    pages: list[tuple[int, list[DraftBlock], list[_FigureCandidate]]] = []
    with open_pdf(data) as pdf:
        total = len(pdf)
        extracted = min(total, max_pages)
        draft.page_count = total
        _metadata(pdf, draft)
        if total > max_pages:
            draft.warn("max-pages", f"extracted the first {max_pages} of {total} pages")
        for index in range(extracted):
            number = index + 1
            page = pdf[index]
            try:
                pages.append(_extract_page(page, number, draft, dpi))
            finally:
                page.close()

    seen_on: dict[str, set[int]] = {}
    for number, _, candidates in pages:
        for candidate in candidates:
            if candidate.digest:
                seen_on.setdefault(candidate.digest, set()).add(number)
    decorative = {digest for digest, where in seen_on.items() if len(where) >= DECORATIVE_PAGES}

    for number, blocks, candidates in pages:
        figures: list[DraftFigure] = []
        for candidate in candidates:
            if candidate.digest in decorative:
                continue
            png = crop_png(draft.page_images[number], candidate.bbox)
            if png is not None:
                locator = PdfPageLocator(page=number, bbox=candidate.bbox)
                figures.append(DraftFigure(locator, png, None, candidate.bbox))
        draft.items.extend(_merge_reading_order(blocks, figures))


def _top(item: DraftBlock | DraftFigure) -> float | None:
    bbox = getattr(item.locator, "bbox", None)
    return bbox[1] if bbox else None


def _merge_reading_order(
    blocks: list[DraftBlock], figures: list[DraftFigure]
) -> list[DraftBlock | DraftFigure]:
    """Insert each figure before the first text block that starts below the figure's top."""
    merged: list[DraftBlock | DraftFigure] = list(blocks)
    for figure in sorted(figures, key=lambda f: (_top(f) or 0.0, f.bbox[0] if f.bbox else 0.0)):
        top = _top(figure) or 0.0
        position = len(merged)
        for index, item in enumerate(merged):
            item_top = _top(item)
            if isinstance(item, DraftBlock) and item_top is not None and item_top > top:
                position = index
                break
        merged.insert(position, figure)
    return merged


def _extract_page(
    page: pdfium.PdfPage, number: int, draft: Draft, dpi: int
) -> tuple[int, list[DraftBlock], list[_FigureCandidate]]:
    geometry = _Geometry(page)
    textpage = page.get_textpage()
    try:
        page_text = _read_lines(textpage)
    finally:
        textpage.close()
    draft.page_images[number] = render_page_png(page, dpi)

    blocks: list[DraftBlock] = []
    if page_text.visible == 0:
        draft.warn(
            "needs-ocr", f"p. {number} has no text layer (local extraction does not run OCR)"
        )
        blocks.append(DraftBlock("ocr-line", "", PdfPageLocator(page=number), "ocr"))
    else:
        if page_text.unmapped > page_text.visible // 2:
            draft.warn("pdf-text-unmappable", f"p. {number} has characters without Unicode")
        body = _body_size(page_text.lines)
        for paragraph in _paragraphs(page_text.lines):
            text = paragraph.text
            box = paragraph.box
            bbox = geometry.box(*box) if box else None
            level = _heading_level(paragraph.size, body, text, len(paragraph.lines))
            kind: BlockKind = (
                "heading" if level else ("list" if BULLET_RE.match(text) else "paragraph")
            )
            locator = PdfPageLocator(page=number, bbox=bbox)
            blocks.append(DraftBlock(kind, text, locator, "native-text", level=level))

    candidates: list[_FigureCandidate] = []
    for obj in page.get_objects(filter=[pdfium_c.FPDF_PAGEOBJ_IMAGE], max_depth=8):
        try:
            bbox = geometry.box(*obj.get_bounds())
        except pdfium.PdfiumError:
            continue
        if bbox is None:
            continue
        area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
        if area < MIN_FIGURE_AREA or area > MAX_FIGURE_AREA:
            continue
        try:
            digest = hashlib.sha256(bytes(obj.get_data(decode_simple=False))).hexdigest()
        except (pdfium.PdfiumError, ValueError):
            digest = None
        candidates.append(_FigureCandidate(number, bbox, digest))
    return number, blocks, candidates
