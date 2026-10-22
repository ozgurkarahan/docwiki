"""The process behind the wiki, live (ADR 0009): what ``/api/process`` shows on the
``how-it-works`` page, and the owner's uploads into ``raw/``.

Everyone sees each document's pipeline status, the ingest queue, the current release and the last
runs, read-only. A document whose sensitivity is above the site's audience is listed without its
name, and error details are for the owner only. An upload is all it takes to add a document:
Event Grid turns the new blob into a queue message and the ingest job compiles it, exactly as for
any other file dropped into ``raw/``; the portal never runs the pipeline itself.
"""

from __future__ import annotations

import logging
import re
import threading
import time
import unicodedata
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import quote

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.enums import allowed_for_audience
from docwiki.contracts.formats import SUPPORTED_EXTENSIONS, detect_format
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.layout import ReleaseFiles, StorageKeys, release_prefix
from docwiki.contracts.state import SourceState
from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, Storage
from docwiki.mcp.tools_ops import SOURCE_STATUSES, OpsTools, overall_status
from docwiki.mcp.workstore import WorkStore
from docwiki.release.publish import read_current_pointer

__all__ = [
    "DOCUMENT_STATUSES",
    "MAX_DEPTH",
    "MAX_PATH_CHARS",
    "PathError",
    "ProcessService",
    "RawBlob",
    "UploadConflictError",
    "UploadError",
    "UploadQuotaError",
    "UploadTooLargeError",
    "check_upload_path",
    "site_link",
]

log = logging.getLogger("docwiki.portal.process")

DOCUMENT_STATUSES = ("new", *SOURCE_STATUSES)
"""``new``: in ``raw/`` but not seen by the pipeline yet; then the pipeline's own statuses."""
RUN_LIMIT = 10
CACHE_TTL_S = 4.0
MAX_PATH_CHARS = 200
MAX_DEPTH = 4
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,99}$")
_WIKI_PATH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,254}$")


class PathError(ValueError):
    """A document path the portal refuses."""


class UploadError(ValueError):
    """An upload the portal refuses (HTTP 400)."""


class UploadTooLargeError(UploadError):
    """HTTP 413."""


class UploadConflictError(UploadError):
    """The file exists and ``replace`` was not requested (HTTP 409)."""


class UploadQuotaError(RuntimeError):
    """The daily upload allowance is used up (HTTP 429)."""


def check_upload_path(path: str) -> str:
    """The normalised ``raw/``-relative path of an upload, or :class:`PathError`.

    Accepts at most four segments of letters, digits, spaces and ``._()+-`` (no leading dot, so
    no hidden files the pipeline would skip) and only the file types the pipeline extracts.
    """
    value = unicodedata.normalize("NFC", path or "").strip()
    if not value or len(value) > MAX_PATH_CHARS:
        raise PathError(f"the path must have 1 to {MAX_PATH_CHARS} characters")
    if value.startswith("/") or "\\" in value or "//" in value:
        raise PathError("the path must be relative and use '/' between folders")
    parts = value.split("/")
    if len(parts) > MAX_DEPTH:
        raise PathError(f"the path may have at most {MAX_DEPTH} segments")
    for part in parts:
        if part in (".", "..") or part != part.strip() or part.endswith("."):
            raise PathError(f"invalid path segment {part!r}")
        if not _SEGMENT_RE.match(part):
            raise PathError(
                f"invalid path segment {part!r}: use letters, digits, spaces and ._()+- only"
            )
    if detect_format(value) is None:
        raise PathError("unsupported file type; supported: " + ", ".join(SUPPORTED_EXTENSIONS))
    return value


def site_link(path: str | None) -> str | None:
    """Site path of a release-relative page (``sources/x.md`` → ``/sources/x``).

    Quartz serves ``x/y.md`` at ``x/y`` (``x/index.md`` at ``x/``). Anything that is not a plain
    relative Markdown path gives ``None``.
    """
    if not path:
        return None
    value = path.strip().split("#", 1)[0]
    if not _WIKI_PATH_RE.match(value) or not value.endswith(".md"):
        return None
    if any(part in ("", ".", "..") for part in value.split("/")):
        return None
    page = value[: -len(".md")]
    if page == "index":
        page = ""
    elif page.endswith("/index"):
        page = page[: -len("index")]
    return "/" + quote(page, safe="/-_.")


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


class ProcessService:
    """Reads for the process view and the owner's upload, over the shared :class:`Storage`."""

    def __init__(
        self,
        storage: Storage,
        *,
        max_upload_bytes: int,
        daily_uploads: int,
        list_raw: RawLister | None = None,
        queue_depth: QueueDepth | None = None,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.daily_uploads = daily_uploads
        self._list_raw = list_raw or self._list_raw_from_storage
        self._queue_depth = queue_depth
        self._clock = clock
        self._today = today
        self._uploads: dict[date, int] = {}
        self._lock = threading.Lock()
        self._catalog: tuple[str, Catalog] | None = None
        self._cache: dict[str, tuple[float, Any]] = {}

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
        """``raw/`` from the storage (Azure uses an account listing for sizes and dates; a
        folder storage gives them through its files)."""
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

    # -- the process -------------------------------------------------------------------------

    def process(self, *, owner: bool = False) -> dict[str, Any]:
        """Release, runs, queue and documents; ``owner`` adds the names and errors hidden from
        visitors."""
        view = self._cached("process", self._process)
        documents = (
            view["documents"] if owner else [self._public_row(row) for row in view["documents"]]
        )
        return {**view, "documents": documents}

    def _process(self) -> dict[str, Any]:
        pointer, catalog = self._current_catalog()
        audience = pointer.audience if pointer is not None else "public"
        release: dict[str, Any] | None = None
        if pointer is not None:
            release = {
                "release_id": pointer.release_id,
                "published_at": _iso(pointer.created_at),
                "audience": pointer.audience,
                "sources": len(catalog.sources) if catalog else None,
                "pages": len(catalog.pages) if catalog else None,
            }
        documents = self._documents(catalog, audience)
        counts = Counter(row["status"] for row in documents)
        return {
            "release": release,
            "runs": self._runs(release),
            "queued": self._queued(),
            "documents": documents,
            "counts": {status: counts.get(status, 0) for status in DOCUMENT_STATUSES},
            "total": len(documents),
        }

    def _queued(self) -> int | None:
        if self._queue_depth is None:
            return None
        try:
            return self._queue_depth()
        except Exception as exc:  # the view degrades, it does not fail
            log.warning("queue depth unavailable: %s", exc)
            return None

    def _documents(self, catalog: Catalog | None, audience: str) -> list[dict[str, Any]]:
        blobs = self._list_raw()
        states, _broken = WorkStore(self.storage).source_states()
        by_path: dict[str, SourceState] = {state.raw_path: state for state in states}
        pages = catalog.page_by_id() if catalog else {}
        in_release = {source.source_id for source in catalog.sources} if catalog else set()
        rows: list[dict[str, Any]] = []
        listed: set[str] = set()
        for blob in blobs:
            listed.add(blob.path)
            rows.append(self._row(blob, by_path.get(blob.path), pages, in_release, audience))
        for path, state in by_path.items():
            if path not in listed and state.deleted:
                rows.append(self._row(RawBlob(path=path), state, pages, in_release, audience))
        rows.sort(key=lambda row: (DOCUMENT_STATUSES.index(row["status"]), row["path"].lower()))
        return rows

    @staticmethod
    def _row(
        blob: RawBlob,
        state: SourceState | None,
        pages: dict[str, Any],
        in_release: set[str],
        audience: str,
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
        sensitivity = state.sensitivity if state else None
        return {
            "path": blob.path,
            "size": blob.size if blob.size is not None else (state.size if state else None),
            "modified": _iso(blob.modified) or (_iso(state.updated_at) if state else None),
            "status": status,
            "stage": stage,
            "source_id": source_id,
            "sensitivity": sensitivity,
            "hidden": bool(sensitivity and not allowed_for_audience(sensitivity, audience)),
            "in_release": bool(source_id and source_id in in_release),
            "page_url": site_link(page.path) if page else None,
            "last_error": _clip(state.last_error) if state else None,
        }

    @staticmethod
    def _public_row(row: dict[str, Any]) -> dict[str, Any]:
        public = {**row, "last_error": None, "failed": bool(row["last_error"])}
        if row["hidden"]:
            public.update(path="(not in this site's audience)", source_id=None, page_url=None)
        return public

    def _runs(self, release: dict[str, Any] | None) -> list[dict[str, Any]]:
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
        return runs

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
        }

    # -- the owner's upload ------------------------------------------------------------------

    def uploads_left(self) -> int:
        return max(self.daily_uploads - self._uploads.get(self._today(), 0), 0)

    def upload(self, path: str, data: bytes, *, replace: bool = False) -> dict[str, Any]:
        """Write ``raw/<path>``; the pipeline picks it up through Event Grid."""
        try:
            rel = check_upload_path(path)
        except ValueError as exc:
            raise UploadError(str(exc)) from exc
        if not data:
            raise UploadError("the file is empty")
        if len(data) > self.max_upload_bytes:
            raise UploadTooLargeError(
                f"the file is larger than {self.max_upload_bytes // (1024 * 1024)} MB"
            )
        if self.uploads_left() <= 0:
            raise UploadQuotaError(
                f"the daily allowance of {self.daily_uploads} uploads is used up "
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

    # -- health ------------------------------------------------------------------------------

    def storage_ok(self) -> bool:
        try:
            read_current_pointer(self.storage)
            self.storage.list(StorageKeys.SOURCE_STATE_DIR + "/")
        except Exception as exc:
            log.warning("storage check failed: %s", exc)
            return False
        return True


def azure_raw_lister(account_url: str, container: str, credential: Any) -> RawLister:
    """``raw/`` with sizes and modification times (``Storage.list`` only returns names)."""
    from azure.storage.blob import ContainerClient

    client = ContainerClient(account_url, container, credential=credential)

    def list_raw() -> list[RawBlob]:
        return [
            RawBlob(
                path=str(item.name),
                size=int(item.size) if item.size is not None else None,
                modified=item.last_modified,
            )
            for item in client.list_blobs()
            if not str(item.name).endswith("/")
        ]

    return list_raw


QUEUE_PEEK_LIMIT = 32
"""Storage queues peek at most 32 messages: the page shows "32+" beyond that."""


def azure_queue_depth(account_url: str, queue_name: str, credential: Any) -> QueueDepth:
    """Messages waiting in the ingest queue (peek: needs only Storage Queue Data Reader)."""
    from azure.storage.queue import QueueClient

    client = QueueClient(account_url, queue_name, credential=credential)

    def depth() -> int:
        return len(list(client.peek_messages(max_messages=QUEUE_PEEK_LIMIT)))

    return depth
