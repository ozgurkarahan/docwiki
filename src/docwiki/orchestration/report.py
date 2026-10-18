"""Run reports and cost receipts (architecture §7) built from the LLM usage ledger."""

from __future__ import annotations

import logging
import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import ValidationError

from docwiki.contracts.enums import STAGE_NAMES
from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.runs import (
    ContentUnderstandingUsage,
    CostReceipt,
    RunReport,
    StageReport,
)
from docwiki.contracts.runs import LlmUsage as UsageLine
from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, Storage
from docwiki.llm.ledger import UsageLedger

__all__ = [
    "ABANDONED_REASON",
    "LedgerCursor",
    "StageClock",
    "close_abandoned_runs",
    "cost_receipt",
]

logger = logging.getLogger("docwiki.engine")
ABANDONED_REASON = "abandoned: the execution ended before finishing"
_RUNNING_RE = re.compile(rb'"status"\s*:\s*"running"')


def close_abandoned_runs(storage: Storage, *, now: datetime) -> list[str]:
    """Mark run reports still ``running`` as ``failed`` (:data:`ABANDONED_REASON`).

    Call only while holding the run lease: no other execution can be running them, so such a
    report belongs to an execution that was stopped, timed out or crashed. A report changed in
    the meantime (ETag) or unreadable is left alone. Returns the run ids marked.
    """
    marked: list[str] = []
    for key in storage.list(StorageKeys.RUNS_DIR + "/"):
        if not key.endswith("/report.json"):
            continue
        try:
            data, etag = storage.read_with_etag(key)
        except KeyNotFoundError:
            continue
        if not _RUNNING_RE.search(data):
            continue
        try:
            report = RunReport.from_json(data)
        except (ValidationError, ValueError) as exc:
            logger.warning("cannot read the run report %s: %s", key, exc)
            continue
        if report.status != "running":
            continue
        closed = report.model_copy(
            update={
                "status": "failed",
                "finished_at": max(now, report.started_at),
                "errors": [*report.errors, ABANDONED_REASON],
            }
        )
        try:
            storage.write_bytes(key, closed.to_json().encode("utf-8"), if_match=etag)
        except PreconditionFailedError:
            continue
        logger.warning("run %s was still marked running: %s", report.run_id, ABANDONED_REASON)
        marked.append(report.run_id)
    return marked


class LedgerCursor:
    """Remembers where a run started in a (possibly shared) usage ledger."""

    def __init__(self, llm: Any) -> None:
        self.ledger: UsageLedger | None = getattr(llm, "ledger", None)
        self.start = len(self.ledger) if self.ledger is not None else 0

    def calls(self) -> int:
        return len(self.ledger) - self.start if self.ledger is not None else 0

    def run_ledger(self) -> UsageLedger | None:
        if self.ledger is None:
            return None
        sub = UsageLedger(self.ledger.prices)
        for record in self.ledger.records()[self.start :]:
            sub.record(record)
        return sub


def cost_receipt(
    cursor: LedgerCursor,
    *,
    duration_s: float,
    content_understanding: Iterable[ContentUnderstandingUsage] = (),
) -> CostReceipt:
    """Contract cost receipt (tokens × price table) of the calls made since ``cursor``."""
    cu = list(content_understanding)
    ledger = cursor.run_ledger()
    if ledger is None:
        return CostReceipt(
            price_table="unknown",
            content_understanding=cu,
            duration_s=round(duration_s, 3),
            notes=["the LLM client exposes no usage ledger; costs are not available"],
        )
    receipt = ledger.receipt()
    lines: list[UsageLine] = []
    for line in receipt.lines:
        price = ledger.prices.resolve(line.priced_as[0]) if line.priced_as else None
        lines.append(
            UsageLine(
                role=line.tier,
                deployment=line.deployment,
                model=line.models[0] if line.models else line.deployment,
                model_version=line.model_versions[0] if line.model_versions else None,
                calls=line.calls,
                input_tokens=line.input_tokens,
                cached_input_tokens=line.cached_input_tokens,
                output_tokens=line.output_tokens,
                price_input_per_1m=price.input_per_1m if price else None,
                price_cached_input_per_1m=price.cached_input_per_1m if price else None,
                price_output_per_1m=price.output_per_1m if price else None,
                cost=None if line.unpriced_calls else line.estimated_cost_usd,
            )
        )
    notes: list[str] = []
    if not receipt.prices_verified:
        notes.append("estimated with an unverified price table: check the prices before use")
    if receipt.totals.unpriced_calls:
        notes.append(f"{receipt.totals.unpriced_calls} model calls could not be priced")
    if receipt.totals.failed_calls:
        notes.append(f"{receipt.totals.failed_calls} model calls failed")
    total: float | None = receipt.totals.estimated_cost_usd
    if receipt.totals.calls and receipt.totals.unpriced_calls == receipt.totals.calls:
        total = None
    return CostReceipt(
        price_table=receipt.price_table.name,
        llm=lines,
        content_understanding=cu,
        duration_s=round(duration_s, 3),
        total_cost=total,
        notes=notes,
    )


@dataclass
class _StageRecord:
    started_at: datetime
    finished_at: datetime | None = None
    status: str = "done"
    items: int = 0
    cache_hits: int = 0
    failures: int = 0
    errors: list[str] = field(default_factory=list)


class StageClock:
    """Collects one :class:`StageReport` per stage (counters are safe across tasks)."""

    def __init__(self, now: Callable[[], datetime]) -> None:
        self._now = now
        self._records: dict[str, _StageRecord] = {}

    def start(self, stage: str) -> None:
        if stage not in self._records:
            self._records[stage] = _StageRecord(started_at=self._now())

    def count(self, stage: str, *, items: int = 0, cache_hits: int = 0, failures: int = 0) -> None:
        self.start(stage)
        record = self._records[stage]
        record.items += items
        record.cache_hits += cache_hits
        record.failures += failures

    def error(self, stage: str, message: str) -> None:
        self.start(stage)
        record = self._records[stage]
        if len(record.errors) < 50:
            record.errors.append(message)

    def finish(self, stage: str, status: str | None = None) -> None:
        self.start(stage)
        record = self._records[stage]
        record.finished_at = self._now()
        if status is not None:
            record.status = status

    def status(self, stage: str) -> str | None:
        record = self._records.get(stage)
        return record.status if record else None

    def abort(self) -> None:
        """Mark stages that started but never finished as failed."""
        for record in self._records.values():
            if record.finished_at is None:
                record.finished_at = self._now()
                record.status = "failed"

    def reports(self) -> list[StageReport]:
        reports: list[StageReport] = []
        for stage in STAGE_NAMES:
            record = self._records.get(stage)
            if record is None:
                continue
            finished = record.finished_at or self._now()
            reports.append(
                StageReport(
                    stage=stage,  # type: ignore[arg-type]
                    status=record.status,  # type: ignore[arg-type]
                    started_at=record.started_at,
                    finished_at=finished,
                    duration_s=round(max(0.0, (finished - record.started_at).total_seconds()), 3),
                    items=record.items,
                    cache_hits=record.cache_hits,
                    failures=record.failures,
                    errors=list(record.errors),
                )
            )
        return reports
