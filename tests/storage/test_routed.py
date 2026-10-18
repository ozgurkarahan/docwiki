"""DirectorySource (read-only input folder) and RoutedStorage."""

from __future__ import annotations

from pathlib import Path

import pytest

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.storage import FolderStorage, KeyNotFoundError, StorageError
from docwiki.storage.routed import DirectorySource, RoutedStorage, local_path_for


@pytest.fixture
def inputs(tmp_path: Path) -> Path:
    root = tmp_path / "input"
    (root / "procedures").mkdir(parents=True)
    (root / "procedures" / "SOP-GBX-010 rev A.txt").write_text(
        "rev A\n", encoding="utf-8", newline="\n"
    )
    (root / "plan.csv").write_text("a,b\n1,2\n", encoding="utf-8", newline="\n")
    (root / ".hidden").mkdir()
    (root / ".hidden" / "secret.txt").write_text("no", encoding="utf-8", newline="\n")
    (root / ".DS_Store").write_text("no", encoding="utf-8", newline="\n")
    return root


def test_directory_source_lists_and_reads_in_place(inputs: Path):
    source = DirectorySource(inputs)
    assert source.list("raw/") == ["raw/plan.csv", "raw/procedures/SOP-GBX-010 rev A.txt"]
    data, etag = source.read_with_etag("raw/plan.csv")
    assert data == b"a,b\n1,2\n" and etag == sha256_hex(data)
    assert source.etag("raw/plan.csv") == etag
    assert source.exists("raw/procedures/SOP-GBX-010 rev A.txt")
    assert not source.exists("raw/.hidden/secret.txt")
    assert source.etag("raw/none.txt") is None
    with pytest.raises(KeyNotFoundError):
        source.read_bytes("raw/none.txt")
    assert source.local_path("raw/plan.csv") == inputs / "plan.csv"
    with pytest.raises(ValueError):
        source.local_path("work/plan.csv")


def test_directory_source_is_read_only(inputs: Path):
    source = DirectorySource(inputs)
    with pytest.raises(StorageError):
        source.write_bytes("raw/new.txt", b"x")
    with pytest.raises(StorageError):
        source.delete("raw/plan.csv")
    with pytest.raises(StorageError):
        source.acquire_lease("raw/plan.csv", 30)
    assert (inputs / "plan.csv").is_file()
    with pytest.raises(FileNotFoundError):
        DirectorySource(inputs / "missing")


def test_routed_storage_sends_raw_to_the_input_folder(inputs: Path, tmp_path: Path):
    base = FolderStorage(tmp_path / "work", fsync=False)
    base.write_bytes("raw/stale.txt", b"not listed: raw is routed")
    storage = RoutedStorage(base, {"raw": DirectorySource(inputs)})
    storage.write_bytes("work/state/x.json", b"{}")
    assert storage.list("raw/") == ["raw/plan.csv", "raw/procedures/SOP-GBX-010 rev A.txt"]
    assert storage.list("") == [
        "raw/plan.csv",
        "raw/procedures/SOP-GBX-010 rev A.txt",
        "work/state/x.json",
    ]
    assert storage.read_bytes("work/state/x.json") == b"{}"
    lease = storage.acquire_lease("work/state/lease", 30)
    assert lease is not None
    storage.renew_lease(lease)
    storage.release_lease(lease)
    assert local_path_for(storage, "raw/plan.csv") == inputs / "plan.csv"
    assert (
        local_path_for(storage, "work/state/x.json")
        == tmp_path / "work" / "work" / "state" / "x.json"
    )
    with pytest.raises(StorageError):
        storage.write_bytes("raw/new.txt", b"x")
