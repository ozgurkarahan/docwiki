"""Azure Blob Storage behind the :class:`~docwiki.contracts.storage.Storage` protocol (subset).

The MCP server only needs reads, listings and ETag-conditional writes of small JSON/Markdown
objects (``work/`` state, proposals, overlay and reports) plus reads of ``releases/``. It
authenticates with Microsoft Entra ID (``DefaultAzureCredential``: managed identity in Azure); no
keys or connection strings. Leases are not supported here (the ingest job owns them).

Storage keys keep the logical container as their first segment (``work/…``, ``releases/…``);
``containers`` maps logical names to the account's container names.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, validate_key

__all__ = ["AzureBlobStorage"]


class AzureBlobStorage:
    """Minimal Blob implementation of the storage protocol used by the MCP server."""

    def __init__(
        self,
        account: str | None = None,
        *,
        containers: Mapping[str, str] | None = None,
        credential: Any = None,
        service_client: Any = None,
    ) -> None:
        self._containers = {"raw": "raw", "work": "work", "releases": "releases"}
        self._containers.update(containers or {})
        if service_client is None:
            if not account:
                raise ValueError("a storage account name is required for blob storage")
            from azure.identity import DefaultAzureCredential
            from azure.storage.blob import BlobServiceClient

            service_client = BlobServiceClient(
                account_url=f"https://{account}.blob.core.windows.net",
                credential=credential or DefaultAzureCredential(),
            )
        self._service = service_client

    def _split(self, key: str) -> tuple[str, str]:
        logical, _, name = validate_key(key).partition("/")
        if logical not in self._containers or not name:
            raise ValueError(f"storage key outside the known containers: {key!r}")
        return self._containers[logical], name

    def _blob(self, key: str) -> Any:
        container, name = self._split(key)
        return self._service.get_container_client(container).get_blob_client(name)

    def read_bytes(self, key: str) -> bytes:
        return self.read_with_etag(key)[0]

    def read_with_etag(self, key: str) -> tuple[bytes, str]:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            downloader = self._blob(key).download_blob()
            data = downloader.readall()
        except ResourceNotFoundError as exc:
            raise KeyNotFoundError(key) from exc
        return bytes(data), str(downloader.properties.etag)

    def write_bytes(
        self,
        key: str,
        data: bytes,
        *,
        if_match: str | None = None,
        if_none_match: Literal["*"] | None = None,
    ) -> str:
        from azure.core import MatchConditions
        from azure.core.exceptions import (
            ResourceExistsError,
            ResourceModifiedError,
            ResourceNotFoundError,
        )

        if if_none_match not in (None, "*"):
            raise ValueError("if_none_match only supports '*'")
        kwargs: dict[str, Any] = {"overwrite": True}
        if if_none_match == "*":
            kwargs = {"overwrite": False}
        elif if_match is not None:
            kwargs.update(etag=if_match, match_condition=MatchConditions.IfNotModified)
        try:
            result = self._blob(key).upload_blob(data, **kwargs)
        except (ResourceExistsError, ResourceModifiedError) as exc:
            raise PreconditionFailedError(f"{key}: precondition failed") from exc
        except ResourceNotFoundError as exc:
            if if_match is not None:
                raise PreconditionFailedError(f"{key}: missing") from exc
            raise
        return str(result.get("etag") or "")

    def exists(self, key: str) -> bool:
        return self.etag(key) is not None

    def etag(self, key: str) -> str | None:
        from azure.core.exceptions import ResourceNotFoundError

        try:
            return str(self._blob(key).get_blob_properties().etag)
        except ResourceNotFoundError:
            return None

    def list(self, prefix: str = "") -> list[str]:
        keys: list[str] = []
        for logical, container in self._containers.items():
            head = logical + "/"
            if prefix.startswith(head):
                name_prefix = prefix[len(head) :]
            elif head.startswith(prefix):
                name_prefix = ""
            else:
                continue
            client = self._service.get_container_client(container)
            for name in client.list_blob_names(name_starts_with=name_prefix or None):
                key = head + str(name)
                if key.startswith(prefix):
                    keys.append(key)
        return sorted(keys)

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        from azure.core import MatchConditions
        from azure.core.exceptions import ResourceModifiedError, ResourceNotFoundError

        kwargs: dict[str, Any] = {}
        if if_match is not None:
            kwargs.update(etag=if_match, match_condition=MatchConditions.IfNotModified)
        try:
            self._blob(key).delete_blob(**kwargs)
        except ResourceNotFoundError as exc:
            if if_match is not None:
                raise PreconditionFailedError(f"{key}: missing") from exc
            return False
        except ResourceModifiedError as exc:
            raise PreconditionFailedError(f"{key}: precondition failed") from exc
        return True

    def acquire_lease(self, key: str, duration_s: float, *, owner: str | None = None) -> Any:
        raise NotImplementedError("the MCP blob adapter does not manage leases")

    def renew_lease(self, lease: Any, duration_s: float | None = None) -> Any:
        raise NotImplementedError("the MCP blob adapter does not manage leases")

    def release_lease(self, lease: Any) -> None:
        raise NotImplementedError("the MCP blob adapter does not manage leases")
