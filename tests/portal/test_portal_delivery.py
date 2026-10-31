"""Cache headers, precompressed responses and delta sync of the portal's static site."""

from __future__ import annotations

import gzip
from datetime import timedelta
from pathlib import Path

import pytest
from portal_testkit import CREATED_AT, VERSIONS
from starlette.testclient import TestClient

from docwiki.contracts.gates import gate_results
from docwiki.contracts.manifest import CurrentPointer
from docwiki.contracts.storage import FolderStorage
from docwiki.portal import SiteSync, create_app
from docwiki.portal.app import ASSET_CACHE_CONTROL, CACHE_CONTROL, PAGE_CACHE_CONTROL
from docwiki.portal.sync import GZIP_DIR, gzip_path
from docwiki.release import ReleaseIntegrityError, ReleaseWriter, publish_release

BIG_PAGE = b"<!DOCTYPE html><title>big</title>" + b"<p>Harbor ledger line.</p>" * 200
BIG_SCRIPT = b"console.log('quartz');\n" * 100


def site(title: str) -> dict[str, bytes]:
    return {
        "site/index.html": f"<!DOCTYPE html><title>{title}</title><p>home</p>".encode(),
        "site/404.html": b"<!DOCTYPE html><p>Page not found</p>",
        "site/big.html": BIG_PAGE,
        "site/postscript.js": BIG_SCRIPT,
        "site/index.css": b"body{}",
        "site/static/contentIndex.json": b'{"a": 1}',
        "site/evidence/src-0/img/p0001.png": b"\x89PNG" + bytes(range(256)) * 8,
    }


def publish(
    storage: FolderStorage,
    staging: Path,
    files: dict[str, bytes],
    *,
    day: int = 0,
    audience: str = "public",
) -> CurrentPointer:
    writer = ReleaseWriter(
        staging, created_at=CREATED_AT + timedelta(days=day), audience=audience, versions=VERSIONS
    )
    writer.write_text("wiki/index.md", "# wiki\n")
    for path, data in files.items():
        writer.write_bytes(path, data)
    staged = writer.finalize(gates=gate_results([]))
    return publish_release(storage, staged, now=CREATED_AT + timedelta(days=day))


class CountingStorage:
    """Folder storage that records the keys read."""

    def __init__(self, inner: FolderStorage) -> None:
        self.inner = inner
        self.reads: list[str] = []

    def read_bytes(self, key: str) -> bytes:
        self.reads.append(key)
        return self.inner.read_bytes(key)

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)


@pytest.fixture
def storage(tmp_path: Path) -> FolderStorage:
    return FolderStorage(tmp_path / "store", fsync=False)


def test_public_site_is_cacheable_by_anonymous_readers(
    storage: FolderStorage, tmp_path: Path
) -> None:
    publish(storage, tmp_path / "s1", site("first"))
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        assert client.get("/").headers["cache-control"] == PAGE_CACHE_CONTROL
        assert client.get("/static/contentIndex.json").headers["cache-control"] == (
            PAGE_CACHE_CONTROL
        )
        assert client.get("/index.css").headers["cache-control"] == ASSET_CACHE_CONTROL
        assert client.get("/evidence/src-0/img/p0001.png").headers["cache-control"] == (
            ASSET_CACHE_CONTROL
        )
        assert client.get("/missing").headers["cache-control"] == PAGE_CACHE_CONTROL
        page = client.get("/")
        cached = client.get("/", headers={"if-none-match": page.headers["etag"]})
        assert cached.status_code == 304
        assert cached.headers["cache-control"] == PAGE_CACHE_CONTROL
        weak = client.get("/", headers={"if-none-match": f'"other", W/{page.headers["etag"]}'})
        assert weak.status_code == 304
        # Signed-in callers (built-in authentication adds the principal) stay private.
        for header in ("x-ms-client-principal-id", "x-ms-client-principal", "authorization"):
            signed_in = client.get("/index.css", headers={header: "x"})
            assert signed_in.headers["cache-control"] == CACHE_CONTROL
        # APIs and probes are never stored.
        assert client.get("/healthz").headers["cache-control"] == "no-store"
        assert client.get("/livez").headers["cache-control"] == "no-store"


def test_non_public_or_forced_private_sites_stay_private(
    storage: FolderStorage, tmp_path: Path
) -> None:
    publish(storage, tmp_path / "s1", site("first"), audience="internal")
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        for path in ("/", "/index.css", "/missing"):
            assert client.get(path).headers["cache-control"] == CACHE_CONTROL
    forced = create_app(SiteSync(storage, tmp_path / "cache2"), poll_seconds=0, public_cache=True)
    with TestClient(forced) as client:
        assert client.get("/").headers["cache-control"] == PAGE_CACHE_CONTROL
        assert client.get("/", headers={"x-ms-client-principal-id": "x"}).headers[
            "cache-control"
        ] == (CACHE_CONTROL)

    public = FolderStorage(tmp_path / "public", fsync=False)
    publish(public, tmp_path / "s2", site("first"))
    off = create_app(SiteSync(public, tmp_path / "cache3"), poll_seconds=0, public_cache=False)
    with TestClient(off) as client:
        assert client.get("/").headers["cache-control"] == CACHE_CONTROL


def test_local_preview_folder_is_private_by_default(tmp_path: Path) -> None:
    root = tmp_path / "site"
    root.mkdir()
    (root / "index.html").write_bytes(BIG_PAGE)
    with TestClient(create_app(site_dir=root)) as client:
        home = client.get("/")
        assert home.headers["cache-control"] == CACHE_CONTROL
        assert "content-encoding" not in home.headers  # no precompressed copy


def test_sync_precompresses_large_text_files(storage: FolderStorage, tmp_path: Path) -> None:
    publish(storage, tmp_path / "s1", site("first"))
    sync = SiteSync(storage, tmp_path / "cache")
    sync.refresh()
    state = sync.state
    assert state is not None
    assert state.audience == "public"
    # Only text types of at least 1 KB that shrink are compressed (not tiny or binary files).
    assert state.compressed == {"big.html", "postscript.js"}
    assert gzip.decompress(gzip_path(state.root, "big.html").read_bytes()) == BIG_PAGE
    assert (state.root / GZIP_DIR).is_dir()

    # A restarted portal finds the copy and its compressed files again.
    again = SiteSync(storage, tmp_path / "cache")
    again.refresh()
    assert again.state is not None and again.state.compressed == state.compressed


def test_portal_serves_gzip_to_clients_that_accept_it(
    storage: FolderStorage, tmp_path: Path
) -> None:
    publish(storage, tmp_path / "s1", site("first"))
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        identity = client.get("/big", headers={"accept-encoding": "identity"})
        assert identity.status_code == 200
        assert "content-encoding" not in identity.headers
        assert identity.content == BIG_PAGE
        assert identity.headers["vary"] == "Accept-Encoding"

        packed = client.get("/big", headers={"accept-encoding": "gzip, br"})
        assert packed.headers["content-encoding"] == "gzip"
        assert packed.headers["content-type"] == "text/html; charset=utf-8"
        assert packed.headers["vary"] == "Accept-Encoding"
        assert packed.content == BIG_PAGE  # httpx decodes the body
        assert int(packed.headers["content-length"]) < len(BIG_PAGE)
        assert packed.headers["etag"] != identity.headers["etag"]
        assert packed.headers["etag"].endswith('-gz"')

        # Each representation revalidates against its own ETag.
        etag = packed.headers["etag"]
        not_modified = client.get(
            "/big", headers={"accept-encoding": "gzip", "if-none-match": etag}
        )
        assert not_modified.status_code == 304
        assert "content-encoding" not in not_modified.headers
        changed = client.get("/big", headers={"accept-encoding": "identity", "if-none-match": etag})
        assert changed.status_code == 200 and changed.content == BIG_PAGE

        refused = client.get("/big", headers={"accept-encoding": "gzip;q=0, *"})
        assert "content-encoding" not in refused.headers
        star = client.get("/postscript.js", headers={"accept-encoding": "*"})
        assert star.headers["content-encoding"] == "gzip"
        ranged = client.get("/big", headers={"accept-encoding": "gzip", "range": "bytes=0-9"})
        assert "content-encoding" not in ranged.headers

        small = client.get("/", headers={"accept-encoding": "gzip"})
        assert "content-encoding" not in small.headers and "vary" not in small.headers
        # The hidden folder of precompressed files is never served directly.
        hidden = client.get(f"/{GZIP_DIR}/big.html.gz")
        assert hidden.status_code == 404 and b"Page not found" in hidden.content


def test_api_routes_are_not_compressed(storage: FolderStorage, tmp_path: Path) -> None:
    publish(storage, tmp_path / "s1", site("first"))
    app = create_app(SiteSync(storage, tmp_path / "cache"), poll_seconds=0)
    with TestClient(app) as client:
        health = client.get("/healthz", headers={"accept-encoding": "gzip"})
        assert "content-encoding" not in health.headers


def test_new_release_downloads_only_changed_files(storage: FolderStorage, tmp_path: Path) -> None:
    publish(storage, tmp_path / "s1", site("first"))
    counting = CountingStorage(storage)
    sync = SiteSync(counting, tmp_path / "cache")  # type: ignore[arg-type]
    sync.refresh()
    first = sync.state
    assert first is not None
    first_reads = [key for key in counting.reads if "/site/" in key]
    assert len(first_reads) == len(site("first"))

    changed = {**site("second"), "site/big.html": BIG_PAGE + b"<p>more</p>"}
    second = publish(storage, tmp_path / "s2", changed, day=1)
    counting.reads.clear()
    assert sync.refresh() is True
    state = sync.state
    assert state is not None and state.release_id == second.release_id
    downloaded = sorted(key.split("/site/", 1)[1] for key in counting.reads if "/site/" in key)
    assert downloaded == ["big.html", "index.html"]
    for path, data in changed.items():
        rel = path.removeprefix("site/")
        assert state.root.joinpath(*rel.split("/")).read_bytes() == data
    assert (
        gzip.decompress(gzip_path(state.root, "big.html").read_bytes()) == changed["site/big.html"]
    )
    assert gzip.decompress(gzip_path(state.root, "postscript.js").read_bytes()) == BIG_SCRIPT
    assert first.root.is_dir()  # the previous copy is untouched and still served meanwhile
    assert (first.root / "big.html").read_bytes() == BIG_PAGE


def test_delta_sync_downloads_a_locally_corrupted_file_again(
    storage: FolderStorage, tmp_path: Path
) -> None:
    publish(storage, tmp_path / "s1", site("first"))
    counting = CountingStorage(storage)
    sync = SiteSync(counting, tmp_path / "cache")  # type: ignore[arg-type]
    sync.refresh()
    first = sync.state
    assert first is not None
    (first.root / "index.css").write_bytes(b"tampered")
    gzip_path(first.root, "postscript.js").write_bytes(b"not gzip")

    publish(storage, tmp_path / "s2", site("second"), day=1)
    counting.reads.clear()
    sync.refresh()
    state = sync.state
    assert state is not None
    downloaded = sorted(key.split("/site/", 1)[1] for key in counting.reads if "/site/" in key)
    assert downloaded == ["index.css", "index.html"]
    assert (state.root / "index.css").read_bytes() == b"body{}"
    assert gzip.decompress(gzip_path(state.root, "postscript.js").read_bytes()) == BIG_SCRIPT


def test_delta_sync_still_verifies_downloads(storage: FolderStorage, tmp_path: Path) -> None:
    publish(storage, tmp_path / "s1", site("first"))
    sync = SiteSync(storage, tmp_path / "cache")
    sync.refresh()
    first = sync.state
    second = publish(storage, tmp_path / "s2", site("second"), day=1)
    storage.write_bytes(f"releases/{second.release_id}/site/index.html", b"<script>evil</script>")
    with pytest.raises(ReleaseIntegrityError, match=r"site/index\.html"):
        sync.refresh()
    assert sync.state == first  # the previous site keeps being served
    assert not any((tmp_path / "cache").glob("*.partial-*"))
