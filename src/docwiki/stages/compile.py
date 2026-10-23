"""Compile stage (pipeline.md §3): one source → verified ``CompiledSource``, citations, proposals.

Flow: the document is rendered as delimited data (blocks ``[b0042]``, table rows ``t03:r0012``,
figures ``[f02]``) → one ``smart`` structured-output call returning the contracts
``CompiledSource`` (map-reduce above ``SINGLE_PASS_MAX_TOKENS``: chunks of at most
``MAP_CHUNK_MAX_TOKENS`` on block boundaries, partial results merged by a reduce call) →
deterministic cleaning and citation verification (evidence-contract §4, see
:mod:`docwiki.stages.verify_citations`) → one repair call for the facts left without a valid
citation, then those still failing are dropped → entity, glossary and injection proposals. The
repair call is best effort: when it fails for that request only (content filter, output still
invalid or truncated, see :mod:`docwiki.stages.llm_failures`) the verified result is kept, the
failing facts stay dropped and ``usage["warnings"]`` says so; systemic failures propagate.

Injection flags are the model's flags (text that tries to instruct an AI system, as defined by
the ``compile`` prompt) plus the findings of :func:`docwiki.contracts.safety.detect_injection` on
every block. The stage trusts the model's flags, with one deterministic exception: a flag on a
block made only of words of the domain pack banner (``pack.yaml`` ``banner``, a notice for human
readers) is dropped and ``usage["warnings"]`` records it.

``CompiledResult.citations`` refs: ``kf<N>`` are the citations of key fact N (1-based) of the
final ``compiled.key_facts`` in the order of ``fact.citations``; ``s<N>`` are the ``[[cite:…]]``
markers of final section N in body order; ``kf-failed`` and ``s-failed`` are citations that failed
verification (removed from the output, kept for gate statistics).

``CompiledResult.usage`` holds the LLM calls (tokens per call, prompt versions; failed calls carry
an ``error``), the map-reduce shape, verification counts, ``warnings`` and ``doc_date`` (the
extractor's ``authored`` date, used by topic pages for recency). ``EntityMention.block_ids`` may
contain table rows (``t03:r0012``). A document without any extracted content is not sent to a
model: its result has no facts and its summary says so (``usage["empty_document"]``).
"""

from __future__ import annotations

import asyncio
import json
import posixpath
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from docwiki.contracts.compiled import (
    Citation,
    CompiledSection,
    CompiledSource,
    EntityMention,
    GlossaryCandidate,
    InjectionFlag,
    KeyFact,
    UnknownEntity,
)
from docwiki.contracts.extracted import Block, ExtractedDoc, Figure, Table
from docwiki.contracts.i18n import language_name
from docwiki.contracts.ids import is_entity_id, parse_entity_id, slugify_ascii
from docwiki.contracts.locators import locator_label
from docwiki.contracts.proposals import (
    EntityProposalPayload,
    GlossaryProposalPayload,
    InjectionProposalPayload,
    Proposal,
    ProposalEvidence,
    new_proposal,
)
from docwiki.contracts.safety import detect_injection
from docwiki.domain import DomainPack
from docwiki.domain.models import RegistryEntry, locked_terms_note
from docwiki.domain.rules import normalize_for_matching
from docwiki.engine_types import Classification, CompiledResult, VerifiedCitation
from docwiki.llm import LlmClient, LlmError, StructuredResult
from docwiki.stages.classify import data_nonce
from docwiki.stages.llm_failures import describe_failure, is_systemic
from docwiki.stages.models import FactRepairOutput
from docwiki.stages.prompts import combine_prompts, load_prompt
from docwiki.stages.render import clean_block_markdown, clean_inline, clean_title, fact_key
from docwiki.stages.verify_citations import (
    CitationCheck,
    CitationRefError,
    DocIndex,
    FactCheck,
    MarkerCheck,
    split_sentences,
    unsupported_quantities,
    verify_fact,
    verify_section_body,
)

__all__ = [
    "CHARS_PER_TOKEN",
    "MAP_CHUNK_MAX_TOKENS",
    "PROMPT_VERSION",
    "PROMPT_VERSIONS",
    "SINGLE_PASS_MAX_TOKENS",
    "STAGE_VERSION",
    "DataUnit",
    "chunk_units",
    "compile_source",
    "data_units",
    "detect_mentions",
]

STAGE_VERSION = "7"
CHARS_PER_TOKEN = 4
SINGLE_PASS_MAX_TOKENS = 24_000
MAP_CHUNK_MAX_TOKENS = 12_000
REDUCE_MAX_INPUT_TOKENS = 24_000
MAX_TABLE_ROWS_IN_PROMPT = 400
REGISTRY_PROMPT_LIMIT = 300
REPAIR_WINDOW_BLOCKS = 3
COMPILE_MAX_OUTPUT_TOKENS = 16_000
# Reasoning models count their reasoning tokens against this budget: at 8,000 the map calls
# on dense chunks (a 12,000-token slice of an alarm log) ran out before the JSON was complete.
MAP_MAX_OUTPUT_TOKENS = 16_000
# A reduce re-emits the facts and sections of up to REDUCE_MAX_INPUT_TOKENS of partials: at
# 16,000 the merge of an alarm log's partials ran out before the JSON was complete.
REDUCE_MAX_OUTPUT_TOKENS = 32_000
REPAIR_MAX_OUTPUT_TOKENS = 4_000
MAX_MENTION_REFS = 50
MAX_PROPOSAL_EVIDENCE = 10

_PROMPT_NAMES = ("compile", "compile-map", "compile-reduce", "compile-repair")
PROMPT_VERSIONS: dict[str, str] = {name: load_prompt(name).version for name in _PROMPT_NAMES}
PROMPT_VERSION = "+".join(PROMPT_VERSIONS[name] for name in _PROMPT_NAMES)
"""Combined version of every prompt the stage may use (for the stage cache key)."""

EMPTY_SUMMARY = "No text, table or figure could be extracted from this document."
EMPTY_OUTPUT = CompiledSource(
    title="",
    summary="",
    key_facts=[],
    sections=[],
    entity_mentions=[],
    unknown_entities=[],
    glossary_candidates=[],
    injection_flags=[],
)
"""Stand-in model output for documents without extracted content (no model call is made)."""


def _now() -> datetime:
    """Proposal timestamp (the only clock read of the stage; tests patch it)."""
    return datetime.now(UTC).replace(microsecond=0)


# --------------------------------------------------------------------------- document data


@dataclass(frozen=True)
class DataUnit:
    """One piece of the document data section: a block, a run of table rows or a figure."""

    text: str
    block_ids: tuple[str, ...] = ()
    table_id: str | None = None
    row_ids: tuple[str, ...] = ()
    figure_id: str | None = None

    @property
    def size(self) -> int:
        return len(self.text) + 1


def _flat(text: str) -> str:
    return " ".join(text.split())


def _indent(text: str) -> str:
    return "\n".join(f"  {line.rstrip()}" for line in text.split("\n"))


def _block_units(block: Block, max_chars: int) -> list[DataUnit]:
    text = block.text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not text.strip():
        return []
    kind = block.kind + (f" {block.level}" if block.level else "")
    extra = "" if block.provenance == "native-text" else f" · {block.provenance}"
    label = locator_label(block.locator)
    pieces: list[str] = []
    current = ""
    for line in text.split("\n"):
        while len(line) > max_chars:
            if current:
                pieces.append(current)
                current = ""
            pieces.append(line[:max_chars])
            line = line[max_chars:]
        if current and len(current) + len(line) + 1 > max_chars:
            pieces.append(current)
            current = ""
        current = f"{current}\n{line}" if current else line
    if current:
        pieces.append(current)
    units: list[DataUnit] = []
    for position, piece in enumerate(pieces):
        marker = "" if position == 0 else " (continued)"
        header = f"[{block.id}] {kind}{marker} · {label}{extra}"
        units.append(DataUnit(f"{header}\n{_indent(piece)}", block_ids=(block.id,)))
    return units


def _table_units(table: Table, max_chars: int) -> list[DataUnit]:
    extra = "" if table.provenance == "deterministic-table" else f" · {table.provenance}"
    label = locator_label(table.locator)
    columns = "  columns: " + " | ".join(_flat(column) for column in table.columns)
    shown = table.rows[:MAX_TABLE_ROWS_IN_PROMPT]
    groups: list[list[tuple[str, str]]] = [[]]
    size = len(columns) + 80
    for row in shown:
        line = f"  {table.id}:{row.row_id}: " + " | ".join(_flat(cell) for cell in row.cells)
        if groups[-1] and size + len(line) + 1 > max_chars:
            groups.append([])
            size = len(columns) + 80
        groups[-1].append((line, row.row_id))
        size += len(line) + 1
    units: list[DataUnit] = []
    for position, group in enumerate(groups):
        marker = "" if position == 0 else " (continued)"
        lines = [f"[{table.id}] table{marker} · {label}{extra}", columns]
        lines += [line for line, _ in group]
        if position == len(groups) - 1 and len(table.rows) > len(shown):
            lines.append(
                f"  ({len(table.rows) - len(shown)} more rows are not shown; the page renders "
                "the full table from the extracted data)"
            )
        units.append(
            DataUnit(
                "\n".join(lines),
                table_id=table.id,
                row_ids=tuple(row_id for _, row_id in group),
            )
        )
    return units


def _figure_unit(figure: Figure) -> DataUnit:
    lines = [f"[{figure.id}] figure · {locator_label(figure.locator)}"]
    if figure.caption:
        lines.append(f"  caption: {_flat(figure.caption)}")
    if figure.description:
        lines.append(f"  generated description: {_flat(figure.description)}")
    if len(lines) == 1:
        lines.append("  (no caption or description)")
    return DataUnit("\n".join(lines), figure_id=figure.id)


def data_units(doc: ExtractedDoc, *, max_chars: int) -> list[DataUnit]:
    """Blocks in reading order, then tables (row groups), then figures."""
    units: list[DataUnit] = []
    for block in doc.blocks:
        units.extend(_block_units(block, max_chars))
    for table in doc.tables:
        units.extend(_table_units(table, max_chars))
    units.extend(_figure_unit(figure) for figure in doc.figures)
    return units


def chunk_units(units: Sequence[DataUnit], max_chars: int) -> list[list[DataUnit]]:
    """Consecutive units packed into chunks of at most ``max_chars`` (never splits a unit)."""
    chunks: list[list[DataUnit]] = []
    current: list[DataUnit] = []
    size = 0
    for unit in units:
        if current and size + unit.size > max_chars:
            chunks.append(current)
            current, size = [], 0
        current.append(unit)
        size += unit.size
    if current:
        chunks.append(current)
    return chunks


def _data_section(doc: ExtractedDoc, units: Sequence[DataUnit], part: str | None = None) -> str:
    filename = posixpath.basename(doc.source_path)
    head = f"source: {doc.source_id} · {doc.media_type} · file {filename}"
    if doc.title_hint:
        head += f" · title hint: {_flat(doc.title_hint)}"
    if part:
        head += f" · {part}"
    body = "\n".join([head, *(unit.text for unit in units)])
    nonce = data_nonce(body)
    return f"BEGIN DOCUMENT DATA {nonce}\n{body}\nEND DOCUMENT DATA {nonce}"


# --------------------------------------------------------------------------- entities


@lru_cache(maxsize=8192)
def _name_pattern(name: str) -> re.Pattern[str] | None:
    words = normalize_for_matching(name).split()
    if not words or len("".join(words)) < 3:
        return None
    return re.compile(r"(?<!\w)" + r"\s+".join(re.escape(word) for word in words) + r"(?!\w)")


def entity_names(entry: RegistryEntry) -> list[str]:
    """Names an entity is recognised by: label, aliases, key and key with spaces."""
    names = [entry.label, *(alias.text for alias in entry.aliases), entry.key]
    names.append(entry.key.replace("-", " "))
    return list(dict.fromkeys(names))


def entity_patterns(entry: RegistryEntry) -> list[re.Pattern[str]]:
    patterns = (_name_pattern(name) for name in entity_names(entry))
    return [pattern for pattern in patterns if pattern is not None]


def detect_mentions(pack: DomainPack, doc: ExtractedDoc) -> dict[str, list[str]]:
    """Registry entities named in the document → block ids / table rows naming them."""
    texts: list[tuple[str, str]] = [
        (block.id, normalize_for_matching(block.text)) for block in doc.blocks if block.text
    ]
    for table in doc.tables:
        texts.extend(
            (f"{table.id}:{row.row_id}", normalize_for_matching(" | ".join(row.cells)))
            for row in table.rows
        )
    full = "\n".join(text for _, text in texts)
    found: dict[str, list[str]] = {}
    for entry in pack.entities.registry:
        patterns = [pattern for pattern in entity_patterns(entry) if pattern.search(full)]
        if not patterns:
            continue
        refs = [ref for ref, text in texts if any(pattern.search(text) for pattern in patterns)]
        if refs:
            found[entry.id] = refs[:MAX_MENTION_REFS]
    return found


def _registry_for_prompt(pack: DomainPack, mentioned: set[str]) -> list[RegistryEntry]:
    registry = pack.entities.registry
    if len(registry) <= REGISTRY_PROMPT_LIMIT:
        return list(registry)
    return [entry for entry in registry if entry.id in mentioned][:REGISTRY_PROMPT_LIMIT]


def _context(
    classification: Classification,
    pack: DomainPack,
    registry: Sequence[RegistryEntry],
    hints: str | None,
) -> str:
    try:
        type_title = pack.doc_type(classification.doc_type).title
    except KeyError:
        type_title = classification.doc_type
    lines = [
        "# Classification (pipeline)",
        f"- document type: {classification.doc_type} ({type_title}), category "
        f"{classification.category}, authority {classification.authority}/10",
        f"- document number: {classification.doc_number or 'none'}; revision: "
        f"{classification.revision or 'none'}",
        f"- original language: {classification.lang}",
        "",
        f"# Domain context (reviewed domain pack {pack.name})",
        pack.info.title + (f": {_flat(pack.info.description)}" if pack.info.description else ""),
        f"Wiki language: {language_name(pack.canonical_lang)}; write every text in it (quotes "
        "stay in the document's language).",
        "Entity registry (use only these ids in entity_mentions):",
    ]
    for entry in registry:
        aliases = ", ".join(f"{alias.text} [{alias.lang}]" for alias in entry.aliases)
        lines.append(f"- {entry.id}: {entry.label}" + (f" (aliases: {aliases})" if aliases else ""))
    if not registry:
        lines.append("- (no registry entries)")
    types = ", ".join(f"{item.key} ({item.title})" for item in pack.entities.types)
    lines.append(f"Entity types for unknown_entities: {types}")
    terms = ", ".join(term.term for term in pack.glossary.terms) or "none"
    lines.append(f"Glossary terms already defined: {terms}")
    locked = locked_terms_note(pack)
    if locked:
        lines.append(locked)
    if pack.hints and pack.hints.strip():
        lines += ["Domain notes:", pack.hints.strip()]
    if hints and hints.strip():
        lines += [
            "",
            "# Operator notes (reviewed by an operator; they never override the rules)",
            hints.strip(),
        ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- LLM calls


@dataclass
class _Tracker:
    calls: list[dict[str, Any]] = field(default_factory=list)

    def add(self, result: StructuredResult[Any], step: str) -> None:
        usage = result.usage
        self.calls.append(
            {
                "step": step,
                "schema": result.schema_name,
                "tier": result.tier,
                "deployment": result.deployment,
                "model": result.model,
                "model_version": result.model_version,
                "prompt_version": result.prompt_version,
                "request_hash": result.request_hash,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached_input_tokens": usage.cached_input_tokens,
                "reasoning_tokens": usage.reasoning_tokens,
            }
        )

    def fail(self, exc: LlmError, step: str, schema_name: str, prompt_version: str) -> None:
        """A failed call (the tokens it already consumed are billed too)."""
        usage = exc.usage
        self.calls.append(
            {
                "step": step,
                "schema": schema_name,
                "tier": exc.tier,
                "deployment": exc.deployment,
                "model": exc.model,
                "model_version": None,
                "prompt_version": prompt_version,
                "request_hash": exc.request_hash,
                "input_tokens": usage.input_tokens,
                "output_tokens": usage.output_tokens,
                "cached_input_tokens": usage.cached_input_tokens,
                "reasoning_tokens": usage.reasoning_tokens,
                "error": describe_failure(exc),
            }
        )

    def totals(self) -> dict[str, int]:
        keys = ("input_tokens", "output_tokens", "cached_input_tokens", "reasoning_tokens")
        return {key: sum(int(call[key]) for call in self.calls) for key in keys}

    def ordered(self) -> list[dict[str, Any]]:
        """Calls in pipeline order (map and reduce calls finish in any order)."""
        phases = {"single": 0, "map": 1, "reduce": 2, "repair": 3}

        def key(call: dict[str, Any]) -> tuple[int, tuple[int, ...]]:
            name, *numbers = str(call["step"]).split("-")
            return phases.get(name, 9), tuple(int(n) for n in numbers if n.isdigit())

        return sorted(self.calls, key=key)


@dataclass
class _Job:
    doc: ExtractedDoc
    classification: Classification
    pack: DomainPack
    llm: LlmClient
    index: DocIndex
    context: str
    units: list[DataUnit]
    tracker: _Tracker
    warnings: list[str] = field(default_factory=list)

    def metadata(self, step: str) -> dict[str, Any]:
        return {"stage": "compile", "source_id": self.doc.source_id, "step": step}


async def _call(
    job: _Job,
    *,
    prompts: Sequence[str],
    user: str,
    output: type[Any],
    schema_name: str,
    max_output_tokens: int,
    step: str,
) -> Any:
    system, version = combine_prompts(*prompts)
    try:
        result = await job.llm.structured(
            tier="smart",
            system=system,
            user=user,
            output=output,
            schema_name=schema_name,
            prompt_version=version,
            max_output_tokens=max_output_tokens,
            metadata=job.metadata(step),
        )
    except LlmError as exc:
        job.tracker.fail(exc, step, schema_name, version)
        raise
    job.tracker.add(result, step)
    return result.output


async def _compile_single(job: _Job) -> CompiledSource:
    user = "\n\n".join(
        [
            "# Task\nCompile the document below into the JSON schema.",
            job.context,
            "# Document data\n" + _data_section(job.doc, job.units),
        ]
    )
    return await _call(
        job,
        prompts=("compile",),
        user=user,
        output=CompiledSource,
        schema_name="compile",
        max_output_tokens=COMPILE_MAX_OUTPUT_TOKENS,
        step="single",
    )


async def _compile_part(job: _Job, chunk: Sequence[DataUnit], number: int, total: int) -> Any:
    part = f"part {number} of {total}"
    user = "\n\n".join(
        [
            f"# Task\nCompile {part} of the document into the JSON schema.",
            job.context,
            "# Document data\n" + _data_section(job.doc, chunk, part),
        ]
    )
    return await _call(
        job,
        prompts=("compile", "compile-map"),
        user=user,
        output=CompiledSource,
        schema_name="compile_map",
        max_output_tokens=MAP_MAX_OUTPUT_TOKENS,
        step=f"map-{number}",
    )


def _partial_json(partial: CompiledSource) -> str:
    return json.dumps(partial.to_json_dict(), ensure_ascii=False, separators=(",", ":"))


# Lists of the partial results that the merged result gets from the map outputs in code (see
# :func:`_map_reduce`): the reduce calls neither read nor re-emit them.
_UNION_FIELDS = ("entity_mentions", "unknown_entities", "glossary_candidates", "injection_flags")


def _for_reduce(partial: CompiledSource) -> CompiledSource:
    """A partial result without the union lists, as sent to a reduce call."""
    return partial.model_copy(update={name: [] for name in _UNION_FIELDS})


def _group_partials(partials: Sequence[CompiledSource], max_chars: int) -> list[list[int]]:
    groups: list[list[int]] = []
    current: list[int] = []
    size = 0
    for position, partial in enumerate(partials):
        length = len(_partial_json(partial))
        if current and len(current) >= 2 and size + length > max_chars:
            groups.append(current)
            current, size = [], 0
        current.append(position)
        size += length
    if current:
        if len(current) == 1 and groups:
            groups[-1].append(current[0])
        else:
            groups.append(current)
    return groups


async def _reduce_group(
    job: _Job, partials: Sequence[CompiledSource], round_number: int, group: int
) -> CompiledSource:
    if len(partials) == 1:
        return partials[0]
    parts = [f"## Part {number}\n{_partial_json(p)}" for number, p in enumerate(partials, 1)]
    body = "\n".join(parts)
    nonce = data_nonce(body)
    user = "\n\n".join(
        [
            "# Task\nMerge the partial compilations below into one compilation of the whole "
            "document.",
            job.context,
            f"# Partial results\nBEGIN PARTIAL RESULTS {nonce}\n{body}\nEND PARTIAL RESULTS "
            f"{nonce}",
        ]
    )
    return await _call(
        job,
        prompts=("compile", "compile-reduce"),
        user=user,
        output=CompiledSource,
        schema_name="compile_reduce",
        max_output_tokens=REDUCE_MAX_OUTPUT_TOKENS,
        step=f"reduce-{round_number}-{group}",
    )


async def _map_reduce(job: _Job, chunks: Sequence[Sequence[DataUnit]]) -> CompiledSource:
    partials = list(
        await asyncio.gather(
            *(
                _compile_part(job, chunk, number, len(chunks))
                for number, chunk in enumerate(chunks, start=1)
            )
        )
    )
    partials = [_prune_partial(job.index, partial) for partial in partials]
    originals = list(partials)
    # The union lists come from the map outputs below; the reduce calls only merge the title,
    # summary, key facts and sections (smaller inputs and outputs).
    partials = [_for_reduce(partial) for partial in partials]
    budget = REDUCE_MAX_INPUT_TOKENS * CHARS_PER_TOKEN
    round_number = 0
    while len(partials) > 1:
        round_number += 1
        groups = _group_partials(partials, budget)
        partials = list(
            await asyncio.gather(
                *(
                    _reduce_group(job, [partials[i] for i in group], round_number, number)
                    for number, group in enumerate(groups, start=1)
                )
            )
        )
    merged = partials[0]
    return merged.model_copy(
        update={
            "entity_mentions": [
                *merged.entity_mentions,
                *(item for p in originals for item in p.entity_mentions),
            ],
            "unknown_entities": [
                *merged.unknown_entities,
                *(item for p in originals for item in p.unknown_entities),
            ],
            "glossary_candidates": [
                *merged.glossary_candidates,
                *(item for p in originals for item in p.glossary_candidates),
            ],
            "injection_flags": [
                *merged.injection_flags,
                *(item for p in originals for item in p.injection_flags),
            ],
        }
    )


def _prune_partial(index: DocIndex, partial: CompiledSource) -> CompiledSource:
    """Partial result keeping only facts that verify (canonical ids), before the reduce."""
    kept: list[KeyFact] = []
    for fact in partial.key_facts:
        cleaned = _clean_fact(fact)
        if cleaned is None:
            continue
        check = verify_fact(index, cleaned)
        if check.kept:
            kept.append(check.fact)
    return partial.model_copy(update={"key_facts": kept})


# --------------------------------------------------------------------------- repair


def _nearest_position(order: Sequence[str], number: int) -> int:
    """Position of the block whose number is closest to ``number`` (ids are ``b<digits>``)."""
    return min(range(len(order)), key=lambda i: (abs(int(order[i][1:]) - number), i))


def _repair_units(job: _Job, dropped: Sequence[FactCheck]) -> list[DataUnit]:
    budget = SINGLE_PASS_MAX_TOKENS * CHARS_PER_TOKEN
    if sum(unit.size for unit in job.units) <= budget:
        return job.units
    index = job.index
    wanted_blocks: set[str] = set()
    wanted_tables: set[str] = set()
    order = list(index.blocks)
    for check in dropped:
        for citation in check.checks:
            for token in re.split(r"[\s,;+&]+", citation.raw_id.lower()):
                table_match = re.match(r"t(\d+)", token)
                table_id = index.table_id(f"t{table_match.group(1)}") if table_match else None
                if table_id is not None:
                    wanted_tables.add(table_id)
                block_match = re.fullmatch(r"b(\d+)", token)
                if not block_match or not order:
                    continue
                number = int(block_match.group(1))
                position = _nearest_position(order, number)
                low = max(0, position - REPAIR_WINDOW_BLOCKS)
                wanted_blocks.update(order[low : position + REPAIR_WINDOW_BLOCKS + 1])
        values: set[str] = set()
        for raw in check.fact.numbers:
            values |= {value.removeprefix("-") for value in index.numbers(raw)}
        if values:
            for block_id, extracted in index.blocks.items():
                found = {value.removeprefix("-") for value in index.numbers(extracted.text)}
                if found & values:
                    wanted_blocks.add(block_id)
    selected: list[DataUnit] = []
    size = 0
    for unit in job.units:
        wanted = bool(set(unit.block_ids) & wanted_blocks) or unit.table_id in wanted_tables
        if wanted and size + unit.size <= budget:
            selected.append(unit)
            size += unit.size
    return selected or job.units[:1]


async def _repair(job: _Job, dropped: Sequence[FactCheck]) -> list[FactCheck | None]:
    """One repair call for the dropped facts; returns the new check per dropped fact."""
    lines = ["# Facts to repair"]
    for number, check in enumerate(dropped, start=1):
        lines.append(f"{number}. {check.fact.text}")
        lines.append(f"   numbers: {json.dumps(list(check.fact.numbers), ensure_ascii=False)}")
        for citation in check.checks:
            quote = json.dumps(citation.quote, ensure_ascii=False)
            lines.append(f"   - citation {citation.raw_id}, quote {quote}: {citation.reason}")
        if check.reason:
            lines.append(f"   fact rejected: {check.reason}")
    user = "\n\n".join(
        [
            "# Task\nRepair the facts below that failed verification.",
            job.context,
            "\n".join(lines),
            "# Document data\n" + _data_section(job.doc, _repair_units(job, dropped)),
        ]
    )
    output: FactRepairOutput = await _call(
        job,
        prompts=("compile", "compile-repair"),
        user=user,
        output=FactRepairOutput,
        schema_name="compile_repair",
        max_output_tokens=REPAIR_MAX_OUTPUT_TOKENS,
        step="repair",
    )
    repaired: list[FactCheck | None] = [None] * len(dropped)
    for item in output.facts:
        position = item.fact_number - 1
        if not 0 <= position < len(dropped) or repaired[position] is not None:
            continue
        fact = _clean_fact(
            KeyFact(text=item.text, citations=list(item.citations), numbers=list(item.numbers))
        )
        if fact is not None:
            repaired[position] = verify_fact(job.index, fact)
    return repaired


# --------------------------------------------------------------------------- cleaning


def _clean_fact(fact: KeyFact) -> KeyFact | None:
    text = clean_inline(fact.text)
    if not text:
        return None
    citations = [
        Citation(block_id=citation.block_id.strip(), quote=citation.quote)
        for citation in fact.citations
        if citation.block_id.strip()
    ]
    numbers = [" ".join(number.split()) for number in fact.numbers if number.strip()]
    return KeyFact(text=text, citations=citations, numbers=numbers)


def _guard_quantities(text: str, index: DocIndex) -> str:
    """Drop sentences stating quantities that appear nowhere in the document."""
    kept = [
        sentence
        for sentence in split_sentences(text)
        if not unsupported_quantities(sentence, index.all_numbers)
    ]
    return " ".join(sentence.strip() for sentence in kept).strip()


def _valid_refs(index: DocIndex, raw_ids: Sequence[str]) -> list[str]:
    refs: list[str] = []
    for raw in raw_ids:
        try:
            cited = index.resolve(raw)
        except CitationRefError:
            continue
        if cited.kind == "blocks":
            refs.extend(cited.block_ids)
        elif cited.kind == "table-rows":
            refs.extend(f"{cited.table_id}:{row_id}" for row_id in cited.row_ids)
    return list(dict.fromkeys(refs))


def _block_ids_only(refs: Sequence[str]) -> list[str]:
    return [ref for ref in refs if re.fullmatch(r"b\d{4,}", ref)]


def _ref_order(index: DocIndex, ref: str) -> tuple[int, int, str]:
    if ref in index.order:
        return (0, index.order[ref], ref)
    return (1, 0, ref)


def _excerpt(text: str, limit: int = 160) -> str:
    flat = _flat(text)
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _evidence(source_id: str, refs: Sequence[str]) -> list[ProposalEvidence]:
    return [
        ProposalEvidence(source_id=source_id, block_id=block_id)
        for block_id in _block_ids_only(refs)[:MAX_PROPOSAL_EVIDENCE]
    ]


def _mentions_and_entity_proposals(
    job: _Job, raw: CompiledSource
) -> tuple[list[EntityMention], list[UnknownEntity], list[Proposal]]:
    pack, index, doc = job.pack, job.index, job.doc
    known = {entry.id: entry for entry in pack.entities.registry}
    names: dict[str, str] = {}
    for entry in pack.entities.registry:
        for name in entity_names(entry):
            names.setdefault(normalize_for_matching(name), entry.id)
    refs: dict[str, list[str]] = {
        entity_id: list(found) for entity_id, found in detect_mentions(pack, doc).items()
    }
    payloads: dict[tuple[str, str], tuple[EntityProposalPayload, list[str]]] = {}
    for mention in raw.entity_mentions:
        entity_id = mention.entity_id.strip().lower()
        mention_refs = _valid_refs(index, mention.block_ids)
        if entity_id in known:
            if mention_refs:
                merged = refs.setdefault(entity_id, [])
                merged.extend(ref for ref in mention_refs if ref not in merged)
            continue
        if not is_entity_id(entity_id) or not mention_refs:
            continue
        entity_type, key = parse_entity_id(entity_id)
        payload = EntityProposalPayload(type=entity_type, key=key, label=key)
        payloads.setdefault((entity_type, key), (payload, mention_refs))
    unknown: list[UnknownEntity] = []
    for item in raw.unknown_entities:
        label = clean_title(item.label, max_len=120)
        unknown_refs = _valid_refs(index, item.block_ids)
        if not label or detect_injection(label):
            continue
        guess = slugify_ascii(item.type_guess or "", 64) or None
        unknown.append(UnknownEntity(label=label, type_guess=guess, block_ids=unknown_refs))
        key = slugify_ascii(label, 64)
        entity_type = guess or "unknown"
        if not key or f"{entity_type}:{key}" in known:
            continue
        if normalize_for_matching(label) in names:
            continue
        payload = EntityProposalPayload(type=entity_type, key=key, label=label)
        payloads.setdefault((entity_type, key), (payload, unknown_refs))
    mentions = [
        EntityMention(
            entity_id=entity_id,
            block_ids=sorted(dict.fromkeys(found), key=lambda ref: _ref_order(index, ref))[
                :MAX_MENTION_REFS
            ],
        )
        for entity_id, found in sorted(refs.items())
        if found
    ]
    created = _now()
    proposals: list[Proposal] = [
        new_proposal(
            "entity", payload, created_at=created, evidence=_evidence(doc.source_id, found)
        )
        for _, (payload, found) in sorted(payloads.items())
    ]
    return mentions, unknown, proposals


def _glossary(job: _Job, raw: CompiledSource) -> tuple[list[GlossaryCandidate], list[Proposal]]:
    existing: set[str] = set()
    for seed in job.pack.glossary.terms:
        existing.add(seed.term.casefold())
        for values in seed.synonyms.values():
            existing.update(value.casefold() for value in values)
    candidates: list[GlossaryCandidate] = []
    proposals: list[Proposal] = []
    seen: set[str] = set()
    created = _now()
    for item in raw.glossary_candidates:
        term = clean_title(item.term, max_len=80)
        definition = clean_inline(item.definition)[:400].strip()
        if not term or not definition or term.casefold() in seen:
            continue
        if detect_injection(term) or detect_injection(definition):
            continue
        seen.add(term.casefold())
        refs = _valid_refs(job.index, item.block_ids)
        candidates.append(GlossaryCandidate(term=term, definition=definition, block_ids=refs))
        if term.casefold() in existing:
            continue
        payload = GlossaryProposalPayload(term=term, definition=definition)
        proposals.append(
            new_proposal(
                "glossary",
                payload,
                created_at=created,
                evidence=_evidence(job.doc.source_id, refs),
            )
        )
    return candidates, proposals


_WORD_RE = re.compile(r"\w+")


def _words(text: str) -> list[str]:
    """Case-folded words of ``text`` without accents (punctuation and dashes ignored)."""
    return _WORD_RE.findall(normalize_for_matching(text))


def _repeats_banner(text: str, banner: frozenset[str]) -> bool:
    """True when every word of ``text`` is a word of the domain pack banner.

    Such a block is the pack's notice for human readers, or a shortened stamp of it (for example
    "FICTIONAL - NOT FOR OPERATIONAL USE" for a banner ending "Not for operational use"); it
    cannot ask an AI system to do anything that the reviewed banner does not say already.
    """
    words = _words(text)
    return bool(words) and banner.issuperset(words)


def _injections(job: _Job, raw: CompiledSource) -> tuple[list[InjectionFlag], list[Proposal]]:
    index = job.index
    reasons: dict[str, list[str]] = {}
    excerpts: dict[str, str] = {}
    banner = frozenset(_words(job.pack.info.banner or ""))
    banner_only: list[str] = []
    for flag in raw.injection_flags:
        block_id = index.block_id(flag.block_id.strip().lower())
        if block_id is None:
            continue
        if banner and _repeats_banner(index.blocks[block_id].text, banner):
            if block_id not in banner_only:
                banner_only.append(block_id)
            continue
        reason = clean_inline(flag.reason)[:200].strip().rstrip(".") or "flagged by the compiler"
        bucket = reasons.setdefault(block_id, [])
        if reason not in bucket:
            bucket.append(reason)
    if banner_only:
        ids = ", ".join(sorted(banner_only, key=index.order.__getitem__))
        job.warnings.append(
            f"ignored the model's injection flags on {ids}: these blocks only repeat the domain "
            "pack banner (pack.yaml banner), a notice for human readers"
        )
    for block in job.doc.blocks:
        findings = detect_injection(block.text)
        if not findings:
            continue
        bucket = reasons.setdefault(block.id, [])
        for finding in findings:
            reason = f"detected: {finding.rule}"
            if reason not in bucket:
                bucket.append(reason)
        excerpts.setdefault(block.id, findings[0].excerpt)
    flags: list[InjectionFlag] = []
    proposals: list[Proposal] = []
    created = _now()
    for block_id in sorted(reasons, key=index.order.__getitem__):
        reason = "; ".join(reasons[block_id])
        flags.append(InjectionFlag(block_id=block_id, reason=reason))
        payload = InjectionProposalPayload(
            source_id=job.doc.source_id,
            block_id=block_id,
            reason=reason,
            excerpt=excerpts.get(block_id) or _excerpt(index.blocks[block_id].text),
        )
        proposals.append(
            new_proposal(
                "injection",
                payload,
                created_at=created,
                evidence=[ProposalEvidence(source_id=job.doc.source_id, block_id=block_id)],
            )
        )
    return flags, proposals


# --------------------------------------------------------------------------- finalisation


def _verified(source_id: str, ref: str, check: CitationCheck | MarkerCheck) -> VerifiedCitation:
    cited = check.cited
    quote = check.quote if isinstance(check, CitationCheck) else None
    return VerifiedCitation(
        ref=ref,
        source_id=source_id,
        block_ids=cited.block_ids if cited else (),
        quote=quote,
        status=check.status,
        provenance=cited.provenance if cited else "native-text",  # type: ignore[arg-type]
        locator=cited.locator if cited else None,
        reason=check.reason,
    )


def _title(job: _Job, raw: CompiledSource) -> str:
    doc = job.doc
    stem = posixpath.splitext(posixpath.basename(doc.source_path))[0]
    for candidate in (raw.title, doc.title_hint or "", stem):
        title = clean_title(candidate)
        if title and not detect_injection(title):
            return title
    return doc.source_id


_Finalized = tuple[CompiledSource, list[VerifiedCitation], list[Proposal], dict[str, Any]]


async def _finalize(job: _Job, raw: CompiledSource) -> _Finalized:
    index, source_id = job.index, job.doc.source_id
    title = _title(job, raw)
    summary = _guard_quantities(clean_inline(raw.summary), index)
    if not summary:
        summary = f"{title}."

    checks: list[FactCheck] = []
    for fact in raw.key_facts:
        cleaned = _clean_fact(fact)
        if cleaned is not None:
            checks.append(verify_fact(index, cleaned))
    failed: list[VerifiedCitation] = []
    dropped_positions = [position for position, check in enumerate(checks) if not check.kept]
    repaired_count = 0
    repair_failed = False
    for position in dropped_positions:
        failed.extend(_verified(source_id, "kf-failed", c) for c in checks[position].checks)
    if dropped_positions:
        dropped = [checks[position] for position in dropped_positions]
        try:
            repaired = await _repair(job, dropped)
        except LlmError as exc:
            if is_systemic(exc):
                raise
            repair_failed = True
            repaired = [None] * len(dropped)
            job.warnings.append(
                f"repair call failed ({describe_failure(exc)}): the {len(dropped)} key fact(s) "
                "that failed verification were dropped"
            )
        for position, new_check in zip(dropped_positions, repaired, strict=True):
            if new_check is None:
                continue
            if new_check.kept:
                checks[position] = new_check
                repaired_count += 1
            else:
                failed.extend(_verified(source_id, "kf-failed", c) for c in new_check.checks)

    key_facts: list[KeyFact] = []
    fact_citations: list[VerifiedCitation] = []
    seen_facts: set[str] = set()
    duplicates = 0
    for check in checks:
        if not check.kept:
            continue
        key = fact_key(check.fact.text)
        if key in seen_facts:
            duplicates += 1
            continue
        seen_facts.add(key)
        key_facts.append(check.fact)
        ref = f"kf{len(key_facts)}"
        for citation_check in check.checks:
            if citation_check.status == "failed":
                failed.append(_verified(source_id, "kf-failed", citation_check))
            else:
                fact_citations.append(_verified(source_id, ref, citation_check))

    sections: list[CompiledSection] = []
    section_citations: list[VerifiedCitation] = []
    dropped_sentences = 0
    for section in raw.sections:
        body_check = verify_section_body(index, clean_block_markdown(section.body))
        dropped_sentences += body_check.dropped_sentences
        failed.extend(_verified(source_id, "s-failed", marker) for marker in body_check.failed)
        table_refs = list(
            dict.fromkeys(
                table_id
                for table_id in (index.table_id(ref.strip().lower()) for ref in section.table_refs)
                if table_id is not None
            )
        )
        body = body_check.body.strip()
        heading = clean_title(section.heading, max_len=100)
        if not body and not table_refs:
            continue
        sections.append(
            CompiledSection(
                heading=heading or f"Section {len(sections) + 1}",
                body=body,
                table_refs=table_refs,
            )
        )
        ref = f"s{len(sections)}"
        section_citations.extend(_verified(source_id, ref, mark) for mark in body_check.markers)

    mentions, unknown, entity_proposals = _mentions_and_entity_proposals(job, raw)
    glossary, glossary_proposals = _glossary(job, raw)
    flags, injection_proposals = _injections(job, raw)
    compiled = CompiledSource(
        title=title,
        summary=summary,
        key_facts=key_facts,
        sections=sections,
        entity_mentions=mentions,
        unknown_entities=unknown,
        glossary_candidates=glossary,
        injection_flags=flags,
    )
    citations = [*fact_citations, *section_citations, *failed]
    proposals: list[Proposal] = []
    seen_ids: set[str] = set()
    for proposal in [*entity_proposals, *glossary_proposals, *injection_proposals]:
        if proposal.id not in seen_ids:
            seen_ids.add(proposal.id)
            proposals.append(proposal)
    counts = {status: 0 for status in ("verified", "unverified-paraphrase", "failed")}
    for citation in citations:
        counts[citation.status] += 1
    stats = {
        **counts,
        "facts_kept": len(key_facts),
        "facts_dropped": sum(1 for check in checks if not check.kept),
        "facts_repaired": repaired_count,
        "facts_duplicate": duplicates,
        "repair_requested": bool(dropped_positions),
        "repair_failed": repair_failed,
        "sentences_dropped": dropped_sentences,
    }
    return compiled, citations, proposals, stats


async def compile_source(
    doc: ExtractedDoc,
    classification: Classification,
    pack: DomainPack,
    llm: LlmClient,
    *,
    hints: str | None = None,
) -> CompiledResult:
    """Compile one source with verified citations (pipeline.md §3, evidence-contract §4)."""
    index = DocIndex(doc)
    chunk_chars = MAP_CHUNK_MAX_TOKENS * CHARS_PER_TOKEN
    units = data_units(doc, max_chars=chunk_chars)
    large_registry = len(pack.entities.registry) > REGISTRY_PROMPT_LIMIT
    mentioned = set(detect_mentions(pack, doc)) if large_registry else set()
    job = _Job(
        doc=doc,
        classification=classification,
        pack=pack,
        llm=llm,
        index=index,
        context=_context(classification, pack, _registry_for_prompt(pack, mentioned), hints),
        units=units,
        tracker=_Tracker(),
    )
    total_chars = sum(unit.size for unit in units)
    if not units:
        raw = EMPTY_OUTPUT.model_copy()
        chunks = 0
    elif total_chars <= SINGLE_PASS_MAX_TOKENS * CHARS_PER_TOKEN:
        raw = await _compile_single(job)
        chunks = 1
    else:
        chunk_list = chunk_units(units, chunk_chars)
        chunks = len(chunk_list)
        raw = await _map_reduce(job, chunk_list)
    compiled, citations, proposals, stats = await _finalize(job, raw)
    if not units:
        compiled = compiled.model_copy(update={"summary": EMPTY_SUMMARY})
    authored = doc.metadata.authored
    usage: dict[str, Any] = {
        "llm_calls": len(job.tracker.calls),
        **job.tracker.totals(),
        "calls": job.tracker.ordered(),
        "prompt_version": PROMPT_VERSION,
        "estimated_input_tokens": -(-total_chars // CHARS_PER_TOKEN),
        "map_reduce": chunks > 1,
        "chunks": chunks,
        "empty_document": not units,
        "verification": stats,
        "warnings": list(job.warnings),
        "doc_date": authored.isoformat() if authored else None,
    }
    return CompiledResult(
        source_id=doc.source_id,
        compiled=compiled,
        citations=citations,
        proposals=proposals,
        usage=usage,
    )
