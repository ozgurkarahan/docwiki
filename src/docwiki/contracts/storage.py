"""Storage protocol (Blob or folder) with ETags, conditional writes and leases.

Keys are POSIX paths whose first segment is the container (``raw/…``, ``work/…``,
``releases/…``). ETags are opaque strings; :class:`FolderStorage` uses the SHA-256 hex digest of
the content. The engine lane provides the Blob implementation with the same semantics.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

from docwiki.contracts._base import sha256_hex

__all__ = [
    "FolderStorage",
    "KeyNotFoundError",
    "Lease",
    "LeaseLostError",
    "PreconditionFailedError",
    "Storage",
    "StorageError",
    "read_json",
    "validate_key",
    "write_json",
]


def _retry_windows[T](
    action: Callable[[], T],
    *,
    attempts: int = 200,
    missing_ok_check: Callable[[], bool] | None = None,
) -> T:
    """Retry ``action`` on ``PermissionError`` (Windows sharing violations during replace)."""
    for attempt in range(attempts):
        try:
            return action()
        except PermissionError:
            if attempt == attempts - 1 or (missing_ok_check is not None and not missing_ok_check()):
                raise
            time.sleep(0.005)
    raise AssertionError("unreachable")  # pragma: no cover


class StorageError(Exception):
    """Base class of storage errors."""


class KeyNotFoundError(StorageError):
    """The key does not exist."""


class PreconditionFailedError(StorageError):
    """``if_match`` / ``if_none_match`` precondition failed (HTTP 412 / 409 semantics)."""


class LeaseLostError(StorageError):
    """The lease is held by someone else (expired and re-acquired, or never ours)."""


@dataclass(frozen=True)
class Lease:
    key: str
    lease_id: str
    expires_at: float
    """Epoch seconds."""
    duration_s: float


@runtime_checkable
class Storage(Protocol):
    """Minimal object storage used by the pipeline, the MCP server and release I/O."""

    def read_bytes(self, key: str) -> bytes:
        """Content of ``key``; raises :class:`KeyNotFoundError`."""
        ...

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        """Content and ETag read atomically (for optimistic concurrency)."""
        ...

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        if_match: str | None = None,
        if_none_match: Literal["*"] | None = None,
    ) -> str:
        """Write ``data`` and return the new ETag.

        ``if_match``: only overwrite when the current ETag equals it. ``if_none_match="*"``: only
        create (fail when the key exists). Violations raise :class:`PreconditionFailedError`.
        """
        ...

    def exists(self, key: str) -> bool: ...

    def etag(self, key: str) -> str | None:
        """Current ETag, or ``None`` when the key does not exist."""
        ...

    def list(self, prefix: str = "") -> list[str]:
        """All keys starting with ``prefix`` (recursive), sorted."""
        ...

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        """Delete ``key``; ``False`` when it did not exist (and no ``if_match`` was given)."""
        ...

    def acquire_lease(
        self, key: str, duration_s: float, *, owner: str | None = None
    ) -> Lease | None:
        """Acquire an exclusive lease on ``key`` (created empty if missing); ``None`` when held."""
        ...

    def renew_lease(self, lease: Lease, duration_s: float | None = None) -> Lease:
        """Extend a lease we still own; raises :class:`LeaseLostError` otherwise."""
        ...

    def release_lease(self, lease: Lease) -> None:
        """Release a lease we own (no-op when already gone); raises :class:`LeaseLostError` when
        another owner holds it."""
        ...


def validate_key(key: str) -> str:
    """Return ``key`` when it is a valid storage key, else raise ``ValueError``."""
    if not key or key.startswith("/") or key.endswith("/") or "\\" in key:
        raise ValueError(f"invalid storage key: {key!r}")
    if any(part in ("", ".", "..") for part in key.split("/")):
        raise ValueError(f"invalid storage key segments: {key!r}")
    if any(ord(ch) < 32 for ch in key):
        raise ValueError("storage keys must not contain control characters")
    if key.split("/", 1)[0] == FolderStorage.INTERNAL_DIR:
        raise ValueError(f"reserved storage key: {key!r}")
    return key


class FolderStorage:
    """:class:`Storage` on a local folder (local mode, tests, the mock release fixture).

    Writes are atomic (temporary file + ``os.replace``); conditional writes and leases are
    serialised per key with an exclusive lock file, so they are safe across processes.
    Internal files live under ``<root>/.docwiki-storage/`` and are never listed.
    ``fsync=False`` skips the flush to disk (caches and tests); keep the default for state.
    """

    INTERNAL_DIR = ".docwiki-storage"

    def __init__(
        self,
        root: str | Path,
        *,
        clock: Callable[[], float] = time.time,
        lock_timeout_s: float = 10.0,
        stale_lock_s: float = 30.0,
        fsync: bool = True,
    ) -> None:
        self.root = Path(root)
        self._fsync = fsync
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock
        self._lock_timeout_s = lock_timeout_s
        self._stale_lock_s = stale_lock_s
        self._internal = self.root / self.INTERNAL_DIR
        for sub in ("locks", "leases", "tmp"):
            (self._internal / sub).mkdir(parents=True, exist_ok=True)

    def path_for(self, key: str) -> Path:
        return self.root.joinpath(*validate_key(key).split("/"))

    @staticmethod
    def _digest(key: str) -> str:
        return sha256_hex(key.encode("utf-8"))[:40]

    @contextlib.contextmanager
    def _locked(self, key: str) -> Iterator[None]:
        lock = self._internal / "locks" / f"{self._digest(key)}.lock"
        deadline = time.monotonic() + self._lock_timeout_s
        while True:
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except (FileExistsError, PermissionError):  # Windows: "delete pending" lock file
                try:
                    if time.time() - lock.stat().st_mtime > self._stale_lock_s:
                        lock.unlink(missing_ok=True)
                        continue
                except (FileNotFoundError, PermissionError):
                    pass
                if time.monotonic() > deadline:
                    raise StorageError(f"timed out waiting for lock on {key!r}") from None
                time.sleep(0.005)
        try:
            yield
        finally:
            _retry_windows(lambda: lock.unlink(missing_ok=True))

    def _atomic_write(self, path: Path, data: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._internal / "tmp" / f"{uuid.uuid4().hex}.tmp"
        with open(tmp, "wb") as handle:
            handle.write(data)
            if self._fsync:
                handle.flush()
                os.fsync(handle.fileno())
        try:
            _retry_windows(lambda: os.replace(tmp, path))
        except PermissionError:
            tmp.unlink(missing_ok=True)
            raise

    def read_bytes(self, key: str) -> bytes:
        path = self.path_for(key)
        try:
            return _retry_windows(path.read_bytes, missing_ok_check=path.is_file)
        except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
            if path.is_file():
                raise
            raise KeyNotFoundError(key) from exc

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        data = self.read_bytes(key)
        return data, sha256_hex(data)

    def exists(self, key: str) -> bool:
        return self.path_for(key).is_file()

    def etag(self, key: str) -> str | None:
        try:
            return sha256_hex(self.read_bytes(key))
        except KeyNotFoundError:
            return None

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        if_match: str | None = None,
        if_none_match: Literal["*"] | None = None,
    ) -> str:
        if if_none_match not in (None, "*"):
            raise ValueError("if_none_match only supports '*'")
        path = self.path_for(key)
        if if_match is None and if_none_match is None:
            self._atomic_write(path, data)
            return sha256_hex(data)
        with self._locked(key):
            current = self.etag(key)
            if if_none_match == "*" and current is not None:
                raise PreconditionFailedError(f"{key} already exists")
            if if_match is not None and current != if_match:
                raise PreconditionFailedError(f"{key} changed (etag mismatch)")
            self._atomic_write(path, data)
        return sha256_hex(data)

    def list(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            rel_dir = Path(dirpath).relative_to(self.root).as_posix()
            if rel_dir == ".":
                dirnames[:] = [name for name in dirnames if name != self.INTERNAL_DIR]
                rel_dir = ""
            for name in filenames:
                key = f"{rel_dir}/{name}" if rel_dir else name
                if key.startswith(prefix):
                    keys.append(key)
        return sorted(keys)

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        path = self.path_for(key)
        if if_match is None:
            try:
                path.unlink()
            except FileNotFoundError:
                return False
            self._prune_dirs(path.parent)
            return True
        with self._locked(key):
            current = self.etag(key)
            if current != if_match:
                raise PreconditionFailedError(f"{key} changed or missing (etag mismatch)")
            path.unlink()
        self._prune_dirs(path.parent)
        return True

    def _prune_dirs(self, directory: Path) -> None:
        while directory != self.root and directory.is_dir():
            try:
                directory.rmdir()
            except OSError:
                return
            directory = directory.parent

    def _lease_file(self, key: str) -> Path:
        return self._internal / "leases" / f"{self._digest(key)}.json"

    def _read_lease(self, key: str) -> dict[str, Any] | None:
        try:
            return json.loads(self._lease_file(key).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None

    def acquire_lease(
        self, key: str, duration_s: float, *, owner: str | None = None
    ) -> Lease | None:
        if duration_s <= 0:
            raise ValueError("lease duration must be positive")
        path = self.path_for(key)
        with self._locked(key):
            if not path.exists():
                self._atomic_write(path, b"")
            current = self._read_lease(key)
            now = self._clock()
            if current is not None and current["expires_at"] > now:
                return None
            lease = Lease(
                key=key,
                lease_id=uuid.uuid4().hex,
                expires_at=now + duration_s,
                duration_s=duration_s,
            )
            self._write_lease(lease, owner)
            return lease

    def _write_lease(self, lease: Lease, owner: str | None) -> None:
        record = {"lease_id": lease.lease_id, "expires_at": lease.expires_at, "owner": owner}
        self._atomic_write(self._lease_file(lease.key), json.dumps(record).encode("utf-8"))

    def renew_lease(self, lease: Lease, duration_s: float | None = None) -> Lease:
        with self._locked(lease.key):
            current = self._read_lease(lease.key)
            if current is None or current["lease_id"] != lease.lease_id:
                raise LeaseLostError(f"lease on {lease.key} is no longer ours")
            span = duration_s if duration_s is not None else lease.duration_s
            renewed = Lease(
                key=lease.key,
                lease_id=lease.lease_id,
                expires_at=self._clock() + span,
                duration_s=span,
            )
            self._write_lease(renewed, current.get("owner"))
            return renewed

    def release_lease(self, lease: Lease) -> None:
        with self._locked(lease.key):
            current = self._read_lease(lease.key)
            if current is None:
                return
            if current["lease_id"] != lease.lease_id:
                raise LeaseLostError(f"lease on {lease.key} is held by another owner")
            self._lease_file(lease.key).unlink(missing_ok=True)


def read_json(storage: Storage, key: str) -> Any:
    return json.loads(storage.read_bytes(key).decode("utf-8"))


def write_json(storage: Storage, key: str, value: Any, **conditions: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    return storage.write_bytes(key, text.encode("utf-8"), **conditions)
