"""Price table used to estimate the cost of LLM calls (USD per 1M tokens)."""

from __future__ import annotations

import functools
from collections.abc import Mapping
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from docwiki.llm.errors import LlmConfigurationError
from docwiki.llm.hashing import sha256_hex
from docwiki.llm.types import LlmUsage

PACKAGED_PRICE_TABLE = "prices.yaml"
TOKENS_PER_PRICE_UNIT = 1_000_000


class ModelPrice(BaseModel):
    """Prices of one model in USD per 1M tokens."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    input: float = Field(ge=0)
    output: float = Field(ge=0)
    cached_input: float | None = Field(default=None, ge=0)
    verified: bool | None = None


class PriceTableFile(BaseModel):
    """On-disk format of a price table (YAML)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    format: Literal["docwiki.llm.prices/v1"]
    currency: Literal["USD"]
    unit: Literal["per_1m_tokens"]
    verified: bool = False
    source: str = ""
    models: dict[str, ModelPrice]
    deployments: dict[str, str] = Field(default_factory=dict)


class PriceTableInfo(BaseModel):
    """Identifies the price table behind a receipt (file name only, never a local path)."""

    model_config = ConfigDict(frozen=True)

    name: str
    sha256: str
    verified: bool
    source: str


@dataclass(frozen=True)
class ResolvedPrice:
    model_id: str
    input_per_1m: float
    cached_input_per_1m: float
    output_per_1m: float
    verified: bool

    def cost(self, usage: LlmUsage) -> float:
        cached = min(usage.cached_input_tokens, usage.input_tokens)
        uncached = usage.input_tokens - cached
        total = (
            uncached * self.input_per_1m
            + cached * self.cached_input_per_1m
            + usage.output_tokens * self.output_per_1m
        )
        return total / TOKENS_PER_PRICE_UNIT


class PriceTable:
    """Model prices plus an optional deployment-name → model-id mapping."""

    def __init__(self, data: PriceTableFile, *, name: str, sha256: str) -> None:
        self._data = data
        self._models = {key.strip().lower(): key for key in data.models}
        self.info = PriceTableInfo(
            name=name, sha256=sha256, verified=data.verified, source=data.source
        )

    @classmethod
    def packaged(cls) -> PriceTable:
        """The price table shipped with DocWiki (placeholder prices, ``verified: false``)."""
        return _packaged_table()

    @classmethod
    def load(cls, path: Path | str | None = None) -> PriceTable:
        """Load a YAML price table; ``None`` returns the packaged table."""
        if path is None:
            return cls.packaged()
        file = Path(path)
        try:
            raw = file.read_bytes()
        except OSError as exc:
            raise LlmConfigurationError(
                f"Cannot read the LLM price table {file.name!r}: {exc.strerror}"
            ) from None
        return cls.from_yaml(raw, name=file.name)

    @classmethod
    def from_yaml(cls, raw: bytes | str, *, name: str) -> PriceTable:
        data_bytes = raw.encode("utf-8") if isinstance(raw, str) else raw
        try:
            parsed = yaml.safe_load(data_bytes.decode("utf-8"))
        except (UnicodeDecodeError, yaml.YAMLError) as exc:
            raise LlmConfigurationError(f"Price table {name!r} is not valid YAML: {exc}") from None
        return cls.from_mapping(parsed, name=name, sha256=sha256_hex(data_bytes))

    @classmethod
    def from_mapping(
        cls, data: Mapping[str, Any] | Any, *, name: str = "inline", sha256: str | None = None
    ) -> PriceTable:
        try:
            parsed = PriceTableFile.model_validate(data)
        except ValidationError as exc:
            details = "; ".join(
                f"{'.'.join(str(p) for p in error['loc'])}: {error['msg']}"
                for error in exc.errors(include_url=False, include_input=False)
            )
            raise LlmConfigurationError(f"Invalid price table {name!r}: {details}") from None
        if sha256 is None:
            sha256 = sha256_hex(parsed.model_dump_json().encode("utf-8"))
        return cls(parsed, name=name, sha256=sha256)

    @property
    def verified(self) -> bool:
        return self._data.verified

    @property
    def models(self) -> Mapping[str, ModelPrice]:
        return self._data.models

    def model_for_deployment(self, deployment: str | None) -> str | None:
        if not deployment:
            return None
        return self._data.deployments.get(deployment)

    def resolve(self, *candidates: str | None) -> ResolvedPrice | None:
        """Price of the first candidate model id found (exact, then longest ``<id>-`` prefix)."""
        for candidate in candidates:
            key = self._match(candidate)
            if key is not None:
                price = self._data.models[key]
                verified = self._data.verified if price.verified is None else price.verified
                return ResolvedPrice(
                    model_id=key,
                    input_per_1m=price.input,
                    cached_input_per_1m=(
                        price.input if price.cached_input is None else price.cached_input
                    ),
                    output_per_1m=price.output,
                    verified=verified,
                )
        return None

    def _match(self, candidate: str | None) -> str | None:
        if not candidate:
            return None
        wanted = candidate.strip().lower()
        if wanted in self._models:
            return self._models[wanted]
        best: str | None = None
        for lowered in self._models:
            if wanted.startswith(f"{lowered}-") and (best is None or len(lowered) > len(best)):
                best = lowered
        return self._models[best] if best is not None else None


@functools.cache
def _packaged_table() -> PriceTable:
    raw = resources.files("docwiki.llm").joinpath(PACKAGED_PRICE_TABLE).read_bytes()
    return PriceTable.from_yaml(raw, name=f"{PACKAGED_PRICE_TABLE} (packaged)")
