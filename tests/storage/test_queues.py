"""Work queues: Storage-backed (local mode) and Azure Storage Queue (fake SDK client)."""

from __future__ import annotations

from pathlib import Path

import pytest
from fake_azure import Clock, FakeQueueClient

from docwiki.contracts.storage import FolderStorage
from docwiki.storage.queue import (
    AzureStorageQueue,
    MessageLostError,
    QueueAuthorizationError,
    StorageQueue,
    WorkQueue,
)


@pytest.fixture(params=["storage", "azure"])
def queue_and_clock(request, tmp_path: Path) -> tuple[WorkQueue, Clock, list[str]]:
    clock = Clock()
    if request.param == "storage":
        storage = FolderStorage(tmp_path / "store", fsync=False)
        queue = StorageQueue(storage, clock=clock)
        return queue, clock, []
    main, poison = FakeQueueClient(clock), FakeQueueClient(clock)
    azure = AzureStorageQueue(queue_client=main, poison_client=poison)
    return azure, clock, poison.sent


def _poisoned(queue: WorkQueue, recorded: list[str]) -> list[str]:
    if isinstance(queue, StorageQueue):
        return queue.poison_messages()
    return recorded


def test_receive_hides_messages_until_their_visibility_timeout(queue_and_clock):
    queue, clock, _ = queue_and_clock
    queue.send("one")
    queue.send("two")
    received = queue.receive(max_messages=32, visibility_timeout_s=30)
    assert sorted(message.content for message in received) == ["one", "two"]
    assert all(message.dequeue_count == 1 for message in received)
    assert queue.receive(visibility_timeout_s=30) == []
    assert queue.visible_count() == 0
    clock.now += 31
    again = queue.receive(visibility_timeout_s=30)
    assert {message.dequeue_count for message in again} == {2}
    assert queue.visible_count() == 0


def test_renew_rotates_the_pop_receipt_and_stale_receipts_lose(queue_and_clock):
    queue, clock, _ = queue_and_clock
    queue.send("work")
    (message,) = queue.receive(visibility_timeout_s=30)
    renewed = queue.renew(message, 60)
    assert renewed.pop_receipt != message.pop_receipt
    clock.now += 45
    assert queue.receive(visibility_timeout_s=30) == [], "the renewal extended the timeout"
    assert queue.delete(message) is False, "the old receipt is stale"
    with pytest.raises(MessageLostError):
        queue.renew(message, 60)
    assert queue.delete(renewed) is True
    assert queue.delete(renewed) is False


def test_message_redelivered_to_someone_else_is_lost_for_us(queue_and_clock):
    queue, clock, _ = queue_and_clock
    queue.send("work")
    (first,) = queue.receive(visibility_timeout_s=10)
    clock.now += 11
    (second,) = queue.receive(visibility_timeout_s=10)
    assert second.dequeue_count == 2
    assert queue.delete(first) is False
    assert queue.delete(second) is True


def test_dead_letter_moves_the_message_to_the_poison_queue(queue_and_clock):
    queue, _, recorded = queue_and_clock
    queue.send("poison me")
    (message,) = queue.receive(visibility_timeout_s=30)
    queue.dead_letter(message)
    assert _poisoned(queue, recorded) == ["poison me"]
    assert queue.visible_count() == 0
    assert queue.receive(visibility_timeout_s=30) == []


def test_storage_queue_send_with_delay(tmp_path: Path):
    clock = Clock()
    queue = StorageQueue(FolderStorage(tmp_path / "s", fsync=False), clock=clock)
    queue.send("later", visibility_timeout_s=60)
    assert queue.visible_count() == 0
    assert queue.pending_count() == 1
    clock.now += 61
    assert queue.visible_count() == 1


def test_storage_queue_accepts_bare_messages_of_other_producers(tmp_path: Path):
    clock = Clock()
    storage = FolderStorage(tmp_path / "s", fsync=False)
    bare = (
        '{\n  "schema": "docwiki.ingest/v1",\n  "kind": "ingest",\n'
        '  "created_at": "2026-02-01T00:00:00Z"\n}\n'
    )
    storage.write_bytes("work/queue/20260201T000000Z-0123456789ab.json", bare.encode())
    storage.write_bytes("work/queue/20260201T000001Z-garbage.json", b"not json")
    queue = StorageQueue(storage, clock=clock)
    assert queue.visible_count() == 2
    first, second = queue.receive(visibility_timeout_s=30)
    assert first.id == "20260201T000000Z-0123456789ab" and first.dequeue_count == 1
    assert first.content == bare.strip() and first.inserted_at is not None
    assert first.inserted_at.isoformat().startswith("2026-02-01T00:00:00")
    assert second.content == "not json"
    assert queue.visible_count() == 0 and queue.receive(visibility_timeout_s=30) == []
    renewed = queue.renew(first, 30)
    assert queue.delete(renewed) and not queue.delete(first)
    queue.dead_letter(second)
    assert queue.pending_count() == 0 and queue.poison_messages() == ["not json"]
    clock.now += 31
    assert queue.receive() == []


def test_azure_queue_requires_clients_or_an_account():
    with pytest.raises(ValueError):
        AzureStorageQueue()


def test_azure_queue_renewal_refused_by_rbac_is_a_configuration_error():
    clock = Clock()
    main = FakeQueueClient(clock)
    queue = AzureStorageQueue(queue_client=main, poison_client=FakeQueueClient(clock))
    queue.send("work")
    (message,) = queue.receive(visibility_timeout_s=30)
    main.deny_updates = True
    with pytest.raises(QueueAuthorizationError, match="HTTP 403") as refused:
        queue.renew(message, 60)
    assert refused.value.status_code == 403
    assert "Storage Queue Data Contributor" in str(refused.value)
    main.deny_updates = False
    assert queue.delete(message) is True, "the receipt is still ours"
    with pytest.raises(MessageLostError):
        queue.renew(message, 60)
