"""Topic pages: routing thresholds, audience filtering, contradictions and supersession."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest
from compile_testkit import (
    PLAN,
    QUOTE_A,
    QUOTE_B,
    STAMP,
    STUDY,
    Corpus,
    build_corpus,
    fact_id,
    source_label,
)

from docwiki.contracts import Page, find_violations
from docwiki.contracts.markdown import extract_footnotes, extract_headings
from docwiki.contracts.pages import ContradictionPair, TopicFrontmatter
from docwiki.domain import DomainPack
from docwiki.domain.models import ResolutionFile, ScopesFile, TopicsFile
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
from docwiki.stages.topics import (
    ScopeContext,
    build_topic_pages,
    is_change,
    resolution_statement,
    route_sources,
)


@pytest.fixture
async def corpus(pack: DomainPack) -> Corpus:
    return await build_corpus(pack)


def synthesis_handler(request: LlmRequest) -> dict:
    text = request.text
    frost = fact_id(text, "In case of frost below")
    if "- slug: cold-weather-works" in text:
        return {
            "summary": "How frost changes the masonry work.",
            "overview": [
                {"text": "Frost below -5 °C suspends the masonry work.", "fact_ids": [frost]}
            ],
            "sections": [],
            "contradictions": [],
            "superseded": [],
        }
    first = fact_id(text, "is installed first")
    wide = fact_id(text, "is widened to")
    plan = fact_id(text, "is ordered at 2,40 m")
    old = fact_id(text, "Indice A specifies")
    quote_b = source_label(text, "Quote DEV-2026-014 indice B")
    return {
        "summary": "Window sizes, the installation order and an open purchase-tracking "
        "contradiction.",
        "overview": [
            {"text": "In frost below -5 °C, the masonry work is suspended.", "fact_ids": [frost]},
            {"text": "All bays are 2,40 m wide.", "fact_ids": [old]},
            {"text": "The bay window F1 is installed first.", "fact_ids": [first, old, "F99"]},
        ],
        "sections": [
            {
                "heading": "Window sizes",
                "claims": [
                    {
                        "text": (
                            "The bay window F1 is ordered at 2,40 m for delivery on 2026-03-30."
                        ),
                        "fact_ids": [plan],
                    },
                    {"text": "The slab is 30,00 m long.", "fact_ids": [frost]},
                ],
            },
            {"heading": "Overview", "claims": [{"text": "Repeated.", "fact_ids": [first]}]},
            {"heading": "Empty", "claims": [{"text": "Nothing.", "fact_ids": ["F404"]}]},
        ],
        "contradictions": [
            {"subject": "Width of the bay window F1", "fact_ids_a": [plan], "fact_ids_b": [wide]},
            {"subject": "Same source", "fact_ids_a": [frost], "fact_ids_b": [first]},
        ],
        "superseded": [
            {
                "subject": "Width of the bays",
                "old_fact_ids": [old],
                "replacement_fact_ids": [wide],
                "superseding_source": quote_b,
            },
            {
                "subject": "Invalid",
                "old_fact_ids": [frost],
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
    assert set(feeding["schedule-and-window-delivery"]) == {QUOTE_B, QUOTE_A, PLAN, STUDY}
    assert feeding["cold-weather-works"] == [QUOTE_B]
    assert "kitchen-renovation" not in feeding
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
    assert sorted(pages) == ["topic:cold-weather-works", "topic:schedule-and-window-delivery"]
    assert skips == [TopicSkip("kitchen-renovation", "insufficient_evidence", ())]
    assert all(r.tier == "smart" and r.prompt_version == "topic-synthesis-v2" for r in llm.requests)
    request = next(r for r in llm.requests if "- slug: schedule-and-window-delivery" in r.text)
    assert "Internal price study" not in request.text and "supplied at cost" not in request.text, (
        "sources above the audience never reach the synthesis"
    )
    assert "Contradictions are resolved by authority, then recency" in request.text
    for page in pages.values():
        assert find_violations(page.body) == []
        assert Page.parse(page.render(), page.path) == page
    assert cited
    cold = pages["topic:cold-weather-works"].frontmatter
    assert isinstance(cold, TopicFrontmatter)
    assert (cold.sources, cold.confidence, cold.contradictions) == ([QUOTE_B], "low", 0)


async def test_window_delivery_page(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, _, _ = await build(corpus, pack)
    page = pages["topic:schedule-and-window-delivery"]
    fm = page.frontmatter
    assert isinstance(fm, TopicFrontmatter)
    assert page.path == "topics/schedule-and-window-delivery.md"
    assert fm.sources == sorted([QUOTE_B, QUOTE_A, PLAN])
    assert (fm.sensitivity, fm.contradictions, fm.superseded_claims, fm.confidence) == (
        "internal",
        1,
        1,
        "medium",
    )
    assert fm.summary == (
        "Window sizes, the installation order and an open purchase-tracking contradiction."
    )
    headings = [h.text for h in extract_headings(page.body)]
    assert headings == [
        "Schedule and window delivery",
        "Overview",
        "Window sizes",
        "Overview (topic section)",
        "Contradictions",
        "Superseded information",
        "Sources consulted",
        "Sources",
    ]
    body = page.body
    overview = body.split("## Overview\n\n", 1)[1].split("\n\n", 1)[0]
    assert overview == (
        "In frost below -5 °C, the masonry work is suspended.[^c1] "
        "The bay window F1 is installed first.[^c1]"
    ), "claims citing only superseded or unknown facts are dropped"
    assert "The slab is 30,00 m long." not in body, "quantities missing from the cited facts"
    contradiction = body.split("## Contradictions\n\n", 1)[1].split("\n\n", 1)[0]
    assert contradiction.startswith(
        "- **Width of the bay window F1.** [Schedule and purchase tracking]"
        "(../sources/planning-et-suivi-des-achats.md) states: The bay window F1 is ordered at "
        "2,40 m for delivery on 2026-03-30.[^c2] (authority 4, dated 2026-03-17). "
        "[Quote DEV-2026-014 indice B](../sources/dev-2026-014-indice-b.md) states: The bay "
        "window F1 is widened to 3,00 m.[^c1] (authority 8, dated 2026-02-03)."
    )
    assert contradiction.endswith(
        "Resolution rule (authority, then recency): Quote DEV-2026-014 indice B prevails "
        "(authority 8 vs 4)."
    )
    assert "Resolution policy: Higher authority wins" in body
    assert "Same source" not in body
    assert "Changed by" not in body, "a pack without amendments keeps every contradiction open"
    assert fm.contradiction_pairs == [
        ContradictionPair(sources=sorted([PLAN, QUOTE_B]), subject="Width of the bay window F1")
    ]
    superseded = body.split("## Superseded information\n\n", 1)[1].split("\n\n", 1)[0]
    assert superseded == (
        "- **Width of the bays.** [Quote DEV-2026-014 indice A]"
        "(../sources/dev-2026-014-indice-a.md) stated: Indice A specifies a width of 2,40 m for "
        "all bays, including the bay window F1.[^c3] Replacement: The bay window F1 is widened "
        "to 3,00 m.[^c1] Superseding source: [Quote DEV-2026-014 indice B]"
        "(../sources/dev-2026-014-indice-b.md)."
    )
    consulted = body.split("## Sources consulted\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert consulted == [
        "- [Quote DEV-2026-014 indice B](../sources/dev-2026-014-indice-b.md): current, "
        "authority 8, dated 2026-02-03",
        "- [Schedule and purchase tracking](../sources/planning-et-suivi-des-achats.md): "
        "current, authority 4, dated 2026-03-17",
        "- [Quote DEV-2026-014 indice A](../sources/dev-2026-014-indice-a.md): superseded, "
        "authority 8, dated 2026-01-20",
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
        if "- slug: schedule-and-window-delivery" not in text:
            return synthesis_handler(request)
        return {
            "summary": "Superseded bay window width.",
            "overview": [
                {
                    "text": "The bay window F1 is ordered at 2,40 m.",
                    "fact_ids": [fact_id(text, "is ordered at 2,40 m")],
                }
            ],
            "sections": [],
            "contradictions": [],
            "superseded": [
                {
                    "subject": "Width of the bays",
                    "old_fact_ids": [fact_id(text, "Indice A specifies")],
                    "replacement_fact_ids": [fact_id(text, "is widened to")],
                    "superseding_source": source_label(text, "Quote DEV-2026-014 indice B"),
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
    body = next(
        page for page in pages if page.frontmatter.id == "topic:schedule-and-window-delivery"
    ).body
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
        ("schedule-and-window-delivery", "audience"),
        ("cold-weather-works", "audience"),
        ("kitchen-renovation", "insufficient_evidence"),
    }
    assert all(s.sources == () for s in skips)
    restricted, _, _, _ = await build(corpus, pack, audience="restricted")
    page = restricted["topic:schedule-and-window-delivery"]
    assert STUDY in page.frontmatter.sources  # type: ignore[union-attr]
    assert page.frontmatter.sensitivity == "restricted"


async def test_minimum_sources_and_current_sources(corpus: Corpus, pack: DomainPack) -> None:
    pages, _, skips, _ = await build(corpus, pack, results=[corpus.results[QUOTE_A]])
    assert pages == {}
    assert ("schedule-and-window-delivery", "insufficient_evidence") in {
        (s.topic_slug, s.reason) for s in skips
    }
    lenient = pack.model_copy(
        update={
            "topics": TopicsFile(
                topics=[topic.model_copy(update={"min_sources": 1}) for topic in pack.topics.topics]
            )
        }
    )
    llm = FakeLlmClient({"topic_synthesis": synthesis_handler})
    pages_list, _, skips = await build_topic_pages(
        [corpus.results[QUOTE_A]],
        corpus.pages,
        corpus.states,
        corpus.classifications,
        lenient,
        llm,
        audience="internal",
        stamp=STAMP,
    )
    assert pages_list == []
    assert TopicSkip("schedule-and-window-delivery", "no_current_sources", (QUOTE_A,)) in skips


def _truncated(request: LlmRequest) -> dict:
    raise LlmOutputTruncated("hit max_output_tokens", raw_output='{"summary": "')


def _filtered(request: LlmRequest) -> dict:
    raise LlmContentFiltered("The completion was blocked by content filtering")


def _invalid(request: LlmRequest) -> dict:
    return {"summary": "Window sizes.", "overview": "not a list"}


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
        if "- slug: schedule-and-window-delivery" in request.text:
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
    assert [page.frontmatter.id for page in pages] == ["topic:cold-weather-works"]
    assert cited
    assert skips == [
        TopicSkip("kitchen-renovation", "insufficient_evidence", ()),
        TopicSkip(
            "schedule-and-window-delivery",
            "insufficient_evidence",
            tuple(sorted([QUOTE_B, QUOTE_A, PLAN])),
        ),
    ]
    warnings = [r.getMessage() for r in caplog.records if r.name == "docwiki.stages.topics"]
    assert warnings == [
        f"topic schedule-and-window-delivery: synthesis call failed ({error}); the topic is "
        "skipped as insufficient_evidence"
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
        doc_type="quote",
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


def _with_resolution(pack: DomainPack, **fields: object) -> DomainPack:
    resolution = ResolutionFile.model_validate({"notes": pack.resolution.notes, **fields})
    return pack.model_copy(update={"resolution": resolution})


async def _window_page(corpus: Corpus, pack: DomainPack) -> tuple[TopicFrontmatter, str]:
    llm = FakeLlmClient({"topic_synthesis": synthesis_handler})
    pages, _, _ = await build_topic_pages(
        list(corpus.results.values()),
        corpus.pages,
        corpus.states,
        corpus.classifications,
        pack,
        llm,
        audience="internal",
        stamp=STAMP,
    )
    page = next(p for p in pages if p.frontmatter.id == "topic:schedule-and-window-delivery")
    assert find_violations(page.body) == []
    assert Page.parse(page.render(), page.path) == page
    assert isinstance(page.frontmatter, TopicFrontmatter)
    return page.frontmatter, page.body.split("## Contradictions\n\n", 1)[1].split("## ", 1)[0]


async def test_a_contradiction_with_an_amending_document_is_a_change(
    corpus: Corpus, pack: DomainPack
) -> None:
    # The test pack's types stand in for a contract (the quote) and an amending act (the
    # schedule, dated after it): the disagreement is a change, not an open contradiction.
    amended = _with_resolution(pack, amendments=[{"amending": ["schedule"], "amended": ["quote"]}])
    fm, section = await _window_page(corpus, amended)
    assert (fm.contradictions, fm.contradiction_pairs) == (0, [])
    assert section.startswith("No contradictions were found between current sources.\n\n")
    assert (
        "Changed by an amending document (changes of terms, not contradictions):\n\n"
        "- **Width of the bay window F1.** [Quote DEV-2026-014 indice B]"
        "(../sources/dev-2026-014-indice-b.md) states: The bay window F1 is widened to 3,00 m."
        "[^c1] (authority 8, dated 2026-02-03). Changed by [Schedule and purchase tracking]"
        "(../sources/planning-et-suivi-des-achats.md): The bay window F1 is ordered at 2,40 m for "
        "delivery on 2026-03-30.[^c2] (authority 4, dated 2026-03-17)."
    ) in section
    assert "Resolution rule" not in section and "Resolution policy:" in section


async def test_an_amending_document_of_another_scope_changes_nothing(
    corpus: Corpus, pack: DomainPack
) -> None:
    scopes = ScopesFile.model_validate(
        {
            "name": "chantier",
            "title": "Chantier",
            "plural": "chantiers",
            "default": {"key": "entreprise", "title": "Entreprise"},
            "paths": [{"regex": "^(?P<scope>planning)/"}],
        }
    )
    amended = _with_resolution(pack, amendments=[{"amending": ["schedule"], "amended": ["quote"]}])
    fm, section = await _window_page(corpus, amended.model_copy(update={"scopes": scopes}))
    assert fm.contradictions == 1 and "Changed by" not in section
    assert "Quote DEV-2026-014 indice B prevails (authority 8 vs 4)." in section


async def test_an_older_amending_document_changes_nothing(corpus: Corpus, pack: DomainPack) -> None:
    # The quote (2026-02-03) cannot have changed the later schedule (2026-03-17).
    amended = _with_resolution(pack, amendments=[{"amending": ["quote"], "amended": ["schedule"]}])
    fm, section = await _window_page(corpus, amended)
    assert fm.contradictions == 1 and "Changed by" not in section


async def test_a_pair_to_arbitrate_is_not_decided_by_the_rule(
    corpus: Corpus, pack: DomainPack
) -> None:
    reason = "a written constraint of the client is arbitrated with the client"
    arbitrated = _with_resolution(
        pack, arbitrate=[{"types": ["quote", "schedule"], "reason": reason}]
    )
    fm, section = await _window_page(corpus, arbitrated)
    assert fm.contradictions == 1 and len(fm.contradiction_pairs) == 1
    assert (
        "Resolution rule (authority, then recency): to arbitrate; the rule does not decide "
        "between Schedule and purchase tracking and Quote DEV-2026-014 indice B. A written "
        "constraint of the client is arbitrated with the client."
    ) in section
    assert "prevails" not in section


def typed(source_id: str, title: str, doc_type: str, authority: int, day: str) -> SourceInfo:
    from datetime import date

    return SourceInfo(
        source_id=source_id,
        title=title,
        path=f"sources/{title.lower()}.md",
        status="current",
        sensitivity="internal",
        authority=authority,
        doc_type=doc_type,
        doc_number=None,
        revision=None,
        date=date.fromisoformat(day),
        supersedes=(),
        superseded_by=(),
    )


def test_a_winning_amended_document_is_to_review(pack: DomainPack) -> None:
    rules = _with_resolution(
        pack, amendments=[{"amending": ["contract-amendment"], "amended": ["quote"]}]
    )
    contract = typed("src-00000000000a", "Contract", "quote", 8, "2026-01-10")
    schedule = typed("src-00000000000b", "Schedule", "schedule", 4, "2026-03-01")
    order = typed("src-00000000000c", "Order 1", "contract-amendment", 10, "2026-02-01")
    early = typed("src-00000000000d", "Old order", "contract-amendment", 10, "2026-01-01")
    links = ((order, "[Order 1](order-1.md)"), (early, "[Old order](old-order.md)"))
    context = {
        sid: ScopeContext("Chantier Alpha", links)
        for sid in (contract.source_id, schedule.source_id)
    }
    assert resolution_statement(rules, schedule, contract, context) == (
        "Resolution rule (authority, then recency): to review; the rule would favour Contract "
        "(authority 8 vs 4), but the terms of Contract may have been changed by the amending "
        "documents of Chantier Alpha: [Order 1](order-1.md); check them before relying on either "
        "statement."
    ), "an amending document dated before the contract is not listed"
    # without amending documents in its scope, or without the pack's amendments, the rule decides
    alone = {sid: ScopeContext("Chantier Alpha") for sid in context}
    plain = "Resolution rule (authority, then recency): Contract prevails (authority 8 vs 4)."
    assert resolution_statement(rules, schedule, contract, alone) == plain
    assert resolution_statement(pack, schedule, contract, context) == plain
    assert resolution_statement(rules, schedule, contract) == plain
    # an amending document and its own contract: a change, never "to review"
    assert is_change(rules, contract, order) and not is_change(rules, contract, early)
    assert not is_change(rules, order, contract) and not is_change(pack, contract, order)
