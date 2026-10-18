"""Runtime overlay ``work/state/overlay.yaml``: accepted proposals applied on top of a pack.

Merge rules (overlay wins for scalars, lists are unioned):

* entities — matched by ``<type>:<key>``; ``label`` replaced, ``aliases`` unioned, ``attributes``
  updated; new entries appended. The entity type must exist in the pack.
* glossary — matched by term (case-insensitive); ``definition`` replaced, synonyms and
  ``see_also`` unioned per language; new terms appended.
* topics — matched by slug; ``title``/``description`` replaced (when non-empty), keywords and
  aliases unioned, ``min_score``/``min_sources`` replaced when set; new topics appended.
"""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import Field, ValidationError

from docwiki.contracts._base import ContractModel
from docwiki.contracts.frontmatter import FrontmatterError, load_yaml_mapping
from docwiki.contracts.proposals import EntityProposal, GlossaryProposal, Proposal, TopicProposal
from docwiki.domain.loader import (
    PackError,
    PackValidationError,
    errors_from_validation,
    validate_cross_references,
)
from docwiki.domain.models import (
    DomainPack,
    EntityAlias,
    GlossaryTerm,
    RegistryEntry,
    TopicDef,
)

__all__ = [
    "Overlay",
    "add_proposal",
    "apply_overlay",
    "dump_overlay",
    "filter_overlay",
    "load_overlay",
    "overlay_size",
]

OVERLAY_FILE = "overlay.yaml"
_FIELDS = ("entities", "glossary", "topics")


class Overlay(ContractModel):
    schema_version: Literal[1] = Field(1, alias="schema")
    entities: list[RegistryEntry] = []
    glossary: list[GlossaryTerm] = []
    topics: list[TopicDef] = []


def load_overlay(path: str | Path) -> Overlay:
    """Load ``overlay.yaml``; a missing file is an empty overlay."""
    file = Path(path)
    if not file.is_file():
        return Overlay()
    try:
        data = load_yaml_mapping(file.read_text(encoding="utf-8"), where=OVERLAY_FILE)
    except FrontmatterError as exc:
        raise PackValidationError([PackError(OVERLAY_FILE, "", str(exc))]) from exc
    try:
        return Overlay.model_validate(data)
    except ValidationError as exc:
        raise PackValidationError(errors_from_validation(OVERLAY_FILE, exc)) from exc


def dump_overlay(overlay: Overlay) -> str:
    """Deterministic YAML text for ``overlay.yaml``."""
    return yaml.safe_dump(
        overlay.to_json_dict(),
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=4096,
    )


def _union_aliases(first: list[EntityAlias], second: list[EntityAlias]) -> list[EntityAlias]:
    seen = {(alias.text, alias.lang) for alias in first}
    merged = list(first)
    for alias in second:
        if (alias.text, alias.lang) not in seen:
            merged.append(alias)
            seen.add((alias.text, alias.lang))
    return merged


def _union(first: list[str], second: list[str]) -> list[str]:
    return list(dict.fromkeys([*first, *second]))


def apply_overlay(pack: DomainPack, overlay: Overlay) -> DomainPack:
    """Return a new pack with ``overlay`` merged in (errors name ``overlay.yaml``)."""
    known_types = {entity_type.key for entity_type in pack.entities.types}
    errors = [
        PackError(OVERLAY_FILE, f"entities[{index}].type", f"unknown entity type {entry.type!r}")
        for index, entry in enumerate(overlay.entities)
        if entry.type not in known_types
    ]
    if errors:
        raise PackValidationError(errors)

    registry = list(pack.entities.registry)
    positions = {entry.id: index for index, entry in enumerate(registry)}
    for entry in overlay.entities:
        if entry.id in positions:
            current = registry[positions[entry.id]]
            registry[positions[entry.id]] = current.model_copy(
                update={
                    "label": entry.label,
                    "aliases": _union_aliases(current.aliases, entry.aliases),
                    "attributes": {**current.attributes, **entry.attributes},
                }
            )
        else:
            positions[entry.id] = len(registry)
            registry.append(entry)

    terms = list(pack.glossary.terms)
    term_positions = {term.term.casefold(): index for index, term in enumerate(terms)}
    for term in overlay.glossary:
        key = term.term.casefold()
        if key in term_positions:
            current = terms[term_positions[key]]
            synonyms = {lang: list(values) for lang, values in current.synonyms.items()}
            for lang, values in term.synonyms.items():
                synonyms[lang] = _union(synonyms.get(lang, []), values)
            terms[term_positions[key]] = current.model_copy(
                update={
                    "definition": term.definition,
                    "synonyms": synonyms,
                    "see_also": _union(current.see_also, term.see_also),
                }
            )
        else:
            term_positions[key] = len(terms)
            terms.append(term)

    topics = list(pack.topics.topics)
    topic_positions = {topic.slug: index for index, topic in enumerate(topics)}
    for topic in overlay.topics:
        if topic.slug in topic_positions:
            current = topics[topic_positions[topic.slug]]
            update: dict[str, object] = {
                "title": topic.title,
                "keywords": _union(current.keywords, topic.keywords),
                "aliases": _union_aliases(current.aliases, topic.aliases),
            }
            if topic.description:
                update["description"] = topic.description
            if topic.min_score is not None:
                update["min_score"] = topic.min_score
            if topic.min_sources is not None:
                update["min_sources"] = topic.min_sources
            topics[topic_positions[topic.slug]] = current.model_copy(update=update)
        else:
            topic_positions[topic.slug] = len(topics)
            topics.append(topic)

    try:
        merged = DomainPack.model_validate(
            {
                **pack.model_dump(by_alias=True),
                "entities": {
                    "types": pack.entities.model_dump()["types"],
                    "registry": [e.model_dump() for e in registry],
                },
                "glossary": {"terms": [t.model_dump() for t in terms]},
                "topics": {"topics": [t.model_dump() for t in topics]},
                "overlay_applied": True,
            }
        )
    except ValidationError as exc:
        raise PackValidationError(errors_from_validation(OVERLAY_FILE, exc)) from exc
    validate_cross_references(merged)
    return merged


def overlay_size(overlay: Overlay) -> int:
    """Number of entries (entities, glossary terms and topics) of ``overlay``."""
    return sum(len(getattr(overlay, name)) for name in _FIELDS)


def _entry_label(item: RegistryEntry | GlossaryTerm | TopicDef) -> str:
    if isinstance(item, RegistryEntry):
        return item.id
    if isinstance(item, GlossaryTerm):
        return repr(item.term)
    return item.slug


def filter_overlay(pack: DomainPack, overlay: Overlay) -> tuple[Overlay, list[str]]:
    """The entries of ``overlay`` that apply to ``pack``, and why the others were left out.

    Entries are tried one at a time (entities, glossary, topics, in file order) on top of the
    ones already kept, so one invalid entry — an unknown entity type, a language the pack does
    not declare — never blocks the others. :func:`apply_overlay` of the kept overlay succeeds.
    """
    try:
        apply_overlay(pack, overlay)
    except PackValidationError:
        pass
    else:
        return overlay, []
    kept = Overlay()
    problems: list[str] = []
    for name in _FIELDS:
        for index, item in enumerate(getattr(overlay, name)):
            candidate = kept.model_copy(update={name: [*getattr(kept, name), item]})
            try:
                apply_overlay(pack, candidate)
            except PackValidationError as exc:
                reason = "; ".join(error.message for error in exc.errors[:3]) or str(exc)
                problems.append(f"{OVERLAY_FILE} {name}[{index}] {_entry_label(item)}: {reason}")
                continue
            kept = candidate
    return kept, problems


def add_proposal(overlay: Overlay, proposal: Proposal) -> Overlay:
    """Return ``overlay`` extended with an *accepted* entity/glossary/topic proposal.

    A payload that cannot become an overlay entry (a synonym language that is not a language
    code, a topic without keywords or aliases...) raises :class:`PackValidationError`.
    """
    if proposal.status != "accepted":
        raise ValueError("only accepted proposals flow into the overlay")
    try:
        return _add_proposal(overlay, proposal)
    except ValidationError as exc:
        raise PackValidationError(errors_from_validation(OVERLAY_FILE, exc)) from exc


def _add_proposal(overlay: Overlay, proposal: Proposal) -> Overlay:
    if isinstance(proposal, EntityProposal):
        payload = proposal.payload
        entry = RegistryEntry(
            type=payload.type,
            key=payload.key,
            label=payload.label,
            aliases=[EntityAlias(text=a.text, lang=a.lang) for a in payload.aliases],
            attributes=dict(payload.attributes),
        )
        return overlay.model_copy(update={"entities": [*overlay.entities, entry]})
    if isinstance(proposal, GlossaryProposal):
        payload = proposal.payload
        term = GlossaryTerm(
            term=payload.term,
            definition=payload.definition,
            synonyms={lang: list(values) for lang, values in payload.synonyms.items()},
            see_also=list(payload.see_also),
        )
        return overlay.model_copy(update={"glossary": [*overlay.glossary, term]})
    if isinstance(proposal, TopicProposal):
        payload = proposal.payload
        topic = TopicDef(
            slug=payload.slug,
            title=payload.title,
            description=payload.description,
            keywords=list(payload.keywords),
            aliases=[EntityAlias(text=a.text, lang=a.lang) for a in payload.aliases],
        )
        return overlay.model_copy(update={"topics": [*overlay.topics, topic]})
    raise ValueError(f"{proposal.kind} proposals do not change the overlay")
