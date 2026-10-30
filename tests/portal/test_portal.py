from __future__ import annotations

import time
from pathlib import Path

import httpx
import pytest
from portal_testkit import publish, site_files
from starlette.testclient import TestClient

from docwiki.contracts.storage import FolderStorage
from docwiki.portal import (
    CONTENT_SECURITY_POLICY,
    SECURITY_HEADERS,
    PortalSyncError,
    SiteSync,
    create_app,
)
from docwiki.portal.__main__ import storage_from_env
from docwiki.release import ReleaseIntegrityError


@pytest.fixture
def storage(tmp_path: Path) -> FolderStorage:
    return FolderStorage(tmp_path / "store", fsync=False)


def assert_security_headers(response: httpx.Response) -> None:
    for name, value in SECURITY_HEADERS.items():
        assert response.headers[name] == value, name


def test_security_headers_follow_the_spec() -> None:
    assert "default-src 'self'" in CONTENT_SECURITY_POLICY
    assert "frame-ancestors 'none'" in CONTENT_SECURITY_POLICY
    assert "object-src 'none'" in CONTENT_SECURITY_POLICY
    assert "unsafe-inline" not in CONTENT_SECURITY_POLICY.split("script-src")[1].split(";")[0]
    assert SECURITY_HEADERS["x-content-type-options"] == "nosniff"
    assert SECURITY_HEADERS["referrer-policy"] == "no-referrer"


def test_sync_downloads_and_verifies_only_the_site(storage: FolderStorage, tmp_path: Path) -> None:
    pointer = publish(storage, tmp_path / "s1")
    sync = SiteSync(storage, tmp_path / "cache")
    assert sync.refresh() is True
    state = sync.state
    assert state is not None
    assert state.release_id == pointer.release_id
    assert state.manifest_sha256 == pointer.manifest_sha256
    assert (state.root / "sources" / "a.html").read_bytes().endswith(b"source a</p>")
    assert not (state.root / "wiki").exists()  # only site/ is mirrored
    assert set(state.hashes) == {path.removeprefix("site/") for path in site_files("first")}
    assert sync.refresh() is False  # pointer unchanged: no download
    assert sync.last_error is None


def test_sync_follows_current_json_and_keeps_the_previous_copy(
    storage: FolderStorage, tmp_path: Path
) -> None:
    publish(storage, tmp_path / "s1")
    sync = SiteSync(storage, tmp_path / "cache", keep=2)
    sync.refresh()
    first_root = sync.state.root  # type: ignore[union-attr]
    second = publish(storage, tmp_path / "s2", title="second", day=1)
    assert sync.refresh() is True
    assert sync.state.release_id == second.release_id  # type: ignore[union-attr]
    assert first_root.is_dir()  # in-flight requests may still read it
    third = publish(storage, tmp_path / "s3", title="third", day=2)
    sync.refresh()
    assert sync.state.release_id == third.release_id  # type: ignore[union-attr]
    assert not first_root.exists()
    assert len([p for p in (tmp_path / "cache").iterdir() if p.is_dir()]) == 2


def test_sync_rejects_tampered_files(storage: FolderStorage, tmp_path: Path) -> None:
    pointer = publish(storage, tmp_path / "s1")
    storage.write_bytes(f"releases/{pointer.release_id}/site/index.html", b"<script>evil</script>")
    sync = SiteSync(storage, tmp_path / "cache")
    with pytest.raises(ReleaseIntegrityError, match=r"site/index\.html"):
        sync.refresh()
    assert sync.state is None and "ReleaseIntegrityError" in (sync.last_error or "")
    assert not any((tmp_path / "cache").glob("*/index.html"))


def test_sync_errors(storage: FolderStorage, tmp_path: Path) -> None:
    sync = SiteSync(storage, tmp_path / "cache")
    with pytest.raises(PortalSyncError, match="no release published"):
        sync.refresh()
    publish(storage, tmp_path / "s1", with_site=False)
    with pytest.raises(PortalSyncError, match=r"no site/index\.html"):
        sync.refresh()


def test_portal_serves_the_current_site(storage: FolderStorage, tmp_path: Path) -> None:
    pointer = publish(storage, tmp_path / "s1")
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        home = client.get("/")
        assert home.status_code == 200
        assert home.headers["content-type"] == "text/html; charset=utf-8"
        assert b"<p>home</p>" in home.content
        assert_security_headers(home)
        assert home.headers["cache-control"] == "public, max-age=60, stale-while-revalidate=600"

        page = client.get("/sources/a")
        assert page.status_code == 200 and b"source a" in page.content
        assert client.get("/sources/a.html").content == page.content
        assert client.get("/sources/").status_code == 200

        redirect = client.get("/sources?x=1", follow_redirects=False)
        assert redirect.status_code == 308
        assert redirect.headers["location"] == "/sources/?x=1"
        assert_security_headers(redirect)

        # The process page was renamed (ADR 0010): old links keep working.
        for old in ("/how-it-works", "/how-it-works/"):
            moved = client.get(old + "?x=1", follow_redirects=False)
            assert moved.status_code == 308
            assert moved.headers["location"] == "/pipeline?x=1"

        script = client.get("/postscript.js")
        assert script.headers["content-type"] == "text/javascript; charset=utf-8"
        assert client.get("/static/docwiki/icon.svg").headers["content-type"] == "image/svg+xml"
        assert client.get("/evidence/src-0/img/p0001.png").headers["content-type"] == "image/png"

        etag = page.headers["etag"]
        cached = client.get("/sources/a", headers={"if-none-match": etag})
        assert cached.status_code == 304 and cached.content == b""
        assert_security_headers(cached)

        head = client.head("/sources/a")
        assert head.status_code == 200 and head.content == b""

        health = client.get("/healthz")
        assert health.status_code == 200
        assert health.json()["release_id"] == pointer.release_id
        assert health.json()["status"] == "ok"
        assert_security_headers(health)
        assert client.get("/livez").json() == {"status": "alive"}


@pytest.mark.parametrize(
    "path",
    [
        "/missing",
        "/sources/missing",
        "/../store/releases/current.json",
        "/%2e%2e/%2e%2e/secret",
        "/.docwiki-portal-complete",
        "/sources/..%5c..%5cindex.html",
    ],
)
def test_portal_not_found_and_traversal(storage: FolderStorage, tmp_path: Path, path: str) -> None:
    publish(storage, tmp_path / "s1")
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        response = client.get(path)
        assert response.status_code == 404
        assert b"Page not found" in response.content
        assert_security_headers(response)


def test_portal_rejects_other_methods(storage: FolderStorage, tmp_path: Path) -> None:
    publish(storage, tmp_path / "s1")
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        response = client.post("/sources/a")
        assert response.status_code == 405
        assert_security_headers(response)


def test_portal_without_a_release_is_unavailable(storage: FolderStorage, tmp_path: Path) -> None:
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        page = client.get("/")
        assert page.status_code == 503 and page.headers["retry-after"] == "30"
        assert_security_headers(page)
        health = client.get("/healthz")
        assert health.status_code == 503
        assert "no release published" in health.json()["error"]


def test_portal_polls_current_json(storage: FolderStorage, tmp_path: Path) -> None:
    publish(storage, tmp_path / "s1")
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0.05)
    with TestClient(app) as client:
        assert b"first" in client.get("/").content
        second = publish(storage, tmp_path / "s2", title="second", day=1)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if client.get("/healthz").json()["release_id"] == second.release_id:
                break
            time.sleep(0.05)
        assert client.get("/healthz").json()["release_id"] == second.release_id
        assert b"second" in client.get("/").content


def test_portal_keeps_serving_when_a_sync_fails(storage: FolderStorage, tmp_path: Path) -> None:
    first = publish(storage, tmp_path / "s1")
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0.05)
    with TestClient(app) as client:
        storage.write_bytes("releases/current.json", b"{not json")
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline and client.get("/healthz").json()["error"] is None:
            time.sleep(0.05)
        health = client.get("/healthz").json()
        assert health["error"] and health["release_id"] == first.release_id
        assert client.get("/").status_code == 200


def test_portal_previews_a_local_site_folder(tmp_path: Path) -> None:
    site = tmp_path / "site"
    for path, data in site_files("preview").items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    with TestClient(create_app(site_dir=site)) as client:
        assert b"preview" in client.get("/sources/a").content
        assert client.get("/healthz").json()["release_id"] is None
    with pytest.raises(ValueError, match="exactly one"):
        create_app()
    with pytest.raises(PortalSyncError, match=r"no index\.html"):
        create_app(site_dir=tmp_path / "empty")


def test_storage_from_env(tmp_path: Path) -> None:
    storage = storage_from_env({"DOCWIKI_MODE": "local", "DOCWIKI_WORK_DIR": str(tmp_path)})
    assert isinstance(storage, FolderStorage)
    with pytest.raises(SystemExit, match="expected local or azure"):
        storage_from_env({"DOCWIKI_MODE": "cloud"})


def test_portal_wraps_its_app_only_when_exporting(monkeypatch, tmp_path):
    import uvicorn

    from docwiki.portal import __main__ as portal_main

    (tmp_path / "index.html").write_text("<p>wiki</p>", encoding="utf-8")
    served: list[object] = []
    monkeypatch.setattr(uvicorn, "run", lambda app, **_kwargs: served.append(app))
    monkeypatch.setattr(portal_main.LiveAsk, "from_env", staticmethod(lambda _env: None))
    monkeypatch.setattr(portal_main, "instrument_asgi", lambda app: ("traced", app))
    for exporting in (False, True):
        monkeypatch.setattr(portal_main, "configure_exporter", lambda e=exporting: e)
        assert portal_main.main(["--site-dir", str(tmp_path)]) == 0
    plain, traced = served
    assert not isinstance(plain, tuple) and traced[0] == "traced"
