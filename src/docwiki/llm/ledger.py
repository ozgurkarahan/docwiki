"""Usage ledger: one record per LLM call, aggregated into a cost receipt for the run report."""

from __future__ import annotations

import threading
from collections import Counter
from dataclasses import dataclass, field
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field

from docwiki.llm.prices import PriceTable, PriceTableInfo, ResolvedPrice
from docwiki.llm.types import LlmUsage, MetadataValue, Origin, UsageRole

RECEIPT_FORMAT: Final = "docwiki.llm.receipt/v1"


class CallRecord(BaseModel):
    """What the ledger keeps about one model call (successful or not).

    ``tier`` is the usage role: ``fast``/``smart`` for ``structured`` calls, ``embed`` for one
    embedding batch (``schema_name`` is then ``embed-<purpose>`` and ``prompt_version`` the input
    rule version)."""

    model_config = ConfigDict(frozen=True)

    tier: UsageRole
    deployment: str
    model: str | None = None
    model_version: str | None = None
    pricing_model: str | None = None
    schema_name: str
    prompt_version: str
    request_hash: str
    origin: Origin
    ok: bool = True
    error: str | None = None
    usage: LlmUsage = Field(default_factory=LlmUsage)
    latency_s: float = 0.0
    wait_s: float = 0.0
    retries: int = 0
    attempts: int = 1
    metadata: dict[str, MetadataValue] = Field(default_factory=dict)

    @property
    def stage(self) -> str | None:
        value = self.metadata.get("stage")
        return value if isinstance(value, str) and value else None


class ReceiptTotals(BaseModel):
    calls: int = 0
    failed_calls: int = 0
    attempts: int = 0
    retries: int = 0
    input_tokens: int = 0
    cached_input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    latency_s: float = 0.0
    wait_s: float = 0.0
    estimated_cost_usd: float = 0.0
    unpriced_calls: int = 0


class ReceiptLine(ReceiptTotals):
    """Totals of one tier/deployment pair."""

    tier: UsageRole
    deployment: str
    models: list[str] = Field(default_factory=list)
    model_versions: list[str] = Field(default_factory=list)
    priced_as: list[str] = Field(default_factory=list)
    prices_verified: bool = True
    max_latency_s: float = 0.0
    origins: dict[str, int] = Field(default_factory=dict)


class PromptUsage(BaseModel):
    schema_name: str
    prompt_version: str
    tier: UsageRole
    calls: int


class LlmReceipt(BaseModel):
    """Cost receipt of a run: tokens × price table, per tier/deployment, stage and prompt."""

    format: Literal["docwiki.llm.receipt/v1"] = RECEIPT_FORMAT
    currency: Literal["USD"] = "USD"
    price_table: PriceTableInfo
    prices_verified: bool
    lines: list[ReceiptLine]
    stages: dict[str, ReceiptTotals]
    prompts: list[PromptUsage]
    totals: ReceiptTotals


@dataclass
class _Accumulator:
    calls: int = 0
    failed_calls: int = 0
    attempts: int = 0
    retries: int = 0
    usage: LlmUsage = field(default_factory=LlmUsage)
    latency_s: float = 0.0
    max_latency_s: float = 0.0
    wait_s: float = 0.0
    cost: float = 0.0
    unpriced: int = 0
    verified: bool = True
    models: set[str] = field(default_factory=set)
    versions: set[str] = field(default_factory=set)
    priced_as: set[str] = field(default_factory=set)
    origins: Counter[str] = field(default_factory=Counter)

    def add(self, record: CallRecord, price: ResolvedPrice | None) -> None:
        self.calls += 1
        self.failed_calls += 0 if record.ok else 1
        self.attempts += record.attempts
        self.retries += record.retries
        self.usage = self.usage + record.usage
        self.latency_s += record.latency_s
        self.max_latency_s = max(self.max_latency_s, record.latency_s)
        self.wait_s += record.wait_s
        self.origins[record.origin] += 1
        if record.model:
            self.models.add(record.model)
        if record.model_version:
            self.versions.add(record.model_version)
        if price is None:
            self.unpriced += 1
            self.verified = False
        else:
            self.cost += price.cost(record.usage)
            self.priced_as.add(price.model_id)
            self.verified = self.verified and price.verified

    def totals(self) -> ReceiptTotals:
        return ReceiptTotals(
            calls=self.calls,
            failed_calls=self.failed_calls,
            attempts=self.attempts,
            retries=self.retries,
            input_tokens=self.usage.input_tokens,
            cached_input_tokens=self.usage.cached_input_tokens,
            output_tokens=self.usage.output_tokens,
            reasoning_tokens=self.usage.reasoning_tokens,
            latency_s=round(self.latency_s, 3),
            wait_s=round(self.wait_s, 3),
            estimated_cost_usd=round(self.cost, 6),
            unpriced_calls=self.unpriced,
        )


class UsageLedger:
    """Thread-safe collection of :class:`CallRecord` with cost estimation."""

    def __init__(self, prices: PriceTable | None = None) -> None:
        self._prices = prices if prices is not None else PriceTable.packaged()
        self._records: list[CallRecord] = []
        self._lock = threading.Lock()

    @property
    def prices(self) -> PriceTable:
        return self._prices

    def price_for(self, record: CallRecord) -> ResolvedPrice | None:
        return self._prices.resolve(
            self._prices.model_for_deployment(record.deployment),
            record.pricing_model,
            record.model,
            record.deployment,
        )

    def cost_of(self, record: CallRecord) -> float | None:
        price = self.price_for(record)
        return None if price is None else price.cost(record.usage)

    def record(self, record: CallRecord) -> float | None:
        """Store ``record``; return its estimated cost in USD (``None`` when unpriced)."""
        with self._lock:
            self._records.append(record)
        return self.cost_of(record)

    def records(self) -> list[CallRecord]:
        with self._lock:
            return list(self._records)

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)

    def receipt(self) -> LlmReceipt:
        records = self.records()
        total = _Accumulator()
        lines: dict[tuple[UsageRole, str], _Accumulator] = {}
        stages: dict[str, _Accumulator] = {}
        prompts: Counter[tuple[str, str, UsageRole]] = Counter()
        for record in records:
            price = self.price_for(record)
            total.add(record, price)
            lines.setdefault((record.tier, record.deployment), _Accumulator()).add(record, price)
            if record.stage:
                stages.setdefault(record.stage, _Accumulator()).add(record, price)
            prompts[(record.schema_name, record.prompt_version, record.tier)] += 1
        return LlmReceipt(
            price_table=self._prices.info,
            prices_verified=total.verified,
            lines=[
                ReceiptLine(
                    **acc.totals().model_dump(),
                    tier=tier,
                    deployment=deployment,
                    models=sorted(acc.models),
                    model_versions=sorted(acc.versions),
                    priced_as=sorted(acc.priced_as),
                    prices_verified=acc.verified,
                    max_latency_s=round(acc.max_latency_s, 3),
                    origins=dict(sorted(acc.origins.items())),
                )
                for (tier, deployment), acc in sorted(lines.items())
            ],
            stages={name: acc.totals() for name, acc in sorted(stages.items())},
            prompts=[
                PromptUsage(
                    schema_name=schema_name, prompt_version=prompt_version, tier=tier, calls=calls
                )
                for (schema_name, prompt_version, tier), calls in sorted(prompts.items())
            ],
            totals=total.totals(),
        )
