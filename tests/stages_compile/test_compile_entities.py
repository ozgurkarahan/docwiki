"""Entity pages: deterministic aggregation, timeline, documents and the cited summary."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from compile_testkit import (
    PLAN,
    QUOTE_A,
    QUOTE_B,
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
    return await build_corpus(pack, include_study=False)


def summary_handler(request: LlmRequest) -> dict:
    text = request.text
    if "- id: building-element:baie-f1" not in text:
        return {"sentences": []}
    first = fact_id(text, "is installed first")
    wide = fact_id(text, "is widened to")
    return {
        "sentences": [
            {"text": "The bay window F1 is installed first.", "fact_ids": [first]},
            {"text": "Its width is 99,00 m.", "fact_ids": [wide]},
            {"text": "It is the best window.", "fact_ids": ["F99"]},
            {"text": "Its width is 3,00 m.", "fact_ids": [wide.lower()]},
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
        "building-element:baie-f1",
        "building-element:fenetre-f2",
        "commercial-document:dev-2026-014",
        "organisation:vanarsdel-menuiseries",
    ]
    assert "organisation:zava-materiaux" not in pages
    called = sorted(str(r.metadata["entity_id"]) for r in llm.requests)
    assert called == [
        "building-element:baie-f1",
        "building-element:fenetre-f2",
    ], "no summary call without facts"
    assert all(r.tier == "fast" and r.prompt_version == "entity-summary-v2" for r in llm.requests)
    for page in pages.values():
        assert find_violations(page.body) == []
        assert Page.parse(page.render(), page.path) == page
    assert cited


async def test_bay_window_page(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, _ = await build(corpus, pack)
    page = pages["building-element:baie-f1"]
    fm = page.frontmatter
    assert isinstance(fm, EntityFrontmatter)
    assert page.path == "entities/building-element/baie-f1.md"
    assert (fm.entity_type, fm.key, fm.title, fm.sensitivity) == (
        "building-element",
        "baie-f1",
        "Baie coulissante F1",
        "internal",
    )
    assert fm.sources == sorted([QUOTE_B, QUOTE_A, PLAN])
    assert [(a.text, a.lang) for a in fm.aliases] == [("bay window F1", "en"), ("baie F1", "fr")]
    assert fm.summary == "The bay window F1 is installed first. Its width is 3,00 m."
    headings = [h.text for h in extract_headings(page.body)]
    assert headings == ["Baie coulissante F1", "Facts", "Timeline", "Documents", "Sources"]
    body = page.body
    intro = body.split("\n\n")[2]
    assert intro.startswith("The bay window F1 is installed first.[^c1]")
    assert "99,00 m" not in body and "best window" not in body
    facts = body.split("## Facts\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert facts == [
        "- The bay window F1 is installed first.[^c1]",
        "- The bay window F1 is widened to 3,00 m.[^c1]",
        "- The bay window F1 costs 4140,00 € HT.[^c2]",
        "- The bay window F1 is ordered at 2,40 m for delivery on 2026-03-30.[^c3]",
        "- Superseded: Indice A specifies a width of 2,40 m for all bays, including the bay "
        "window F1.[^c4]",
    ]
    timeline = body.split("## Timeline\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert timeline == [
        "- 2026-03-30: The bay window F1 is ordered at 2,40 m for delivery on 2026-03-30.[^c3]"
    ]
    documents = body.split("## Documents\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert documents == [
        "- [Quote DEV-2026-014 indice B](../../sources/dev-2026-014-indice-b.md)",
        "- [Schedule and purchase tracking](../../sources/planning-et-suivi-des-achats.md)",
        "- [Quote DEV-2026-014 indice A](../../sources/dev-2026-014-indice-a.md) (superseded)",
    ]
    _, defs = extract_footnotes(body)
    targets = [CITATION_RE.match(d.content).group("href") for d in defs]  # type: ignore[union-attr]
    assert all(target.startswith("../../evidence/src-") for target in targets)
    titles = {CITATION_RE.match(d.content).group("title") for d in defs}  # type: ignore[union-attr]
    assert titles == {
        "Quote DEV-2026-014 indice B",
        "Schedule and purchase tracking",
        "Quote DEV-2026-014 indice A",
    }
    assert defs[2].content.endswith(" · table")


async def test_entity_without_facts(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, _ = await build(corpus, pack)
    page = pages["organisation:vanarsdel-menuiseries"]
    assert "No verified facts name this entity yet." in page.body
    assert "No dated facts." in page.body
    assert page.frontmatter.summary == (
        "VanArsdel Menuiseries is an entity of type organisation in the domain registry, "
        "mentioned in 1 source document."
    )
    assert "No evidence is cited on this page." in page.body


async def test_results_without_source_pages_are_ignored(corpus: Corpus, pack: DomainPack) -> None:
    llm = FakeLlmClient({"entity_summary": {"sentences": []}})
    pages, _ = await build_entity_pages(
        list(corpus.results.values()), {QUOTE_B: corpus.pages[QUOTE_B]}, pack, llm, stamp=STAMP
    )
    bay_window = next(page for page in pages if page.frontmatter.id == "building-element:baie-f1")
    assert bay_window.frontmatter.sources == [QUOTE_B]  # type: ignore[union-attr]


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
        if "- id: building-element:baie-f1" in request.text:
            return failure(request)
        return summary_handler(request)

    llm = FakeLlmClient({"entity_summary": handler})
    with caplog.at_level(logging.WARNING, logger="docwiki.stages.entities"):
        pages, cited = await build_entity_pages(
            list(corpus.results.values()), corpus.pages, pack, llm, stamp=STAMP
        )
    by_id = {page.frontmatter.id: page for page in pages}
    assert sorted(by_id) == [
        "building-element:baie-f1",
        "building-element:fenetre-f2",
        "commercial-document:dev-2026-014",
        "organisation:vanarsdel-menuiseries",
    ]
    page = by_id["building-element:baie-f1"]
    intro = (
        "Baie coulissante F1 is an entity of type building element in the domain registry, "
        "mentioned in 3 source documents."
    )
    assert page.frontmatter.summary == intro
    assert page.body.split("\n\n")[2] == intro
    facts = page.body.split("## Facts\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert len(facts) == 5 and all("[^c" in line for line in facts)
    assert find_violations(page.body) == []
    assert cited
    warnings = [r.getMessage() for r in caplog.records if r.name == "docwiki.stages.entities"]
    assert warnings == [
        f"entity building-element:baie-f1: summary call failed ({error}); the page keeps the "
        "deterministic introduction"
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
        ("Delivery planned for 2026-03 with 6 weeks of lead time.", "2026-03"),
        ("Ordered on 2026-02-01, then 2026-03.", "2026-02-01"),
        ("Delivered on 12 March 2026.", "2026-03-12"),
        ("Due March 5, 2026 at the latest.", "2026-03-05"),
        ("Planned for Sept 2026.", "2026-09"),
        ("Valid since 2026 only.", None),
        ("Invalid 2026-13 month.", None),
        ("DEV-2026-014 indice B.", None),
    ],
)
def test_fact_dates(text: str, expected: str | None) -> None:
    assert fact_date(text) == expected
