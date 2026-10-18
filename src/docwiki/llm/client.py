"""The ``LlmClient`` protocol and the base class shared by every implementation.

The base class owns everything that must behave identically for live, fake and replayed calls:
request validation and hashing, the usage ledger, per-call logging and the OpenTelemetry span.
"""

from __future__ import annotations

import dataclasses
import logging
import time
from abc import ABC, abstractmethod
from collections.abc import Mapping, Sequence
from typing import Any, ClassVar, Protocol, Self, runtime_checkable

from docwiki.llm.errors import LlmError
from docwiki.llm.ledger import CallRecord, UsageLedger
from docwiki.llm.request import LlmRequest
from docwiki.llm.telemetry import llm_span
from docwiki.llm.types import (
    ContentPart,
    DeploymentInfo,
    Origin,
    StructuredResult,
    T,
    Tier,
)

logger = logging.getLogger("docwiki.llm")


@runtime_checkable
class LlmClient(Protocol):
    """The only way DocWiki talks to models: structured outputs, no tools."""

    async def structured(
        self,
        tier: Tier,
        system: str,
        user: str | Sequence[ContentPart],
        output: type[T],
        schema_name: str,
        prompt_version: str,
        max_output_tokens: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> StructuredResult[T]:
        """Run one structured-output call and return the validated pydantic object."""
        ...

    async def describe(self, tier: Tier) -> DeploymentInfo:
        """Deployment and model (version) behind ``tier``, for cache keys and run reports."""
        ...

    async def aclose(self) -> None:
        """Release network resources."""
        ...


class BaseLlmClient(ABC):
    """Template for clients: subclasses implement :meth:`_run` (and :meth:`describe`)."""

    origin: ClassVar[Origin]
    measures_latency: ClassVar[bool] = True

    def __init__(
        self, *, ledger: UsageLedger | None = None, tracer_provider: Any | None = None
    ) -> None:
        self.ledger = ledger if ledger is not None else UsageLedger()
        self._tracer_provider = tracer_provider

    async def structured(
        self,
        tier: Tier,
        system: str,
        user: str | Sequence[ContentPart],
        output: type[T],
        schema_name: str,
        prompt_version: str,
        max_output_tokens: int,
        metadata: Mapping[str, Any] | None = None,
    ) -> StructuredResult[T]:
        request = LlmRequest.build(
            tier, system, user, output, schema_name, prompt_version, max_output_tokens, metadata
        )
        return await self.execute(request)

    async def execute(self, request: LlmRequest) -> StructuredResult[Any]:
        """Run an already built request (records usage, logs and traces it)."""
        started = time.perf_counter()
        attributes = self._request_attributes(request)
        with llm_span(attributes, tracer_provider=self._tracer_provider) as span:
            try:
                result = await self._run(request)
            except LlmError as exc:
                exc.with_context(
                    tier=request.tier,
                    schema_name=request.schema_name,
                    request_hash=request.request_hash,
                )
                record = self._failure_record(request, exc, self._elapsed(started))
                cost = self.ledger.record(record)
                span.set_attributes(_record_attributes(record, cost))
                _log(record, cost)
                raise
            result = dataclasses.replace(result, latency_s=self._elapsed(started))
            record = self._success_record(request, result)
            cost = self.ledger.record(record)
            span.set_attributes(_record_attributes(record, cost))
            _log(record, cost)
            return result

    @abstractmethod
    async def _run(self, request: LlmRequest) -> StructuredResult[Any]:
        """Produce the result for ``request`` or raise an :class:`LlmError`."""

    @abstractmethod
    async def describe(self, tier: Tier) -> DeploymentInfo: ...

    async def aclose(self) -> None:
        return None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc_info: object) -> None:
        await self.aclose()

    def _pricing_model(self, tier: Tier) -> str | None:
        """Model id used for pricing when the price table has no deployment mapping."""
        return None

    def _elapsed(self, started: float) -> float:
        return time.perf_counter() - started if self.measures_latency else 0.0

    def _request_attributes(self, request: LlmRequest) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "docwiki.llm.origin": self.origin,
            "docwiki.llm.tier": request.tier,
            "docwiki.llm.schema_name": request.schema_name,
            "docwiki.llm.prompt_version": request.prompt_version,
            "docwiki.llm.request_hash": request.request_hash,
            "docwiki.llm.max_output_tokens": request.max_output_tokens,
            "gen_ai.operation.name": "chat",
            "gen_ai.request.max_tokens": request.max_output_tokens,
        }
        for key, value in request.metadata.items():
            attributes[f"docwiki.llm.metadata.{key}"] = value
        return attributes

    def _success_record(self, request: LlmRequest, result: StructuredResult[Any]) -> CallRecord:
        return CallRecord(
            tier=request.tier,
            deployment=result.deployment,
            model=result.model,
            model_version=result.model_version,
            pricing_model=self._pricing_model(request.tier),
            schema_name=request.schema_name,
            prompt_version=request.prompt_version,
            request_hash=request.request_hash,
            origin=result.origin,
            usage=result.usage,
            latency_s=result.latency_s,
            wait_s=result.wait_s,
            retries=result.retries,
            attempts=result.attempts,
            metadata=dict(request.metadata),
        )

    def _failure_record(self, request: LlmRequest, exc: LlmError, latency_s: float) -> CallRecord:
        return CallRecord(
            tier=request.tier,
            deployment=exc.deployment or "unconfigured",
            model=exc.model,
            pricing_model=self._pricing_model(request.tier),
            schema_name=request.schema_name,
            prompt_version=request.prompt_version,
            request_hash=request.request_hash,
            origin=self.origin,
            ok=False,
            error=type(exc).__name__,
            usage=exc.usage,
            latency_s=latency_s,
            retries=exc.retries,
            attempts=exc.attempts,
            metadata=dict(request.metadata),
        )


def _record_attributes(record: CallRecord, cost: float | None) -> dict[str, Any]:
    return {
        "docwiki.llm.outcome": "ok" if record.ok else record.error,
        "docwiki.llm.deployment": record.deployment,
        "docwiki.llm.model": record.model,
        "docwiki.llm.model_version": record.model_version,
        "docwiki.llm.input_tokens": record.usage.input_tokens,
        "docwiki.llm.output_tokens": record.usage.output_tokens,
        "docwiki.llm.cached_input_tokens": record.usage.cached_input_tokens,
        "docwiki.llm.latency_ms": round(record.latency_s * 1000.0, 1),
        "docwiki.llm.wait_ms": round(record.wait_s * 1000.0, 1),
        "docwiki.llm.retries": record.retries,
        "docwiki.llm.attempts": record.attempts,
        "docwiki.llm.estimated_cost_usd": cost,
        "gen_ai.request.model": record.deployment,
        "gen_ai.response.model": record.model,
        "gen_ai.usage.input_tokens": record.usage.input_tokens,
        "gen_ai.usage.output_tokens": record.usage.output_tokens,
    }


def _log(record: CallRecord, cost: float | None) -> None:
    outcome = "ok" if record.ok else f"failed ({record.error})"
    cost_text = "unpriced" if cost is None else f"{cost:.6f}"
    logger.log(
        logging.INFO if record.ok else logging.WARNING,
        "llm call %s: tier=%s deployment=%s model=%s version=%s schema=%s prompt=%s "
        "tokens_in=%d tokens_out=%d latency=%.3fs wait=%.3fs retries=%d cost_usd=%s origin=%s",
        outcome,
        record.tier,
        record.deployment,
        record.model,
        record.model_version,
        record.schema_name,
        record.prompt_version,
        record.usage.input_tokens,
        record.usage.output_tokens,
        record.latency_s,
        record.wait_s,
        record.retries,
        cost_text,
        record.origin,
        extra={
            "docwiki_llm": {
                **record.model_dump(mode="json", exclude={"metadata"}),
                "stage": record.stage,
                "estimated_cost_usd": cost,
            }
        },
    )
