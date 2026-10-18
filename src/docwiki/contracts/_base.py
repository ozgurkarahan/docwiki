"""Shared base model, scalar types and canonical JSON / hashing helpers for all contracts."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, date, datetime
from typing import Annotated, Any, Self

from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict, Field

__all__ = [
    "BBox",
    "CacheKey",
    "ContractModel",
    "Hex64",
    "IsoDate",
    "Kebab",
    "LangCode",
    "MediaType",
    "NonEmptyStr",
    "RelPath",
    "Sha256Ref",
    "UtcDateTime",
    "canonical_json",
    "dumps_json",
    "sha256_bytes",
    "sha256_hex",
    "sha256_ref",
]


class ContractModel(BaseModel):
    """Base class of every DocWiki contract.

    Strict validation (no type coercion) and unknown keys are rejected. Dates and datetimes
    additionally accept ISO 8601 strings so that YAML and ``json.loads`` input both work.
    Serialise with :meth:`to_json_dict` / :meth:`to_json` so that aliases (``schema``,
    ``from``) are used.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        populate_by_name=True,
        protected_namespaces=(),
    )

    def to_json_dict(self) -> dict[str, Any]:
        """JSON-compatible dict using field aliases (stable field order)."""
        return self.model_dump(mode="json", by_alias=True)

    def to_json(self, *, indent: int | None = 2) -> str:
        """Pretty JSON text (UTF-8, LF, trailing newline when indented)."""
        return dumps_json(self.to_json_dict(), indent=indent)

    @classmethod
    def from_json(cls, data: str | bytes) -> Self:
        """Validate a JSON document (strict JSON mode)."""
        return cls.model_validate_json(data)


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[Tt ]\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:[Zz]|[+-]\d{2}:\d{2})$"
)


def _parse_iso_date(value: object) -> object:
    if isinstance(value, str):
        if not _DATE_RE.match(value):
            raise ValueError("date must be formatted YYYY-MM-DD")
        return date.fromisoformat(value)
    if isinstance(value, datetime):
        raise ValueError("expected a date, got a datetime")
    return value


def _parse_iso_datetime(value: object) -> object:
    if isinstance(value, str):
        if not _DATETIME_RE.match(value):
            raise ValueError(
                "datetime must be RFC 3339 with a timezone (e.g. 2026-01-31T08:00:00Z)"
            )
        return datetime.fromisoformat(value.replace("z", "Z"))
    return value


def _require_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return value.astimezone(UTC)


IsoDate = Annotated[date, BeforeValidator(_parse_iso_date)]
"""A calendar date; accepts ``date`` objects or ``YYYY-MM-DD`` strings."""

UtcDateTime = Annotated[
    datetime, BeforeValidator(_parse_iso_datetime), AfterValidator(_require_utc)
]
"""A timezone-aware datetime normalised to UTC; accepts RFC 3339 strings."""

NonEmptyStr = Annotated[str, Field(min_length=1)]
Kebab = Annotated[str, Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=64)]
LangCode = Annotated[str, Field(pattern=r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$")]
MediaType = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9.+\-]*/[a-z0-9][a-z0-9.+\-]*$")]
Hex64 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Sha256Ref = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
CacheKey = Hex64


def _check_rel_path(value: str) -> str:
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError("must be a relative POSIX path")
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("path segments must be non-empty and must not be '.' or '..'")
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("path must not contain control characters")
    return value


RelPath = Annotated[str, AfterValidator(_check_rel_path)]
"""A normalised relative POSIX path (no leading slash, no ``.``/``..`` segments, no backslash)."""


def _check_bbox(value: list[float]) -> list[float]:
    if len(value) != 4:
        raise ValueError("bbox must have exactly 4 numbers [x0, y0, x1, y1]")
    x0, y0, x1, y1 = value
    if not (0.0 <= x0 <= x1 <= 1.0 and 0.0 <= y0 <= y1 <= 1.0):
        raise ValueError("bbox must be normalised to [0, 1] with x0 <= x1 and y0 <= y1")
    return value


BBox = Annotated[list[float], AfterValidator(_check_bbox)]
"""Bounding box ``[x0, y0, x1, y1]`` normalised to the page/image size, origin top-left."""


def canonical_json(obj: Any) -> bytes:
    """Canonical JSON bytes used for hashing (sorted keys, no whitespace, UTF-8)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )


def dumps_json(obj: Any, *, indent: int | None = 2) -> str:
    """Human-readable, deterministic JSON text (keeps insertion order)."""
    text = json.dumps(obj, ensure_ascii=False, indent=indent)
    return text + "\n" if indent is not None else text


def sha256_hex(data: bytes) -> str:
    """Lower-case hex SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def sha256_bytes(data: bytes) -> str:
    """``sha256:<hex>`` reference of ``data`` (format used for source hashes)."""
    return "sha256:" + sha256_hex(data)


def sha256_ref(hex_digest: str) -> str:
    """Prefix a hex digest with ``sha256:``."""
    return "sha256:" + hex_digest
