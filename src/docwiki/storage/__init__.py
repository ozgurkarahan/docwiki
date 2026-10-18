"""Storage backends of the engine: Azure Blob, routed/read-only folders and work queues.

``BlobStorage`` lives in :mod:`docwiki.storage.blob` and needs the ``azure`` extra; it is not
imported here so that local mode works without the Azure SDK.
:func:`storage_from_settings` picks the folder or Blob storage from the ``DOCWIKI_*`` settings.
"""

from docwiki.storage.factory import LOGICAL_CONTAINERS, storage_from_settings
from docwiki.storage.queue import (
    AzureStorageQueue,
    MessageLostError,
    ReceivedMessage,
    StorageQueue,
    WorkQueue,
)
from docwiki.storage.routed import DirectorySource, RoutedStorage, local_path_for

__all__ = [
    "LOGICAL_CONTAINERS",
    "AzureStorageQueue",
    "DirectorySource",
    "MessageLostError",
    "ReceivedMessage",
    "RoutedStorage",
    "StorageQueue",
    "WorkQueue",
    "local_path_for",
    "storage_from_settings",
]
