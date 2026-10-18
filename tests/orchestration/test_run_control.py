"""Run control (architecture §4): lease, queue drain, acknowledgement, poison, loop."""

from __future__ import annotations

import asyncio
import base64
import json
import time
from datetime import UTC, datetime

import pytest
from engine_stubs import extract_source, stub_engine

from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.queue import QueueMessage
from docwiki.contracts.storage import LeaseLostError
from docwiki.orchestration.pipeline import RunRequest
from docwiki.orchestration.runner import LeaseKeeper, VisibilityKeeper, request_from_messages
from docwiki.orchestration.workflow import execute_run, run_with_asyncio
from docwiki.release.publish import read_current_pointer
from docwiki.storage.queue import QueueAuthorizationError, StorageQueue


class Clock:
    def __init__(self) -> None:
        self.now = time.time()

    def __call__(self) -> float:
        return self.now


def ingest(key: str, **extra: object) -> str:
    message = QueueMessage(
        kind="ingest",
        requested_by="librarian",
        idempotency_key=key,
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
        **extra,  # type: ignore[arg-type]
    )
    return message.to_body()


EVENT = json.dumps(
    {
        "id": "evt-1",
        "eventType": "Microsoft.Storage.BlobCreated",
        "subject": "/blobServices/default/containers/raw/blobs/notes/a.txt",
        "eventTime": "2026-02-01T08:00:00Z",
        "data": {},
    }
)


async def test_second_worker_exits_when_the_lease_is_held(harness):
    lease = harness.storage.acquire_lease(StorageKeys.LEASE, 60, owner="other")
    assert lease is not None
    result = await harness.worker(queue=StorageQueue(harness.storage))
    assert result.status == "lease-held"
    assert result.outcomes == []
    assert harness.storage.list(StorageKeys.RUNS_DIR + "/") == []
    harness.storage.release_lease(lease)
    after = await harness.worker(queue=StorageQueue(harness.storage))
    assert after.status == "completed"


async def test_messages_are_acknowledged_after_a_successful_run(harness):
    queue = StorageQueue(harness.storage)
    queue.send(ingest("cli:1"))
    queue.send(EVENT)
    queue.send(base64.b64encode(ingest("cli:2").encode()).decode())
    result = await harness.worker(queue=queue)
    assert result.status == "completed", result.errors
    assert result.deleted == 3 and result.kept == 0
    assert queue.pending_count() == 0
    outcome = result.outcomes[0]
    assert outcome.status == "succeeded", outcome.errors
    assert outcome.report.messages == 3
    assert outcome.report.requested_by == "librarian"


async def test_failed_run_keeps_messages_for_retry_then_poisons_them(make_harness):
    from docwiki.llm import LlmServiceError

    async def down(*args, **kwargs):
        raise LlmServiceError("service unavailable after retries")

    clock = Clock()
    harness = make_harness(engine=stub_engine(compile_source=down), max_dequeue=2)
    queue = StorageQueue(harness.storage, clock=clock)
    queue.send(ingest("cli:retry"))
    for _ in range(2):
        result = await harness.worker(queue=queue)
        assert result.status == "failed"
        assert result.deleted == 0 and result.kept == 1
        assert queue.pending_count() == 1
        assert queue.receive() == [], "the message stays invisible until its timeout"
        clock.now += harness.settings.visibility_timeout_s + 1
        assert read_current_pointer(harness.storage) is None
        assert result.outcomes[0].report.messages == 1
    result = await harness.worker(queue=queue)
    assert result.poisoned == 1
    assert queue.pending_count() == 0
    assert len(queue.poison_messages()) == 1


async def test_unparseable_messages_go_to_the_poison_queue(harness):
    queue = StorageQueue(harness.storage)
    queue.send("not json at all")
    queue.send(ingest("cli:ok"))
    result = await harness.worker(queue=queue)
    assert result.status == "completed"
    assert result.invalid == 1 and result.deleted == 1
    assert queue.poison_messages() == ["not json at all"]


async def test_worker_loops_once_more_when_messages_arrive_during_the_run(make_harness):
    holder: dict[str, StorageQueue] = {}
    sent: list[bool] = []

    async def extract_and_poke(raw_file, *, rel_path, settings, llm=None):
        if not sent:
            sent.append(True)
            holder["queue"].send(ingest("event:during-run"))
        return await extract_source(raw_file, rel_path=rel_path, settings=settings, llm=llm)

    harness = make_harness(engine=stub_engine(extract_source=extract_and_poke))
    queue = StorageQueue(harness.storage)
    holder["queue"] = queue
    queue.send(ingest("event:first"))
    result = await harness.worker(queue=queue)
    assert result.status == "completed", result.errors
    assert [outcome.status for outcome in result.outcomes] == ["succeeded", "no-op"]
    assert result.deleted == 2
    assert queue.pending_count() == 0


async def test_lost_lease_stops_the_run_before_publishing(harness):
    async with harness.context(lambda: False) as ctx:
        outcome = await execute_run(ctx, RunRequest())
    assert outcome.status == "failed"
    assert any("LeaseLostError" in error for error in outcome.errors)
    assert read_current_pointer(harness.storage) is None


def test_lease_keeper_reports_a_lost_lease():
    class LosingStorage:
        def __init__(self) -> None:
            self.renewed = 0

        def renew_lease(self, lease, duration_s=None):
            self.renewed += 1
            raise LeaseLostError("taken")

        def release_lease(self, lease):
            raise LeaseLostError("taken")

    from docwiki.contracts.storage import Lease

    storage = LosingStorage()
    keeper = LeaseKeeper(
        storage,  # type: ignore[arg-type]
        Lease(key="work/state/lease", lease_id="x", expires_at=0.0, duration_s=15),
        interval_s=0.05,
    ).start()
    deadline = time.time() + 5
    while not keeper.lost and time.time() < deadline:
        time.sleep(0.02)
    keeper.stop()
    keeper.release()
    assert keeper.lost and not keeper.ok()
    assert storage.renewed == 1


def _message(kind: str, **kwargs: object) -> QueueMessage:
    return QueueMessage(
        kind=kind,  # type: ignore[arg-type]
        requested_by="librarian",
        idempotency_key=f"k-{kind}",
        created_at=datetime(2026, 2, 1, tzinfo=UTC),
        **kwargs,  # type: ignore[arg-type]
    )


@pytest.mark.parametrize(
    ("kinds", "expected", "force"),
    [
        ([], "ingest", False),
        (["ingest"], "ingest", False),
        (["ingest", "rebuild"], "rebuild", True),
        (["ingest", "recompile"], "recompile", False),
    ],
)
def test_messages_merge_into_one_request(kinds, expected, force):
    messages = [
        _message(kind, scope={"source_ids": ["src-0123456789ab"]}, hints={"operator_notes": "x"})
        if kind == "recompile"
        else _message(kind)
        for kind in kinds
    ]
    request = request_from_messages(messages, kind="ingest", requested_by="event")
    assert request.kind == expected
    assert request.force is force
    assert request.messages == len(kinds)
    if "recompile" in kinds:
        assert request.recompile == {"src-0123456789ab": "x"}


def test_reconcile_keeps_its_kind_and_notes_are_merged():
    first = _message(
        "recompile", scope={"source_ids": ["src-0123456789ab"]}, hints={"operator_notes": "a"}
    )
    second = _message(
        "recompile", scope={"source_ids": ["src-0123456789ab"]}, hints={"operator_notes": "b"}
    )
    request = request_from_messages([first, second], kind="reconcile", requested_by="schedule")
    assert request.kind == "reconcile"
    assert request.recompile == {"src-0123456789ab": "a\n\nb"}


class DeniedRenewals(StorageQueue):
    """A queue whose identity may not update messages (HTTP 403 on Update Message)."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.renewals = 0

    def renew(self, message, visibility_timeout_s):
        self.renewals += 1
        raise QueueAuthorizationError(
            f"renewing message {message.id} was refused (HTTP 403)", status_code=403
        )


def test_visibility_keeper_stops_renewing_when_the_queue_refuses(
    tmp_path, caplog: pytest.LogCaptureFixture
):
    from docwiki.contracts.storage import FolderStorage

    queue = DeniedRenewals(FolderStorage(tmp_path / "q", fsync=False))
    queue.send(ingest("cli:1"))
    queue.send(ingest("cli:2"))
    received = queue.receive(visibility_timeout_s=30)
    keeper = VisibilityKeeper(queue, received, visibility_s=30, interval_s=10)
    keeper.renew_all()
    keeper.renew_all()
    assert queue.renewals == 1, "a refused renewal is not retried"
    (problem,) = keeper.problems()
    assert "not authorized" in problem and "Storage Queue Data Contributor" in problem
    errors = [r for r in caplog.records if r.levelname == "ERROR" and "not authorized" in r.message]
    assert len(errors) == 1, "logged once"
    assert {message.id for message in keeper.stop()} == {message.id for message in received}


async def test_refused_renewals_are_reported_as_run_warnings(make_harness):
    harness = make_harness(visibility_timeout_s=3)
    queue = DeniedRenewals(harness.storage)
    queue.send(ingest("cli:renew"))

    async def after_a_renewal(pipeline):
        for _ in range(200):
            if queue.renewals:
                break
            await asyncio.sleep(0.02)
        await asyncio.sleep(0.05)
        return await run_with_asyncio(pipeline)

    result = await harness.worker(queue=queue, orchestrator=after_a_renewal)
    assert result.status == "completed", result.errors
    assert queue.renewals == 1
    (outcome,) = result.outcomes
    assert outcome.status == "succeeded", outcome.errors
    assert any("not authorized" in warning for warning in outcome.report.warnings)
    report = json.loads(
        harness.storage.read_bytes(f"{StorageKeys.RUNS_DIR}/{outcome.run_id}/report.json")
    )
    assert any("Storage Queue Data Contributor" in warning for warning in report["warnings"])
    assert result.deleted == 1 and queue.pending_count() == 0
