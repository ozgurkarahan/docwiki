"""Topic pages (pipeline.md §4, wiki-contract §3–4 and §9).

Routing is deterministic: every compiled source (title, compiled sections and the key-facts
section) is scored against the closed topic catalog with ``docwiki.domain.route_topics``
(keywords and aliases, title 3 / heading 2 / body 1, ``min_score`` default 3.0). Sources above
the build audience never feed a page. A topic is synthesised when at least ``min_sources``
(default 2) current or superseded sources feed it and one of them is current; otherwise it is
skipped with a :class:`~docwiki.engine_types.TopicSkip` reason.

The ``smart`` synthesis returns thematic claims citing fact ids, contradictions (fact ids of two
current sources) and superseded information (old and replacement fact ids, superseding source).
Code keeps only known fact ids, current-source facts in the overview and sections, and states the
domain pack's resolution rule (authority, then recency) for each contradiction without applying
it silently. Footnotes map every fact back to its source locators.

A synthesis call that fails for its request only (content filter, output invalid or truncated,
see :mod:`docwiki.stages.llm_failures`) does not stop the other topics: that topic is skipped with
reason ``insufficient_evidence`` (the closest :class:`~docwiki.engine_types.TopicSkip` reason, as
for a synthesis without any verifiable claim) and a warning names the failure; the usage ledger
records the failed call. Systemic failures (auth, rate limits, timeouts…) propagate.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from docwiki.contracts.enums import Sensitivity, allowed_for_audience, max_sensitivity
from docwiki.contracts.ids import format_topic_id, normalize_tags, topic_page_path
from docwiki.contracts.markdown import relative_link
from docwiki.contracts.pages import DocwikiStamp, Page, TopicFrontmatter
from docwiki.contracts.state import SourceState
from docwiki.domain import DomainPack, route_topics, score_topic
from docwiki.domain.models import TopicDef
from docwiki.domain.rules import DEFAULT_MIN_SOURCES
from docwiki.engine_types import CitedLocator, Classification, CompiledResult, TopicSkip
from docwiki.llm import LlmClient, LlmError
from docwiki.stages.classify import data_nonce
from docwiki.stages.entities import source_order
from docwiki.stages.llm_failures import describe_failure, is_systemic
from docwiki.stages.models import (
    FactRecord,
    SourceInfo,
    TopicClaimOut,
    TopicSynthesisOutput,
)
from docwiki.stages.prompts import load_prompt
from docwiki.stages.render import (
    Footnotes,
    attach_refs,
    banner_line,
    clean_inline,
    fact_records,
    release_date,
    section_heading,
    source_infos,
)
from docwiki.stages.verify_citations import (
    split_sentences,
    strip_markers,
    unsigned_values,
    unsupported_quantities,
)

__all__ = [
    "MAX_FACT_TOKENS",
    "PROMPT_VERSION",
    "STAGE_VERSION",
    "build_topic_pages",
    "resolution_statement",
    "route_sources",
]

STAGE_VERSION = "1"
PROMPT_VERSION = load_prompt("topic-synthesis").version
SCHEMA_NAME = "topic_synthesis"
MAX_FACT_TOKENS = 16_000
CHARS_PER_TOKEN = 4
MAX_OUTPUT_TOKENS = 12_000

logger = logging.getLogger("docwiki.stages.topics")


@dataclass(frozen=True)
class _Fact:
    fact_id: str
    record: FactRecord
    current: bool


@dataclass
class _Claim:
    text: str
    facts: list[_Fact]


@dataclass
class _Contradiction:
    subject: str
    side_a: list[_Fact]
    side_b: list[_Fact]


@dataclass
class _Superseded:
    subject: str
    old: list[_Fact]
    replacement: list[_Fact]
    superseding: str


@dataclass
class _Synthesis:
    summary: str
    overview: list[_Claim]
    sections: list[tuple[str, list[_Claim]]]
    contradictions: list[_Contradiction]
    superseded: list[_Superseded]
    dropped: int
    total: int


def route_sources(results: Sequence[CompiledResult], pack: DomainPack) -> dict[str, list[str]]:
    """Topic slug → source ids feeding it (deterministic keyword routing, best scores first)."""
    feeding: dict[str, list[tuple[float, str]]] = {}
    for result in sorted(results, key=lambda item: item.source_id):
        compiled = result.compiled
        sections = [(section.heading, strip_markers(section.body)) for section in compiled.sections]
        facts = "\n".join(fact.text for fact in compiled.key_facts)
        if facts:
            sections.append(("Key facts", facts))
        for score in route_topics(pack, compiled.title, sections):
            feeding.setdefault(score.slug, []).append((score.score, result.source_id))
    return {
        slug: [source_id for _, source_id in sorted(items, key=lambda item: (-item[0], item[1]))]
        for slug, items in feeding.items()
    }


def resolution_statement(pack: DomainPack, first: SourceInfo, second: SourceInfo) -> str:
    """The pack's contradiction rule stated for two sources (never applied silently)."""
    criteria = list(pack.resolution.order)
    rule = ", then ".join(criteria)
    for criterion in criteria:
        if criterion == "authority" and first.authority != second.authority:
            winner, loser = (
                (first, second)
                if first.authority > second.authority
                else (
                    second,
                    first,
                )
            )
            return (
                f"Resolution rule ({rule}): {winner.title} prevails (authority "
                f"{winner.authority} vs {loser.authority})."
            )
        if (
            criterion == "recency"
            and first.date is not None
            and second.date is not None
            and first.date != second.date
        ):
            winner, loser = (first, second) if first.date > second.date else (second, first)
            return (
                f"Resolution rule ({rule}): {winner.title} prevails (dated "
                f"{winner.date.isoformat()} vs {loser.date.isoformat()})."  # type: ignore[union-attr]
            )
    return (
        f"Resolution rule ({rule}): the rule does not decide between them (same authority and "
        "no usable dates); review both sources."
    )


def _select_facts(
    topic: TopicDef,
    sources: Sequence[str],
    records: Mapping[str, list[FactRecord]],
    infos: Mapping[str, SourceInfo],
) -> list[_Fact]:
    """Facts given to the model: topic-relevant ones first within the budget, source order."""
    candidates: list[tuple[int, int, FactRecord]] = []
    for source_rank, source_id in enumerate(sources):
        for fact_rank, record in enumerate(records.get(source_id, [])):
            candidates.append((source_rank, fact_rank, record))
    relevant = [
        item for item in candidates if score_topic(topic, "", [("", item[2].text)]).score > 0
    ]
    relevant_keys = {(item[0], item[1]) for item in relevant}
    others = [item for item in candidates if (item[0], item[1]) not in relevant_keys]
    budget = MAX_FACT_TOKENS * CHARS_PER_TOKEN
    chosen: list[tuple[int, int, FactRecord]] = []
    size = 0
    for item in [*relevant, *others]:
        length = len(item[2].text) + 40
        if size + length > budget:
            continue
        chosen.append(item)
        size += length
    chosen.sort(key=lambda item: (item[0], item[1]))
    return [
        _Fact(
            fact_id=f"F{number}",
            record=record,
            current=infos[record.source_id].status == "current",
        )
        for number, (_, _, record) in enumerate(chosen, start=1)
    ]


def _request(
    topic: TopicDef,
    pack: DomainPack,
    sources: Sequence[str],
    labels: Mapping[str, str],
    facts: Sequence[_Fact],
    infos: Mapping[str, SourceInfo],
) -> str:
    lines = [
        "# Task",
        "Write the synthesis of the topic below from the verified facts.",
        "",
        "# Topic (reviewed topic catalog)",
        f"- slug: {topic.slug}",
        f"- title: {topic.title}",
    ]
    if topic.description:
        lines.append(f"- description: {topic.description}")
    if topic.keywords:
        lines.append("- keywords: " + ", ".join(topic.keywords))
    lines += [
        "",
        "# Resolution policy (reviewed domain pack)",
        "Contradictions are resolved by " + ", then ".join(pack.resolution.order) + "; the "
        "page states the rule and shows both claims.",
    ]
    if pack.resolution.notes:
        lines.append(pack.resolution.notes.strip())
    lines += ["", "# Sources"]
    for source_id in sources:
        info = infos[source_id]
        parts = [
            f"doc type {info.doc_type}",
            f"authority {info.authority}/10",
            info.status,
            f"dated {info.date.isoformat()}" if info.date else "date unknown",
        ]
        if info.doc_number:
            parts.append(
                f"document {info.doc_number}" + (f" rev {info.revision}" if info.revision else "")
            )
        relations = [f"supersedes {labels[sid]}" for sid in info.supersedes if sid in labels]
        relations += [f"superseded by {labels[sid]}" for sid in info.superseded_by if sid in labels]
        lines.append(f"- [{labels[source_id]}] {info.title} — " + ", ".join(parts + relations))
    body = "\n".join(
        f"[{fact.fact_id}] {labels[fact.record.source_id]}: {fact.record.text}" for fact in facts
    )
    nonce = data_nonce(body)
    lines += ["", "# Facts", f"BEGIN FACTS {nonce}", body, f"END FACTS {nonce}"]
    return "\n".join(lines)


def _fact_lookup(facts: Sequence[_Fact]) -> dict[str, _Fact]:
    return {fact.fact_id.lower(): fact for fact in facts}


def _resolve_ids(
    raw_ids: Sequence[str], lookup: Mapping[str, _Fact], *, current: bool | None
) -> list[_Fact]:
    found: list[_Fact] = []
    for raw in raw_ids:
        match = re.fullmatch(r"\s*\[?(f\d+)\]?\s*", raw, re.IGNORECASE)
        fact = lookup.get(match.group(1).lower()) if match else None
        if fact is None or fact in found:
            continue
        if current is not None and fact.current != current:
            continue
        found.append(fact)
    return found


def _support(facts: Sequence[_Fact]) -> set[str]:
    texts: list[str] = []
    for fact in facts:
        texts.append(fact.record.text)
        texts.extend(fact.record.numbers)
        texts.extend(citation.quote or "" for citation in fact.record.citations)
    return unsigned_values(texts)


def _guarded(text: str, facts: Sequence[_Fact]) -> str:
    support = _support(facts)
    kept = [
        piece.strip()
        for piece in split_sentences(clean_inline(text))
        if not unsupported_quantities(piece, support)
    ]
    return " ".join(piece for piece in kept if piece)


def _claims(raw: Sequence[TopicClaimOut], lookup: Mapping[str, _Fact]) -> tuple[list[_Claim], int]:
    claims: list[_Claim] = []
    dropped = 0
    for item in raw:
        facts = _resolve_ids(item.fact_ids, lookup, current=True)
        text = _guarded(item.text, facts) if facts else ""
        if not text:
            dropped += 1
            continue
        claims.append(_Claim(text, facts))
    return claims, dropped


def _single_source(facts: Sequence[_Fact]) -> str | None:
    sources = {fact.record.source_id for fact in facts}
    return next(iter(sources)) if len(sources) == 1 else None


def _verify(
    output: TopicSynthesisOutput,
    facts: Sequence[_Fact],
    labels: Mapping[str, str],
    infos: Mapping[str, SourceInfo],
) -> _Synthesis:
    lookup = _fact_lookup(facts)
    overview, dropped = _claims(output.overview, lookup)
    total = len(output.overview)
    sections: list[tuple[str, list[_Claim]]] = []
    used: set[str] = set()
    for section in output.sections:
        claims, lost = _claims(section.claims, lookup)
        dropped += lost
        total += len(section.claims)
        heading = section_heading(section.heading, used, suffix="topic section") if claims else None
        if heading and claims:
            sections.append((heading, claims))
    contradictions: list[_Contradiction] = []
    seen_pairs: set[tuple[str, str, str]] = set()
    for item in output.contradictions:
        total += 1
        side_a = _resolve_ids(item.fact_ids_a, lookup, current=True)
        side_b = _resolve_ids(item.fact_ids_b, lookup, current=True)
        source_a, source_b = _single_source(side_a), _single_source(side_b)
        subject = clean_inline(item.subject).rstrip(".")
        if not (source_a and source_b and subject) or source_a == source_b:
            dropped += 1
            continue
        key = (min(source_a, source_b), max(source_a, source_b), subject.casefold())
        if key in seen_pairs:
            continue
        seen_pairs.add(key)
        contradictions.append(_Contradiction(subject, side_a, side_b))
    by_label = {label.lower(): source_id for source_id, label in labels.items()}
    superseded: list[_Superseded] = []
    for change in output.superseded:
        total += 1
        old = _resolve_ids(change.old_fact_ids, lookup, current=False)
        replacement = _resolve_ids(change.replacement_fact_ids, lookup, current=True)
        subject = clean_inline(change.subject).rstrip(".")
        superseding = by_label.get((change.superseding_source or "").strip().strip("[]").lower())
        if superseding is None or infos[superseding].status != "current":
            superseding = next(
                (
                    sid
                    for fact in old
                    for sid in infos[fact.record.source_id].superseded_by
                    if sid in infos and infos[sid].status == "current"
                ),
                None,
            )
        if not old or not subject or superseding is None:
            dropped += 1
            continue
        superseded.append(_Superseded(subject, old, replacement, superseding))
    summary = _guarded(output.summary, facts)
    return _Synthesis(summary, overview, sections, contradictions, superseded, dropped, total)


def _confidence(current_sources: int, synthesis: _Synthesis) -> str:
    ratio = synthesis.dropped / synthesis.total if synthesis.total else 1.0
    if current_sources >= 3 and not synthesis.contradictions and ratio <= 0.2:
        return "high"
    if current_sources >= 2 and ratio <= 0.5:
        return "medium"
    return "low"


def _fact_texts(facts: Sequence[_Fact], footnotes: Footnotes) -> str:
    return " ".join(
        attach_refs(fact.record.text, footnotes.cite_all(fact.record.citations)) for fact in facts
    )


def _source_link(info: SourceInfo, path: str) -> str:
    return f"[{info.title}]({relative_link(path, info.path)})"


def _render(
    topic: TopicDef,
    sources: Sequence[str],
    synthesis: _Synthesis,
    infos: Mapping[str, SourceInfo],
    tiers: Mapping[str, str],
    pack: DomainPack,
    stamp: DocwikiStamp,
) -> tuple[Page, list[CitedLocator]]:
    path = topic_page_path(format_topic_id(topic.slug))
    footnotes = Footnotes(path, {sid: info.title for sid, info in infos.items()})
    title = topic.title
    lines = [f"# {title}", ""]
    banner = banner_line(pack)
    if banner:
        lines += [banner, ""]
    summary = (
        synthesis.summary
        or clean_inline(topic.description)
        or (f"Synthesis of {len(sources)} sources about {title.lower()}.")
    )
    lines += [summary, "", "## Overview", ""]
    if synthesis.overview:
        lines.append(
            " ".join(
                attach_refs(claim.text, _claim_refs(claim, footnotes))
                for claim in synthesis.overview
            )
        )
    else:
        lines.append("No overview claim could be verified against current sources.")
    for heading, claims in synthesis.sections:
        lines += ["", f"## {heading}", ""]
        lines += [f"- {attach_refs(claim.text, _claim_refs(claim, footnotes))}" for claim in claims]
    lines += ["", "## Contradictions", ""]
    if synthesis.contradictions:
        for item in synthesis.contradictions:
            first = infos[item.side_a[0].record.source_id]
            second = infos[item.side_b[0].record.source_id]
            lines.append(
                f"- **{item.subject}.** {_source_link(first, path)} states: "
                f"{_fact_texts(item.side_a, footnotes)} ({_meta(first)}). "
                f"{_source_link(second, path)} states: {_fact_texts(item.side_b, footnotes)} "
                f"({_meta(second)}). {resolution_statement(pack, first, second)}"
            )
        notes = clean_inline(pack.resolution.notes)
        if notes:
            lines += ["", f"Resolution policy: {notes}"]
    else:
        lines.append("No contradictions were found between current sources.")
    lines += ["", "## Superseded information", ""]
    if synthesis.superseded:
        for entry in synthesis.superseded:
            old_source = infos[entry.old[0].record.source_id]
            # Cite in reading order (old statement, then its replacement): footnote labels
            # must be c1..cN in order of first use (gate G03).
            old_text = _fact_texts(entry.old, footnotes)
            replacement = (
                _fact_texts(entry.replacement, footnotes)
                if entry.replacement
                else "no current source restates it."
            )
            lines.append(
                f"- **{entry.subject}.** {_source_link(old_source, path)} stated: "
                f"{old_text} Replacement: {replacement} "
                f"Superseding source: {_source_link(infos[entry.superseding], path)}."
            )
    else:
        lines.append("No superseded information.")
    lines += ["", "## Sources consulted", ""]
    for source_id in sources:
        info = infos[source_id]
        lines.append(f"- {_source_link(info, path)}: {_meta(info, with_status=True)}")
    lines += ["", *footnotes.sources_section()]
    current = sum(1 for sid in sources if infos[sid].status == "current")
    frontmatter = TopicFrontmatter(
        id=format_topic_id(topic.slug),
        title=title,
        summary=summary,
        sensitivity=max_sensitivity(*(tiers[sid] for sid in sources)),  # type: ignore[arg-type]
        updated=release_date(stamp),
        tags=normalize_tags([topic.slug]),
        docwiki=stamp,
        topic_slug=topic.slug,
        sources=sorted(sources),
        confidence=_confidence(current, synthesis),  # type: ignore[arg-type]
        contradictions=len(synthesis.contradictions),
        superseded_claims=len(synthesis.superseded),
    )
    page = Page(path=path, frontmatter=frontmatter, body="\n".join(lines) + "\n")
    return page, footnotes.cited_locators()


def _claim_refs(claim: _Claim, footnotes: Footnotes) -> str:
    return footnotes.cite_all(c for fact in claim.facts for c in fact.record.citations)


def _meta(info: SourceInfo, *, with_status: bool = False) -> str:
    parts = [info.status] if with_status else []
    parts.append(f"authority {info.authority}")
    parts.append(f"dated {info.date.isoformat()}" if info.date else "date unknown")
    return ", ".join(parts)


async def _synthesize(
    llm: LlmClient,
    topic: TopicDef,
    pack: DomainPack,
    sources: Sequence[str],
    labels: Mapping[str, str],
    facts: Sequence[_Fact],
    infos: Mapping[str, SourceInfo],
) -> TopicSynthesisOutput | None:
    """The model's synthesis, or None when the call fails for this topic only."""
    try:
        result = await llm.structured(
            tier="smart",
            system=load_prompt("topic-synthesis").text,
            user=_request(topic, pack, sources, labels, facts, infos),
            output=TopicSynthesisOutput,
            schema_name=SCHEMA_NAME,
            prompt_version=PROMPT_VERSION,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            metadata={"stage": "topics", "topic": topic.slug},
        )
    except LlmError as exc:
        if is_systemic(exc):
            raise
        logger.warning(
            "topic %s: synthesis call failed (%s); the topic is skipped as insufficient_evidence",
            topic.slug,
            describe_failure(exc),
        )
        return None
    return result.output


async def build_topic_pages(
    results: Sequence[CompiledResult],
    source_pages: Mapping[str, Page],
    states: Mapping[str, SourceState],
    classifications: Mapping[str, Classification],
    pack: DomainPack,
    llm: LlmClient,
    *,
    audience: Sensitivity,
    stamp: DocwikiStamp,
) -> tuple[list[Page], list[CitedLocator], list[TopicSkip]]:
    """Topic pages of the closed catalog, the locators they cite and the skipped topics."""
    infos = source_infos(source_pages, results)
    for source_id, classification in classifications.items():
        if source_id in infos:
            infos[source_id] = replace(infos[source_id], authority=classification.authority)
    usable = [
        result
        for result in results
        if result.source_id in infos
        and infos[result.source_id].status in ("current", "superseded")
        and not (result.source_id in states and states[result.source_id].deleted)
    ]
    tiers: dict[str, str] = {}
    for result in usable:
        tier = infos[result.source_id].sensitivity
        state = states.get(result.source_id)
        tiers[result.source_id] = max_sensitivity(tier, state.sensitivity) if state else tier
    records = {result.source_id: fact_records(result) for result in usable}
    feeding = route_sources(usable, pack)
    skips: list[TopicSkip] = []
    jobs: list[tuple[TopicDef, list[str], dict[str, str], list[_Fact]]] = []
    for topic in pack.topics.topics:
        routed = feeding.get(topic.slug, [])
        minimum = topic.min_sources if topic.min_sources is not None else DEFAULT_MIN_SOURCES
        allowed = [sid for sid in routed if allowed_for_audience(tiers[sid], audience)]
        ordered = sorted(allowed, key=lambda sid: source_order(infos[sid]))
        if len(allowed) < minimum:
            reason = "audience" if len(routed) >= minimum else "insufficient_evidence"
            skips.append(TopicSkip(topic.slug, reason, tuple(sorted(allowed))))  # type: ignore[arg-type]
            continue
        if not any(infos[sid].status == "current" for sid in allowed):
            skips.append(TopicSkip(topic.slug, "no_current_sources", tuple(sorted(allowed))))
            continue
        labels = {source_id: f"S{number}" for number, source_id in enumerate(ordered, start=1)}
        facts = _select_facts(topic, ordered, records, infos)
        if not facts:
            skips.append(TopicSkip(topic.slug, "insufficient_evidence", tuple(sorted(allowed))))
            continue
        jobs.append((topic, ordered, labels, facts))
    outputs = await asyncio.gather(
        *(
            _synthesize(llm, topic, pack, ordered, labels, facts, infos)
            for topic, ordered, labels, facts in jobs
        )
    )
    pages: list[Page] = []
    cited: list[CitedLocator] = []
    for (topic, ordered, labels, facts), output in zip(jobs, outputs, strict=True):
        if output is None:
            skips.append(TopicSkip(topic.slug, "insufficient_evidence", tuple(sorted(ordered))))
            continue
        synthesis = _verify(output, facts, labels, infos)
        if not (
            synthesis.overview
            or synthesis.sections
            or synthesis.contradictions
            or synthesis.superseded
        ):
            skips.append(TopicSkip(topic.slug, "insufficient_evidence", tuple(sorted(ordered))))
            continue
        page, locators = _render(topic, ordered, synthesis, infos, tiers, pack, stamp)
        pages.append(page)
        cited.extend(locators)
    return pages, cited, skips
