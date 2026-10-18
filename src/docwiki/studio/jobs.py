"""Agent questions asked from the Studio: one background task per question, human approvals.

A question runs :meth:`AgentClient.ask` in an asyncio task. When the Librarian calls a tool that
needs approval (``ingest_start``, ``recompile``, ``decide_proposal``), the approval callback parks
the request in the job until the signed-in user approves or denies it in the browser (denied
after ``approval_timeout_s``). The browser polls the job. State lives in memory: the Studio runs
as a single replica and a restart forgets questions in flight, which is fine for a demo.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Literal, Protocol

from docwiki.agents_client.client import AgentAnswer, ApprovalRequest
from docwiki.agents_client.errors import AgentsClientError
from docwiki.studio.paths import wiki_link

__all__ = [
    "AGENTS",
    "AgentJob",
    "AgentJobs",
    "JobBusyError",
    "JobNotFoundError",
    "JobStateError",
    "QuestionError",
    "QuotaExceededError",
]

log = logging.getLogger("docwiki.studio.jobs")

AGENTS = ("researcher", "librarian")
MAX_QUESTION_CHARS = 2000
MAX_JOBS_KEPT = 50
MAX_ARGUMENT_CHARS = 600
HEALTH_TIMEOUT_S = 15.0

JobStatus = Literal["running", "waiting_approval", "done", "error", "cancelled"]
ApprovalState = Literal["pending", "approved", "denied", "expired"]


class QuestionError(ValueError):
    """An invalid question or agent (HTTP 400)."""


class QuotaExceededError(RuntimeError):
    """The daily question cap is reached (HTTP 429)."""


class JobBusyError(RuntimeError):
    """Another question is still running (HTTP 409)."""


class JobNotFoundError(LookupError):
    """Unknown job or approval (HTTP 404)."""


class JobStateError(RuntimeError):
    """The job or approval is not in a state that allows the action (HTTP 409)."""


class AgentAsker(Protocol):
    async def ask(self, question: str, *, agent: str = ..., approve: Any = ...) -> AgentAnswer: ...

    async def latest_version(self, agent: str) -> tuple[str, str | None]: ...

    async def aclose(self) -> None: ...


@dataclass
class Approval:
    request: ApprovalRequest
    future: asyncio.Future[bool]
    state: ApprovalState = "pending"


@dataclass
class AgentJob:
    id: str
    agent: str
    question: str
    principal: str | None
    started: float
    created_at: datetime
    status: JobStatus = "running"
    approvals: list[Approval] = field(default_factory=list)
    answer: AgentAnswer | None = None
    error: str | None = None
    finished: float | None = None
    task: asyncio.Task[None] | None = None

    @property
    def active(self) -> bool:
        return self.status in ("running", "waiting_approval")


def _arguments(value: dict[str, Any] | str) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=1)
    return text if len(text) <= MAX_ARGUMENT_CHARS else text[: MAX_ARGUMENT_CHARS - 1] + "…"


class AgentJobs:
    """Questions in flight and recently answered."""

    def __init__(
        self,
        client_factory: Callable[[], AgentAsker],
        *,
        daily_questions: int,
        approval_timeout_s: float,
        question_timeout_s: float = 1200.0,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self._client_factory = client_factory
        self._client: AgentAsker | None = None
        self.daily_questions = daily_questions
        self.approval_timeout_s = approval_timeout_s
        self.question_timeout_s = question_timeout_s
        self._clock = clock
        self._today = today
        self._jobs: dict[str, AgentJob] = {}
        self._asked: dict[date, int] = {}

    def _get_client(self) -> AgentAsker:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    # -- questions ---------------------------------------------------------------------------

    def questions_left(self) -> int:
        return max(self.daily_questions - self._asked.get(self._today(), 0), 0)

    def start(self, agent: str, question: str, principal: str | None) -> AgentJob:
        """Start a question (must run inside the event loop)."""
        name = (agent or "").strip().lower()
        if name not in AGENTS:
            raise QuestionError(f"agent must be one of {', '.join(AGENTS)}")
        text = (question or "").strip()
        if not text:
            raise QuestionError("the question is empty")
        if len(text) > MAX_QUESTION_CHARS:
            raise QuestionError(f"the question is longer than {MAX_QUESTION_CHARS} characters")
        if any(job.active for job in self._jobs.values()):
            raise JobBusyError("another question is still running; wait for it or cancel it")
        today = self._today()
        if self._asked.get(today, 0) >= self.daily_questions:
            raise QuotaExceededError(
                f"the daily limit of {self.daily_questions} questions is reached"
            )
        self._asked = {today: self._asked.get(today, 0) + 1}
        job = AgentJob(
            id=uuid.uuid4().hex[:16],
            agent=name,
            question=text,
            principal=principal,
            started=self._clock(),
            created_at=datetime.now(UTC).replace(microsecond=0),
        )
        self._jobs[job.id] = job
        self._prune()
        job.task = asyncio.get_running_loop().create_task(self._run(job))
        return job

    def _prune(self) -> None:
        finished = [job for job in self._jobs.values() if not job.active]
        excess = len(self._jobs) - MAX_JOBS_KEPT
        for job in sorted(finished, key=lambda item: item.started)[: max(excess, 0)]:
            self._jobs.pop(job.id, None)

    async def _run(self, job: AgentJob) -> None:
        try:
            async with asyncio.timeout(self.question_timeout_s):
                answer = await self._get_client().ask(
                    job.question,
                    agent=job.agent,
                    approve=lambda request: self._approve(job, request),
                )
        except asyncio.CancelledError:
            job.status = "cancelled"
        except TimeoutError:
            job.status = "error"
            job.error = (
                f"The question was stopped after {self.question_timeout_s / 60:.0f} minutes."
            )
            log.warning("question %s timed out", job.id)
        except AgentsClientError as exc:
            job.status = "error"
            job.error = str(exc)
            log.warning("question %s failed: %s", job.id, exc)
        except Exception:
            job.status = "error"
            job.error = "The agent call failed unexpectedly; the Studio logs have the details."
            log.exception("question %s failed", job.id)
        else:
            job.answer = answer
            job.status = "done"
        finally:
            job.finished = self._clock()
            for approval in job.approvals:
                if approval.state == "pending":
                    approval.state = "expired"
                    if not approval.future.done():
                        approval.future.set_result(False)

    async def _approve(self, job: AgentJob, request: ApprovalRequest) -> bool:
        future: asyncio.Future[bool] = asyncio.get_running_loop().create_future()
        approval = Approval(request=request, future=future)
        job.approvals.append(approval)
        job.status = "waiting_approval"
        try:
            approved = await asyncio.wait_for(asyncio.shield(future), self.approval_timeout_s)
        except TimeoutError:
            approval.state = "expired"
            approved = False
        finally:
            if job.status == "waiting_approval":
                job.status = "running"
        if approval.state == "pending":
            approval.state = "approved" if approved else "denied"
        return approved

    def decide(self, job_id: str, approval_id: str, approve: bool) -> None:
        job = self.get(job_id)
        for approval in job.approvals:
            if approval.request.id == approval_id:
                if approval.state != "pending" or approval.future.done():
                    raise JobStateError(f"approval {approval_id} is already {approval.state}")
                approval.state = "approved" if approve else "denied"
                approval.future.set_result(approve)
                return
        raise JobNotFoundError(f"unknown approval {approval_id}")

    def cancel(self, job_id: str) -> None:
        job = self.get(job_id)
        if not job.active:
            raise JobStateError(f"question {job_id} is already {job.status}")
        if job.task is not None:
            job.task.cancel()

    def get(self, job_id: str) -> AgentJob:
        job = self._jobs.get(job_id)
        if job is None:
            raise JobNotFoundError(f"unknown question {job_id}")
        return job

    def recent(self, limit: int = 20) -> dict[str, Any]:
        """Questions of this replica, newest first, and the one still running (if any)."""
        jobs = sorted(self._jobs.values(), key=lambda item: item.started, reverse=True)
        active = next((job.id for job in jobs if job.active), None)
        return {
            "active": active,
            "jobs": [
                {
                    "job_id": job.id,
                    "agent": job.agent,
                    "question": job.question,
                    "status": job.status,
                    "created_at": job.created_at.isoformat().replace("+00:00", "Z"),
                }
                for job in jobs[:limit]
            ],
        }

    # -- views -------------------------------------------------------------------------------

    def view(self, job: AgentJob, wiki_url: str | None) -> dict[str, Any]:
        end = job.finished if job.finished is not None else self._clock()
        payload: dict[str, Any] = {
            "job_id": job.id,
            "agent": job.agent,
            "question": job.question,
            "status": job.status,
            "created_at": job.created_at.isoformat().replace("+00:00", "Z"),
            "elapsed_s": round(max(end - job.started, 0.0), 1),
            "approvals": [
                {
                    "id": approval.request.id,
                    "name": approval.request.name,
                    "server_label": approval.request.server_label,
                    "arguments": _arguments(approval.request.arguments),
                    "state": approval.state,
                }
                for approval in job.approvals
            ],
            "answer": None,
            "error": job.error,
        }
        answer = job.answer
        if answer is not None:
            payload["answer"] = {
                "agent": answer.agent,
                "version": answer.version,
                "body": answer.body.strip(),
                "sources": [
                    {
                        "n": source.n,
                        "title": source.title,
                        "locator_label": source.locator_label,
                        "provenance": source.provenance,
                        "path": source.path,
                        "url": wiki_link(wiki_url, source.path),
                    }
                    for source in answer.sources
                ],
                "tool_calls": [
                    {
                        "name": call.name,
                        "server_label": call.server_label,
                        "arguments": _arguments(call.arguments),
                        "status": call.status,
                        "error": call.error,
                    }
                    for call in answer.tool_calls
                ],
                "usage": answer.usage.model_dump(),
                "latency_s": answer.latency_s,
            }
        return payload

    # -- lifecycle ---------------------------------------------------------------------------

    async def healthy(self) -> bool:
        try:
            await asyncio.wait_for(
                self._get_client().latest_version("researcher"), HEALTH_TIMEOUT_S
            )
        except Exception as exc:
            log.warning("agent check failed: %s", exc)
            return False
        return True

    async def aclose(self) -> None:
        for job in list(self._jobs.values()):
            if job.task is not None and not job.task.done():
                job.task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await job.task
        if self._client is not None:
            client, self._client = self._client, None
            await client.aclose()
