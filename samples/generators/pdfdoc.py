"""fpdf2 helpers: stamped header/footer, headings, paragraphs and business tables.

Every PDF embeds a subset of the DejaVu Sans TrueType fonts (:mod:`.fonts`): the PDF core fonts
only encode latin-1, so they cannot print the euro sign or "œ" of the French documents.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from fpdf import FPDF, FontFace
from fpdf.enums import XPos, YPos

from .common import GENERATOR_AUTHOR, STAMP, DocMeta
from .fonts import font_path

FAMILY = "DejaVu"
_STYLES = {"": "regular", "B": "bold", "I": "oblique", "BI": "bold-oblique"}
LEFT = 18.0
WIDTH = 174.0
GREY = (90, 90, 90)
HEAD_FILL = (222, 229, 238)
GROUP_FILL = (240, 243, 247)
TOTAL_FILL = (228, 234, 242)
_PAGE_LABELS = {"fr": "Page {page} sur {{nb}}", "en": "Page {page} of {{nb}}"}


def clean(text: str) -> str:
    """Plain spaces only (no non-breaking spaces), single-line breaks kept."""
    text = text.replace("\u00a0", " ").replace("\u202f", " ").replace("\u2009", " ")
    if "\r" in text or "\t" in text:
        raise ValueError(f"control character in PDF text: {text!r}")
    return text


@dataclass(frozen=True)
class Group:
    """A full-width row that opens a group of lines (for example a lot of a quote)."""

    text: str


@dataclass(frozen=True)
class Subtotal:
    """A right-aligned label spanning all columns but the last, which holds the amount."""

    label: str
    amount: str


class StampedPDF(FPDF):
    """A4 document whose header and footer both carry the fictional stamp."""

    def __init__(self, meta: DocMeta, header_left: str, footer_left: str = "") -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        for style, key in _STYLES.items():
            self.add_font(FAMILY, style, str(font_path(key)))
        self.meta = meta
        self.header_left = clean(header_left)
        self.footer_left = clean(footer_left)
        self.page_label = _PAGE_LABELS.get(meta.lang, _PAGE_LABELS["en"])
        self.set_margins(LEFT, 21, LEFT)
        self.set_auto_page_break(True, margin=22)
        self.set_title(clean(meta.title))
        self.set_subject(STAMP)
        self.set_author(GENERATOR_AUTHOR)
        self.set_creator(GENERATOR_AUTHOR)
        self.set_producer(GENERATOR_AUTHOR)
        self.set_keywords(clean(meta.keywords))
        self.set_creation_date(meta.created)
        self.set_lang(meta.lang)

    # -- page furniture -------------------------------------------------------------------
    def header(self) -> None:
        self.set_font(FAMILY, "", 7.5)
        self.set_text_color(*GREY)
        self.set_xy(LEFT, 9)
        self.cell(WIDTH * 0.58, 5, self.header_left, align="L")
        self.cell(WIDTH * 0.42, 5, STAMP, align="R")
        self.set_draw_color(160, 160, 160)
        self.line(LEFT, 15, LEFT + WIDTH, 15)
        self.set_text_color(0, 0, 0)
        self.set_xy(LEFT, 21)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_draw_color(160, 160, 160)
        self.line(LEFT, self.get_y() - 1, LEFT + WIDTH, self.get_y() - 1)
        self.set_font(FAMILY, "", 7.5)
        self.set_text_color(*GREY)
        self.cell(WIDTH * 0.30, 5, self.footer_left, align="L")
        self.cell(WIDTH * 0.48, 5, STAMP, align="C")
        self.cell(WIDTH * 0.22, 5, self.page_label.format(page=self.page_no()), align="R")
        self.set_text_color(0, 0, 0)

    # -- layout helpers -------------------------------------------------------------------
    def keep_space(self, height: float) -> None:
        """Start a new page unless ``height`` mm still fit above the bottom margin."""
        if self.get_y() + height > self.page_break_trigger:
            self.add_page()

    def lines_at(
        self,
        x: float,
        y: float,
        width: float,
        lines: Sequence[tuple[str, float, str]],
        align: str = "L",
    ) -> float:
        """Write ``(text, size, style)`` lines in a column starting at (x, y); return bottom y."""
        self.set_xy(x, y)
        for text, size, style in lines:
            self.set_font(FAMILY, style, size)
            self.set_x(x)
            self.multi_cell(width, size * 0.48, clean(text), align=align,
                            new_x=XPos.LEFT, new_y=YPos.NEXT)
        return self.get_y()

    def framed_lines(
        self, x: float, y: float, width: float, title: str, lines: Sequence[str],
        size: float = 9.5,
    ) -> float:
        """A framed block with a small grey title; return bottom y."""
        top = y
        self.set_xy(x + 3, y + 2.5)
        self.set_font(FAMILY, "B", 8)
        self.set_text_color(*GREY)
        self.cell(width - 6, 4, clean(title), new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.set_font(FAMILY, "", size)
        for line in lines:
            self.set_x(x + 3)
            self.multi_cell(width - 6, size * 0.5, clean(line), new_x=XPos.LEFT,
                            new_y=YPos.NEXT)
        bottom = self.get_y() + 2.5
        self.set_draw_color(150, 150, 150)
        self.rect(x, top, width, bottom - top)
        self.set_xy(LEFT, bottom)
        return bottom

    def h1(self, text: str) -> None:
        self.keep_space(18)
        self.ln(2)
        self.set_font(FAMILY, "B", 11.5)
        self.multi_cell(0, 6, clean(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def para(self, text: str, size: float = 9.5, style: str = "") -> None:
        self.set_font(FAMILY, style, size)
        self.multi_cell(0, size * 0.5, clean(text), align="L", new_x=XPos.LMARGIN,
                        new_y=YPos.NEXT)
        self.ln(1.6)

    def label_para(self, label: str, text: str, size: float = 9.5) -> None:
        """``Label : text`` with a bold label, wrapped as one paragraph."""
        self.set_x(LEFT)
        self.set_font(FAMILY, "B", size)
        self.write(size * 0.5, f"{clean(label)} : ")
        self.set_font(FAMILY, "", size)
        self.write(size * 0.5, clean(text))
        self.ln(size * 0.5 + 1.6)

    def bullets(self, items: Sequence[str], size: float = 9.5) -> None:
        self.set_font(FAMILY, "", size)
        for item in items:
            self.set_x(LEFT + 2)
            self.cell(5, size * 0.5, "-")
            self.multi_cell(WIDTH - 7, size * 0.5, clean(item), align="L",
                            new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(0.8)
        self.ln(1)

    # -- tables ---------------------------------------------------------------------------
    def fits(self, draw: Callable[[], object]) -> bool:
        """True when ``draw()`` renders without a page break (dry run, state restored)."""
        with self.offset_rendering() as dummy:
            draw()
        return not dummy.page_break_triggered

    def grid(
        self,
        header: Sequence[str],
        rows: Sequence[Sequence[str] | Group | Subtotal],
        widths: Sequence[float],
        align: Sequence[str],
        size: float = 8.5,
    ) -> None:
        """A bordered table with group rows and subtotal rows.

        A group (a ``Group`` row and the rows up to the next one) never splits across pages; the
        heading row is repeated at the top of every page the table continues on.
        """
        blocks: list[list[Sequence[str] | Group | Subtotal]] = []
        for row in rows:
            if isinstance(row, Group) or not blocks:
                blocks.append([])
            blocks[-1].append(row)
        self._grid_rows([header], widths, align, size, heading=True)
        for block in blocks:
            if not self.fits(lambda block=block: self._grid_rows(block, widths, align, size)):
                self.add_page()
                self._grid_rows([header], widths, align, size, heading=True)
            self._grid_rows(block, widths, align, size)
        self.ln(2.5)

    def _grid_rows(
        self,
        rows: Sequence[Sequence[str] | Group | Subtotal],
        widths: Sequence[float],
        align: Sequence[str],
        size: float,
        heading: bool = False,
    ) -> None:
        self.set_font(FAMILY, "", size)
        group_face = FontFace(emphasis="BOLD", fill_color=GROUP_FILL)
        subtotal_face = FontFace(emphasis="BOLD")
        with self.table(
            col_widths=tuple(widths),
            text_align=tuple(align),
            first_row_as_headings=heading,
            headings_style=FontFace(emphasis="BOLD", fill_color=HEAD_FILL),
            line_height=size * 0.5,
            padding=(0.9, 1.4),
        ) as table:
            for row in rows:
                cells = table.row()
                if isinstance(row, Group):
                    cells.cell(clean(row.text), colspan=len(widths), style=group_face,
                               align="L")
                elif isinstance(row, Subtotal):
                    cells.cell(clean(row.label), colspan=len(widths) - 1, style=subtotal_face,
                               align="R")
                    cells.cell(clean(row.amount), style=subtotal_face, align="R")
                else:
                    for value in row:
                        cells.cell(clean(value))

    def totals(self, rows: Sequence[tuple[str, str]], width: float = 112.0,
               size: float = 9.5) -> None:
        """Right-aligned two-column totals box (never split); the last row is emphasised."""
        if not self.fits(lambda: self._totals(rows, width, size)):
            self.add_page()
        self._totals(rows, width, size)
        self.ln(3)

    def _totals(self, rows: Sequence[tuple[str, str]], width: float, size: float) -> None:
        self.set_font(FAMILY, "", size)
        strong = FontFace(emphasis="BOLD", fill_color=TOTAL_FILL)
        with self.table(
            width=width,
            align="RIGHT",
            col_widths=(width * 0.7, width * 0.3),
            text_align=("LEFT", "RIGHT"),
            first_row_as_headings=False,
            line_height=size * 0.52,
            padding=(1.0, 1.6),
        ) as table:
            for index, (label, value) in enumerate(rows):
                style = strong if index == len(rows) - 1 else None
                row = table.row()
                row.cell(clean(label), style=style)
                row.cell(clean(value), style=style)

    def signature_boxes(self, boxes: Sequence[tuple[str, Sequence[str]]],
                        height: float = 26.0) -> None:
        """Side-by-side framed boxes with a bold title and a few lines (signatures, stamps)."""
        self.keep_space(height + 4)
        gap = 6.0
        width = (WIDTH - gap * (len(boxes) - 1)) / len(boxes)
        top = self.get_y()
        for index, (title, lines) in enumerate(boxes):
            x = LEFT + index * (width + gap)
            self.set_draw_color(150, 150, 150)
            self.rect(x, top, width, height)
            self.set_xy(x + 2.5, top + 2)
            self.set_font(FAMILY, "B", 8.5)
            self.multi_cell(width - 5, 4.2, clean(title), new_x=XPos.LEFT, new_y=YPos.NEXT)
            self.set_font(FAMILY, "", 8.5)
            for line in lines:
                self.set_x(x + 2.5)
                self.multi_cell(width - 5, 4.2, clean(line), new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.set_xy(LEFT, top + height + 3)

    def render(self) -> bytes:
        return bytes(self.output())
