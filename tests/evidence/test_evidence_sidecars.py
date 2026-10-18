"""Evidence sidecars for every locator kind, validated against the release contract."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from evidence_helpers import (
    DESCRIPTION,
    TITLES,
    Built,
    build,
    by_text,
    check_page,
    cite,
    describer,
)
from extract_fixtures import Corpus

from docwiki.contracts import ExtractedDoc, find_violations, locator_key, locator_label
from docwiki.contracts.ids import check_wiki_path
from docwiki.contracts.locators import Locator, XlsxRowsLocator
from docwiki.engine_types import CitedLocator
from docwiki.evidence import build_evidence
from docwiki.release.validate import validate_release
from docwiki.release.writer import ReleaseWriter


async def test_pdf_page_sidecar_with_highlights_original_and_figure(
    corpus: Corpus, writer: ReleaseWriter
) -> None:
    rel = "docs/sop-gbx-010.pdf"

    def select(doc: ExtractedDoc) -> list[CitedLocator]:
        figure_ref = next(b for b in doc.blocks if b.kind == "figure-ref")
        return cite(doc, by_text(doc, "Use ISO VG 320"), by_text(doc, "Drain"), figure_ref)

    built = await build(corpus, writer, rel, select, llm=describer(), publish_original=True)
    page = built.page("p0001")
    check_page(page, "p0001", "native-text", TITLES[rel])
    body = page.body
    assert "](../../sources/sop-gbx-010.md)" in body
    assert "[original.pdf, p. 1](original.pdf#page=1)" in body
    assert "Provenance: ✓ quote verified (native text)" in body
    assert "![Page 1 of Gearbox oil change SOP rev A with the cited regions highlighted]" in body
    assert "## Text" in body and "> Drain the oil while it is still warm." in body
    assert "Litware turbines" in body
    assert "## Figure f01" in body and "**Generated description**" in body
    assert DESCRIPTION in body
    assert "Figures: generated description" in body
    assert built.asset("original.pdf") == corpus.path(rel).read_bytes()
    highlighted = built.asset("img/p0001.png")
    assert highlighted.startswith(b"\x89PNG")
    assert built.asset("img/p0001-f01.png").startswith(b"\x89PNG")


async def test_page_images_are_rendered_when_not_provided(
    corpus: Corpus, writer: ReleaseWriter, tmp_path: Path
) -> None:
    rel = "docs/sop-gbx-010.pdf"
    built = await build(corpus, writer, rel, lambda d: cite(d, d.blocks[2]), use_page_images=False)
    rendered = built.asset("img/p0001.png")
    other = ReleaseWriter(
        tmp_path / "other",
        created_at=writer.created_at,
        audience="public",
        versions=writer.versions,
    )
    provided = await build(corpus, other, rel, lambda d: cite(d, d.blocks[2]))
    assert rendered == provided.asset("img/p0001.png")


async def test_scanned_page_sidecar_is_ocr(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(
        corpus, writer, "docs/crane-lift-plan-scan.pdf", lambda d: cite(d, d.blocks[0])
    )
    page = built.page("p0001")
    check_page(page, "p0001", "ocr", "Crane lift plan")
    assert "Provenance: OCR (" in page.body
    assert "## OCR text" in page.body and "local extraction does not run OCR" in page.body
    assert "OCR confidence: not reported" in page.body
    assert built.asset("img/p0001.png").startswith(b"\x89PNG")


async def test_docx_paragraph_table_and_figure(corpus: Corpus, writer: ReleaseWriter) -> None:
    rel = "docs/sop-gbx-010-rev-b.docx"

    def select(doc: ExtractedDoc) -> list[CitedLocator]:
        row = next(b for b in doc.blocks if b.locator_key == "tbl-01-r0002-r0002")
        figure_ref = next(b for b in doc.blocks if b.kind == "figure-ref")
        return cite(doc, by_text(doc, "At cold sites"), row, figure_ref)

    built = await build(corpus, writer, rel, select, llm=describer())
    paragraph = built.page("para-0005")
    check_page(paragraph, "para-0005", "native-text", TITLES[rel])
    assert "> At cold sites, where the ambient temperature can fall below -20 °C" in paragraph.body

    table = built.page("tbl-01-r0002-r0002")
    check_page(table, "tbl-01-r0002-r0002", "deterministic-table", TITLES[rel])
    assert "Provenance: table (parsed deterministically)" in table.body
    assert "## Row 2\n\n| Asset | Task | Oil grade |\n| --- | --- | --- |\n" in table.body
    assert "| WTG-07 | Gearbox oil change | ISO VG 220 |" in table.body

    figure = built.page("para-0008")
    check_page(figure, "para-0008", "model-description", TITLES[rel])
    assert "Provenance: generated description (" in figure.body
    assert "![Figure f01](img/para-0008-f01.png)" in figure.body
    assert built.asset("img/para-0008-f01.png").startswith(b"\x89PNG")


async def test_xlsx_rows_with_row_headings(corpus: Corpus, writer: ReleaseWriter) -> None:
    rel = "plans/maintenance-plan-2026.xlsx"

    def select(doc: ExtractedDoc) -> list[CitedLocator]:
        rows = XlsxRowsLocator(sheet="Plan", row_start=2, row_end=5)
        single = next(b for b in doc.blocks if b.locator_key == "sheet-notes-olstand-r0002-r0002")
        return [
            CitedLocator(doc.source_id, rows, (), provenance="deterministic-table"),
            *cite(doc, single),
        ]

    built = await build(corpus, writer, rel, select)
    page = built.page("sheet-plan-r0002-r0005")
    frontmatter = check_page(page, "sheet-plan-r0002-r0005", "deterministic-table", TITLES[rel])
    assert locator_label(frontmatter.locator) == 'sheet "Plan", rows 2–5'
    assert [line for line in page.body.splitlines() if line.startswith("## ")] == [
        "## Row 2",
        "## Row 3",
        "## Row 4",
    ]
    assert "| WTG-07 | Gearbox oil change | 6 | 2026-03-01 | 25% | 12 |" in page.body
    notes = built.page("sheet-notes-olstand-r0002-r0002")
    assert locator_label(notes.frontmatter.locator) == 'sheet "Notes & Ölstand", row 2'  # type: ignore[union-attr]
    assert "| Oil level checked |" in notes.body


async def test_csv_rows(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(corpus, writer, "plans/work-orders.csv", lambda d: cite(d, *d.blocks))
    first = built.page("r0002-r0002")
    check_page(first, "r0002-r0002", "deterministic-table", "Work orders")
    assert "| WTG-07 | Gearbox oil change with flush | 6 |" in first.body
    assert "## Row 4" in built.page("r0004-r0004").body


async def test_pptx_slide_with_notes(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(
        corpus,
        writer,
        "slides/gearbox-review.pptx",
        lambda d: cite(d, *[b for b in d.blocks if b.locator_key == "slide-02"]),
    )
    page = built.page("slide-02")
    frontmatter = check_page(page, "slide-02", "native-text", "Gearbox review")
    assert frontmatter.locator.shape is None  # type: ignore[union-attr]
    assert "> *Speaker notes*\\\n> Mention the cold-site exception." in page.body
    assert "> Drain the oil\\\n> Refill with ISO VG 320" in page.body


async def test_eml_parts(corpus: Corpus, writer: ReleaseWriter) -> None:
    def select(doc: ExtractedDoc) -> list[CitedLocator]:
        return cite(doc, doc.blocks[0], by_text(doc, "WTG-07"), doc.blocks[-1])

    built = await build(corpus, writer, "mail/oil-change-schedule.eml", select)
    headers = built.page("msg-headers")
    check_page(headers, "msg-headers", "native-text", "Oil change schedule")
    assert "`planner@example.org`" in headers.body  # e-mail addresses are not clickable
    body = built.page("msg-body-l0003-l0004")
    assert locator_label(body.frontmatter.locator) == "message body, lines 3–4"  # type: ignore[union-attr]
    assert "> WTG\\-07 gearbox oil change" not in body.body
    assert "> WTG-07 gearbox oil change is planned for March.\\\n> Use ISO VG 320." in body.body
    attachment = built.page("msg-att-checklist-pdf")
    assert 'attachment "checklist.pdf"' in attachment.frontmatter.title


async def test_vtt_cue(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(corpus, writer, "meetings/standup.vtt", lambda d: cite(d, d.blocks[1]))
    page = built.page("cue-00-03-15")
    frontmatter = check_page(page, "cue-00-03-15", "native-text", "Stand-up")
    assert locator_label(frontmatter.locator) == "03:15–03:42"
    assert "> **03:15–03:42**\\\n> Switch to ISO VG 220 & log it\\\n> before winter." in page.body


async def test_text_lines(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(corpus, writer, "notes/gearbox-oil.txt", lambda d: cite(d, *d.blocks))
    check_page(built.page("l0003-l0004"), "l0003-l0004", "native-text", "Gearbox oil notes")
    assert "> \\- WTG\\-07 switches" not in built.page("l0007-l0007").body
    assert "> \\- WTG-07 switches to ISO VG 220." in built.page("l0007-l0007").body


async def test_image_region_with_ocr_and_description(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(
        corpus, writer, "photos/checklist.png", lambda d: cite(d, *d.blocks), llm=describer()
    )
    page = built.page("img-b01")
    check_page(page, "img-b01", "ocr", "Checklist photo")
    assert "![Image of Checklist photo](img/img-b01.png)" in page.body
    assert "## OCR text" in page.body and "## Figure f01" in page.body
    assert DESCRIPTION in page.body
    assert built.asset("img/img-b01-f01.png").startswith(b"\x89PNG")


async def test_index_and_release_validation(corpus: Corpus, writer: ReleaseWriter) -> None:
    selections: dict[str, Callable[[ExtractedDoc], Sequence[CitedLocator]]] = {
        "docs/sop-gbx-010.pdf": lambda d: cite(d, *d.blocks),
        "docs/crane-lift-plan-scan.pdf": lambda d: cite(d, *d.blocks),
        "docs/sop-gbx-010-rev-b.docx": lambda d: cite(d, *d.blocks),
        "plans/maintenance-plan-2026.xlsx": lambda d: cite(d, *d.blocks),
        "plans/work-orders.csv": lambda d: cite(d, *d.blocks),
        "slides/gearbox-review.pptx": lambda d: cite(d, *d.blocks),
        "mail/oil-change-schedule.eml": lambda d: cite(d, *d.blocks),
        "meetings/standup.vtt": lambda d: cite(d, *d.blocks),
        "notes/gearbox-oil.txt": lambda d: cite(d, *d.blocks),
        "photos/checklist.png": lambda d: cite(d, *d.blocks),
    }
    built: list[Built] = []
    for rel, select in selections.items():
        built.append(
            await build(corpus, writer, rel, select, llm=describer(), publish_original=True)
        )

    for item in built:
        doc = item.doc
        keys = {block.locator_key for block in doc.blocks}
        written = {p.rsplit("/", 1)[-1][:-3] for p in item.paths if p.endswith(".md")}
        assert written == keys | {"index"}
        index = item.page("index")
        assert index.frontmatter.type == "evidence-index"
        for key in keys:
            assert f"]({key}.md) · " in index.body
        for path in item.paths:
            assert check_wiki_path(path) is None, path
            if path.endswith(".md"):
                text = (item.root / path).read_text(encoding="utf-8")
                assert find_violations(text, allow_markers=False) == [], path

    violations = validate_release(writer.root, require_manifest=False, audience="public")
    evidence = [v for v in violations if (v.path or "").startswith("evidence/")]
    assert evidence == [], evidence


def test_foreign_locators_are_rejected(writer: ReleaseWriter, tmp_path: Path) -> None:
    from docwiki.contracts.extracted import ExtractionInfo
    from docwiki.contracts.locators import TextLinesLocator

    raw = tmp_path / "a.txt"
    raw.write_text("x\n", encoding="utf-8")
    locator: Locator = TextLinesLocator(line_start=1, line_end=1)
    doc = ExtractedDoc(
        source_id="src-000000000001",
        source_path="a.txt",
        source_hash="sha256:" + "0" * 64,
        media_type="text/plain",
        lang="en",
        extraction=ExtractionInfo(adapter="local", adapter_version="1.0.0"),
    )
    with pytest.raises(ValueError, match="src-000000000002"):
        build_evidence(
            doc=doc,
            raw_file=raw,
            cited=[CitedLocator("src-000000000002", locator, ())],
            source_title="A",
            source_page_path="sources/a.md",
            sensitivity="public",
            publish_original=False,
            writer=writer,
        )
    assert locator_key(locator) == "l0001-l0001"


def test_table_sidecars_are_capped(writer: ReleaseWriter, tmp_path: Path) -> None:
    from docwiki.contracts import Table, TableRow
    from docwiki.contracts.extracted import ExtractionInfo
    from docwiki.contracts.locators import CsvRowsLocator
    from docwiki.evidence import MAX_SIDECAR_ROWS

    raw = tmp_path / "big.csv"
    raw.write_text("n\n", encoding="utf-8")
    rows = [TableRow(row_id=f"r{n:04d}", cells=[str(n)]) for n in range(2, 603)]
    doc = ExtractedDoc(
        source_id="src-0000000000cc",
        source_path="big.csv",
        source_hash="sha256:" + "c" * 64,
        media_type="text/csv",
        lang="en",
        tables=[
            Table(
                id="t01",
                locator=CsvRowsLocator(row_start=1, row_end=602),
                provenance="deterministic-table",
                columns=["n"],
                rows=rows,
                artifact="tables/t01.parquet",
            )
        ],
        extraction=ExtractionInfo(adapter="local", adapter_version="1.0.0"),
    )
    locator = CsvRowsLocator(row_start=1, row_end=602)
    paths = build_evidence(
        doc=doc,
        raw_file=raw,
        cited=[CitedLocator(doc.source_id, locator, (), provenance="deterministic-table")],
        source_title="Big",
        source_page_path="sources/big.md",
        sensitivity="public",
        publish_original=False,
        writer=writer,
    )
    text = (writer.root / next(p for p in paths if p.endswith("r0001-r0602.md"))).read_text(
        encoding="utf-8"
    )
    headings = [line for line in text.splitlines() if line.startswith("## Row ")]
    assert len(headings) == MAX_SIDECAR_ROWS
    assert headings[:2] == ["## Row 1", "## Row 2"] and headings[-1] == "## Row 500"
    assert "Rows 501 and later are not shown" in text
