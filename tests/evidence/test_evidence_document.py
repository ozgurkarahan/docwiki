"""The document page (``evidence/<source_id>/index.md``, ADR 0010 slice B): the whole document as
received, its pages, its full text with tables, then the passages the wiki cites."""

from __future__ import annotations

from evidence_helpers import TITLES, build, by_text, cite, describer
from extract_fixtures import Corpus

from docwiki.contracts import ExtractedDoc, find_violations
from docwiki.contracts.pages import EvidencePage
from docwiki.engine_types import CitedLocator
from docwiki.release.writer import ReleaseWriter


def _none(_doc: ExtractedDoc) -> list[CitedLocator]:
    return []


async def test_a_pdf_document_page_shows_its_pages_and_full_text(
    corpus: Corpus, writer: ReleaseWriter
) -> None:
    rel = "docs/devis-indice-a.pdf"

    def select(doc: ExtractedDoc) -> list[CitedLocator]:
        return cite(doc, by_text(doc, "Nettoyer"))

    built = await build(corpus, writer, rel, select, llm=describer(), publish_original=True)
    page = built.page("index")
    assert page.frontmatter.type == "evidence-index"
    assert page.frontmatter.title == TITLES[rel]
    body = page.body
    assert body.index("## Pages") < body.index("## Full text") < body.index("## Cited passages")
    assert "![Page 1 of Quote DEV-2026-014 indice A](img/page-0001.png)" in body
    assert built.asset("img/page-0001.png").startswith(b"\x89PNG")
    assert "Nettoyer la dalle avant la pose." in body
    assert "*Figure (generated description, not verified):*" in body
    assert "- [p. 1](p0001.md)" in body
    assert "Original file: [original.pdf](original.pdf)" in body
    assert not find_violations(body, allow_markers=False)


async def test_without_a_published_original_no_page_images(
    corpus: Corpus, writer: ReleaseWriter
) -> None:
    built = await build(corpus, writer, "docs/devis-indice-a.pdf", _none, llm=describer())
    body = built.page("index").body
    assert "## Pages" not in body and "## Full text" in body
    assert not any("/img/page-" in path for path in built.paths)
    assert "No passage of this document is cited." in body


async def test_a_workbook_is_shown_as_tables(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(corpus, writer, "plans/planning-chantier.xlsx", _none)
    body = built.page("index").body
    table = built.doc.tables[0]
    rows = [line for line in body.splitlines() if line.startswith("| ")]
    first = next(column for column in table.columns if column)
    assert first in rows[0]
    assert len(rows) >= len(table.rows) + 2  # header, separator and every row
    assert "table-ref" not in body


async def test_an_email_keeps_its_headers_and_body(corpus: Corpus, writer: ReleaseWriter) -> None:
    built = await build(corpus, writer, "mail/report-de-livraison.eml", _none)
    body = built.page("index").body
    for block in built.doc.blocks:
        first = block.text.strip().splitlines()[0] if block.text.strip() else ""
        if first and block.kind in ("email-header", "email-body"):
            assert first.split()[0] in body


async def test_canaries_are_never_rendered(corpus: Corpus, writer: ReleaseWriter) -> None:
    rel = "notes/consignes-de-pose.txt"
    plain = await build(corpus, writer, rel, _none)
    word = next(
        token for token in plain.page("index").body.split() if token.isalpha() and len(token) > 6
    )
    guarded = await build(corpus, writer, rel, _none, canaries=[word])
    text = guarded.text("index")
    assert word.lower() not in text.lower()
    EvidencePage.parse(text, f"evidence/{guarded.doc.source_id}/index.md")
