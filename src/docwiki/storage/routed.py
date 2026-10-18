"""Storage composition for local mode.

* :class:`DirectorySource` — a read-only view of a local folder mounted as one container
  (``raw/<relative path>``), used by ``docwiki run --input <dir>`` so that the input folder is
  read in place and never written to.
* :class:`RoutedStorage` — routes keys by their first segment (the container) to different
  backends, e.g. ``raw`` to a :class:`DirectorySource` and everything else to a
  :class:`~docwiki.contracts.storage.FolderStorage`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Literal

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.storage import (
    KeyNotFoundError,
    Lease,
    Storage,
    StorageError,
    validate_key,
)

__all__ = ["DirectorySource", "RoutedStorage", "local_path_for"]


class DirectorySource:
    """Read-only :class:`Storage` over a folder; keys are ``<container>/<relative POSIX path>``.

    Hidden files and folders (name starting with ``.``) are ignored, as are files that are not
    valid storage keys. ETags are the SHA-256 of the content (like ``FolderStorage``).
    """

    def __init__(self, root: str | Path, *, container: str = "raw") -> None:
        self.root = Path(root)
        if not self.root.is_dir():
            raise FileNotFoundError(f"input folder not found: {self.root}")
        if "/" in container or not container:
            raise ValueError(f"invalid container name: {container!r}")
        self.container = container

    def local_path(self, key: str) -> Path:
        validate_key(key)
        head, sep, rest = key.partition("/")
        if head != self.container or not sep:
            raise ValueError(f"key {key!r} is outside the {self.container!r} container")
        if any(part.startswith(".") for part in rest.split("/")):
            raise KeyNotFoundError(key)
        return self.root.joinpath(*rest.split("/"))

    def read_bytes(self, key: str) -> bytes:
        path = self.local_path(key)
        try:
            return path.read_bytes()
        except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
            if path.is_file():
                raise
            raise KeyNotFoundError(key) from exc

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        data = self.read_bytes(key)
        return data, sha256_hex(data)

    def exists(self, key: str) -> bool:
        try:
            return self.local_path(key).is_file()
        except KeyNotFoundError:
            return False

    def etag(self, key: str) -> str | None:
        try:
            return sha256_hex(self.read_bytes(key))
        except KeyNotFoundError:
            return None

    def list(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        for dirpath, dirnames, filenames in os.walk(self.root):
            dirnames[:] = [name for name in dirnames if not name.startswith(".")]
            rel_dir = Path(dirpath).relative_to(self.root).as_posix()
            for name in filenames:
                if name.startswith("."):
                    continue
                rel = name if rel_dir == "." else f"{rel_dir}/{name}"
                key = f"{self.container}/{rel}"
                try:
                    validate_key(key)
                except ValueError:
                    continue
                if key.startswith(prefix):
                    keys.append(key)
        return sorted(keys)

    def _read_only(self, *_: object, **__: object) -> None:
        raise StorageError(f"{self.container}/ is a read-only input folder")

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        if_match: str | None = None,
        if_none_match: Literal["*"] | None = None,
    ) -> str:
        self._read_only()
        raise AssertionError("unreachable")  # pragma: no cover

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        self._read_only()
        raise AssertionError("unreachable")  # pragma: no cover

    def acquire_lease(
        self, key: str, duration_s: float, *, owner: str | None = None
    ) -> Lease | None:
        self._read_only()
        raise AssertionError("unreachable")  # pragma: no cover

    def renew_lease(self, lease: Lease, duration_s: float | None = None) -> Lease:
        self._read_only()
        raise AssertionError("unreachable")  # pragma: no cover

    def release_lease(self, lease: Lease) -> None:
        self._read_only()


class RoutedStorage:
    """Routes each key to the backend registered for its first segment (else ``default``)."""

    def __init__(self, default: Storage, routes: Mapping[str, Storage]) -> None:
        self.default = default
        self.routes = dict(routes)

    def backend(self, key: str) -> Storage:
        return self.routes.get(key.split("/", 1)[0], self.default)

    def read_bytes(self, key: str) -> bytes:
        return self.backend(key).read_bytes(key)

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        return self.backend(key).read_with_etag(key)

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        if_match: str | None = None,
        if_none_match: Literal["*"] | None = None,
    ) -> str:
        return self.backend(key).write_bytes(
            key, data, if_match=if_match, if_none_match=if_none_match
        )

    def exists(self, key: str) -> bool:
        return self.backend(key).exists(key)

    def etag(self, key: str) -> str | None:
        return self.backend(key).etag(key)

    def list(self, prefix: str = "") -> list[str]:
        head, sep, _ = prefix.partition("/")
        if sep:
            return self.backend(prefix).list(prefix)
        keys = [key for key in self.default.list(prefix) if key.split("/", 1)[0] not in self.routes]
        for name, backend in self.routes.items():
            if name.startswith(head):
                keys.extend(key for key in backend.list(prefix) if key.split("/", 1)[0] == name)
        return sorted(keys)

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        return self.backend(key).delete(key, if_match=if_match)

    def acquire_lease(
        self, key: str, duration_s: float, *, owner: str | None = None
    ) -> Lease | None:
        return self.backend(key).acquire_lease(key, duration_s, owner=owner)

    def renew_lease(self, lease: Lease, duration_s: float | None = None) -> Lease:
        return self.backend(lease.key).renew_lease(lease, duration_s)

    def release_lease(self, lease: Lease) -> None:
        self.backend(lease.key).release_lease(lease)

    def local_path(self, key: str) -> Path | None:
        return local_path_for(self.backend(key), key)


def local_path_for(storage: Storage, key: str) -> Path | None:
    """Local file path of ``key`` when the backend is folder-based, else ``None``."""
    local = getattr(storage, "local_path", None)
    if callable(local):
        try:
            path = local(key)
        except (KeyNotFoundError, ValueError):
            return None
        return path if isinstance(path, Path) else None
    path_for = getattr(storage, "path_for", None)
    if callable(path_for):
        try:
            path = path_for(key)
        except ValueError:
            return None
        return path if isinstance(path, Path) else None
    return None
