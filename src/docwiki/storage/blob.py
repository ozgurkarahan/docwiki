"""``BlobStorage``: the :class:`~docwiki.contracts.storage.Storage` protocol on Azure Blob Storage.

Keys keep the contract layout (``<container>/<path>``). By default every logical container
(``raw``, ``work``, ``releases``) maps to an Azure container of the same name; names can be
remapped, all keys can live in one container (:meth:`BlobStorage.single_container`) and an
optional blob-name prefix isolates several environments in the same containers.

Semantics match :class:`~docwiki.contracts.storage.FolderStorage`:

* ETags are opaque strings (the service ETag); ``if_match`` / ``if_none_match="*"`` map to
  conditional requests and failed preconditions raise ``PreconditionFailedError``;
* missing keys raise ``KeyNotFoundError``; ``list`` is recursive and sorted;
* leases are blob leases on the key (created empty when missing). Azure only accepts lease
  durations of 15–60 s, so durations are clamped; a renewal keeps the acquired duration.

Authentication uses ``DefaultAzureCredential`` (managed identity in Azure, ``az login``
locally); shared keys and SAS tokens are never used.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable, Mapping
from typing import Any, Literal

from azure.core import MatchConditions
from azure.core.exceptions import (
    AzureError,
    HttpResponseError,
    ResourceExistsError,
    ResourceModifiedError,
    ResourceNotFoundError,
)

from docwiki.contracts.storage import (
    KeyNotFoundError,
    Lease,
    LeaseLostError,
    PreconditionFailedError,
    StorageError,
    validate_key,
)

__all__ = ["DEFAULT_CONTAINERS", "MAX_LEASE_S", "MIN_LEASE_S", "BlobStorage", "clamp_lease"]

MIN_LEASE_S = 15
MAX_LEASE_S = 60
DEFAULT_CONTAINERS: dict[str, str] = {"raw": "raw", "work": "work", "releases": "releases"}

_LEASE_NOT_PRESENT = "LeaseNotPresentWithLeaseOperation"


def clamp_lease(duration_s: float) -> int:
    """Blob leases last 15–60 seconds (infinite leases are never used)."""
    if duration_s <= 0:
        raise ValueError("lease duration must be positive")
    return int(min(MAX_LEASE_S, max(MIN_LEASE_S, round(duration_s))))


def _status(exc: BaseException) -> int | None:
    value = getattr(exc, "status_code", None)
    return value if isinstance(value, int) else None


def _code(exc: BaseException) -> str | None:
    value = getattr(exc, "error_code", None)
    return str(value) if value else None


def _normalize_prefix(prefix: str) -> str:
    if not prefix:
        return ""
    clean = prefix.strip("/")
    if not clean:
        return ""
    validate_key(clean)
    return clean + "/"


def _default_service_client(account_url: str, credential: Any | None) -> Any:
    from azure.storage.blob import BlobServiceClient

    if credential is None:
        from azure.identity import DefaultAzureCredential

        credential = DefaultAzureCredential()
    return BlobServiceClient(account_url, credential=credential)


def _default_lease_client(blob_client: Any, lease_id: str) -> Any:
    from azure.storage.blob import BlobLeaseClient

    return BlobLeaseClient(blob_client, lease_id=lease_id)


class BlobStorage:
    """:class:`~docwiki.contracts.storage.Storage` backed by Azure Blob Storage."""

    def __init__(
        self,
        account_url: str | None = None,
        *,
        credential: Any | None = None,
        containers: Mapping[str, str] | None = None,
        single_container: str | None = None,
        prefix: str = "",
        service_client: Any | None = None,
        lease_client_factory: Callable[[Any, str], Any] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        if service_client is None:
            if not account_url:
                raise ValueError("BlobStorage needs an account URL or a service client")
            service_client = _default_service_client(account_url, credential)
        self._service = service_client
        self._containers = dict(DEFAULT_CONTAINERS if containers is None else containers)
        if not self._containers and single_container is None:
            raise ValueError("at least one container mapping is required")
        for logical in self._containers:
            if "/" in logical or not logical:
                raise ValueError(f"invalid logical container name: {logical!r}")
        self._single = single_container
        self._prefix = _normalize_prefix(prefix)
        self._lease_factory = lease_client_factory or _default_lease_client
        self._clock = clock
        self._container_clients: dict[str, Any] = {}

    @classmethod
    def single(
        cls, account_url: str | None, container: str, *, prefix: str = "", **kwargs: Any
    ) -> BlobStorage:
        """Every key in one container: blob name = ``prefix`` + full key."""
        return cls(account_url, single_container=container, prefix=prefix, containers={}, **kwargs)

    # -- routing ---------------------------------------------------------------------------

    def _container_client(self, name: str) -> Any:
        client = self._container_clients.get(name)
        if client is None:
            client = self._service.get_container_client(name)
            self._container_clients[name] = client
        return client

    def _route(self, key: str) -> tuple[str, str]:
        validate_key(key)
        if self._single is not None:
            return self._single, self._prefix + key
        logical, sep, rest = key.partition("/")
        if not sep or logical not in self._containers:
            raise ValueError(f"key {key!r} does not start with a known container {self._names()}")
        return self._containers[logical], self._prefix + rest

    def _names(self) -> list[str]:
        return sorted(self._containers)

    def _blob(self, key: str) -> Any:
        container, name = self._route(key)
        return self._container_client(container).get_blob_client(name)

    # -- reads -------------------------------------------------------------------------------

    def read_bytes(self, key: str) -> bytes:
        return self.read_with_etag(key)[0]

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        blob = self._blob(key)
        try:
            downloader = blob.download_blob()
            data = downloader.readall()
            etag = downloader.properties.etag
        except ResourceNotFoundError as exc:
            raise KeyNotFoundError(key) from exc
        except AzureError as exc:
            raise StorageError(f"reading {key!r} failed: {exc}") from exc
        return bytes(data), str(etag)

    def exists(self, key: str) -> bool:
        try:
            return bool(self._blob(key).exists())
        except AzureError as exc:
            raise StorageError(f"checking {key!r} failed: {exc}") from exc

    def etag(self, key: str) -> str | None:
        try:
            return str(self._blob(key).get_blob_properties().etag)
        except ResourceNotFoundError:
            return None
        except AzureError as exc:
            raise StorageError(f"reading properties of {key!r} failed: {exc}") from exc

    def list(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        if self._single is not None:
            names = self._list_names(self._single, self._prefix + prefix)
            keys = [name[len(self._prefix) :] for name in names]
        else:
            for logical, container in sorted(self._containers.items()):
                root = logical + "/"
                if prefix.startswith(root):
                    inner = prefix[len(root) :]
                elif root.startswith(prefix):
                    inner = ""
                else:
                    continue
                for name in self._list_names(container, self._prefix + inner):
                    keys.append(root + name[len(self._prefix) :])
        return sorted(key for key in keys if key.startswith(prefix) and not key.endswith("/"))

    def _list_names(self, container: str, starts_with: str) -> list[str]:
        client = self._container_client(container)
        try:
            return [str(name) for name in client.list_blob_names(name_starts_with=starts_with)]
        except ResourceNotFoundError:
            return []
        except AzureError as exc:
            raise StorageError(f"listing {container}/{starts_with} failed: {exc}") from exc

    # -- writes ------------------------------------------------------------------------------

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
        if if_match is not None and if_none_match is not None:
            raise PreconditionFailedError(f"{key}: if_match and if_none_match cannot both hold")
        blob = self._blob(key)
        kwargs: dict[str, Any] = {"overwrite": True}
        if if_none_match == "*":
            kwargs = {"overwrite": False}
        elif if_match is not None:
            kwargs["etag"] = if_match
            kwargs["match_condition"] = MatchConditions.IfNotModified
        try:
            result = blob.upload_blob(bytes(data), **kwargs)
        except (ResourceExistsError, ResourceModifiedError) as exc:
            raise PreconditionFailedError(f"{key}: precondition failed") from exc
        except ResourceNotFoundError as exc:
            if if_match is not None:
                raise PreconditionFailedError(f"{key} does not exist (etag mismatch)") from exc
            raise StorageError(f"writing {key!r} failed: {exc}") from exc
        except HttpResponseError as exc:
            if _status(exc) in (409, 412):
                raise PreconditionFailedError(f"{key}: precondition failed") from exc
            raise StorageError(f"writing {key!r} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"writing {key!r} failed: {exc}") from exc
        return str(result["etag"])

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        blob = self._blob(key)
        kwargs: dict[str, Any] = {"delete_snapshots": "include"}
        if if_match is not None:
            kwargs["etag"] = if_match
            kwargs["match_condition"] = MatchConditions.IfNotModified
        try:
            blob.delete_blob(**kwargs)
        except ResourceNotFoundError as exc:
            if if_match is not None:
                raise PreconditionFailedError(f"{key} changed or missing (etag mismatch)") from exc
            return False
        except ResourceModifiedError as exc:
            raise PreconditionFailedError(f"{key} changed (etag mismatch)") from exc
        except HttpResponseError as exc:
            if _status(exc) == 412:
                raise PreconditionFailedError(f"{key}: precondition failed") from exc
            raise StorageError(f"deleting {key!r} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"deleting {key!r} failed: {exc}") from exc
        return True

    # -- leases ------------------------------------------------------------------------------

    def acquire_lease(
        self, key: str, duration_s: float, *, owner: str | None = None
    ) -> Lease | None:
        span = clamp_lease(duration_s)
        blob = self._blob(key)
        try:
            blob.upload_blob(b"", overwrite=False)
        except ResourceExistsError:
            pass
        except HttpResponseError as exc:
            if _status(exc) not in (409, 412):
                raise StorageError(f"creating lease blob {key!r} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"creating lease blob {key!r} failed: {exc}") from exc
        lease_id = str(uuid.uuid4())
        try:
            self._lease_factory(blob, lease_id).acquire(lease_duration=span)
        except HttpResponseError as exc:
            if _status(exc) == 409:
                return None
            raise StorageError(f"acquiring the lease on {key!r} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"acquiring the lease on {key!r} failed: {exc}") from exc
        return Lease(key=key, lease_id=lease_id, expires_at=self._clock() + span, duration_s=span)

    def renew_lease(self, lease: Lease, duration_s: float | None = None) -> Lease:
        """Renew with the duration chosen at acquisition (Azure cannot change it)."""
        blob = self._blob(lease.key)
        try:
            self._lease_factory(blob, lease.lease_id).renew()
        except HttpResponseError as exc:
            if _status(exc) in (400, 404, 409, 412):
                raise LeaseLostError(f"lease on {lease.key} is no longer ours") from exc
            raise StorageError(f"renewing the lease on {lease.key!r} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"renewing the lease on {lease.key!r} failed: {exc}") from exc
        return Lease(
            key=lease.key,
            lease_id=lease.lease_id,
            expires_at=self._clock() + lease.duration_s,
            duration_s=lease.duration_s,
        )

    def release_lease(self, lease: Lease) -> None:
        blob = self._blob(lease.key)
        try:
            self._lease_factory(blob, lease.lease_id).release()
        except ResourceNotFoundError:
            return
        except HttpResponseError as exc:
            if _code(exc) == _LEASE_NOT_PRESENT:
                return
            if _status(exc) in (409, 412):
                raise LeaseLostError(f"lease on {lease.key} is held by another owner") from exc
            raise StorageError(f"releasing the lease on {lease.key!r} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"releasing the lease on {lease.key!r} failed: {exc}") from exc

    def close(self) -> None:
        close = getattr(self._service, "close", None)
        if callable(close):
            close()
