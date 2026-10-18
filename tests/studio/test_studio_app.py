from __future__ import annotations

import re
import time
from collections.abc import Iterator
from dataclasses import replace
from typing import Any

import pytest
from starlette.testclient import TestClient
from studio_testkit import NEW_PATH, OWNER, WIKI_URL, FakeAgentClient

from docwiki.contracts.storage import FolderStorage
from docwiki.studio.app import STATIC_DIR, create_app
from docwiki.studio.config import StudioConfig
from docwiki.studio.jobs import AgentJobs
from docwiki.studio.service import StudioService

HOST = "studio.example.org"
SIGNED_IN = {"x-ms-client-principal-id": OWNER, "x-ms-client-principal-name": "owner@example.org"}
WRITE = {**SIGNED_IN, "x-docwiki-studio": "1"}


def _client(
    storage: FolderStorage,
    config: StudioConfig,
    *,
    agents: FakeAgentClient | None = None,
    with_agents: bool = True,
) -> TestClient:
    service = StudioService(storage, config, queue_depth=lambda: 0)
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
    with _client(storage, config) as test_client:
        yield test_client


def _settle(client: TestClient, job_id: str, *statuses: str) -> dict[str, Any]:
    deadline = time.monotonic() + 5.0
    while True:
        response = client.get(f"/api/jobs/{job_id}", headers=SIGNED_IN)
        assert response.status_code == 200, response.text
        view = response.json()
        if view["status"] in statuses:
            return view
        if time.monotonic() > deadline:
            raise AssertionError(f"job stuck: {view}")
        time.sleep(0.02)


# --- protection ----------------------------------------------------------------------------


def test_security_headers_everywhere(client: TestClient) -> None:
    for path, headers in (("/", {}), ("/livez", {}), ("/api/me", SIGNED_IN)):
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        csp = response.headers["content-security-policy"]
        assert "script-src 'self';" in csp and "unsafe-eval" not in csp
        assert "frame-ancestors 'none'" in csp
        assert response.headers["x-frame-options"] == "DENY"
    assert client.get("/").headers["cache-control"] == "no-store"


def test_liveness_is_public_and_shallow(client: TestClient) -> None:
    assert client.get("/livez").json() == {"status": "alive"}
    assert client.get("/healthz").json() == {"status": "alive"}


def test_deep_health_needs_sign_in(client: TestClient) -> None:
    assert client.get("/api/health").status_code == 401
    response = client.get("/api/health", headers=SIGNED_IN)
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "storage": True, "agents": True}


@pytest.mark.parametrize(
    ("headers", "status"),
    [
        ({}, 401),
        ({"x-ms-client-principal-id": "someone-else"}, 403),
        ({"x-ms-client-principal-id": OWNER.upper()}, 200),
    ],
)
def test_api_needs_an_allowed_principal(
    client: TestClient, headers: dict[str, str], status: int
) -> None:
    assert client.get("/api/documents", headers=headers).status_code == status


def test_an_empty_allowlist_lets_nobody_in(storage: FolderStorage, config: StudioConfig) -> None:
    with _client(storage, replace(config, allowed_principals=frozenset())) as client:
        response = client.get("/api/me", headers=SIGNED_IN)
    assert response.status_code == 403
    assert "DOCWIKI_STUDIO_ALLOWED_PRINCIPALS" in response.json()["error"]


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"x-docwiki-studio": "1", "sec-fetch-site": "cross-site"},
        {"x-docwiki-studio": "1", "origin": "https://evil.example"},
    ],
)
def test_writes_need_the_csrf_header_and_same_origin(
    client: TestClient, extra: dict[str, str]
) -> None:
    headers = {**SIGNED_IN, **extra}
    response = client.put("/api/documents/uploads/csrf.md", content=b"x", headers=headers)
    assert response.status_code == 403
    response = client.post("/api/ask", json={"question": "q"}, headers=headers)
    assert response.status_code == 403


def test_same_origin_writes_are_accepted(client: TestClient) -> None:
    headers = {**WRITE, "origin": f"https://{HOST}", "sec-fetch-site": "same-origin"}
    response = client.put("/api/documents/uploads/ok.md", content=b"# ok", headers=headers)
    assert response.status_code == 201, response.text


def test_local_mode_skips_sign_in_but_keeps_csrf(
    storage: FolderStorage, config: StudioConfig
) -> None:
    with _client(
        storage, replace(config, require_sign_in=False, allowed_principals=frozenset())
    ) as client:
        me = client.get("/api/me")
        assert me.status_code == 200 and me.json()["user"] == "local"
        assert me.json()["sign_out_url"] is None
        assert client.put("/api/documents/uploads/l.md", content=b"x").status_code == 403
        response = client.put(
            "/api/documents/uploads/l.md", content=b"x", headers={"x-docwiki-studio": "1"}
        )
        assert response.status_code == 201


# --- documents and pipeline ------------------------------------------------------------------


def test_me(client: TestClient, config: StudioConfig) -> None:
    data = client.get("/api/me", headers=SIGNED_IN).json()
    assert data["user"] == "owner@example.org"
    assert data["wiki_url"] == WIKI_URL
    assert data["agents"] == ["researcher", "librarian"]
    assert (data["questions_left"], data["uploads_left"]) == (100, config.daily_uploads)
    assert ".pdf" in data["extensions"] and data["max_upload_mb"] == 50
    assert data["sign_out_url"] == "/.auth/logout"


def test_upload_flow(client: TestClient, storage: FolderStorage) -> None:
    response = client.put(
        "/api/documents/uploads/Field%20report.md", content=b"# Field", headers=WRITE
    )
    assert response.status_code == 201, response.text
    assert response.json()["path"] == "uploads/Field report.md"
    assert response.json()["uploads_left"] == 9
    assert storage.read_bytes("raw/uploads/Field report.md") == b"# Field"
    rows = {
        row["path"]: row
        for row in client.get("/api/documents", headers=SIGNED_IN).json()["documents"]
    }
    assert rows["uploads/Field report.md"]["status"] == "new"
    conflict = client.put(f"/api/documents/{NEW_PATH}", content=b"again", headers=WRITE)
    assert conflict.status_code == 409
    replaced = client.put(f"/api/documents/{NEW_PATH}?replace=1", content=b"again", headers=WRITE)
    assert replaced.status_code == 201 and replaced.json()["replaced"] is True


@pytest.mark.parametrize(
    ("path", "body", "status"),
    [
        ("uploads/tool.exe", b"MZ", 400),
        ("uploads/empty.md", b"", 400),
        ("uploads/big.md", b"x" * 2048, 413),
    ],
)
def test_upload_errors(
    storage: FolderStorage, config: StudioConfig, path: str, body: bytes, status: int
) -> None:
    with _client(storage, replace(config, max_upload_bytes=1024)) as client:
        response = client.put(f"/api/documents/{path}", content=body, headers=WRITE)
    assert response.status_code == status, response.text
    assert "error" in response.json()


def test_upload_allowance(storage: FolderStorage, config: StudioConfig) -> None:
    with _client(storage, replace(config, daily_uploads=1)) as client:
        assert (
            client.put("/api/documents/uploads/a.md", content=b"a", headers=WRITE).status_code
            == 201
        )
        response = client.put("/api/documents/uploads/b.md", content=b"b", headers=WRITE)
    assert response.status_code == 429
    assert "allowance" in response.json()["error"]


def test_pipeline(client: TestClient) -> None:
    data = client.get("/api/pipeline", headers=SIGNED_IN).json()
    assert data["release"]["wiki_url"] == WIKI_URL
    assert data["queued"] == 0
    assert [run["status"] for run in data["runs"]] == ["failed", "succeeded"]


# --- agents ------------------------------------------------------------------------------------


def test_researcher_question(client: TestClient) -> None:
    response = client.post(
        "/api/ask", json={"agent": "researcher", "question": "Which revision?"}, headers=WRITE
    )
    assert response.status_code == 202, response.text
    assert response.json()["questions_left"] == 99
    view = _settle(client, response.json()["job_id"], "done")
    urls = [source["url"] for source in view["answer"]["sources"]]
    assert urls == [
        f"{WIKI_URL}/evidence/src-4d9c65e05302/para-0004",
        f"{WIKI_URL}/evidence/src-f2750f41f3fa/p0001",
    ]


def test_librarian_question_with_approval(client: TestClient) -> None:
    job_id = client.post(
        "/api/ask", json={"agent": "librarian", "question": "Start an ingest run"}, headers=WRITE
    ).json()["job_id"]
    approval = _settle(client, job_id, "waiting_approval")["approvals"][0]
    url = f"/api/jobs/{job_id}/approvals/{approval['id']}"
    assert client.post(url, json={"approve": True}).status_code == 401
    assert client.post(url, json={"approve": "yes"}, headers=WRITE).status_code == 400
    response = client.post(url, json={"approve": True}, headers=WRITE)
    assert response.json() == {"approval_id": approval["id"], "approved": True}
    view = _settle(client, job_id, "done")
    assert view["approvals"][0]["state"] == "approved"
    assert client.post(url, json={"approve": False}, headers=WRITE).status_code == 409


def test_cancel_and_busy(storage: FolderStorage, config: StudioConfig) -> None:
    with _client(storage, config, agents=FakeAgentClient(delay_s=5.0)) as client:
        job_id = client.post("/api/ask", json={"question": "slow"}, headers=WRITE).json()["job_id"]
        busy = client.post("/api/ask", json={"question": "another"}, headers=WRITE)
        assert busy.status_code == 409
        assert client.delete(f"/api/jobs/{job_id}", headers=WRITE).status_code == 202
        assert _settle(client, job_id, "cancelled")["answer"] is None


@pytest.mark.parametrize(
    ("body", "status"),
    [
        (b"not json", 400),
        (b"[1, 2]", 400),
        (b'{"agent": "writer", "question": "q"}', 400),
        (b'{"question": ""}', 400),
    ],
)
def test_bad_questions(client: TestClient, body: bytes, status: int) -> None:
    response = client.post(
        "/api/ask", content=body, headers={**WRITE, "content-type": "application/json"}
    )
    assert response.status_code == status
    assert "error" in response.json()


def test_unknown_question_is_404(client: TestClient) -> None:
    assert client.get("/api/jobs/does-not-exist", headers=SIGNED_IN).status_code == 404


def test_recent_questions_and_the_active_one(storage: FolderStorage, config: StudioConfig) -> None:
    with _client(storage, config, agents=FakeAgentClient(delay_s=5.0)) as client:
        assert client.get("/api/jobs", headers=SIGNED_IN).json() == {"active": None, "jobs": []}
        job_id = client.post("/api/ask", json={"question": "slow"}, headers=WRITE).json()["job_id"]
        listing = client.get("/api/jobs", headers=SIGNED_IN).json()
        assert listing["active"] == job_id
        assert [(job["job_id"], job["question"], job["status"]) for job in listing["jobs"]] == [
            (job_id, "slow", "running")
        ]
        client.delete(f"/api/jobs/{job_id}", headers=WRITE)
        _settle(client, job_id, "cancelled")
        assert client.get("/api/jobs", headers=SIGNED_IN).json()["active"] is None


def test_static_files_are_revalidated(client: TestClient) -> None:
    response = client.get("/static/studio.js")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache"
    assert "etag" in response.headers


def test_without_agents(storage: FolderStorage, config: StudioConfig) -> None:
    with _client(storage, config, with_agents=False) as client:
        assert client.get("/api/me", headers=SIGNED_IN).json()["agents"] == []
        assert client.post("/api/ask", json={"question": "q"}, headers=WRITE).status_code == 503
        assert client.get("/api/health", headers=SIGNED_IN).json()["agents"] is None


# --- static files ------------------------------------------------------------------------------


def test_index_is_served(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")


def test_static_files_respect_the_content_security_policy() -> None:
    """No inline script, inline style attribute or inline event handler (the CSP blocks them),
    no third-party resource and no HTML injection sink in the script."""
    index = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>", index), "inline <script>"
    assert not re.search(r"\sstyle\s*=", index), "inline style attribute"
    assert not re.search(r"\son[a-z]+\s*=", index), "inline event handler"
    assert not re.search(r"""(?:src|href)\s*=\s*["']?(?:https?:)?//""", index), "external resource"
    stylesheet = STATIC_DIR / "studio.css"
    if stylesheet.exists():
        css = stylesheet.read_text(encoding="utf-8")
        assert not re.search(r"""url\(\s*["']?(?:https?:)?//|@import""", css), "external CSS"
    script = STATIC_DIR / "studio.js"
    if script.exists():
        code = script.read_text(encoding="utf-8")
        for sink in ("innerHTML", "outerHTML", "insertAdjacentHTML", "document.write", "eval("):
            assert sink not in code, sink
        assert not re.search(r"""fetch\(\s*["'`](?:https?:)?//|importScripts|import\(""", code)
