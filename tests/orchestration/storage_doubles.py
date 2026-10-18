"""Storage test doubles of the orchestration tests.

:class:`RemoteStorage` makes a folder-based storage look remote (like Blob Storage): it exposes
no local file paths, so the pipeline downloads raw files into its scratch folder, and it records
every raw download. Failures can be injected per operation.
"""

from __future__ import annotations

from collections.abc import Callable

from docwiki.contracts.storage import Lease, Storage

RAW_PREFIX = "raw/"


class RemoteStorage:
    """:class:`Storage` delegating to ``inner`` without ``local_path`` (no in-place reads)."""

    def __init__(self, inner: Storage) -> None:
        self.inner = inner
        self.raw_reads: list[str] = []
        self.on_delete: Callable[[str], None] | None = None

    def _count(self, key: str) -> None:
        if key.startswith(RAW_PREFIX):
            self.raw_reads.append(key)

    def read_bytes(self, key: str) -> bytes:
        self._count(key)
        return self.inner.read_bytes(key)

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        self._count(key)
        return self.inner.read_with_etag(key)

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        if_match: str | None = None,
        if_none_match: str | None = None,
    ) -> str:
        return self.inner.write_bytes(key, data, if_match=if_match, if_none_match=if_none_match)

    def exists(self, key: str) -> bool:
        return self.inner.exists(key)

    def etag(self, key: str) -> str | None:
        return self.inner.etag(key)

    def list(self, prefix: str = "") -> list[str]:
        return self.inner.list(prefix)

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        if self.on_delete is not None:
            self.on_delete(key)
        return self.inner.delete(key, if_match=if_match)

    def acquire_lease(
        self, key: str, duration_s: float, *, owner: str | None = None
    ) -> Lease | None:
        return self.inner.acquire_lease(key, duration_s, owner=owner)

    def renew_lease(self, lease: Lease, duration_s: float | None = None) -> Lease:
        return self.inner.renew_lease(lease, duration_s)

    def release_lease(self, lease: Lease) -> None:
        self.inner.release_lease(lease)
