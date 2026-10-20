"""File to wiki: preview and filing of Researcher answers (ADR 0007), with the Studio's guards."""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import date
from typing import Any

import pytest
from starlette.testclient import TestClient
from studio_testkit import (
    NOT_FOUND_TEXT,
    OWNER,
    RELEASE_ID,
    WINDOWS_TEXT,
    FakeAgentClient,
)

from docwiki.answers import read_inbox
from docwiki.contracts.pages import Page, QueryFrontmatter
from docwiki.contracts.storage import FolderStorage, StorageError
from docwiki.studio.app import create_app
from docwiki.studio.config import StudioConfig
from docwiki.studio.jobs import AgentJobs
from docwiki.studio.service import StudioService

HOST = "studio.example.org"
SIGNED_IN = {"x-ms-client-principal-id": OWNER, "x-ms-client-principal-name": "owner@example.org"}
WRITE = {**SIGNED_IN, "x-docwiki-studio": "1"}
DAY = date(2026, 3, 2)
QUESTION = "When are the windows of the extension delivered?"
PAGE = f"queries/{DAY.isoformat()}-when-are-the-windows-of-the-extension-delivered.md"
INBOX = "work/inbox/"


def _client(
    storage: FolderStorage,
    config: StudioConfig,
    *,
    agents: FakeAgentClient | None = None,
    with_agents: bool = True,
    today: Callable[[], date] = lambda: DAY,
) -> TestClient:
    service = StudioService(storage, config, queue_depth=lambda: 0, today=today)
    jobs = None
    if with_agents:
        client = agents or FakeAgentClient()
        jobs = AgentJobs(
            lambda: client,
            daily_questions=config.daily_questions,
            approval_timeout_s=config.approval_timeout_s,
        )
    return TestClient(create_app(service, jobs, config), base_url=f"https://{HOST}")


@pytest.fixture
def client(storage: FolderStorage, config: StudioConfig) -> Iterator[TestClient]:
    with _client(storage, config, agents=FakeAgentClient(researcher_text=WINDOWS_TEXT)) as test:
        yield test


def _settle(client: TestClient, job_id: str, *statuses: str) -> dict[str, Any]:
    deadline = time.monotonic() + 5.0
    while True:
        view = client.get(f"/api/jobs/{job_id}", headers=SIGNED_IN).json()
        if view["status"] in statuses:
            return view
        if time.monotonic() > deadline:
            raise AssertionError(f"job stuck: {view}")
        time.sleep(0.02)


def _answered(client: TestClient, question: str = QUESTION, agent: str = "researcher") -> str:
    response = client.post("/api/ask", json={"agent": agent, "question": question}, headers=WRITE)
    assert response.status_code == 202, response.text
    job_id = str(response.json()["job_id"])
    if agent == "librarian":
        approval = _settle(client, job_id, "waiting_approval")["approvals"][0]
        url = f"/api/jobs/{job_id}/approvals/{approval['id']}"
        assert client.post(url, json={"approve": False}, headers=WRITE).status_code == 200
    _settle(client, job_id, "done")
    return job_id


def _inbox(storage: FolderStorage) -> list[str]:
    return storage.list(INBOX)


# --- preview ---------------------------------------------------------------------------------


def test_preview_shows_the_page_and_its_warnings_without_writing(
    client: TestClient, storage: FolderStorage
) -> None:
    job_id = _answered(client)
    response = client.get(f"/api/questions/{job_id}/filing", headers=SIGNED_IN)
    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "no-store"
    preview = response.json()
    assert preview["path"] == PAGE
    assert preview["inbox_key"] == "work/inbox/" + PAGE
    assert (preview["release_id"], preview["sensitivity"], preview["sources"]) == (
        RELEASE_ID,
        "public",
        2,
    )
    assert (preview["not_found"], preview["numbers_checked"]) == (False, 3)
    # The last sentence states a computed delay that the cited minutes do not contain.
    (warning,) = preview["warnings"]
    assert warning.startswith("numbers not found in the cited evidence: 69")
    markdown = preview["markdown"]
    page = Page.parse(markdown, PAGE)
    assert isinstance(page.frontmatter, QueryFrontmatter)
    assert (page.frontmatter.asked_by, page.frontmatter.approved_by) == ("human", "owner")
    assert page.frontmatter.question == QUESTION
    assert f"on {DAY.isoformat()} from release `{RELEASE_ID}`" in markdown
    assert "../evidence/src-86eabe3d6d0d/sheet-planning-r0006-r0009.md" in markdown
    assert preview["digest"] == hashlib.sha256(markdown.encode("utf-8")).hexdigest()
    assert (preview["filed"], preview["filings_left"]) == (None, 20)
    assert _inbox(storage) == []


def test_preview_of_an_abstention(storage: FolderStorage, config: StudioConfig) -> None:
    with _client(storage, config, agents=FakeAgentClient(researcher_text=NOT_FOUND_TEXT)) as client:
        job_id = _answered(client, "What is the torque of the yaw brake bolts?")
        preview = client.get(f"/api/questions/{job_id}/filing", headers=SIGNED_IN).json()
        assert (preview["not_found"], preview["sources"], preview["warnings"]) == (True, 0, [])
        assert "sources: []" in preview["markdown"]
        filed = client.post(f"/api/questions/{job_id}/file", json={}, headers=WRITE)
    assert filed.status_code == 201, filed.text
    assert _inbox(storage) == [filed.json()["inbox_key"]]


# --- filing ----------------------------------------------------------------------------------


def test_filing_writes_the_reviewed_page_to_the_inbox_once(
    client: TestClient, storage: FolderStorage
) -> None:
    job_id = _answered(client)
    preview = client.get(f"/api/questions/{job_id}/filing", headers=SIGNED_IN).json()
    url = f"/api/questions/{job_id}/file"
    response = client.post(url, json={"digest": preview["digest"]}, headers=WRITE)
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["inbox_key"] == "work/inbox/" + PAGE == preview["inbox_key"]
    assert (result["path"], result["release_id"]) == (PAGE, RELEASE_ID)
    assert (result["repeated"], result["filings_left"]) == (False, 19)
    assert storage.read_bytes(result["inbox_key"]).decode("utf-8") == preview["markdown"]
    # The next run reads it as a valid query page.
    (item,) = read_inbox(storage)
    assert item.error is None and item.page is not None and item.page.path == PAGE

    again = client.post(url, json={"digest": preview["digest"]}, headers=WRITE)
    assert again.status_code == 200, again.text
    assert again.json()["inbox_key"] == result["inbox_key"]
    assert (again.json()["repeated"], again.json()["filings_left"]) == (True, 19)
    assert _inbox(storage) == [result["inbox_key"]]

    filed = {key: result[key] for key in ("inbox_key", "path", "release_id", "filed_at")}
    assert client.get(f"/api/jobs/{job_id}", headers=SIGNED_IN).json()["filed"] == filed
    assert client.get(url.replace("/file", "/filing"), headers=SIGNED_IN).json()["filed"] == filed
    assert client.get("/api/me", headers=SIGNED_IN).json()["filings_left"] == 19


def test_only_the_previewed_page_is_filed(client: TestClient, storage: FolderStorage) -> None:
    job_id = _answered(client)
    url = f"/api/questions/{job_id}/file"
    stale = client.post(url, json={"digest": "0" * 64}, headers=WRITE)
    assert stale.status_code == 409
    assert "changed since your preview" in stale.json()["error"]
    assert client.post(url, json={"digest": 7}, headers=WRITE).status_code == 400
    assert _inbox(storage) == []


def test_librarian_answers_are_never_filed(client: TestClient, storage: FolderStorage) -> None:
    job_id = _answered(client, "Start an ingest run for uploads/", agent="librarian")
    for response in (
        client.get(f"/api/questions/{job_id}/filing", headers=SIGNED_IN),
        client.post(f"/api/questions/{job_id}/file", json={}, headers=WRITE),
    ):
        assert response.status_code == 400
        assert "only Researcher answers" in response.json()["error"]
    assert _inbox(storage) == []


@pytest.mark.parametrize(
    ("text", "message"),
    [
        (
            "Indice C is current [1].\n\nSources:\n[1] Planning, indice C — ¶ 1 "
            "(native-text) — evidence/src-000000000000/para-0001.md\n",
            "no evidence sidecar evidence/src-000000000000/para-0001.md",
        ),
        ("Indice B is the current planning.", "the answer cites nothing"),
    ],
)
def test_answers_that_cannot_become_a_page_get_the_reason(
    storage: FolderStorage, config: StudioConfig, text: str, message: str
) -> None:
    with _client(storage, config, agents=FakeAgentClient(researcher_text=text)) as client:
        job_id = _answered(client)
        for response in (
            client.get(f"/api/questions/{job_id}/filing", headers=SIGNED_IN),
            client.post(f"/api/questions/{job_id}/file", json={}, headers=WRITE),
        ):
            assert response.status_code == 422
            error = response.json()["error"]
            assert error.startswith("this answer cannot be filed: ") and message in error
    assert _inbox(storage) == []


def test_without_a_release_nothing_can_be_filed(client: TestClient, storage: FolderStorage) -> None:
    job_id = _answered(client)
    storage.delete("releases/current.json")
    response = client.get(f"/api/questions/{job_id}/filing", headers=SIGNED_IN)
    assert response.status_code == 422
    assert "no release has been published yet" in response.json()["error"]


def test_unanswered_and_unknown_questions(storage: FolderStorage, config: StudioConfig) -> None:
    with _client(storage, config, agents=FakeAgentClient(delay_s=5.0)) as client:
        job_id = client.post("/api/ask", json={"question": "slow"}, headers=WRITE).json()["job_id"]
        running = client.post(f"/api/questions/{job_id}/file", json={}, headers=WRITE)
        assert running.status_code == 409
        assert "no answer to file" in running.json()["error"]
        assert client.get(f"/api/questions/{job_id}/filing", headers=SIGNED_IN).status_code == 409
        client.delete(f"/api/jobs/{job_id}", headers=WRITE)
        unknown = client.get("/api/questions/does-not-exist/filing", headers=SIGNED_IN)
        assert unknown.status_code == 404
    assert _inbox(storage) == []


def test_without_agents_there_is_nothing_to_file(
    storage: FolderStorage, config: StudioConfig
) -> None:
    with _client(storage, config, with_agents=False) as client:
        assert client.get("/api/questions/x/filing", headers=SIGNED_IN).status_code == 404
        assert client.post("/api/questions/x/file", json={}, headers=WRITE).status_code == 404


def test_a_refused_write_is_reported_and_not_counted(
    client: TestClient, storage: FolderStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    """For example an identity without the inbox role (``azd provision`` not run yet)."""
    job_id = _answered(client)

    def refuse(key: str, data: bytes, **kwargs: Any) -> str:
        raise StorageError(f"writing {key!r} failed: (AuthorizationPermissionMismatch)")

    monkeypatch.setattr(storage, "write_bytes", refuse)
    response = client.post(f"/api/questions/{job_id}/file", json={}, headers=WRITE)
    assert response.status_code == 502
    assert response.json()["error"].startswith("the storage refused the filing")
    assert client.get("/api/me", headers=SIGNED_IN).json()["filings_left"] == 20
    assert client.get(f"/api/jobs/{job_id}", headers=SIGNED_IN).json()["filed"] is None


# --- protection ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({"x-docwiki-studio": "1"}, 401),
        ({"x-ms-client-principal-id": "someone-else", "x-docwiki-studio": "1"}, 403),
        (SIGNED_IN, 403),
        ({**WRITE, "sec-fetch-site": "cross-site"}, 403),
        ({**WRITE, "origin": "https://evil.example"}, 403),
    ],
)
def test_filing_needs_an_allowed_owner_the_csrf_header_and_the_same_origin(
    client: TestClient, storage: FolderStorage, headers: dict[str, str], status: int
) -> None:
    job_id = _answered(client)
    response = client.post(f"/api/questions/{job_id}/file", json={}, headers=headers)
    assert response.status_code == status
    assert "error" in response.json()
    assert _inbox(storage) == []


@pytest.mark.parametrize(
    ("headers", "status"),
    [({}, 401), ({"x-ms-client-principal-id": "someone-else"}, 403)],
)
def test_the_preview_needs_an_allowed_owner(
    client: TestClient, headers: dict[str, str], status: int
) -> None:
    job_id = _answered(client)
    assert client.get(f"/api/questions/{job_id}/filing", headers=headers).status_code == status


def test_same_origin_filing_is_accepted(client: TestClient, storage: FolderStorage) -> None:
    job_id = _answered(client)
    headers = {**WRITE, "origin": f"https://{HOST}", "sec-fetch-site": "same-origin"}
    response = client.post(f"/api/questions/{job_id}/file", json={}, headers=headers)
    assert response.status_code == 201, response.text
    assert _inbox(storage) == [response.json()["inbox_key"]]


def test_daily_filing_allowance(storage: FolderStorage, config: StudioConfig) -> None:
    day = [DAY]
    agents = FakeAgentClient(researcher_text=WINDOWS_TEXT)
    with _client(
        storage, replace(config, daily_filings=1), agents=agents, today=lambda: day[0]
    ) as client:
        first = _answered(client)
        filed = client.post(f"/api/questions/{first}/file", json={}, headers=WRITE)
        assert filed.status_code == 201, filed.text
        second = _answered(client, "Who installs the windows?")
        refused = client.post(f"/api/questions/{second}/file", json={}, headers=WRITE)
        assert refused.status_code == 429
        assert "allowance of 1 filings" in refused.json()["error"]
        assert client.get("/api/me", headers=SIGNED_IN).json()["filings_left"] == 0
        assert len(_inbox(storage)) == 1
        day[0] = date(2026, 3, 3)
        accepted = client.post(f"/api/questions/{second}/file", json={}, headers=WRITE)
    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["path"] == "queries/2026-03-03-who-installs-the-windows.md"
    assert len(_inbox(storage)) == 2
