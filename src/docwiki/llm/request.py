"""Validated LLM request and its stable request hash."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from pydantic import BaseModel

from docwiki.llm.hashing import canonical_hash, normalize_newlines
from docwiki.llm.schema import to_strict_json_schema
from docwiki.llm.types import TIERS, ContentPart, ImagePart, MetadataValue, TextPart, Tier

SCHEMA_NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
CHARS_PER_TOKEN = 4
"""Token estimate used for client-side budgeting (pipeline.md §3: 4 characters per token)."""
IMAGE_TOKEN_ESTIMATE: Mapping[str, int] = MappingProxyType({"low": 85, "auto": 1000, "high": 1000})
MAX_METADATA_KEY_LENGTH = 64
_METADATA_SCALARS = (str, int, float, bool)


def estimate_text_tokens(text: str) -> int:
    """Rough token estimate for budgeting (never used for billing)."""
    return math.ceil(len(text) / CHARS_PER_TOKEN)


def build_hash_payload(
    *,
    tier: str,
    system: str,
    parts: Sequence[ContentPart],
    schema_name: str,
    output_schema: Mapping[str, Any],
    prompt_version: str,
) -> dict[str, Any]:
    """The object whose canonical JSON is hashed into the request hash."""
    return {
        "tier": tier,
        "system": normalize_newlines(system),
        "user": [part.hash_repr() for part in parts],
        "schema_name": schema_name,
        "output_schema": output_schema,
        "prompt_version": prompt_version,
    }


@dataclass(frozen=True, eq=False)
class LlmRequest:
    """A fully validated structured-output request (shared by every client implementation)."""

    tier: Tier
    system: str
    parts: tuple[ContentPart, ...]
    output: type[BaseModel]
    schema_name: str
    prompt_version: str
    max_output_tokens: int
    json_schema: dict[str, Any]
    request_hash: str
    metadata: Mapping[str, MetadataValue] = field(default_factory=dict)

    @classmethod
    def build(
        cls,
        tier: Tier,
        system: str,
        user: str | Sequence[ContentPart],
        output: type[BaseModel],
        schema_name: str,
        prompt_version: str,
        max_output_tokens: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> LlmRequest:
        if tier not in TIERS:
            raise ValueError(f"tier must be one of {', '.join(TIERS)}, got {tier!r}")
        if not isinstance(system, str):
            raise TypeError("system must be a str")
        if not (isinstance(output, type) and issubclass(output, BaseModel)):
            raise TypeError(f"output must be a pydantic BaseModel subclass, got {output!r}")
        if not isinstance(schema_name, str) or not SCHEMA_NAME_RE.match(schema_name):
            raise ValueError(
                f"schema_name must match {SCHEMA_NAME_RE.pattern} (letters, digits, '_' or '-', "
                f"at most 64 characters), got {schema_name!r}"
            )
        if not isinstance(prompt_version, str) or not prompt_version.strip():
            raise ValueError("prompt_version must be a non-empty string")
        if isinstance(max_output_tokens, bool) or not isinstance(max_output_tokens, int):
            raise TypeError("max_output_tokens must be an int")
        if max_output_tokens < 1:
            raise ValueError("max_output_tokens must be >= 1")
        parts = _normalize_user(user)
        clean_metadata = _validate_metadata(metadata)
        json_schema = to_strict_json_schema(output)
        payload = build_hash_payload(
            tier=tier,
            system=system,
            parts=parts,
            schema_name=schema_name,
            output_schema=json_schema,
            prompt_version=prompt_version,
        )
        return cls(
            tier=tier,
            system=system,
            parts=parts,
            output=output,
            schema_name=schema_name,
            prompt_version=prompt_version,
            max_output_tokens=max_output_tokens,
            json_schema=json_schema,
            request_hash=canonical_hash(payload),
            metadata=MappingProxyType(clean_metadata),
        )

    def hash_payload(self) -> dict[str, Any]:
        return build_hash_payload(
            tier=self.tier,
            system=self.system,
            parts=self.parts,
            schema_name=self.schema_name,
            output_schema=self.json_schema,
            prompt_version=self.prompt_version,
        )

    @property
    def text(self) -> str:
        """All text parts joined with blank lines (handy in fake handlers)."""
        return "\n\n".join(part.text for part in self.parts if isinstance(part, TextPart))

    @property
    def images(self) -> tuple[ImagePart, ...]:
        return tuple(part for part in self.parts if isinstance(part, ImagePart))

    def estimated_input_tokens(self) -> int:
        """Client-side estimate of the prompt size (system + text + images)."""
        text_chars = len(self.system) + sum(
            len(part.text) for part in self.parts if isinstance(part, TextPart)
        )
        image_tokens = sum(IMAGE_TOKEN_ESTIMATE[part.detail] for part in self.images)
        return math.ceil(text_chars / CHARS_PER_TOKEN) + image_tokens


def _normalize_user(user: str | Sequence[ContentPart]) -> tuple[ContentPart, ...]:
    if isinstance(user, str):
        return (TextPart(user),)
    if isinstance(user, TextPart | ImagePart):
        return (user,)
    if not isinstance(user, Sequence):
        raise TypeError("user must be a str or a sequence of TextPart/ImagePart")
    parts: list[ContentPart] = []
    for part in user:
        if not isinstance(part, TextPart | ImagePart):
            raise TypeError(f"user content parts must be TextPart or ImagePart, got {part!r}")
        parts.append(part)
    if not parts:
        raise ValueError("user content must not be empty")
    return tuple(parts)


def _validate_metadata(metadata: Mapping[str, Any] | None) -> dict[str, MetadataValue]:
    if metadata is None:
        return {}
    if not isinstance(metadata, Mapping):
        raise TypeError("metadata must be a mapping")
    clean: dict[str, MetadataValue] = {}
    for key, value in metadata.items():
        if not isinstance(key, str) or not key or len(key) > MAX_METADATA_KEY_LENGTH:
            raise ValueError(
                f"metadata keys must be non-empty strings of at most 64 characters: {key!r}"
            )
        if value is not None and not isinstance(value, _METADATA_SCALARS):
            raise TypeError(f"metadata[{key!r}] must be a str, int, float, bool or None")
        clean[key] = value
    return clean
