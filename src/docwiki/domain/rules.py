"""Deterministic domain-pack rules: classification, sensitivity, supersession and topics."""

from __future__ import annotations

import posixpath
import re
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from functools import lru_cache

from docwiki.contracts.enums import max_sensitivity, sensitivity_rank
from docwiki.domain.models import DomainPack, TopicDef

__all__ = [
    "DEFAULT_MIN_SCORE",
    "DEFAULT_MIN_SOURCES",
    "FIELD_WEIGHTS",
    "DocTypeMatch",
    "TopicScore",
    "compare_revisions",
    "explicit_references",
    "glob_to_regex",
    "glossary_synonym_rows",
    "match_doc_type",
    "normalize_for_matching",
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

DEFAULT_MIN_SCORE = 3.0
DEFAULT_MIN_SOURCES = 2
FIELD_WEIGHTS = {"title": 3.0, "heading": 2.0, "body": 1.0}


@dataclass(frozen=True)
class DocTypeMatch:
    doc_type: str
    category: str
    authority: int
    rule_id: str
    """``<doc_type>#<rule index>``."""


def match_doc_type(pack: DomainPack, filename: str, text: str) -> DocTypeMatch | None:
    """First doc type (pack order) with a rule whose regexes all match, else ``None``.

    ``filename_regex`` is searched in the file name (no folders); ``text_regex`` in the first
    ``first_chars`` characters of the extracted text. Use inline flags (``(?i)``) for case.
    """
    name = posixpath.basename(filename)
    for doc_type in pack.taxonomy.doc_types:
        for index, rule in enumerate(doc_type.rules):
            if rule.filename_regex is not None and not re.search(rule.filename_regex, name):
                continue
            if rule.text_regex is not None and not re.search(
                rule.text_regex, text[: rule.first_chars]
            ):
                continue
            return DocTypeMatch(
                doc_type.key, doc_type.category, doc_type.authority, f"{doc_type.key}#{index}"
            )
    return None


@lru_cache(maxsize=512)
def glob_to_regex(glob: str) -> re.Pattern[str]:
    """Compile a path glob: ``**`` spans folders, ``*`` and ``?`` stay inside one segment.

    Matching is case-insensitive (a broader match can only raise a source's tier).
    """
    out = ["^"]
    index = 0
    while index < len(glob):
        char = glob[index]
        if glob.startswith("**/", index):
            out.append("(?:.*/)?")
            index += 3
            continue
        if glob.startswith("**", index):
            out.append(".*")
            index += 2
            continue
        if char == "*":
            out.append("[^/]*")
        elif char == "?":
            out.append("[^/]")
        else:
            out.append(re.escape(char))
        index += 1
    out.append("$")
    return re.compile("".join(out), re.IGNORECASE)


def sensitivity_for(pack: DomainPack, raw_path: str, doc_type: str | None = None) -> str:
    """Tier of a source: the highest tier among matching rules, else the pack default."""
    matched = [
        rule.tier
        for rule in pack.sensitivity.rules
        if (rule.path_glob is None or glob_to_regex(rule.path_glob).match(raw_path))
        and (rule.doc_type is None or rule.doc_type == doc_type)
    ]
    return max_sensitivity(*matched) if matched else pack.sensitivity.default


def sensitivity_floor(pack: DomainPack, raw_path: str) -> str:
    """Lowest tier a source can get once classified, over every doc type of the pack.

    A doc-type rule may set a tier *below* the pack default (only that rule matches), so the
    unclassified tier ``sensitivity_for(pack, raw_path, None)`` is not a lower bound; a source is
    above an audience before classification only when this floor is.
    """
    candidates = [None, *(doc_type.key for doc_type in pack.taxonomy.doc_types)]
    return min(
        (sensitivity_for(pack, raw_path, doc_type) for doc_type in candidates),
        key=sensitivity_rank,
    )


def _group(match: re.Match[str], name: str) -> str:
    if name in match.re.groupindex and match.group(name) is not None:
        return match.group(name)
    if match.re.groups >= 1 and match.group(1) is not None:
        return match.group(1)
    return match.group(0)


def _search(pattern: str, candidates: Iterable[str], group: str) -> str | None:
    for candidate in candidates:
        if not candidate:
            continue
        match = re.search(pattern, candidate)
        if match:
            return _group(match, group).strip()
    return None


def parse_doc_number(pack: DomainPack, *candidates: str) -> str | None:
    """Document number from the first candidate that matches (e.g. file name, then text head).

    Uses the named group ``number`` when present, else group 1, else the whole match.
    """
    if pack.supersession is None:
        return None
    return _search(pack.supersession.doc_number_regex, candidates, "number")


def parse_revision(pack: DomainPack, *candidates: str) -> str | None:
    """Revision from the first matching candidate (named group ``rev``, else group 1)."""
    if pack.supersession is None:
        return None
    return _search(pack.supersession.revision_regex, candidates, "rev")


def revision_rank(pack: DomainPack, revision: str) -> int:
    """Sort key of a revision (``ValueError`` for revisions outside ``revision_order``)."""
    if pack.supersession is None:
        raise ValueError("the domain pack defines no supersession rules")
    order = pack.supersession.revision_order
    if order == "numeric":
        if not re.fullmatch(r"\d+", revision.strip()):
            raise ValueError(f"revision {revision!r} is not numeric")
        return int(revision)
    normalized = {value.casefold(): index for index, value in enumerate(order)}
    try:
        return normalized[revision.strip().casefold()]
    except KeyError:
        raise ValueError(f"revision {revision!r} is not in revision_order") from None


def compare_revisions(pack: DomainPack, first: str, second: str) -> int:
    """-1, 0 or 1 like ``cmp(first, second)``."""
    a, b = revision_rank(pack, first), revision_rank(pack, second)
    return (a > b) - (a < b)


def explicit_references(pack: DomainPack, text: str) -> list[str]:
    """Document numbers a text declares it replaces (``explicit_reference_regex``), in order."""
    if pack.supersession is None or not pack.supersession.explicit_reference_regex:
        return []
    found: list[str] = []
    for match in re.finditer(pack.supersession.explicit_reference_regex, text):
        value = _group(match, "number").strip()
        if value and value not in found:
            found.append(value)
    return found


def order_revisions(
    pack: DomainPack, sources: Iterable[tuple[str, str | None, str | None]]
) -> dict[str, list[str]]:
    """Group ``(source_id, doc_number, revision)`` by document number, oldest revision first.

    Sources without a document number or revision are ignored; ties keep ``source_id`` order.
    """
    groups: dict[str, list[tuple[int, str]]] = {}
    for source_id, doc_number, revision in sources:
        if not doc_number or not revision:
            continue
        groups.setdefault(doc_number, []).append((revision_rank(pack, revision), source_id))
    return {number: [sid for _, sid in sorted(items)] for number, items in sorted(groups.items())}


def supersession_pairs(
    pack: DomainPack, sources: Sequence[tuple[str, str | None, str | None]]
) -> list[tuple[str, str]]:
    """``(newer, older)`` pairs: every revision supersedes the one just before it."""
    pairs: list[tuple[str, str]] = []
    for ordered in order_revisions(pack, sources).values():
        pairs.extend(zip(ordered[1:], ordered[:-1], strict=True))
    return pairs


def normalize_for_matching(text: str) -> str:
    """Case-fold, strip diacritics, unify apostrophes and collapse whitespace."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = stripped.replace("’", "'").replace("‘", "'")
    return re.sub(r"\s+", " ", stripped.casefold()).strip()


@lru_cache(maxsize=4096)
def _term_pattern(term: str) -> re.Pattern[str] | None:
    words = normalize_for_matching(term).split(" ")
    words = [word for word in words if word]
    if not words:
        return None
    body = r"\s+".join(re.escape(word) for word in words)
    return re.compile(rf"(?<!\w){body}(?!\w)")


@dataclass(frozen=True)
class TopicScore:
    slug: str
    score: float
    by_field: dict[str, float] = field(default_factory=dict)
    matched_terms: tuple[str, ...] = ()

    def feeds(self, topic: TopicDef) -> bool:
        threshold = topic.min_score if topic.min_score is not None else DEFAULT_MIN_SCORE
        return self.score >= threshold


def _topic_terms(topic: TopicDef) -> list[str]:
    return list(dict.fromkeys([*topic.keywords, *(alias.text for alias in topic.aliases)]))


def score_topic(topic: TopicDef, title: str, sections: Iterable[tuple[str, str]]) -> TopicScore:
    """Score = Σ matches × field weight (title 3, heading 2, body 1) over keywords and aliases.

    Matching is case-insensitive, accent-insensitive and on word boundaries; every occurrence
    counts. ``sections`` are ``(heading, body)`` pairs.
    """
    fields = {"title": [title], "heading": [], "body": []}
    for heading, body in sections:
        fields["heading"].append(heading)
        fields["body"].append(body)
    by_field: dict[str, float] = {}
    matched: list[str] = []
    for name, texts in fields.items():
        normalized = [normalize_for_matching(text) for text in texts if text]
        total = 0.0
        for term in _topic_terms(topic):
            pattern = _term_pattern(term)
            if pattern is None:
                continue
            count = sum(len(pattern.findall(text)) for text in normalized)
            if count:
                total += count * FIELD_WEIGHTS[name]
                if term not in matched:
                    matched.append(term)
        by_field[name] = total
    return TopicScore(topic.slug, sum(by_field.values()), by_field, tuple(matched))


def route_topics(
    pack: DomainPack, title: str, sections: Sequence[tuple[str, str]]
) -> list[TopicScore]:
    """Topics this source feeds (score ≥ the topic's ``min_score``), best first."""
    scores = [score_topic(topic, title, sections) for topic in pack.topics.topics]
    feeding = [
        score for score, topic in zip(scores, pack.topics.topics, strict=True) if score.feeds(topic)
    ]
    return sorted(feeding, key=lambda score: (-score.score, score.slug))


def glossary_synonym_rows(
    pack: DomainPack, *, include_entity_aliases: bool = True
) -> list[tuple[str, str, str]]:
    """``(term, synonym, lang)`` rows for the ``synonyms`` table of ``search.db``."""
    rows: list[tuple[str, str, str]] = []
    for term in pack.glossary.terms:
        for lang, values in term.synonyms.items():
            rows.extend((term.term, value, lang) for value in values)
    if include_entity_aliases:
        for entry in pack.entities.registry:
            rows.extend((entry.label, alias.text, alias.lang) for alias in entry.aliases)
    return list(dict.fromkeys(rows))
