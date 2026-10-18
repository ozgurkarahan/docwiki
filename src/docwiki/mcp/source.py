"""Release sources: the one release the server answers from, reloaded when the pointer moves.

* :class:`FolderReleaseSource` reads a release in place: a portable wiki folder
  (``.docwiki/manifest.json``, CONTRACT.md section 19), a release directory, a ``releases/``
  folder with ``current.json``, or a folder containing ``releases/current.json``.
* :class:`StorageReleaseSource` reads ``releases/current.json`` through a
  :class:`~docwiki.contracts.storage.Storage` (Azure Blob in production) and materialises the
  release into a local cache directory with verified hashes.

Both re-check the pointer at most every ``ttl_s`` seconds and swap the served
:class:`Snapshot` atomically: a reload happens in one request thread while the others keep using
the current snapshot, and a release that fails to load never replaces a working one. Sources never
write to ``releases/``. ``search.db`` is checked against the manifest and loaded into memory, so
no release file stays open: a portable folder can be re-exported in place and old caches can be
deleted while the server runs (also on Windows).
"""

from __future__ import annotations

import logging
import os
import shutil
import sqlite3
import threading
import time
import uuid
from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.ids import RELEASE_ID_RE
from docwiki.contracts.layout import ReleaseFiles, StorageKeys
from docwiki.contracts.manifest import ReleaseManifest
from docwiki.contracts.storage import KeyNotFoundError, Storage
from docwiki.release import ReleaseIntegrityError, ReleaseLayout, ReleaseReader
from docwiki.release.layout import POINTER_FILE
from docwiki.release.publish import (
    list_release_ids,
    materialize_release,
    read_current_pointer,
    read_manifest,
)

__all__ = [
    "FolderReleaseSource",
    "ReleaseSource",
    "ReleaseUnavailableError",
    "Snapshot",
    "StorageReleaseSource",
    "open_search_in_memory",
]

logger = logging.getLogger("docwiki.mcp.source")


class ReleaseUnavailableError(RuntimeError):
    """No release can be served (none published yet, unreadable or failing integrity checks)."""


def open_search_in_memory(reader: ReleaseReader) -> Any:
    """The release's ``search.db`` as an in-memory :class:`~docwiki.search.index.SearchIndex`.

    The bytes are checked against the manifest first. Keeping no file handle open lets a
    portable folder be re-exported in place and old release caches be deleted while the server
    keeps answering (Windows refuses to replace open files). Falls back to opening the file when
    this SQLite build cannot deserialize.
    """
    from docwiki.search.index import SearchIndex, fts5_available

    data = reader.search_db_path.read_bytes()
    entry = reader.manifest.files.get(ReleaseFiles.SEARCH_DB)
    if entry is not None and (len(data) != entry.size or sha256_hex(data) != entry.sha256):
        raise ReleaseIntegrityError(f"{ReleaseFiles.SEARCH_DB} does not match the manifest")
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    try:
        conn.deserialize(data)
    except (AttributeError, sqlite3.Error):  # pragma: no cover - SQLite without deserialize
        conn.close()
        return reader.open_search()
    conn.execute("PRAGMA query_only = ON")
    has_fts = conn.execute(
        "SELECT count(*) FROM sqlite_master WHERE type = 'table' AND name = 'docs_fts'"
    ).fetchone()[0]
    backend: Literal["fts5", "bm25"] = "bm25"
    if has_fts and fts5_available():
        try:
            conn.execute("SELECT rowid FROM docs_fts LIMIT 1").fetchall()
            backend = "fts5"
        except sqlite3.OperationalError:
            backend = "bm25"
    return SearchIndex(conn, backend=backend)


class Snapshot:
    """One opened, immutable release with its search index and per-release caches."""

    def __init__(self, reader: ReleaseReader) -> None:
        self.reader = reader
        self.release_id = reader.release_id
        self.audience = reader.audience
        self.manifest_sha256 = reader.manifest_sha256
        self.catalog = reader.catalog
        self.search = open_search_in_memory(reader)
        self.loaded_at = time.time()
        self._lock = threading.Lock()
        self._cache: dict[str, Any] = {}

    def cached[T](self, key: str, factory: Callable[[], T]) -> T:
        """Value computed once per release (thread-safe; the release never changes)."""
        with self._lock:
            if key in self._cache:
                return self._cache[key]  # type: ignore[no-any-return,unused-ignore]
        value = factory()
        with self._lock:
            return self._cache.setdefault(key, value)  # type: ignore[no-any-return,unused-ignore]

    def close(self) -> None:
        try:
            self.search.close()
        except Exception:  # pragma: no cover - closing a read-only connection
            logger.debug("search index of %s already closed", self.release_id)


class ReleaseSource(ABC):
    """Serves the current :class:`Snapshot`, reloading at most every ``ttl_s`` seconds."""

    kind = "abstract"

    def __init__(self, *, ttl_s: float = 30.0, clock: Callable[[], float] = time.monotonic) -> None:
        self.ttl_s = ttl_s
        self._clock = clock
        self._refresh_lock = threading.Lock()
        self._snapshot: Snapshot | None = None
        self._previous: Snapshot | None = None
        self._version: str | None = None
        self._checked_at = float("-inf")
        self.last_error: str | None = None

    @abstractmethod
    def _probe(self) -> str:
        """Cheap version of the current pointer (ETag or content hash)."""

    @abstractmethod
    def _load(self) -> Snapshot:
        """Open the release the pointer designates."""

    @abstractmethod
    def manifest_for(self, release_id: str) -> ReleaseManifest:
        """Manifest of any release present at the source (``KeyError`` when unknown)."""

    @abstractmethod
    def release_ids(self) -> list[str]:
        """Release ids present at the source, oldest first."""

    def current(self) -> Snapshot:
        """The release to answer from; reloads when the pointer changed (thread-safe)."""
        snapshot = self._snapshot
        if snapshot is not None and self._clock() - self._checked_at < self.ttl_s:
            return snapshot
        if snapshot is None:
            self._refresh_lock.acquire()
        elif not self._refresh_lock.acquire(blocking=False):
            return snapshot
        try:
            snapshot = self._snapshot
            if snapshot is not None and self._clock() - self._checked_at < self.ttl_s:
                return snapshot
            try:
                version = self._probe()
                if snapshot is None or version != self._version:
                    fresh = self._load()
                    self._swap(fresh, version)
                self.last_error = None
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                if snapshot is None:
                    raise ReleaseUnavailableError(str(exc)) from exc
                logger.warning(
                    "keeping release %s, reload failed: %s", snapshot.release_id, self.last_error
                )
            finally:
                self._checked_at = self._clock()
            assert self._snapshot is not None
            return self._snapshot
        finally:
            self._refresh_lock.release()

    def _swap(self, fresh: Snapshot, version: str) -> None:
        evicted = self._previous
        old = self._snapshot
        self._previous, self._snapshot, self._version = old, fresh, version
        if evicted is not None and evicted is not fresh and evicted is not old:
            evicted.close()
        if old is None:
            logger.info("serving release %s (%s)", fresh.release_id, fresh.audience)
        elif old.release_id != fresh.release_id:
            logger.info("swapped release %s -> %s", old.release_id, fresh.release_id)
        self._after_swap()

    def _after_swap(self) -> None:  # noqa: B027 - optional hook, a no-op by default
        """Hook run after every swap (cache housekeeping)."""

    def invalidate(self) -> None:
        """Force a pointer check on the next :meth:`current` call."""
        self._checked_at = float("-inf")

    def describe(self) -> dict[str, Any]:
        snapshot = self._snapshot
        return {
            "source": self.kind,
            "release_id": snapshot.release_id if snapshot else None,
            "audience": snapshot.audience if snapshot else None,
        }


@dataclass(frozen=True)
class _FolderShape:
    """How a ``--release`` folder is organised."""

    kind: Literal["portable", "release", "pointer"]
    version_file: Path
    """File whose content identifies the served release (a manifest or a pointer)."""
    releases_root: Path | None
    """Folder of sibling releases (``None`` for a portable folder: it holds one release)."""


class FolderReleaseSource(ReleaseSource):
    """Release read in place from a local folder (``--release PATH``)."""

    kind = "folder"

    def __init__(
        self,
        path: str | Path,
        *,
        ttl_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(ttl_s=ttl_s, clock=clock)
        self.path = Path(path)

    def _shape(self) -> _FolderShape:
        layout = ReleaseLayout.detect(self.path)
        if layout is not None and layout.portable:
            return _FolderShape("portable", layout.manifest_path, None)
        if layout is not None:
            return _FolderShape("release", layout.manifest_path, self.path.parent)
        for releases in (self.path, self.path / StorageKeys.RELEASES):
            pointer = releases / POINTER_FILE
            if pointer.is_file():
                return _FolderShape("pointer", pointer, releases)
        raise ReleaseUnavailableError(
            "no release found at the configured location (expected a portable wiki folder with "
            ".docwiki/manifest.json, a release folder with manifest.json, or current.json in it "
            "or in its releases/ folder)"
        )

    def _probe(self) -> str:
        shape = self._shape()
        return f"{shape.kind}:{sha256_hex(shape.version_file.read_bytes())}"

    def _load(self) -> Snapshot:
        reader = ReleaseReader.open(self.path)
        if reader.pointer is not None and reader.manifest_sha256 != reader.pointer.manifest_sha256:
            raise ReleaseIntegrityError(
                f"manifest of {reader.release_id} does not match current.json"
            )
        return Snapshot(reader)

    def manifest_for(self, release_id: str) -> ReleaseManifest:
        if not RELEASE_ID_RE.match(release_id):
            raise KeyError(f"invalid release id: {release_id!r}")
        shape = self._shape()
        if shape.releases_root is None:
            manifest = ReleaseManifest.from_json(shape.version_file.read_bytes())
            if manifest.release_id != release_id:
                raise KeyError(f"unknown release: {release_id}")
            return manifest
        file = shape.releases_root / release_id / ReleaseFiles.MANIFEST
        if not file.is_file():
            raise KeyError(f"unknown release: {release_id}")
        return ReleaseManifest.from_json(file.read_bytes())

    def release_ids(self) -> list[str]:
        shape = self._shape()
        if shape.releases_root is None:
            return [ReleaseManifest.from_json(shape.version_file.read_bytes()).release_id]
        return sorted(
            child.name
            for child in shape.releases_root.iterdir()
            if child.is_dir()
            and RELEASE_ID_RE.match(child.name)
            and (child / ReleaseFiles.MANIFEST).is_file()
        )


class StorageReleaseSource(ReleaseSource):
    """Release published through a :class:`Storage`, materialised into ``cache_dir``."""

    kind = "storage"

    def __init__(
        self,
        storage: Storage,
        cache_dir: str | Path,
        *,
        prefix: str = StorageKeys.RELEASES,
        ttl_s: float = 30.0,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        super().__init__(ttl_s=ttl_s, clock=clock)
        self.storage = storage
        self.cache_dir = Path(cache_dir)
        self.prefix = prefix.rstrip("/")

    def _probe(self) -> str:
        etag = self.storage.etag(f"{self.prefix}/current.json")
        if etag is None:
            raise ReleaseUnavailableError("no release has been published yet (no current.json)")
        return etag

    def _materialize(self, release_id: str, manifest_sha256: str) -> Path:
        target = self.cache_dir / release_id
        manifest = target / ReleaseFiles.MANIFEST
        if manifest.is_file() and sha256_hex(manifest.read_bytes()) == manifest_sha256:
            return target
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        staging = self.cache_dir / f".staging-{uuid.uuid4().hex}"
        try:
            built = materialize_release(
                self.storage,
                release_id,
                staging,
                prefix=self.prefix,
                expected_manifest_sha256=manifest_sha256,
            )
            if target.exists():
                shutil.rmtree(target, ignore_errors=True)
            os.replace(built, target)
        finally:
            shutil.rmtree(staging, ignore_errors=True)
        return target

    def _load(self) -> Snapshot:
        found = read_current_pointer(self.storage, self.prefix)
        if found is None:
            raise ReleaseUnavailableError("no release has been published yet (no current.json)")
        pointer, _ = found
        target = self._materialize(pointer.release_id, pointer.manifest_sha256)
        reader = ReleaseReader(target, pointer=pointer)
        if reader.manifest_sha256 != pointer.manifest_sha256:
            raise ReleaseIntegrityError(f"cached manifest of {pointer.release_id} is stale")
        return Snapshot(reader)

    def _after_swap(self) -> None:
        """Delete cached releases other than the served and the previous one (best effort:
        files still open on Windows are left for a later swap)."""
        keep = {s.release_id for s in (self._snapshot, self._previous) if s is not None}
        if not self.cache_dir.is_dir():
            return
        for child in self.cache_dir.iterdir():
            if child.is_dir() and RELEASE_ID_RE.match(child.name) and child.name not in keep:
                shutil.rmtree(child, ignore_errors=True)

    def manifest_for(self, release_id: str) -> ReleaseManifest:
        if not RELEASE_ID_RE.match(release_id):
            raise KeyError(f"invalid release id: {release_id!r}")
        try:
            manifest, _ = read_manifest(self.storage, release_id, prefix=self.prefix)
        except KeyNotFoundError:
            raise KeyError(f"unknown release: {release_id}") from None
        return manifest

    def release_ids(self) -> list[str]:
        return list_release_ids(self.storage, self.prefix)
