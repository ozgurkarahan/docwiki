"""fpdf2 helpers: stamped header/footer, headings, paragraphs, tables and vector figures."""

from __future__ import annotations

import io
from collections.abc import Sequence

from fpdf import FPDF, FontFace
from fpdf.enums import XPos, YPos

from .common import GENERATOR_AUTHOR, STAMP, DocMeta, latin1

_LEFT = 18.0
_WIDTH = 174.0


class StampedPDF(FPDF):
    """A4 document whose header and footer both carry the fictional stamp."""

    def __init__(self, meta: DocMeta, header_left: str, footer_left: str = "") -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.meta = meta
        self.header_left = latin1(header_left)
        self.footer_left = latin1(footer_left)
        self.set_margins(_LEFT, 20, _LEFT)
        self.set_auto_page_break(True, margin=22)
        self.set_title(latin1(meta.title))
        self.set_subject(STAMP)
        self.set_author(GENERATOR_AUTHOR)
        self.set_creator(GENERATOR_AUTHOR)
        self.set_producer(GENERATOR_AUTHOR)
        self.set_keywords(latin1(meta.keywords))
        self.set_creation_date(meta.created)
        self.set_lang(meta.lang)

    # -- page furniture -------------------------------------------------------------------
    def header(self) -> None:
        self.set_font("Helvetica", "", 8)
        self.set_text_color(80, 80, 80)
        self.set_xy(_LEFT, 9)
        self.cell(_WIDTH / 2, 5, self.header_left, align="L")
        self.cell(_WIDTH / 2, 5, STAMP, align="R")
        self.set_draw_color(150, 150, 150)
        self.line(_LEFT, 15, _LEFT + _WIDTH, 15)
        self.set_text_color(0, 0, 0)
        self.set_xy(_LEFT, 20)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_draw_color(150, 150, 150)
        self.line(_LEFT, self.get_y() - 1, _LEFT + _WIDTH, self.get_y() - 1)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(80, 80, 80)
        self.cell(_WIDTH * 0.32, 5, self.footer_left, align="L")
        self.cell(_WIDTH * 0.46, 5, STAMP, align="C")
        self.cell(_WIDTH * 0.22, 5, f"Page {self.page_no()} of {{nb}}", align="R")
        self.set_text_color(0, 0, 0)

    # -- content helpers ------------------------------------------------------------------
    def title_block(self, title: str, subtitle: str = "") -> None:
        self.set_font("Helvetica", "B", 15)
        self.multi_cell(0, 7, latin1(title), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if subtitle:
            self.set_font("Helvetica", "", 10)
            self.set_text_color(60, 60, 60)
            self.multi_cell(0, 5, latin1(subtitle), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(0, 0, 0)
        self.ln(3)

    def h1(self, text: str) -> None:
        if self.get_y() > 245:
            self.add_page()
        self.ln(2)
        self.set_font("Helvetica", "B", 12)
        self.multi_cell(0, 6, latin1(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def h2(self, text: str) -> None:
        if self.get_y() > 250:
            self.add_page()
        self.ln(1)
        self.set_font("Helvetica", "B", 10.5)
        self.multi_cell(0, 5.5, latin1(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(0.5)

    def para(self, text: str, size: float = 10, style: str = "") -> None:
        self.set_font("Helvetica", style, size)
        self.multi_cell(0, 5, latin1(text), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1.5)

    def bullets(self, items: Sequence[str], numbered: bool = False, size: float = 10) -> None:
        self.set_font("Helvetica", "", size)
        for index, item in enumerate(items, start=1):
            marker = f"{index}." if numbered else "-"
            self.set_x(_LEFT + 2)
            self.cell(7, 5, marker)
            self.multi_cell(_WIDTH - 9, 5, latin1(item), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.ln(0.6)
        self.ln(1)

    def note(self, label: str, text: str) -> None:
        self.set_font("Helvetica", "B", 9.5)
        self.set_fill_color(242, 242, 242)
        self.multi_cell(
            0, 5, latin1(f"{label}: {text}"), border=1, fill=True,
            new_x=XPos.LMARGIN, new_y=YPos.NEXT, padding=2,
        )
        self.ln(2)

    def grid(
        self,
        header: Sequence[str],
        rows: Sequence[Sequence[object]],
        widths: Sequence[float] | None = None,
        size: float = 8.5,
    ) -> None:
        self.set_font("Helvetica", "", size)
        heading = FontFace(emphasis="BOLD", fill_color=(225, 230, 238))
        with self._table(widths, heading) as table:
            for values in [header, *rows]:
                row = table.row()
                for value in values:
                    row.cell(latin1(str(value)))
        self.ln(2.5)

    def _table(self, widths: Sequence[float] | None, heading: FontFace):  # type: ignore[no-untyped-def]
        return self.table(
            col_widths=tuple(widths) if widths else None,
            headings_style=heading,
            line_height=4.6,
            text_align="LEFT",
            padding=1.2,
        )

    def figure(self, svg: bytes, width: float, caption: str) -> None:
        """Embed an SVG figure as vector graphics with a caption below it."""
        x = _LEFT + (_WIDTH - width) / 2
        self.image(io.BytesIO(svg), x=x, w=width)
        self.set_font("Helvetica", "I", 8.5)
        self.multi_cell(0, 4.5, latin1(caption), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)

    def signature_lines(self, entries: Sequence[tuple[str, str]]) -> None:
        self.ln(3)
        self.set_font("Helvetica", "", 9)
        col = _WIDTH / max(1, len(entries))
        y = self.get_y()
        for index, (role, name) in enumerate(entries):
            self.set_xy(_LEFT + index * col, y)
            self.multi_cell(col - 4, 4.6, latin1(f"{role}\n{name}"), new_x=XPos.RIGHT,
                            new_y=YPos.TOP)
        self.set_xy(_LEFT, y + 12)

    def render(self) -> bytes:
        return bytes(self.output())
