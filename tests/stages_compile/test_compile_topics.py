"""Topic pages: routing thresholds, audience filtering, contradictions and supersession."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from compile_testkit import (
    CONTRACT,
    PLAN,
    SOP_A,
    SOP_B,
    STAMP,
    Corpus,
    build_corpus,
    fact_id,
    source_label,
)

from docwiki.contracts import Page, find_violations
from docwiki.contracts.markdown import extract_footnotes, extract_headings
from docwiki.contracts.pages import TopicFrontmatter
from docwiki.domain import DomainPack
from docwiki.domain.models import TopicsFile
from docwiki.engine_types import TopicSkip
from docwiki.llm import (
    FakeLlmClient,
    LlmContentFiltered,
    LlmOutputTruncated,
    LlmRequest,
    LlmServiceError,
)
from docwiki.release.validate import CITATION_RE
from docwiki.stages.models import SourceInfo
from docwiki.stages.topics import build_topic_pages, resolution_statement, route_sources


@pytest.fixture
async def corpus(pack: DomainPack) -> Corpus:
    return await build_corpus(pack)


def synthesis_handler(request: LlmRequest) -> dict:
    text = request.text
    if "- slug: cold-weather" in text:
        cold = fact_id(text, "At cold sites below")
        return {
            "summary": "How cold sites change gearbox oil requirements.",
            "overview": [{"text": "Cold sites below -20 °C use ISO VG 220.", "fact_ids": [cold]}],
            "sections": [],
            "contradictions": [],
            "superseded": [],
        }
    cold = fact_id(text, "At cold sites below")
    first = fact_id(text, "first turbine to switch")
    plan = fact_id(text, "planned for 2026-03")
    old = fact_id(text, "Revision A specifies")
    rev_b = source_label(text, "Gearbox oil change SOP rev B")
    return {
        "summary": "Gearbox oil grades, the cold-site change and an open plan contradiction.",
        "overview": [
            {"text": "Cold sites below -20 °C use ISO VG 220 gearbox oil.", "fact_ids": [cold]},
            {"text": "All turbines use ISO VG 320.", "fact_ids": [old]},
            {"text": "WTG-07 switches first.", "fact_ids": [first, old, "F99"]},
        ],
        "sections": [
            {
                "heading": "Oil grade by site",
                "claims": [
                    {"text": "WTG-07 is planned for ISO VG 320 in 2026-03.", "fact_ids": [plan]},
                    {"text": "The plug takes 45 Nm.", "fact_ids": [cold]},
                ],
            },
            {"heading": "Overview", "claims": [{"text": "Repeated.", "fact_ids": [first]}]},
            {"heading": "Empty", "claims": [{"text": "Nothing.", "fact_ids": ["F404"]}]},
        ],
        "contradictions": [
            {"subject": "Oil grade for WTG-07", "fact_ids_a": [plan], "fact_ids_b": [first]},
            {"subject": "Same source", "fact_ids_a": [cold], "fact_ids_b": [first]},
        ],
        "superseded": [
            {
                "subject": "Oil grade for all turbines",
                "old_fact_ids": [old],
                "replacement_fact_ids": [cold],
                "superseding_source": rev_b,
            },
            {
                "subject": "Invalid",
                "old_fact_ids": [cold],
                "replacement_fact_ids": [],
                "superseding_source": None,
            },
        ],
    }


async def build(
    corpus: Corpus, pack: DomainPack, audience: str = "internal", results: list | None = None
) -> tuple[dict[str, Page], list, list[TopicSkip], FakeLlmClient]:
    llm = FakeLlmClient({"topic_synthesis": synthesis_handler})
    pages, cited, skips = await build_topic_pages(
        results if results is not None else list(corpus.results.values()),
        corpus.pages,
        corpus.states,
        corpus.classifications,
        pack,
        llm,
        audience=audience,  # type: ignore[arg-type]
        stamp=STAMP,
    )
    return {page.frontmatter.id: page for page in pages}, cited, skips, llm


async def test_routing_thresholds(corpus: Corpus, pack: DomainPack) -> None:
    feeding = route_sources(list(corpus.results.values()), pack)
    assert set(feeding["gearbox-oil"]) == {SOP_B, SOP_A, PLAN, CONTRACT}
    assert feeding["cold-weather"] == [SOP_B]
    assert "blade-inspection" not in feeding
    strict = pack.model_copy(
        update={
            "topics": TopicsFile(
                topics=[
                    topic.model_copy(update={"min_score": 50.0}) for topic in pack.topics.topics
                ]
            )
        }
    )
    assert route_sources(list(corpus.results.values()), strict) == {}


async def test_topic_pages_and_skips(corpus: Corpus, pack: DomainPack) -> None:
    pages, cited, skips, llm = await build(corpus, pack)
    assert sorted(pages) == ["topic:cold-weather", "topic:gearbox-oil"]
    assert skips == [TopicSkip("blade-inspection", "insufficient_evidence", ())]
    assert all(r.tier == "smart" and r.prompt_version == "topic-synthesis-v1" for r in llm.requests)
    request = next(r for r in llm.requests if "- slug: gearbox-oil" in r.text)
    assert "Rate card" not in request.text and "supplied at cost" not in request.text, (
        "sources above the audience never reach the synthesis"
    )
    assert "Contradictions are resolved by authority, then recency" in request.text
    for page in pages.values():
        assert find_violations(page.body) == []
        assert Page.parse(page.render(), page.path) == page
    assert cited
    cold = pages["topic:cold-weather"].frontmatter
    assert isinstance(cold, TopicFrontmatter)
    assert (cold.sources, cold.confidence, cold.contradictions) == ([SOP_B], "low", 0)


async def test_gearbox_oil_page(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, _, _ = await build(corpus, pack)
    page = pages["topic:gearbox-oil"]
    fm = page.frontmatter
    assert isinstance(fm, TopicFrontmatter)
    assert page.path == "topics/gearbox-oil.md"
    assert fm.sources == sorted([SOP_B, SOP_A, PLAN])
    assert (fm.sensitivity, fm.contradictions, fm.superseded_claims, fm.confidence) == (
        "internal",
        1,
        1,
        "medium",
    )
    assert fm.summary == "Gearbox oil grades, the cold-site change and an open plan contradiction."
    headings = [h.text for h in extract_headings(page.body)]
    assert headings == [
        "Gearbox oil",
        "Overview",
        "Oil grade by site",
        "Overview (topic section)",
        "Contradictions",
        "Superseded information",
        "Sources consulted",
        "Sources",
    ]
    body = page.body
    overview = body.split("## Overview\n\n", 1)[1].split("\n\n", 1)[0]
    assert overview == (
        "Cold sites below -20 °C use ISO VG 220 gearbox oil.[^c1] WTG-07 switches first.[^c1]"
    ), "claims citing only superseded or unknown facts are dropped"
    assert "The plug takes 45 Nm." not in body, "quantities missing from the cited facts"
    contradiction = body.split("## Contradictions\n\n", 1)[1].split("\n\n", 1)[0]
    assert contradiction.startswith(
        "- **Oil grade for WTG-07.** [Maintenance plan 2026](../sources/maintenance-plan-2026.md)"
        " states: WTG-07 has a gearbox oil change planned for 2026-03 with ISO VG 320 oil "
        "(6 hours).[^c2] (authority 5, dated 2026-01-10). [Gearbox oil change SOP rev B]"
        "(../sources/sop-gbx-010-rev-b.md) states: WTG-07 is the first turbine to switch to ISO "
        "VG 220.[^c1] (authority 7, dated 2026-01-15)."
    )
    assert contradiction.endswith(
        "Resolution rule (authority, then recency): Gearbox oil change SOP rev B prevails "
        "(authority 7 vs 5)."
    )
    assert "Resolution policy: Higher authority wins" in body
    assert "Same source" not in body
    superseded = body.split("## Superseded information\n\n", 1)[1].split("\n\n", 1)[0]
    assert superseded == (
        "- **Oil grade for all turbines.** [Gearbox oil change SOP rev A]"
        "(../sources/sop-gbx-010-rev-a.md) stated: Revision A specifies ISO VG 320 gearbox oil "
        "for all turbines, including WTG-07.[^c3] Replacement: At cold sites below -20 °C, ISO VG "
        "220 gearbox oil is used.[^c1] Superseding source: [Gearbox oil change SOP rev B]"
        "(../sources/sop-gbx-010-rev-b.md)."
    )
    consulted = body.split("## Sources consulted\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert consulted == [
        "- [Gearbox oil change SOP rev B](../sources/sop-gbx-010-rev-b.md): current, "
        "authority 7, dated 2026-01-15",
        "- [Maintenance plan 2026](../sources/maintenance-plan-2026.md): current, authority 5, "
        "dated 2026-01-10",
        "- [Gearbox oil change SOP rev A](../sources/sop-gbx-010-rev-a.md): superseded, "
        "authority 7, dated 2025-03-01",
    ]
    _, defs = extract_footnotes(body)
    assert [d.label for d in defs] == ["c1", "c2", "c3"]
    assert [CITATION_RE.match(d.content).group("badge") for d in defs] == [  # type: ignore[union-attr]
        "✓ quote verified",
        "table",
        "✓ quote verified",
    ]


async def test_superseded_footnotes_follow_reading_order(corpus: Corpus, pack: DomainPack) -> None:
    # The old statement is printed before its replacement, so it must be cited first: footnote
    # labels are c1..cN in order of first use (gate G03; the first Azure run failed on it).
    def handler(request: LlmRequest) -> dict:
        text = request.text
        if "- slug: gearbox-oil" not in text:
            return synthesis_handler(request)
        return {
            "summary": "Superseded gearbox oil grade.",
            "overview": [
                {
                    "text": "WTG-07 has an oil change planned.",
                    "fact_ids": [fact_id(text, "planned for 2026-03")],
                }
            ],
            "sections": [],
            "contradictions": [],
            "superseded": [
                {
                    "subject": "Oil grade for all turbines",
                    "old_fact_ids": [fact_id(text, "Revision A specifies")],
                    "replacement_fact_ids": [fact_id(text, "At cold sites below")],
                    "superseding_source": source_label(text, "Gearbox oil change SOP rev B"),
                }
            ],
        }

    pages, _, _ = await build_topic_pages(
        list(corpus.results.values()),
        corpus.pages,
        corpus.states,
        corpus.classifications,
        pack,
        FakeLlmClient({"topic_synthesis": handler}),
        audience="internal",
        stamp=STAMP,
    )
    body = next(page for page in pages if page.frontmatter.id == "topic:gearbox-oil").body
    refs, defs = extract_footnotes(body)
    order: list[str] = []
    for label, _line in refs:
        if label not in order:
            order.append(label)
    assert order == [f"c{index}" for index in range(1, len(order) + 1)] and len(order) == 3
    assert [d.label for d in defs] == order


async def test_audience_filtering(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, skips, llm = await build(corpus, pack, audience="public")
    assert pages == {} and llm.requests == []
    assert {(s.topic_slug, s.reason) for s in skips} == {
        ("gearbox-oil", "audience"),
        ("cold-weather", "audience"),
        ("blade-inspection", "insufficient_evidence"),
    }
    assert all(s.sources == () for s in skips)
    restricted, _, _, _ = await build(corpus, pack, audience="restricted")
    page = restricted["topic:gearbox-oil"]
    assert CONTRACT in page.frontmatter.sources  # type: ignore[union-attr]
    assert page.frontmatter.sensitivity == "restricted"


async def test_minimum_sources_and_current_sources(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, skips, _ = await build(corpus, pack, results=[corpus.results[SOP_A]])
    assert pages == {}
    assert ("gearbox-oil", "insufficient_evidence") in {(s.topic_slug, s.reason) for s in skips}
    lenient = pack.model_copy(
        update={
            "topics": TopicsFile(
                topics=[topic.model_copy(update={"min_sources": 1}) for topic in pack.topics.topics]
            )
        }
    )
    llm = FakeLlmClient({"topic_synthesis": synthesis_handler})
    pages_list, _, skips = await build_topic_pages(
        [corpus.results[SOP_A]],
        corpus.pages,
        corpus.states,
        corpus.classifications,
        lenient,
        llm,
        audience="internal",
        stamp=STAMP,
    )
    assert pages_list == []
    assert TopicSkip("gearbox-oil", "no_current_sources", (SOP_A,)) in skips


def _truncated(request: LlmRequest) -> dict:
    raise LlmOutputTruncated("hit max_output_tokens", raw_output='{"summary": "')


def _filtered(request: LlmRequest) -> dict:
    raise LlmContentFiltered("The completion was blocked by content filtering")


def _invalid(request: LlmRequest) -> dict:
    return {"summary": "Gearbox oil.", "overview": "not a list"}


@pytest.mark.parametrize(
    ("failure", "error"),
    [
        (_truncated, "LlmOutputTruncated"),
        (_filtered, "LlmContentFiltered (content_filter)"),
        (_invalid, "LlmInvalidOutput"),
    ],
)
async def test_failed_synthesis_skips_only_that_topic(
    corpus: Corpus,
    pack: DomainPack,
    caplog: pytest.LogCaptureFixture,
    failure: Callable[[LlmRequest], dict],
    error: str,
) -> None:
    def handler(request: LlmRequest) -> dict:
        if "- slug: gearbox-oil" in request.text:
            return failure(request)
        return synthesis_handler(request)

    with caplog.at_level(logging.WARNING, logger="docwiki.stages.topics"):
        pages, cited, skips = await build_topic_pages(
            list(corpus.results.values()),
            corpus.pages,
            corpus.states,
            corpus.classifications,
            pack,
            FakeLlmClient({"topic_synthesis": handler}),
            audience="internal",
            stamp=STAMP,
        )
    assert [page.frontmatter.id for page in pages] == ["topic:cold-weather"]
    assert cited
    assert skips == [
        TopicSkip("blade-inspection", "insufficient_evidence", ()),
        TopicSkip("gearbox-oil", "insufficient_evidence", tuple(sorted([SOP_B, SOP_A, PLAN]))),
    ]
    warnings = [r.getMessage() for r in caplog.records if r.name == "docwiki.stages.topics"]
    assert warnings == [
        f"topic gearbox-oil: synthesis call failed ({error}); the topic is skipped as "
        "insufficient_evidence"
    ]


async def test_systemic_synthesis_failures_propagate(corpus: Corpus, pack: DomainPack) -> None:
    def handler(request: LlmRequest) -> dict:
        raise LlmServiceError("HTTP 503 after the retries", status_code=503)

    with pytest.raises(LlmServiceError):
        await build_topic_pages(
            list(corpus.results.values()),
            corpus.pages,
            corpus.states,
            corpus.classifications,
            pack,
            FakeLlmClient({"topic_synthesis": handler}),
            audience="internal",
            stamp=STAMP,
        )


def info(title: str, authority: int, day: str | None) -> SourceInfo:
    from datetime import date

    return SourceInfo(
        source_id="src-000000000000",
        title=title,
        path="sources/x.md",
        status="current",
        sensitivity="internal",
        authority=authority,
        doc_type="sop",
        doc_number=None,
        revision=None,
        date=date.fromisoformat(day) if day else None,
        supersedes=(),
        superseded_by=(),
    )


def test_resolution_statement(pack: DomainPack) -> None:
    assert resolution_statement(pack, info("A", 5, None), info("B", 7, None)).endswith(
        "B prevails (authority 7 vs 5)."
    )
    assert resolution_statement(
        pack, info("A", 7, "2026-01-01"), info("B", 7, "2026-02-01")
    ).endswith("B prevails (dated 2026-02-01 vs 2026-01-01).")
    assert "does not decide" in resolution_statement(pack, info("A", 7, None), info("B", 7, None))
