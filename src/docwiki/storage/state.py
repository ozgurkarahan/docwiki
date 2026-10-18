"""Per-source state shards ``work/state/sources/<source_id>.json`` with ETag If-Match writes."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime

from pydantic import ValidationError

from docwiki.contracts.enums import StageStatus
from docwiki.contracts.layout import StorageKeys, source_state_key
from docwiki.contracts.state import SourceState, StageState
from docwiki.contracts.storage import (
    KeyNotFoundError,
    PreconditionFailedError,
    Storage,
    StorageError,
)

__all__ = ["StateConflictError", "StateStore", "with_stage"]


class StateConflictError(StorageError):
    """A state shard kept changing under us (too many If-Match conflicts)."""


def with_stage(
    state: SourceState,
    stage: str,
    status: StageStatus,
    *,
    now: datetime,
    cache_key: str | None = None,
    error: str | None = None,
    clear_error: bool = False,
    retryable: bool = False,
    attempts: int = 0,
) -> SourceState:
    """``state`` with ``stages[stage]`` set; the same object when nothing changes.

    ``retryable`` and ``attempts`` describe a quarantine (see :class:`StageState`).
    """
    current = state.stages.get(stage)  # type: ignore[call-overload]
    last_error = state.last_error
    if error is not None:
        last_error = f"{stage}: {error}"
    elif clear_error:
        last_error = None
    if (
        current is not None
        and current.status == status
        and current.cache_key == cache_key
        and current.error == error
        and current.retryable == retryable
        and current.attempts == attempts
        and last_error == state.last_error
    ):
        return state
    stages = dict(state.stages)
    stages[stage] = StageState(  # type: ignore[index]
        status=status,
        cache_key=cache_key,
        error=error,
        updated_at=now,
        retryable=retryable,
        attempts=attempts,
    )
    return state.model_copy(update={"stages": stages, "last_error": last_error, "updated_at": now})


class StateStore:
    """Reads and writes source state shards; writes are conditional on the ETag."""

    def __init__(self, storage: Storage, *, retries: int = 8) -> None:
        self.storage = storage
        self.retries = retries

    def load_all(self) -> dict[str, tuple[SourceState, str]]:
        """Every shard with its ETag, keyed by ``source_id`` (unreadable shards are skipped)."""
        shards: dict[str, tuple[SourceState, str]] = {}
        for key in self.storage.list(StorageKeys.SOURCE_STATE_DIR + "/"):
            if not key.endswith(".json"):
                continue
            try:
                data, etag = self.storage.read_with_etag(key)
                state = SourceState.from_json(data)
            except KeyNotFoundError:
                continue
            except ValidationError as exc:
                raise StorageError(f"state shard {key} is invalid: {exc}") from exc
            shards[state.source_id] = (state, etag)
        return shards

    def read(self, source_id: str) -> tuple[SourceState, str] | None:
        try:
            data, etag = self.storage.read_with_etag(source_state_key(source_id))
        except KeyNotFoundError:
            return None
        return SourceState.from_json(data), etag

    def write(self, state: SourceState, *, etag: str | None) -> str:
        """Create (``etag=None``) or replace (If-Match) a shard; raises on conflicts."""
        data = state.to_json().encode("utf-8")
        key = source_state_key(state.source_id)
        if etag is None:
            return self.storage.write_bytes(key, data, if_none_match="*")
        return self.storage.write_bytes(key, data, if_match=etag)

    def update(
        self,
        source_id: str,
        mutate: Callable[[SourceState | None], SourceState | None],
    ) -> SourceState | None:
        """Read-modify-write with If-Match; retried with fresh state on conflicts.

        ``mutate`` receives the current shard (or ``None``) and returns the new shard, the same
        object (no write) or ``None`` (no write).
        """
        for _ in range(self.retries):
            current = self.read(source_id)
            state, etag = current if current is not None else (None, None)
            new = mutate(state)
            if new is None or new is state:
                return state
            try:
                self.write(new, etag=etag)
            except PreconditionFailedError:
                continue
            return new
        raise StateConflictError(f"state shard of {source_id} changed too often; giving up")
