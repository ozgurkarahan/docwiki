"""The compile lane's pages pass the release validator's page gates (G01–G12).

Evidence sidecars belong to the extract lane; minimal sidecars are written here for every
returned ``CitedLocator`` so that footnote targets, labels, titles and badges are checked
against real sidecar frontmatter.
"""

from __future__ import annotations

from pathlib import Path

from compile_testkit import FIXED_NOW, build_corpus
from test_compile_entities import summary_handler
from test_compile_topics import synthesis_handler

from docwiki.contracts.locators import locator_label
from docwiki.contracts.pages import EvidenceFrontmatter, EvidencePage
from docwiki.contracts.runs import VersionInfo
from docwiki.domain import DomainPack
from docwiki.engine_types import CitedLocator
from docwiki.llm import FakeLlmClient
from docwiki.release import ReleaseWriter, validate_release
from docwiki.stages.entities import build_entity_pages
from docwiki.stages.render import link_source_refs
from docwiki.stages.topics import build_topic_pages

PROVENANCE_PRIORITY = ("native-text", "ocr", "deterministic-table", "model-description")
PAGE_GATES = {"G01", "G02", "G03", "G05", "G06", "G07", "G09", "G11", "G12"}


def write_sidecars(
    writer: ReleaseWriter, cited: list[CitedLocator], titles: dict[str, str]
) -> None:
    by_key: dict[tuple[str, str], list[CitedLocator]] = {}
    for item in cited:
        by_key.setdefault((item.source_id, item.key), []).append(item)
    for (source_id, key), items in sorted(by_key.items()):
        provenance = min((item.provenance for item in items), key=PROVENANCE_PRIORITY.index)
        locator = items[0].locator
        frontmatter = EvidenceFrontmatter(
            id=f"evidence:{source_id}:{key}",
            title=f"{titles[source_id]} — {locator_label(locator)}",
            source_id=source_id,
            locator=locator,
            provenance=provenance,
            sensitivity="internal",
        )
        body = f"# {locator_label(locator)}\n\nEvidence placeholder for the compile-lane test.\n"
        writer.write_evidence(
            EvidencePage(path=f"evidence/{source_id}/{key}.md", frontmatter=frontmatter, body=body)
        )


async def test_pages_pass_the_release_page_gates(tmp_path: Path, pack: DomainPack) -> None:
    writer = ReleaseWriter(
        tmp_path / "release",
        created_at=FIXED_NOW,
        audience="internal",
        versions=VersionInfo(
            docwiki="0.1.0", domain_pack=pack.name, domain_pack_hash=pack.content_hash()
        ),
    )
    stamp = writer.stamp
    corpus = await build_corpus(pack, include_study=False, stamp=stamp)
    results = list(corpus.results.values())
    entity_pages, entity_cited = await build_entity_pages(
        results,
        corpus.pages,
        pack,
        FakeLlmClient({"entity_summary": summary_handler}),
        stamp=stamp,
    )
    topic_pages, topic_cited, _ = await build_topic_pages(
        results,
        corpus.pages,
        corpus.states,
        corpus.classifications,
        pack,
        FakeLlmClient({"topic_synthesis": synthesis_handler}),
        audience="internal",
        stamp=stamp,
    )
    source_pages = [link_source_refs(page, corpus.pages) for page in corpus.pages.values()]
    pages = [*source_pages, *entity_pages, *topic_pages]
    for page in pages:
        writer.write_page(page)
    cited = [item for items in corpus.cited.values() for item in items]
    cited += [*entity_cited, *topic_cited]
    titles = {page.frontmatter.id: page.frontmatter.title for page in source_pages}
    write_sidecars(writer, cited, titles)

    violations = validate_release(writer.root, require_manifest=False, audience="internal")
    paths = {f"wiki/{page.path}" for page in pages}
    relevant = [
        violation
        for violation in violations
        if violation.gate in PAGE_GATES
        and (violation.path in paths or (violation.path or "").startswith("evidence/"))
    ]
    assert relevant == []
    assert len(pages) == 3 + 4 + 2
