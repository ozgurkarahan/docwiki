"""Where ``ingest_start`` / ``recompile`` put their ``docwiki.ingest/v1`` messages.

* Local mode: :class:`FolderQueue` writes ``work/queue/<created>-<key hash>.json`` through the
  work :class:`~docwiki.contracts.storage.Storage` (one JSON message per file).
* Azure mode: :class:`AzureStorageQueue` sends the message to the Storage queue (``ingest`` by
  default) with Microsoft Entra ID (managed identity); the job is woken by KEDA.

Messages carry a deterministic ``idempotency_key``; a folder queue keeps at most one pending file
per key and the job de-duplicates by key.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.queue import QueueMessage
from docwiki.contracts.storage import PreconditionFailedError, Storage

__all__ = ["QUEUE_PREFIX", "AzureStorageQueue", "FolderQueue", "IngestQueue", "QueueReceipt"]

QUEUE_PREFIX = "work/queue/"


@dataclass(frozen=True)
class QueueReceipt:
    queue: str
    """``folder`` or ``azure-storage-queue``."""
    location: str
    """Folder queue key, or the queue name."""
    message_id: str | None = None
    duplicate: bool = False


class IngestQueue(Protocol):
    def send(self, message: QueueMessage) -> QueueReceipt: ...


class FolderQueue:
    """Folder queue ``work/queue/*.json`` for local mode."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    def send(self, message: QueueMessage) -> QueueReceipt:
        digest = sha256_hex(message.idempotency_key.encode("utf-8"))[:12]
        suffix = f"-{digest}.json"
        pending = [key for key in self.storage.list(QUEUE_PREFIX) if key.endswith(suffix)]
        if pending:
            return QueueReceipt("folder", pending[0], duplicate=True)
        key = f"{QUEUE_PREFIX}{message.created_at.strftime('%Y%m%dT%H%M%SZ')}{suffix}"
        try:
            self.storage.write_bytes(key, message.to_json().encode("utf-8"), if_none_match="*")
        except PreconditionFailedError:
            return QueueReceipt("folder", key, duplicate=True)
        return QueueReceipt("folder", key)


class AzureStorageQueue:
    """Azure Storage queue client authenticated with ``DefaultAzureCredential``."""

    def __init__(
        self,
        account: str | None,
        queue_name: str,
        *,
        credential: Any = None,
        client: Any = None,
    ) -> None:
        self.queue_name = queue_name
        if client is None:
            if not account:
                raise ValueError("a storage account name is required for the Azure queue")
            from azure.identity import DefaultAzureCredential
            from azure.storage.queue import QueueClient

            client = QueueClient(
                account_url=f"https://{account}.queue.core.windows.net",
                queue_name=queue_name,
                credential=credential or DefaultAzureCredential(),
            )
        self._client = client

    def send(self, message: QueueMessage) -> QueueReceipt:
        sent = self._client.send_message(message.to_body())
        message_id = getattr(sent, "id", None)
        return QueueReceipt("azure-storage-queue", self.queue_name, str(message_id or "") or None)
