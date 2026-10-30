"""Keep a local, verified copy of the current release's ``site/`` folder.

The portal reads ``releases/current.json`` through the :class:`~docwiki.contracts.storage.Storage`
protocol (folder or Blob), takes only the ``site/`` files listed in the release manifest,
verifies every SHA-256 against the manifest (whose own hash is pinned by the pointer), then swaps
the served folder atomically. :meth:`SiteSync.refresh` is cheap when the pointer's ETag did not
change, so it can be polled.

A new release reuses the files of the active copy that the manifests say are unchanged (same path,
SHA-256 and size, re-verified locally) and downloads only the others. Text files of at least
:data:`GZIP_MIN_BYTES` are also gzip-compressed once, before activation, into
``<copy>/.docwiki-gzip/<path>.gz`` (a hidden folder the portal never serves directly).
"""

from __future__ import annotations

import gzip
import logging
import os
import shutil
import threading
import zlib
from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.layout import ReleaseFiles, StorageKeys
from docwiki.contracts.manifest import FileEntry
from docwiki.contracts.storage import Storage
from docwiki.release.publish import ReleaseIntegrityError, read_current_pointer, read_manifest

__all__ = [
    "COMPRESSIBLE_SUFFIXES",
    "GZIP_DIR",
    "GZIP_MIN_BYTES",
    "PortalSyncError",
    "SiteState",
    "SiteSync",
    "gzip_path",
    "site_state_from_dir",
]

log = logging.getLogger("docwiki.portal")

SITE_PREFIX = f"{ReleaseFiles.SITE_DIR}/"
_COMPLETE_MARKER = ".docwiki-portal-complete"
GZIP_DIR = ".docwiki-gzip"
"""Hidden folder of a local copy holding the precompressed files (``<path>.gz``)."""
GZIP_MIN_BYTES = 1024
COMPRESSIBLE_SUFFIXES = frozenset(
    {".html", ".css", ".js", ".mjs", ".json", ".svg", ".xml", ".txt", ".md", ".csv"}
)


def gzip_path(root: Path, rel: str) -> Path:
    """Where the precompressed copy of the site file ``rel`` lives under ``root``."""
    return root.joinpath(GZIP_DIR, *f"{rel}.gz".split("/"))


def _compressible(rel: str, size: int) -> bool:
    return size >= GZIP_MIN_BYTES and PurePosixPath(rel).suffix.lower() in COMPRESSIBLE_SUFFIXES


class PortalSyncError(RuntimeError):
    """The current release cannot be served (no pointer, no site, integrity failure)."""


@dataclass(frozen=True)
class SiteState:
    """A complete local copy of one release's site."""

    root: Path
    release_id: str | None
    manifest_sha256: str | None
    hashes: Mapping[str, str] = field(default_factory=dict)
    """Site-relative path → SHA-256 hex (strong ETags); empty for a plain folder."""
    synced_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    audience: str | None = None
    """The release's audience (from its verified manifest); ``None`` for a plain folder."""
    compressed: frozenset[str] = frozenset()
    """Site-relative paths that have a precompressed copy (:func:`gzip_path`)."""


def site_state_from_dir(root: Path) -> SiteState:
    """Serve an already built site folder as is (local preview, no storage)."""
    if not (root / "index.html").is_file():
        raise PortalSyncError(f"no index.html in {root}")
    return SiteState(root.resolve(), None, None)


def _safe_relative(path: str) -> str:
    parts = path.split("/")
    if not path or "\\" in path or any(part in ("", ".", "..") for part in parts):
        raise PortalSyncError(f"unsafe path in manifest: {path!r}")
    return path


class SiteSync:
    """Mirror ``<prefix>/<current release>/site/`` into ``cache_dir/<release_id>-<sha>/``."""

    def __init__(
        self,
        storage: Storage,
        cache_dir: str | Path,
        *,
        prefix: str = StorageKeys.RELEASES,
        keep: int = 2,
        workers: int = 8,
    ) -> None:
        self.storage = storage
        self.cache_dir = Path(cache_dir).resolve()
        self.prefix = prefix.rstrip("/")
        self.keep = max(keep, 1)
        self.workers = max(workers, 1)
        self._state: SiteState | None = None
        self._pointer_etag: str | None = None
        self._lock = threading.Lock()
        self.last_error: str | None = None

    @property
    def state(self) -> SiteState | None:
        return self._state

    @property
    def pointer_key(self) -> str:
        return f"{self.prefix}/current.json"

    def refresh(self, *, force: bool = False) -> bool:
        """Sync when ``current.json`` changed; True when a new site was activated.

        Errors are raised and remembered in :attr:`last_error`; the previous site keeps being
        served.
        """
        with self._lock:
            try:
                activated = self._refresh(force=force)
            except Exception as exc:
                self.last_error = f"{type(exc).__name__}: {exc}"
                raise
            self.last_error = None
            return activated

    def _refresh(self, *, force: bool) -> bool:
        etag = self.storage.etag(self.pointer_key)
        if etag is None:
            raise PortalSyncError(f"no release published ({self.pointer_key} not found)")
        if not force and etag == self._pointer_etag and self._state is not None:
            return False
        current = read_current_pointer(self.storage, self.prefix)
        if current is None:
            raise PortalSyncError(f"no release published ({self.pointer_key} not found)")
        pointer, pointer_etag = current
        state = self._state
        if (
            state is not None
            and state.release_id == pointer.release_id
            and state.manifest_sha256 == pointer.manifest_sha256
        ):
            self._pointer_etag = pointer_etag
            return False
        manifest, manifest_sha = read_manifest(self.storage, pointer.release_id, prefix=self.prefix)
        if manifest_sha != pointer.manifest_sha256:
            raise ReleaseIntegrityError("manifest hash does not match current.json")
        files = {
            _safe_relative(path[len(SITE_PREFIX) :]): entry
            for path, entry in manifest.files.items()
            if path.startswith(SITE_PREFIX)
        }
        if "index.html" not in files:
            raise PortalSyncError(f"release {pointer.release_id} has no site/index.html")
        target = self.cache_dir / f"{pointer.release_id}-{manifest_sha[:12]}"
        if (target / _COMPLETE_MARKER).is_file():
            compressed = frozenset(path for path in files if gzip_path(target, path).is_file())
        else:
            compressed = self._download(pointer.release_id, files, target, previous=state)
        self._state = SiteState(
            target,
            pointer.release_id,
            manifest_sha,
            {path: entry.sha256 for path, entry in files.items()},
            audience=manifest.audience,
            compressed=compressed,
        )
        self._pointer_etag = pointer_etag
        self._prune(keep_dir=target)
        return True

    def _download(
        self,
        release_id: str,
        files: Mapping[str, FileEntry],
        target: Path,
        *,
        previous: SiteState | None = None,
    ) -> frozenset[str]:
        """Fill ``target`` with verified copies of ``files``: unchanged files of ``previous``
        (the active copy) are reused locally, the others are downloaded. Returns the paths that
        were precompressed."""
        partial = target.with_name(f"{target.name}.partial-{os.getpid()}")
        shutil.rmtree(partial, ignore_errors=True)
        partial.mkdir(parents=True)
        reusable = previous if previous is not None and previous.root.is_dir() else None

        def local(path: str, entry: FileEntry) -> tuple[Path, bytes] | None:
            """The previous copy of ``path`` when it is the same file (re-verified)."""
            if reusable is None or reusable.hashes.get(path) != entry.sha256:
                return None
            source = reusable.root.joinpath(*path.split("/"))
            try:
                data = source.read_bytes()
            except OSError:
                return None
            if sha256_hex(data) != entry.sha256 or len(data) != entry.size:
                return None
            return source, data

        def place(source: Path | None, data: bytes, destination: Path) -> None:
            destination.parent.mkdir(parents=True, exist_ok=True)
            if source is not None:
                try:
                    os.link(source, destination)
                    return
                except OSError:
                    pass
            destination.write_bytes(data)

        def compress(path: str, entry: FileEntry, data: bytes) -> bool:
            if not _compressible(path, len(data)):
                return False
            old: Path | None = None
            packed: bytes | None = None
            if reusable is not None and path in reusable.compressed:
                old = gzip_path(reusable.root, path)
                try:
                    packed = old.read_bytes()
                    if sha256_hex(gzip.decompress(packed)) != entry.sha256:
                        packed = None
                except (OSError, EOFError, zlib.error):
                    packed = None
            if packed is None:
                old = None
                packed = gzip.compress(data, compresslevel=9, mtime=0)
            if len(packed) >= len(data):
                return False
            place(old, packed, gzip_path(partial, path))
            return True

        def fetch(item: tuple[str, FileEntry]) -> tuple[str, bool, bool]:
            path, entry = item
            found = local(path, entry)
            if found is not None:
                source, data = found
            else:
                source = None
                key = f"{self.prefix}/{release_id}/{SITE_PREFIX}{path}"
                data = self.storage.read_bytes(key)
                if sha256_hex(data) != entry.sha256 or len(data) != entry.size:
                    raise ReleaseIntegrityError(f"site/{path} does not match the manifest")
            place(source, data, partial.joinpath(*path.split("/")))
            return path, found is not None, compress(path, entry, data)

        try:
            with ThreadPoolExecutor(max_workers=self.workers) as pool:
                results = list(pool.map(fetch, sorted(files.items())))
            (partial / _COMPLETE_MARKER).write_text(release_id + "\n", encoding="utf-8")
            shutil.rmtree(target, ignore_errors=True)
            partial.replace(target)
        finally:
            shutil.rmtree(partial, ignore_errors=True)
        reused = sum(1 for _, was_reused, _ in results if was_reused)
        log.info(
            "site of release %s: %d files reused, %d downloaded",
            release_id,
            reused,
            len(results) - reused,
        )
        return frozenset(path for path, _, packed in results if packed)

    def _prune(self, *, keep_dir: Path) -> None:
        """Keep the active copy and the previous ones (in-flight requests may still read them)."""
        if not self.cache_dir.is_dir():
            return
        copies = sorted(
            (p for p in self.cache_dir.iterdir() if p.is_dir() and p != keep_dir),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for stale in copies[self.keep - 1 :]:
            shutil.rmtree(stale, ignore_errors=True)
