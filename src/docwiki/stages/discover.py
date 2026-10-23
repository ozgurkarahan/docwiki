"""Stage 1 — ``discover``: diff ``raw/`` against the state shards (pipeline §1, architecture §4–5).

Lists the raw container, hashes new or modified files (SHA-256 of the bytes), writes the state
shards with ETag ``If-Match`` and returns the work plan: new / changed / deleted / unchanged
sources, explicit recompile scopes, preliminary sensitivity (path rules of the domain pack) and
preliminary revision groups (document numbers and revisions parsed from file names). Deleted raw
files become tombstones. The pipeline refines sensitivity and supersession once documents are
classified (:func:`resolve_supersession`).

A raw file is re-read only when its storage ETag changed since the last run (the shard keeps a
marker of the ETag in ``stages.discover.cache_key``), so unchanged Blob inputs are never
downloaded again.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, Literal

from docwiki.contracts._base import sha256_bytes, sha256_hex
from docwiki.contracts.ids import normalize_raw_path, source_id_for
from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.state import SourceState, StageState
from docwiki.contracts.storage import KeyNotFoundError, Storage
from docwiki.domain.models import DomainPack
from docwiki.domain.rules import (
    order_revisions,
    parse_doc_number,
    parse_revision,
    revision_rank,
    scope_axes,
    sensitivity_for,
    supersession_pairs,
)
from docwiki.storage.state import StateStore

__all__ = [
    "MEDIA_TYPES",
    "STAGE_VERSION",
    "Change",
    "PlanItem",
    "SkippedFile",
    "SupersessionRecord",
    "WorkPlan",
    "discover",
    "etag_marker",
    "media_type_for",
    "resolve_supersession",
    "revalidate_state",
]

STAGE_VERSION = "1"
Change = Literal["new", "changed", "unchanged", "deleted"]

MEDIA_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".csv": "text/csv",
    ".eml": "message/rfc822",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".vtt": "text/vtt",
    ".md": "text/markdown",
    ".txt": "text/plain",
}
"""Input formats of spec goal G1, by file extension."""

RAW_PREFIX = StorageKeys.RAW + "/"


def media_type_for(path: str) -> str | None:
    """Media type of a supported input file, else ``None``."""
    return MEDIA_TYPES.get(PurePosixPath(path).suffix.lower())


def etag_marker(etag: str) -> str:
    """64-hex marker of a raw ETag, stored as ``stages.discover.cache_key``."""
    return sha256_hex(("raw-etag:" + etag).encode("utf-8"))


def revalidate_state(state: SourceState, **updates: Any) -> SourceState:
    """A validated copy of ``state`` with ``updates`` (keeps the contract invariants)."""
    data = state.model_dump(by_alias=True)
    data.update(updates)
    return SourceState.model_validate(data)


@dataclass(frozen=True)
class SkippedFile:
    raw_path: str
    reason: str


@dataclass
class PlanItem:
    """One source of the run."""

    source_id: str
    raw_path: str
    change: Change
    state: SourceState
    media_type: str
    forced: bool = False
    hints: str | None = None

    @property
    def key(self) -> str:
        return RAW_PREFIX + self.raw_path

    @property
    def active(self) -> bool:
        return self.change != "deleted"


@dataclass
class WorkPlan:
    """Result of ``discover``."""

    items: dict[str, PlanItem] = field(default_factory=dict)
    skipped: list[SkippedFile] = field(default_factory=list)
    revision_groups: dict[str, list[str]] = field(default_factory=dict)
    supersedes: list[tuple[str, str]] = field(default_factory=list)
    restricted: bool = False
    notes: list[str] = field(default_factory=list)

    def ids(self, change: Change) -> list[str]:
        return sorted(sid for sid, item in self.items.items() if item.change == change)

    @property
    def new(self) -> list[str]:
        return self.ids("new")

    @property
    def changed(self) -> list[str]:
        return self.ids("changed")

    @property
    def deleted(self) -> list[str]:
        return self.ids("deleted")

    @property
    def unchanged(self) -> list[str]:
        return self.ids("unchanged")

    @property
    def forced(self) -> list[str]:
        return sorted(sid for sid, item in self.items.items() if item.forced and item.active)

    def active_items(self) -> list[PlanItem]:
        return [self.items[sid] for sid in sorted(self.items) if self.items[sid].active]

    @property
    def has_changes(self) -> bool:
        return bool(self.new or self.changed or self.deleted or self.forced)


@dataclass(frozen=True)
class SupersessionRecord:
    """What supersession needs to know about one source."""

    source_id: str
    doc_number: str | None
    revision: str | None
    references: tuple[str, ...] = ()
    scope: str | None = None
    """Revisions and explicit references only connect documents of the same scope (v1.7)."""

    @property
    def key(self) -> str | None:
        """The revision group: the document number, within its scope."""
        if not self.doc_number:
            return None
        return f"{self.scope}/{self.doc_number}" if self.scope else self.doc_number


def resolve_supersession(
    pack: DomainPack, records: Iterable[SupersessionRecord]
) -> tuple[dict[str, list[str]], list[tuple[str, str]]]:
    """Revision groups (document number → sources, oldest first) and ``(newer, older)`` pairs.

    Later revisions of the same document number supersede earlier ones (pack revision order);
    a source whose text declares that it replaces another document number (pack
    ``explicit_reference_regex``) supersedes every source of that number. Revisions outside the
    pack's revision order are ignored; contradictory explicit declarations (A replaces B and B
    replaces A) are dropped.
    """
    items = list(records)
    ranked: list[tuple[str, str | None, str | None]] = []
    for record in items:
        if not record.doc_number or not record.revision:
            continue
        try:
            revision_rank(pack, record.revision)
        except ValueError:
            continue
        ranked.append((record.source_id, record.key, record.revision))
    groups = order_revisions(pack, ranked) if pack.supersession else {}
    pairs = set(supersession_pairs(pack, ranked)) if pack.supersession else set()
    by_number: dict[str, list[str]] = {}
    for record in items:
        if record.key:
            by_number.setdefault(record.key, []).append(record.source_id)
    explicit: set[tuple[str, str]] = set()
    for record in items:
        for number in record.references:
            if number == record.doc_number:
                continue
            target = f"{record.scope}/{number}" if record.scope else number
            for older in by_number.get(target, []):
                if older != record.source_id:
                    explicit.add((record.source_id, older))
    for newer, older in explicit:
        if (older, newer) in explicit or (older, newer) in pairs:
            continue
        pairs.add((newer, older))
    return groups, sorted(pairs)


def _raw_files(storage: Storage, plan: WorkPlan) -> list[tuple[str, str, str]]:
    """``(key, raw_path, source_id)`` of supported files, sorted by path."""
    files: dict[str, tuple[str, str, str]] = {}
    for key in storage.list(RAW_PREFIX):
        rel = key[len(RAW_PREFIX) :]
        if any(part.startswith(".") for part in rel.split("/")):
            continue
        try:
            raw_path = normalize_raw_path(rel)
        except ValueError as exc:
            plan.skipped.append(SkippedFile(rel, f"invalid path: {exc}"))
            continue
        if media_type_for(raw_path) is None:
            plan.skipped.append(SkippedFile(raw_path, "unsupported file type"))
            continue
        source_id = source_id_for(raw_path)
        if source_id in files:
            plan.skipped.append(
                SkippedFile(
                    raw_path,
                    f"same source id as {files[source_id][1]!r} (paths differ only in case)",
                )
            )
            continue
        files[source_id] = (key, raw_path, source_id)
    return sorted(files.values(), key=lambda item: item[1])


def discover(
    storage: Storage,
    pack: DomainPack,
    *,
    now: datetime,
    state_store: StateStore | None = None,
    recompile: Mapping[str, str | None] | None = None,
    only: Iterable[str] | None = None,
    limit: int | None = None,
) -> WorkPlan:
    """Build the work plan and persist the state shards.

    ``recompile`` maps source ids to reviewed operator hints (``None`` for none) and forces
    their recompilation. ``only``/``limit`` restrict the run to some sources (development);
    deletions are not detected in a restricted run.
    """
    store = state_store or StateStore(storage)
    plan = WorkPlan()
    raw_files = _raw_files(storage, plan)
    selected = set(only or ())
    if selected:
        raw_files = [item for item in raw_files if item[2] in selected]
        plan.restricted = True
    if limit is not None:
        raw_files = raw_files[: max(0, limit)]
        plan.restricted = True
    shards = store.load_all()
    seen: set[str] = set()
    for key, raw_path, source_id in raw_files:
        etag = storage.etag(key)
        if etag is None:
            continue
        seen.add(source_id)
        marker = etag_marker(etag)
        shard = shards.get(source_id)
        prior = shard[0] if shard is not None and not shard[0].deleted else None
        media_type = media_type_for(raw_path) or "application/octet-stream"
        discover_stage = StageState(status="done", cache_key=marker, updated_at=now)
        stored_marker = prior.stages.get("discover") if prior is not None else None
        if (
            prior is not None
            and prior.raw_path == raw_path
            and stored_marker is not None
            and stored_marker.cache_key == marker
        ):
            plan.items[source_id] = PlanItem(source_id, raw_path, "unchanged", prior, media_type)
            continue
        try:
            data = storage.read_bytes(key)
        except KeyNotFoundError:
            seen.discard(source_id)
            continue
        content_hash = sha256_bytes(data)
        name = PurePosixPath(raw_path).name
        if prior is not None and prior.content_hash == content_hash:
            stages = dict(prior.stages)
            stages["discover"] = discover_stage
            state = revalidate_state(prior, raw_path=raw_path, stages=stages, updated_at=now)
            change: Change = "unchanged"
        elif prior is not None:
            state = revalidate_state(
                prior,
                raw_path=raw_path,
                content_hash=content_hash,
                size=len(data),
                media_type=media_type,
                sensitivity=sensitivity_for(pack, raw_path, None),
                revision_group=parse_doc_number(pack, name),
                stages={"discover": discover_stage},
                last_error=None,
                updated_at=now,
            )
            change = "changed"
        else:
            state = SourceState(
                source_id=source_id,
                raw_path=raw_path,
                content_hash=content_hash,
                size=len(data),
                media_type=media_type,
                sensitivity=sensitivity_for(pack, raw_path, None),  # type: ignore[arg-type]
                revision_group=parse_doc_number(pack, name),
                stages={"discover": discover_stage},
                first_seen_at=now,
                updated_at=now,
            )
            change = "new"
        stored = _persist(store, state)
        plan.items[source_id] = PlanItem(source_id, raw_path, change, stored, media_type)
    if not plan.restricted:
        for source_id, (state, _) in sorted(shards.items()):
            if source_id in seen or state.deleted:
                continue
            tombstone = revalidate_state(state, deleted=True, deleted_at=now, updated_at=now)
            stored = _persist(store, tombstone)
            plan.items[source_id] = PlanItem(
                source_id,
                state.raw_path,
                "deleted",
                stored,
                media_type_for(state.raw_path) or state.media_type,
            )
    for source_id, hints in sorted((recompile or {}).items()):
        item = plan.items.get(source_id)
        if item is None or not item.active:
            plan.notes.append(f"recompile requested for unknown or deleted source {source_id}")
            continue
        item.forced = True
        item.hints = hints or None
    records = [
        SupersessionRecord(
            item.source_id,
            item.state.revision_group or parse_doc_number(pack, PurePosixPath(item.raw_path).name),
            parse_revision(pack, PurePosixPath(item.raw_path).name),
            scope=scope_axes(pack, item.raw_path).scope,
        )
        for item in plan.active_items()
    ]
    plan.revision_groups, plan.supersedes = resolve_supersession(pack, records)
    return plan


def _persist(store: StateStore, state: SourceState) -> SourceState:
    def mutate(current: SourceState | None) -> SourceState | None:
        if current is not None and current == state:
            return current
        if current is not None:
            return revalidate_state(state, first_seen_at=current.first_seen_at)
        return state

    stored = store.update(state.source_id, mutate)
    return stored if stored is not None else state


def unchanged_since(states: Sequence[SourceState]) -> dict[str, str]:
    """``source_id → content_hash`` of active shards (used for no-op detection)."""
    return {state.source_id: state.content_hash for state in states if not state.deleted}
