"""Small synthetic documents for the extraction and evidence tests (generated at test time).

All content is fictional. Procedure-like fixtures carry the stamp required by AGENTS.md.
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

STAMP = "FICTIONAL - NOT FOR OPERATIONAL USE"
MM_PER_INCH = 25.4
A4_MM = (210.0, 297.0)


def png_image(
    width: int = 160, height: int = 100, color: tuple[int, int, int] = (30, 120, 200)
) -> Image.Image:
    image = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, width - 8, height - 8), fill=color)
    draw.line((8, height - 8, width - 8, 8), fill=(250, 250, 250), width=4)
    return image


def png_bytes(width: int = 160, height: int = 100) -> bytes:
    buffer = io.BytesIO()
    png_image(width, height).save(buffer, format="PNG")
    return buffer.getvalue()


@dataclass
class PdfItem:
    """A paragraph written into a fixture PDF, with its fpdf2 box in millimetres."""

    page: int
    text: str
    box_mm: tuple[float, float, float, float]
    role: str | None = None


@dataclass
class PdfLayout:
    items: list[PdfItem] = field(default_factory=list)
    figures: list[tuple[int, tuple[float, float, float, float]]] = field(default_factory=list)
    pages: int = 0


def _new_pdf() -> Any:
    from fpdf import FPDF

    pdf = FPDF(format="A4")
    pdf.set_creation_date(datetime(2026, 1, 15, tzinfo=UTC))
    pdf.set_author("DocWiki sample generator")
    pdf.set_margins(20, 20, 20)
    pdf.set_auto_page_break(False)
    return pdf


def _write(
    pdf: Any,
    layout: PdfLayout,
    text: str,
    *,
    size: float,
    style: str = "",
    height: float = 6.0,
    role: str | None = None,
) -> None:
    from fpdf.enums import XPos, YPos

    pdf.set_font("helvetica", style, size)
    top = pdf.get_y()
    pdf.multi_cell(0, height, text, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    bottom = pdf.get_y()
    right = 20 + min(pdf.get_string_width(text), A4_MM[0] - 40)
    layout.items.append(PdfItem(pdf.page_no(), text, (20.0, top, right, bottom), role))


def make_text_pdf(path: Path, *, pages: int = 2) -> PdfLayout:
    """A text PDF: title, stamp, paragraphs, a numbered list and a figure on page 1."""
    pdf = _new_pdf()
    pdf.set_title("Devis DEV-2026-014 indice A")
    layout = PdfLayout()
    pdf.add_page()
    _write(pdf, layout, "Devis de l'extension", size=20, style="B", height=12, role="title")
    _write(pdf, layout, STAMP, size=9)
    pdf.ln(4)
    _write(
        pdf,
        layout,
        "Toutes les baies de l'extension mesurent 2,40 x 2,15 m. Vérifier la cote après chaque "
        "pose et noter la valeur dans le compte rendu de chantier.",
        size=11,
    )
    pdf.ln(4)
    _write(pdf, layout, "Nettoyer la dalle avant la pose.", size=11)
    pdf.ln(4)
    _write(pdf, layout, "1. Fermer l'ouverture provisoire.", size=11)
    _write(pdf, layout, "2. Contrôler la livraison.", size=11)
    pdf.image(png_image(), x=20, y=150, w=70)
    layout.figures.append((1, (20.0, 150.0, 90.0, 150.0 + 70.0 * 100 / 160)))
    for number in range(2, pages + 1):
        pdf.add_page()
        _write(
            pdf, layout, f"Section {number}", size=16, style="B", height=10, role="sectionHeading"
        )
        _write(
            pdf,
            layout,
            f"La baie F1 est posée en premier, sauf gel sous -5 \u00b0C (page {number}).",
            size=11,
        )
    layout.pages = pages
    path.write_bytes(bytes(pdf.output()))
    return layout


def make_scanned_pdf(path: Path) -> None:
    """An image-only PDF page (no text layer)."""
    pdf = _new_pdf()
    pdf.add_page()
    scan = Image.new("RGB", (620, 877), (245, 245, 240))
    draw = ImageDraw.Draw(scan)
    for row in range(12):
        draw.rectangle((60, 80 + row * 50, 560, 95 + row * 50), fill=(90, 90, 90))
    pdf.image(scan, x=0, y=0, w=A4_MM[0], h=A4_MM[1])
    path.write_bytes(bytes(pdf.output()))


def make_docx(path: Path) -> None:
    """Paragraph indices (python-docx ``Document.paragraphs``, empty ones included):

    1 Title · 2 stamp · 3 empty · 4 Heading 1 "Objet" · 5 text · 6 empty · (table 1) ·
    7 list item · 8 picture · 9 closing text.
    """
    from docx import Document
    from docx.shared import Inches

    document = Document()
    document.core_properties.title = "Avenant n°1 au contrat de travaux"
    document.core_properties.author = "DocWiki sample generator"
    document.add_paragraph("Avenant n°1", style="Title")
    document.add_paragraph(STAMP)
    document.add_paragraph("")
    document.add_heading("Objet", level=1)
    document.add_paragraph(
        "En cas de gel, lorsque la température peut descendre sous -5 \u00b0C, la pose de la "
        "fenêtre de toit est reportée."
    )
    document.add_paragraph("")
    table = document.add_table(rows=3, cols=3)
    for row, values in enumerate(
        (
            ("Repère", "Désignation", "Montant HT"),
            ("FT1", "Fenêtre de toit", "1160,00 €"),
            ("F1", "Baie coulissante", "4140,00 €"),
        )
    ):
        for column, value in enumerate(values):
            table.cell(row, column).text = value
    document.add_paragraph("Nettoyer la dalle avant la pose.", style="List Number")
    document.add_picture(io.BytesIO(png_bytes(200, 120)), width=Inches(2))
    document.add_paragraph("Fin de l'avenant.")
    document.save(path)


def _set_cached_value(path: Path, member: str, cell: str, value: str) -> None:
    """Give an openpyxl formula cell the cached value Excel would have stored."""
    with zipfile.ZipFile(path) as archive:
        entries = [(info, archive.read(info.filename)) for info in archive.infolist()]
    pattern = re.compile(rf'(<c r="{cell}"[^>]*>\s*<f>[^<]*</f>\s*)<v\s*(?:/>|></v>)')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as archive:
        for info, data in entries:
            if info.filename == member:
                text, count = pattern.subn(rf"\g<1><v>{value}</v>", data.decode("utf-8"))
                assert count == 1, "formula cell not found"
                data = text.encode("utf-8")
            archive.writestr(info, data)


def make_xlsx(path: Path) -> None:
    """Sheets "Planning" (rows 1-6, row 5 empty, merged A6:B6, F2 = 12) and "Notes & Réserves"."""
    from openpyxl import Workbook

    workbook = Workbook()
    planning = workbook.active
    planning.title = "Planning"
    planning.append(["Tâche", "Désignation", "Durée", "Début", "Avancement", "Double"])
    planning.append(["T05", "Élévation des murs", 6, date(2026, 3, 17), 0.2])
    planning["E2"].number_format = "0%"
    planning["F2"] = "=C2*2"
    planning.append(["T07", "Livraison des menuiseries", 2.5, datetime(2026, 3, 30, 13, 30)])
    planning.append(["T08", "Pose des menuiseries", 6, date(2026, 3, 31)])
    planning["A6"] = "Remarque fusionnée"
    planning.merge_cells("A6:B6")
    planning["C6"] = 1
    notes = workbook.create_sheet("Notes & R\u00e9serves")
    notes.append(["Note"])
    notes.append(["Réserves levées"])
    workbook.save(path)
    _set_cached_value(path, "xl/worksheets/sheet1.xml", "F2", "12")


def make_csv(path: Path) -> None:
    """UTF-8 BOM, semicolons, a quoted field with a line break, a blank record (row 3)."""
    text = (
        "Commande;Désignation;Montant HT\r\n"
        'BC-2026-009;"Baie coulissante F1\navec quincaillerie";3320,00\r\n'
        "\r\n"
        "BC-2026-010;Fenêtre F2 PVC;1020,00\r\n"
    )
    path.write_bytes(b"\xef\xbb\xbf" + text.encode("utf-8"))


def make_pptx(path: Path) -> None:
    """Slide 1 title; slide 2 bullets + notes; slide 3 table + picture."""
    from pptx import Presentation
    from pptx.util import Inches

    presentation = Presentation()
    presentation.core_properties.author = "DocWiki sample generator"
    presentation.core_properties.last_modified_by = "DocWiki sample generator"
    first = presentation.slides.add_slide(presentation.slide_layouts[0])
    first.shapes.title.text = "Réunion de chantier n°3"
    first.placeholders[1].text = "Avancement des travaux"
    second = presentation.slides.add_slide(presentation.slide_layouts[1])
    second.shapes.title.text = "Décisions"
    frame = second.placeholders[1].text_frame
    frame.text = "Fermer les ouvertures"
    frame.add_paragraph().text = "Avancer la cuisine"
    second.notes_slide.notes_text_frame.text = "Rappeler le report de livraison des menuiseries."
    third = presentation.slides.add_slide(presentation.slide_layouts[5])
    third.shapes.title.text = "Planning"
    table = third.shapes.add_table(3, 2, Inches(1), Inches(2), Inches(5), Inches(1.5)).table
    for row, values in enumerate((("Tâche", "Date"), ("T07", "2026-04-20"), ("T08", "2026-04-21"))):
        for column, value in enumerate(values):
            table.cell(row, column).text = value
    third.shapes.add_picture(io.BytesIO(png_bytes(120, 80)), Inches(7), Inches(2), Inches(1.5))
    presentation.save(path)


def make_eml(path: Path, *, html_only: bool = False) -> None:
    """Body lines: 1 greeting · 2 blank · 3-4 delay · 5 blank · 6-7 closing."""
    message = EmailMessage()
    message["From"] = "Erwan Gouzelin <erwan.gouzelin@vanarsdel-menuiseries.example>"
    message["To"] = "ines.roux@lamna-batiment.example"
    message["Subject"] = "Report de livraison des menuiseries"
    message["Date"] = "Wed, 18 Mar 2026 09:30:00 +0100"
    html = (
        "<html><head><style>p {color: red}</style><script>alert(1)</script></head><body>"
        "<p>Bonjour,</p><p>La livraison de la commande BC-2026-009 est reportée au "
        "20/04/2026.</p></body></html>"
    )
    if html_only:
        message.set_content(html, subtype="html")
    else:
        message.set_content(
            "Bonjour,\n\nLa livraison de la commande BC-2026-009 est reportée au lundi "
            "20 avril 2026.\nPénurie de profilés aluminium.\n\nCordialement,\nErwan Gouzelin\n"
        )
        message.add_alternative(html, subtype="html")
        message.add_attachment(
            b"%PDF-1.4 fictional",
            maintype="application",
            subtype="pdf",
            filename="bon-de-commande.pdf",
        )
    path.write_bytes(message.as_bytes())


def make_vtt(path: Path) -> None:
    path.write_text(
        "WEBVTT\n\nNOTE fictional transcript\n\n1\n00:00:01.500 --> 00:00:04.250\n"
        "<v Chef d'équipe>Livraison des palettes contrôlée sur le chantier.\n\n"
        "00:03:15.000 --> 00:03:42.900 align:start\nFermer les ouvertures &amp; noter la date\n"
        "avant le 07/04.\n",
        encoding="utf-8",
        newline="\n",
    )


def make_text(path: Path, *, markdown: bool) -> None:
    heading = "# Consignes de pose\n" if markdown else "Consignes de pose\n"
    path.write_text(
        f"{heading}\nLa baie F1 mesure 3,00 x 2,15 m.\nNoter la mesure.\n\n\n"
        "- BC-2026-009 est livrée le 20/04/2026.\n",
        encoding="utf-8",
        newline="\n",
    )


def make_png(path: Path) -> None:
    png_image(320, 200, (200, 60, 40)).save(path, format="PNG")


@dataclass
class Corpus:
    """Every fixture file, keyed by its relative path (``rel``) under ``root``."""

    root: Path
    pdf_layout: PdfLayout

    def path(self, rel: str) -> Path:
        return self.root / rel

    async def extract(
        self, rel: str, settings: Any = None, *, llm: Any = None, path: Path | None = None
    ) -> Any:
        """``extract_source`` on a fixture (default local settings)."""
        from docwiki.engine_types import ExtractSettings
        from docwiki.extract import extract_source

        return await extract_source(
            path or self.path(rel),
            rel_path=rel,
            settings=settings or ExtractSettings(),
            llm=llm,
        )


CORPUS_FILES = (
    "docs/devis-indice-a.pdf",
    "docs/bon-de-livraison-scan.pdf",
    "docs/avenant-n1.docx",
    "plans/planning-chantier.xlsx",
    "plans/commandes.csv",
    "slides/support-reunion-chantier.pptx",
    "mail/report-de-livraison.eml",
    "mail/html-only.eml",
    "meetings/reunion-de-chantier.vtt",
    "notes/consignes-de-pose.md",
    "notes/consignes-de-pose.txt",
    "photos/photo-palettes.png",
)


def build_corpus(root: Path) -> Corpus:
    for rel in CORPUS_FILES:
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
    layout = make_text_pdf(root / "docs/devis-indice-a.pdf")
    make_scanned_pdf(root / "docs/bon-de-livraison-scan.pdf")
    make_docx(root / "docs/avenant-n1.docx")
    make_xlsx(root / "plans/planning-chantier.xlsx")
    make_csv(root / "plans/commandes.csv")
    make_pptx(root / "slides/support-reunion-chantier.pptx")
    make_eml(root / "mail/report-de-livraison.eml")
    make_eml(root / "mail/html-only.eml", html_only=True)
    make_vtt(root / "meetings/reunion-de-chantier.vtt")
    make_text(root / "notes/consignes-de-pose.md", markdown=True)
    make_text(root / "notes/consignes-de-pose.txt", markdown=False)
    make_png(root / "photos/photo-palettes.png")
    return Corpus(root, layout)


# --- fake Content Understanding results ------------------------------------------------------


def _inches(box_mm: tuple[float, float, float, float]) -> list[float]:
    x0, y0, x1, y1 = (value / MM_PER_INCH for value in box_mm)
    return [round(v, 4) for v in (x0, y0, x1, y0, x1, y1, x0, y1)]


def source(page: int, polygon: list[float]) -> str:
    return f"D({page}," + ",".join(f"{value:g}" for value in polygon) + ")"


def fake_cu_response(
    layout: PdfLayout,
    *,
    tables: list[dict[str, Any]] | None = None,
    figures: list[dict[str, Any]] | None = None,
    extra_paragraphs: list[dict[str, Any]] | None = None,
    words: bool = False,
    mime_type: str = "application/pdf",
) -> dict[str, Any]:
    """A Content Understanding 2025-11-01 result for a fixture PDF (shape as on Microsoft Learn)."""
    width, height = (value / MM_PER_INCH for value in A4_MM)
    markdown = ""
    paragraphs: list[dict[str, Any]] = []
    page_spans: dict[int, list[int]] = {}
    page_words: dict[int, list[dict[str, Any]]] = {}
    for item in layout.items:
        prefix = "# " if item.role == "title" else "## " if item.role == "sectionHeading" else ""
        if item.page > 1 and item.page not in page_spans:
            markdown += "<!-- PageBreak -->\n\n"
        start = len(markdown)
        markdown += prefix + item.text
        offset = start + len(prefix)
        paragraph: dict[str, Any] = {
            "content": item.text,
            "source": source(item.page, _inches(item.box_mm)),
            "span": {"offset": offset, "length": len(item.text)},
        }
        if item.role:
            paragraph["role"] = item.role
        paragraphs.append(paragraph)
        bounds = page_spans.setdefault(item.page, [start, len(markdown)])
        bounds[1] = len(markdown)
        markdown += "\n\n"
        if words:
            position = offset
            for word in item.text.split(" "):
                page_words.setdefault(item.page, []).append(
                    {
                        "content": word,
                        "span": {"offset": position, "length": len(word)},
                        "confidence": 0.9,
                    }
                )
                position += len(word) + 1
    paragraphs += extra_paragraphs or []
    pages = []
    for number in range(1, layout.pages + 1):
        start, end = page_spans.get(number, [len(markdown), len(markdown)])
        page: dict[str, Any] = {
            "pageNumber": number,
            "width": round(width, 4),
            "height": round(height, 4),
            "spans": [{"offset": start, "length": end - start}],
        }
        if words:
            page["words"] = page_words.get(number, [])
        pages.append(page)
    return {
        "status": "Succeeded",
        "result": {
            "analyzerId": "prebuilt-layout",
            "apiVersion": "2025-11-01",
            "createdAt": "2026-01-15T10:00:00Z",
            "warnings": [],
            "contents": [
                {
                    "kind": "document",
                    "mimeType": mime_type,
                    "markdown": markdown,
                    "startPageNumber": 1,
                    "endPageNumber": layout.pages,
                    "unit": "inch",
                    "pages": pages,
                    "paragraphs": paragraphs,
                    "tables": tables or [],
                    "figures": figures or [],
                }
            ],
        },
    }
