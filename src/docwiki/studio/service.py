"""What the Studio shows: the documents in ``raw/``, their pipeline state, the runs, the queue and
the ingest job; and the two writes it makes: an upload into ``raw/`` and a reviewed Researcher
answer filed into the answers inbox ``work/inbox/queries/`` (:mod:`docwiki.studio.filing`).

An upload is all it takes: Event Grid turns the new blob into a queue message and the ingest job
compiles it, exactly as for any other file dropped into ``raw/``; a filed answer wakes the job the
same way. The Studio never runs the pipeline itself.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.layout import ReleaseFiles, StorageKeys, release_prefix
from docwiki.contracts.state import SourceState
from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, Storage
from docwiki.mcp.tools_ops import SOURCE_STATUSES, OpsTools, overall_status
from docwiki.mcp.workstore import WorkStore
from docwiki.release.publish import read_current_pointer
from docwiki.studio.config import StudioConfig
from docwiki.studio.filing import AnswerFiler
from docwiki.studio.paths import check_upload_path, wiki_link

__all__ = [
    "DOCUMENT_STATUSES",
    "RawBlob",
    "StudioService",
    "UploadConflictError",
    "UploadError",
    "UploadQuotaError",
    "UploadTooLargeError",
]

log = logging.getLogger("docwiki.studio")

DOCUMENT_STATUSES = ("new", *SOURCE_STATUSES)
"""``new``: in ``raw/`` but not seen by the pipeline yet; then the pipeline's own statuses."""
RUN_LIMIT = 10
CACHE_TTL_S = 4.0


class UploadError(ValueError):
    """An upload the Studio refuses (HTTP 400)."""


class UploadTooLargeError(UploadError):
    """HTTP 413."""


class UploadConflictError(UploadError):
    """The file exists and ``replace`` was not requested (HTTP 409)."""


class UploadQuotaError(RuntimeError):
    """The daily upload allowance is used up (HTTP 429)."""


@dataclass(frozen=True)
class RawBlob:
    path: str
    """Path relative to ``raw/``."""
    size: int | None = None
    modified: datetime | None = None


RawLister = Callable[[], list[RawBlob]]
QueueDepth = Callable[[], int | None]


def _iso(value: datetime | None) -> str | None:
    return value.isoformat().replace("+00:00", "Z") if value else None


def _clip(value: str | None, limit: int = 300) -> str | None:
    if value is None:
        return None
    return value if len(value) <= limit else value[: limit - 1] + "…"


class StudioService:
    """Reads for the dashboard and the upload, over the shared :class:`Storage`."""

    def __init__(
        self,
        storage: Storage,
        config: StudioConfig,
        *,
        list_raw: RawLister | None = None,
        queue_depth: QueueDepth | None = None,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self.storage = storage
        self.config = config
        self._list_raw = list_raw or self._list_raw_from_storage
        self._queue_depth = queue_depth
        self._clock = clock
        self._today = today
        self._uploads: dict[date, int] = {}
        self._lock = threading.Lock()
        self._catalog: tuple[str, Catalog] | None = None
        self._cache: dict[str, tuple[float, Any]] = {}
        self.filing = AnswerFiler(storage, daily_filings=config.daily_filings, today=today)

    # -- helpers -----------------------------------------------------------------------------

    def _cached(self, key: str, factory: Callable[[], Any]) -> Any:
        now = self._clock()
        with self._lock:
            hit = self._cache.get(key)
            if hit is not None and now - hit[0] < CACHE_TTL_S:
                return hit[1]
        value = factory()
        with self._lock:
            self._cache[key] = (self._clock(), value)
        return value

    def invalidate(self) -> None:
        with self._lock:
            self._cache.clear()

    def _list_raw_from_storage(self) -> list[RawBlob]:
        """``raw/`` from the storage (Azure uses :func:`azure_raw_lister` for sizes and dates;
        a folder storage gives them through its files)."""
        prefix = StorageKeys.RAW + "/"
        path_for = getattr(self.storage, "path_for", None)
        blobs: list[RawBlob] = []
        for key in self.storage.list(prefix):
            size: int | None = None
            modified: datetime | None = None
            if callable(path_for):
                try:
                    stat = path_for(key).stat()
                    size, modified = stat.st_size, datetime.fromtimestamp(stat.st_mtime, UTC)
                except (OSError, ValueError):
                    pass
            blobs.append(RawBlob(path=key[len(prefix) :], size=size, modified=modified))
        return blobs

    def _current_catalog(self) -> tuple[Any, Catalog | None]:
        """``(pointer, catalog)`` of the served release (the catalog is cached per release)."""
        current = read_current_pointer(self.storage)
        if current is None:
            return None, None
        pointer = current[0]
        cached = self._catalog
        if cached is not None and cached[0] == pointer.release_id:
            return pointer, cached[1]
        key = release_prefix(pointer.release_id) + ReleaseFiles.CATALOG
        try:
            catalog = Catalog.from_json(self.storage.read_bytes(key))
        except (KeyNotFoundError, ValueError):
            log.warning("no readable catalog for release %s", pointer.release_id)
            return pointer, None
        self._catalog = (pointer.release_id, catalog)
        return pointer, catalog

    # -- documents ---------------------------------------------------------------------------

    def documents(self) -> dict[str, Any]:
        return self._cached("documents", self._documents)

    def _documents(self) -> dict[str, Any]:
        blobs = self._list_raw()
        states, broken = WorkStore(self.storage).source_states()
        by_path: dict[str, SourceState] = {state.raw_path: state for state in states}
        _pointer, catalog = self._current_catalog()
        pages = catalog.page_by_id() if catalog else {}
        in_release = {source.source_id for source in catalog.sources} if catalog else set()
        rows: list[dict[str, Any]] = []
        listed: set[str] = set()
        for blob in blobs:
            listed.add(blob.path)
            rows.append(self._row(blob, by_path.get(blob.path), pages, in_release))
        for path, state in by_path.items():
            if path not in listed and state.deleted:
                rows.append(self._row(RawBlob(path=path), state, pages, in_release))
        rows.sort(key=lambda row: (DOCUMENT_STATUSES.index(row["status"]), row["path"].lower()))
        counts = Counter(row["status"] for row in rows)
        return {
            "documents": rows,
            "counts": {status: counts.get(status, 0) for status in DOCUMENT_STATUSES},
            "total": len(rows),
            "unreadable_states": len(broken),
        }

    def _row(
        self,
        blob: RawBlob,
        state: SourceState | None,
        pages: dict[str, Any],
        in_release: set[str],
    ) -> dict[str, Any]:
        if state is None:
            status, stage = "new", None
            try:
                source_id: str | None = source_id_for(blob.path)
            except ValueError:
                source_id = None
        else:
            status, stage = overall_status(state)
            source_id = state.source_id
        page = pages.get(source_id) if source_id else None
        return {
            "path": blob.path,
            "size": blob.size if blob.size is not None else (state.size if state else None),
            "modified": _iso(blob.modified) or (_iso(state.updated_at) if state else None),
            "status": status,
            "stage": stage,
            "source_id": source_id,
            "sensitivity": state.sensitivity if state else None,
            "in_release": bool(source_id and source_id in in_release),
            "wiki_url": wiki_link(self.config.wiki_url, page.path) if page else None,
            "last_error": _clip(state.last_error) if state else None,
        }

    def uploads_left(self) -> int:
        return max(self.config.daily_uploads - self._uploads.get(self._today(), 0), 0)

    def upload(self, path: str, data: bytes, *, replace: bool = False) -> dict[str, Any]:
        """Write ``raw/<path>``; the pipeline picks it up through Event Grid."""
        try:
            rel = check_upload_path(path)
        except ValueError as exc:
            raise UploadError(str(exc)) from exc
        if not data:
            raise UploadError("the file is empty")
        if len(data) > self.config.max_upload_bytes:
            raise UploadTooLargeError(
                f"the file is larger than {self.config.max_upload_bytes // (1024 * 1024)} MB"
            )
        if self.uploads_left() <= 0:
            raise UploadQuotaError(
                f"the daily allowance of {self.config.daily_uploads} uploads is used up "
                "(each upload can start a paid pipeline run)"
            )
        key = f"{StorageKeys.RAW}/{rel}"
        existed = self.storage.exists(key)
        if existed and not replace:
            raise UploadConflictError(f"{rel} already exists; upload it again to replace it")
        try:
            if replace:
                self.storage.write_bytes(key, data)
            else:
                self.storage.write_bytes(key, data, if_none_match="*")
        except PreconditionFailedError as exc:
            raise UploadConflictError(f"{rel} already exists") from exc
        today = self._today()
        self._uploads = {today: self._uploads.get(today, 0) + 1}
        self.invalidate()
        log.info("uploaded raw/%s (%d bytes, replaced=%s)", rel, len(data), existed)
        return {
            "path": rel,
            "size": len(data),
            "replaced": existed,
            "source_id": source_id_for(rel),
        }

    # -- pipeline ----------------------------------------------------------------------------

    def pipeline(self) -> dict[str, Any]:
        return self._cached("pipeline", self._pipeline)

    def _pipeline(self) -> dict[str, Any]:
        pointer, catalog = self._current_catalog()
        release: dict[str, Any] | None = None
        if pointer is not None:
            release = {
                "release_id": pointer.release_id,
                "published_at": _iso(pointer.created_at),
                "audience": pointer.audience,
                "sources": len(catalog.sources) if catalog else None,
                "pages": len(catalog.pages) if catalog else None,
                "wiki_url": self.config.wiki_url,
            }
        store = WorkStore(self.storage)
        runs: list[dict[str, Any]] = []
        for run_id in reversed(store.run_ids()[-RUN_LIMIT:]):
            try:
                report = store.run_report(run_id)
            except ValueError:
                continue
            if report is None:
                continue
            runs.append(self._run_view(OpsTools._run_summary(report), release))
        queued: int | None = None
        if self._queue_depth is not None:
            try:
                queued = self._queue_depth()
            except Exception as exc:  # the dashboard degrades, it does not fail
                log.warning("queue depth unavailable: %s", exc)
        return {"release": release, "runs": runs, "queued": queued}

    @staticmethod
    def _run_view(summary: dict[str, Any], release: dict[str, Any] | None) -> dict[str, Any]:
        cost = summary.get("cost") or {}
        gates = summary.get("gates") or {}
        return {
            "run_id": summary["run_id"],
            "kind": summary["kind"],
            "requested_by": summary["requested_by"],
            "status": summary["status"],
            "started_at": summary["started_at"],
            "finished_at": summary.get("finished_at"),
            "release_id": summary.get("release_id"),
            "is_current": bool(release and summary.get("release_id") == release.get("release_id")),
            "counts": summary.get("counts") or {},
            "stages": [
                {
                    "stage": stage["stage"],
                    "status": stage["status"],
                    "duration_s": stage.get("duration_s"),
                    "items": stage.get("items"),
                    "cache_hits": stage.get("cache_hits"),
                    "failures": stage.get("failures"),
                }
                for stage in summary.get("stages") or []
            ],
            "gates": {
                "summary": gates.get("summary") or {},
                "not_passing": [
                    {key: gate.get(key) for key in ("gate", "name", "status", "blocking")}
                    for gate in gates.get("not_passing") or []
                ],
            },
            "cost": {
                "currency": cost.get("currency"),
                "total": cost.get("total_cost"),
                "duration_s": cost.get("duration_s"),
            },
            "errors_total": summary.get("errors_total", 0),
            "warnings_total": summary.get("warnings_total", 0),
        }

    # -- health ------------------------------------------------------------------------------

    def storage_ok(self) -> bool:
        try:
            read_current_pointer(self.storage)
            self.storage.list(StorageKeys.SOURCE_STATE_DIR + "/")
        except Exception as exc:
            log.warning("storage check failed: %s", exc)
            return False
        return True
