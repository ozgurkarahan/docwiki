"""Release sources: atomic pointer swap, TTL, integrity, Blob cache and the Blob adapter."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from azure.core import MatchConditions
from azure.core.exceptions import (
    ResourceExistsError,
    ResourceModifiedError,
    ResourceNotFoundError,
)
from mcp_testkit import (
    FIXTURE_ROOT,
    MINUTES,
    NOW,
    PLAN_B,
    RELEASE_ID,
    TOPIC_ID,
    copy_fixture,
    stage_release,
)

from docwiki.contracts.storage import FolderStorage, KeyNotFoundError, PreconditionFailedError
from docwiki.mcp.blob import AzureBlobStorage
from docwiki.mcp.config import McpConfig
from docwiki.mcp.source import FolderReleaseSource, ReleaseUnavailableError, StorageReleaseSource
from docwiki.mcp.tools_read import ReadTools
from docwiki.release import publish_release


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def _files(root: Path) -> dict[str, tuple[int, int]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_folder_source_swaps_atomically_when_the_pointer_moves(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path / "mock")
    pointer_file = root / "releases" / "current.json"
    original_pointer = pointer_file.read_bytes()
    clock = FakeClock()
    source = FolderReleaseSource(root, ttl_s=30, clock=clock)
    reads = ReadTools(source, McpConfig())
    first = source.current()
    assert first.release_id == RELEASE_ID
    before = _files(root / "releases" / RELEASE_ID)
    reads.search("menuiseries")
    reads.query_table(PLAN_B, "SELECT row_id FROM t01")
    assert _files(root / "releases" / RELEASE_ID) == before, "the server never writes releases"

    staged = stage_release(tmp_path / "s2", created_at=NOW, topic_note="Second release note.")
    publish_release(FolderStorage(root, fsync=False), staged)
    assert source.current() is first, "the pointer is re-checked at most every ttl_s"
    clock.advance(31)
    second = source.current()
    assert second.release_id == staged.release_id
    assert "Second release note." in json.loads(reads.read_page(TOPIC_ID))["markdown"]
    clock.advance(31)
    assert source.current() is second, "an unchanged pointer does not reload"

    pointer_file.write_text('{"release_id": "broken"}', encoding="utf-8")
    clock.advance(31)
    assert source.current() is second, "a failing reload keeps the working release"
    assert source.last_error

    pointer_file.write_bytes(original_pointer)
    clock.advance(31)
    assert source.current().release_id == RELEASE_ID
    assert source.last_error is None
    assert source.release_ids() == sorted([RELEASE_ID, staged.release_id])
    assert source.manifest_for(staged.release_id).release_id == staged.release_id
    with pytest.raises(KeyError):
        source.manifest_for("20990101T000000Z-00000000")


def test_folder_source_refuses_a_manifest_that_does_not_match_the_pointer(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path / "mock")
    pointer_file = root / "releases" / "current.json"
    pointer = json.loads(pointer_file.read_text(encoding="utf-8"))
    pointer["manifest_sha256"] = "0" * 64
    pointer_file.write_text(json.dumps(pointer), encoding="utf-8")
    with pytest.raises(ReleaseUnavailableError, match="does not match"):
        FolderReleaseSource(root).current()
    with pytest.raises(ReleaseUnavailableError, match="no release found"):
        FolderReleaseSource(tmp_path / "nowhere").current()


def test_direct_release_folder_is_served(tmp_path: Path) -> None:
    source = FolderReleaseSource(FIXTURE_ROOT / "releases" / RELEASE_ID)
    assert source.current().release_id == RELEASE_ID
    assert source.describe() == {"source": "folder", "release_id": RELEASE_ID, "audience": "public"}


def test_search_index_is_verified_and_served_from_memory(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path / "mock")
    search_db = root / "releases" / RELEASE_ID / "search.db"
    moved = search_db.with_name("search.moved")
    source = FolderReleaseSource(root)
    reads = ReadTools(source, McpConfig())
    snapshot = source.current()
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        snapshot.search._conn.execute("DELETE FROM meta")
    search_db.rename(moved)  # refused on Windows while a handle is open
    assert json.loads(reads.search("menuiseries"))["hits"]
    moved.rename(search_db)

    tampered = bytearray(search_db.read_bytes())
    tampered[-1] ^= 0xFF
    search_db.write_bytes(bytes(tampered))
    with pytest.raises(ReleaseUnavailableError, match=r"search\.db"):
        FolderReleaseSource(root).current()


def test_concurrent_reads_during_a_swap(tmp_path: Path) -> None:
    root = copy_fixture(tmp_path / "mock")
    source = FolderReleaseSource(root, ttl_s=0)
    reads = ReadTools(source, McpConfig())
    staged = stage_release(tmp_path / "s2", created_at=NOW)
    seen: set[str] = set()
    errors: list[BaseException] = []

    def worker() -> None:
        for _ in range(25):
            try:
                seen.add(json.loads(reads.search("livraison menuiseries"))["release_id"])
            except BaseException as exc:
                errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for thread in threads:
        thread.start()
    publish_release(FolderStorage(root, fsync=False), staged)
    for thread in threads:
        thread.join()
    assert not errors
    assert seen <= {RELEASE_ID, staged.release_id}
    assert source.current().release_id == staged.release_id


def test_storage_source_materializes_verifies_swaps_and_prunes(tmp_path: Path) -> None:
    remote = FolderStorage(tmp_path / "remote", fsync=False)
    staged = [
        stage_release(tmp_path / f"s{day}", created_at=NOW + timedelta(days=day))
        for day in range(3)
    ]
    cache = tmp_path / "cache"
    clock = FakeClock()
    source = StorageReleaseSource(remote, cache, ttl_s=30, clock=clock)
    with pytest.raises(ReleaseUnavailableError, match="no release has been published"):
        source.current()

    publish_release(remote, staged[0])
    first = source.current()
    assert first.release_id == staged[0].release_id
    assert (cache / first.release_id / "manifest.json").is_file()
    assert not list(cache.glob(".staging-*"))
    assert json.loads(ReadTools(source, McpConfig()).search("menuiseries"))["hits"]

    publish_release(remote, staged[1])
    clock.advance(31)
    assert source.current().release_id == staged[1].release_id

    publish_release(remote, staged[2])
    key = f"releases/{staged[2].release_id}/wiki/index.md"
    remote.write_bytes(key, b"tampered")
    clock.advance(31)
    assert source.current().release_id == staged[1].release_id, "tampered release refused"
    assert "does not match the manifest" in (source.last_error or "")
    remote.write_bytes(key, (staged[2].root / "wiki" / "index.md").read_bytes())
    clock.advance(31)
    assert source.current().release_id == staged[2].release_id
    cached = sorted(path.name for path in cache.iterdir())
    assert cached == [staged[1].release_id, staged[2].release_id], "older caches are pruned"
    assert source.release_ids() == [s.release_id for s in staged]
    assert source.manifest_for(staged[0].release_id).release_id == staged[0].release_id


class _Props:
    def __init__(self, etag: str) -> None:
        self.etag = etag


class _Downloader:
    def __init__(self, data: bytes, etag: str) -> None:
        self._data = data
        self.properties = _Props(etag)

    def readall(self) -> bytes:
        return self._data


class FakeContainer:
    """In-memory stand-in for an Azure ``ContainerClient`` (only what the adapter uses)."""

    def __init__(self) -> None:
        self.blobs: dict[str, tuple[bytes, str]] = {}
        self.version = 0

    def get_blob_client(self, name: str) -> FakeBlob:
        return FakeBlob(self, name)

    def list_blob_names(self, name_starts_with: str | None = None) -> list[str]:
        return sorted(name for name in self.blobs if name.startswith(name_starts_with or ""))


class FakeBlob:
    def __init__(self, container: FakeContainer, name: str) -> None:
        self.container = container
        self.name = name

    def _current(self) -> tuple[bytes, str]:
        if self.name not in self.container.blobs:
            raise ResourceNotFoundError("missing")
        return self.container.blobs[self.name]

    def download_blob(self) -> _Downloader:
        return _Downloader(*self._current())

    def get_blob_properties(self) -> _Props:
        return _Props(self._current()[1])

    def upload_blob(self, data: bytes, **kwargs: Any) -> dict[str, Any]:
        exists = self.name in self.container.blobs
        if not kwargs.get("overwrite", False) and exists:
            raise ResourceExistsError("exists")
        if kwargs.get("match_condition") == MatchConditions.IfNotModified:
            if not exists:
                raise ResourceNotFoundError("missing")
            if self.container.blobs[self.name][1] != kwargs["etag"]:
                raise ResourceModifiedError("modified")
        self.container.version += 1
        etag = f'"0x{self.container.version:04X}"'
        self.container.blobs[self.name] = (bytes(data), etag)
        return {"etag": etag}

    def delete_blob(self, **kwargs: Any) -> None:
        _, etag = self._current()
        if (
            kwargs.get("match_condition") == MatchConditions.IfNotModified
            and etag != kwargs["etag"]
        ):
            raise ResourceModifiedError("modified")
        del self.container.blobs[self.name]


class FakeService:
    def __init__(self) -> None:
        self.containers: dict[str, FakeContainer] = {}

    def get_container_client(self, name: str) -> FakeContainer:
        return self.containers.setdefault(name, FakeContainer())


def test_blob_adapter_semantics() -> None:
    service = FakeService()
    blob = AzureBlobStorage(service_client=service, containers={"releases": "published"})
    etag = blob.write_bytes("work/state/sources/x.json", b"one")
    assert blob.read_with_etag("work/state/sources/x.json") == (b"one", etag)
    assert blob.etag("work/state/sources/x.json") == etag and blob.exists(
        "work/state/sources/x.json"
    )
    with pytest.raises(PreconditionFailedError):
        blob.write_bytes("work/state/sources/x.json", b"two", if_match='"stale"')
    with pytest.raises(PreconditionFailedError):
        blob.write_bytes("work/state/sources/x.json", b"two", if_none_match="*")
    new_etag = blob.write_bytes("work/state/sources/x.json", b"two", if_match=etag)
    assert new_etag != etag
    with pytest.raises(KeyNotFoundError):
        blob.read_bytes("work/missing.json")
    assert blob.etag("work/missing.json") is None
    blob.write_bytes("releases/current.json", b"{}")
    assert "current.json" in service.containers["published"].blobs
    assert blob.list("work/") == ["work/state/sources/x.json"]
    assert blob.list("") == ["releases/current.json", "work/state/sources/x.json"]
    assert blob.list("releases/cur") == ["releases/current.json"]
    assert blob.delete("work/state/sources/x.json") is True
    assert blob.delete("work/state/sources/x.json") is False
    with pytest.raises(ValueError):
        blob.read_bytes("elsewhere/x")
    with pytest.raises(NotImplementedError):
        blob.acquire_lease("work/state/lease", 30)


def test_blob_adapter_serves_a_published_release(tmp_path: Path) -> None:
    blob = AzureBlobStorage(service_client=FakeService())
    staged = stage_release(tmp_path / "s", created_at=NOW)
    publish_release(blob, staged)
    source = StorageReleaseSource(blob, tmp_path / "cache")
    assert source.current().release_id == staged.release_id
    data = json.loads(ReadTools(source, McpConfig()).get_evidence(MINUTES, "para-0011"))
    assert data["provenance"] == "native-text"
