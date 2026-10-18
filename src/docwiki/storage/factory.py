"""Storage from the shared ``DOCWIKI_*`` settings (engine, portal and MCP server).

Keys keep their logical container as first segment (``raw/…``, ``work/…``, ``releases/…``,
architecture §3) in both modes, so callers use :class:`docwiki.contracts.layout.StorageKeys`
unchanged.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.storage import FolderStorage, Storage

if TYPE_CHECKING:
    from docwiki.orchestration.settings import EngineSettings

__all__ = ["LOGICAL_CONTAINERS", "storage_from_settings"]

LOGICAL_CONTAINERS = (StorageKeys.RAW, StorageKeys.WORK, StorageKeys.RELEASES)


def storage_from_settings(
    container: str | None = None,
    *,
    settings: EngineSettings | None = None,
    env: Mapping[str, str] | None = None,
) -> Storage:
    """The storage of this deployment.

    * ``DOCWIKI_MODE=local``: a :class:`FolderStorage` rooted at ``DOCWIKI_WORK_DIR``;
    * ``DOCWIKI_MODE=azure``: a :class:`docwiki.storage.blob.BlobStorage` on
      ``DOCWIKI_STORAGE_ACCOUNT`` with ``DefaultAzureCredential`` (managed identity), the
      container names coming from ``DOCWIKI_RAW_CONTAINER`` / ``DOCWIKI_WORK_CONTAINER`` /
      ``DOCWIKI_RELEASES_CONTAINER``.

    ``container`` (``raw``, ``work`` or ``releases``) restricts a Blob storage to that logical
    container, so a reader such as the portal only touches what its role allows; keys still
    start with the container name. ``settings`` wins over ``env`` (default ``os.environ``).
    """
    from docwiki.orchestration.settings import EngineSettings

    if container is not None and container not in LOGICAL_CONTAINERS:
        raise ValueError(
            f"unknown container {container!r} (expected one of {', '.join(LOGICAL_CONTAINERS)})"
        )
    resolved = settings if settings is not None else EngineSettings.from_env(env)
    if resolved.mode == "azure":
        from docwiki.storage.blob import BlobStorage

        names = {
            StorageKeys.RAW: resolved.raw_container,
            StorageKeys.WORK: resolved.work_container,
            StorageKeys.RELEASES: resolved.releases_container,
        }
        if container is not None:
            names = {container: names[container]}
        return BlobStorage(resolved.blob_account_url, containers=names)
    return FolderStorage(resolved.work_dir)
