"""Helpers shared by the evidence tests (fixture extraction, source pages, sidecar access)."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import date
from pathlib import Path

from extract_fixtures import Corpus

from docwiki.contracts import Block, ExtractedDoc, Page, locator_label
from docwiki.contracts.ids import slugify_ascii
from docwiki.contracts.pages import (
    EvidenceFrontmatter,
    EvidencePage,
    ExtractionSummary,
    SourceFrontmatter,
)
from docwiki.engine_types import CitedLocator, ExtractResult
from docwiki.evidence import build_evidence
from docwiki.extract import FIGURE_SCHEMA_NAME
from docwiki.llm import FakeLlmClient
from docwiki.release.writer import ReleaseWriter

DESCRIPTION = "Blue rectangle crossed by a white diagonal line."
TITLES = {
    "docs/devis-indice-a.pdf": "Quote DEV-2026-014 indice A",
    "docs/bon-de-livraison-scan.pdf": "Delivery note scan",
    "docs/avenant-n1.docx": "Amendment n°1",
    "plans/planning-chantier.xlsx": "Site schedule",
    "plans/commandes.csv": "Purchase orders",
    "slides/support-reunion-chantier.pptx": "Site meeting slides",
    "mail/report-de-livraison.eml": "Delivery postponement",
    "meetings/reunion-de-chantier.vtt": "Site meeting",
    "notes/consignes-de-pose.txt": "Installation notes",
    "photos/photo-palettes.png": "Pallets photo",
}


def cite(doc: ExtractedDoc, *blocks: Block) -> list[CitedLocator]:
    """Block citations as the compile lane emits them (block ids, block provenance)."""
    return [
        CitedLocator(doc.source_id, block.locator, (block.id,), provenance=block.provenance)
        for block in blocks
    ]


def source_page(doc: ExtractedDoc, writer: ReleaseWriter, title: str) -> str:
    path = f"sources/{slugify_ascii(Path(doc.source_path).stem)}.md"
    frontmatter = SourceFrontmatter(
        id=doc.source_id,
        title=title,
        summary=f"Fixture {title}.",
        sensitivity="public",
        updated=date(2026, 4, 1),
        docwiki=writer.stamp,
        source_id=doc.source_id,
        source_path=doc.source_path,
        source_hash=doc.source_hash,
        media_type=doc.media_type,
        doc_type="quote",
        category="contract-documents",
        status="current",
        original_lang=doc.lang,
        authority=5,
        extraction=ExtractionSummary(
            adapter=doc.extraction.adapter, version=doc.extraction.adapter_version
        ),
    )
    writer.write_page(Page(path=path, frontmatter=frontmatter, body=f"# {title}\n"))
    return path


class Built:
    def __init__(self, root: Path, doc: ExtractedDoc, paths: list[str]) -> None:
        self.root = root
        self.doc = doc
        self.paths = paths

    def page(self, key: str) -> EvidencePage:
        rel = f"evidence/{self.doc.source_id}/{key}.md"
        assert rel in self.paths, f"{rel} not written: {self.paths}"
        return EvidencePage.parse((self.root / rel).read_text(encoding="utf-8"), rel)

    def text(self, key: str) -> str:
        return (self.root / f"evidence/{self.doc.source_id}/{key}.md").read_text(encoding="utf-8")

    def asset(self, name: str) -> bytes:
        rel = f"evidence/{self.doc.source_id}/{name}"
        assert rel in self.paths, f"{rel} not written: {self.paths}"
        return (self.root / rel).read_bytes()


async def build(
    corpus: Corpus,
    writer: ReleaseWriter,
    rel: str,
    select: Callable[[ExtractedDoc], Sequence[CitedLocator]],
    *,
    llm: FakeLlmClient | None = None,
    publish_original: bool = False,
    use_page_images: bool = True,
    canaries: Sequence[str] = (),
    path: Path | None = None,
    title: str | None = None,
) -> Built:
    result: ExtractResult = await corpus.extract(rel, llm=llm, path=path)
    doc = result.doc
    page_title = title or TITLES[rel]
    page_path = source_page(doc, writer, page_title)
    paths = build_evidence(
        doc=doc,
        raw_file=path or corpus.path(rel),
        cited=select(doc),
        source_title=page_title,
        source_page_path=page_path,
        sensitivity="public",
        publish_original=publish_original,
        writer=writer,
        page_images=result.page_images if use_page_images else None,
        canaries=canaries,
    )
    return Built(writer.root, doc, paths)


def describer() -> FakeLlmClient:
    return FakeLlmClient({FIGURE_SCHEMA_NAME: {"description": DESCRIPTION}})


def by_text(doc: ExtractedDoc, prefix: str) -> Block:
    return next(block for block in doc.blocks if block.text.startswith(prefix))


def check_page(page: EvidencePage, key: str, provenance: str, title: str) -> EvidenceFrontmatter:
    frontmatter = page.frontmatter
    assert isinstance(frontmatter, EvidenceFrontmatter)
    assert frontmatter.locator_key == key
    assert frontmatter.id.endswith(f":{key}")
    assert frontmatter.provenance == provenance
    assert frontmatter.sensitivity == "public"
    label = locator_label(frontmatter.locator)
    assert frontmatter.title == f"{title} — {label}"
    assert page.body.startswith(f"# {title} — ")
    return frontmatter
