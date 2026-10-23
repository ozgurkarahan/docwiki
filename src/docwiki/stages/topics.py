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

The pack's ``resolution.yaml`` may refine how the rule is stated (v1.7), by code only: a
contradiction between a document of an amended type (a contract) and a document of a type that
amends it (an amendment, a service order) of the same scope is a change, listed as "changed by"
and not counted as open; when the rule's winner is of an amended type and its scope has current
amending documents, the statement links them and says the point is to review; a pair of
``arbitrate`` types is never decided by the rule (to arbitrate, with the pack's reason). The
frontmatter records the open contradictions (``contradictions`` and ``contradiction_pairs``).

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
from dataclasses import dataclass, field, replace

from docwiki.contracts.enums import Sensitivity, allowed_for_audience, max_sensitivity
from docwiki.contracts.i18n import Strings, core_strings, language_name
from docwiki.contracts.ids import format_topic_id, normalize_tags, topic_page_path
from docwiki.contracts.markdown import relative_link
from docwiki.contracts.pages import ContradictionPair, DocwikiStamp, Page, TopicFrontmatter
from docwiki.contracts.state import SourceState
from docwiki.domain import DomainPack, route_topics, score_topic
from docwiki.domain.models import TopicDef, locked_terms_note
from docwiki.domain.rules import DEFAULT_MIN_SOURCES
from docwiki.engine_types import CitedLocator, Classification, CompiledResult, TopicSkip
from docwiki.llm import LlmClient, LlmError
from docwiki.stages.classify import data_nonce
from docwiki.stages.entities import source_order
from docwiki.stages.hubs import scope_label, source_scope
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
    "ScopeContext",
    "build_topic_pages",
    "is_change",
    "resolution_statement",
    "route_sources",
]

STAGE_VERSION = "4"
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
    """The open contradictions."""
    superseded: list[_Superseded]
    dropped: int
    total: int
    changes: list[_Contradiction] = field(default_factory=list)
    """Contradictions that are changes by an amending document: ``side_a`` is the amended
    document (the contract), ``side_b`` the amending one (v1.7)."""


@dataclass(frozen=True)
class ScopeContext:
    """What a resolution statement may say about the scope of one source (v1.7)."""

    label: str
    """The scope's name in a sentence (its registry label), or "" when the pack has no scopes."""
    amending: tuple[tuple[SourceInfo, str], ...] = ()
    """The scope's current documents of an amending type, each with its Markdown link."""


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


def _sentence(text: str) -> str:
    text = text.strip()
    text = text[:1].upper() + text[1:]
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _not_older(amending: SourceInfo, amended: SourceInfo) -> bool:
    """An amending document dated before the document it would amend cannot change it."""
    return not (amending.date and amended.date and amending.date < amended.date)


def is_change(pack: DomainPack, amended: SourceInfo, amending: SourceInfo) -> bool:
    """Whether ``amending`` may change ``amended``: its type amends that type (the pack's
    ``amendments``) and it is not dated before it. The caller checks they share a scope."""
    return pack.resolution.amendment(amending.doc_type, amended.doc_type) and _not_older(
        amending, amended
    )


def _amended_review(
    pack: DomainPack,
    winner: SourceInfo,
    sides: set[str],
    context: Mapping[str, ScopeContext] | None,
) -> str | None:
    """Why a winner of an amended type is to review: its scope's amending documents."""
    types = pack.resolution.amending_types(winner.doc_type)
    scope = (context or {}).get(winner.source_id)
    if not types or scope is None:
        return None
    links = [
        link
        for info, link in scope.amending
        if info.doc_type in types and info.source_id not in sides and _not_older(info, winner)
    ]
    if not links:
        return None
    t = pack.strings()
    where = t("resolution.where", label=scope.label) if scope.label else ""
    return t("resolution.amended_review", winner=winner.title, where=where, links=", ".join(links))


def resolution_statement(
    pack: DomainPack,
    first: SourceInfo,
    second: SourceInfo,
    context: Mapping[str, ScopeContext] | None = None,
) -> str:
    """The pack's contradiction rule stated for two sources (never applied silently).

    A pair of the pack's ``arbitrate`` types is stated as to arbitrate, whatever the rule would
    say. ``context`` maps source ids to their scope's amending documents (v1.7): a winner of an
    amended type whose scope has some is stated as to review, with their links.
    """
    t = pack.strings()
    criteria = list(pack.resolution.order)
    rule = t("resolution.then").join(t(f"resolution.{criterion}") for criterion in criteria)
    head = t("resolution.head", rule=rule)
    pair = pack.resolution.arbitration(first.doc_type, second.doc_type)
    if pair is not None:
        return t(
            "resolution.arbitrate",
            head=head,
            first=first.title,
            second=second.title,
            reason=_sentence(pair.reason),
        )
    for criterion in criteria:
        if criterion == "authority" and first.authority != second.authority:
            winner, loser = (
                (first, second) if first.authority > second.authority else (second, first)
            )
            why = t("resolution.why_authority", winner=winner.authority, loser=loser.authority)
        elif (
            criterion == "recency"
            and first.date is not None
            and second.date is not None
            and first.date != second.date
        ):
            winner, loser = (first, second) if first.date > second.date else (second, first)
            why = t(
                "resolution.why_dated",
                winner=winner.date.isoformat(),  # type: ignore[union-attr]
                loser=loser.date.isoformat(),  # type: ignore[union-attr]
            )
        else:
            continue
        review = _amended_review(pack, winner, {first.source_id, second.source_id}, context)
        if review is not None:
            return t("resolution.review", head=head, winner=winner.title, why=why, review=review)
        return t("resolution.prevails", head=head, winner=winner.title, why=why)
    return t("resolution.undecided", head=head)


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
    scope: str | None = None,
) -> str:
    lines = [
        "# Task",
        "Write the synthesis of the topic below from the verified facts.",
        f"Wiki language: {language_name(pack.canonical_lang)}.",
        "",
        "# Topic (reviewed topic catalog)",
        f"- slug: {topic.slug}",
        f"- title: {topic.title}",
    ]
    if scope is not None and pack.scopes is not None:
        # A per-scope topic (v1.7, ADR 0011): only the sources of this scope feed it.
        lines.append(f"- {pack.scopes.title.lower()}: {scope_label(pack, scope)} ({scope})")
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
    locked = locked_terms_note(pack)
    if locked:
        lines += ["", "# Vocabulary (reviewed domain pack)", locked]
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


def _split_changes(
    synthesis: _Synthesis,
    pack: DomainPack,
    infos: Mapping[str, SourceInfo],
    scope_of: Mapping[str, str | None],
) -> _Synthesis:
    """Move the contradictions between an amended and an amending document of the same scope
    to ``changes`` (amended side first): they are changes, not open contradictions."""
    if not pack.resolution.amendments:
        return synthesis
    still: list[_Contradiction] = []
    changes: list[_Contradiction] = []
    for item in synthesis.contradictions:
        a, b = item.side_a[0].record.source_id, item.side_b[0].record.source_id
        same_scope = scope_of.get(a) == scope_of.get(b)
        if same_scope and is_change(pack, infos[a], infos[b]):
            changes.append(item)
        elif same_scope and is_change(pack, infos[b], infos[a]):
            changes.append(_Contradiction(item.subject, item.side_b, item.side_a))
        else:
            still.append(item)
    return replace(synthesis, contradictions=still, changes=[*synthesis.changes, *changes])


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
    scope: str | None = None,
    scope_of: Mapping[str, str | None] | None = None,
    amending: Mapping[str | None, Sequence[str]] | None = None,
) -> tuple[Page, list[CitedLocator]]:
    topic_id = format_topic_id(topic.slug, scope)
    path = topic_page_path(topic_id)
    t = pack.strings()
    footnotes = Footnotes(path, {sid: info.title for sid, info in infos.items()}, t)
    sensitivity = max_sensitivity(*(tiers[sid] for sid in sources))
    context = _contexts(pack, sources, infos, tiers, sensitivity, path, scope_of, amending)
    title = topic.title if scope is None else f"{topic.title} — {scope_label(pack, scope)}"
    lines = [f"# {title}", ""]
    banner = banner_line(pack)
    if banner:
        lines += [banner, ""]
    summary = (
        synthesis.summary
        or clean_inline(topic.description)
        or t("topic.summary", count=len(sources), title=title.lower())
    )
    lines += [summary, "", f"## {t.heading('overview')}", ""]
    if synthesis.overview:
        lines.append(
            " ".join(
                attach_refs(claim.text, _claim_refs(claim, footnotes))
                for claim in synthesis.overview
            )
        )
    else:
        lines.append(t("topic.no_overview"))
    for heading, claims in synthesis.sections:
        lines += ["", f"## {heading}", ""]
        lines += [f"- {attach_refs(claim.text, _claim_refs(claim, footnotes))}" for claim in claims]
    lines += ["", f"## {t.heading('contradictions')}", ""]
    if synthesis.contradictions:
        for item in synthesis.contradictions:
            first = infos[item.side_a[0].record.source_id]
            second = infos[item.side_b[0].record.source_id]
            lines.append(
                t(
                    "topic.contradiction",
                    subject=item.subject,
                    first=_source_link(first, path),
                    first_facts=_fact_texts(item.side_a, footnotes),
                    first_meta=_meta(first, t),
                    second=_source_link(second, path),
                    second_facts=_fact_texts(item.side_b, footnotes),
                    second_meta=_meta(second, t),
                    resolution=resolution_statement(pack, first, second, context),
                )
            )
    else:
        lines.append(t("topic.no_contradictions"))
    if synthesis.changes:
        lines += ["", t("topic.changes_intro"), ""]
        for item in synthesis.changes:
            amended = infos[item.side_a[0].record.source_id]
            amending_doc = infos[item.side_b[0].record.source_id]
            lines.append(
                t(
                    "topic.change",
                    subject=item.subject,
                    amended=_source_link(amended, path),
                    amended_facts=_fact_texts(item.side_a, footnotes),
                    amended_meta=_meta(amended, t),
                    amending=_source_link(amending_doc, path),
                    amending_facts=_fact_texts(item.side_b, footnotes),
                    amending_meta=_meta(amending_doc, t),
                )
            )
    if synthesis.contradictions or synthesis.changes:
        notes = clean_inline(pack.resolution.notes)
        if notes:
            lines += ["", t("topic.policy", notes=notes)]
    lines += ["", f"## {t.heading('superseded')}", ""]
    if synthesis.superseded:
        for entry in synthesis.superseded:
            old_source = infos[entry.old[0].record.source_id]
            # Cite in reading order (old statement, then its replacement): footnote labels
            # must be c1..cN in order of first use (gate G03).
            old_text = _fact_texts(entry.old, footnotes)
            replacement = (
                _fact_texts(entry.replacement, footnotes)
                if entry.replacement
                else t("topic.no_restatement")
            )
            lines.append(
                t(
                    "topic.superseded_item",
                    subject=entry.subject,
                    old=_source_link(old_source, path),
                    old_text=old_text,
                    replacement=replacement,
                    superseding=_source_link(infos[entry.superseding], path),
                )
            )
    else:
        lines.append(t("topic.no_superseded"))
    lines += ["", f"## {t.heading('sources_consulted')}", ""]
    for source_id in sources:
        info = infos[source_id]
        lines.append(t("topic.consulted", link=_source_link(info, path), meta=_meta(info, t, True)))
    lines += ["", *footnotes.sources_section()]
    current = sum(1 for sid in sources if infos[sid].status == "current")
    frontmatter = TopicFrontmatter(
        id=topic_id,
        title=title,
        summary=summary,
        lang=pack.canonical_lang,
        sensitivity=sensitivity,  # type: ignore[arg-type]
        updated=release_date(stamp),
        tags=normalize_tags([topic.slug]),
        docwiki=stamp,
        topic_slug=topic.slug,
        scope=scope,
        sources=sorted(sources),
        confidence=_confidence(current, synthesis),  # type: ignore[arg-type]
        contradictions=len(synthesis.contradictions),
        superseded_claims=len(synthesis.superseded),
        contradiction_pairs=[
            ContradictionPair(
                sources=sorted({item.side_a[0].record.source_id, item.side_b[0].record.source_id}),
                subject=item.subject,
            )
            for item in synthesis.contradictions
        ],
    )
    page = Page(path=path, frontmatter=frontmatter, body="\n".join(lines) + "\n")
    return page, footnotes.cited_locators()


def _contexts(
    pack: DomainPack,
    sources: Sequence[str],
    infos: Mapping[str, SourceInfo],
    tiers: Mapping[str, str],
    sensitivity: str,
    path: str,
    scope_of: Mapping[str, str | None] | None,
    amending: Mapping[str | None, Sequence[str]] | None,
) -> dict[str, ScopeContext]:
    """Source id → its scope's amending documents that this page may link: none of a higher tier
    than the page, whose tier stays the highest of its sources (gate G07)."""
    if not amending or scope_of is None:
        return {}
    contexts: dict[str, ScopeContext] = {}
    for source_id in sources:
        value = scope_of.get(source_id)
        label = scope_label(pack, value) if pack.scopes is not None and value else ""
        docs = tuple(
            (infos[sid], _source_link(infos[sid], path))
            for sid in amending.get(value, ())
            if allowed_for_audience(tiers[sid], sensitivity)  # type: ignore[arg-type]
        )
        contexts[source_id] = ScopeContext(label, docs)
    return contexts


def _claim_refs(claim: _Claim, footnotes: Footnotes) -> str:
    return footnotes.cite_all(c for fact in claim.facts for c in fact.record.citations)


def _meta(info: SourceInfo, t: Strings | None = None, with_status: bool = False) -> str:
    t = t or core_strings()
    parts = [t.status(info.status)] if with_status else []
    parts.append(t("topic.meta_authority", authority=info.authority))
    parts.append(
        t("topic.meta_dated", date=info.date.isoformat()) if info.date else t("topic.meta_undated")
    )
    return ", ".join(parts)


async def _synthesize(
    llm: LlmClient,
    topic: TopicDef,
    pack: DomainPack,
    sources: Sequence[str],
    labels: Mapping[str, str],
    facts: Sequence[_Fact],
    infos: Mapping[str, SourceInfo],
    scope: str | None = None,
) -> TopicSynthesisOutput | None:
    """The model's synthesis, or None when the call fails for this topic only."""
    metadata = {"stage": "topics", "topic": topic.slug}
    if scope is not None:
        metadata["scope"] = scope
    try:
        result = await llm.structured(
            tier="smart",
            system=load_prompt("topic-synthesis").text,
            user=_request(topic, pack, sources, labels, facts, infos, scope),
            output=TopicSynthesisOutput,
            schema_name=SCHEMA_NAME,
            prompt_version=PROMPT_VERSION,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            metadata=metadata,
        )
    except LlmError as exc:
        if is_systemic(exc):
            raise
        logger.warning(
            "topic %s: synthesis call failed (%s); the topic is skipped as insufficient_evidence",
            topic.slug if scope is None else f"{scope}/{topic.slug}",
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
    scopes = {
        sid: source_scope(pack, page.frontmatter)  # type: ignore[arg-type]
        for sid, page in source_pages.items()
        if sid in infos
    }
    scope_of: dict[str, str | None] = {
        sid: (scopes.get(sid) or pack.scopes.default.key) if pack.scopes is not None else None
        for sid in infos
    }
    # v1.7: the current documents of an amending type, per scope (resolution.yaml amendments)
    amending_types = {key for rule in pack.resolution.amendments for key in rule.amending}
    amending: dict[str | None, list[str]] = {}
    for sid in sorted(tiers, key=lambda sid: source_order(infos[sid])):
        info = infos[sid]
        if (
            info.doc_type in amending_types
            and info.status == "current"
            and allowed_for_audience(tiers[sid], audience)  # type: ignore[arg-type]
        ):
            amending.setdefault(scope_of[sid], []).append(sid)
    skips: list[TopicSkip] = []
    # (topic, scope) → why it was not written; one skip per per-scope topic without any page
    scoped_skips: dict[str, list[TopicSkip]] = {}
    jobs: list[tuple[TopicDef, str | None, list[str], dict[str, str], list[_Fact]]] = []

    def skip(topic: TopicDef, scope: str | None, reason: str, sources: Sequence[str]) -> None:
        item = TopicSkip(topic.slug, reason, tuple(sorted(sources)))  # type: ignore[arg-type]
        if scope is None:
            skips.append(item)
        else:
            scoped_skips.setdefault(topic.slug, []).append(item)

    for topic in pack.topics.topics:
        routed = feeding.get(topic.slug, [])
        minimum = topic.min_sources if topic.min_sources is not None else DEFAULT_MIN_SOURCES
        if topic.per_scope and pack.scopes is not None:
            # v1.7 (ADR 0011): one page per scope that has routed sources, from those only.
            groups: dict[str, list[str]] = {}
            for sid in routed:
                groups.setdefault(scopes.get(sid) or pack.scopes.default.key, []).append(sid)
            planned: list[tuple[str | None, list[str]]] = [
                (scope, groups[scope]) for scope in sorted(groups)
            ]
            if not planned:
                skips.append(TopicSkip(topic.slug, "insufficient_evidence", ()))
        else:
            planned = [(None, routed)]
        for scope, members in planned:
            allowed = [sid for sid in members if allowed_for_audience(tiers[sid], audience)]
            ordered = sorted(allowed, key=lambda sid: source_order(infos[sid]))
            if len(allowed) < minimum:
                reason = "audience" if len(members) >= minimum else "insufficient_evidence"
                skip(topic, scope, reason, allowed)
                continue
            if not any(infos[sid].status == "current" for sid in allowed):
                skip(topic, scope, "no_current_sources", allowed)
                continue
            labels = {source_id: f"S{number}" for number, source_id in enumerate(ordered, start=1)}
            facts = _select_facts(topic, ordered, records, infos)
            if not facts:
                skip(topic, scope, "insufficient_evidence", allowed)
                continue
            jobs.append((topic, scope, ordered, labels, facts))
    outputs = await asyncio.gather(
        *(
            _synthesize(llm, topic, pack, ordered, labels, facts, infos, scope)
            for topic, scope, ordered, labels, facts in jobs
        )
    )
    pages: list[Page] = []
    cited: list[CitedLocator] = []
    for (topic, scope, ordered, labels, facts), output in zip(jobs, outputs, strict=True):
        if output is None:
            skip(topic, scope, "insufficient_evidence", ordered)
            continue
        synthesis = _split_changes(_verify(output, facts, labels, infos), pack, infos, scope_of)
        if not (
            synthesis.overview
            or synthesis.sections
            or synthesis.contradictions
            or synthesis.changes
            or synthesis.superseded
        ):
            skip(topic, scope, "insufficient_evidence", ordered)
            continue
        page, locators = _render(
            topic, ordered, synthesis, infos, tiers, pack, stamp, scope, scope_of, amending
        )
        pages.append(page)
        cited.extend(locators)
    written = {page.frontmatter.topic_slug for page in pages}  # type: ignore[union-attr]
    for slug, items in scoped_skips.items():
        if slug in written:
            continue  # some scopes have a page: the others simply have none
        reasons = {item.reason for item in items}
        reason = reasons.pop() if len(reasons) == 1 else "insufficient_evidence"
        sources = sorted({sid for item in items for sid in item.sources})
        skips.append(TopicSkip(slug, reason, tuple(sources)))  # type: ignore[arg-type]
    return pages, cited, skips
