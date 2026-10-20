"""End to end with the compile lane: refs resolved by ``DocIndex``, footnotes and cited locators
from ``Footnotes``, sidecars from ``build_evidence``, checked by ``validate_release``.

This is the contract between the two lanes: every footnote must point to an existing sidecar
(G06) whose label and provenance make the footnote badge honest (G03).
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from evidence_helpers import TITLES, describer
from extract_fixtures import Corpus

from docwiki.contracts import Page, slugify_ascii
from docwiki.contracts.pages import ExtractionSummary, SourceFrontmatter
from docwiki.evidence import build_evidence
from docwiki.release.validate import validate_release
from docwiki.release.writer import ReleaseWriter
from docwiki.stages.render import Footnotes
from docwiki.stages.verify_citations import DocIndex

CASES: dict[str, list[str]] = {
    "docs/devis-indice-a.pdf": ["b0003", "b0003,b0004", "f01", "b0007"],
    "docs/bon-de-livraison-scan.pdf": ["b0001"],
    "docs/avenant-n1.docx": ["b0004", "t01:r0003", "t01:r0002,t01:r0003", "f01"],
    "plans/planning-chantier.xlsx": [
        "t01:r0003",
        "t01:r0002,t01:r0004",
        "t01:r0006",
        "t01",
        "t02:r0002",
        "b0001",
    ],
    "plans/commandes.csv": ["t01:r0004", "t01:r0002"],
    "slides/support-reunion-chantier.pptx": ["b0005", "t01:r0002", "f01"],
    "mail/report-de-livraison.eml": ["b0001", "b0003", "b0005"],
    "meetings/reunion-de-chantier.vtt": ["b0002"],
    "notes/consignes-de-pose.txt": ["b0002"],
    "photos/photo-palettes.png": ["f01", "b0001"],
}


@pytest.mark.parametrize("rel", sorted(CASES))
async def test_compile_citations_resolve_to_honest_sidecars(
    corpus: Corpus, writer: ReleaseWriter, rel: str
) -> None:
    result = await corpus.extract(rel, llm=describer())
    doc = result.doc
    title = TITLES[rel]
    page_path = f"sources/{slugify_ascii(Path(doc.source_path).stem)}.md"
    footnotes = Footnotes(page_path, {doc.source_id: title})
    index = DocIndex(doc)
    facts = []
    for ref in CASES[rel]:
        cited = index.resolve(ref)
        marker = footnotes.ref(
            doc.source_id,
            cited.locator,
            cited.provenance,
            "verified",
            block_ids=cited.block_ids,
        )
        facts.append(f"- Fact citing {ref}.{marker}")
    body = "\n".join(
        [f"# {title}", "", "## Key facts", "", *facts, "", *footnotes.sources_section(), ""]
    )
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
    writer.write_page(Page(path=page_path, frontmatter=frontmatter, body=body))
    build_evidence(
        doc=doc,
        raw_file=corpus.path(rel),
        cited=footnotes.cited_locators(),
        source_title=title,
        source_page_path=page_path,
        sensitivity="public",
        publish_original=True,
        writer=writer,
        page_images=result.page_images,
    )

    violations = validate_release(writer.root, require_manifest=False, audience="public")
    relevant = [
        v
        for v in violations
        if v.gate in ("G01", "G02", "G03", "G05", "G06", "G07", "G09")
        and ((v.path or "").startswith("evidence/") or v.path == f"wiki/{page_path}")
    ]
    assert relevant == [], relevant

    # negative control: the validator does check these footnotes against the sidecars
    first = footnotes.cited_locators()[0]
    (writer.root / f"evidence/{doc.source_id}/{first.key}.md").unlink()
    violations = validate_release(writer.root, require_manifest=False, audience="public")
    assert any(v.gate == "G06" and v.path == f"wiki/{page_path}" for v in violations), violations
