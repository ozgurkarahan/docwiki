"""Following each document through a run, what a release changed, and the owner's rebuild
(slice C of the v2 plan)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

import pytest
from process_testkit import DONE_PATH, NEW_PATH, OWNER, PENDING_PATH, RELEASE_ID, seed_storage
from starlette.applications import Starlette
from starlette.testclient import TestClient

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.queue import QueueMessage
from docwiki.contracts.storage import FolderStorage
from docwiki.mcp.workstore import WorkStore
from docwiki.portal.owner import OwnerConfig, process_routes
from docwiki.portal.process import ProcessService, document_phase

HOST = "wiki.example.org"
SIGNED_IN = {"x-ms-client-principal-id": OWNER, "x-ms-client-principal-name": "owner"}
WRITE = {**SIGNED_IN, "x-docwiki-owner": "1"}
DONE_PAGE = "/sources/2026-03-24-compte-rendu-de-chantier-n3"


@pytest.fixture
def storage(tmp_path: Path) -> FolderStorage:
    return seed_storage(tmp_path / "store", sensitivity="public")


def _service(storage: FolderStorage, **kwargs: Any) -> ProcessService:
    return ProcessService(storage, max_upload_bytes=1024, daily_uploads=5, **kwargs)


def _template(storage: FolderStorage) -> dict[str, Any]:
    newest = WorkStore(storage).run_ids()[-1]
    return json.loads(storage.read_bytes(f"work/runs/{newest}/report.json"))


def _write_report(storage: FolderStorage, run_id: str, **fields: Any) -> None:
    report = {**_template(storage), "run_id": run_id, **fields}
    storage.write_bytes(f"work/runs/{run_id}/report.json", json.dumps(report).encode("utf-8"))


def _rows(view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["path"]: row for row in view["documents"]}


@pytest.mark.parametrize(
    ("stage", "phase"),
    [
        ("discover", "read"),
        ("extract", "read"),
        ("classify", "file"),
        ("compile", "write"),
        ("agentkit", "write"),
        ("evidence", "check"),
        ("publish", "check"),
        (None, None),
    ],
)
def test_phases(stage: str | None, phase: str | None) -> None:
    assert document_phase(stage) == phase


def test_a_run_at_work_moves_its_documents_through_the_phases(storage: FolderStorage) -> None:
    documents = [
        {"source_id": source_id_for(PENDING_PATH), "path": PENDING_PATH, "change": "new"},
        {"source_id": source_id_for(NEW_PATH), "path": NEW_PATH, "change": "new"},
    ]
    run_id = "run-29991231-235959-00000001"
    _write_report(
        storage,
        run_id,
        status="running",
        finished_at=None,
        release_id=None,
        current_stage="discover",
        documents=documents,
        stages=[],
    )
    view = _service(storage).process(owner=True)
    rows = _rows(view)
    assert (rows[NEW_PATH]["state"], rows[NEW_PATH]["phase"]) == ("processing", "read")
    run = view["runs"][0]
    assert run["current_stage"] == "discover" and run["finished_at"] is None
    assert {item["path"] for item in run["documents"]} == {PENDING_PATH, NEW_PATH}

    # later the run is writing topics: a document whose own stages are done is where the run is
    _write_report(
        storage,
        run_id,
        status="running",
        finished_at=None,
        release_id=None,
        current_stage="topics",
        documents=documents,
        stages=[],
    )
    service = _service(storage)
    rows = _rows(service.process(owner=True))
    row = rows[PENDING_PATH]
    assert (row["state"], row["stage"], row["step"], row["phase"]) == (
        "processing",
        "topics",
        6,
        "write",
    )
    # a document outside the run is not moved by it
    assert rows[DONE_PATH]["state"] == "in_wiki" and rows[DONE_PATH]["phase"] is None


def test_what_a_release_changed_and_each_documents_last_change(storage: FolderStorage) -> None:
    sid = source_id_for(DONE_PATH)
    _write_report(
        storage,
        "run-29991231-235959-00000002",
        status="succeeded",
        release_id=RELEASE_ID,
        documents=[{"source_id": sid, "path": DONE_PATH, "change": "changed"}],
        page_changes=[
            {"path": DONE_PAGE.lstrip("/") + ".md", "change": "changed"},
            {"path": "topics/no-such-topic.md", "change": "removed"},
        ],
    )
    view = _service(storage).process(owner=True)
    run = view["runs"][0]
    changes = run["changes"]
    assert changes["counts"] == {"added": 0, "changed": 1, "removed": 1}
    assert changes["changed"][0]["url"] == DONE_PAGE and changes["changed"][0]["title"]
    assert changes["removed"][0]["url"] is None
    assert changes["contradictions"] == {"opened": [], "closed": []}
    assert run["is_current"] is True
    last = _rows(view)[DONE_PATH]["last_change"]
    assert last["change"] == "changed"
    assert [page["url"] for page in last["pages"]] == [DONE_PAGE]
    assert _rows(view)[DONE_PATH]["document_url"] == f"/evidence/{sid}/"


def test_contradictions_opened_and_closed() -> None:
    from docwiki.contracts.runs import RunReport
    from docwiki.portal.process import _changes

    report = RunReport.model_validate(
        {
            **json.loads(
                json.dumps(
                    {
                        "run_id": "run-20260401-090000-00000003",
                        "kind": "ingest",
                        "requested_by": "event",
                        "status": "succeeded",
                        "started_at": "2026-04-01T09:00:00Z",
                        "audience": "public",
                        "release_id": RELEASE_ID,
                        "versions": {
                            "docwiki": "1",
                            "domain_pack": "batiment",
                            "domain_pack_hash": "x",
                        },
                        "cost": {"price_table": "test"},
                    }
                )
            ),
            "page_changes": [
                {
                    "path": "topics/a.md",
                    "change": "changed",
                    "contradictions": 1,
                    "previous_contradictions": 0,
                },
                {
                    "path": "topics/b.md",
                    "change": "changed",
                    "contradictions": 0,
                    "previous_contradictions": 2,
                },
                {"path": "topics/c.md", "change": "added", "contradictions": 1},
                {"path": "topics/d.md", "change": "changed", "contradictions": 1},
            ],
        }
    )
    changes = _changes(report, None)
    assert [item["title"] for item in changes["contradictions"]["opened"]] == ["a", "c"]
    assert [item["title"] for item in changes["contradictions"]["closed"]] == ["b"]


def test_visitors_do_not_see_documents_above_the_audience_in_runs(tmp_path: Path) -> None:
    storage = seed_storage(tmp_path / "store")  # the done document is internal
    sid = source_id_for(DONE_PATH)
    _write_report(
        storage,
        "run-29991231-235959-00000004",
        status="succeeded",
        release_id=RELEASE_ID,
        documents=[{"source_id": sid, "path": DONE_PATH, "change": "new"}],
    )
    service = _service(storage)
    assert service.process(owner=True)["runs"][0]["documents"]
    assert service.process(owner=False)["runs"][0]["documents"] == []


# --- the owner's rebuild ----------------------------------------------------------------------


def _client(service: ProcessService) -> TestClient:
    config = OwnerConfig(owners=frozenset({OWNER}), max_upload_bytes=1024)
    return TestClient(Starlette(routes=process_routes(service, config)), base_url=f"https://{HOST}")


def test_the_owner_rebuilds_the_wiki(storage: FolderStorage) -> None:
    sent: list[QueueMessage] = []
    service = _service(storage, enqueue=sent.append, daily_rebuilds=2)
    client = _client(service)
    me = client.get("/api/owner/me", headers=SIGNED_IN).json()
    assert me["rebuild"] == {"left": 2}
    assert client.get("/api/owner/me").json()["rebuild"] is None

    response = client.put("/api/owner/runs/key-0001", headers=WRITE)
    assert response.status_code == 202
    assert response.json() == {"queued": True, "kind": "rebuild", "rebuilds_left": 1}
    assert [(m.kind, m.requested_by, m.idempotency_key) for m in sent] == [
        ("rebuild", "owner", "owner:rebuild:key-0001")
    ]
    # the same key again: queued once
    assert client.put("/api/owner/runs/key-0001", headers=WRITE).status_code == 202
    assert len(sent) == 1
    assert client.put("/api/owner/runs/key-0002", headers=WRITE).status_code == 202
    over = client.put("/api/owner/runs/key-0003", headers=WRITE)
    assert over.status_code == 429 and len(sent) == 2


def test_only_the_owner_rebuilds(storage: FolderStorage) -> None:
    sent: list[QueueMessage] = []
    client = _client(_service(storage, enqueue=sent.append))
    assert client.put("/api/owner/runs/key-0001").status_code == 401
    forged = {"x-ms-client-principal-id": str(uuid.UUID(int=0xBAD))}
    assert (
        client.put(
            "/api/owner/runs/key-0001", headers={**forged, "x-docwiki-owner": "1"}
        ).status_code
        == 403
    )
    assert client.put("/api/owner/runs/key-0001", headers=SIGNED_IN).status_code == 403
    cross = {**WRITE, "origin": "https://elsewhere.example.org"}
    assert client.put("/api/owner/runs/key-0001", headers=cross).status_code == 403
    assert client.put("/api/owner/runs/bad", headers=WRITE).status_code == 400
    assert client.post("/api/owner/runs/key-0001", headers=WRITE).status_code == 405
    assert sent == []


def test_no_rebuild_without_a_queue(storage: FolderStorage) -> None:
    client = _client(_service(storage))
    assert client.put("/api/owner/runs/key-0001", headers=WRITE).status_code == 503
    assert client.get("/api/owner/me", headers=SIGNED_IN).json()["rebuild"] is None


@pytest.mark.parametrize(
    ("stage", "expected"),
    [("compile", ("compile", 4, "write")), ("site", ("site", 12, "check"))],
)
def test_a_changed_document_in_the_wiki_follows_its_run(
    storage: FolderStorage, stage: str, expected: tuple[str, int, str]
) -> None:
    """A new version of a document already in the wiki: its old state says done, the run is at
    work on it, so it is processing where the run is (not "In the wiki")."""
    _write_report(
        storage,
        "run-29991231-235959-00000009",
        status="running",
        finished_at=None,
        release_id=None,
        current_stage=stage,
        documents=[{"source_id": source_id_for(DONE_PATH), "path": DONE_PATH, "change": "changed"}],
        stages=[],
    )
    row = _rows(_service(storage).process(owner=True))[DONE_PATH]
    assert (row["state"], row["stage"], row["step"], row["phase"]) == ("processing", *expected)


def test_a_new_version_of_a_document_reads_received_until_its_run(storage: FolderStorage) -> None:
    """The file changed after the release was published: not "In the wiki" any more."""
    import os
    import time

    assert _rows(_service(storage).process(owner=True))[DONE_PATH]["state"] == "in_wiki"
    now = time.time()
    os.utime(storage.path_for(f"raw/{DONE_PATH}"), (now, now))
    row = _rows(_service(storage).process(owner=True))[DONE_PATH]
    assert (row["state"], row["phase"]) == ("received", None)
    assert row["page_url"] == DONE_PAGE  # the version in the wiki is still linked


def test_published_originals_are_linked(storage: FolderStorage) -> None:
    sid = source_id_for(DONE_PATH)
    storage.write_bytes(f"releases/{RELEASE_ID}/evidence/{sid}/original.docx", b"PK")
    rows = _rows(_service(storage).process(owner=True))
    assert rows[DONE_PATH]["original_url"] == f"/evidence/{sid}/original.docx"
    assert rows[NEW_PATH]["original_url"] is None


def test_a_last_change_older_than_the_listed_runs_is_found(storage: FolderStorage) -> None:
    sid = source_id_for(DONE_PATH)
    _write_report(
        storage,
        "run-29991230-000000-00000001",
        status="succeeded",
        release_id=RELEASE_ID,
        documents=[{"source_id": sid, "path": DONE_PATH, "change": "new"}],
        page_changes=[{"path": DONE_PAGE.lstrip("/") + ".md", "change": "added"}],
    )
    for n in range(12):  # newer runs that did something else
        _write_report(
            storage,
            f"run-29991231-0000{n:02d}-000000{n:02d}",
            status="succeeded",
            release_id=RELEASE_ID,
            documents=[],
            page_changes=[],
        )
    view = _service(storage).process(owner=True)
    assert len(view["runs"]) == 10
    last = _rows(view)[DONE_PATH]["last_change"]
    assert last["run_id"] == "run-29991230-000000-00000001" and last["change"] == "new"
