"""Local adapters: locators, labels, provenance, tables, figures, warnings, determinism."""

from __future__ import annotations

import io
from pathlib import Path

import pytest
from docx import Document
from extract_fixtures import CORPUS_FILES, Corpus, make_text_pdf
from openpyxl import load_workbook

from docwiki.contracts import ExtractedDoc, locator_label, source_id_for
from docwiki.contracts.locators import (
    CsvRowsLocator,
    DocxParagraphLocator,
    DocxTableLocator,
    EmlPartLocator,
    ImageRegionLocator,
    PdfPageLocator,
    PptxSlideLocator,
    TextLinesLocator,
    VttCueLocator,
    XlsxRowsLocator,
)
from docwiki.engine_types import ExtractionError, ExtractSettings

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def keys(doc: ExtractedDoc) -> list[str]:
    return [block.locator_key for block in doc.blocks]


async def test_pdf_paragraphs_headings_figures_and_page_images(corpus: Corpus) -> None:
    result = await corpus.extract("docs/sop-gbx-010.pdf")
    doc = result.doc
    assert doc.source_id == source_id_for("docs/sop-gbx-010.pdf")
    assert doc.source_hash.startswith("sha256:")
    assert doc.media_type == "application/pdf"
    assert doc.metadata.page_count == 2
    assert doc.title_hint == "Gearbox oil change SOP"
    assert str(doc.metadata.authored) == "2026-01-15"
    assert doc.extraction.adapter == "local"
    assert doc.extraction.warnings == [] == result.warnings

    texts = [block.text for block in doc.blocks]
    assert texts[0] == "Gearbox oil change"
    assert doc.blocks[0].kind == "heading" and doc.blocks[0].level == 1
    assert any("FICTIONAL - NOT FOR OPERATIONAL USE" in text for text in texts)
    assert "Drain the oil while it is still warm." in texts
    lists = [block for block in doc.blocks if block.kind == "list"]
    assert [block.text for block in lists] == [
        "1. Stop the turbine and lock the rotor.",
        "2. Open the drain valve.",
    ]
    for block in doc.blocks:
        assert isinstance(block.locator, PdfPageLocator)
        assert block.provenance == "native-text"
        assert block.locator.bbox is not None
        x0, y0, x1, y1 = block.locator.bbox
        assert 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1
    assert [b.id for b in doc.blocks] == [f"b{i:04d}" for i in range(1, len(doc.blocks) + 1)]
    assert {block.locator_key for block in doc.blocks} == {"p0001", "p0002"}
    assert locator_label(doc.blocks[0].locator) == "p. 1"

    stamp = next(b for b in doc.blocks if b.text.startswith("FICTIONAL"))
    paragraph = next(b for b in doc.blocks if b.text.startswith("Use ISO VG 320"))
    assert stamp.locator.bbox[1] < paragraph.locator.bbox[1]  # top-left origin, reading order

    assert [figure.id for figure in doc.figures] == ["f01"]
    figure = doc.figures[0]
    assert figure.image == "figures/f01.png"
    assert figure.locator == PdfPageLocator(page=1, bbox=figure.bbox)
    assert figure.bbox == pytest.approx([20 / 210, 150 / 297, 90 / 210, 193.75 / 297], abs=0.01)
    assert figure.description is None and figure.description_provenance is None
    assert result.figures["f01"].startswith(PNG_SIGNATURE)
    assert sorted(result.page_images) == [1, 2]
    assert all(png.startswith(PNG_SIGNATURE) for png in result.page_images.values())


async def test_scanned_pdf_needs_ocr(corpus: Corpus) -> None:
    result = await corpus.extract("docs/crane-lift-plan-scan.pdf")
    doc = result.doc
    assert len(doc.blocks) == 1
    block = doc.blocks[0]
    assert (block.kind, block.text, block.provenance) == ("ocr-line", "", "ocr")
    assert block.locator == PdfPageLocator(page=1)
    assert any(warning.startswith("needs-ocr:") for warning in result.warnings)
    assert doc.figures == []  # a full-page scan is not a figure
    assert 1 in result.page_images


async def test_pdf_max_pages(corpus: Corpus, tmp_path: Path) -> None:
    path = tmp_path / "long.pdf"
    make_text_pdf(path, pages=3)
    result = await corpus.extract("docs/long.pdf", ExtractSettings(max_pages=2), path=path)
    assert result.doc.metadata.page_count == 3
    assert sorted(result.page_images) == [1, 2]
    assert {block.locator.page for block in result.doc.blocks} == {1, 2}
    assert any(w.startswith("max-pages: extracted the first 2 of 3 pages") for w in result.warnings)


async def test_docx_paragraph_indices_follow_python_docx(corpus: Corpus) -> None:
    result = await corpus.extract("docs/sop-gbx-010-rev-b.docx")
    doc = result.doc
    paragraphs = Document(str(corpus.path("docs/sop-gbx-010-rev-b.docx"))).paragraphs
    text_blocks = [b for b in doc.blocks if isinstance(b.locator, DocxParagraphLocator)]
    assert [b.locator.paragraph for b in text_blocks] == [1, 2, 4, 5, 7, 9]
    for block in text_blocks:
        assert paragraphs[block.locator.paragraph - 1].text == block.text
    assert paragraphs[2].text == "" and paragraphs[5].text == ""  # empty ones keep their index
    title, scope = text_blocks[0], text_blocks[2]
    assert (title.kind, title.level) == ("heading", 1)
    assert (scope.kind, scope.level, scope.text) == ("heading", 1, "Scope")
    assert text_blocks[4].kind == "list"
    assert keys(doc)[4:6] == ["tbl-01-r0002-r0002", "tbl-01-r0003-r0003"]
    assert doc.blocks[4].text == "Asset: WTG-07; Task: Gearbox oil change; Oil grade: ISO VG 220"
    assert doc.blocks[4].provenance == "deterministic-table"
    assert locator_label(doc.blocks[4].locator) == "table 1, row 2"

    (table,) = doc.tables
    assert table.id == "t01" and table.artifact == "tables/t01.parquet"
    assert table.locator == DocxTableLocator(table=1, row_start=1, row_end=3)
    assert table.columns == ["Asset", "Task", "Oil grade"]
    assert [row.row_id for row in table.rows] == ["r0002", "r0003"]
    assert table.provenance == "deterministic-table"

    (figure,) = doc.figures
    assert figure.locator == DocxParagraphLocator(paragraph=8)
    assert paragraphs[7].text == ""  # the picture paragraph
    assert result.figures["f01"].startswith(PNG_SIGNATURE)


async def test_xlsx_values_rows_slugs_and_merges(corpus: Corpus) -> None:
    result = await corpus.extract("plans/maintenance-plan-2026.xlsx")
    doc = result.doc
    plan, notes = doc.tables
    assert plan.locator == XlsxRowsLocator(sheet="Plan", row_start=1, row_end=6)
    assert plan.columns == ["Asset", "Task", "Hours", "Due", "Share", "Double"]
    rows = {row.row_id: row.cells for row in plan.rows}
    assert list(rows) == ["r0002", "r0003", "r0004", "r0006"]  # Excel numbers, empty row 5 skipped
    assert rows["r0002"] == ["WTG-07", "Gearbox oil change", "6", "2026-03-01", "25%", "12"]
    assert rows["r0003"][2:4] == ["2.5", "2026-04-02 13:30:00"]
    assert rows["r0006"][:3] == ["Merged remark", "Merged remark", "1"]  # merged A6:B6 expanded
    assert all("=" not in cell for cells in rows.values() for cell in cells)  # values, not formulas
    assert plan.provenance == notes.provenance == "deterministic-table"
    assert notes.locator.sheet == "Notes & \u00d6lstand"
    assert {block.provenance for block in doc.blocks} == {"deterministic-table"}
    assert keys(doc) == [
        "sheet-plan-r0001-r0001",
        "sheet-plan-r0002-r0002",
        "sheet-plan-r0003-r0003",
        "sheet-plan-r0004-r0004",
        "sheet-plan-r0006-r0006",
        "sheet-notes-olstand-r0001-r0001",
        "sheet-notes-olstand-r0002-r0002",
    ]
    assert locator_label(doc.blocks[1].locator) == 'sheet "Plan", row 2'
    assert doc.blocks[0].kind == "heading" and doc.blocks[0].text == "Plan"
    # the workbook really stores a formula with a cached value
    sheet = load_workbook(corpus.path("plans/maintenance-plan-2026.xlsx"))["Plan"]
    assert sheet["F2"].value == "=C2*2"


async def test_xlsx_colliding_sheet_slugs_and_formula_without_value(tmp_path: Path) -> None:
    from openpyxl import Workbook

    from docwiki.extract import extract_source

    workbook = Workbook()
    first = workbook.active
    first.title = "Plan"
    first.append(["A", "B"])
    first.append([1, "=A2*2"])
    second = workbook.create_sheet("plan!")
    second.append(["A"])
    second.append(["x"])
    third = workbook.create_sheet("Plan{2026}")
    third.append(["A"])
    third.append(["y"])
    path = tmp_path / "book.xlsx"
    workbook.save(path)
    result = await extract_source(path, rel_path="book.xlsx", settings=ExtractSettings())
    locators = [table.locator for table in result.doc.tables]
    # slugs come from slugify_ascii(raw sheet name); labels drop Markdown-significant characters
    assert [loc.sheet for loc in locators] == ["Plan", "plan!", "Plan2026"]
    assert [loc.sheet_slug for loc in locators] == [None, "plan-2", "plan-2026"]
    assert [b.locator_key for b in result.doc.blocks if b.kind == "table-ref"] == [
        "sheet-plan-r0002-r0002",
        "sheet-plan-2-r0002-r0002",
        "sheet-plan-2026-r0002-r0002",
    ]
    assert any(w.startswith('xlsx-formula-no-value: sheet "Plan": 1') for w in result.warnings)
    assert result.doc.tables[0].rows[0].cells == ["1", ""]


def test_extractor_versions() -> None:
    from docwiki.extract import ADAPTER_VERSION, CU_API_VERSION, extractor_versions

    versions = extractor_versions()
    assert versions["local"] == ADAPTER_VERSION
    assert versions["content-understanding"].endswith(CU_API_VERSION)
    assert {"pypdfium2", "python-docx", "openpyxl", "python-pptx", "pillow"} <= set(versions)


async def test_csv_bom_dialect_and_record_numbers(corpus: Corpus) -> None:
    doc = (await corpus.extract("plans/work-orders.csv")).doc
    (table,) = doc.tables
    assert table.columns == ["Asset", "Task", "Hours"]  # BOM stripped, ';' sniffed
    assert table.locator == CsvRowsLocator(row_start=1, row_end=4)
    assert [(row.row_id, row.cells) for row in table.rows] == [
        ("r0002", ["WTG-07", "Gearbox oil change\nwith flush", "6"]),
        ("r0004", ["WTG-12", "Vibration check", "2"]),
    ]
    assert keys(doc) == ["r0002-r0002", "r0004-r0004"]
    assert locator_label(doc.blocks[1].locator) == "row 4"
    assert doc.blocks[0].text == "Asset: WTG-07; Task: Gearbox oil change with flush; Hours: 6"


async def test_pptx_slides_notes_tables_pictures(corpus: Corpus) -> None:
    result = await corpus.extract("slides/gearbox-review.pptx")
    doc = result.doc
    assert doc.metadata.page_count == 3
    assert doc.title_hint == "Gearbox maintenance review"
    assert all(isinstance(block.locator, PptxSlideLocator) for block in doc.blocks)
    assert keys(doc) == ["slide-01"] * 2 + ["slide-02"] * 3 + ["slide-03"] * 3
    kinds = [(block.kind, block.text) for block in doc.blocks]
    assert kinds[2:5] == [
        ("heading", "Oil change steps"),
        ("slide", "Drain the oil\nRefill with ISO VG 320"),
        ("note", "Mention the cold-site exception."),
    ]
    assert doc.blocks[4].locator == PptxSlideLocator(slide=2, shape="notes")
    assert kinds[6] == ("table-ref", "Asset: WTG-07; Due: 2026-03")
    (table,) = doc.tables
    assert table.provenance == "native-text"
    assert [row.row_id for row in table.rows] == ["r0002", "r0003"]
    (figure,) = doc.figures
    assert isinstance(figure.locator, PptxSlideLocator) and figure.locator.slide == 3
    assert locator_label(figure.locator) == "slide 3"


async def test_eml_headers_body_lines_and_attachments(corpus: Corpus) -> None:
    doc = (await corpus.extract("mail/oil-change-schedule.eml")).doc
    assert doc.title_hint == "Gearbox oil change schedule"
    assert str(doc.metadata.authored) == "2026-01-12"
    header = doc.blocks[0]
    assert header.kind == "email-header"
    assert header.locator == EmlPartLocator(part="headers")
    assert header.text.splitlines()[0] == "From: Maintenance planner <planner@example.org>"
    assert "Subject: Gearbox oil change schedule" in header.text
    body = [b for b in doc.blocks if b.kind == "email-body"]
    assert [(b.locator.line_start, b.locator.line_end) for b in body] == [(1, 1), (3, 4), (6, 7)]
    assert body[1].text == "WTG-07 gearbox oil change is planned for March.\nUse ISO VG 320."
    assert locator_label(body[1].locator) == "message body, lines 3–4"
    attachment = doc.blocks[-1]
    assert attachment.locator == EmlPartLocator(part="attachment:checklist.pdf")
    assert attachment.locator_key == "msg-att-checklist-pdf"
    assert attachment.text.startswith("Attachment: checklist.pdf (application/pdf")
    assert "alert" not in doc.text()


async def test_eml_html_only_body_is_converted_safely(corpus: Corpus) -> None:
    result = await corpus.extract("mail/html-only.eml")
    body = [b.text for b in result.doc.blocks if b.kind == "email-body"]
    assert body == ["Hello team,", "WTG-07 gearbox oil change is planned for March."]
    assert "alert" not in result.doc.text() and "color" not in result.doc.text()
    assert any(w.startswith("eml-html-body") for w in result.warnings)


async def test_vtt_cues(corpus: Corpus) -> None:
    doc = (await corpus.extract("meetings/standup.vtt")).doc
    first, second = doc.blocks
    assert first.locator == VttCueLocator(cue_start="00:00:01", cue_end="00:00:04")
    assert first.text == "Technician: Gearbox oil level checked on WTG-07."
    assert second.locator == VttCueLocator(cue_start="00:03:15", cue_end="00:03:42")
    assert second.text == "Switch to ISO VG 220 & log it\nbefore winter."
    assert (first.locator_key, second.locator_key) == ("cue-00-00-01", "cue-00-03-15")
    assert locator_label(second.locator) == "03:15–03:42"
    assert {b.kind for b in doc.blocks} == {"cue"}


@pytest.mark.parametrize(
    ("rel", "first_kind"),
    [("notes/gearbox-oil.md", "heading"), ("notes/gearbox-oil.txt", "paragraph")],
)
async def test_text_line_ranges(corpus: Corpus, rel: str, first_kind: str) -> None:
    doc = (await corpus.extract(rel)).doc
    assert [b.locator for b in doc.blocks] == [
        TextLinesLocator(line_start=1, line_end=1),
        TextLinesLocator(line_start=3, line_end=4),
        TextLinesLocator(line_start=7, line_end=7),
    ]
    assert doc.blocks[0].kind == first_kind
    assert doc.blocks[1].text == "Use ISO VG 320 for all turbines.\nRecord the level."
    assert doc.blocks[2].kind == "list"
    assert locator_label(doc.blocks[1].locator) == "lines 3–4"


async def test_image_figure_and_ocr_placeholder(corpus: Corpus) -> None:
    result = await corpus.extract("photos/checklist.png")
    doc = result.doc
    region = ImageRegionLocator(region=1, bbox=[0.0, 0.0, 1.0, 1.0])
    (block,) = doc.blocks
    assert (block.kind, block.text, block.provenance, block.locator) == (
        "ocr-line",
        "",
        "ocr",
        region,
    )
    assert block.locator_key == "img-b01"
    (figure,) = doc.figures
    assert figure.locator == region
    assert result.page_images[1].startswith(PNG_SIGNATURE)
    assert any(w.startswith("needs-ocr") for w in result.warnings)


async def test_unsupported_and_damaged_files_raise(tmp_path: Path) -> None:
    from docwiki.extract import extract_source

    legacy = tmp_path / "old.doc"
    legacy.write_bytes(b"\xd0\xcf\x11\xe0")
    with pytest.raises(ExtractionError) as unsupported:
        await extract_source(legacy, rel_path="old.doc", settings=ExtractSettings())
    assert unsupported.value.source_id == source_id_for("old.doc")
    assert "unsupported file type .doc" in unsupported.value.reason

    broken = tmp_path / "broken.pdf"
    broken.write_bytes(b"this is not a PDF")
    with pytest.raises(ExtractionError, match="not a readable PDF"):
        await extract_source(broken, rel_path="broken.pdf", settings=ExtractSettings())

    not_zip = tmp_path / "broken.docx"
    not_zip.write_bytes(b"plain text")
    with pytest.raises(ExtractionError, match="docx could not be parsed"):
        await extract_source(not_zip, rel_path="broken.docx", settings=ExtractSettings())

    with pytest.raises(ExtractionError, match="cannot read the file"):
        await extract_source(
            tmp_path / "missing.txt", rel_path="missing.txt", settings=ExtractSettings()
        )


async def test_invalid_settings_raise_value_error(corpus: Corpus) -> None:
    with pytest.raises(ValueError, match="max_pages"):
        await corpus.extract("notes/gearbox-oil.txt", ExtractSettings(max_pages=0))
    with pytest.raises(ValueError, match="cu_endpoint"):
        await corpus.extract("docs/sop-gbx-010.pdf", ExtractSettings(mode="azure"))


@pytest.mark.parametrize("rel", CORPUS_FILES)
async def test_extraction_is_deterministic(corpus: Corpus, rel: str) -> None:
    first = await corpus.extract(rel)
    second = await corpus.extract(rel)
    assert first.doc.to_json() == second.doc.to_json()
    assert first.figures == second.figures
    assert first.page_images == second.page_images
    assert ExtractedDoc.from_json(first.doc.to_json()) == first.doc


def test_docx_fixture_is_a_real_docx(corpus: Corpus) -> None:
    data = corpus.path("docs/sop-gbx-010-rev-b.docx").read_bytes()
    assert len(Document(io.BytesIO(data)).tables) == 1
