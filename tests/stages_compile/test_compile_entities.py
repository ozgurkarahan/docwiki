"""Entity pages: deterministic aggregation, timeline, documents and the cited summary."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from compile_testkit import (
    PLAN,
    SOP_A,
    SOP_B,
    STAMP,
    Corpus,
    build_corpus,
    fact_id,
)

from docwiki.contracts import Page, find_violations
from docwiki.contracts.markdown import extract_footnotes, extract_headings
from docwiki.contracts.pages import EntityFrontmatter
from docwiki.domain import DomainPack
from docwiki.llm import (
    FakeLlmClient,
    LlmContentFiltered,
    LlmOutputTruncated,
    LlmRequest,
    LlmTimeout,
)
from docwiki.release.validate import CITATION_RE
from docwiki.stages.entities import MAX_OUTPUT_TOKENS, build_entity_pages, fact_date


@pytest.fixture
async def corpus(pack: DomainPack) -> Corpus:
    return await build_corpus(pack, include_contract=False)


def summary_handler(request: LlmRequest) -> dict:
    text = request.text
    if "- id: asset:wtg-07" not in text:
        return {"sentences": []}
    first = fact_id(text, "first turbine to switch")
    interval = fact_id(text, "interval of WTG-07")
    return {
        "sentences": [
            {"text": "WTG-07 is the first turbine to switch to ISO VG 220.", "fact_ids": [first]},
            {"text": "Its oil change interval is 99 months.", "fact_ids": [interval]},
            {"text": "It is the best turbine.", "fact_ids": ["F99"]},
            {"text": "Its oil change interval is 12 months.", "fact_ids": [interval.lower()]},
        ]
    }


async def build(corpus: Corpus, pack: DomainPack) -> tuple[dict[str, Page], list, FakeLlmClient]:
    llm = FakeLlmClient({"entity_summary": summary_handler})
    pages, cited = await build_entity_pages(
        list(corpus.results.values()), corpus.pages, pack, llm, stamp=STAMP
    )
    return {page.frontmatter.id: page for page in pages}, cited, llm


async def test_pages_for_mentioned_registry_entities(corpus: Corpus, pack: DomainPack) -> None:
    pages, cited, llm = await build(corpus, pack)
    assert sorted(pages) == [
        "asset:wtg-07",
        "asset:wtg-12",
        "organisation:litware",
        "procedure:sop-gbx-010",
    ]
    assert "organisation:trey-research" not in pages
    called = sorted(str(r.metadata["entity_id"]) for r in llm.requests)
    assert called == ["asset:wtg-07", "asset:wtg-12"], "no summary call without facts"
    assert all(r.tier == "fast" and r.prompt_version == "entity-summary-v1" for r in llm.requests)
    for page in pages.values():
        assert find_violations(page.body) == []
        assert Page.parse(page.render(), page.path) == page
    assert cited


async def test_wtg07_page(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, _ = await build(corpus, pack)
    page = pages["asset:wtg-07"]
    fm = page.frontmatter
    assert isinstance(fm, EntityFrontmatter)
    assert page.path == "entities/asset/wtg-07.md"
    assert (fm.entity_type, fm.key, fm.title, fm.sensitivity) == (
        "asset",
        "wtg-07",
        "WTG-07",
        "internal",
    )
    assert fm.sources == sorted([SOP_B, SOP_A, PLAN])
    assert [(a.text, a.lang) for a in fm.aliases] == [("turbine 7", "en"), ("éolienne 7", "fr")]
    assert fm.summary == (
        "WTG-07 is the first turbine to switch to ISO VG 220. Its oil change interval is 12 months."
    )
    headings = [h.text for h in extract_headings(page.body)]
    assert headings == ["WTG-07", "Facts", "Timeline", "Documents", "Sources"]
    body = page.body
    intro = body.split("\n\n")[2]
    assert intro.startswith("WTG-07 is the first turbine to switch to ISO VG 220.[^c1]")
    assert "99 months" not in body and "best turbine" not in body
    facts = body.split("## Facts\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert facts == [
        "- WTG-07 is the first turbine to switch to ISO VG 220.[^c1]",
        "- The oil change interval of WTG-07 is 12 months.[^c2]",
        "- WTG-07 has a gearbox oil change planned for 2026-03 with ISO VG 320 oil (6 hours).[^c3]",
        "- Superseded: Revision A specifies ISO VG 320 gearbox oil for all turbines, including "
        "WTG-07.[^c4]",
    ]
    timeline = body.split("## Timeline\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert timeline == [
        "- 2026-03: WTG-07 has a gearbox oil change planned for 2026-03 with ISO VG 320 oil "
        "(6 hours).[^c3]"
    ]
    documents = body.split("## Documents\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert documents == [
        "- [Gearbox oil change SOP rev B](../../sources/sop-gbx-010-rev-b.md)",
        "- [Maintenance plan 2026](../../sources/maintenance-plan-2026.md)",
        "- [Gearbox oil change SOP rev A](../../sources/sop-gbx-010-rev-a.md) (superseded)",
    ]
    _, defs = extract_footnotes(body)
    targets = [CITATION_RE.match(d.content).group("href") for d in defs]  # type: ignore[union-attr]
    assert all(target.startswith("../../evidence/src-") for target in targets)
    titles = {CITATION_RE.match(d.content).group("title") for d in defs}  # type: ignore[union-attr]
    assert titles == {
        "Gearbox oil change SOP rev B",
        "Maintenance plan 2026",
        "Gearbox oil change SOP rev A",
    }
    assert defs[2].content.endswith(" · table")


async def test_entity_without_facts(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, _ = await build(corpus, pack)
    page = pages["organisation:litware"]
    assert "No verified facts name this entity yet." in page.body
    assert "No dated facts." in page.body
    assert page.frontmatter.summary == (
        "Litware is an entity of type organisation in the domain registry, mentioned in 1 "
        "source document."
    )
    assert "No evidence is cited on this page." in page.body


async def test_results_without_source_pages_are_ignored(corpus: Corpus, pack: DomainPack) -> None:
    llm = FakeLlmClient({"entity_summary": {"sentences": []}})
    pages, _ = await build_entity_pages(
        list(corpus.results.values()), {SOP_B: corpus.pages[SOP_B]}, pack, llm, stamp=STAMP
    )
    wtg07 = next(page for page in pages if page.frontmatter.id == "asset:wtg-07")
    assert wtg07.frontmatter.sources == [SOP_B]  # type: ignore[union-attr]


def _truncated(request: LlmRequest) -> dict:
    raise LlmOutputTruncated("hit max_output_tokens", raw_output='{"sentences": [')


def _filtered(request: LlmRequest) -> dict:
    raise LlmContentFiltered("The model refused to answer", reason="refusal")


def _invalid(request: LlmRequest) -> dict:
    return {"sentences": "not a list"}


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (_truncated, "LlmOutputTruncated"),
        (_filtered, "LlmContentFiltered (refusal)"),
        (_invalid, "LlmInvalidOutput"),
    ],
)
async def test_failed_summary_keeps_the_deterministic_introduction(
    corpus: Corpus,
    pack: DomainPack,
    caplog: pytest.LogCaptureFixture,
    failure: Callable[[LlmRequest], dict],
    error: str,
) -> None:
    def handler(request: LlmRequest) -> dict:
        if "- id: asset:wtg-07" in request.text:
            return failure(request)
        return summary_handler(request)

    llm = FakeLlmClient({"entity_summary": handler})
    with caplog.at_level(logging.WARNING, logger="docwiki.stages.entities"):
        pages, cited = await build_entity_pages(
            list(corpus.results.values()), corpus.pages, pack, llm, stamp=STAMP
        )
    by_id = {page.frontmatter.id: page for page in pages}
    assert sorted(by_id) == [
        "asset:wtg-07",
        "asset:wtg-12",
        "organisation:litware",
        "procedure:sop-gbx-010",
    ]
    page = by_id["asset:wtg-07"]
    intro = (
        "WTG-07 is an entity of type asset in the domain registry, mentioned in 3 source documents."
    )
    assert page.frontmatter.summary == intro
    assert page.body.split("\n\n")[2] == intro
    facts = page.body.split("## Facts\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert len(facts) == 4 and all("[^c" in line for line in facts)
    assert find_violations(page.body) == []
    assert cited
    warnings = [r.getMessage() for r in caplog.records if r.name == "docwiki.stages.entities"]
    assert warnings == [
        f"entity asset:wtg-07: summary call failed ({error}); the page keeps the deterministic "
        "introduction"
    ]


async def test_systemic_summary_failures_propagate(corpus: Corpus, pack: DomainPack) -> None:
    def handler(request: LlmRequest) -> dict:
        raise LlmTimeout("timed out after the retries")

    with pytest.raises(LlmTimeout):
        await build_entity_pages(
            list(corpus.results.values()),
            corpus.pages,
            pack,
            FakeLlmClient({"entity_summary": handler}),
            stamp=STAMP,
        )


async def test_summary_budget_leaves_room_for_reasoning(corpus: Corpus, pack: DomainPack) -> None:
    _, _, llm = await build(corpus, pack)
    assert llm.requests
    assert {request.max_output_tokens for request in llm.requests} == {MAX_OUTPUT_TOKENS}
    assert MAX_OUTPUT_TOKENS >= 2_000, "reasoning models spend output tokens before answering"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Planned for 2026-03 with 6 hours.", "2026-03"),
        ("Done on 2026-02-01, then 2026-03.", "2026-02-01"),
        ("Inspected on 12 March 2026.", "2026-03-12"),
        ("Due March 5, 2026 at the latest.", "2026-03-05"),
        ("Planned for Sept 2026.", "2026-09"),
        ("Valid since 2026 only.", None),
        ("Invalid 2026-13 month.", None),
        ("SOP-GBX-010 revision B.", None),
    ],
)
def test_fact_dates(text: str, expected: str | None) -> None:
    assert fact_date(text) == expected
