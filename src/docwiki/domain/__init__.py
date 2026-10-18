"""Domain packs: schema, loader, runtime overlay and deterministic rule helpers."""

from docwiki.domain.loader import PackError, PackValidationError, load_pack
from docwiki.domain.models import DomainPack
from docwiki.domain.overlay import (
    Overlay,
    add_proposal,
    apply_overlay,
    dump_overlay,
    filter_overlay,
    load_overlay,
)
from docwiki.domain.rules import (
    DocTypeMatch,
    TopicScore,
    explicit_references,
    glossary_synonym_rows,
    match_doc_type,
    order_revisions,
    parse_doc_number,
    parse_revision,
    revision_rank,
    route_topics,
    score_topic,
    sensitivity_floor,
    sensitivity_for,
    supersession_pairs,
)

__all__ = [
    "DocTypeMatch",
    "DomainPack",
    "Overlay",
    "PackError",
    "PackValidationError",
    "TopicScore",
    "add_proposal",
    "apply_overlay",
    "dump_overlay",
    "explicit_references",
    "filter_overlay",
    "glossary_synonym_rows",
    "load_overlay",
    "load_pack",
    "match_doc_type",
    "order_revisions",
    "parse_doc_number",
    "parse_revision",
    "revision_rank",
    "route_topics",
    "score_topic",
    "sensitivity_floor",
    "sensitivity_for",
    "supersession_pairs",
]
