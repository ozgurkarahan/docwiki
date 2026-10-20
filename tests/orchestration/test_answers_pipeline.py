"""Filed research answers inside a run (ADR 0007): inbox → ``queries/`` → published release."""

from __future__ import annotations

import dataclasses
import shutil
from collections.abc import Mapping
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from engine_stubs import CANARY, build_evidence, render_source_page, stub_engine

from docwiki.answers import INBOX_PREFIX, FolderRelease, build_query_page, write_inbox
from docwiki.answers.inbox import REJECTED_PREFIX
from docwiki.contracts.catalog import Catalog
from docwiki.contracts.extracted import Block, ExtractedDoc, ExtractionInfo
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.markdown import extract_footnotes
from docwiki.contracts.pages import (
    DocwikiStamp,
    EvidenceFrontmatter,
    EvidencePage,
    Page,
    QueryFrontmatter,
    SourceFrontmatter,
)
from docwiki.orchestration.pipeline import carry_queries, settle_query_citations
from docwiki.release.publish import read_current_pointer
from docwiki.release.validate import CITATION_RE, validate_page, validate_release
from docwiki.stages.links import replace_frontmatter

MOCK_RELEASE_DIR = (
    Path(__file__).resolve().parents[2]
    / "samples"
    / "fixtures"
    / "mock-release"
    / "releases"
    / "20260401T090000Z-7ce99a3f"
)
PLAN_A, PLAN_B, MINUTES = "src-c6436ec50050", "src-86eabe3d6d0d", "src-165f1d3a109c"
MOCK_QUERY = "queries/2026-03-31-window-delivery-date.md"
STAMP = DocwikiStamp(release="20260501T090000Z-0b1c2d3e")
DAY = date(2026, 5, 1)


def _sidecars(root: Path, catalog: Catalog, status: str) -> list[str]:
    """Evidence sidecars (content paths) of the release's sources with ``status``."""
    wanted = {source.source_id for source in catalog.sources if source.status == status}
    found: list[str] = []
    for source_id in sorted(wanted):
        for file in sorted((root / "evidence" / source_id).glob("*.md")):
            if file.name != "index.md":
                found.append(f"evidence/{source_id}/{file.name}")
    return found


def _filed(root: Path, *, question: str) -> Page:
    release = FolderRelease(root)
    old = _sidecars(root, release.catalog, "superseded")[0]
    current = _sidecars(root, release.catalog, "current")[0]
    text = (
        "Revision A gave the earlier instruction [1]. The current documents say more [2].\n\n"
        f"Sources:\n[1] Revision A — part — {old}\n[2] Current — part — {current}\n"
    )
    answer = SimpleNamespace(text=text, sources=None, tool_calls=[], agent="docwiki-researcher")
    return build_query_page(
        answer, question=question, release=release, filed_on=date(2026, 2, 16)
    ).page


def _page(root: Path, path: str) -> Page:
    return Page.parse((root / "wiki" / path).read_text(encoding="utf-8"), path)


def _definitions(page: Page) -> list[str]:
    return [definition.content for definition in extract_footnotes(page.body)[1]]


def _retitled(result: Any, *args: Any, **kwargs: Any) -> Any:
    """``render_source_page`` after a recompile that words every source title differently."""
    compiled = result.compiled.model_copy(update={"title": f"{result.compiled.title}, revised"})
    return render_source_page(dataclasses.replace(result, compiled=compiled), *args, **kwargs)


def _mock_sources() -> dict[str, Page]:
    """The source pages of the mock release, by source id."""
    pages = [
        _page(MOCK_RELEASE_DIR, f"sources/{file.name}")
        for file in sorted((MOCK_RELEASE_DIR / "wiki" / "sources").glob("*.md"))
    ]
    return {
        page.frontmatter.source_id: page
        for page in pages
        if isinstance(page.frontmatter, SourceFrontmatter)
    }


def _mock_sidecars() -> dict[str, EvidencePage]:
    """The evidence sidecars of the mock release, by content path."""
    sidecars: dict[str, EvidencePage] = {}
    for file in sorted((MOCK_RELEASE_DIR / "evidence").glob("src-*/*.md")):
        if file.name != "index.md":
            path = f"evidence/{file.parent.name}/{file.name}"
            sidecars[path] = EvidencePage.parse(file.read_text(encoding="utf-8"), path)
    return sidecars


def _with_provenance(sidecar: EvidencePage, provenance: str) -> EvidencePage:
    frontmatter = sidecar.frontmatter.model_copy(update={"provenance": provenance})
    return sidecar.model_copy(update={"frontmatter": frontmatter})


def _mock_docs(
    sources: Mapping[str, Page], sidecars: Mapping[str, EvidencePage]
) -> dict[str, ExtractedDoc]:
    """Extracted documents of the mock sources: one block per sidecar, same locator and
    provenance (what a recompile of the documents would give)."""
    docs: dict[str, ExtractedDoc] = {}
    for source_id, page in sources.items():
        fm = page.frontmatter
        assert isinstance(fm, SourceFrontmatter)
        cited = [
            sidecar.frontmatter
            for sidecar in sidecars.values()
            if isinstance(sidecar.frontmatter, EvidenceFrontmatter)
            and sidecar.frontmatter.source_id == source_id
        ]
        docs[source_id] = ExtractedDoc(
            source_id=source_id,
            source_path=fm.source_path,
            source_hash=fm.source_hash,
            media_type=fm.media_type,
            lang="fr",
            blocks=[
                Block(
                    id=f"b{index:04d}",
                    kind="paragraph",
                    text=item.title,
                    locator=item.locator,
                    provenance=item.provenance,
                )
                for index, item in enumerate(cited, start=1)
            ],
            extraction=ExtractionInfo(adapter="local", adapter_version="1"),
        )
    return docs


def _hand_filed(
    release_id: str, *, slug: str, question: str, text: str, citation: str, source: str
) -> Page:
    """A filed answer as an older release could have written it (one citation)."""
    frontmatter = QueryFrontmatter(
        id=f"query:2026-02-16-{slug}",
        title=question,
        summary=text,
        sensitivity="public",
        updated=date(2026, 2, 16),
        docwiki=DocwikiStamp(release=release_id),
        question=question,
        asked_by="human",
        sources=[source],
        approved_by="owner",
    )
    body = f"# {question}\n\n{text}[^c1]\n\n## Sources\n\n[^c1]: {citation}\n"
    return Page(path=f"queries/2026-02-16-{slug}.md", frontmatter=frontmatter, body=body)


async def test_a_filed_answer_becomes_a_page_of_the_next_release(make_harness) -> None:
    harness = make_harness()
    first = await harness.run()
    assert first.status == "succeeded" and first.published, first.errors
    page = _filed(harness.current_release(), question="What did revision A say?")
    write_inbox(harness.storage, page)

    second = await harness.run()
    assert second.status == "succeeded" and second.published, second.errors
    root = harness.current_release()
    published = (root / "wiki" / page.path).read_text(encoding="utf-8")
    assert "> **Superseded:** this answer cites" in published  # it cites revision A
    assert "## How this answer was produced" in published
    assert (root / "wiki" / "queries" / "index.md").is_file()
    log = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "query | What did revision A say?" in log
    assert harness.storage.list(INBOX_PREFIX) == []
    assert validate_release(root, canaries=[CANARY]) == []

    third = await harness.run()
    assert third.status == "no-op"  # an empty inbox and unchanged sources: nothing to publish
    carried = (harness.current_release() / "wiki" / page.path).read_text(encoding="utf-8")
    assert carried.count("> **Superseded:** this answer cites") == 1


async def test_a_non_empty_inbox_is_never_a_no_op_and_bad_filings_are_rejected(
    make_harness,
) -> None:
    harness = make_harness()
    assert (await harness.run()).published
    assert (await harness.run()).status == "no-op"
    root = harness.current_release()
    harness.storage.write_bytes(f"{INBOX_PREFIX}2026-02-16-broken.md", b"not a page")
    restricted = _filed(root, question="Which tier is this?")
    restricted = Page(
        path=restricted.path,
        frontmatter=restricted.frontmatter.model_copy(update={"sensitivity": "restricted"}),
        body=restricted.body,
    )
    write_inbox(harness.storage, restricted)

    outcome = await harness.run()
    assert outcome.status == "succeeded" and outcome.published, outcome.errors
    assert harness.storage.list(INBOX_PREFIX) == []
    rejected = harness.storage.list(REJECTED_PREFIX)
    assert f"{REJECTED_PREFIX}2026-02-16-broken.md" in rejected
    assert f"{REJECTED_PREFIX}2026-02-16-which-tier-is-this.md" in rejected
    reason_key = f"{REJECTED_PREFIX}2026-02-16-which-tier-is-this.md.reason.txt"
    assert b"above the audience" in harness.storage.read_bytes(reason_key)
    assert not (harness.current_release() / "wiki" / restricted.path).exists()
    assert any("answers inbox" in warning for warning in outcome.report.warnings)


def test_a_carried_answer_is_re_cited_from_the_current_release() -> None:
    """A later recompile renames a cited source, raises the tier of another and changes the
    provenance of a third: the carried answer follows instead of failing G03 and G07."""
    query = _page(MOCK_RELEASE_DIR, MOCK_QUERY)
    assert validate_page(query, sources=_mock_sources(), evidence=_mock_sidecars()) == []
    sources = _mock_sources()
    sources[MINUTES] = replace_frontmatter(sources[MINUTES], title="Site meeting minutes n°3 (v2)")
    sources[PLAN_B] = replace_frontmatter(sources[PLAN_B], sensitivity="internal")
    sidecars = _mock_sidecars()
    scan = f"evidence/{PLAN_A}/p0001.md"
    sidecars[scan] = _with_provenance(sidecars[scan], "ocr")
    stale = {
        violation.code for violation in validate_page(query, sources=sources, evidence=sidecars)
    }
    assert stale == {"citation-title", "citation-badge", "page-tier"}

    pages, cited = carry_queries(
        [query], sources, _mock_docs(sources, sidecars), stamp=STAMP, day=DAY, audience="internal"
    )

    (page,) = pages
    assert page.frontmatter.sensitivity == "internal"
    assert page.frontmatter.sources == [MINUTES, PLAN_B, PLAN_A]
    assert _definitions(page) == [
        '[Planning and purchase tracking, indice B — sheet "Planning", rows 6–9]'
        f"(../evidence/{PLAN_B}/sheet-planning-r0006-r0009.md) · table",
        f"[Site meeting minutes n°3 (v2) — ¶ 11](../evidence/{MINUTES}/para-0011.md) · paraphrase",
        f"[Planning and purchase tracking, indice A — p. 1](../evidence/{PLAN_A}/p0001.md) · OCR",
    ]
    assert all(CITATION_RE.match(content) for content in _definitions(page))
    assert validate_page(page, sources=sources, evidence=sidecars) == []
    assert sorted(item.key for item in cited) == [
        "p0001",
        "para-0011",
        "sheet-planning-r0006-r0009",
    ]


def test_a_carried_answer_that_cannot_be_re_cited_is_left_out() -> None:
    query = _page(MOCK_RELEASE_DIR, MOCK_QUERY)
    body = query.body.replace(
        "## How this answer", "See also the purchase order.[^c4]\n\n## How this answer", 1
    )
    broken = Page(path=query.path, frontmatter=query.frontmatter, body=body)
    sources = _mock_sources()
    invalid: dict[str, str] = {}

    pages, cited = carry_queries(
        [broken],
        sources,
        _mock_docs(sources, _mock_sidecars()),
        stamp=STAMP,
        day=DAY,
        audience="public",
        invalid=invalid,
    )

    assert pages == [] and cited == []
    assert invalid == {
        query.frontmatter.id: "it fails the release checks: G02 footnote-undefined: "
        "footnote [^c4] has no definition"
    }


def test_answers_take_the_label_and_badge_of_the_sidecars_written() -> None:
    query = _page(MOCK_RELEASE_DIR, MOCK_QUERY)
    written = {path: sidecar.frontmatter for path, sidecar in _mock_sidecars().items()}
    minutes = f"evidence/{MINUTES}/para-0011.md"
    written[minutes] = written[minutes].model_copy(update={"provenance": "model-description"})

    settled = settle_query_citations(query, written.get)

    assert _definitions(settled) == [
        '[Planning and purchase tracking, indice B — sheet "Planning", rows 6–9]'
        f"(../evidence/{PLAN_B}/sheet-planning-r0006-r0009.md) · table",
        f"[Site meeting minutes n°3 — ¶ 11](../{minutes}) · generated description",
        f"[Planning and purchase tracking, indice A — p. 1](../evidence/{PLAN_A}/p0001.md) "
        "· paraphrase",
    ]
    assert settle_query_citations(settled, written.get) is settled
    assert settle_query_citations(query, lambda path: None) is query


async def test_answers_follow_a_new_source_title_and_tier(
    make_harness, pack_dir: Path, tmp_path: Path
) -> None:
    harness = make_harness()
    assert (await harness.run()).published
    carried = _filed(harness.current_release(), question="What did revision A say?")
    write_inbox(harness.storage, carried)
    assert (await harness.run()).published
    filed = _filed(harness.current_release(), question="What do the quotes say?")
    write_inbox(harness.storage, filed)  # merged by a run that sees new titles and tiers

    pack = tmp_path / "pack"
    shutil.copytree(pack_dir, pack)
    rules = (pack / "sensitivity.yaml").read_text(encoding="utf-8").rstrip("\n")
    (pack / "sensitivity.yaml").write_text(
        rules + "\n  - tier: internal\n    doc_type: quote\n", encoding="utf-8"
    )
    harness.pack = pack
    harness.engine = stub_engine(render_source_page=_retitled)
    outcome = await harness.run()

    assert outcome.status == "succeeded" and outcome.published, outcome.errors
    root = harness.current_release()
    assert validate_release(root, canaries=[CANARY]) == []
    for page in (carried, filed):
        published = _page(root, page.path)
        assert published.frontmatter.sensitivity == "internal"  # it cites revision A, a quote
        titles = [CITATION_RE.match(content)["title"] for content in _definitions(published)]
        assert len(titles) == 2 and all(title.endswith(", revised") for title in titles)
    assert harness.storage.list(INBOX_PREFIX) == []


async def test_answers_take_the_badge_of_the_sidecar_the_evidence_stage_wrote(
    make_harness,
) -> None:
    harness = make_harness()
    assert (await harness.run()).published
    pointer = read_current_pointer(harness.storage)
    assert pointer is not None
    quote_a = source_id_for("devis/DEV-2026-014 indice A.txt")
    page = _hand_filed(
        pointer[0].release_id,
        slug="first-delivery-date",
        question="When were the windows first due?",
        text="At the end of March 2026.",
        citation=f"[DEV-2026-014 indice A — line 4](../evidence/{quote_a}/l0004-l0004.md)"
        " · paraphrase",
        source=quote_a,
    )
    write_inbox(harness.storage, page)

    def scanned_line(**kwargs: Any) -> list[str]:
        cited = [
            dataclasses.replace(item, provenance="ocr") if item.key == "l0004-l0004" else item
            for item in kwargs.pop("cited")
        ]
        return build_evidence(cited=cited, **kwargs)

    harness.engine = stub_engine(build_evidence=scanned_line)
    outcome = await harness.run()

    assert outcome.status == "succeeded" and outcome.published, outcome.errors
    root = harness.current_release()
    assert validate_release(root, canaries=[CANARY]) == []
    assert _definitions(_page(root, page.path)) == [
        f"[DEV-2026-014 indice A — line 4](../evidence/{quote_a}/l0004-l0004.md) · OCR"
    ]


async def test_answers_that_fail_the_release_checks_are_left_out_without_blocking(
    make_harness,
) -> None:
    harness = make_harness()
    assert (await harness.run()).published
    carried = _filed(harness.current_release(), question="What did revision A say?")
    write_inbox(harness.storage, carried)
    second = await harness.run()
    assert second.published
    # the published copy of the answer references a citation it never defines
    stored = f"releases/{second.release_id}/wiki/{carried.path}"
    text = harness.storage.read_bytes(stored).decode("utf-8")
    text = text.replace("## How this answer", "Noted on site.[^c3]\n\n## How this answer", 1)
    harness.storage.write_bytes(stored, text.encode("utf-8"))
    # a filing whose first citation links to a source page instead of its evidence
    root = harness.current_release()
    filed = _filed(root, question="What do the quotes say?")
    href = CITATION_RE.match(_definitions(filed)[0])["href"]
    catalog = Catalog.from_json((root / "catalog.json").read_bytes())
    source_page = next(entry.path for entry in catalog.pages if entry.id == href.split("/")[2])
    body = filed.body.replace(f"({href})", f"(../{source_page})", 1)
    write_inbox(harness.storage, Page(path=filed.path, frontmatter=filed.frontmatter, body=body))

    outcome = await harness.run()

    assert outcome.status == "succeeded" and outcome.published, outcome.errors
    root = harness.current_release()
    assert validate_release(root, canaries=[CANARY]) == []
    assert not (root / "wiki" / carried.path).exists()
    assert not (root / "wiki" / filed.path).exists()
    assert harness.storage.list(INBOX_PREFIX) == []
    name = filed.path.removeprefix("queries/")
    reason = harness.storage.read_bytes(f"{REJECTED_PREFIX}{name}.reason.txt").decode("utf-8")
    assert reason.startswith("it fails the release checks: G06 citation-target")
    assert any(
        f"queries: {carried.frontmatter.id} left out of this release" in warning
        and "G02 footnote-undefined" in warning
        for warning in outcome.report.warnings
    )
    log = (root / "wiki" / "log.md").read_text(encoding="utf-8")
    assert "] withdraw | What did revision A say?" in log
    assert "Research answer removed: it no longer passes the checks of this release." in log


async def test_an_answer_filed_again_during_a_run_waits_for_the_next_run(make_harness) -> None:
    harness = make_harness()
    assert (await harness.run()).published
    first = _filed(harness.current_release(), question="What did revision A say?")
    key = write_inbox(harness.storage, first)
    body = first.body.replace("the earlier instruction", "the first instruction")
    again = Page(path=first.path, frontmatter=first.frontmatter, body=body)
    assert again.body != first.body

    def file_again_then_render(*args: Any, **kwargs: Any) -> Any:
        harness.storage.write_bytes(key, again.render().encode("utf-8"))
        return render_source_page(*args, **kwargs)

    harness.engine = stub_engine(render_source_page=file_again_then_render)
    outcome = await harness.run()

    assert outcome.status == "succeeded" and outcome.published, outcome.errors
    assert "the earlier instruction" in _page(harness.current_release(), first.path).body
    assert harness.storage.read_bytes(key) == again.render().encode("utf-8")
    assert harness.storage.list(REJECTED_PREFIX) == []
    assert any(f"{key} was filed again during this run" in w for w in outcome.report.warnings)

    harness.engine = stub_engine()
    following = await harness.run()
    assert following.status == "succeeded" and following.published, following.errors
    assert "the first instruction" in _page(harness.current_release(), first.path).body
    assert harness.storage.list(INBOX_PREFIX) == []
