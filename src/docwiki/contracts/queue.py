"""Run-control queue message ``docwiki.ingest/v1`` (architecture §4) and Event Grid adapter."""

# Pydantic copies mutable defaults per instance, so `= []` / `= {}` field defaults are safe.
# ruff: noqa: RUF012

from __future__ import annotations

import base64
import binascii
import json
from datetime import UTC, datetime
from typing import Annotated, Any, Literal, Self

from pydantic import Field, model_validator

from docwiki.contracts._base import ContractModel, NonEmptyStr, UtcDateTime
from docwiki.contracts.enums import QueueKind, RequestedBy
from docwiki.contracts.ids import SOURCE_ID_RE

__all__ = ["QUEUE_SCHEMA", "QueueMessage", "QueueScope", "parse_queue_message"]

QUEUE_SCHEMA = "docwiki.ingest/v1"
SourceId = Annotated[str, Field(pattern=SOURCE_ID_RE.pattern)]


class QueueScope(ContractModel):
    """Optional narrowing: explicit sources and/or a raw path prefix (``None`` = everything)."""

    source_ids: list[SourceId] = []
    prefix: str | None = None


class QueueMessage(ContractModel):
    """Wake-up message for the ingest job; ``hints`` may carry ``operator_notes`` (reviewed)."""

    schema_version: Literal["docwiki.ingest/v1"] = Field(QUEUE_SCHEMA, alias="schema")
    kind: QueueKind
    scope: QueueScope = Field(default_factory=QueueScope)
    hints: dict[str, str] = {}
    requested_by: RequestedBy
    idempotency_key: NonEmptyStr
    created_at: UtcDateTime

    @model_validator(mode="after")
    def _recompile_scope(self) -> Self:
        if self.kind == "recompile" and not self.scope.source_ids:
            raise ValueError("recompile messages need scope.source_ids")
        return self

    def to_body(self) -> str:
        """Compact JSON body for the queue (UTF-8 text)."""
        return self.to_json(indent=None)


_EVENT_TYPES = ("Microsoft.Storage.BlobCreated", "Microsoft.Storage.BlobDeleted")


def _decode(body: str | bytes) -> Any:
    raw = body.decode("utf-8") if isinstance(body, bytes) else body
    text = raw.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    try:
        decoded = base64.b64decode(text, validate=True).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError) as exc:
        raise ValueError("queue message is neither JSON nor base64-encoded JSON") from exc
    try:
        return json.loads(decoded)
    except json.JSONDecodeError as exc:
        raise ValueError("queue message is not valid JSON") from exc


def _blob_name(subject: str) -> str | None:
    marker = "/blobs/"
    return subject.split(marker, 1)[1] if marker in subject else None


def _from_event(event: dict[str, Any]) -> QueueMessage:
    event_type = event.get("eventType") or event.get("type")
    if event_type not in _EVENT_TYPES:
        raise ValueError(f"unsupported event type: {event_type!r}")
    event_id = event.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError("event without id")
    stamp = event.get("eventTime") or event.get("time")
    created = (
        datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        if isinstance(stamp, str)
        else datetime.now(UTC)
    )
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    hints = {"event_type": event_type}
    blob = _blob_name(str(event.get("subject", "")))
    if blob:
        hints["blob"] = blob
    return QueueMessage(
        kind="ingest",
        requested_by="event",
        idempotency_key=f"event:{event_id}",
        created_at=created.replace(microsecond=0),
        hints=hints,
    )


def parse_queue_message(body: str | bytes) -> QueueMessage:
    """Parse a queue body: native ``docwiki.ingest/v1`` JSON, or an Event Grid / CloudEvents
    blob event (single event or a one-element list), optionally base64-encoded.

    Event Grid events become ``kind=ingest, requested_by=event`` with an empty scope: the job is
    level-triggered and diffs the whole ``raw/`` container anyway.
    """
    data = _decode(body)
    if isinstance(data, list):
        if len(data) != 1:
            raise ValueError("expected exactly one event per queue message")
        data = data[0]
    if not isinstance(data, dict):
        raise ValueError("queue message must be a JSON object")
    if data.get("schema") == QUEUE_SCHEMA:
        return QueueMessage.model_validate_json(json.dumps(data))
    if "eventType" in data or ("specversion" in data and "type" in data):
        return _from_event(data)
    raise ValueError("unknown queue message schema")
