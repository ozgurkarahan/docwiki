from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from process_testkit import (
    BROKEN_PATH,
    DONE_PATH,
    GONE_PATH,
    NEW_PATH,
    ODD_PATH,
    OWNER,
    PENDING_PATH,
    RELEASE_ID,
    seed_storage,
)
from starlette.applications import Starlette
from starlette.testclient import TestClient

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.storage import FolderStorage
from docwiki.mcp.workstore import WorkStore
from docwiki.portal.owner import OwnerConfig, OwnerConfigError, process_routes
from docwiki.portal.process import (
    JUST_PUBLISHED_S,
    PathError,
    ProcessService,
    RawBlob,
    UploadConflictError,
    UploadError,
    UploadQuotaError,
    UploadTooLargeError,
    check_upload_path,
    document_state,
    site_link,
)

HOST = "wiki.example.org"
DONE_PAGE = "/sources/2026-03-24-compte-rendu-de-chantier-n3"
HIDDEN_PATH = "(not in this site's audience)"
SIGNED_IN = {"x-ms-client-principal-id": OWNER, "x-ms-client-principal-name": "owner@example.org"}
WRITE = {**SIGNED_IN, "x-docwiki-owner": "1"}


@pytest.fixture
def storage(tmp_path: Path) -> FolderStorage:
    return seed_storage(tmp_path / "store", sensitivity="public")


def _service(storage: FolderStorage, **kwargs: Any) -> ProcessService:
    options: dict[str, Any] = {"max_upload_bytes": 1024, "daily_uploads": 5}
    options.update(kwargs)
    return ProcessService(storage, **options)


def _rows(view: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {row["path"]: row for row in view["documents"]}


# --- paths ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "manuel-pompe.pdf",
        "uploads/Compte rendu (1).pdf",
        "a/b/c/d.md",
        "chantiers/moreau/3-execution/schedule/PLN-2026-003_indice-B.xlsx",
        "a/b/c/d/e/f.md",
        "notes_v2+final.DOCX",
        "  padded.md  ",
    ],
)
def test_check_upload_path_accepts(path: str) -> None:
    assert check_upload_path(path) == path.strip()


@pytest.mark.parametrize(
    "path",
    [
        "",
        "   ",
        "a/b/c/d/e/f/g.md",
        "/abs.md",
        "a//b.md",
        "a\\b.md",
        "../x.md",
        "a/./b.md",
        "a/../b.md",
        ".hidden.md",
        "dir/.hidden.md",
        "tool.exe",
        "noextension",
        "trailing-dot./x.md",
        "a /x.md",
        "x" * 201 + ".md",
        "bad:name.md",
        "tab\t.md",
    ],
)
def test_check_upload_path_refuses(path: str) -> None:
    with pytest.raises(PathError):
        check_upload_path(path)


@pytest.mark.parametrize(
    ("path", "link"),
    [
        ("sources/x.md", "/sources/x"),
        ("index.md", "/"),
        ("topics/index.md", "/topics/"),
        ("sources/a b.md", None),
        ("sources/x.md#section", "/sources/x"),
        ("../x.md", None),
        ("a/../x.md", None),
        ("/x.md", None),
        ("a//x.md", None),
        ("http://example.org/x.md", None),
        ("sources/x.pdf", None),
        ("", None),
        (None, None),
    ],
)
def test_site_link(path: str | None, link: str | None) -> None:
    assert site_link(path) == link


# --- the process view ------------------------------------------------------------------------


def test_process_merges_raw_files_with_pipeline_state(storage: FolderStorage) -> None:
    view = _service(storage).process(owner=True)
    rows = _rows(view)
    assert {path: row["status"] for path, row in rows.items()} == {
        NEW_PATH: "new",
        BROKEN_PATH: "failed",
        ODD_PATH: "quarantined",
        PENDING_PATH: "pending",
        GONE_PATH: "deleted",
        DONE_PATH: "done",
    }
    # The site's words (ADR 0010), in display order.
    assert [(row["state"], row["path"]) for row in view["documents"]] == [
        ("failed", BROKEN_PATH),
        ("received", NEW_PATH),
        ("queued", PENDING_PATH),
        ("in_wiki", DONE_PATH),
        ("held_back", ODD_PATH),
        ("removed", GONE_PATH),
    ]
    assert view["states"]["in_wiki"] == 1 and view["states"]["processing"] == 0
    assert rows[DONE_PATH]["title"]
    assert rows[NEW_PATH]["title"] is None
    assert view["counts"] == {
        "new": 1,
        "failed": 1,
        "quarantined": 1,
        "pending": 1,
        "deleted": 1,
        "done": 1,
    }
    assert view["total"] == 6
    assert rows[NEW_PATH]["source_id"] == source_id_for(NEW_PATH)
    assert rows[NEW_PATH]["stage"] is None
    assert rows[NEW_PATH]["size"] == len(b"# Fresh note\n")
    assert rows[NEW_PATH]["modified"] is not None
    assert rows[BROKEN_PATH]["stage"] == "extract"
    assert "no text layer" in rows[BROKEN_PATH]["last_error"]
    assert rows[GONE_PATH]["modified"] is not None  # from the state: no raw file any more


def test_process_gives_the_page_of_a_document_in_the_release(storage: FolderStorage) -> None:
    view = _service(storage).process(owner=True)
    rows = _rows(view)
    assert rows[DONE_PATH]["in_release"] is True
    assert rows[DONE_PATH]["page_url"] == DONE_PAGE
    assert rows[BROKEN_PATH]["page_url"] is None
    assert rows[BROKEN_PATH]["in_release"] is False
    release = view["release"]
    assert release["release_id"] == RELEASE_ID
    assert release["audience"] == "public"
    assert release["sources"] == 3
    assert release["pages"] > 0


def test_process_runs_come_from_the_work_reports(storage: FolderStorage) -> None:
    runs = _service(storage).process()["runs"]
    newest, older = runs
    assert (newest["status"], older["status"]) == ("failed", "succeeded")
    assert (newest["is_current"], older["is_current"]) == (False, True)
    assert [stage["stage"] for stage in newest["stages"]] == ["discover", "extract"]
    assert newest["stages"][1]["failures"] == 1
    assert newest["counts"]["quarantined"] == 1
    assert older["cost"] == {"currency": "USD", "total": 0.42, "duration_s": 540.0}
    assert set(newest) >= {"run_id", "kind", "requested_by", "gates", "release_id"}


@pytest.mark.parametrize(
    ("status", "stage", "in_release", "hidden", "superseded", "expected"),
    [
        ("new", None, False, False, False, ("received", None)),
        ("pending", None, False, False, False, ("queued", None)),
        ("pending", "compile", False, False, False, ("processing", 4)),
        # Every stage done, but the release that carries it is not out yet.
        ("done", None, False, False, False, ("processing", 13)),
        ("done", None, True, False, False, ("in_wiki", None)),
        ("done", None, True, False, True, ("superseded", None)),
        ("done", None, True, True, False, ("held_back", None)),
        ("quarantined", "compile", False, False, False, ("held_back", None)),
        ("failed", "extract", False, False, False, ("failed", None)),
        ("deleted", None, False, False, False, ("removed", None)),
    ],
)
def test_document_state(
    status: str,
    stage: str | None,
    in_release: bool,
    hidden: bool,
    superseded: bool,
    expected: tuple[str, int | None],
) -> None:
    assert (
        document_state(status, stage, in_release=in_release, hidden=hidden, superseded=superseded)
        == expected
    )


def test_a_done_document_outside_the_release_is_still_processing(tmp_path: Path) -> None:
    storage = seed_storage(tmp_path / "store", sensitivity="public")
    # The served catalog does not have the document yet: a run finished its stages, not its publish.
    service = _service(storage)
    service._current_catalog = lambda: (None, None)  # type: ignore[method-assign]
    row = _rows(service.process(owner=True))[DONE_PATH]
    assert (row["state"], row["step"], row["steps"]) == ("processing", 13, 13)
    assert row["page_url"] is None and row["title"] is None


def test_no_op_checks_are_counted_not_listed(storage: FolderStorage) -> None:
    before = _service(storage).process()["runs"]
    newest = WorkStore(storage).run_ids()[-1]
    report = json.loads(storage.read_bytes(f"work/runs/{newest}/report.json"))
    for n in range(3):
        # Later than every seeded run (run ids sort by their UTC timestamp).
        run_id = f"run-29991231-23595{n}-0000000{n}"
        report.update(run_id=run_id, status="no-op", release_id=None)
        storage.write_bytes(f"work/runs/{run_id}/report.json", json.dumps(report).encode("utf-8"))
    view = _service(storage).process()
    assert [run["run_id"] for run in view["runs"]] == [run["run_id"] for run in before]
    assert view["checks"]["count"] == 3
    assert view["checks"]["last"]


def test_status_idle_processing_and_published(storage: FolderStorage) -> None:
    service = _service(storage)
    # The seeded storage has documents on their way: received, queued.
    status = service.status()
    assert status["state"] == "processing" and status["processing"] == 2
    assert status["release_id"] == RELEASE_ID

    done_only = [RawBlob(path=DONE_PATH, size=1)]
    quiet = _service(storage, list_raw=lambda: done_only)
    stamp = quiet.process()["release"]["published_at"]
    published = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    assert quiet.status(now=published + timedelta(seconds=JUST_PUBLISHED_S + 1))["state"] == "idle"

    fresh = [RawBlob(path=DONE_PATH, size=1, modified=published - timedelta(minutes=3))]
    recent = _service(storage, list_raw=lambda: fresh)
    status = recent.status(now=published + timedelta(minutes=2))
    assert status["state"] == "published"
    assert status["document"] == {"title": status["document"]["title"], "page_url": DONE_PAGE}
    assert status["document"]["title"]

    old = [RawBlob(path=DONE_PATH, size=1, modified=published - timedelta(days=3))]
    status = _service(storage, list_raw=lambda: old).status(now=published + timedelta(minutes=2))
    assert status["state"] == "idle" and status["document"] is None


def test_process_without_a_release_or_state(tmp_path: Path) -> None:
    view = _service(FolderStorage(tmp_path, fsync=False)).process()
    assert view["release"] is None
    assert view["runs"] == []
    assert view["documents"] == []
    assert view["total"] == 0
    assert set(view["counts"].values()) == {0}


def test_queue_depth_is_reported_and_degrades_to_unknown(storage: FolderStorage) -> None:
    assert _service(storage, queue_depth=lambda: 3).process()["queued"] == 3

    def broken() -> int:
        raise RuntimeError("queue unreachable")

    assert _service(storage, queue_depth=broken).process()["queued"] is None
    assert _service(storage).process()["queued"] is None


def test_custom_raw_lister(storage: FolderStorage) -> None:
    listed = [RawBlob(path="only/this.md", size=7)]
    view = _service(storage, list_raw=lambda: listed).process(owner=True)
    assert _rows(view)["only/this.md"]["status"] == "new"
    assert _rows(view)["only/this.md"]["size"] == 7
    assert DONE_PATH not in _rows(view)  # no raw blob, and not deleted: not listed


def test_visitors_do_not_see_documents_above_the_audience(tmp_path: Path) -> None:
    storage = seed_storage(tmp_path / "store")  # the done document is internal
    service = _service(storage)
    owner_rows = _rows(service.process(owner=True))
    visitor = service.process(owner=False)
    visitor_rows = _rows(visitor)
    assert owner_rows[DONE_PATH]["hidden"] is True
    assert owner_rows[DONE_PATH]["page_url"] == DONE_PAGE
    assert DONE_PATH not in visitor_rows
    hidden = visitor_rows[HIDDEN_PATH]
    assert hidden["hidden"] is True
    assert hidden["source_id"] is None and hidden["page_url"] is None
    assert hidden["status"] == "done"
    assert visitor["total"] == 6
    assert all(DONE_PATH not in str(row.values()) for row in visitor["documents"])


def test_visitors_see_that_a_document_failed_but_not_why(storage: FolderStorage) -> None:
    service = _service(storage)
    owner = _rows(service.process(owner=True))[BROKEN_PATH]
    visitor_rows = _rows(service.process(owner=False))
    assert owner["last_error"]
    assert visitor_rows[BROKEN_PATH]["last_error"] is None
    assert visitor_rows[BROKEN_PATH]["failed"] is True
    assert visitor_rows[NEW_PATH]["failed"] is False


def test_the_view_is_cached_briefly(storage: FolderStorage) -> None:
    ticks = iter([0.0, 0.0, 1.0, 10.0, 10.0, 10.0, 10.0])
    service = _service(storage, clock=lambda: next(ticks))
    first = service.process(owner=True)
    storage.write_bytes("raw/uploads/late.md", b"late")
    assert service.process(owner=True)["total"] == first["total"]
    assert service.process(owner=True)["total"] == first["total"] + 1


# --- uploads ---------------------------------------------------------------------------------


def test_upload_writes_raw_and_shows_the_file_as_new(storage: FolderStorage) -> None:
    service = _service(storage)
    path = "uploads/Compte rendu (1).pdf"
    result = service.upload(path, b"%PDF-1.7 report")
    assert result == {
        "path": path,
        "size": 15,
        "replaced": False,
        "source_id": source_id_for(path),
    }
    assert storage.read_bytes(f"raw/{path}") == b"%PDF-1.7 report"
    row = _rows(service.process(owner=True))[path]  # the cache was invalidated
    assert row["status"] == "new"
    assert row["size"] == 15
    assert service.uploads_left() == 4


def test_upload_refuses_to_overwrite_unless_asked(storage: FolderStorage) -> None:
    service = _service(storage)
    with pytest.raises(UploadConflictError):
        service.upload(NEW_PATH, b"other")
    assert storage.read_bytes(f"raw/{NEW_PATH}") == b"# Fresh note\n"
    assert service.uploads_left() == 5
    result = service.upload(NEW_PATH, b"# v2\n", replace=True)
    assert result["replaced"] is True
    assert storage.read_bytes(f"raw/{NEW_PATH}") == b"# v2\n"


def test_replace_of_a_missing_file_creates_it(storage: FolderStorage) -> None:
    result = _service(storage).upload("uploads/brand-new.md", b"x", replace=True)
    assert result["replaced"] is False
    assert storage.exists("raw/uploads/brand-new.md")


@pytest.mark.parametrize(
    ("path", "data", "error"),
    [
        ("uploads/tool.exe", b"MZ", UploadError),
        ("../escape.md", b"x", UploadError),
        ("uploads/empty.md", b"", UploadError),
        ("uploads/big.md", b"x" * 11, UploadTooLargeError),
    ],
)
def test_invalid_uploads(
    storage: FolderStorage, path: str, data: bytes, error: type[Exception]
) -> None:
    service = _service(storage, max_upload_bytes=10)
    with pytest.raises(error):
        service.upload(path, data)
    if ".." not in path:
        assert not storage.exists(f"raw/{path}")
    assert service.uploads_left() == 5


def test_daily_upload_allowance(storage: FolderStorage) -> None:
    day = [date(2026, 3, 1)]
    service = _service(storage, daily_uploads=1, today=lambda: day[0])
    service.upload("uploads/one.md", b"1")
    assert service.uploads_left() == 0
    with pytest.raises(UploadQuotaError):
        service.upload("uploads/two.md", b"2")
    assert not storage.exists("raw/uploads/two.md")
    day[0] = date(2026, 3, 2)
    assert service.uploads_left() == 1
    service.upload("uploads/two.md", b"2")
    assert storage.exists("raw/uploads/two.md")


def test_storage_check(storage: FolderStorage) -> None:
    service = _service(storage)
    assert service.storage_ok() is True

    def fail(_prefix: str = "") -> list[str]:
        raise OSError("disk gone")

    storage.list = fail  # type: ignore[method-assign]
    assert service.storage_ok() is False


# --- routes ----------------------------------------------------------------------------------


def _client(service: ProcessService | None, config: OwnerConfig | None = None) -> TestClient:
    config = config or OwnerConfig(owners=frozenset({OWNER}), max_upload_bytes=1024)
    return TestClient(Starlette(routes=process_routes(service, config)), base_url=f"https://{HOST}")


@pytest.fixture
def service(storage: FolderStorage) -> ProcessService:
    return _service(storage, queue_depth=lambda: 2)


@pytest.fixture
def client(service: ProcessService) -> TestClient:
    return _client(service)


def test_process_is_public(client: TestClient) -> None:
    response = client.get("/api/process")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["queued"] == 2
    assert body["total"] == 6
    assert _rows(body)[BROKEN_PATH]["last_error"] is None


def test_status_is_public(client: TestClient) -> None:
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["state"] == "processing"


def test_status_without_storage_is_unavailable() -> None:
    app = Starlette(routes=process_routes(None, OwnerConfig()))
    assert TestClient(app).get("/api/status").status_code == 503


def test_process_hides_for_visitors_and_shows_for_the_owner(tmp_path: Path) -> None:
    storage = seed_storage(tmp_path / "store")
    client = _client(_service(storage))
    visitor = client.get("/api/process").json()
    assert DONE_PATH not in _rows(visitor) and HIDDEN_PATH in _rows(visitor)
    stranger = client.get("/api/process", headers={"x-ms-client-principal-id": "someone"}).json()
    assert DONE_PATH not in _rows(stranger)
    owner = client.get("/api/process", headers=SIGNED_IN).json()
    assert _rows(owner)[DONE_PATH]["hidden"] is True
    assert _rows(owner)[BROKEN_PATH]["last_error"]


def test_process_without_storage_is_unavailable() -> None:
    assert _client(None).get("/api/process").status_code == 503


def test_me_for_anonymous(client: TestClient) -> None:
    body = client.get("/api/owner/me").json()
    assert body["sign_in"] is True
    assert body["signed_in"] is False
    assert body["owner"] is False
    assert body["name"] is None
    assert body["upload"] is None
    assert body["sign_in_url"].startswith("/.auth/login/aad")
    assert body["sign_out_url"] is None


def test_me_for_a_non_owner(client: TestClient) -> None:
    body = client.get(
        "/api/owner/me",
        headers={"x-ms-client-principal-id": "someone", "x-ms-client-principal-name": "x@y.z"},
    ).json()
    assert (body["sign_in"], body["signed_in"], body["owner"]) == (True, True, False)
    assert body["name"] is None and body["upload"] is None
    assert body["sign_out_url"].startswith("/.auth/logout")


def test_me_for_the_owner(storage: FolderStorage) -> None:
    config = OwnerConfig(owners=frozenset({OWNER}), max_upload_bytes=3 * 1024 * 1024)
    body = _client(_service(storage), config).get("/api/owner/me", headers=SIGNED_IN).json()
    assert (body["sign_in"], body["signed_in"], body["owner"]) == (True, True, True)
    assert body["name"] == "owner@example.org"
    assert body["sign_out_url"].startswith("/.auth/logout")
    assert body["upload"]["max_mb"] == 3
    assert body["upload"]["uploads_left"] == 5
    assert ".md" in body["upload"]["extensions"]


def test_me_without_storage_is_never_owner() -> None:
    body = _client(None).get("/api/owner/me", headers=SIGNED_IN).json()
    assert body["owner"] is False and body["upload"] is None


def test_local_owner_is_everyone(service: ProcessService) -> None:
    client = _client(service, OwnerConfig(local_owner=True, owners=frozenset({OWNER})))
    body = client.get("/api/owner/me").json()
    assert body["sign_in"] is False
    assert body["signed_in"] is True
    assert body["owner"] is True
    assert body["sign_in_url"] is None and body["sign_out_url"] is None
    assert body["upload"] is not None
    headers = {"x-docwiki-owner": "1"}
    response = client.put("/api/owner/documents/uploads/l.md", content=b"x", headers=headers)
    assert response.status_code == 201
    # the CSRF header stays required
    assert client.put("/api/owner/documents/uploads/m.md", content=b"x").status_code == 403


def test_no_owners_means_no_sign_in(service: ProcessService) -> None:
    client = _client(service, OwnerConfig())
    body = client.get("/api/owner/me", headers=SIGNED_IN).json()
    assert (body["sign_in"], body["owner"], body["sign_in_url"]) == (False, False, None)
    assert client.put("/api/owner/documents/a.md", content=b"x", headers=WRITE).status_code == 403


def test_upload_needs_sign_in(client: TestClient) -> None:
    response = client.put("/api/owner/documents/uploads/a.md", content=b"x")
    assert response.status_code == 401


def test_upload_refuses_another_account(client: TestClient) -> None:
    headers = {"x-ms-client-principal-id": "someone-else", "x-docwiki-owner": "1"}
    response = client.put("/api/owner/documents/uploads/a.md", content=b"x", headers=headers)
    assert response.status_code == 403


@pytest.mark.parametrize(
    "extra",
    [
        {},
        {"x-docwiki-owner": "0"},
        {"x-docwiki-owner": "1", "sec-fetch-site": "cross-site"},
        {"x-docwiki-owner": "1", "sec-fetch-site": "same-site"},
        {"x-docwiki-owner": "1", "origin": "https://evil.example"},
    ],
)
def test_upload_needs_the_header_and_same_origin(
    client: TestClient, storage: FolderStorage, extra: dict[str, str]
) -> None:
    response = client.put(
        "/api/owner/documents/uploads/csrf.md", content=b"x", headers={**SIGNED_IN, **extra}
    )
    assert response.status_code == 403
    assert not storage.exists("raw/uploads/csrf.md")


@pytest.mark.parametrize(
    "extra",
    [
        {"origin": f"https://{HOST}", "sec-fetch-site": "same-origin"},
        {"sec-fetch-site": "none"},
        {"origin": "null"},
    ],
)
def test_same_origin_uploads_are_accepted(client: TestClient, extra: dict[str, str]) -> None:
    response = client.put(
        "/api/owner/documents/uploads/ok.md", content=b"# ok", headers={**WRITE, **extra}
    )
    assert response.status_code == 201, response.text


def test_upload_succeeds(client: TestClient, storage: FolderStorage) -> None:
    response = client.put("/api/owner/documents/uploads/hello.md", content=b"# hi", headers=WRITE)
    assert response.status_code == 201
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "path": "uploads/hello.md",
        "size": 4,
        "replaced": False,
        "source_id": source_id_for("uploads/hello.md"),
        "uploads_left": 4,
    }
    assert storage.read_bytes("raw/uploads/hello.md") == b"# hi"


def test_upload_conflict_then_replace(client: TestClient, storage: FolderStorage) -> None:
    url = f"/api/owner/documents/{NEW_PATH}"
    assert client.put(url, content=b"other", headers=WRITE).status_code == 409
    assert storage.read_bytes(f"raw/{NEW_PATH}") == b"# Fresh note\n"
    response = client.put(f"{url}?replace=true", content=b"other", headers=WRITE)
    assert response.status_code == 201
    assert response.json()["replaced"] is True
    assert storage.read_bytes(f"raw/{NEW_PATH}") == b"other"


def test_upload_size_limits(client: TestClient, storage: FolderStorage) -> None:
    big = b"x" * 1025
    response = client.put("/api/owner/documents/uploads/big.md", content=big, headers=WRITE)
    assert response.status_code == 413  # by content-length
    chunked = client.put(
        "/api/owner/documents/uploads/big.md",
        content=iter([b"x" * 600, b"x" * 600]),
        headers=WRITE,
    )
    assert chunked.status_code == 413  # streamed, no content-length
    assert not storage.exists("raw/uploads/big.md")


def test_upload_bad_requests(client: TestClient) -> None:
    for path in ("uploads/tool.exe", "a/b/c/d/e/f/g.md", "uploads/.hidden.md"):
        response = client.put(f"/api/owner/documents/{path}", content=b"x", headers=WRITE)
        assert response.status_code == 400, path
    empty = client.put("/api/owner/documents/uploads/e.md", content=b"", headers=WRITE)
    assert empty.status_code == 400


def test_upload_quota_is_429(storage: FolderStorage) -> None:
    client = _client(_service(storage, daily_uploads=1))
    assert client.put("/api/owner/documents/a.md", content=b"1", headers=WRITE).status_code == 201
    assert client.put("/api/owner/documents/b.md", content=b"2", headers=WRITE).status_code == 429


def test_upload_without_storage_is_unavailable() -> None:
    response = _client(None).put("/api/owner/documents/a.md", content=b"x", headers=WRITE)
    assert response.status_code == 503


def test_post_to_the_upload_path_is_not_allowed(client: TestClient) -> None:
    response = client.post("/api/owner/documents/uploads/a.md", content=b"x", headers=WRITE)
    assert response.status_code == 405


def test_principal_comparison_ignores_case(client: TestClient, storage: FolderStorage) -> None:
    headers = {**WRITE, "x-ms-client-principal-id": f"  {OWNER.upper()} "}
    response = client.put("/api/owner/documents/uploads/case.md", content=b"x", headers=headers)
    assert response.status_code == 201
    assert storage.exists("raw/uploads/case.md")


# --- configuration ---------------------------------------------------------------------------


def test_owner_config_defaults() -> None:
    config = OwnerConfig.from_env({})
    assert config.owners == frozenset()
    assert config.max_upload_bytes == 50 * 1024 * 1024
    assert config.daily_uploads == 10
    assert config.sign_in is False and config.local_owner is False


def test_owner_config_parses_the_environment() -> None:
    config = OwnerConfig.from_env(
        {
            "DOCWIKI_PORTAL_OWNERS": " AAA-1 , bbb-2,, ",
            "DOCWIKI_PORTAL_MAX_UPLOAD_MB": "5",
            "DOCWIKI_PORTAL_DAILY_UPLOADS": " 3 ",
        }
    )
    assert config.owners == frozenset({"aaa-1", "bbb-2"})
    assert config.max_upload_bytes == 5 * 1024 * 1024
    assert config.daily_uploads == 3
    assert config.sign_in is True
    local = OwnerConfig.from_env({"DOCWIKI_PORTAL_OWNERS": "aaa"}, local_owner=True)
    assert local.local_owner is True and local.sign_in is False


def test_owner_config_blank_numbers_use_defaults() -> None:
    config = OwnerConfig.from_env({"DOCWIKI_PORTAL_MAX_UPLOAD_MB": "  "})
    assert config.max_upload_bytes == 50 * 1024 * 1024


@pytest.mark.parametrize(
    "env",
    [
        {"DOCWIKI_PORTAL_MAX_UPLOAD_MB": "many"},
        {"DOCWIKI_PORTAL_MAX_UPLOAD_MB": "0"},
        {"DOCWIKI_PORTAL_MAX_UPLOAD_MB": "-1"},
        {"DOCWIKI_PORTAL_DAILY_UPLOADS": "1.5"},
        {"DOCWIKI_PORTAL_DAILY_UPLOADS": "0"},
    ],
)
def test_owner_config_rejects_invalid_numbers(env: dict[str, str]) -> None:
    with pytest.raises(OwnerConfigError):
        OwnerConfig.from_env(env)
