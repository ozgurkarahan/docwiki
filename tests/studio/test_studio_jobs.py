from __future__ import annotations

import asyncio
from typing import Any

import pytest
from studio_testkit import WIKI_URL, FakeAgentClient

from docwiki.agents_client.errors import AgentInvocationError
from docwiki.studio.jobs import (
    MAX_JOBS_KEPT,
    AgentJobs,
    JobBusyError,
    JobNotFoundError,
    JobStateError,
    QuestionError,
    QuotaExceededError,
)


def _jobs(client: FakeAgentClient, **options: Any) -> AgentJobs:
    settings: dict[str, Any] = {"daily_questions": 100, "approval_timeout_s": 5.0, **options}
    return AgentJobs(lambda: client, **settings)


async def _settle(jobs: AgentJobs, job_id: str, *statuses: str) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 5.0
    while True:
        view = jobs.view(jobs.get(job_id), WIKI_URL)
        if view["status"] in statuses:
            return view
        if loop.time() > deadline:
            raise AssertionError(f"job stuck: {view}")
        await asyncio.sleep(0.01)


async def test_researcher_answer_with_linked_sources() -> None:
    client = FakeAgentClient()
    jobs = _jobs(client)
    job = jobs.start("Researcher", "  When are the windows delivered?  ", "owner")
    view = await _settle(jobs, job.id, "done")
    assert view["agent"] == "researcher"
    assert view["question"] == "When are the windows delivered?"
    answer = view["answer"]
    assert answer["body"].startswith("The windows") and "Sources:" not in answer["body"]
    assert [(source["n"], source["url"]) for source in answer["sources"]] == [
        (1, f"{WIKI_URL}/evidence/src-165f1d3a109c/para-0011"),
        (2, f"{WIKI_URL}/evidence/src-c6436ec50050/p0001"),
    ]
    assert [call["name"] for call in answer["tool_calls"]] == ["search", "get_evidence"]
    assert answer["usage"]["total_tokens"] == 5610
    assert (answer["agent"], answer["version"]) == ("docwiki-researcher", "3")
    assert client.calls == [("researcher", "When are the windows delivered?")]
    finished = jobs.get(job.id).finished_at
    assert finished is not None and finished >= job.created_at, "the answer's date"


async def test_librarian_waits_for_approval_then_runs_the_tool() -> None:
    jobs = _jobs(FakeAgentClient())
    job = jobs.start("librarian", "Start an ingest run for uploads/", "owner")
    view = await _settle(jobs, job.id, "waiting_approval")
    (approval,) = view["approvals"]
    assert (approval["name"], approval["state"]) == ("ingest_start", "pending")
    assert '"prefix": "uploads/"' in approval["arguments"]
    jobs.decide(job.id, approval["id"], True)
    view = await _settle(jobs, job.id, "done")
    assert view["approvals"][0]["state"] == "approved"
    assert "queued an ingest run" in view["answer"]["body"]
    assert view["answer"]["tool_calls"][-1] == {
        "name": "ingest_start",
        "server_label": "docwiki",
        "arguments": '{\n "prefix": "uploads/",\n "reason": "a new document was uploaded"\n}',
        "status": "completed",
        "error": None,
    }
    with pytest.raises(JobStateError):
        jobs.decide(job.id, approval["id"], False)


async def test_denied_approval() -> None:
    jobs = _jobs(FakeAgentClient())
    job = jobs.start("librarian", "Start an ingest run", None)
    approval = (await _settle(jobs, job.id, "waiting_approval"))["approvals"][0]
    jobs.decide(job.id, approval["id"], False)
    view = await _settle(jobs, job.id, "done")
    assert view["approvals"][0]["state"] == "denied"
    assert view["answer"]["tool_calls"][-1]["status"] == "denied"
    assert "did not start" in view["answer"]["body"]


async def test_unanswered_approval_expires_as_denied() -> None:
    jobs = _jobs(FakeAgentClient(), approval_timeout_s=0.05)
    job = jobs.start("librarian", "Start an ingest run", None)
    view = await _settle(jobs, job.id, "done")
    assert view["approvals"][0]["state"] == "expired"
    assert view["answer"]["tool_calls"][-1]["status"] == "denied"


async def test_one_question_at_a_time_and_a_daily_cap() -> None:
    jobs = _jobs(FakeAgentClient(delay_s=0.2), daily_questions=2)
    first = jobs.start("researcher", "one", None)
    with pytest.raises(JobBusyError):
        jobs.start("researcher", "two", None)
    await _settle(jobs, first.id, "done")
    second = jobs.start("researcher", "two", None)
    await _settle(jobs, second.id, "done")
    assert jobs.questions_left() == 0
    with pytest.raises(QuotaExceededError):
        jobs.start("researcher", "three", None)


@pytest.mark.parametrize(
    ("agent", "question"),
    [("writer", "Which window?"), ("researcher", "   "), ("researcher", "x" * 2001)],
)
async def test_invalid_questions(agent: str, question: str) -> None:
    with pytest.raises(QuestionError):
        _jobs(FakeAgentClient()).start(agent, question, None)


async def test_cancel_a_running_question() -> None:
    jobs = _jobs(FakeAgentClient(delay_s=5.0))
    job = jobs.start("researcher", "slow question", None)
    await asyncio.sleep(0.01)
    jobs.cancel(job.id)
    view = await _settle(jobs, job.id, "cancelled")
    assert view["answer"] is None
    with pytest.raises(JobStateError):
        jobs.cancel(job.id)


async def test_agent_errors_are_reported_without_internal_details() -> None:
    known = _jobs(FakeAgentClient(fail=AgentInvocationError("agent failed: rate limited")))
    view = await _settle(known, known.start("researcher", "q", None).id, "error")
    assert "rate limited" in view["error"]
    unknown = _jobs(FakeAgentClient(fail=RuntimeError("secret internal detail")))
    view = await _settle(unknown, unknown.start("researcher", "q", None).id, "error")
    assert "secret internal detail" not in view["error"]
    assert "unexpectedly" in view["error"]


async def test_overall_question_deadline() -> None:
    jobs = _jobs(FakeAgentClient(delay_s=5.0), question_timeout_s=0.05)
    view = await _settle(jobs, jobs.start("researcher", "slow", None).id, "error")
    assert "stopped" in view["error"]


async def test_unknown_questions_and_approvals() -> None:
    jobs = _jobs(FakeAgentClient())
    with pytest.raises(JobNotFoundError):
        jobs.get("nope")
    job = jobs.start("researcher", "q", None)
    await _settle(jobs, job.id, "done")
    with pytest.raises(JobNotFoundError):
        jobs.decide(job.id, "mcpr_unknown", True)


async def test_health_check_and_close() -> None:
    client = FakeAgentClient()
    jobs = _jobs(client)
    assert await jobs.healthy() is True
    await jobs.aclose()
    assert client.closed is True
    assert await _jobs(FakeAgentClient(fail=RuntimeError("down"))).healthy() is False


async def test_finished_questions_are_pruned() -> None:
    jobs = _jobs(FakeAgentClient())
    last = None
    for index in range(MAX_JOBS_KEPT + 5):
        last = jobs.start("researcher", f"question {index}", None)
        await _settle(jobs, last.id, "done")
    assert last is not None
    assert len(jobs._jobs) <= MAX_JOBS_KEPT
    assert jobs.get(last.id).status == "done"
