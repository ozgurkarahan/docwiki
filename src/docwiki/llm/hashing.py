"""Canonical JSON and hashing helpers shared by the LLM clients and their fixtures."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def normalize_newlines(text: str) -> str:
    """Return ``text`` with CRLF and CR line endings converted to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def canonical_json(value: Any) -> str:
    """Serialise ``value`` deterministically: sorted keys, no whitespace, UTF-8 friendly."""
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of ``data``."""
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value: Any) -> str:
    """Return the SHA-256 of the canonical JSON encoding of ``value`` (UTF-8)."""
    return sha256_hex(canonical_json(value).encode("utf-8"))
