"""Work queues of the run control (architecture §4).

Two implementations of :class:`WorkQueue`:

* :class:`AzureStorageQueue` — Azure Storage Queue with ``DefaultAzureCredential`` (queue
  ``ingest`` and its poison queue ``ingest-poison``);
* :class:`StorageQueue` — messages as JSON files under ``work/queue/`` of any
  :class:`~docwiki.contracts.storage.Storage` (local mode), claimed with ETag-conditional writes.

Both give the same semantics: a received message is invisible for ``visibility_timeout_s`` and
carries a pop receipt; renewing the visibility returns a new pop receipt; deleting or renewing
with a stale receipt fails (the message was re-delivered to someone else). Messages are moved to
the poison queue by :meth:`WorkQueue.dead_letter`.
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from docwiki.contracts.storage import (
    KeyNotFoundError,
    PreconditionFailedError,
    Storage,
    StorageError,
)

__all__ = [
    "DEFAULT_POISON_PREFIX",
    "DEFAULT_QUEUE_PREFIX",
    "AzureStorageQueue",
    "MessageLostError",
    "QueueAuthorizationError",
    "ReceivedMessage",
    "StorageQueue",
    "WorkQueue",
]

DEFAULT_QUEUE_PREFIX = "work/queue"
DEFAULT_POISON_PREFIX = "work/queue-poison"
MAX_BATCH = 32
_ENVELOPE_KEYS = frozenset({"id", "content", "dequeue_count", "visible_at"})


def _created_at(message: Any) -> float:
    """``created_at`` of a bare JSON message as a timestamp (0 when absent or invalid)."""
    value = message.get("created_at") if isinstance(message, dict) else None
    if not isinstance(value, str):
        return 0.0
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return 0.0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


class MessageLostError(StorageError):
    """The pop receipt is stale: the message became visible again or was deleted."""


class QueueAuthorizationError(StorageError):
    """The queue refused the operation (HTTP 401/403): a configuration error, retrying is futile.

    Renewing the visibility (Update Message) needs ``queues/messages/write``, e.g. the role
    *Storage Queue Data Contributor* on the queue.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class ReceivedMessage:
    """A message received from a queue, with the pop receipt that proves ownership."""

    id: str
    pop_receipt: str
    content: str
    dequeue_count: int
    inserted_at: datetime | None = None
    next_visible_at: datetime | None = None


@runtime_checkable
class WorkQueue(Protocol):
    """Minimal queue API used by the worker loop."""

    def send(self, content: str, *, visibility_timeout_s: int = 0) -> str:
        """Enqueue ``content``; returns the message id."""
        ...

    def receive(
        self, *, max_messages: int = MAX_BATCH, visibility_timeout_s: int = 300
    ) -> list[ReceivedMessage]:
        """Receive up to ``max_messages`` visible messages and hide them for a while."""
        ...

    def renew(self, message: ReceivedMessage, visibility_timeout_s: int) -> ReceivedMessage:
        """Extend the invisibility; returns the message with its new pop receipt.

        Raises :class:`MessageLostError` when the receipt is stale and
        :class:`QueueAuthorizationError` when the identity may not update messages."""
        ...

    def delete(self, message: ReceivedMessage) -> bool:
        """Delete a message we own; ``False`` when it is gone or the receipt is stale."""
        ...

    def dead_letter(self, message: ReceivedMessage) -> None:
        """Copy the message to the poison queue and delete it from this queue."""
        ...

    def visible_count(self) -> int:
        """Number of currently visible messages (approximate, capped at 32)."""
        ...


# -- Azure Storage Queue -----------------------------------------------------------------------


def _status(exc: BaseException) -> int | None:
    value = getattr(exc, "status_code", None)
    return value if isinstance(value, int) else None


def _as_text(content: Any) -> str:
    if isinstance(content, bytes):
        return content.decode("utf-8")
    return "" if content is None else str(content)


class AzureStorageQueue:
    """:class:`WorkQueue` on Azure Storage Queues (Entra auth, no shared keys)."""

    def __init__(
        self,
        account_url: str | None = None,
        queue_name: str = "ingest",
        poison_queue_name: str = "ingest-poison",
        *,
        credential: Any | None = None,
        queue_client: Any | None = None,
        poison_client: Any | None = None,
    ) -> None:
        if queue_client is None or poison_client is None:
            if not account_url:
                raise ValueError("AzureStorageQueue needs an account URL or queue clients")
            from azure.storage.queue import QueueClient

            if credential is None:
                from azure.identity import DefaultAzureCredential

                credential = DefaultAzureCredential()
            queue_client = queue_client or QueueClient(
                account_url, queue_name, credential=credential
            )
            poison_client = poison_client or QueueClient(
                account_url, poison_queue_name, credential=credential
            )
        self._queue = queue_client
        self._poison = poison_client

    @staticmethod
    def _convert(message: Any) -> ReceivedMessage:
        return ReceivedMessage(
            id=str(message.id),
            pop_receipt=str(message.pop_receipt),
            content=_as_text(message.content),
            dequeue_count=int(message.dequeue_count or 0),
            inserted_at=getattr(message, "inserted_on", None),
            next_visible_at=getattr(message, "next_visible_on", None),
        )

    def send(self, content: str, *, visibility_timeout_s: int = 0) -> str:
        sent = self._queue.send_message(content, visibility_timeout=visibility_timeout_s or None)
        return str(sent.id)

    def receive(
        self, *, max_messages: int = MAX_BATCH, visibility_timeout_s: int = 300
    ) -> list[ReceivedMessage]:
        from azure.core.exceptions import AzureError

        count = max(1, min(MAX_BATCH, max_messages))
        try:
            pages = self._queue.receive_messages(
                messages_per_page=count,
                visibility_timeout=visibility_timeout_s,
                max_messages=count,
            )
            return [self._convert(message) for message in pages]
        except AzureError as exc:
            raise StorageError(f"receiving queue messages failed: {exc}") from exc

    def renew(self, message: ReceivedMessage, visibility_timeout_s: int) -> ReceivedMessage:
        from azure.core.exceptions import AzureError, HttpResponseError

        try:
            updated = self._queue.update_message(
                message.id,
                pop_receipt=message.pop_receipt,
                visibility_timeout=visibility_timeout_s,
            )
        except HttpResponseError as exc:
            status = _status(exc)
            if status in (400, 404):
                raise MessageLostError(f"message {message.id} is no longer ours") from exc
            if status in (401, 403):
                raise QueueAuthorizationError(
                    f"renewing message {message.id} was refused (HTTP {status}): the identity "
                    "needs queues/messages/write on the queue (Storage Queue Data Contributor)",
                    status_code=status,
                ) from exc
            raise StorageError(f"renewing message {message.id} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"renewing message {message.id} failed: {exc}") from exc
        return replace(
            message,
            pop_receipt=str(updated.pop_receipt),
            next_visible_at=getattr(updated, "next_visible_on", None),
        )

    def delete(self, message: ReceivedMessage) -> bool:
        from azure.core.exceptions import AzureError, HttpResponseError

        try:
            self._queue.delete_message(message.id, pop_receipt=message.pop_receipt)
        except HttpResponseError as exc:
            if _status(exc) in (400, 404):
                return False
            raise StorageError(f"deleting message {message.id} failed: {exc}") from exc
        except AzureError as exc:
            raise StorageError(f"deleting message {message.id} failed: {exc}") from exc
        return True

    def dead_letter(self, message: ReceivedMessage) -> None:
        self._poison.send_message(message.content)
        self.delete(message)

    def visible_count(self) -> int:
        return len(self._queue.peek_messages(max_messages=MAX_BATCH))


# -- Storage-backed queue (local mode) -------------------------------------------------------


class StorageQueue:
    """:class:`WorkQueue` as JSON files under a storage prefix (default ``work/queue/``).

    Each message is one file ``<prefix>/<inserted ns>-<uuid>.json`` holding the content, the
    dequeue count, the time it becomes visible again and the current pop receipt. Receiving,
    renewing and deleting are ETag-conditional, so several workers can share the folder.

    Files written by other producers that hold a bare message (e.g. the ``docwiki.ingest/v1``
    JSON written by the MCP server's folder queue) are visible messages with a dequeue count of
    0; the first receive rewrites them into the envelope above (same key, ``If-Match``).
    """

    def __init__(
        self,
        storage: Storage,
        *,
        prefix: str = DEFAULT_QUEUE_PREFIX,
        poison_prefix: str = DEFAULT_POISON_PREFIX,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._storage = storage
        self._prefix = prefix.strip("/")
        self._poison_prefix = poison_prefix.strip("/")
        self._clock = clock

    def _key(self, message_id: str, *, poison: bool = False) -> str:
        return f"{self._poison_prefix if poison else self._prefix}/{message_id}.json"

    @staticmethod
    def _encode(record: dict[str, Any]) -> bytes:
        return (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")

    @staticmethod
    def _decode(key: str, data: bytes) -> dict[str, Any]:
        """The envelope of ``key``; a bare message becomes a fresh, visible envelope."""
        text = data.decode("utf-8", errors="replace")
        try:
            parsed: Any = json.loads(text)
        except json.JSONDecodeError:
            parsed = None
        if isinstance(parsed, dict) and parsed.keys() >= _ENVELOPE_KEYS:
            return parsed
        name = key.rsplit("/", 1)[-1].removesuffix(".json")
        return {
            "id": name,
            "content": text.strip(),
            "inserted_at": _created_at(parsed),
            "dequeue_count": 0,
            "visible_at": 0.0,
            "pop_receipt": None,
        }

    def send(self, content: str, *, visibility_timeout_s: int = 0) -> str:
        now = self._clock()
        message_id = f"{time.time_ns():020d}-{uuid.uuid4().hex[:12]}"
        record = {
            "id": message_id,
            "content": content,
            "inserted_at": now,
            "dequeue_count": 0,
            "visible_at": now + max(0, visibility_timeout_s),
            "pop_receipt": None,
        }
        self._storage.write_bytes(self._key(message_id), self._encode(record), if_none_match="*")
        return message_id

    def _records(self, prefix: str) -> list[str]:
        return [key for key in self._storage.list(prefix + "/") if key.endswith(".json")]

    @staticmethod
    def _message(record: dict[str, Any]) -> ReceivedMessage:
        return ReceivedMessage(
            id=str(record["id"]),
            pop_receipt=str(record["pop_receipt"]),
            content=str(record["content"]),
            dequeue_count=int(record["dequeue_count"]),
            inserted_at=datetime.fromtimestamp(float(record["inserted_at"]), UTC),
            next_visible_at=datetime.fromtimestamp(float(record["visible_at"]), UTC),
        )

    def receive(
        self, *, max_messages: int = MAX_BATCH, visibility_timeout_s: int = 300
    ) -> list[ReceivedMessage]:
        wanted = max(1, min(MAX_BATCH, max_messages))
        received: list[ReceivedMessage] = []
        for key in self._records(self._prefix):
            if len(received) >= wanted:
                break
            try:
                data, etag = self._storage.read_with_etag(key)
            except KeyNotFoundError:
                continue
            record = self._decode(key, data)
            now = self._clock()
            if float(record["visible_at"]) > now:
                continue
            record["id"] = key.rsplit("/", 1)[-1].removesuffix(".json")
            record["dequeue_count"] = int(record["dequeue_count"]) + 1
            record["visible_at"] = now + visibility_timeout_s
            record["pop_receipt"] = uuid.uuid4().hex
            try:
                self._storage.write_bytes(key, self._encode(record), if_match=etag)
            except (PreconditionFailedError, KeyNotFoundError):
                continue
            received.append(self._message(record))
        return received

    def _owned(self, message: ReceivedMessage) -> tuple[dict[str, Any], str] | None:
        key = self._key(message.id)
        try:
            data, etag = self._storage.read_with_etag(key)
        except KeyNotFoundError:
            return None
        record = self._decode(key, data)
        if record.get("pop_receipt") != message.pop_receipt:
            return None
        return record, etag

    def renew(self, message: ReceivedMessage, visibility_timeout_s: int) -> ReceivedMessage:
        owned = self._owned(message)
        if owned is None:
            raise MessageLostError(f"message {message.id} is no longer ours")
        record, etag = owned
        record["visible_at"] = self._clock() + visibility_timeout_s
        record["pop_receipt"] = uuid.uuid4().hex
        try:
            self._storage.write_bytes(self._key(message.id), self._encode(record), if_match=etag)
        except (PreconditionFailedError, KeyNotFoundError) as exc:
            raise MessageLostError(f"message {message.id} is no longer ours") from exc
        return self._message(record)

    def delete(self, message: ReceivedMessage) -> bool:
        owned = self._owned(message)
        if owned is None:
            return False
        _, etag = owned
        try:
            return self._storage.delete(self._key(message.id), if_match=etag)
        except (PreconditionFailedError, KeyNotFoundError):
            return False

    def dead_letter(self, message: ReceivedMessage) -> None:
        owned = self._owned(message)
        if owned is None:
            raise MessageLostError(f"message {message.id} is no longer ours")
        record, _ = owned
        record["pop_receipt"] = None
        self._storage.write_bytes(self._key(message.id, poison=True), self._encode(record))
        self.delete(message)

    def visible_count(self) -> int:
        now = self._clock()
        count = 0
        for key in self._records(self._prefix):
            try:
                record = self._decode(key, self._storage.read_bytes(key))
            except KeyNotFoundError:
                continue
            if float(record["visible_at"]) <= now:
                count += 1
                if count >= MAX_BATCH:
                    break
        return count

    def poison_messages(self) -> list[str]:
        """Contents of the poison queue (oldest first), for diagnostics and tests."""
        contents: list[str] = []
        for key in self._records(self._poison_prefix):
            record = self._decode(key, self._storage.read_bytes(key))
            contents.append(str(record["content"]))
        return contents

    def pending_count(self) -> int:
        """All messages in the queue, visible or not."""
        return len(self._records(self._prefix))
