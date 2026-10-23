"""The process behind the wiki, live (ADR 0009, 0010): what ``/api/process`` shows on the
``pipeline`` page, the header chip's ``/api/status``, and the owner's uploads into ``raw/``.

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
from pathlib import PurePosixPath
from typing import Any
from urllib.parse import quote

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.enums import STAGE_NAMES, allowed_for_audience
from docwiki.contracts.formats import SUPPORTED_EXTENSIONS, detect_format
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.layout import ReleaseFiles, StorageKeys, release_prefix
from docwiki.contracts.queue import QueueMessage
from docwiki.contracts.runs import RunReport
from docwiki.contracts.state import SourceState
from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, Storage
from docwiki.mcp.tools_ops import SOURCE_STATUSES, OpsTools, overall_status
from docwiki.mcp.workstore import WorkStore
from docwiki.release.publish import read_current_pointer

__all__ = [
    "DOCUMENT_STATES",
    "DOCUMENT_STATUSES",
    "MAX_DEPTH",
    "MAX_PATH_CHARS",
    "PHASES",
    "PathError",
    "ProcessService",
    "RawBlob",
    "RebuildError",
    "UploadConflictError",
    "UploadError",
    "UploadQuotaError",
    "UploadTooLargeError",
    "check_upload_path",
    "document_phase",
    "document_state",
    "site_link",
]

log = logging.getLogger("docwiki.portal.process")

DOCUMENT_STATUSES = ("new", *SOURCE_STATUSES)
"""``new``: in ``raw/`` but not seen by the pipeline yet; then the pipeline's own statuses."""
DOCUMENT_STATES = (
    "failed",
    "received",
    "queued",
    "processing",
    "in_wiki",
    "superseded",
    "held_back",
    "removed",
)
"""What the site shows (ADR 0010), in display order. ``in_wiki`` and ``superseded`` only for a
document of the published release: one whose stages are all done but that is not published yet is
still ``processing``."""
PHASES: dict[str, tuple[str, ...]] = {
    "read": ("discover", "extract"),
    "file": ("classify",),
    "write": ("compile", "entities", "topics", "links", "indexes", "agentkit"),
    "check": ("evidence", "verify", "site", "publish"),
}
"""The business view of the 13 stages (ADR 0010): Read, File, Write, Check and publish."""
PER_SOURCE_STAGES = ("extract", "classify", "compile")
MAX_PAGE_CHANGES = 200
"""Pages listed per change kind in a run's view (the page shows fewer, with "and n more")."""
DEFAULT_DAILY_REBUILDS = 5
_REBUILD_KEY_RE = re.compile(r"^[A-Za-z0-9-]{8,64}$")
RUN_LIMIT = 10
RUN_SCAN = 200
"""Run reports read to find :data:`RUN_LIMIT` runs that did something; no-op checks are counted,
not listed."""
JUST_PUBLISHED_S = 15 * 60
"""The header chip says "In the wiki → <document>" this long after the release that added it."""
CACHE_TTL_S = 4.0
MAX_PATH_CHARS = 200
MAX_DEPTH = 6
"""Segments of an upload path: room for a scoped layout such as
``chantiers/<code>/<phase>/<type>/<file>`` under one more folder (ADR 0011)."""
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


class RebuildError(ValueError):
    """A rebuild the portal refuses: a bad key (HTTP 400)."""


def check_upload_path(path: str) -> str:
    """The normalised ``raw/``-relative path of an upload, or :class:`PathError`.

    Accepts at most six segments of letters, digits, spaces and ``._()+-`` (no leading dot, so
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


def document_state(
    status: str,
    stage: str | None,
    *,
    in_release: bool,
    hidden: bool,
    superseded: bool = False,
) -> tuple[str, int | None]:
    """``(state, step)``: the status the site shows and, while processing, the 1-based number of
    the stage at work out of the 13 (ADR 0010)."""
    if hidden or status == "quarantined":
        return "held_back", None
    if status == "failed":
        return "failed", None
    if status == "deleted":
        return "removed", None
    if status == "new":
        return "received", None
    if status == "pending":
        if stage in STAGE_NAMES:
            return "processing", STAGE_NAMES.index(stage) + 1
        return "queued", None
    if not in_release:
        # Every stage of the document is done; the release that carries it is not out yet.
        return "processing", len(STAGE_NAMES)
    return ("superseded" if superseded else "in_wiki"), None


def document_phase(stage: str | None) -> str | None:
    """The business phase of a stage (:data:`PHASES`), or ``None``."""
    return next((phase for phase, stages in PHASES.items() if stage in stages), None)


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


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


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
        enqueue: Callable[[QueueMessage], None] | None = None,
        daily_rebuilds: int = DEFAULT_DAILY_REBUILDS,
        clock: Callable[[], float] = time.monotonic,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
    ) -> None:
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes
        self.daily_uploads = daily_uploads
        self._list_raw = list_raw or self._list_raw_from_storage
        self._queue_depth = queue_depth
        self._enqueue = enqueue
        self._finished: dict[str, RunReport] = {}
        """Run reports that will not change any more (finished runs), by run id."""
        self._originals: tuple[str, dict[str, str]] | None = None
        """``(release_id, {source_id: original file name})`` of the served release."""
        self.daily_rebuilds = daily_rebuilds
        self._rebuilds: dict[date, set[str]] = {}
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
        if owner:
            return view
        runs = [
            {**run, "documents": [item for item in run["documents"] if not item["hidden"]]}
            for run in view["runs"]
        ]
        documents = [self._public_row(row) for row in view["documents"]]
        return {**view, "documents": documents, "runs": runs}

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
        reports, checks, history, seen_at = self._reports()
        running = reports[0] if reports and reports[0].status == "running" else None
        documents = self._documents(
            catalog,
            audience,
            running,
            released_at=pointer.created_at if pointer is not None else None,
            seen_at=seen_at,
            originals=self._published_originals(pointer.release_id) if pointer else {},
        )
        counts = Counter(row["status"] for row in documents)
        states = Counter(row["state"] for row in documents)
        hidden = {row["source_id"] for row in documents if row["hidden"]}
        runs = [self._run_view(report, release, catalog, hidden) for report in reports]
        self._last_changes(documents, history, catalog)
        return {
            "release": release,
            "runs": runs,
            "checks": checks,
            "queued": self._queued(),
            "documents": documents,
            "counts": {status: counts.get(status, 0) for status in DOCUMENT_STATUSES},
            "states": {state: states.get(state, 0) for state in DOCUMENT_STATES},
            "total": len(documents),
        }

    def status(self, *, now: datetime | None = None) -> dict[str, Any]:
        """The header chip (ADR 0010): ``idle``, ``processing`` (with how many documents) or
        ``published`` (a document reached the wiki in the last minutes, with its page)."""
        view = self.process()
        release = view["release"]
        working = sum(
            1 for row in view["documents"] if row["state"] in ("received", "queued", "processing")
        )
        latest = view["runs"][0] if view["runs"] else None
        result: dict[str, Any] = {
            "state": "idle",
            "processing": working,
            "release_id": release["release_id"] if release else None,
            "document": None,
        }
        if working or (latest and not latest["finished_at"]) or (view["queued"] or 0) > 0:
            result["state"] = "processing"
            return result
        published = _parse_time(release["published_at"]) if release else None
        moment = now or datetime.now(UTC)
        if published is None or (moment - published).total_seconds() > JUST_PUBLISHED_S:
            return result
        # The newest document of the release, when it arrived shortly before the release.
        fresh = [
            row
            for row in view["documents"]
            if row["state"] in ("in_wiki", "superseded")
            and row["page_url"]
            and (arrived := _parse_time(row["modified"])) is not None
            and (published - arrived).total_seconds() <= JUST_PUBLISHED_S
        ]
        if fresh:
            row = max(fresh, key=lambda item: _parse_time(item["modified"]) or published)
            result["state"] = "published"
            result["document"] = {"title": row["title"], "page_url": row["page_url"]}
        return result

    def _queued(self) -> int | None:
        if self._queue_depth is None:
            return None
        try:
            return self._queue_depth()
        except Exception as exc:  # the view degrades, it does not fail
            log.warning("queue depth unavailable: %s", exc)
            return None

    def _documents(
        self,
        catalog: Catalog | None,
        audience: str,
        running: RunReport | None = None,
        *,
        released_at: datetime | None = None,
        seen_at: datetime | None = None,
        originals: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        blobs = self._list_raw()
        states, _broken = WorkStore(self.storage).source_states()
        by_path: dict[str, SourceState] = {state.raw_path: state for state in states}
        pages = catalog.page_by_id() if catalog else {}
        released = {item.source_id: item.status for item in catalog.sources} if catalog else {}
        in_run = {document.path for document in running.documents} if running else set()
        stage = running.current_stage if running else None
        rows: list[dict[str, Any]] = []
        listed: set[str] = set()
        for blob in blobs:
            listed.add(blob.path)
            row = self._row(blob, by_path.get(blob.path), pages, released, audience)
            if _received_after(row, blob, released_at, seen_at):
                # A new version of a document of the release: received, not yet in the wiki.
                row.update(state="received", stage=None, step=None, phase=None)
            name = (originals or {}).get(row["source_id"] or "")
            row["original_url"] = f"/evidence/{row['source_id']}/{name}" if name else None
            rows.append(self._follow_run(row, stage, blob.path in in_run))
        for path, state in by_path.items():
            if path not in listed and state.deleted:
                rows.append(self._row(RawBlob(path=path), state, pages, released, audience))
        rows.sort(
            key=lambda row: (
                DOCUMENT_STATES.index(row["state"]),
                (row["title"] or row["path"]).lower(),
            )
        )
        return rows

    @staticmethod
    def _row(
        blob: RawBlob,
        state: SourceState | None,
        pages: dict[str, Any],
        released: dict[str, str],
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
        sensitivity = state.sensitivity if state else None
        hidden = bool(sensitivity and not allowed_for_audience(sensitivity, audience))
        in_release = bool(source_id and source_id in released)
        page = pages.get(source_id) if source_id and in_release else None
        shown, step = document_state(
            status,
            stage,
            in_release=in_release,
            hidden=hidden,
            superseded=bool(source_id and released.get(source_id) == "superseded"),
        )
        return {
            "path": blob.path,
            "title": page.title if page else None,
            "size": blob.size if blob.size is not None else (state.size if state else None),
            "modified": _iso(blob.modified) or (_iso(state.updated_at) if state else None),
            "status": status,
            "stage": stage,
            "state": shown,
            "step": step,
            "steps": len(STAGE_NAMES),
            "source_id": source_id,
            "sensitivity": sensitivity,
            "hidden": hidden,
            "in_release": in_release,
            "page_url": site_link(page.path) if page else None,
            "document_url": f"/evidence/{source_id}/" if page and source_id else None,
            "original_url": None,
            "phase": document_phase(STAGE_NAMES[step - 1]) if step else None,
            "last_change": None,
            "last_error": _clip(state.last_error) if state else None,
        }

    @staticmethod
    @staticmethod
    def _follow_run(row: dict[str, Any], stage: str | None, in_run: bool) -> dict[str, Any]:
        """A document of the run at work is processing, even one whose earlier version is in the
        wiki: before its own stages (extract, classify, compile, recorded in its state) it is at
        the run's stage (a new document waits at extract); past them, it is where the run is."""
        if not in_run or stage not in STAGE_NAMES:
            return row
        if row["state"] in ("held_back", "failed", "removed"):
            return row
        at = STAGE_NAMES.index(stage) + 1
        own = row["step"] if row["state"] == "processing" else None
        if own is None:
            waiting = row["state"] in ("received", "queued") and stage in PER_SOURCE_STAGES
            where = "extract" if waiting else stage
            row.update(state="processing", stage=where, step=STAGE_NAMES.index(where) + 1)
        elif stage not in PER_SOURCE_STAGES and (at > own or own == len(STAGE_NAMES)):
            row.update(stage=stage, step=at)
        row["phase"] = document_phase(row["stage"])
        return row
        at = STAGE_NAMES.index(stage) + 1
        own = row["step"] if row["state"] == "processing" else None
        if own is None:
            # not started on its own stages yet: the run is discovering it, or it waits for extract
            where = "extract" if stage in PER_SOURCE_STAGES else stage
            row.update(state="processing", stage=where, step=STAGE_NAMES.index(where) + 1)
        elif stage not in PER_SOURCE_STAGES and (at > own or own == len(STAGE_NAMES)):
            row.update(stage=stage, step=at)
        row["phase"] = document_phase(row["stage"])
        return row
        if row["state"] == "received" and stage == "discover":
            row.update(state="processing", stage="discover", step=1, phase="read")
        elif row["state"] == "processing" and stage not in PER_SOURCE_STAGES:
            own = row["step"] or 0
            at = STAGE_NAMES.index(stage) + 1
            if at > own or own == len(STAGE_NAMES):
                row.update(stage=stage, step=at, phase=document_phase(stage))
        return row

    @staticmethod
    def _public_row(row: dict[str, Any]) -> dict[str, Any]:
        public = {**row, "last_error": None, "failed": bool(row["last_error"])}
        if row["hidden"]:
            public.update(
                path="(not in this site's audience)",
                title=None,
                source_id=None,
                page_url=None,
                document_url=None,
                original_url=None,
                last_change=None,
            )
        return public

    def _reports(
        self,
    ) -> tuple[list[RunReport], dict[str, Any], list[RunReport], datetime | None]:
        """The last :data:`RUN_LIMIT` runs that did something, newest first, the no-op checks met
        on the way (``{"count", "last"}``: counted, not listed; ADR 0010), and every published
        run of the last :data:`RUN_SCAN` (for each document's last change), and when the newest
        finished run (no-op checks included) started: files older than that were seen by the
        pipeline. Finished reports are read once."""
        store = WorkStore(self.storage)
        runs: list[RunReport] = []
        history: list[RunReport] = []
        checks = 0
        last_check: str | None = None
        seen_at: datetime | None = None
        for run_id in reversed(store.run_ids()[-RUN_SCAN:]):
            report = self._finished.get(run_id)
            if report is None:
                try:
                    report = store.run_report(run_id)
                except ValueError:
                    continue
                if report is None:
                    continue
                if report.status != "running":
                    self._finished[run_id] = report
            if report.status != "running" and seen_at is None:
                seen_at = report.started_at
            if report.status == "no-op":
                if len(runs) < RUN_LIMIT:
                    checks += 1
                    last_check = last_check or _iso(report.finished_at) or _iso(report.started_at)
                continue
            if len(runs) < RUN_LIMIT:
                runs.append(report)
            if report.release_id is not None and report.page_changes:
                history.append(report)
        return runs, {"count": checks, "last": last_check}, history, seen_at

    def _published_originals(self, release_id: str) -> dict[str, str]:
        """``{source_id: original file name}`` of the originals the release publishes (listed
        once per release)."""
        cached = self._originals
        if cached is not None and cached[0] == release_id:
            return cached[1]
        prefix = release_prefix(release_id) + "evidence/"
        found: dict[str, str] = {}
        try:
            for key in self.storage.list(prefix):
                parts = key[len(prefix) :].split("/")
                if len(parts) == 2 and parts[1].startswith("original."):
                    found[parts[0]] = parts[1]
        except Exception as exc:  # the view degrades, it does not fail
            log.warning("originals of %s not listed: %s", release_id, exc)
            return {}
        self._originals = (release_id, found)
        return found

    def _last_changes(
        self, rows: list[dict[str, Any]], reports: list[RunReport], catalog: Catalog | None
    ) -> None:
        """Each document's ``last_change``: what the last published run that processed it
        changed in the wiki (the pages that cite it)."""
        if catalog is None:
            return
        by_path = {page.path: page for page in catalog.pages}
        wanted = {row["source_id"]: row for row in rows if row["source_id"]}
        for report in reports:  # newest first
            if report.release_id is None or not report.page_changes:
                continue
            for document in report.documents:
                row = wanted.pop(document.source_id, None)
                if row is None:
                    continue
                pages = [
                    _page_item(change.path, change.change, by_path)
                    for change in report.page_changes
                    if change.change != "removed"
                    and change.path in by_path
                    and document.source_id in by_path[change.path].sources
                ]
                row["last_change"] = {
                    "run_id": report.run_id,
                    "finished_at": _iso(report.finished_at),
                    "change": document.change,
                    "pages": pages[:MAX_PAGE_CHANGES],
                }

    @staticmethod
    def _run_view(
        report: RunReport,
        release: dict[str, Any] | None,
        catalog: Catalog | None = None,
        hidden: set[str] | frozenset[str] = frozenset(),
    ) -> dict[str, Any]:
        summary = OpsTools._run_summary(report)
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
            "current_stage": report.current_stage if report.status == "running" else None,
            "documents": [
                {
                    "path": document.path,
                    "title": _title(document.source_id, catalog),
                    "change": document.change,
                    "hidden": document.source_id in hidden,
                }
                for document in report.documents
            ],
            "changes": _changes(report, catalog) if report.release_id else None,
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

    # -- the owner's rebuild -----------------------------------------------------------------

    @property
    def can_rebuild(self) -> bool:
        return self._enqueue is not None

    def rebuilds_left(self) -> int:
        return max(self.daily_rebuilds - len(self._rebuilds.get(self._today(), set())), 0)

    def rebuild(self, key: str) -> dict[str, Any]:
        """Enqueue a rebuild of the wiki and the site (every page from the cache: about $0 when
        no document changed). ``key`` makes a retried request enqueue once."""
        if self._enqueue is None:
            raise RuntimeError("this portal cannot enqueue runs")
        if not _REBUILD_KEY_RE.match(key or ""):
            raise RebuildError("the key must be 8 to 64 letters, digits or dashes")
        today = self._today()
        done = self._rebuilds.get(today, set())
        if key in done:
            return {"queued": True, "kind": "rebuild", "rebuilds_left": self.rebuilds_left()}
        if len(done) >= self.daily_rebuilds:
            raise UploadQuotaError(
                f"the daily allowance of {self.daily_rebuilds} rebuilds is used up"
            )
        self._enqueue(
            QueueMessage(
                kind="rebuild",
                requested_by="owner",
                idempotency_key=f"owner:rebuild:{key}",
                created_at=datetime.now(UTC).replace(microsecond=0),
            )
        )
        self._rebuilds = {today: {*done, key}}
        self.invalidate()
        log.info("owner rebuild queued (%s)", key)
        return {"queued": True, "kind": "rebuild", "rebuilds_left": self.rebuilds_left()}

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


def _received_after(
    row: dict[str, Any],
    blob: RawBlob,
    released_at: datetime | None,
    seen_at: datetime | None,
) -> bool:
    """A document of the release whose file changed after the release was published and after
    the last finished run started (an identical copy uploaded again ends in a no-op run: the
    document is in the wiki again once that run has seen it)."""
    if not row["in_release"] or row["state"] not in ("in_wiki", "superseded"):
        return False
    if blob.modified is None or released_at is None:
        return False

    def utc(value: datetime) -> datetime:
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    modified = utc(blob.modified)
    return modified > utc(released_at) and (seen_at is None or modified > utc(seen_at))


def _title(source_id: str, catalog: Catalog | None) -> str | None:
    if catalog is None:
        return None
    page = catalog.page_by_id().get(source_id)
    return page.title if page else None


def _page_item(path: str, change: str, by_path: dict[str, Any]) -> dict[str, Any]:
    page = by_path.get(path)
    title = page.title if page else PurePosixPath(path).stem.replace("-", " ")
    return {
        "title": title,
        "url": site_link(path) if page else None,
        "type": page.type if page else None,
        "change": change,
    }


def _changes(report: RunReport, catalog: Catalog | None) -> dict[str, Any]:
    """The pages a published run added, changed or removed, and the contradictions it opened or
    closed (a topic page whose count went up from zero, or down to zero)."""
    by_path = {page.path: page for page in catalog.pages} if catalog else {}
    result: dict[str, Any] = {"added": [], "changed": [], "removed": []}
    opened: list[dict[str, Any]] = []
    closed: list[dict[str, Any]] = []
    for change in report.page_changes:
        item = _page_item(change.path, change.change, by_path)
        if len(result[change.change]) < MAX_PAGE_CHANGES:
            result[change.change].append(item)
        now, before = change.contradictions, change.previous_contradictions
        if now and not before and (before is not None or change.change == "added"):
            opened.append(item)
        elif before and now == 0:
            closed.append(item)
    result["counts"] = {
        kind: sum(1 for change in report.page_changes if change.change == kind)
        for kind in ("added", "changed", "removed")
    }
    result["contradictions"] = {"opened": opened, "closed": closed}
    return result


QUEUE_PEEK_LIMIT = 32
"""Storage queues peek at most 32 messages: the page shows "32+" beyond that."""


def azure_queue_depth(account_url: str, queue_name: str, credential: Any) -> QueueDepth:
    """Messages waiting in the ingest queue (peek: needs only Storage Queue Data Reader)."""
    from azure.storage.queue import QueueClient

    client = QueueClient(account_url, queue_name, credential=credential)

    def depth() -> int:
        return len(list(client.peek_messages(max_messages=QUEUE_PEEK_LIMIT)))

    return depth


def azure_enqueue(
    account_url: str, queue_name: str, credential: Any
) -> Callable[[QueueMessage], None]:
    """Send a message to the ingest queue (the portal identity needs Queue Data Message Sender on
    it, which the infra gives only when owners are configured)."""
    from azure.storage.queue import QueueClient

    client = QueueClient(account_url, queue_name, credential=credential)

    def send(message: QueueMessage) -> None:
        client.send_message(message.to_body())

    return send
