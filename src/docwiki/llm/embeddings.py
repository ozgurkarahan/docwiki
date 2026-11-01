"""Embedding clients: one protocol beside :class:`~docwiki.llm.client.LlmClient`.

``LlmClient`` stays "structured outputs only"; vectors go through :class:`EmbeddingClient`.
Every implementation shares :class:`BaseEmbeddingClient`, which validates the request, cuts it
into batches, checks the returned vectors, records one usage-ledger line per batch (role
``embed``), logs it and wraps it in a ``docwiki.llm.embed`` span. Logs and spans carry
identifiers, counts and tokens only, never the embedded text.

Implementations: :class:`~docwiki.llm.foundry_embeddings.FoundryEmbeddingClient` (live),
:class:`FakeEmbeddingClient` (deterministic hash vectors), :class:`RecordingEmbeddingClient` and
:class:`ReplayEmbeddingClient` (one JSON fixture per batch under
``<fixtures>/embed-<purpose>/<request_hash>.json``).
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
import os
import re
import struct
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import Any, ClassVar, Final, Literal, Protocol, Self, get_args, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from docwiki.llm.embed_input import EMBED_INPUT_MAX_CHARS
from docwiki.llm.errors import (
    LlmConfigurationError,
    LlmError,
    LlmReplayMissing,
    LlmServiceError,
)
from docwiki.llm.hashing import canonical_hash, normalize_newlines
from docwiki.llm.ledger import CallRecord, UsageLedger
from docwiki.llm.request import _validate_metadata, estimate_text_tokens
from docwiki.llm.settings import (
    DEFAULT_EMBED_BATCH_SIZE,
    DEFAULT_EMBED_DIMENSIONS,
    ENV_EMBED_DEPLOYMENT,
    ENV_FIXTURES,
    ENV_MODE,
    MAX_EMBED_BATCH_SIZE,
)
from docwiki.llm.telemetry import EMBED_SPAN_NAME, llm_span
from docwiki.llm.types import EMBED_ROLE, LlmUsage, MetadataValue, Origin

logger = logging.getLogger("docwiki.llm")

type EmbedPurpose = Literal["document", "query"]
EMBED_PURPOSES: tuple[EmbedPurpose, ...] = get_args(EmbedPurpose.__value__)
EMBED_REQUEST_FORMAT: Final = "docwiki.llm.embed-request/v1"
EMBED_RECORDING_FORMAT: Final = "docwiki.llm.embed-recording/v1"
INPUT_VERSION_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
FAKE_EMBED_MODEL = "fake-embed"


@dataclass(frozen=True)
class EmbedRequest:
    """One batch sent to the model; ``request_hash`` covers everything that shapes the vectors."""

    texts: tuple[str, ...]
    purpose: EmbedPurpose
    input_version: str
    dimensions: int
    metadata: Mapping[str, MetadataValue] = field(default_factory=dict)
    request_hash: str = ""

    @classmethod
    def build(
        cls,
        texts: Sequence[str],
        purpose: EmbedPurpose,
        input_version: str,
        dimensions: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> EmbedRequest:
        clean = _validate_texts(texts)
        _validate_common(purpose, input_version, dimensions)
        payload = embed_hash_payload(clean, purpose, input_version, dimensions)
        return cls(
            texts=clean,
            purpose=purpose,
            input_version=input_version,
            dimensions=dimensions,
            metadata=MappingProxyType(_validate_metadata(metadata)),
            request_hash=canonical_hash(payload),
        )

    @property
    def schema_name(self) -> str:
        """Ledger/fixture name of the batch kind: ``embed-document`` or ``embed-query``."""
        return f"embed-{self.purpose}"

    def hash_payload(self) -> dict[str, Any]:
        return embed_hash_payload(self.texts, self.purpose, self.input_version, self.dimensions)

    def estimated_input_tokens(self) -> int:
        return sum(estimate_text_tokens(text) for text in self.texts)


def embed_hash_payload(
    texts: Sequence[str], purpose: str, input_version: str, dimensions: int
) -> dict[str, Any]:
    return {
        "format": EMBED_REQUEST_FORMAT,
        "purpose": purpose,
        "input_version": input_version,
        "dimensions": dimensions,
        "texts": [normalize_newlines(text) for text in texts],
    }


@dataclass(frozen=True)
class EmbeddingBatch:
    """What an implementation returns for one :class:`EmbedRequest`."""

    vectors: tuple[tuple[float, ...], ...]
    usage: LlmUsage
    deployment: str
    model: str | None
    model_version: str | None = None
    latency_s: float = 0.0
    wait_s: float = 0.0
    retries: int = 0
    attempts: int = 1
    origin: Origin = "foundry"


@dataclass(frozen=True)
class EmbeddingResult:
    """Vectors of one :meth:`EmbeddingClient.embed` call, in input order, plus its accounting."""

    vectors: tuple[tuple[float, ...], ...]
    dimensions: int
    purpose: EmbedPurpose
    input_version: str
    usage: LlmUsage
    calls: int
    deployment: str
    model: str | None
    model_version: str | None
    request_hashes: tuple[str, ...]
    latency_s: float
    retries: int
    origin: Origin


class EmbeddingInfo(BaseModel):
    """What the embedding deployment serves (for cache keys, manifests and run reports)."""

    model_config = ConfigDict(frozen=True)

    deployment: str
    model_name: str | None = None
    model_version: str | None = None
    dimensions: int = Field(ge=1)
    sku: str | None = None
    capacity: int | None = None
    source: Literal["service", "fake", "replay"]


@runtime_checkable
class EmbeddingClient(Protocol):
    """Turns texts into unit-length vectors; texts are data, never instructions."""

    async def embed(
        self,
        texts: Sequence[str],
        purpose: EmbedPurpose,
        input_version: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> EmbeddingResult:
        """Embed ``texts`` (already shaped by the ``input_version`` rule) in input order."""
        ...

    async def describe(self) -> EmbeddingInfo:
        """Deployment, model, version and dimensions behind the client."""
        ...

    async def aclose(self) -> None:
        """Release network resources."""
        ...


BatchObserver = Callable[[EmbedRequest, EmbeddingBatch], None]


class BaseEmbeddingClient(ABC):
    """Template for embedding clients: subclasses implement :meth:`_run` and :meth:`describe`."""

    origin: ClassVar[Origin]
    measures_latency: ClassVar[bool] = True

    def __init__(
        self,
        *,
        dimensions: int = DEFAULT_EMBED_DIMENSIONS,
        batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
        ledger: UsageLedger | None = None,
        tracer_provider: Any | None = None,
    ) -> None:
        if isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions < 1:
            raise ValueError("dimensions must be a positive int")
        if not 1 <= batch_size <= MAX_EMBED_BATCH_SIZE:
            raise ValueError(f"batch_size must be between 1 and {MAX_EMBED_BATCH_SIZE}")
        self.dimensions = dimensions
        self.batch_size = batch_size
        self.ledger = ledger if ledger is not None else UsageLedger()
        self._tracer_provider = tracer_provider
        self._observers: list[BatchObserver] = []

    def add_observer(self, observer: BatchObserver) -> None:
        """Call ``observer(request, batch)`` after every successful batch (used for recording)."""
        self._observers.append(observer)

    async def embed(
        self,
        texts: Sequence[str],
        purpose: EmbedPurpose,
        input_version: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> EmbeddingResult:
        clean = _validate_texts(texts)
        _validate_common(purpose, input_version, self.dimensions)
        vectors: list[tuple[float, ...]] = []
        hashes: list[str] = []
        usage = LlmUsage()
        latency = 0.0
        retries = 0
        last: EmbeddingBatch | None = None
        for start in range(0, len(clean), self.batch_size):
            request = EmbedRequest.build(
                clean[start : start + self.batch_size],
                purpose,
                input_version,
                self.dimensions,
                metadata,
            )
            batch = await self.execute(request)
            vectors.extend(batch.vectors)
            hashes.append(request.request_hash)
            usage = usage + batch.usage
            latency += batch.latency_s
            retries += batch.retries
            last = batch
        assert last is not None  # _validate_texts refuses an empty list
        return EmbeddingResult(
            vectors=tuple(vectors),
            dimensions=self.dimensions,
            purpose=purpose,
            input_version=input_version,
            usage=usage,
            calls=len(hashes),
            deployment=last.deployment,
            model=last.model,
            model_version=last.model_version,
            request_hashes=tuple(hashes),
            latency_s=round(latency, 3),
            retries=retries,
            origin=last.origin,
        )

    async def execute(self, request: EmbedRequest) -> EmbeddingBatch:
        """Run one batch: records usage, logs and traces it, and checks the vectors."""
        started = time.perf_counter()
        attributes = _request_attributes(self.origin, request)
        tracer = self._tracer_provider
        with llm_span(attributes, tracer_provider=tracer, name=EMBED_SPAN_NAME) as span:
            try:
                batch = await self._run(request)
                batch = _checked(batch, request)
            except LlmError as exc:
                exc.with_context(
                    tier=EMBED_ROLE,
                    schema_name=request.schema_name,
                    request_hash=request.request_hash,
                )
                record = self._record(request, None, exc, self._elapsed(started))
                cost = self.ledger.record(record)
                span.set_attributes(_record_attributes(record, cost))
                _log(record, cost, len(request.texts))
                raise
            batch = _replace_latency(batch, self._elapsed(started))
            record = self._record(request, batch, None, batch.latency_s)
            cost = self.ledger.record(record)
            span.set_attributes(_record_attributes(record, cost))
            _log(record, cost, len(request.texts))
        for observer in self._observers:
            observer(request, batch)
        return batch

    @abstractmethod
    async def _run(self, request: EmbedRequest) -> EmbeddingBatch:
        """Produce the vectors of ``request`` or raise an :class:`LlmError`."""

    @abstractmethod
    async def describe(self) -> EmbeddingInfo: ...

    async def aclose(self) -> None:
        return None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    def _pricing_model(self) -> str | None:
        return None

    def _elapsed(self, started: float) -> float:
        return time.perf_counter() - started if self.measures_latency else 0.0

    def _record(
        self,
        request: EmbedRequest,
        batch: EmbeddingBatch | None,
        exc: LlmError | None,
        latency_s: float,
    ) -> CallRecord:
        common: dict[str, Any] = {
            "tier": EMBED_ROLE,
            "pricing_model": self._pricing_model(),
            "schema_name": request.schema_name,
            "prompt_version": request.input_version,
            "request_hash": request.request_hash,
            "latency_s": latency_s,
            "metadata": dict(request.metadata),
        }
        if batch is not None:
            return CallRecord(
                **common,
                deployment=batch.deployment,
                model=batch.model,
                model_version=batch.model_version,
                origin=batch.origin,
                usage=batch.usage,
                wait_s=batch.wait_s,
                retries=batch.retries,
                attempts=batch.attempts,
            )
        assert exc is not None
        return CallRecord(
            **common,
            deployment=exc.deployment or "unconfigured",
            model=exc.model,
            origin=self.origin,
            ok=False,
            error=type(exc).__name__,
            usage=exc.usage,
            retries=exc.retries,
            attempts=exc.attempts,
        )


class FakeEmbeddingClient(BaseEmbeddingClient):
    """Deterministic offline vectors: SHA-256 of model, dimensions and text, then L2-normalised.

    The same text always gives the same vector; different texts give unrelated vectors, so the
    fake proves plumbing, not semantics. Usage is the 4-characters-per-token estimate.
    """

    origin: ClassVar[Origin] = "fake"
    measures_latency: ClassVar[bool] = False

    def __init__(
        self,
        *,
        dimensions: int = DEFAULT_EMBED_DIMENSIONS,
        batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
        model: str = FAKE_EMBED_MODEL,
        ledger: UsageLedger | None = None,
        tracer_provider: Any | None = None,
    ) -> None:
        super().__init__(
            dimensions=dimensions,
            batch_size=batch_size,
            ledger=ledger,
            tracer_provider=tracer_provider,
        )
        self.model = model
        self.requests: list[EmbedRequest] = []

    @property
    def deployment(self) -> str:
        return "fake-embed"

    async def describe(self) -> EmbeddingInfo:
        return EmbeddingInfo(
            deployment=self.deployment,
            model_name=self.model,
            dimensions=self.dimensions,
            source="fake",
        )

    async def _run(self, request: EmbedRequest) -> EmbeddingBatch:
        self.requests.append(request)
        vectors = tuple(fake_vector(text, request.dimensions, self.model) for text in request.texts)
        return EmbeddingBatch(
            vectors=vectors,
            usage=LlmUsage(input_tokens=request.estimated_input_tokens()),
            deployment=self.deployment,
            model=self.model,
            origin="fake",
        )


def fake_vector(text: str, dimensions: int, model: str = FAKE_EMBED_MODEL) -> tuple[float, ...]:
    """The unit vector :class:`FakeEmbeddingClient` returns for ``text``."""
    seed = f"{model}\n{dimensions}\n{normalize_newlines(text)}".encode()
    raw = bytearray()
    counter = 0
    while len(raw) < dimensions * 4:
        raw.extend(hashlib.sha256(seed + counter.to_bytes(4, "big")).digest())
        counter += 1
    values = [
        (value / 0xFFFFFFFF) * 2.0 - 1.0
        for value in struct.unpack(f">{dimensions}I", bytes(raw[: dimensions * 4]))
    ]
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return tuple(value / norm for value in values)


# ---------------------------------------------------------------------- record / replay


class EmbedRecording(BaseModel):
    """Content of one embedding fixture file (one batch)."""

    model_config = ConfigDict(extra="forbid")

    format: Literal["docwiki.llm.embed-recording/v1"] = EMBED_RECORDING_FORMAT
    request_hash: str
    request: dict[str, Any]
    vectors: list[list[float]]
    usage: LlmUsage
    deployment: str
    model: str | None = None
    model_version: str | None = None


def embed_fixture_path(fixtures_dir: Path | str, request: EmbedRequest) -> Path:
    return Path(fixtures_dir) / request.schema_name / f"{request.request_hash}.json"


def write_embed_recording(
    fixtures_dir: Path | str, request: EmbedRequest, batch: EmbeddingBatch
) -> Path:
    recording = EmbedRecording(
        request_hash=request.request_hash,
        request=request.hash_payload(),
        vectors=[list(vector) for vector in batch.vectors],
        usage=batch.usage,
        deployment=batch.deployment,
        model=batch.model,
        model_version=batch.model_version,
    )
    path = embed_fixture_path(fixtures_dir, request)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(recording.model_dump(mode="json"), indent=2, sort_keys=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(text + "\n", encoding="utf-8", newline="\n")
    os.replace(temporary, path)
    return path


def read_embed_recording(path: Path) -> EmbedRecording:
    where = f"{path.parent.name}/{path.name}"
    try:
        recording = EmbedRecording.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise LlmConfigurationError(
            f"Embedding fixture {where} is unreadable or malformed: {exc}"
        ) from exc
    if canonical_hash(recording.request) != recording.request_hash:
        raise LlmConfigurationError(
            f"Embedding fixture {where} does not match its request hash (was the request "
            "section edited?); re-record it"
        )
    return recording


class RecordingEmbeddingClient:
    """Wraps a live client and writes every successful batch as a fixture file."""

    def __init__(self, inner: BaseEmbeddingClient, fixtures_dir: Path | str) -> None:
        self.inner = inner
        self.fixtures_dir = Path(fixtures_dir)
        self.recorded: list[Path] = []
        inner.add_observer(self._write)

    @property
    def ledger(self) -> UsageLedger:
        return self.inner.ledger

    def _write(self, request: EmbedRequest, batch: EmbeddingBatch) -> None:
        self.recorded.append(write_embed_recording(self.fixtures_dir, request, batch))

    async def embed(
        self,
        texts: Sequence[str],
        purpose: EmbedPurpose,
        input_version: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> EmbeddingResult:
        return await self.inner.embed(texts, purpose, input_version, metadata)

    async def describe(self) -> EmbeddingInfo:
        return await self.inner.describe()

    async def aclose(self) -> None:
        await self.inner.aclose()

    async def __aenter__(self) -> RecordingEmbeddingClient:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()


class ReplayEmbeddingClient(BaseEmbeddingClient):
    """Serves recorded batches; a missing fixture raises :class:`LlmReplayMissing`.

    Batches are cut exactly as when recording, so ``batch_size`` and ``dimensions`` must match.
    """

    origin: ClassVar[Origin] = "replay"
    measures_latency: ClassVar[bool] = False

    def __init__(
        self,
        fixtures_dir: Path | str,
        *,
        dimensions: int = DEFAULT_EMBED_DIMENSIONS,
        batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
        ledger: UsageLedger | None = None,
        tracer_provider: Any | None = None,
    ) -> None:
        super().__init__(
            dimensions=dimensions,
            batch_size=batch_size,
            ledger=ledger,
            tracer_provider=tracer_provider,
        )
        self.fixtures_dir = Path(fixtures_dir)

    async def describe(self) -> EmbeddingInfo:
        return EmbeddingInfo(
            deployment="replay-embed", dimensions=self.dimensions, source="replay"
        )

    async def _run(self, request: EmbedRequest) -> EmbeddingBatch:
        path = embed_fixture_path(self.fixtures_dir, request)
        if not path.is_file():
            raise LlmReplayMissing(
                f"No recorded embedding batch for '{request.schema_name}' (input version "
                f"'{request.input_version}', {request.dimensions} dimensions, "
                f"{len(request.texts)} texts, batch size {self.batch_size}, request hash "
                f"{request.request_hash}) in the fixtures directory: expected "
                f"{request.schema_name}/{path.name}. Record it with {ENV_MODE}=record, "
                f"{ENV_FIXTURES} and {ENV_EMBED_DEPLOYMENT} set, using the same batch size.",
                fixture=str(path),
                deployment="replay-embed",
            )
        recording = read_embed_recording(path)
        return EmbeddingBatch(
            vectors=tuple(tuple(vector) for vector in recording.vectors),
            usage=recording.usage,
            deployment=recording.deployment,
            model=recording.model,
            model_version=recording.model_version,
            origin="replay",
        )


# ---------------------------------------------------------------------- helpers


def _validate_texts(texts: Sequence[str]) -> tuple[str, ...]:
    if isinstance(texts, str) or not isinstance(texts, Sequence):
        raise TypeError("texts must be a sequence of str")
    clean = tuple(texts)
    if not clean:
        raise ValueError("texts must not be empty")
    for index, text in enumerate(clean):
        if not isinstance(text, str):
            raise TypeError(f"texts[{index}] must be a str")
        if not text.strip():
            raise ValueError(f"texts[{index}] is empty")
        if len(text) > EMBED_INPUT_MAX_CHARS:
            raise ValueError(
                f"texts[{index}] has {len(text)} characters, more than {EMBED_INPUT_MAX_CHARS}; "
                "shape it with build_embed_input() first"
            )
    return clean


def _validate_common(purpose: str, input_version: str, dimensions: int) -> None:
    if purpose not in EMBED_PURPOSES:
        raise ValueError(f"purpose must be one of {', '.join(EMBED_PURPOSES)}, got {purpose!r}")
    if not isinstance(input_version, str) or not INPUT_VERSION_RE.match(input_version):
        raise ValueError(f"input_version must match {INPUT_VERSION_RE.pattern}")
    if isinstance(dimensions, bool) or not isinstance(dimensions, int) or dimensions < 1:
        raise ValueError("dimensions must be a positive int")


def _checked(batch: EmbeddingBatch, request: EmbedRequest) -> EmbeddingBatch:
    """Errors surface: a wrong count, size or a non-finite value is a service error."""
    context: dict[str, Any] = {
        "deployment": batch.deployment,
        "model": batch.model,
        "usage": batch.usage,
        "retries": batch.retries,
        "attempts": batch.attempts,
    }
    if len(batch.vectors) != len(request.texts):
        raise LlmServiceError(
            f"Embedding deployment '{batch.deployment}' returned {len(batch.vectors)} vectors "
            f"for {len(request.texts)} texts",
            **context,
        )
    for index, vector in enumerate(batch.vectors):
        if len(vector) != request.dimensions:
            raise LlmServiceError(
                f"Embedding deployment '{batch.deployment}' returned a vector of {len(vector)} "
                f"dimensions at position {index}, expected {request.dimensions}",
                **context,
            )
        if not all(math.isfinite(value) for value in vector):
            raise LlmServiceError(
                f"Embedding deployment '{batch.deployment}' returned a non-finite value at "
                f"position {index}",
                **context,
            )
    return batch


def _replace_latency(batch: EmbeddingBatch, latency_s: float) -> EmbeddingBatch:
    return replace(batch, latency_s=latency_s)


def _request_attributes(origin: Origin, request: EmbedRequest) -> dict[str, Any]:
    attributes: dict[str, Any] = {
        "docwiki.llm.origin": origin,
        "docwiki.llm.tier": EMBED_ROLE,
        "docwiki.llm.schema_name": request.schema_name,
        "docwiki.llm.prompt_version": request.input_version,
        "docwiki.llm.request_hash": request.request_hash,
        "docwiki.llm.embed.texts": len(request.texts),
        "docwiki.llm.embed.dimensions": request.dimensions,
        "gen_ai.operation.name": "embeddings",
    }
    for key, value in request.metadata.items():
        attributes[f"docwiki.llm.metadata.{key}"] = value
    return attributes


def _record_attributes(record: CallRecord, cost: float | None) -> dict[str, Any]:
    return {
        "docwiki.llm.outcome": "ok" if record.ok else record.error,
        "docwiki.llm.deployment": record.deployment,
        "docwiki.llm.model": record.model,
        "docwiki.llm.model_version": record.model_version,
        "docwiki.llm.input_tokens": record.usage.input_tokens,
        "docwiki.llm.latency_ms": round(record.latency_s * 1000.0, 1),
        "docwiki.llm.wait_ms": round(record.wait_s * 1000.0, 1),
        "docwiki.llm.retries": record.retries,
        "docwiki.llm.attempts": record.attempts,
        "docwiki.llm.estimated_cost_usd": cost,
        "gen_ai.request.model": record.deployment,
        "gen_ai.response.model": record.model,
        "gen_ai.usage.input_tokens": record.usage.input_tokens,
    }


def _log(record: CallRecord, cost: float | None, texts: int) -> None:
    outcome = "ok" if record.ok else f"failed ({record.error})"
    cost_text = "unpriced" if cost is None else f"{cost:.6f}"
    logger.log(
        logging.INFO if record.ok else logging.WARNING,
        "embed call %s: deployment=%s model=%s version=%s kind=%s input=%s texts=%d "
        "tokens_in=%d latency=%.3fs wait=%.3fs retries=%d cost_usd=%s origin=%s",
        outcome,
        record.deployment,
        record.model,
        record.model_version,
        record.schema_name,
        record.prompt_version,
        texts,
        record.usage.input_tokens,
        record.latency_s,
        record.wait_s,
        record.retries,
        cost_text,
        record.origin,
        extra={
            "docwiki_llm": {
                **record.model_dump(mode="json", exclude={"metadata"}),
                "stage": record.stage,
                "texts": texts,
                "estimated_cost_usd": cost,
            }
        },
    )
