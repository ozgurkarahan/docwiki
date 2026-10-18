"""Failure semantics of the run control: deterministic failures are acknowledged, systemic ones
are retried, and reports left ``running`` by a stopped execution are closed as abandoned."""

from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest
from engine_stubs import CANARY, render_source_page, stub_engine

from docwiki.contracts.layout import run_report_key
from docwiki.contracts.queue import QueueMessage
from docwiki.contracts.runs import CostReceipt, RunReport, VersionInfo
from docwiki.orchestration.pipeline import DETERMINISTIC_NOTE
from docwiki.orchestration.report import ABANDONED_REASON
from docwiki.release.publish import read_current_pointer
from docwiki.storage.queue import AzureStorageQueue, StorageQueue, WorkQueue

STORAGE_TESTS = Path(__file__).resolve().parents[1] / "storage"
if str(STORAGE_TESTS) not in sys.path:
    sys.path.insert(0, str(STORAGE_TESTS))

from fake_azure import Clock, FakeQueueClient  # noqa: E402


def _ingest(key: str) -> str:
    return QueueMessage(
        kind="ingest",
        requested_by="librarian",
        idempotency_key=key,
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
    ).to_body()


def _queue(kind: str, harness, clock: Clock) -> WorkQueue:
    if kind == "folder":
        return StorageQueue(harness.storage, clock=clock)
    return AzureStorageQueue(
        queue_client=FakeQueueClient(clock), poison_client=FakeQueueClient(clock)
    )


def _leaky_render(*args, **kwargs):
    page, cited = render_source_page(*args, **kwargs)
    body = page.body.replace("## Figures", f"Leaked: {CANARY}\n\n## Figures", 1)
    return page.model_copy(update={"body": body}), cited


@pytest.mark.parametrize("kind", ["folder", "azure"])
async def test_blocking_gate_failure_acknowledges_its_messages(make_harness, kind):
    clock = Clock()
    harness = make_harness(engine=stub_engine(render_source_page=_leaky_render))
    queue = _queue(kind, harness, clock)
    queue.send(_ingest("cli:gate"))
    result = await harness.worker(queue=queue)
    assert result.status == "failed" and not result.retry
    assert result.deleted == 1 and result.kept == 0
    (outcome,) = result.outcomes
    assert outcome.status == "failed" and outcome.deterministic and not outcome.retry
    assert read_current_pointer(harness.storage) is None
    clock.now += harness.settings.visibility_timeout_s + 1
    assert queue.receive() == [], "acknowledged: never delivered again"
    report = json.loads(harness.storage.read_bytes(run_report_key(outcome.run_id)))
    assert report["status"] == "failed" and report["finished_at"]
    assert any("G08" in error for error in report["errors"])
    assert DETERMINISTIC_NOTE in report["errors"]
    assert {g["gate"] for g in report["gates"] if g["status"] == "fail" and g["blocking"]} == {
        "G08"
    }


@pytest.mark.parametrize("kind", ["folder", "azure"])
async def test_systemic_failure_keeps_its_messages_for_a_retry(make_harness, kind):
    from docwiki.llm import LlmRateLimited

    async def throttled(*args, **kwargs):
        raise LlmRateLimited("still throttled after retries")

    clock = Clock()
    harness = make_harness(engine=stub_engine(compile_source=throttled))
    queue = _queue(kind, harness, clock)
    queue.send(_ingest("cli:throttled"))
    result = await harness.worker(queue=queue)
    assert result.status == "failed" and result.retry
    assert result.deleted == 0 and result.kept == 1
    (outcome,) = result.outcomes
    assert outcome.retry and not outcome.deterministic
    assert DETERMINISTIC_NOTE not in outcome.report.errors
    clock.now += harness.settings.visibility_timeout_s + 1
    (again,) = queue.receive()
    assert again.dequeue_count == 2, "kept: delivered again"


async def test_invalid_domain_pack_is_deterministic(make_harness, pack_dir: Path, tmp_path: Path):
    pack = tmp_path / "broken-pack"
    shutil.copytree(pack_dir, pack)
    (pack / "taxonomy.yaml").unlink()
    harness = make_harness(pack=pack)
    queue = StorageQueue(harness.storage)
    queue.send(_ingest("cli:pack"))
    result = await harness.worker(queue=queue)
    (outcome,) = result.outcomes
    assert outcome.status == "failed" and outcome.deterministic
    assert any("PackValidationError" in error for error in outcome.errors)
    assert result.deleted == 1 and not result.retry and queue.pending_count() == 0


def _running_report(run_id: str) -> RunReport:
    return RunReport(
        run_id=run_id,
        kind="ingest",
        requested_by="event",
        status="running",
        started_at=datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
        audience="internal",
        versions=VersionInfo(docwiki="0.0.0", domain_pack="test", domain_pack_hash="x"),
        cost=CostReceipt(price_table="test"),
    )


async def test_reports_left_running_are_closed_as_abandoned(harness):
    stale = "run-20260101-080000-0a0b0c0d"
    harness.storage.write_bytes(
        run_report_key(stale), _running_report(stale).to_json().encode("utf-8")
    )
    result = await harness.worker(queue=StorageQueue(harness.storage), max_cycles=1)
    assert result.status == "completed", result.errors
    assert result.abandoned == [stale]
    closed = RunReport.from_json(harness.storage.read_bytes(run_report_key(stale)))
    assert closed.status == "failed" and closed.finished_at is not None
    assert closed.errors[-1] == ABANDONED_REASON
    (outcome,) = result.outcomes
    current = RunReport.from_json(harness.storage.read_bytes(run_report_key(outcome.run_id)))
    assert current.status == "succeeded", "the new run is never touched"
    again = await harness.worker(queue=StorageQueue(harness.storage), max_cycles=1)
    assert again.abandoned == []
