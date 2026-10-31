"""Publishing through :class:`~docwiki.contracts.storage.Storage`: upload, atomic pointer swap,
retention, rollback and local materialisation of a release."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.ids import RELEASE_ID_RE
from docwiki.contracts.layout import ReleaseFiles, StorageKeys
from docwiki.contracts.manifest import CurrentPointer, ReleaseManifest
from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, Storage
from docwiki.release.layout import ReleaseIntegrityError
from docwiki.release.writer import StagedRelease

__all__ = [
    "PointerConflictError",
    "ReleaseIntegrityError",
    "RetentionOutcome",
    "apply_retention",
    "list_release_ids",
    "materialize_release",
    "publish_release",
    "read_current_pointer",
    "read_manifest",
    "rollback",
    "swap_current_pointer",
    "try_retention",
    "upload_release",
]

logger = logging.getLogger("docwiki.release")


class PointerConflictError(RuntimeError):
    """``current.json`` changed between read and swap (another writer won)."""


def _key(prefix: str, *parts: str) -> str:
    return "/".join([prefix.rstrip("/"), *parts])


def read_current_pointer(
    storage: Storage, prefix: str = StorageKeys.RELEASES
) -> tuple[CurrentPointer, str] | None:
    """``(pointer, etag)`` or ``None`` when no release was published yet."""
    try:
        data, etag = storage.read_with_etag(_key(prefix, "current.json"))
    except KeyNotFoundError:
        return None
    return CurrentPointer.from_json(data), etag


def swap_current_pointer(
    storage: Storage,
    pointer: CurrentPointer,
    *,
    expected_etag: str | None,
    prefix: str = StorageKeys.RELEASES,
) -> str:
    """Write ``current.json`` with ``If-Match`` (or create-only when ``expected_etag`` is None)."""
    data = pointer.to_json().encode("utf-8")
    try:
        if expected_etag is None:
            return storage.write_bytes(_key(prefix, "current.json"), data, if_none_match="*")
        return storage.write_bytes(_key(prefix, "current.json"), data, if_match=expected_etag)
    except PreconditionFailedError as exc:
        raise PointerConflictError("current.json changed concurrently; re-read and retry") from exc


def upload_release(
    storage: Storage,
    staged: StagedRelease,
    *,
    prefix: str = StorageKeys.RELEASES,
    workers: int = 8,
) -> None:
    """Copy a staged release to ``<prefix>/<release_id>/``; ``manifest.json`` is written last.

    Files are uploaded by up to ``workers`` threads. The first failure cancels the uploads not
    yet started, waits for the running ones and is raised; the manifest is then never written, so
    the release stays incomplete and no pointer can name it.
    """
    release_id = staged.release_id
    manifest_key = _key(prefix, release_id, ReleaseFiles.MANIFEST)
    if storage.exists(manifest_key):
        raise FileExistsError(f"release {release_id} already exists")

    def put(rel_path: str) -> None:
        storage.write_bytes(
            _key(prefix, release_id, rel_path), (staged.root / rel_path).read_bytes()
        )

    pool = ThreadPoolExecutor(max_workers=max(workers, 1), thread_name_prefix="docwiki-upload")
    try:
        futures = [pool.submit(put, rel_path) for rel_path in staged.manifest.files]
        for future in as_completed(futures):
            future.result()
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
    manifest_bytes = (staged.root / ReleaseFiles.MANIFEST).read_bytes()
    if sha256_hex(manifest_bytes) != staged.manifest_sha256:
        raise ReleaseIntegrityError("staged manifest changed after finalize")
    storage.write_bytes(manifest_key, manifest_bytes, if_none_match="*")


def list_release_ids(storage: Storage, prefix: str = StorageKeys.RELEASES) -> list[str]:
    """Release ids present under ``prefix`` (complete or not), oldest first."""
    ids = {
        key[len(prefix) + 1 :].split("/", 1)[0]
        for key in storage.list(prefix.rstrip("/") + "/")
        if "/" in key[len(prefix) + 1 :]
    }
    return sorted(release_id for release_id in ids if RELEASE_ID_RE.match(release_id))


def read_manifest(
    storage: Storage, release_id: str, *, prefix: str = StorageKeys.RELEASES
) -> tuple[ReleaseManifest, str]:
    data = storage.read_bytes(_key(prefix, release_id, ReleaseFiles.MANIFEST))
    return ReleaseManifest.from_json(data), sha256_hex(data)


def apply_retention(
    storage: Storage, *, prefix: str = StorageKeys.RELEASES, keep: int = 10
) -> list[str]:
    """Delete releases beyond the newest ``keep`` (the one in ``current.json`` is always kept)."""
    if keep < 1:
        raise ValueError("keep must be >= 1")
    ids = list_release_ids(storage, prefix)
    current = read_current_pointer(storage, prefix)
    current_id = current[0].release_id if current is not None else None
    # ids sort by their second-resolution timestamp: the current release goes last among the
    # releases of its second, so a fast second publish never keeps the older one instead
    ordered = sorted(ids, key=lambda rid: (rid.split("-", 1)[0], rid == current_id, rid))
    keep_ids = set(ordered[-keep:])
    if current_id is not None:
        keep_ids.add(current_id)
    deleted: list[str] = []
    for release_id in ids:
        if release_id in keep_ids:
            continue
        for key in storage.list(_key(prefix, release_id) + "/"):
            storage.delete(key)
        deleted.append(release_id)
    return deleted


@dataclass(frozen=True)
class RetentionOutcome:
    """Result of :func:`try_retention`: deleted release ids, and the failure if any."""

    deleted: list[str] = field(default_factory=list)
    error: str | None = None


def try_retention(
    storage: Storage, *, prefix: str = StorageKeys.RELEASES, keep: int = 10
) -> RetentionOutcome:
    """:func:`apply_retention` that never raises: a failure is logged and returned.

    Retention runs after the pointer swap, when the release is already published; a transient
    list or delete failure only delays the pruning to the next publish.
    """
    try:
        return RetentionOutcome(apply_retention(storage, prefix=prefix, keep=keep))
    except Exception as exc:
        text = " ".join(str(exc).split())[:300]
        error = f"{type(exc).__name__}: {text}" if text else type(exc).__name__
        logger.warning("release retention failed (old releases are kept for now): %s", error)
        return RetentionOutcome(error=error)


def publish_release(
    storage: Storage,
    staged: StagedRelease,
    *,
    prefix: str = StorageKeys.RELEASES,
    keep: int | None = 10,
    now: datetime | None = None,
    workers: int = 8,
) -> CurrentPointer:
    """Upload (``workers`` parallel uploads), swap ``current.json`` atomically (ETag-guarded),
    then apply retention.

    Refuses releases whose manifest records a failing blocking gate. The pointer is swapped only
    after every file and the manifest were uploaded. Retention is best effort
    (:func:`try_retention`) once the pointer is swapped; ``keep=None`` leaves it to the caller.
    """
    failing = staged.manifest.blocking_failures
    if failing:
        raise ValueError("blocking gates failed: " + ", ".join(gate.gate for gate in failing))
    current = read_current_pointer(storage, prefix)
    upload_release(storage, staged, prefix=prefix, workers=workers)
    pointer = CurrentPointer(
        release_id=staged.release_id,
        created_at=(now or datetime.now(UTC)).replace(microsecond=0),
        audience=staged.manifest.audience,
        manifest_sha256=staged.manifest_sha256,
    )
    swap_current_pointer(
        storage, pointer, expected_etag=current[1] if current else None, prefix=prefix
    )
    if keep is not None:
        try_retention(storage, prefix=prefix, keep=keep)
    return pointer


def rollback(
    storage: Storage,
    release_id: str,
    *,
    prefix: str = StorageKeys.RELEASES,
    now: datetime | None = None,
) -> CurrentPointer:
    """Point ``current.json`` at an existing, complete release."""
    manifest, manifest_sha = read_manifest(storage, release_id, prefix=prefix)
    current = read_current_pointer(storage, prefix)
    pointer = CurrentPointer(
        release_id=release_id,
        created_at=(now or datetime.now(UTC)).replace(microsecond=0),
        audience=manifest.audience,
        manifest_sha256=manifest_sha,
    )
    swap_current_pointer(
        storage, pointer, expected_etag=current[1] if current else None, prefix=prefix
    )
    return pointer


def materialize_release(
    storage: Storage,
    release_id: str,
    dest_dir: str | Path,
    *,
    prefix: str = StorageKeys.RELEASES,
    expected_manifest_sha256: str | None = None,
) -> Path:
    """Download a release into ``dest_dir/<release_id>`` verifying every hash (MCP cache)."""
    manifest, manifest_sha = read_manifest(storage, release_id, prefix=prefix)
    if expected_manifest_sha256 and manifest_sha != expected_manifest_sha256:
        raise ReleaseIntegrityError("manifest hash does not match current.json")
    target = Path(dest_dir) / release_id
    target.mkdir(parents=True, exist_ok=True)
    for rel_path, entry in manifest.files.items():
        data = storage.read_bytes(_key(prefix, release_id, rel_path))
        if sha256_hex(data) != entry.sha256 or len(data) != entry.size:
            raise ReleaseIntegrityError(f"{rel_path} does not match the manifest")
        path = target.joinpath(*rel_path.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    (target / ReleaseFiles.MANIFEST).write_bytes(
        storage.read_bytes(_key(prefix, release_id, ReleaseFiles.MANIFEST))
    )
    return target
