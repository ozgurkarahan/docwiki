import json
import threading
from pathlib import Path

import pytest

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.storage import (
    FolderStorage,
    KeyNotFoundError,
    LeaseLostError,
    PreconditionFailedError,
    Storage,
    read_json,
    validate_key,
    write_json,
)


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_folder_storage_basic_operations(tmp_path: Path) -> None:
    storage = FolderStorage(tmp_path / "store")
    assert isinstance(storage, Storage)
    etag = storage.write_bytes("work/state/sources/a.json", b"one")
    assert etag == sha256_hex(b"one") == storage.etag("work/state/sources/a.json")
    assert storage.read_bytes("work/state/sources/a.json") == b"one"
    assert storage.read_with_etag("work/state/sources/a.json") == (b"one", etag)
    assert storage.exists("work/state/sources/a.json")
    assert not storage.exists("work/state/sources/b.json")
    assert storage.etag("missing/key") is None
    storage.write_bytes("raw/Procédures/SOP rev B.docx", b"doc")
    storage.write_bytes("releases/current.json", b"{}")
    assert storage.list() == [
        "raw/Procédures/SOP rev B.docx",
        "releases/current.json",
        "work/state/sources/a.json",
    ]
    assert storage.list("work/") == ["work/state/sources/a.json"]
    assert storage.list("re") == ["releases/current.json"]
    with pytest.raises(KeyNotFoundError):
        storage.read_bytes("work/state/sources/b.json")
    assert storage.delete("work/state/sources/a.json") is True
    assert storage.delete("work/state/sources/a.json") is False
    assert not (tmp_path / "store" / "work").exists()


def test_conditional_writes_and_deletes(tmp_path: Path) -> None:
    storage = FolderStorage(tmp_path)
    first = storage.write_bytes("releases/current.json", b"v1", if_none_match="*")
    with pytest.raises(PreconditionFailedError):
        storage.write_bytes("releases/current.json", b"v2", if_none_match="*")
    second = storage.write_bytes("releases/current.json", b"v2", if_match=first)
    with pytest.raises(PreconditionFailedError):
        storage.write_bytes("releases/current.json", b"v3", if_match=first)
    with pytest.raises(PreconditionFailedError):
        storage.delete("releases/current.json", if_match=first)
    assert storage.delete("releases/current.json", if_match=second)
    with pytest.raises(PreconditionFailedError):
        storage.write_bytes("releases/current.json", b"v4", if_match=second)


@pytest.mark.parametrize(
    "key", ["", "/abs", "a/", "a//b", "a/../b", "a\\b", "./a", ".docwiki-storage/x", "a\x00b"]
)
def test_invalid_keys(tmp_path: Path, key: str) -> None:
    with pytest.raises(ValueError):
        validate_key(key)
    with pytest.raises(ValueError):
        FolderStorage(tmp_path).write_bytes(key, b"x")


def test_internal_files_are_never_listed(tmp_path: Path) -> None:
    storage = FolderStorage(tmp_path)
    storage.write_bytes("a.json", b"1", if_none_match="*")
    storage.acquire_lease("work/state/lease", 60)
    assert storage.list() == ["a.json", "work/state/lease"]


def test_lease_lifecycle_with_expiry(tmp_path: Path) -> None:
    clock = FakeClock()
    storage = FolderStorage(tmp_path, clock=clock)
    lease = storage.acquire_lease("work/state/lease", 60, owner="job-1")
    assert lease is not None and storage.exists("work/state/lease")
    assert storage.acquire_lease("work/state/lease", 60) is None
    clock.now += 30
    renewed = storage.renew_lease(lease)
    assert renewed.expires_at == clock.now + 60
    clock.now += 59
    assert storage.acquire_lease("work/state/lease", 60) is None
    clock.now += 2
    other = storage.acquire_lease("work/state/lease", 60, owner="job-2")
    assert other is not None and other.lease_id != lease.lease_id
    with pytest.raises(LeaseLostError):
        storage.renew_lease(lease)
    with pytest.raises(LeaseLostError):
        storage.release_lease(lease)
    storage.release_lease(other)
    storage.release_lease(other)
    third = storage.acquire_lease("work/state/lease", 15)
    assert third is not None


def test_expired_lease_can_still_be_renewed_when_not_taken(tmp_path: Path) -> None:
    clock = FakeClock()
    storage = FolderStorage(tmp_path, clock=clock)
    lease = storage.acquire_lease("work/state/lease", 10)
    assert lease is not None
    clock.now += 100
    assert storage.renew_lease(lease, 20).expires_at == clock.now + 20


def test_optimistic_concurrency_counter(tmp_path: Path) -> None:
    storage = FolderStorage(tmp_path)
    write_json(storage, "work/counter.json", {"n": 0})
    errors: list[BaseException] = []

    def worker() -> None:
        try:
            for _ in range(20):
                while True:
                    data, etag = storage.read_with_etag("work/counter.json")
                    value = json.loads(data)["n"] + 1
                    try:
                        write_json(storage, "work/counter.json", {"n": value}, if_match=etag)
                        break
                    except PreconditionFailedError:
                        continue
        except BaseException as exc:  # pragma: no cover - surfaced below
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert not errors
    assert read_json(storage, "work/counter.json") == {"n": 80}
