"""Parallel uploads of :func:`docwiki.release.upload_release` keep the publish guarantees."""

from __future__ import annotations

import threading
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import pytest

from docwiki.contracts.gates import gate_results
from docwiki.contracts.runs import VersionInfo
from docwiki.contracts.storage import FolderStorage
from docwiki.release import (
    ReleaseWriter,
    publish_release,
    read_current_pointer,
    upload_release,
)
from docwiki.release.publish import read_manifest
from docwiki.release.writer import StagedRelease

CREATED_AT = datetime(2026, 3, 1, 9, 0, tzinfo=UTC)
VERSIONS = VersionInfo(docwiki="0.1.0", domain_pack="publish-test", domain_pack_hash="test")


def stage(root: Path, *, day: int = 0, files: int = 24) -> StagedRelease:
    writer = ReleaseWriter(
        root, created_at=CREATED_AT + timedelta(days=day), audience="public", versions=VERSIONS
    )
    writer.write_text("wiki/index.md", f"# wiki {day}\n")
    for n in range(files):
        writer.write_bytes(f"site/page-{n:02d}.html", f"<p>{day}-{n}</p>".encode())
    return writer.finalize(gates=gate_results([]))


class SlowStorage:
    """Folder storage whose writes take a while, recording their peak concurrency."""

    def __init__(self, inner: FolderStorage, *, fail_on: str | None = None) -> None:
        self.inner = inner
        self.fail_on = fail_on
        self.active = 0
        self.peak = 0
        self.writes: list[str] = []
        self._lock = threading.Lock()

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        if_match: str | None = None,
        if_none_match: Literal["*"] | None = None,
    ) -> str:
        with self._lock:
            self.active += 1
            self.peak = max(self.peak, self.active)
            self.writes.append(key)
        try:
            time.sleep(0.01)
            if self.fail_on and key.endswith(self.fail_on):
                raise OSError(f"upload of {key} failed")
            return self.inner.write_bytes(key, data, if_match=if_match, if_none_match=if_none_match)
        finally:
            with self._lock:
                self.active -= 1

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)


def test_uploads_run_in_parallel_and_the_manifest_comes_last(tmp_path: Path) -> None:
    storage = SlowStorage(FolderStorage(tmp_path / "store", fsync=False))
    staged = stage(tmp_path / "s1")
    upload_release(storage, staged, workers=4)  # type: ignore[arg-type]
    assert 1 < storage.peak <= 4
    assert storage.writes[-1].endswith("/manifest.json")
    manifest, manifest_sha = read_manifest(storage.inner, staged.release_id)
    assert manifest_sha == staged.manifest_sha256
    for rel_path in manifest.files:
        key = f"releases/{staged.release_id}/{rel_path}"
        assert storage.inner.read_bytes(key) == (staged.root / rel_path).read_bytes()


def test_one_worker_uploads_serially(tmp_path: Path) -> None:
    storage = SlowStorage(FolderStorage(tmp_path / "store", fsync=False))
    publish_release(storage, stage(tmp_path / "s1"), workers=1)  # type: ignore[arg-type]
    assert storage.peak == 1


def test_a_failed_upload_never_swaps_the_pointer(tmp_path: Path) -> None:
    inner = FolderStorage(tmp_path / "store", fsync=False)
    first = publish_release(inner, stage(tmp_path / "s1"))
    storage = SlowStorage(inner, fail_on="site/page-05.html")
    second = stage(tmp_path / "s2", day=1)
    with pytest.raises(OSError, match="page-05"):
        publish_release(storage, second, workers=4)  # type: ignore[arg-type]
    assert storage.active == 0  # every running upload finished before the error surfaced
    assert not inner.exists(f"releases/{second.release_id}/manifest.json")
    current = read_current_pointer(inner)
    assert current is not None and current[0].release_id == first.release_id
