"""In-memory fakes of the Azure Blob and Queue SDK clients used by docwiki.storage.

They raise the real ``azure.core`` exception types with the HTTP status and error codes of the
service, so the storage classes are tested against the same failure modes without any network.
"""

from __future__ import annotations

import itertools
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from azure.core import MatchConditions
from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
    ResourceModifiedError,
    ResourceNotFoundError,
)


def error(cls: type[HttpResponseError], status: int, code: str) -> HttpResponseError:
    exc = cls(message=code)
    exc.status_code = status
    exc.error_code = code
    return exc


class Clock:
    def __init__(self) -> None:
        self.now = time.time()

    def __call__(self) -> float:
        return self.now


@dataclass
class _Blob:
    data: bytes
    etag: str
    lease_id: str | None = None
    lease_expires: float = 0.0
    lease_duration: int = 0


class FakeAccount:
    """Containers of blobs with ETags and leases."""

    def __init__(self, clock: Clock, containers: tuple[str, ...] = ("raw", "work", "releases")):
        self.clock = clock
        self.containers: dict[str, dict[str, _Blob]] = {name: {} for name in containers}
        self._etags = itertools.count(1)
        self.calls: list[tuple[str, str, str]] = []

    def etag(self) -> str:
        return f'"0x{next(self._etags):016X}"'

    def leased(self, blob: _Blob) -> bool:
        return blob.lease_id is not None and blob.lease_expires > self.clock()


class FakeServiceClient:
    def __init__(self, account: FakeAccount) -> None:
        self.account = account
        self.closed = False

    def get_container_client(self, name: str) -> FakeContainerClient:
        return FakeContainerClient(self.account, name)

    def close(self) -> None:
        self.closed = True


class FakeContainerClient:
    def __init__(self, account: FakeAccount, name: str) -> None:
        self.account = account
        self.name = name

    def get_blob_client(self, blob: str) -> FakeBlobClient:
        return FakeBlobClient(self.account, self.name, blob)

    def list_blob_names(self, name_starts_with: str | None = None, **_: Any) -> Any:
        if self.name not in self.account.containers:
            raise error(ResourceNotFoundError, 404, "ContainerNotFound")
        prefix = name_starts_with or ""
        return iter(sorted(n for n in self.account.containers[self.name] if n.startswith(prefix)))


class FakeBlobClient:
    def __init__(self, account: FakeAccount, container: str, name: str) -> None:
        self.account = account
        self.container = container
        self.blob_name = name

    def _blobs(self) -> dict[str, _Blob]:
        if self.container not in self.account.containers:
            raise error(ResourceNotFoundError, 404, "ContainerNotFound")
        return self.account.containers[self.container]

    def _get(self) -> _Blob:
        blob = self._blobs().get(self.blob_name)
        if blob is None:
            raise error(ResourceNotFoundError, 404, "BlobNotFound")
        return blob

    def upload_blob(
        self,
        data: bytes,
        overwrite: bool = False,
        etag: str | None = None,
        match_condition: MatchConditions | None = None,
        **_: Any,
    ) -> dict[str, Any]:
        self.account.calls.append(("upload", self.container, self.blob_name))
        blobs = self._blobs()
        current = blobs.get(self.blob_name)
        if current is not None and not overwrite:
            raise error(ResourceExistsError, 409, "BlobAlreadyExists")
        if match_condition == MatchConditions.IfNotModified and (
            current is None or current.etag != etag
        ):
            raise error(ResourceModifiedError, 412, "ConditionNotMet")
        if current is not None and self.account.leased(current):
            raise error(HttpResponseError, 412, "LeaseIdMissing")
        new = _Blob(bytes(data), self.account.etag())
        if current is not None:
            new.lease_id, new.lease_expires = current.lease_id, current.lease_expires
            new.lease_duration = current.lease_duration
        blobs[self.blob_name] = new
        return {"etag": new.etag}

    def download_blob(self, **_: Any) -> Any:
        self.account.calls.append(("download", self.container, self.blob_name))
        blob = self._get()
        return SimpleNamespace(
            readall=lambda: blob.data, properties=SimpleNamespace(etag=blob.etag)
        )

    def get_blob_properties(self, **_: Any) -> Any:
        return SimpleNamespace(etag=self._get().etag)

    def exists(self, **_: Any) -> bool:
        return self.blob_name in self._blobs()

    def delete_blob(
        self,
        delete_snapshots: str | None = None,
        etag: str | None = None,
        match_condition: MatchConditions | None = None,
        **_: Any,
    ) -> None:
        blob = self._get()
        if match_condition == MatchConditions.IfNotModified and blob.etag != etag:
            raise error(ResourceModifiedError, 412, "ConditionNotMet")
        if self.account.leased(blob):
            raise error(HttpResponseError, 412, "LeaseIdMissing")
        del self._blobs()[self.blob_name]


class FakeLeaseClient:
    """Lease operations of the blob service (60 s maximum, ids are opaque)."""

    def __init__(self, blob_client: FakeBlobClient, lease_id: str) -> None:
        self.blob = blob_client
        self.id = lease_id

    def acquire(self, lease_duration: int = -1, **_: Any) -> None:
        assert 15 <= lease_duration <= 60, "Azure only accepts 15-60 s leases"
        blob = self.blob._get()
        if self.blob.account.leased(blob) and blob.lease_id != self.id:
            raise error(ResourceExistsError, 409, "LeaseAlreadyPresent")
        blob.lease_id = self.id
        blob.lease_duration = lease_duration
        blob.lease_expires = self.blob.account.clock() + lease_duration

    def renew(self, **_: Any) -> None:
        blob = self.blob._get()
        if blob.lease_id is None:
            raise error(HttpResponseError, 409, "LeaseNotPresentWithLeaseOperation")
        if blob.lease_id != self.id:
            raise error(HttpResponseError, 409, "LeaseIdMismatchWithLeaseOperation")
        blob.lease_expires = self.blob.account.clock() + blob.lease_duration

    def release(self, **_: Any) -> None:
        blob = self.blob._get()
        if blob.lease_id is None:
            raise error(HttpResponseError, 409, "LeaseNotPresentWithLeaseOperation")
        if blob.lease_id != self.id:
            raise error(HttpResponseError, 409, "LeaseIdMismatchWithLeaseOperation")
        blob.lease_id = None
        blob.lease_expires = 0.0


@dataclass
class _Message:
    id: str
    content: str
    dequeue_count: int
    visible_at: float
    pop_receipt: str | None
    inserted: float


class FakeQueueClient:
    """Visibility timeouts, pop receipts and dequeue counts of a storage queue.

    ``deny_updates`` makes Update Message fail like an identity without
    ``queues/messages/write`` (HTTP 403 AuthorizationPermissionMismatch).
    """

    def __init__(self, clock: Clock) -> None:
        self.clock = clock
        self.messages: dict[str, _Message] = {}
        self.sent: list[str] = []
        self.deny_updates = False

    @staticmethod
    def _view(message: _Message) -> Any:
        return SimpleNamespace(
            id=message.id,
            pop_receipt=message.pop_receipt,
            content=message.content,
            dequeue_count=message.dequeue_count,
            inserted_on=datetime.fromtimestamp(message.inserted, UTC),
            next_visible_on=datetime.fromtimestamp(message.visible_at, UTC),
        )

    def send_message(self, content: str, visibility_timeout: int | None = None, **_: Any) -> Any:
        self.sent.append(content)
        message = _Message(
            id=uuid.uuid4().hex,
            content=content,
            dequeue_count=0,
            visible_at=self.clock() + (visibility_timeout or 0),
            pop_receipt=None,
            inserted=self.clock(),
        )
        self.messages[message.id] = message
        return self._view(message)

    def receive_messages(
        self,
        *,
        messages_per_page: int | None = None,
        visibility_timeout: int | None = None,
        max_messages: int | None = None,
        **_: Any,
    ) -> Any:
        now = self.clock()
        out = []
        for message in list(self.messages.values()):
            if len(out) >= (max_messages or 32):
                break
            if message.visible_at > now:
                continue
            message.dequeue_count += 1
            message.visible_at = now + (visibility_timeout or 30)
            message.pop_receipt = uuid.uuid4().hex
            out.append(self._view(message))
        return iter(out)

    def _owned(self, message_id: str, pop_receipt: str | None) -> _Message:
        message = self.messages.get(message_id)
        if message is None or message.pop_receipt != pop_receipt:
            raise error(HttpResponseError, 404, "MessageNotFound")
        return message

    def update_message(
        self,
        message: str,
        pop_receipt: str | None = None,
        content: object | None = None,
        *,
        visibility_timeout: int | None = None,
        **_: Any,
    ) -> Any:
        if self.deny_updates:
            raise error(HttpResponseError, 403, "AuthorizationPermissionMismatch")
        owned = self._owned(message, pop_receipt)
        owned.pop_receipt = uuid.uuid4().hex
        owned.visible_at = self.clock() + (visibility_timeout or 0)
        return self._view(owned)

    def delete_message(self, message: str, pop_receipt: str | None = None, **_: Any) -> None:
        self._owned(message, pop_receipt)
        del self.messages[message]

    def peek_messages(self, max_messages: int | None = None, **_: Any) -> list[Any]:
        now = self.clock()
        visible = [m for m in self.messages.values() if m.visible_at <= now]
        return [self._view(m) for m in visible[: max_messages or 32]]
