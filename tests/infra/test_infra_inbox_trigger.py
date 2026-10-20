"""File to wiki (ADR 0007): a page written to the answers inbox wakes the ingest job.

The Bicep subscription ``inbox-to-ingest`` sends Event Grid's BlobCreated events of
``work/inbox/queries/`` to the ``ingest`` queue, exactly like ``raw-to-ingest`` does for uploads;
the worker accepts such an event as an ingest request (the run is level-triggered: the pipeline
reads the inbox itself).
"""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path

import pytest
from infra_testkit import REPO_ROOT, RolePermissions, bicep_multiline_var, role_allows

from docwiki.answers.inbox import INBOX_PREFIX
from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.storage import FolderStorage
from docwiki.orchestration.runner import drain_queue, request_from_messages
from docwiki.storage.queue import StorageQueue

STORAGE = REPO_ROOT / "infra" / "modules" / "storage.bicep"
INBOX = INBOX_PREFIX.removeprefix(StorageKeys.WORK + "/")


def _resource(text: str, name: str) -> str:
    return text[text.index(f"resource {name} ") :].split("\n}\n", 1)[0]


def _property(block: str, key: str) -> str:
    """The value of ``key:`` in a resource declaration (a balanced ``{…}``/``[…]`` or a line)."""
    start = re.search(rf"^\s*{key}: ", block, re.MULTILINE)
    assert start, key
    rest = block[start.end() :]
    if rest[0] not in "{[":
        return rest.split("\n", 1)[0]
    depth = 0
    for index, char in enumerate(rest):
        depth += {"{": 1, "[": 1, "}": -1, "]": -1}.get(char, 0)
        if depth == 0:
            return rest[: index + 1]
    raise AssertionError(f"unbalanced {key}")


def test_inbox_subscription_mirrors_the_upload_trigger() -> None:
    storage = STORAGE.read_text(encoding="utf-8")
    assert "var workContainerName = 'work'" in storage
    inbox = _resource(storage, "inboxToIngest")
    raw = _resource(storage, "rawToIngest")
    assert re.match(
        r"resource inboxToIngest 'Microsoft\.EventGrid/systemTopics/eventSubscriptions@[^']+' "
        r"= if \(!networkPerimeter\) \{",
        inbox,
    )
    assert "parent: systemTopic" in inbox and "name: 'inbox-to-ingest'" in inbox
    # Creations only: the job deletes consumed items and must not wake itself.
    assert re.findall(r"'(Microsoft\.Storage\.\w+)'", _property(inbox, "includedEventTypes")) == [
        "Microsoft.Storage.BlobCreated"
    ]
    assert _property(inbox, "subjectBeginsWith") == (
        f"'/blobServices/default/containers/${{workContainerName}}/blobs/{INBOX}'"
    )
    # Same queue, same managed-identity delivery and retry policy as the upload trigger.
    for key in ("eventDeliverySchema", "deliveryWithResourceIdentity", "retryPolicy"):
        assert _property(inbox, key) == _property(raw, key), key
    assert "queueName: ingestQueue.name" in inbox and "resourceId: storage.id" in inbox
    depends = _property(inbox, "dependsOn")
    assert "eventGridQueueSender" in depends and "rawToIngest" in depends


def test_the_studio_files_only_where_the_trigger_listens() -> None:
    """The Studio's work/ role writes and creates blobs only under the prefix that
    ``inbox-to-ingest`` watches, so its filings wake the job; it never deletes or moves one, and
    cannot delete or rewrite the container that holds the inbox and the job's state."""
    storage = STORAGE.read_text(encoding="utf-8")
    role = RolePermissions.from_bicep(_resource(storage, "studioInboxWriterRole"))
    condition = bicep_multiline_var(storage, "studioWorkInboxCondition")
    assert _property(_resource(storage, "inboxToIngest"), "subjectBeginsWith").endswith(
        f"/blobs/{INBOX}'"
    )
    filing = f"{INBOX}2026-03-02-window-delivery.md"
    rejected = "inbox/rejected/2026-03-02-window-delivery.md"
    for action in ("blobs/write", "blobs/add/action"):
        assert role_allows(role, action, condition=condition, path=filing, container="work")
        assert not role_allows(role, action, condition=condition, path=rejected, container="work")
    for action in ("blobs/delete", "blobs/move/action", "containers/delete", "containers/write"):
        assert not role_allows(role, action, condition=condition, path=filing, container="work")


@pytest.mark.parametrize("encoding", ["json", "base64"])
def test_an_inbox_event_wakes_an_ingest_run(tmp_path: Path, encoding: str) -> None:
    blob = f"{INBOX}2026-03-02-when-are-the-windows-of-the-extension-delivered.md"
    event = {
        "subject": f"/blobServices/default/containers/work/blobs/{blob}",
        "eventType": "Microsoft.Storage.BlobCreated",
        "id": "evt-inbox-1",
        "eventTime": "2026-03-02T09:15:00Z",
        "data": {"api": "PutBlob", "contentType": "application/octet-stream", "blobType": "Block"},
        "dataVersion": "",
        "metadataVersion": "1",
    }
    body = json.dumps(event)
    queue = StorageQueue(FolderStorage(tmp_path, fsync=False))
    queue.send(base64.b64encode(body.encode()).decode() if encoding == "base64" else body)
    drained = drain_queue(queue)
    assert (drained.poisoned, drained.invalid) == (0, 0), "the worker must not poison it"
    ((_, message),) = drained.messages
    assert (message.kind, message.requested_by) == ("ingest", "event")
    assert message.hints == {"event_type": "Microsoft.Storage.BlobCreated", "blob": blob}
    assert not message.scope.source_ids and message.scope.prefix is None, "the whole inbox"
    request = request_from_messages([message])
    assert (request.kind, request.requested_by, request.messages) == ("ingest", "event", 1)
