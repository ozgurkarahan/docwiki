"""Identifiers, slugs, page paths and content-addressing helpers (wiki-contract §2)."""

from __future__ import annotations

import hashlib
import re
import secrets
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime

from docwiki.contracts._base import canonical_json, sha256_hex

__all__ = [
    "KEBAB_RE",
    "PROPOSAL_ID_RE",
    "RELEASE_ID_RE",
    "RESERVED_ENTITY_TYPES",
    "RUN_ID_RE",
    "SOURCE_ID_RE",
    "assign_source_slugs",
    "assign_unique_slugs",
    "cache_key",
    "check_wiki_path",
    "entity_page_path",
    "format_entity_id",
    "format_hub_id",
    "format_query_id",
    "format_release_id",
    "format_topic_id",
    "hub_page_path",
    "index_page_path",
    "is_entity_id",
    "is_kebab",
    "new_run_id",
    "normalize_raw_path",
    "normalize_tags",
    "parse_entity_id",
    "parse_hub_id",
    "parse_query_id",
    "parse_release_id",
    "parse_topic_id",
    "proposal_id_for",
    "query_page_path",
    "release_id_for",
    "slugify_ascii",
    "source_id_for",
    "source_page_path",
    "source_slug",
    "topic_page_path",
]

KEBAB_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCE_ID_RE = re.compile(r"^src-[0-9a-f]{12}$")
RELEASE_ID_RE = re.compile(r"^(\d{8}T\d{6}Z)-([0-9a-f]{8})$")
RUN_ID_RE = re.compile(r"^run-\d{8}-\d{6}-[0-9a-f]{8}$")
PROPOSAL_ID_RE = re.compile(r"^prop-[0-9a-f]{12}$")
QUERY_ID_RE = re.compile(r"^query:(\d{4}-\d{2}-\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)$")
WIKI_PATH_RE = re.compile(r"^[a-z0-9][a-z0-9\-/._]*$")

RESERVED_ENTITY_TYPES = frozenset(
    {
        "entities",
        "evidence",
        "glossary",
        "index",
        "log",
        "meta",
        "queries",
        "query",
        "source",
        "sources",
        "src",
        "topic",
        "topics",
    }
)
"""Entity type keys that would clash with page-id namespaces or wiki folders."""

_TRANSLITERATE = str.maketrans(
    {
        "ß": "ss",
        "ẞ": "ss",
        "æ": "ae",
        "Æ": "ae",
        "œ": "oe",
        "Œ": "oe",
        "ø": "o",
        "Ø": "o",
        "đ": "d",
        "Đ": "d",
        "ð": "d",
        "Ð": "d",
        "ł": "l",
        "Ł": "l",
        "þ": "th",
        "Þ": "th",
        "ı": "i",
    }
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_SUSPICIOUS_SEGMENTS = frozenset({"none", "null", "nan", "undefined"})


def is_kebab(value: str, *, max_len: int = 64) -> bool:
    """True for ASCII kebab-case keys such as ``baie-f1``."""
    return bool(KEBAB_RE.match(value)) and len(value) <= max_len


def normalize_raw_path(relative_path: str) -> str:
    """Validate a raw relative POSIX path and return it NFC-normalised.

    Raises ``ValueError`` for absolute paths, backslashes, empty, ``.`` or ``..`` segments.
    """
    if not relative_path:
        raise ValueError("raw path must not be empty")
    if "\\" in relative_path:
        raise ValueError(
            f"raw path must use '/' separators (use Path.as_posix()): {relative_path!r}"
        )
    path = relative_path[2:] if relative_path.startswith("./") else relative_path
    if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise ValueError(f"raw path must be relative: {relative_path!r}")
    segments = path.split("/")
    if any(segment in ("", ".", "..") for segment in segments):
        raise ValueError(f"raw path has empty, '.' or '..' segments: {relative_path!r}")
    if any(ord(ch) < 32 for ch in path):
        raise ValueError("raw path must not contain control characters")
    return unicodedata.normalize("NFC", path)


def source_id_for(relative_path: str) -> str:
    """``src-`` + first 12 hex of sha256 of the lower-cased raw relative POSIX path.

    The path is NFC-normalised first so that the id does not depend on the uploader's OS.
    """
    path = normalize_raw_path(relative_path).lower()
    return "src-" + hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]


def slugify_ascii(text: str, max_len: int = 60) -> str:
    """ASCII kebab-case slug: NFKD → ASCII, lower, non ``[a-z0-9]`` → ``-``, collapse dashes.

    A few letters without a decomposition (ß, æ, œ, ø, đ, ł, þ, ı) are transliterated first.
    Returns ``""`` when nothing ASCII remains; callers decide the fallback.
    """
    if max_len < 1:
        raise ValueError("max_len must be >= 1")
    decomposed = unicodedata.normalize("NFKD", text.translate(_TRANSLITERATE))
    ascii_text = decomposed.encode("ascii", "ignore").decode("ascii").lower()
    slug = _NON_ALNUM.sub("-", ascii_text).strip("-")
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    return slug


def source_slug(stem: str, source_id: str) -> str:
    """Base slug of a source page from its file stem (falls back to the source id)."""
    return slugify_ascii(stem, 60) or source_id


def _with_suffix(base: str, suffix: str, max_len: int) -> str:
    room = max_len - len(suffix) - 1
    trimmed = base[:room].rstrip("-") if room > 0 else ""
    return f"{trimmed}-{suffix}" if trimmed else suffix


def assign_source_slugs(
    stems: Mapping[str, str],
    existing: Mapping[str, str] | None = None,
    *,
    max_len: int = 60,
) -> dict[str, str]:
    """Collision-safe source slugs, independent of input order.

    ``stems`` maps ``source_id`` → file stem. Slugs already assigned in ``existing`` (previous
    release) are kept for sources that are still present, so URLs stay stable. Any other source
    whose base slug is shared with another source (or already taken) gets ``-`` + 4 hex of its
    ``source_id`` appended (8 or 12 hex if that still collides).
    """
    for source_id in stems:
        if not SOURCE_ID_RE.match(source_id):
            raise ValueError(f"invalid source_id: {source_id!r}")
    result: dict[str, str] = {}
    taken: set[str] = set()
    for source_id in sorted(existing or {}):
        slug = (existing or {})[source_id]
        if source_id in stems and is_kebab(slug, max_len=max_len) and slug not in taken:
            result[source_id] = slug
            taken.add(slug)
    pending = {sid: source_slug(stem, sid) for sid, stem in stems.items() if sid not in result}
    base_counts: dict[str, int] = {}
    for base in pending.values():
        base_counts[base] = base_counts.get(base, 0) + 1
    for source_id in sorted(pending, key=lambda sid: (pending[sid], sid)):
        base = pending[source_id]
        if base_counts[base] == 1 and base not in taken:
            slug = base
        else:
            digest = source_id[4:]
            for width in (4, 8, 12):
                slug = _with_suffix(base, digest[:width], max_len)
                if slug not in taken:
                    break
            else:  # pragma: no cover - 12 hex digits are unique per source_id
                raise ValueError(f"cannot assign a unique slug for {source_id}")
        result[source_id] = slug
        taken.add(slug)
    return result


def assign_unique_slugs(
    names: Sequence[str], *, max_len: int = 40, fallback: str = "item"
) -> list[str]:
    """Slugs for an ordered list of names (e.g. workbook sheets), suffixing ``-2``, ``-3``…"""
    used: set[str] = set()
    slugs: list[str] = []
    for name in names:
        base = slugify_ascii(name, max_len) or fallback
        slug = base
        counter = 2
        while slug in used:
            slug = _with_suffix(base, str(counter), max_len)
            counter += 1
        used.add(slug)
        slugs.append(slug)
    return slugs


def format_entity_id(entity_type: str, key: str) -> str:
    """``<type>:<key>`` after validating both parts."""
    if not is_kebab(entity_type) or entity_type in RESERVED_ENTITY_TYPES:
        raise ValueError(f"invalid entity type: {entity_type!r}")
    if not is_kebab(key):
        raise ValueError(f"invalid entity key: {key!r}")
    return f"{entity_type}:{key}"


def parse_entity_id(entity_id: str) -> tuple[str, str]:
    """Split ``<type>:<key>``; raises ``ValueError`` when malformed or reserved."""
    entity_type, sep, key = entity_id.partition(":")
    if not sep:
        raise ValueError(f"entity id must look like '<type>:<key>': {entity_id!r}")
    format_entity_id(entity_type, key)
    return entity_type, key


def is_entity_id(value: str) -> bool:
    try:
        parse_entity_id(value)
    except ValueError:
        return False
    return True


def format_topic_id(slug: str, scope: str | None = None) -> str:
    """``topic:<slug>``, or ``topic:<scope>/<slug>`` for a topic of one scope (v1.7, ADR 0011)."""
    if not is_kebab(slug):
        raise ValueError(f"invalid topic slug: {slug!r}")
    if scope is None:
        return f"topic:{slug}"
    if not is_kebab(scope):
        raise ValueError(f"invalid topic scope: {scope!r}")
    return f"topic:{scope}/{slug}"


def parse_topic_id(topic_id: str) -> str:
    """The topic's path under ``topics/``: ``<slug>`` or ``<scope>/<slug>``."""
    prefix, sep, rest = topic_id.partition(":")
    parts = rest.split("/")
    if prefix != "topic" or not sep or len(parts) > 2 or not all(is_kebab(p) for p in parts):
        raise ValueError(f"topic id must look like 'topic:[<scope>/]<slug>': {topic_id!r}")
    return rest


def format_hub_id(folder: str, key: str) -> str:
    """``hub:<folder>/<key>``: the hub page of one scope value (``hub:chantiers/moreau``)."""
    if not is_kebab(folder) or not is_kebab(key):
        raise ValueError(f"invalid hub folder or key: {folder!r}, {key!r}")
    return f"hub:{folder}/{key}"


def parse_hub_id(hub_id: str) -> tuple[str, str]:
    prefix, sep, rest = hub_id.partition(":")
    folder, slash, key = rest.partition("/")
    if prefix != "hub" or not sep or not slash or not is_kebab(folder) or not is_kebab(key):
        raise ValueError(f"hub id must look like 'hub:<folder>/<key>': {hub_id!r}")
    return folder, key


def format_query_id(day: date, slug: str) -> str:
    if not is_kebab(slug):
        raise ValueError(f"invalid query slug: {slug!r}")
    return f"query:{day.isoformat()}-{slug}"


def parse_query_id(query_id: str) -> tuple[date, str]:
    match = QUERY_ID_RE.match(query_id)
    if not match:
        raise ValueError(f"query id must look like 'query:<yyyy-mm-dd>-<slug>': {query_id!r}")
    return date.fromisoformat(match.group(1)), match.group(2)


def source_page_path(slug: str) -> str:
    if not is_kebab(slug, max_len=60):
        raise ValueError(f"invalid source slug: {slug!r}")
    return f"sources/{slug}.md"


def entity_page_path(entity_id: str) -> str:
    entity_type, key = parse_entity_id(entity_id)
    return f"entities/{entity_type}/{key}.md"


def topic_page_path(topic_id: str) -> str:
    return f"topics/{parse_topic_id(topic_id)}.md"


def hub_page_path(hub_id: str) -> str:
    folder, key = parse_hub_id(hub_id)
    return f"{folder}/{key}.md"


def query_page_path(query_id: str) -> str:
    day, slug = parse_query_id(query_id)
    return f"queries/{day.isoformat()}-{slug}.md"


def index_page_path(scope: str) -> str:
    """Path of an index page by scope: ``home``, ``sources``, ``entities``, ``entities/<type>``,
    ``topics`` or ``queries``."""
    if scope == "home":
        return "index.md"
    if scope in ("sources", "entities", "topics", "queries"):
        return f"{scope}/index.md"
    if scope.startswith("entities/") and is_kebab(scope.removeprefix("entities/")):
        return f"{scope}/index.md"
    if scope.startswith("hubs/") and is_kebab(scope.removeprefix("hubs/")):
        # The list of a scope's hubs (``index:hubs/chantiers`` → ``chantiers/index.md``).
        return f"{scope.removeprefix('hubs/')}/index.md"
    raise ValueError(f"unknown index scope: {scope!r}")


_SKILL_PATH_RE = re.compile(r"^\.(agents|claude|github)/skills/[a-z0-9]+(?:-[a-z0-9]+)*/SKILL\.md$")
_FIXED_PATHS = frozenset({"AGENTS.md"})


def check_wiki_path(path: str) -> str | None:
    """Return an error message when ``path`` breaks the slug/path rules (gate G09), else None.

    Generated paths must match ``^[a-z0-9][a-z0-9\\-/._]*$`` with no ``.`` in directory names.
    Fixed agent-kit paths are allowed: ``AGENTS.md``, ``_meta/...`` and the skill projections
    ``.agents|.claude|.github/skills/<name>/SKILL.md``.
    """
    if path in _FIXED_PATHS or _SKILL_PATH_RE.match(path):
        return None
    candidate = path.removeprefix("_meta/") if path.startswith("_meta/") else path
    if not WIKI_PATH_RE.match(candidate):
        return f"path {path!r} must match ^[a-z0-9][a-z0-9\\-/._]*$"
    segments = candidate.split("/")
    if any(segment == "" for segment in segments):
        return f"path {path!r} has an empty segment"
    if any("." in segment for segment in segments[:-1]):
        return f"path {path!r} has a '.' inside a directory name"
    if any(segment in ("..", ".") for segment in segments):
        return f"path {path!r} has a relative segment"
    for segment in segments:
        stem = segment.split(".", 1)[0]
        if stem in _SUSPICIOUS_SEGMENTS:
            return f"path {path!r} contains a suspicious segment {segment!r} (repr leak?)"
    return None


def normalize_tags(tags: Iterable[str]) -> list[str]:
    """Lower-case, strip, de-duplicate and sort tags (wiki-contract §3)."""
    return sorted({tag.strip().lower() for tag in tags if tag.strip()})


def cache_key(
    stage: str,
    input_hashes: Iterable[str],
    *,
    stage_version: str,
    prompt_version: str | None = None,
    model_id: str | None = None,
    model_version: str | None = None,
    domain_pack_hash: str | None = None,
    schema_version: int = 1,
) -> str:
    """Content-addressed artifact key (architecture §5): 64 hex chars.

    ``sha256(json([stage, input_hashes, stage_version, prompt_version, model_id,
    model_version, domain_pack_hash, schema_version]))`` with ``input_hashes`` sorted.
    """
    payload = [
        stage,
        sorted(input_hashes),
        stage_version,
        prompt_version,
        model_id,
        model_version,
        domain_pack_hash,
        schema_version,
    ]
    return sha256_hex(canonical_json(payload))


def format_release_id(created_at: datetime, digest_hex: str) -> str:
    """``YYYYMMDDTHHMMSSZ-<8 hex>`` from a UTC timestamp and a hex digest."""
    if created_at.tzinfo is None:
        raise ValueError("created_at must be timezone-aware")
    if not re.match(r"^[0-9a-f]{8,}$", digest_hex):
        raise ValueError("digest must be at least 8 lower-case hex characters")
    stamp = created_at.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{stamp}-{digest_hex[:8]}"


def parse_release_id(release_id: str) -> tuple[datetime, str]:
    """Return ``(created_at, hash8)`` of a release id."""
    match = RELEASE_ID_RE.match(release_id)
    if not match:
        raise ValueError(f"invalid release id: {release_id!r}")
    created = datetime.strptime(match.group(1), "%Y%m%dT%H%M%SZ").replace(tzinfo=UTC)
    return created, match.group(2)


def release_id_for(created_at: datetime, identity: object) -> str:
    """Release id from the manifest identity (see ``ReleaseManifest.identity_payload``)."""
    return format_release_id(created_at, sha256_hex(canonical_json(identity)))


def new_run_id(now: datetime | None = None, entropy: str | None = None) -> str:
    """``run-YYYYMMDD-HHMMSS-<8 hex>`` (lower-case so it can be used in wiki paths)."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    suffix = entropy if entropy is not None else secrets.token_hex(4)
    if not re.match(r"^[0-9a-f]{8}$", suffix):
        raise ValueError("entropy must be 8 lower-case hex characters")
    return f"run-{moment.strftime('%Y%m%d-%H%M%S')}-{suffix}"


def proposal_id_for(kind: str, payload: object) -> str:
    """Deterministic proposal id so the same suggestion is not filed twice."""
    return "prop-" + sha256_hex(canonical_json([kind, payload]))[:12]
