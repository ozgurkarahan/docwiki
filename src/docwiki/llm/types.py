"""Value objects shared by every DocWiki LLM client."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from functools import cached_property
from typing import Any, Literal, TypeVar, get_args

from pydantic import BaseModel, ConfigDict, Field

from docwiki.llm.hashing import normalize_newlines, sha256_hex

type Tier = Literal["fast", "smart"]
TIERS: tuple[Tier, ...] = get_args(Tier.__value__)

type Origin = Literal["foundry", "fake", "replay"]
"""Where a result came from: the live Foundry service, a fake handler or a replayed fixture."""

type MetadataValue = str | int | float | bool | None
type ImageDetail = Literal["auto", "low", "high"]
IMAGE_DETAILS: tuple[str, ...] = get_args(ImageDetail.__value__)

T = TypeVar("T", bound=BaseModel)

_IMAGE_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/gif": (b"GIF87a", b"GIF89a"),
    "image/webp": (b"RIFF",),
}
_MODEL_VERSION_RE = re.compile(r"^(?P<model>.+?)-(?P<version>\d{4}-\d{2}-\d{2})$")


@dataclass(frozen=True, slots=True)
class TextPart:
    """A text segment of the user message."""

    text: str

    def __post_init__(self) -> None:
        if not isinstance(self.text, str):
            raise TypeError("TextPart.text must be a str")

    def hash_repr(self) -> dict[str, Any]:
        return {"type": "text", "text": normalize_newlines(self.text)}


@dataclass(frozen=True)
class ImagePart:
    """An image segment of the user message (sent to the model as a base64 data URL)."""

    data: bytes
    media_type: str = "image/png"
    detail: ImageDetail = "auto"

    def __post_init__(self) -> None:
        if isinstance(self.data, bytearray):
            object.__setattr__(self, "data", bytes(self.data))
        if not isinstance(self.data, bytes) or not self.data:
            raise ValueError("ImagePart.data must be non-empty bytes")
        signatures = _IMAGE_SIGNATURES.get(self.media_type)
        if signatures is None:
            supported = ", ".join(sorted(_IMAGE_SIGNATURES))
            raise ValueError(f"Unsupported image media type {self.media_type!r}; use {supported}")
        if not self.data.startswith(signatures):
            raise ValueError(f"ImagePart.data does not look like {self.media_type} content")
        if self.media_type == "image/webp" and self.data[8:12] != b"WEBP":
            raise ValueError("ImagePart.data does not look like image/webp content")
        if self.detail not in IMAGE_DETAILS:
            raise ValueError(f"Unsupported image detail {self.detail!r}")

    @classmethod
    def png(cls, data: bytes, *, detail: ImageDetail = "auto") -> ImagePart:
        """Build an image part from PNG bytes (the format of extracted figure crops)."""
        return cls(data=data, media_type="image/png", detail=detail)

    @cached_property
    def sha256(self) -> str:
        return sha256_hex(self.data)

    def data_url(self) -> str:
        encoded = base64.b64encode(self.data).decode("ascii")
        return f"data:{self.media_type};base64,{encoded}"

    def hash_repr(self) -> dict[str, Any]:
        return {
            "type": "image",
            "media_type": self.media_type,
            "detail": self.detail,
            "sha256": self.sha256,
        }


type ContentPart = TextPart | ImagePart


class LlmUsage(BaseModel):
    """Token usage of one call (summed over every billed model call it made)."""

    model_config = ConfigDict(frozen=True)

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens

    def __add__(self, other: LlmUsage) -> LlmUsage:
        if not isinstance(other, LlmUsage):
            return NotImplemented
        return LlmUsage(
            input_tokens=self.input_tokens + other.input_tokens,
            output_tokens=self.output_tokens + other.output_tokens,
            cached_input_tokens=self.cached_input_tokens + other.cached_input_tokens,
            reasoning_tokens=self.reasoning_tokens + other.reasoning_tokens,
        )


@dataclass(frozen=True)
class StructuredResult[OutputT: BaseModel]:
    """A validated structured output plus everything needed for logging, caching and costs."""

    output: OutputT
    output_json: dict[str, Any]
    usage: LlmUsage
    tier: Tier
    deployment: str
    model: str | None
    model_version: str | None
    schema_name: str
    prompt_version: str
    request_hash: str
    latency_s: float
    wait_s: float = 0.0
    retries: int = 0
    attempts: int = 1
    origin: Origin = "foundry"
    response_id: str | None = None


class DeploymentInfo(BaseModel):
    """What a tier resolves to: deployment name and the model (version) behind it."""

    model_config = ConfigDict(frozen=True)

    tier: Tier
    deployment: str
    model_name: str | None = None
    model_version: str | None = None
    model_publisher: str | None = None
    sku: str | None = None
    capacity: int | None = None
    source: Literal["service", "fake", "replay"]


def split_model_version(model: str | None) -> tuple[str | None, str | None]:
    """Split a reported model id such as ``name-2025-04-14`` into ``(name, version)``."""
    if not model:
        return None, None
    match = _MODEL_VERSION_RE.match(model)
    if match is None:
        return model, None
    return match.group("model"), match.group("version")
