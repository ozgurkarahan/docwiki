"""Run control (architecture §4): lease, debounce, drain, run, acknowledge, loop, release.

1. Acquire the blob lease ``work/state/lease`` (renewed in a background thread every third of
   its duration). When another execution holds it, exit successfully: that execution picks up
   the changes (level-triggered). Holding it, close earlier run reports still ``running`` as
   failed (``abandoned``): no other execution can be running them.
2. Debounce, then receive every visible message (batches of 32) and keep their pop receipts;
   their visibility is renewed in a background thread while the run lasts (a refused renewal —
   HTTP 401/403 — stops the renewals and is reported as a warning of the run). Messages dequeued
   more than ``max_dequeue`` times, or that cannot be parsed, go to the poison queue.
3. Run the pipeline (diff of ``raw/`` + explicit recompile scopes).
4. On success, and after a deterministic failure (blocking gates, final validation, invalid
   domain pack: a retry would fail the same way), delete exactly the messages whose pop
   receipts are still owned; on any other failure keep them (they become visible again and are
   retried).
5. Loop once more when new messages arrived during a successful run, otherwise release the
   lease.
"""

from __future__ import annotations

import asyncio
import logging
import threading
import uuid
from collections.abc import Awaitable, Callable, Sequence
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime
from typing import Literal

from docwiki.contracts.enums import QueueKind, RequestedBy
from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.queue import QueueMessage, parse_queue_message
from docwiki.contracts.storage import Lease, LeaseLostError, Storage, StorageError
from docwiki.orchestration.pipeline import RunContext, RunOutcome, RunRequest
from docwiki.orchestration.report import close_abandoned_runs
from docwiki.orchestration.settings import EngineSettings
from docwiki.orchestration.workflow import Orchestrator, execute_run
from docwiki.storage.queue import (
    MessageLostError,
    QueueAuthorizationError,
    ReceivedMessage,
    WorkQueue,
)

__all__ = [
    "ContextFactory",
    "Drained",
    "LeaseKeeper",
    "VisibilityKeeper",
    "WorkerResult",
    "drain_queue",
    "request_from_messages",
    "run_worker",
]

logger = logging.getLogger("docwiki.engine")
ContextFactory = Callable[[Callable[[], bool]], AbstractAsyncContextManager[RunContext]]
MAX_MESSAGES_PER_CYCLE = 2000
_KIND_RANK = {"ingest": 0, "reconcile": 1, "recompile": 2, "rebuild": 3}


class LeaseKeeper:
    """Renews a lease in a background thread; :attr:`lost` turns true when it is gone."""

    def __init__(self, storage: Storage, lease: Lease, *, interval_s: float) -> None:
        self.storage = storage
        self.lease = lease
        self.interval_s = max(0.05, interval_s)
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="docwiki-lease", daemon=True)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            try:
                self.lease = self.storage.renew_lease(self.lease)
            except LeaseLostError:
                logger.error("run lease on %s was lost", self.lease.key)
                self._lost.set()
                return
            except StorageError as exc:
                logger.warning("renewing the run lease failed (will retry): %s", exc)

    @property
    def lost(self) -> bool:
        return self._lost.is_set()

    def ok(self) -> bool:
        return not self._lost.is_set()

    def start(self) -> LeaseKeeper:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=5)

    def release(self) -> None:
        try:
            self.storage.release_lease(self.lease)
        except LeaseLostError:
            logger.warning("the run lease was taken by another execution before release")
        except StorageError as exc:
            logger.warning("releasing the run lease failed: %s", exc)


class VisibilityKeeper:
    """Keeps received messages invisible while the run lasts (renewing their pop receipts).

    A refused renewal (HTTP 401/403) is a configuration error: it is logged once, renewing
    stops and :attr:`problems` describes it for the run report. The messages stay owned; they
    may become visible again before the run ends.
    """

    def __init__(
        self,
        queue: WorkQueue | None,
        messages: Sequence[ReceivedMessage],
        *,
        visibility_s: int,
        interval_s: float,
    ) -> None:
        self.queue = queue
        self.visibility_s = visibility_s
        self.interval_s = max(0.05, interval_s)
        self._owned = {message.id: message for message in messages}
        self._lost: list[str] = []
        self._problems: list[str] = []
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._loop, name="docwiki-visibility", daemon=True)

    def _loop(self) -> None:
        while not self._stop.wait(self.interval_s):
            self.renew_all()

    def renew_all(self) -> None:
        if self.queue is None:
            return
        with self._lock:
            if self._problems:
                return
            current = list(self._owned.values())
        for message in current:
            try:
                renewed = self.queue.renew(message, self.visibility_s)
            except MessageLostError:
                with self._lock:
                    self._owned.pop(message.id, None)
                    self._lost.append(message.id)
                continue
            except QueueAuthorizationError as exc:
                problem = (
                    "queue: renewing the visibility of the run's messages is not authorized "
                    f"({exc}); renewals stopped, so the messages may be delivered again while "
                    "this run lasts. Grant the jobs identity 'Storage Queue Data Contributor' on "
                    "the ingest queue (azd provision)."
                )
                logger.error("%s", problem)
                with self._lock:
                    self._problems.append(problem)
                self._stop.set()
                return
            except StorageError as exc:
                logger.warning("renewing message %s failed (will retry): %s", message.id, exc)
                continue
            with self._lock:
                if message.id in self._owned:
                    self._owned[message.id] = renewed

    def start(self) -> VisibilityKeeper:
        if self.queue is not None and self._owned:
            self._thread.start()
        return self

    def stop(self) -> list[ReceivedMessage]:
        """Stop renewing; returns the messages whose receipts we still own."""
        self._stop.set()
        if self._thread.is_alive():
            self._thread.join(timeout=10)
        with self._lock:
            return list(self._owned.values())

    @property
    def lost(self) -> list[str]:
        with self._lock:
            return list(self._lost)

    def problems(self) -> list[str]:
        """Configuration problems met while renewing (for the run report)."""
        with self._lock:
            return list(self._problems)


@dataclass
class Drained:
    messages: list[tuple[ReceivedMessage, QueueMessage]] = field(default_factory=list)
    poisoned: int = 0
    invalid: int = 0


def drain_queue(
    queue: WorkQueue | None,
    *,
    max_dequeue: int = 5,
    visibility_s: int = 300,
    limit: int = MAX_MESSAGES_PER_CYCLE,
) -> Drained:
    """Receive every visible message; poison over-delivered and unparseable ones."""
    drained = Drained()
    if queue is None:
        return drained
    while len(drained.messages) < limit:
        batch = queue.receive(max_messages=32, visibility_timeout_s=visibility_s)
        if not batch:
            break
        for message in batch:
            if message.dequeue_count > max_dequeue:
                logger.warning(
                    "message %s was dequeued %d times; moving it to the poison queue",
                    message.id,
                    message.dequeue_count,
                )
                queue.dead_letter(message)
                drained.poisoned += 1
                continue
            try:
                parsed = parse_queue_message(message.content)
            except ValueError as exc:
                logger.warning(
                    "message %s is not a DocWiki message (%s); poisoning", message.id, exc
                )
                queue.dead_letter(message)
                drained.invalid += 1
                continue
            drained.messages.append((message, parsed))
    return drained


def request_from_messages(
    messages: Sequence[QueueMessage],
    *,
    kind: QueueKind = "ingest",
    requested_by: RequestedBy = "event",
    base: RunRequest | None = None,
) -> RunRequest:
    """Merge the messages of a cycle into one run request.

    ``rebuild`` forces a release; ``recompile`` scopes force their sources with the reviewed
    operator notes (``hints["operator_notes"]``); a ``reconcile`` worker keeps its kind.
    """
    request = (
        replace(base) if base is not None else RunRequest(kind=kind, requested_by=requested_by)
    )
    recompile = dict(request.recompile)
    effective = request.kind
    for message in messages:
        if request.kind != "reconcile" and _KIND_RANK[message.kind] > _KIND_RANK[effective]:
            effective = message.kind
        if message.kind != "recompile":
            continue
        notes = message.hints.get("operator_notes") or None
        for source_id in message.scope.source_ids:
            previous = recompile.get(source_id)
            if previous and notes and notes not in previous:
                recompile[source_id] = f"{previous}\n\n{notes}"
            else:
                recompile[source_id] = previous or notes
    return replace(
        request,
        kind=effective,
        requested_by=messages[0].requested_by if messages else request.requested_by,
        messages=len(messages),
        recompile=recompile,
        force=request.force or any(message.kind == "rebuild" for message in messages),
    )


@dataclass
class WorkerResult:
    status: Literal["lease-held", "completed", "failed"]
    outcomes: list[RunOutcome] = field(default_factory=list)
    deleted: int = 0
    kept: int = 0
    poisoned: int = 0
    invalid: int = 0
    errors: list[str] = field(default_factory=list)
    retry: bool = False
    """A failed run kept its messages for a retry (systemic failure, lost lease, run not
    started); ``False`` after a deterministic failure whose messages were acknowledged."""
    abandoned: list[str] = field(default_factory=list)
    """Earlier runs still marked ``running`` that this execution closed as abandoned."""


async def run_worker(
    context: ContextFactory,
    *,
    storage: Storage,
    settings: EngineSettings,
    queue: WorkQueue | None = None,
    kind: QueueKind = "ingest",
    requested_by: RequestedBy = "event",
    base_request: RunRequest | None = None,
    max_cycles: int | None = None,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    orchestrator: Orchestrator | None = None,
    owner: str | None = None,
) -> WorkerResult:
    """The ingest job (``docwiki worker``/``reconcile``/``run``): see the module docstring."""
    lease = storage.acquire_lease(
        StorageKeys.LEASE, settings.lease_s, owner=owner or f"worker-{uuid.uuid4().hex[:8]}"
    )
    if lease is None:
        logger.info("another execution holds the run lease; exiting")
        return WorkerResult("lease-held")
    keeper = LeaseKeeper(storage, lease, interval_s=max(1.0, lease.duration_s / 3)).start()
    result = WorkerResult("completed")
    cycles = max_cycles if max_cycles is not None else settings.max_cycles
    try:
        try:
            result.abandoned = close_abandoned_runs(storage, now=datetime.now(UTC))
        except Exception as exc:  # housekeeping must never block a run
            logger.warning("closing abandoned run reports failed: %s", exc)
        for cycle in range(max(1, cycles)):
            if settings.debounce_s > 0:
                await sleep(settings.debounce_s)
            drained = drain_queue(
                queue,
                max_dequeue=settings.max_dequeue,
                visibility_s=settings.visibility_timeout_s,
            )
            result.poisoned += drained.poisoned
            result.invalid += drained.invalid
            if cycle > 0 and not drained.messages:
                break
            received = [message for message, _ in drained.messages]
            visibility = VisibilityKeeper(
                queue,
                received,
                visibility_s=settings.visibility_timeout_s,
                interval_s=max(1.0, settings.visibility_timeout_s / 3),
            ).start()
            request = request_from_messages(
                [parsed for _, parsed in drained.messages],
                kind=kind,
                requested_by=requested_by,
                base=base_request,
            )
            outcome: RunOutcome | None = None
            try:
                async with context(keeper.ok) as ctx:
                    ctx = replace(ctx, notices=visibility.problems)
                    outcome = await execute_run(ctx, request, orchestrator=orchestrator)
            except Exception as exc:
                result.errors.append(f"{type(exc).__name__}: {exc}")
                logger.error("run could not start: %s", exc)
            finally:
                owned = visibility.stop()
            if outcome is not None:
                result.outcomes.append(outcome)
            if outcome is None or keeper.lost or outcome.retry:
                result.kept += len(owned)
                result.status = "failed"
                result.retry = True
                break
            for message in owned:
                if queue is not None and queue.delete(message):
                    result.deleted += 1
                else:
                    result.kept += 1
            if outcome.status == "failed":
                # deterministic: a retry of the same inputs fails the same way
                result.status = "failed"
                break
            if queue is None or queue.visible_count() == 0:
                break
    finally:
        keeper.stop()
        keeper.release()
    return result
