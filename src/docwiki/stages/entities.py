"""Entity pages (pipeline.md §1 stage 5, wiki-contract §3–4).

One page per registry entity (pack + overlay) mentioned by at least one compiled source that has
a source page; an entity bound to one scope (v1.7) counts only the sources of that scope. Facts
are aggregated deterministically: the verified key facts whose text names the entity (label,
aliases or key, case- and accent-insensitive, on word boundaries), de-duplicated across sources
and ordered current sources first (authority, then title). Dated facts feed the
timeline. The optional introduction is written by the ``fast`` model from those facts only; each
sentence must cite fact ids, unknown ids are dropped and quantities must appear in the cited facts.
When that call fails for its request only (content filter, output invalid or truncated, see
:mod:`docwiki.stages.llm_failures`) the page keeps the deterministic introduction and a warning
is logged; systemic failures (auth, rate limits, timeouts…) propagate and stop the run.
``## Related`` and the backlinks block are added by the assemble lane before ``## Sources``.
"""

from __future__ import annotations

import asyncio
import logging
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date

from docwiki.contracts.enums import max_sensitivity
from docwiki.contracts.i18n import language_name
from docwiki.contracts.ids import entity_page_path, normalize_tags
from docwiki.contracts.markdown import relative_link
from docwiki.contracts.pages import (
    Alias,
    DocwikiStamp,
    EntityFrontmatter,
    Page,
    SourceFrontmatter,
)
from docwiki.domain import DomainPack
from docwiki.domain.models import RegistryEntry, locked_terms_note
from docwiki.domain.rules import document_scope, entity_in_scope, normalize_for_matching
from docwiki.engine_types import CitedLocator, CompiledResult, VerifiedCitation
from docwiki.llm import LlmClient, LlmError
from docwiki.stages.classify import data_nonce
from docwiki.stages.compile import entity_patterns
from docwiki.stages.hubs import scope_label
from docwiki.stages.llm_failures import describe_failure, is_systemic
from docwiki.stages.models import EntitySummaryOutput, FactRecord, SourceInfo
from docwiki.stages.prompts import load_prompt
from docwiki.stages.render import (
    Footnotes,
    attach_refs,
    banner_line,
    clean_inline,
    clean_title,
    fact_key,
    fact_records,
    release_date,
    source_infos,
)
from docwiki.stages.verify_citations import split_sentences, unsigned_values, unsupported_quantities

__all__ = [
    "MAX_SUMMARY_FACTS",
    "PROMPT_VERSION",
    "STAGE_VERSION",
    "build_entity_pages",
    "fact_date",
    "unsupported_validity",
]

STAGE_VERSION = "5"
PROMPT_VERSION = load_prompt("entity-summary").version
SCHEMA_NAME = "entity_summary"
MAX_SUMMARY_FACTS = 40
MAX_SUMMARY_SENTENCES = 3
MAX_OUTPUT_TOKENS = 4_000
"""Output budget of one summary call: the answer is a few sentences, the rest is headroom for
the reasoning tokens of reasoning models (``docwiki.llm`` exposes no reasoning-effort setting)."""

logger = logging.getLogger("docwiki.stages.entities")

_MONTHS = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}
_MONTH_NAMES = r"(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sept|sep|oct|nov|dec)"  # noqa: E501
_DATE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ymd", re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")),
    ("ym", re.compile(r"\b(\d{4})-(\d{2})\b(?!-\d)")),
    ("dmy", re.compile(rf"\b(\d{{1,2}})\s+{_MONTH_NAMES}\.?\s+(\d{{4}})\b", re.IGNORECASE)),
    ("mdy", re.compile(rf"\b{_MONTH_NAMES}\.?\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE)),
    ("my", re.compile(rf"\b{_MONTH_NAMES}\.?\s+(\d{{4}})\b", re.IGNORECASE)),
)


def _month(name: str) -> int:
    lowered = name.lower()
    for full, number in _MONTHS.items():
        if full.startswith(lowered[:3]):
            return number
    raise ValueError(name)  # pragma: no cover - the regex only admits month names


def _valid(year: int, month: int, day: int | None = None) -> bool:
    if not (1900 <= year <= 2100 and 1 <= month <= 12):
        return False
    if day is None:
        return True
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def fact_date(text: str) -> str | None:
    """First date stated in a fact, as ``YYYY-MM-DD`` or ``YYYY-MM`` (bare years are ignored)."""
    found: list[tuple[int, int, str]] = []
    for kind, pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            groups = match.groups()
            if kind == "ymd":
                year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            elif kind == "ym":
                year, month, day = int(groups[0]), int(groups[1]), None
            elif kind == "dmy":
                day, month, year = int(groups[0]), _month(groups[1]), int(groups[2])
            elif kind == "mdy":
                month, day, year = _month(groups[0]), int(groups[1]), int(groups[2])
            else:
                month, year, day = _month(groups[0]), int(groups[1]), None
            if not _valid(year, month, day):
                continue
            value = f"{year:04d}-{month:02d}" + (f"-{day:02d}" if day is not None else "")
            found.append((match.start(), -len(match.group(0)), value))
    return min(found)[2] if found else None


@dataclass
class _EntityFact:
    text: str
    citations: list[VerifiedCitation] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    numbers: list[str] = field(default_factory=list)
    superseded: bool = False
    date: str | None = None


def _citation_key(citation: VerifiedCitation) -> tuple[str, str, str]:
    locator = citation.locator.model_dump_json() if citation.locator else ""
    return (citation.source_id, locator, citation.status)


def source_order(info: SourceInfo) -> tuple[int, int, str, str]:
    """Current sources first, then higher authority, then title."""
    return (0 if info.status == "current" else 1, -info.authority, info.title, info.source_id)


def _names_entity(patterns: Sequence[re.Pattern[str]], text: str) -> bool:
    normalized = normalize_for_matching(text)
    return any(pattern.search(normalized) for pattern in patterns)


def _aggregate(
    entry: RegistryEntry,
    sources: Sequence[str],
    records: Mapping[str, list[FactRecord]],
    infos: Mapping[str, SourceInfo],
) -> list[_EntityFact]:
    patterns = entity_patterns(entry)
    facts: dict[str, _EntityFact] = {}
    for source_id in sources:
        superseded = infos[source_id].status != "current"
        for record in records.get(source_id, []):
            if not _names_entity(patterns, record.text):
                continue
            key = fact_key(record.text)
            fact = facts.get(key)
            if fact is None:
                fact = facts[key] = _EntityFact(
                    text=record.text, superseded=superseded, date=fact_date(record.text)
                )
            elif not superseded:
                fact.superseded = False
            if source_id not in fact.sources:
                fact.sources.append(source_id)
            fact.numbers.extend(n for n in record.numbers if n not in fact.numbers)
            seen = {_citation_key(citation) for citation in fact.citations}
            for citation in record.citations:
                if _citation_key(citation) not in seen:
                    seen.add(_citation_key(citation))
                    fact.citations.append(citation)
    ordered = list(facts.values())
    return [fact for fact in ordered if not fact.superseded] + [
        fact for fact in ordered if fact.superseded
    ]


def _summary_request(
    entry: RegistryEntry,
    type_title: str,
    facts: Sequence[_EntityFact],
    infos: Mapping[str, SourceInfo],
    locked: str = "",
    lang: str = "en",
    scopes: Mapping[str, str] | None = None,
) -> str:
    lines = [
        "# Task",
        "Write the introduction of the entity page described below.",
        f"Wiki language: {language_name(lang)}.",
        "",
        "# Entity (reviewed registry)",
        f"- id: {entry.id}",
        f"- type: {type_title}",
        f"- label: {entry.label}",
    ]
    if entry.aliases:
        lines.append(
            "- aliases: " + ", ".join(f"{alias.text} [{alias.lang}]" for alias in entry.aliases)
        )
    fact_lines: list[str] = []
    for number, fact in enumerate(facts[:MAX_SUMMARY_FACTS], start=1):
        source = infos[fact.sources[0]]
        parts = [source.title, "superseded" if fact.superseded else "current"]
        parts.append(f"dated {source.date.isoformat()}" if source.date else "undated")
        scope = (scopes or {}).get(source.source_id)
        if scope:
            parts.append(f"scope: {scope}")
        fact_lines.append(f"[F{number}] ({', '.join(parts)}) {fact.text}")
    if locked:
        lines += ["", "# Vocabulary (reviewed domain pack)", locked]
    body = "\n".join(fact_lines)
    nonce = data_nonce(body)
    lines += ["", "# Facts", f"BEGIN FACTS {nonce}", body, f"END FACTS {nonce}"]
    return "\n".join(lines)


async def _summarize(
    llm: LlmClient,
    entry: RegistryEntry,
    type_title: str,
    facts: Sequence[_EntityFact],
    infos: Mapping[str, SourceInfo],
    locked: str = "",
    lang: str = "en",
    scopes: Mapping[str, str] | None = None,
) -> EntitySummaryOutput | None:
    """The model's introduction, or None without facts or when the call fails for this entity."""
    if not facts:
        return None
    try:
        result = await llm.structured(
            tier="fast",
            system=load_prompt("entity-summary").text,
            user=_summary_request(entry, type_title, facts, infos, locked, lang, scopes),
            output=EntitySummaryOutput,
            schema_name=SCHEMA_NAME,
            prompt_version=PROMPT_VERSION,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            metadata={"stage": "entities", "entity_id": entry.id},
        )
    except LlmError as exc:
        if is_systemic(exc):
            raise
        logger.warning(
            "entity %s: summary call failed (%s); the page keeps the deterministic introduction",
            entry.id,
            describe_failure(exc),
        )
        return None
    return result.output


def _summary_sentences(
    output: EntitySummaryOutput | None, facts: Sequence[_EntityFact]
) -> list[tuple[str, list[_EntityFact]]]:
    if output is None:
        return []
    usable = list(facts[:MAX_SUMMARY_FACTS])
    sentences: list[tuple[str, list[_EntityFact]]] = []
    for sentence in output.sentences:
        text = clean_inline(sentence.text)
        cited: list[_EntityFact] = []
        for raw in sentence.fact_ids:
            match = re.fullmatch(r"\s*\[?f(\d+)\]?\s*", raw, re.IGNORECASE)
            if not match:
                continue
            position = int(match.group(1)) - 1
            if 0 <= position < len(usable) and usable[position] not in cited:
                cited.append(usable[position])
        if not text or not cited:
            continue
        support = unsigned_values([part for fact in cited for part in (fact.text, *_numbers(fact))])
        kept = [
            piece.strip()
            for piece in split_sentences(text)
            if not unsupported_quantities(piece, support)
        ]
        text = " ".join(piece for piece in kept if piece and not unsupported_validity(piece))
        if text:
            sentences.append((text, cited))
        if len(sentences) == MAX_SUMMARY_SENTENCES:
            break
    return sentences


_VALIDITY_RE = re.compile(
    r"\b(?:valables?|valides?|en cours de validité|en règle|valid|in force|up to date)\b",
    re.IGNORECASE,
)


def unsupported_validity(sentence: str) -> bool:
    """A model sentence that calls documents valid without a single date or duration (v1.7,
    slice G): "ses attestations sont valables" hides an expiry the facts may show, so it is
    dropped; "valable jusqu'au 31/12/2026" stays."""
    return bool(_VALIDITY_RE.search(sentence)) and not re.search(r"\d", sentence)


def _numbers(fact: _EntityFact) -> list[str]:
    quotes = [citation.quote for citation in fact.citations if citation.quote]
    return [*fact.numbers, *quotes]


def _render(
    entry: RegistryEntry,
    type_title: str,
    sources: Sequence[str],
    facts: Sequence[_EntityFact],
    summary: Sequence[tuple[str, list[_EntityFact]]],
    infos: Mapping[str, SourceInfo],
    pack: DomainPack,
    stamp: DocwikiStamp,
) -> tuple[Page, list[CitedLocator]]:
    path = entity_page_path(entry.id)
    t = pack.strings()
    footnotes = Footnotes(path, {sid: info.title for sid, info in infos.items()}, t)
    title = clean_title(entry.label) or entry.label
    lines = [f"# {title}", ""]
    banner = banner_line(pack)
    if banner:
        lines += [banner, ""]
    if summary:
        intro = " ".join(
            attach_refs(text, footnotes.cite_all(c for fact in cited for c in fact.citations))
            for text, cited in summary
        )
        plain = " ".join(text for text, _ in summary)
    else:
        count = len(sources)
        plain = t.count("entity.intro", count, title=title, type_title=type_title.lower())
        intro = plain
    lines += [intro, "", f"## {t.heading('facts')}", ""]
    if facts:
        for fact in facts:
            text = t("entity.superseded_fact", text=fact.text) if fact.superseded else fact.text
            lines.append(f"- {attach_refs(text, footnotes.cite_all(fact.citations))}")
    else:
        lines.append(t("entity.no_facts"))
    lines += ["", f"## {t.heading('timeline')}", ""]
    dated = sorted(
        (fact for fact in facts if fact.date), key=lambda fact: (fact.date or "", fact.text)
    )
    if dated:
        for fact in dated:
            lines.append(
                f"- {fact.date}: {attach_refs(fact.text, footnotes.cite_all(fact.citations))}"
            )
    else:
        lines.append(t("entity.no_dated"))
    lines += ["", f"## {t.heading('documents')}", ""]
    for source_id in sorted(sources, key=lambda sid: source_order(infos[sid])):
        info = infos[source_id]
        suffix = t("entity.superseded_suffix") if info.status == "superseded" else ""
        lines.append(f"- [{info.title}]({relative_link(path, info.path)}){suffix}")
    lines += ["", *footnotes.sources_section()]
    aliases: list[Alias] = []
    for alias in entry.aliases:
        candidate = Alias(text=alias.text, lang=alias.lang)
        if candidate not in aliases:
            aliases.append(candidate)
    summary_line = clean_inline(plain)
    if len(summary_line) > 300:
        summary_line = summary_line[:299].rsplit(" ", 1)[0] + "…"
    frontmatter = EntityFrontmatter(
        id=entry.id,
        title=title,
        summary=summary_line,
        lang=pack.canonical_lang,
        sensitivity=max_sensitivity(*(infos[sid].sensitivity for sid in sources)),  # type: ignore[arg-type]
        updated=release_date(stamp),
        tags=normalize_tags([entry.type]),
        docwiki=stamp,
        entity_type=entry.type,
        key=entry.key,
        aliases=aliases,
        sources=sorted(sources),
    )
    page = Page(path=path, frontmatter=frontmatter, body="\n".join(lines) + "\n")
    return page, footnotes.cited_locators()


def _source_scopes(source_pages: Mapping[str, Page], pack: DomainPack) -> dict[str, str | None]:
    """Source id → scope value of its document (``None`` without ``scopes.yaml``)."""
    scopes: dict[str, str | None] = {}
    for page in source_pages.values():
        fm = page.frontmatter
        if isinstance(fm, SourceFrontmatter):
            scopes[fm.source_id] = document_scope(pack, fm.scope, fm.source_path)
    return scopes


async def build_entity_pages(
    results: Sequence[CompiledResult],
    source_pages: Mapping[str, Page],
    pack: DomainPack,
    llm: LlmClient,
    *,
    stamp: DocwikiStamp,
) -> tuple[list[Page], list[CitedLocator]]:
    """Entity pages for every registry entity mentioned by a compiled source with a page.

    An entity bound to one scope (its registry attribute named after the pack's scope dimension)
    counts only the sources of that scope: a document of another scope that shares its names does
    not mention it (v1.7, ADR 0011)."""
    infos = source_infos(source_pages, results)
    by_source = {result.source_id: result for result in results if result.source_id in infos}
    records = {source_id: fact_records(result) for source_id, result in by_source.items()}
    type_titles = {entity_type.key: entity_type.title for entity_type in pack.entities.types}
    scopes = _source_scopes(source_pages, pack)
    scope_labels = {
        sid: scope_label(pack, value) for sid, value in scopes.items() if value is not None
    }
    jobs: list[tuple[RegistryEntry, list[str], list[_EntityFact]]] = []
    for entry in pack.entities.registry:
        sources = [
            source_id
            for source_id, result in sorted(by_source.items())
            if entity_in_scope(pack, entry, scopes.get(source_id))
            and any(mention.entity_id == entry.id for mention in result.compiled.entity_mentions)
        ]
        if not sources:
            continue
        ordered = sorted(sources, key=lambda sid: source_order(infos[sid]))
        jobs.append((entry, sources, _aggregate(entry, ordered, records, infos)))
    outputs = await asyncio.gather(
        *(
            _summarize(
                llm,
                entry,
                type_titles.get(entry.type, entry.type),
                facts,
                infos,
                locked_terms_note(pack),
                pack.canonical_lang,
                scope_labels,
            )
            for entry, _, facts in jobs
        )
    )
    pages: list[Page] = []
    cited: list[CitedLocator] = []
    for (entry, sources, facts), output in zip(jobs, outputs, strict=True):
        page, locators = _render(
            entry,
            type_titles.get(entry.type, entry.type),
            sources,
            facts,
            _summary_sentences(output, facts),
            infos,
            pack,
            stamp,
        )
        pages.append(page)
        cited.extend(locators)
    return pages, cited
