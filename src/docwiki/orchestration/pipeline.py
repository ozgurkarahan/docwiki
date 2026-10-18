"""One run of the DocWiki pipeline (pipeline §1, architecture §4–5, §7).

:class:`Pipeline` holds the state of a run and exposes the steps that the orchestrators drive:

* :meth:`Pipeline.prepare` — domain pack + overlay, model versions, ``discover``, previous
  release, no-op detection;
* :meth:`Pipeline.extract_one`, :meth:`Pipeline.classify_one`, :meth:`Pipeline.compile_one` —
  per-source stages (fanned out by the orchestrator), each content-addressed under
  ``work/artifacts/<stage>/<cache_key>/`` and recorded in the source's state shard;
* :meth:`Pipeline.resolve` — final sensitivity (doc type rules) and audience filtering;
* :meth:`Pipeline.assemble` — render, entities, topics, links, indexes, agent kit, evidence,
  catalog, search index, verify, site and publish.

Remote raw files are downloaded only when a stage needs their bytes (extraction, an evidence page
render or embedded figure, a published original) into ``<scratch>/raw/<source_id>/<hash>/``,
verified against the content hash recorded by ``discover``; the folder is cleared at the start of
every run.

Sources that fail extraction or compilation are quarantined (state shard status and
``last_error``) and the run continues; infrastructure errors (storage, authentication, rate
limits after retries, lost lease, Content Understanding outages) abort the run so that it is
retried. A quarantine caused by a transient problem (``retryable``, e.g. a raw file overwritten
during the run) is retried by the next runs, a bounded number of times
(:data:`~docwiki.contracts.state.RETRY_ATTEMPTS`); other quarantines stay until the content
changes or a recompile is requested. Correctness never depends on workflow checkpoints: a re-run
reuses every artifact that already exists.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from docwiki import __version__
from docwiki.contracts._base import sha256_hex
from docwiki.contracts.catalog import Catalog
from docwiki.contracts.enums import QueueKind, RequestedBy, allowed_for_audience, max_sensitivity
from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.gates import GateResult
from docwiki.contracts.ids import assign_source_slugs, cache_key, new_run_id, source_page_path
from docwiki.contracts.layout import ReleaseFiles, StorageKeys, WikiFiles, run_report_key
from docwiki.contracts.locators import ImageRegionLocator, PdfPageLocator
from docwiki.contracts.manifest import ReleaseInputs
from docwiki.contracts.markdown import extract_footnotes, extract_links, resolve_href
from docwiki.contracts.pages import DocwikiStamp, Page, QueryFrontmatter, SourceFrontmatter
from docwiki.contracts.runs import (
    ContentUnderstandingUsage,
    ModelVersion,
    RunCounts,
    RunReport,
    VersionInfo,
)
from docwiki.contracts.state import RETRY_ATTEMPTS, SourceState
from docwiki.contracts.storage import (
    KeyNotFoundError,
    LeaseLostError,
    Storage,
    StorageError,
)
from docwiki.domain.loader import PackValidationError, load_pack
from docwiki.domain.models import DomainPack
from docwiki.domain.rules import (
    explicit_references,
    glossary_synonym_rows,
    parse_doc_number,
    parse_revision,
    sensitivity_floor,
    sensitivity_for,
)
from docwiki.engine_types import (
    CitedLocator,
    Classification,
    CompiledResult,
    ExtractionError,
    ExtractResult,
    ExtractSettings,
    TopicSkip,
)
from docwiki.llm.client import LlmClient
from docwiki.llm.errors import (
    LlmAuthError,
    LlmConfigurationError,
    LlmRateLimited,
    LlmReplayMissing,
    LlmServiceError,
    LlmTimeout,
)
from docwiki.llm.types import DeploymentInfo
from docwiki.orchestration.artifacts import ArtifactStore
from docwiki.orchestration.codec import (
    content_digest,
    decode_cited,
    decode_classification,
    decode_compiled_result,
    decode_extract_result,
    decode_pages,
    decode_topic_skips,
    encode_cited,
    encode_classification,
    encode_compiled_result,
    encode_extract_result,
    encode_pages,
    encode_topic_skips,
    json_bytes,
)
from docwiki.orchestration.containment import Containment, assess, redact, searchable
from docwiki.orchestration.proposals import ProposalStore
from docwiki.orchestration.registry import Engine, EngineUnavailableError
from docwiki.orchestration.report import LedgerCursor, StageClock, cost_receipt
from docwiki.orchestration.settings import EngineSettings
from docwiki.orchestration.telemetry import engine_logger, stage_span
from docwiki.release.publish import read_current_pointer, read_manifest, try_retention
from docwiki.release.writer import ReleaseWriter
from docwiki.search.index import blocks_from_extracted
from docwiki.stages.agentkit import build_agent_kit, write_agent_kit
from docwiki.stages.discover import (
    PlanItem,
    SupersessionRecord,
    WorkPlan,
    discover,
    resolve_supersession,
    revalidate_state,
)
from docwiki.stages.indexes import build_catalog, build_indexes, changes_since, run_page_path
from docwiki.stages.links import apply_links, build_edges, replace_frontmatter
from docwiki.stages.publish import finalize_and_publish, run_receipt_page
from docwiki.stages.sitehook import SiteResult, build_site_for_release, site_unavailable
from docwiki.stages.verify import (
    QuarantineItem,
    extend_verdict,
    quality_page,
    scan_canaries,
    scrub,
    verify_release,
)
from docwiki.storage.routed import local_path_for
from docwiki.storage.state import StateStore, with_stage

__all__ = [
    "NEUTRAL_STAMP",
    "SYSTEMIC_ERRORS",
    "Pipeline",
    "RawContentChangedError",
    "RunContext",
    "RunOutcome",
    "RunRequest",
    "SourceWork",
    "build_state_key",
    "fingerprint",
    "is_deterministic",
    "is_retryable",
    "is_systemic",
    "restamp",
]

logger = engine_logger
NEUTRAL_STAMP = DocwikiStamp(release="00000000T000000Z-00000000")
NEUTRAL_DATE = date(2000, 1, 1)
SYSTEMIC_ERRORS: tuple[type[BaseException], ...] = (
    LlmAuthError,
    LlmConfigurationError,
    LlmRateLimited,
    LlmTimeout,
    LlmServiceError,
    LlmReplayMissing,
    StorageError,
    EngineUnavailableError,
    MemoryError,
)
"""Errors that abort the run (it is retried) instead of quarantining one source.

Errors that declare ``systemic = True`` (Content Understanding throttling, outages and
authorization failures) abort the run as well, see :func:`is_systemic`."""
_EXPLICIT_REFERENCE_CHARS = 4000
DETERMINISTIC_NOTE = (
    "deterministic failure: not retried (the queue messages are acknowledged); fix the cause, "
    "then a new upload, a recompile or the reconcile schedule starts the next run"
)
_WITHDRAWN_BANNER = "> **Warning:** this answer cited sources that were withdrawn"
_HASH_CHUNK = 1 << 20


class RawContentChangedError(ExtractionError):
    """The raw bytes differ from the content hash recorded by ``discover`` (the file was replaced
    during the run). The quarantine is ``retryable``: the next run picks the new content up."""

    retryable = True


def _file_hash(path: Path) -> str:
    """``sha256:<hex>`` of a file, read in chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(_HASH_CHUNK):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def build_state_key(audience: str) -> str:
    """``work/state/build-<audience>.json``: inputs and page fingerprints of the last publish."""
    return f"{StorageKeys.WORK}/state/build-{audience}.json"


def hints_key(source_id: str) -> str:
    return f"{StorageKeys.WORK}/state/hints/{source_id}.json"


def fingerprint(page: Page) -> str:
    """Hash of a page without its release stamp and ``updated`` date."""
    fm = page.frontmatter.model_copy(update={"docwiki": NEUTRAL_STAMP, "updated": NEUTRAL_DATE})
    return sha256_hex(Page(path=page.path, frontmatter=fm, body=page.body).render().encode())


def restamp(page: Page, stamp: DocwikiStamp, day: date) -> Page:
    """``page`` stamped for another release (cached entity/topic pages, carried queries)."""
    fm = page.frontmatter.model_copy(update={"docwiki": stamp, "updated": day})
    return Page(path=page.path, frontmatter=fm, body=page.body)


@dataclass
class RunRequest:
    """What triggered the run and how to run it."""

    kind: QueueKind = "ingest"
    requested_by: RequestedBy = "cli"
    messages: int = 0
    recompile: dict[str, str | None] = field(default_factory=dict)
    force: bool = False
    only: tuple[str, ...] = ()
    limit: int | None = None
    site: bool | None = None
    publish: bool = True


@dataclass
class RunContext:
    """Dependencies of a run.

    ``notices`` returns problems noticed outside the pipeline while the run lasts (for example
    by the queue worker); they are added to the warnings of the run report.
    """

    storage: Storage
    llm: LlmClient
    engine: Engine
    settings: EngineSettings
    pack_path: Path
    scratch_dir: Path
    canaries: tuple[str, ...] = ()
    now: Callable[[], datetime] = lambda: datetime.now(UTC)
    lease_ok: Callable[[], bool] = lambda: True
    templates_dir: Path | None = None
    notices: Callable[[], Sequence[str]] = lambda: ()


@dataclass
class RunOutcome:
    run_id: str
    status: Literal["succeeded", "failed", "no-op"]
    report: RunReport
    release_id: str | None = None
    published: bool = False
    staged_root: Path | None = None
    gates: list[GateResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    plan: WorkPlan | None = None
    deterministic: bool = False
    """A failure that a retry of the same inputs repeats (blocking gates, final validation, an
    invalid domain pack): the run control acknowledges its queue messages instead of retrying."""

    @property
    def retry(self) -> bool:
        """Whether the queue delivers this run's messages again (failed, not deterministic)."""
        return self.status == "failed" and not self.deterministic


@dataclass
class SourceWork:
    """Per-source state during a run."""

    item: PlanItem
    status: Literal["pending", "ok", "quarantined", "failed", "excluded"] = "pending"
    stage: str | None = None
    error: str | None = None
    extract: ExtractResult | None = None
    doc_hash: str | None = None
    classification: Classification | None = None
    class_hash: str | None = None
    result: CompiledResult | None = None
    result_hash: str | None = None
    sensitivity: str | None = None
    extracted_now: bool = False

    @property
    def source_id(self) -> str:
        return self.item.source_id


@dataclass
class _Previous:
    release_id: str | None = None
    catalog: Catalog | None = None
    log: str | None = None
    queries: list[Page] = field(default_factory=list)


def _error_text(exc: BaseException) -> str:
    text = " ".join(str(exc).split())[:500]
    return f"{type(exc).__name__}: {text}" if text else type(exc).__name__


def is_systemic(exc: BaseException) -> bool:
    """Whether ``exc`` aborts the run (retried later) instead of quarantining one source."""
    return isinstance(exc, SYSTEMIC_ERRORS) or getattr(exc, "systemic", False) is True


def is_retryable(exc: BaseException) -> bool:
    """Whether a quarantine caused by ``exc`` is transient (retried by the next runs)."""
    return getattr(exc, "retryable", False) is True


def is_deterministic(exc: BaseException) -> bool:
    """Whether a run aborted by ``exc`` would fail the same way when retried (invalid domain
    pack or overlay). Unknown errors are not: their queue messages are kept for a retry."""
    return isinstance(exc, PackValidationError) and not is_systemic(exc)


class Pipeline:
    """State and steps of one run (driven by :mod:`docwiki.orchestration.workflow`)."""

    def __init__(self, ctx: RunContext, request: RunRequest, *, run_id: str | None = None) -> None:
        self.ctx = ctx
        self.request = request
        self.started = ctx.now().astimezone(UTC).replace(microsecond=0)
        self.run_id = run_id or new_run_id(self.started)
        self.audience = ctx.settings.audience
        self.state = StateStore(ctx.storage)
        self.artifacts = ArtifactStore(ctx.storage)
        self.proposals = ProposalStore(ctx.storage)
        self.clock = StageClock(ctx.now)
        self.cursor = LedgerCursor(ctx.llm)
        self.work: dict[str, SourceWork] = {}
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.plan: WorkPlan | None = None
        self.pack: DomainPack | None = None
        self.pack_hash = ""
        self.versions: VersionInfo | None = None
        self.fast: DeploymentInfo | None = None
        self.smart: DeploymentInfo | None = None
        self.previous = _Previous()
        self.no_op = False
        self.retries: list[str] = []
        """Sources whose transient quarantine this run retries."""
        self.extract_settings = ExtractSettings(
            mode="azure"
            if ctx.settings.mode == "azure" and ctx.settings.content_understanding
            else "local",
            cu_endpoint=ctx.settings.foundry_endpoint
            if ctx.settings.content_understanding
            else None,
            max_pages=ctx.settings.max_pages,
        )
        self.extract_digest = content_digest(
            {
                "mode": self.extract_settings.mode,
                "analyzer": self.extract_settings.cu_analyzer,
                "describe_figures": self.extract_settings.describe_figures,
                "max_pages": self.extract_settings.max_pages,
                "dpi": self.extract_settings.page_render_dpi,
            }
        )

    # -- helpers ---------------------------------------------------------------------------

    def check_lease(self) -> None:
        if not self.ctx.lease_ok():
            raise LeaseLostError("the run lease was lost; stopping before writing more state")

    @property
    def domain(self) -> DomainPack:
        if self.pack is None:
            raise RuntimeError("prepare() must run first")
        return self.pack

    def _model(self, info: DeploymentInfo | None) -> tuple[str | None, str | None]:
        if info is None:
            return None, None
        return info.model_name or info.deployment, info.model_version

    def _key(self, stage: str, inputs: Iterable[str], *, tier: str | None) -> str:
        info = self.fast if tier == "fast" else self.smart if tier == "smart" else None
        model_id, model_version = self._model(info)
        return cache_key(
            stage,
            inputs,
            stage_version=self.ctx.engine.version(stage),
            prompt_version=self.ctx.engine.prompts_for(stage),
            model_id=model_id,
            model_version=model_version,
            domain_pack_hash=self.pack_hash if stage != "extract" else None,
        )

    def _set_stage(
        self,
        work: SourceWork,
        stage: str,
        status: str,
        *,
        key: str | None = None,
        error: str | None = None,
        clear_error: bool = False,
        retryable: bool = False,
        attempts: int = 0,
    ) -> None:
        now = self.ctx.now()

        def mutate(current: SourceState | None) -> SourceState | None:
            if current is None:
                return None
            return with_stage(
                current,
                stage,
                status,  # type: ignore[arg-type]
                now=now,
                cache_key=key,
                error=error,
                clear_error=clear_error,
                retryable=retryable,
                attempts=attempts,
            )

        updated = self.state.update(work.source_id, mutate)
        if updated is not None:
            work.item.state = updated

    def _quarantine(self, work: SourceWork, stage: str, exc: BaseException) -> None:
        if is_systemic(exc):
            raise exc
        message = (
            f"ExtractionError: {exc.reason}"
            if isinstance(exc, ExtractionError)
            else _error_text(exc)
        )
        retryable = is_retryable(exc)
        previous = work.item.state.stages.get(stage)  # type: ignore[call-overload]
        attempts = 1
        if previous is not None and previous.status == "quarantined":
            attempts += previous.attempts
        work.status = "quarantined"
        work.stage = stage
        work.error = message
        self.clock.count(stage, failures=1)
        self.clock.error(stage, f"{work.source_id}: {message}")
        if retryable and attempts < RETRY_ATTEMPTS:
            logger.warning(
                "quarantined %s at %s (transient, attempt %d of %d; the next run retries): %s",
                work.source_id,
                stage,
                attempts,
                RETRY_ATTEMPTS,
                message,
            )
        else:
            logger.warning("quarantined %s at %s: %s", work.source_id, stage, message)
        self._set_stage(
            work, stage, "quarantined", error=message, retryable=retryable, attempts=attempts
        )

    def materialize(self, item: PlanItem) -> Path:
        """Local path of the raw file (downloaded to the scratch folder when remote).

        A scratch copy is reused only when its SHA-256 still matches the content hash recorded by
        ``discover``; downloaded bytes are verified the same way. A mismatch means the raw file
        was replaced after ``discover``: :class:`RawContentChangedError` (retryable).
        """
        local = local_path_for(self.ctx.storage, item.key)
        if local is not None and local.is_file():
            return local
        target = self.scratch_path(item)
        expected = item.state.content_hash
        if target.is_file() and _file_hash(target) == expected:
            return target
        data = self.ctx.storage.read_bytes(item.key)
        if sha256_hex(data) != expected.removeprefix("sha256:"):
            raise RawContentChangedError(
                item.source_id,
                "the raw file changed after discover (its content hash differs); "
                "the next run processes the new content",
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_name(target.name + ".partial")
        partial.write_bytes(data)
        partial.replace(target)
        return target

    def scratch_path(self, item: PlanItem) -> Path:
        """Where :meth:`materialize` puts a remote raw file (keyed by its content hash)."""
        digest = item.state.content_hash.removeprefix("sha256:")[:16]
        name = PurePosixPath(item.raw_path).name
        return self.ctx.scratch_dir / "raw" / item.source_id / digest / name

    def concurrency(self, stage: str) -> int:
        if stage == "extract":
            return max(1, self.ctx.settings.extract_concurrency)
        return max(1, self.ctx.settings.llm_concurrency)

    def stage_ids(self, stage: str) -> list[str]:
        if stage == "extract":
            return sorted(sid for sid, work in self.work.items() if work.status == "pending")
        return sorted(sid for sid, work in self.work.items() if work.status == "ok")

    def begin_stage(self, stage: str) -> None:
        self.check_lease()
        self.clock.start(stage)

    def end_stage(self, stage: str) -> None:
        self.clock.finish(stage)

    async def run_source_stage(self, stage: str, source_id: str) -> None:
        if stage == "extract":
            await self.extract_one(source_id)
        elif stage == "classify":
            await self.classify_one(source_id)
        elif stage == "compile":
            await self.compile_one(source_id)
        else:
            raise ValueError(f"unknown per-source stage {stage!r}")

    # -- prepare ---------------------------------------------------------------------------

    async def prepare(self) -> None:
        self._write_report("running")
        with stage_span("discover", run_id=self.run_id):
            self.clock.start("discover")
            # raw files downloaded by an earlier run may be stale: start from an empty folder
            shutil.rmtree(self.ctx.scratch_dir / "raw", ignore_errors=True)
            base = load_pack(self.ctx.pack_path)
            self.proposals.record_pack(base)
            self.pack, sync = self.proposals.domain_pack(base)
            for rejected in sync.rejected:
                logger.warning("overlay: %s", rejected)
                self.warnings.append(f"overlay: {rejected}")
            self.pack_hash = self.pack.content_hash()
            self.fast = await self.ctx.llm.describe("fast")
            self.smart = await self.ctx.llm.describe("smart")
            self.versions = self._versions()
            self.plan = discover(
                self.ctx.storage,
                self.pack,
                now=self.ctx.now(),
                state_store=self.state,
                recompile=self.request.recompile,
                only=self.request.only or None,
                limit=self.request.limit,
            )
            plan = self.plan
            self.clock.count("discover", items=len(plan.items))
            for skipped in plan.skipped:
                self.clock.error("discover", f"skipped {skipped.raw_path}: {skipped.reason}")
            self.errors.extend(plan.notes)
            self._load_previous()
            for item in plan.active_items():
                work = SourceWork(item=item)
                floor = sensitivity_floor(self.pack, item.raw_path)
                if not allowed_for_audience(floor, self.audience):
                    work.status = "excluded"
                    work.sensitivity = floor
                elif item.state.quarantined and item.change == "unchanged" and not item.forced:
                    stage, stage_state = item.state.quarantine or ("extract", None)
                    if item.state.retry_pending and stage_state is not None:
                        logger.info(
                            "retrying %s, quarantined at %s by a transient error "
                            "(attempt %d of %d)",
                            item.source_id,
                            stage,
                            stage_state.attempts + 1,
                            RETRY_ATTEMPTS,
                        )
                        self.retries.append(item.source_id)
                    else:
                        work.status = "quarantined"
                        work.stage = stage
                        work.error = item.state.last_error
                self.work[item.source_id] = work
            self.no_op = self._is_no_op()
            self.clock.finish("discover")

    def _versions(self) -> VersionInfo:
        engine = self.ctx.engine
        models: dict[str, ModelVersion] = {}
        for role, info in (("fast", self.fast), ("smart", self.smart)):
            if info is not None:
                models[role] = ModelVersion(
                    deployment=info.deployment,
                    model=info.model_name or info.deployment,
                    version=info.model_version,
                )
        return VersionInfo(
            docwiki=__version__,
            domain_pack=self.domain.name,
            domain_pack_hash=self.pack_hash,
            prompts=dict(engine.prompt_versions),
            models=models,
            extractors=dict(sorted({**engine.stage_versions, **engine.version_details}.items())),
        )

    def _load_previous(self) -> None:
        storage = self.ctx.storage
        pointer = read_current_pointer(storage)
        if pointer is None:
            return
        release_id = pointer[0].release_id
        self.previous.release_id = release_id
        try:
            manifest, _ = read_manifest(storage, release_id)
        except KeyNotFoundError:
            return
        if manifest.audience != self.audience:
            return
        base = f"{StorageKeys.RELEASES}/{release_id}"
        try:
            self.previous.catalog = Catalog.from_json(storage.read_bytes(f"{base}/catalog.json"))
            self.previous.log = storage.read_bytes(f"{base}/wiki/{WikiFiles.LOG}").decode("utf-8")
        except KeyNotFoundError:
            return
        for key in storage.list(f"{base}/wiki/queries/"):
            rel = key[len(f"{base}/wiki/") :]
            if not rel.endswith(".md") or rel == WikiFiles.QUERIES_INDEX:
                continue
            page = Page.parse(storage.read_bytes(key).decode("utf-8"), rel)
            if isinstance(page.frontmatter, QueryFrontmatter):
                self.previous.queries.append(page)

    def _build_state(self) -> dict[str, Any] | None:
        try:
            return json.loads(self.ctx.storage.read_bytes(build_state_key(self.audience)))
        except KeyNotFoundError:
            return None

    def _versions_digest(self) -> str:
        assert self.versions is not None
        return content_digest(self.versions.to_json_dict())

    def want_site(self) -> bool:
        """Whether this run builds the site (request flag, else ``DOCWIKI_SITE_BUILD``)."""
        if self.request.site is not None:
            return self.request.site
        return self.ctx.settings.site_enabled

    def _options_digest(self) -> str:
        """Build options that change the release without changing any version."""
        return content_digest({"site": self.want_site(), "canaries": sorted(self.ctx.canaries)})

    def _is_no_op(self) -> bool:
        plan = self.plan
        assert plan is not None
        if self.request.force or self.request.kind == "rebuild" or plan.forced or self.retries:
            return False
        state = self._build_state()
        if state is None or self.previous.release_id is None:
            return False
        current = {item.source_id: item.state.content_hash for item in plan.active_items()}
        return (
            state.get("release_id") == self.previous.release_id
            and state.get("versions") == self._versions_digest()
            and state.get("options") == self._options_digest()
            and state.get("sources") == current
            and not plan.restricted
        )

    # -- per-source stages -----------------------------------------------------------------

    async def extract_one(self, source_id: str) -> None:
        work = self.work[source_id]
        item = work.item
        key = self._key("extract", [item.state.content_hash, self.extract_digest], tier="fast")
        with stage_span("extract", run_id=self.run_id, source_id=source_id):
            artifact = self.artifacts.load("extract", key)
            if artifact is not None:
                result = decode_extract_result(artifact.files)
                self.clock.count("extract", items=1, cache_hits=1)
            else:
                try:
                    path = self.materialize(item)
                    result = await self.ctx.engine.extract_source(
                        path,
                        rel_path=item.raw_path,
                        settings=self.extract_settings,
                        llm=self.ctx.llm,
                    )
                    self._check_doc(result, item)
                except Exception as exc:
                    self._quarantine(work, "extract", exc)
                    return
                files = encode_extract_result(result)
                artifact = self.artifacts.save("extract", key, files)
                work.extracted_now = True
                self.clock.count("extract", items=1)
            work.extract = result
            work.doc_hash = sha256_hex(artifact.bytes("doc.json"))
            work.status = "ok"
            self._set_stage(work, "extract", "done", key=key)

    @staticmethod
    def _check_doc(result: ExtractResult, item: PlanItem) -> None:
        doc = result.doc
        if doc.source_id != item.source_id or doc.source_path != item.raw_path:
            raise ExtractionError(item.source_id, "extractor returned another source")
        if doc.source_hash != item.state.content_hash:
            raise RawContentChangedError(
                item.source_id, "extracted content hash differs from the file"
            )

    async def classify_one(self, source_id: str) -> None:
        work = self.work[source_id]
        assert work.extract is not None and work.doc_hash is not None
        key = self._key("classify", [work.doc_hash], tier="fast")
        with stage_span("classify", run_id=self.run_id, source_id=source_id):
            artifact = self.artifacts.load("classify", key)
            if artifact is not None:
                classification = decode_classification(artifact.bytes("classification.json"))
                self.clock.count("classify", items=1, cache_hits=1)
            else:
                try:
                    classification = await self.ctx.engine.classify_source(
                        work.extract.doc, self.domain, self.ctx.llm
                    )
                    self.domain.doc_type(classification.doc_type)
                except Exception as exc:
                    self._quarantine(work, "classify", exc)
                    return
                artifact = self.artifacts.save(
                    "classify", key, {"classification.json": encode_classification(classification)}
                )
                self.clock.count("classify", items=1)
            work.classification = classification
            work.class_hash = sha256_hex(artifact.bytes("classification.json"))
            self._set_stage(work, "classify", "done", key=key)

    def resolve(self) -> None:
        """Final sensitivity from the doc type; sources above the audience are excluded."""
        for work in sorted(self.work.values(), key=lambda item: item.source_id):
            if work.status != "ok" or work.classification is None:
                continue
            item = work.item
            tier = sensitivity_for(self.domain, item.raw_path, work.classification.doc_type)
            work.sensitivity = tier
            group = work.classification.doc_number
            if item.state.sensitivity != tier or item.state.revision_group != group:

                def mutate(
                    current: SourceState | None, tier: str = tier, group: str | None = group
                ) -> SourceState | None:
                    if current is None:
                        return None
                    return revalidate_state(
                        current, sensitivity=tier, revision_group=group, updated_at=self.ctx.now()
                    )

                updated = self.state.update(work.source_id, mutate)
                if updated is not None:
                    item.state = updated
            if not allowed_for_audience(tier, self.audience):
                work.status = "excluded"

    def _hints_for(self, item: PlanItem) -> str | None:
        if item.forced:
            return item.hints
        try:
            data = json.loads(self.ctx.storage.read_bytes(hints_key(item.source_id)))
        except KeyNotFoundError:
            return None
        if data.get("content_hash") != item.state.content_hash:
            return None
        hints = data.get("hints")
        return hints if isinstance(hints, str) and hints else None

    async def compile_one(self, source_id: str) -> None:
        work = self.work[source_id]
        assert work.extract is not None and work.classification is not None
        item = work.item
        hints = self._hints_for(item)
        inputs = [f"doc:{work.doc_hash}", f"classification:{work.class_hash}"]
        if hints:
            inputs.append("hints:" + sha256_hex(hints.encode("utf-8")))
        key = self._key("compile", inputs, tier="smart")
        with stage_span("compile", run_id=self.run_id, source_id=source_id):
            artifact = None if item.forced else self.artifacts.load("compile", key)
            if artifact is not None:
                result = decode_compiled_result(artifact.bytes("result.json"))
                self.clock.count("compile", items=1, cache_hits=1)
            else:
                try:
                    result = await self.ctx.engine.compile_source(
                        work.extract.doc,
                        work.classification,
                        self.domain,
                        self.ctx.llm,
                        hints=hints,
                    )
                    if result.source_id != source_id:
                        raise ValueError("compile_source returned another source")
                except Exception as exc:
                    self._quarantine(work, "compile", exc)
                    return
                artifact = self.artifacts.save(
                    "compile", key, {"result.json": encode_compiled_result(result)}
                )
                self.clock.count("compile", items=1)
                if item.forced and hints:
                    self.ctx.storage.write_bytes(
                        hints_key(source_id),
                        json_bytes({"content_hash": item.state.content_hash, "hints": hints}),
                    )
            work.result = result
            work.result_hash = sha256_hex(artifact.bytes("result.json"))
            self.proposals.save_new(result.proposals)
            self._set_stage(work, "compile", "done", key=key, clear_error=True)

    # -- assemble --------------------------------------------------------------------------

    def included(self) -> list[SourceWork]:
        return [
            self.work[sid]
            for sid in sorted(self.work)
            if self.work[sid].status == "ok" and self.work[sid].result is not None
        ]

    def _supersession(self, included: Sequence[SourceWork]) -> tuple[dict, dict]:
        pack = self.domain
        records = []
        for work in included:
            assert work.classification is not None and work.extract is not None
            name = PurePosixPath(work.item.raw_path).name
            text = work.extract.doc.text()[:_EXPLICIT_REFERENCE_CHARS]
            records.append(
                SupersessionRecord(
                    work.source_id,
                    work.classification.doc_number or parse_doc_number(pack, name, text),
                    work.classification.revision or parse_revision(pack, name, text),
                    tuple(explicit_references(pack, text)),
                )
            )
        _, pairs = resolve_supersession(pack, records)
        supersedes: dict[str, list[str]] = {}
        superseded_by: dict[str, list[str]] = {}
        for newer, older in pairs:
            supersedes.setdefault(newer, []).append(older)
            superseded_by.setdefault(older, []).append(newer)
        return supersedes, superseded_by

    def _previous_slugs(self) -> dict[str, str]:
        catalog = self.previous.catalog
        if catalog is None:
            return {}
        slugs: dict[str, str] = {}
        for page in catalog.pages:
            if page.type == "source" and page.path.startswith("sources/"):
                slugs[page.id] = page.path.removeprefix("sources/").removesuffix(".md")
        return slugs

    async def _cached_pages(
        self,
        stage: str,
        key: str,
        build: Callable[[], Any],
        stamp: DocwikiStamp,
        day: date,
    ) -> tuple[list[Page], list[CitedLocator], list[TopicSkip]]:
        artifact = self.artifacts.load(stage, key)
        if artifact is not None:
            self.clock.count(stage, cache_hits=1)
            pages = [
                restamp(page, stamp, day) for page in decode_pages(artifact.bytes("pages.json"))
            ]
            cited = decode_cited(artifact.bytes("cited.json"))
            skips = (
                decode_topic_skips(artifact.bytes("skips.json"))
                if "skips.json" in artifact.files
                else []
            )
            self.clock.count(stage, items=len(pages))
            return pages, cited, skips
        output = await build()
        pages, cited = list(output[0]), list(output[1])
        skips = list(output[2]) if len(output) > 2 else []
        files = {"pages.json": encode_pages(pages), "cited.json": encode_cited(cited)}
        if stage == "topics":
            files["skips.json"] = encode_topic_skips(skips)
        self.artifacts.save(stage, key, files)
        self.clock.count(stage, items=len(pages))
        return pages, cited, skips

    async def assemble(self) -> RunOutcome:
        self.check_lease()
        pack = self.domain
        engine = self.ctx.engine
        assert self.versions is not None
        included = self.included()
        created_at = self.ctx.now().astimezone(UTC).replace(microsecond=0)
        day = created_at.date()
        supersedes, superseded_by = self._supersession(included)
        stems = {w.source_id: PurePosixPath(w.item.raw_path).stem for w in included}
        slugs = assign_source_slugs(stems, self._previous_slugs())
        staging = self.ctx.scratch_dir / "staging" / self.run_id
        if staging.exists():
            shutil.rmtree(staging)
        writer = ReleaseWriter(
            staging,
            created_at=created_at,
            audience=self.audience,
            versions=self.versions,
            inputs=ReleaseInputs(
                sources={w.source_id: w.item.state.content_hash for w in included}
            ),
            run_id=self.run_id,
        )
        stamp = writer.stamp

        # injection containment: redacted documents for every downstream stage
        contained = self._containment(included)
        docs = {
            w.source_id: redact(w.extract.doc, contained[w.source_id], self.ctx.canaries)
            for w in included
            if w.extract is not None
        }

        # render (accounted in the compile stage)
        source_pages: dict[str, Page] = {}
        cited: list[CitedLocator] = []
        with stage_span("render", run_id=self.run_id):
            for work in included:
                assert work.result and work.extract and work.classification
                page, page_cited = engine.render_source_page(
                    work.result,
                    docs[work.source_id],
                    work.classification,
                    work.item.state,
                    slug=slugs[work.source_id],
                    stamp=stamp,
                    pack=pack,
                    supersedes=sorted(supersedes.get(work.source_id, [])),
                    superseded_by=sorted(superseded_by.get(work.source_id, [])),
                )
                fm = page.frontmatter
                if (
                    not isinstance(fm, SourceFrontmatter)
                    or fm.source_id != work.source_id
                    or page.path != source_page_path(slugs[work.source_id])
                ):
                    raise ValueError(
                        f"render_source_page returned an unexpected page for {work.source_id}"
                    )
                if fm.sensitivity != work.sensitivity:
                    page = replace_frontmatter(page, sensitivity=work.sensitivity)
                source_pages[work.source_id] = page
                cited.extend(page_cited)
        fingerprints = {sid: fingerprint(page) for sid, page in source_pages.items()}
        results = [work.result for work in included if work.result is not None]
        result_inputs = [f"result:{w.source_id}:{w.result_hash}" for w in included]
        page_inputs = [f"page:{sid}:{value}" for sid, value in sorted(fingerprints.items())]

        # entities
        self.check_lease()
        self.clock.start("entities")
        with stage_span("entities", run_id=self.run_id):
            key = self._key("entities", [*result_inputs, *page_inputs], tier="fast")
            entity_pages, entity_cited, _ = await self._cached_pages(
                "entities",
                key,
                lambda: engine.build_entity_pages(
                    results, source_pages, pack, self.ctx.llm, stamp=stamp
                ),
                stamp,
                day,
            )
        self.clock.finish("entities")

        # topics
        self.check_lease()
        self.clock.start("topics")
        states = {w.source_id: w.item.state for w in included}
        classifications = {
            w.source_id: w.classification for w in included if w.classification is not None
        }
        with stage_span("topics", run_id=self.run_id):
            state_inputs = [
                f"state:{sid}:{s.content_hash}:{s.sensitivity}:{s.revision_group}"
                for sid, s in sorted(states.items())
            ]
            class_inputs = [f"class:{w.source_id}:{w.class_hash}" for w in included]
            key = self._key(
                "topics",
                [
                    *result_inputs,
                    *page_inputs,
                    *state_inputs,
                    *class_inputs,
                    f"audience:{self.audience}",
                ],
                tier="smart",
            )
            topic_pages, topic_cited, topic_skips = await self._cached_pages(
                "topics",
                key,
                lambda: engine.build_topic_pages(
                    results,
                    source_pages,
                    states,
                    classifications,
                    pack,
                    self.ctx.llm,
                    audience=self.audience,  # type: ignore[arg-type]
                    stamp=stamp,
                ),
                stamp,
                day,
            )
        self.clock.finish("topics")
        cited.extend(entity_cited)
        cited.extend(topic_cited)

        # research answers filed in earlier releases
        query_pages, query_cited = carry_queries(
            self.previous.queries, source_pages, docs, stamp=stamp, day=day
        )
        cited.extend(query_cited)

        # links
        self.check_lease()
        self.clock.start("links")
        with stage_span("links", run_id=self.run_id):
            content = [*source_pages.values(), *entity_pages, *topic_pages, *query_pages]
            linked = apply_links(content, pack)
            content = linked.pages
            self.clock.count("links", items=len(content))
        self.clock.finish("links")

        # agent kit, placeholders and indexes
        tier = max_sensitivity(*(w.sensitivity or "public" for w in included))
        self.clock.start("agentkit")
        with stage_span("agentkit", run_id=self.run_id):
            kit = build_agent_kit(
                content,
                pack,
                stamp=stamp,
                updated=day,
                sensitivity=tier,
                audience=self.audience,
                max_steps=self.ctx.settings.research_max_tool_calls,
                templates_dir=self.ctx.templates_dir,
                canaries=self.ctx.canaries,
            )
            self.clock.count("agentkit", items=1 + len(kit.skills))
        self.clock.finish("agentkit")
        self.clock.start("indexes")
        removed = self._removed_reasons()
        entries = changes_since(self.previous.catalog, content, day=day, removed=removed)
        bundle = build_indexes(
            content,
            pack,
            stamp=stamp,
            updated=day,
            sensitivity=tier,
            run_id=self.run_id,
            previous_log=self.previous.log,
            new_entries=entries,
            topic_skips=topic_skips,
            extra_paths=[WikiFiles.AGENTS, WikiFiles.QUALITY, run_page_path(self.run_id)],
        )
        injections = [item for sid in sorted(contained) for item in contained[sid].items]
        quarantined = [
            QuarantineItem(w.source_id, w.item.raw_path, w.stage or "extract")
            for w in sorted(self.work.values(), key=lambda item: item.source_id)
            if w.status in ("quarantined", "failed")
            and allowed_for_audience(w.item.state.sensitivity, self.audience)
        ]
        quality = quality_page(
            None,
            stamp=stamp,
            updated=day,
            sensitivity=tier,
            audience=self.audience,
            run_id=self.run_id,
        )
        receipt = run_receipt_page(
            self._report("running"), stamp=stamp, updated=day, sensitivity=tier, final=False
        )
        pages = [*content, *bundle.pages, kit.agents, quality, receipt]
        pages = self._normalize_updated(pages, day)
        by_path = {page.path: page for page in pages}
        quality = by_path[quality.path]
        receipt = by_path[receipt.path]
        for page in pages:
            writer.write_page(page)
        writer.write_wiki_file(WikiFiles.LLMS, bundle.llms_txt)
        write_agent_kit(kit, writer.write_wiki_file)
        self.clock.count("indexes", items=len(bundle.pages) + 1)

        # evidence sidecars and tables
        self.check_lease()
        self.clock.start("evidence")
        with stage_span("evidence", run_id=self.run_id):
            self._write_evidence(writer, included, source_pages, cited, docs, contained)
        self.clock.finish("evidence")

        # catalog and search index
        edges = build_edges(pages)
        catalog = build_catalog(
            pages,
            edges,
            release_id=writer.release_id,
            audience=self.audience,
            generated_at=created_at,
            glossary=bundle.glossary,
        )
        writer.write_catalog(catalog)
        blocks = []
        for work in included:
            page = source_pages[work.source_id]
            final_page = by_path[page.path]
            fm = final_page.frontmatter
            assert isinstance(fm, SourceFrontmatter) and work.extract is not None
            blocks.extend(
                blocks_from_extracted(
                    searchable(docs[work.source_id], contained[work.source_id]),
                    page_path=final_page.path,
                    title=fm.title,
                    sensitivity=fm.sensitivity,
                    status=fm.status,
                )
            )
        writer.write_search_db(
            [page for page in pages if not page.path.startswith("_meta/")],
            blocks,
            glossary_synonym_rows(pack),
        )
        self.clock.finish("indexes")

        # verify
        self.check_lease()
        self.clock.start("verify")
        considered = [
            w
            for w in self.work.values()
            if w.status != "excluded"
            and allowed_for_audience(w.sensitivity or w.item.state.sensitivity, self.audience)
        ]
        with stage_span("verify", run_id=self.run_id):
            verdict = verify_release(
                writer.root,
                audience=self.audience,
                canaries=self.ctx.canaries,
                glossary_seeded=bool(pack.glossary.terms),
                citations=[c for w in included if w.result for c in w.result.citations],
                sources_total=len(considered),
                quarantined=sum(1 for w in considered if w.status in ("quarantined", "failed")),
            )
        self.clock.count("verify", items=len(verdict.gates))
        self.clock.finish("verify", "done" if verdict.passed else "failed")

        # the site is built into the staged release (before finalize) when enabled
        want_site = self.want_site()
        site_skip = site_unavailable() if want_site else None
        if want_site and site_skip is None and not verdict.passed:
            site_skip = "blocking gates failed, the release will not be published"
        site_note: str | None = None
        if want_site:
            site_note = (
                f"Not built: {site_skip}."
                if site_skip
                else "Built from this release after the gates above were evaluated; its link "
                "check, security scan and canary scan must pass before publication."
            )
        quality_args: dict[str, Any] = {
            "stamp": stamp,
            "updated": quality.frontmatter.updated,
            "sensitivity": tier,
            "audience": self.audience,
            "run_id": self.run_id,
            "injections": injections,
            "quarantined": quarantined,
            "canaries": self.ctx.canaries,
        }
        writer.write_page(quality_page(verdict, site=site_note, **quality_args))

        # run receipt (final): the run until verification
        report = self._report("running", gates=verdict.gates, release_id=writer.release_id)
        receipt = run_receipt_page(
            report, stamp=stamp, updated=receipt.frontmatter.updated, sensitivity=tier
        )
        writer.write_page(receipt)

        # site
        site_error: str | None = None
        if want_site:
            self.check_lease()
            self.clock.start("site")
            result = (
                SiteResult("skipped", f"site not built: {site_skip}")
                if site_skip
                else build_site_for_release(
                    writer.root,
                    page_title=pack.info.wiki_title,
                    banner=pack.info.banner,
                    base_url=self.ctx.settings.site_base_url,
                )
            )
            message = scrub(result.message, self.ctx.canaries)
            if result.status == "built":
                findings = scan_canaries(
                    writer.root, self.ctx.canaries, under=[ReleaseFiles.SITE_DIR]
                )
                if findings:
                    verdict = extend_verdict(verdict, findings)
                    site_note = "Built, but the canary scan found injection canaries in it."
                    writer.write_page(quality_page(verdict, site=site_note, **quality_args))
                self.clock.count("site", items=1)
                self.clock.finish("site")
            elif result.status == "skipped":
                logger.warning("%s", message)
                self.clock.error("site", message)
                self.clock.finish("site", "skipped")
                if not site_skip:
                    writer.write_page(
                        quality_page(verdict, site=f"Not built: {message}.", **quality_args)
                    )
            else:
                site_error = message
                self.clock.error("site", message)
                self.clock.finish("site", "failed")
                writer.write_page(
                    quality_page(
                        verdict, site="The site build failed; see the run report.", **quality_args
                    )
                )

        # publish
        counts = self._counts(pages, writer)
        self.check_lease()
        self.clock.start("publish")
        if site_error:
            self.errors.append(site_error)
            staged = writer.finalize(gates=verdict.gates, counts=counts)
            self.clock.finish("publish", "skipped")
            return self._finish(
                "failed", gates=verdict.gates, release_id=staged.release_id, staged=staged.root
            )
        published = finalize_and_publish(
            writer,
            gates=verdict.gates,
            counts=counts,
            storage=self.ctx.storage if self.request.publish else None,
            canaries=self.ctx.canaries,
            retention=None,
            now=self.ctx.now(),
            glossary_seeded=bool(pack.glossary.terms),
        )
        if published.status == "blocked":
            self.errors.append(published.reason or "publish blocked")
            self.clock.finish("publish", "skipped")
            return self._finish(
                "failed",
                gates=verdict.gates,
                release_id=published.staged.release_id,
                staged=published.staged.root,
                deterministic=True,
            )
        if published.published:
            # the pointer is swapped: record the build state first, then prune (best effort)
            self._save_build_state(published.staged.release_id, pages)
            shutil.rmtree(published.staged.root, ignore_errors=True)
            self._retention()
        self.clock.finish("publish")
        return self._finish(
            "succeeded",
            gates=verdict.gates,
            release_id=published.staged.release_id,
            published=published.published,
            staged=None if published.published else published.staged.root,
        )

    def _retention(self) -> None:
        """Keep the newest releases; a failure is a warning (the next publish prunes again)."""
        outcome = try_retention(self.ctx.storage, keep=self.ctx.settings.retention)
        if outcome.error:
            self.warnings.append(
                "retention: old releases were not pruned (the next publish retries): "
                f"{outcome.error}"
            )
        elif outcome.deleted:
            logger.info("retention removed %d old release(s)", len(outcome.deleted))

    def _removed_reasons(self) -> dict[str, str]:
        reasons: dict[str, str] = {}
        for work in self.work.values():
            if work.status in ("quarantined", "failed"):
                reasons[work.source_id] = "the current version could not be processed"
            elif work.status == "excluded":
                reasons[work.source_id] = "the source is above the audience of this build"
        return reasons

    def _normalize_updated(self, pages: Sequence[Page], day: date) -> list[Page]:
        state = self._build_state() or {}
        previous = (
            state.get("pages", {}) if state.get("release_id") == self.previous.release_id else {}
        )
        result: list[Page] = []
        for page in pages:
            entry = previous.get(page.path)
            updated = day
            if entry and entry[0] == fingerprint(page):
                updated = date.fromisoformat(entry[1])
            if page.frontmatter.updated != updated:
                page = Page(
                    path=page.path,
                    frontmatter=page.frontmatter.model_copy(update={"updated": updated}),
                    body=page.body,
                )
            result.append(page)
        return result

    def raw_location(self, item: PlanItem) -> Path:
        """Local path of the raw file *without* downloading it (it may not exist yet)."""
        local = local_path_for(self.ctx.storage, item.key)
        if local is not None and local.is_file():
            return local
        return self.scratch_path(item)

    def _publishes_originals(self) -> bool:
        """Originals are published only by public builds of fictional (sample) packs."""
        return bool(self.domain.info.fictional) and self.audience == "public"

    def _containment(self, included: Sequence[SourceWork]) -> dict[str, Containment]:
        canaries = self.ctx.canaries
        # The raw bytes matter only for an original that would be published: everything else in
        # the release comes from the extracted (and scanned) text.
        scan_raw = bool(canaries) and self._publishes_originals()
        found: dict[str, Containment] = {}
        for work in included:
            assert work.extract is not None
            raw = self.materialize(work.item).read_bytes() if scan_raw else None
            found[work.source_id] = assess(work.extract.doc, work.result, canaries, raw=raw)
        return found

    @staticmethod
    def _evidence_needs_raw(
        work: SourceWork, cited: Sequence[CitedLocator], publish_original: bool
    ) -> bool:
        """Whether ``build_evidence`` reads the raw file of ``work``.

        It does for a published original, for a PDF/image page that the extract stage did not
        render and for figures that are not located on a page (DOCX/PPTX pictures are re-read
        from the file); everything else comes from the ExtractedDoc and the page renders.
        """
        if publish_original:
            return True
        assert work.extract is not None
        page_located = (PdfPageLocator, ImageRegionLocator)
        figures = work.extract.doc.figures
        if any(not isinstance(figure.locator, page_located) for figure in figures):
            return True
        pages = {
            locator.page
            for locator in [*(item.locator for item in cited), *(f.locator for f in figures)]
            if isinstance(locator, page_located)
        }
        return not pages <= set(work.extract.page_images)

    def _write_evidence(
        self,
        writer: ReleaseWriter,
        included: Sequence[SourceWork],
        source_pages: Mapping[str, Page],
        cited: Sequence[CitedLocator],
        docs: Mapping[str, ExtractedDoc],
        contained: Mapping[str, Containment],
    ) -> None:
        by_source: dict[str, list[CitedLocator]] = {}
        seen: set[tuple[str, str, tuple[str, ...]]] = set()
        for item in cited:
            marker = (item.source_id, item.key, item.block_ids)
            if marker in seen:
                continue
            seen.add(marker)
            by_source.setdefault(item.source_id, []).append(item)
        unknown = sorted(set(by_source) - set(source_pages))
        if unknown:
            raise ValueError(f"pages cite sources that are not in the release: {unknown}")
        publish_originals = self._publishes_originals()
        for work in included:
            assert work.extract is not None
            page = source_pages[work.source_id]
            sensitivity = page.frontmatter.sensitivity
            doc = docs[work.source_id]
            source_cited = by_source.get(work.source_id, [])
            publish_original = publish_originals and contained[work.source_id].publish_original
            raw_file = (
                self.materialize(work.item)
                if self._evidence_needs_raw(work, source_cited, publish_original)
                else self.raw_location(work.item)
            )
            written = self.ctx.engine.build_evidence(
                doc=doc,
                raw_file=raw_file,
                cited=source_cited,
                source_title=page.frontmatter.title,
                source_page_path=page.path,
                sensitivity=sensitivity,
                publish_original=publish_original,
                writer=writer,
                page_images=work.extract.page_images or None,
            )
            self.clock.count("evidence", items=len(written))
            if doc.tables:
                writer.write_tables(work.source_id, list(doc.tables), sensitivity)

    def _counts(self, pages: Sequence[Page], writer: ReleaseWriter) -> dict[str, int]:
        types: dict[str, int] = {}
        for page in pages:
            types[page.frontmatter.type] = types.get(page.frontmatter.type, 0) + 1
        evidence_root = writer.root / "evidence"
        sidecars = (
            sum(1 for path in evidence_root.rglob("*.md") if path.name != "index.md")
            if evidence_root.is_dir()
            else 0
        )
        tables_root = writer.root / "tables"
        tables = len(list(tables_root.rglob("*.parquet"))) if tables_root.is_dir() else 0
        return {
            "pages": len(pages),
            "sources": types.get("source", 0),
            "entities": types.get("entity", 0),
            "topics": types.get("topic", 0),
            "queries": types.get("query", 0),
            "evidence": sidecars,
            "tables": tables,
            "quarantined": sum(1 for w in self.work.values() if w.status == "quarantined"),
        }

    def _save_build_state(self, release_id: str, pages: Sequence[Page]) -> None:
        assert self.plan is not None
        state = {
            "release_id": release_id,
            "versions": self._versions_digest(),
            "options": self._options_digest(),
            "sources": {
                item.source_id: item.state.content_hash for item in self.plan.active_items()
            },
            "pages": {
                page.path: [fingerprint(page), page.frontmatter.updated.isoformat()]
                for page in pages
            },
        }
        self.ctx.storage.write_bytes(build_state_key(self.audience), json_bytes(state))

    # -- reports ---------------------------------------------------------------------------

    def _cu_usage(self) -> list[ContentUnderstandingUsage]:
        pages: dict[str, int] = {}
        for work in self.work.values():
            doc = work.extract.doc if work.extract else None
            if doc is None or not work.extracted_now:
                continue
            if doc.extraction.adapter == "content-understanding":
                analyzer = doc.extraction.analyzer or "prebuilt-layout"
                pages[analyzer] = pages.get(analyzer, 0) + (doc.metadata.page_count or 0)
        return [
            ContentUnderstandingUsage(analyzer=name, pages=count) for name, count in pages.items()
        ]

    def _report(
        self,
        status: str,
        *,
        gates: Sequence[GateResult] = (),
        release_id: str | None = None,
    ) -> RunReport:
        plan = self.plan
        now = self.ctx.now()
        duration = max(0.0, (now - self.started).total_seconds())
        counts = RunCounts()
        if plan is not None:
            counts = RunCounts(
                sources_total=len(plan.active_items()),
                new=len(plan.new),
                changed=len(plan.changed),
                deleted=len(plan.deleted),
                unchanged=len(plan.unchanged),
                quarantined=sum(1 for w in self.work.values() if w.status == "quarantined"),
                failed=sum(1 for w in self.work.values() if w.status == "failed"),
            )
        versions = self.versions or VersionInfo(
            docwiki=__version__,
            domain_pack=self.ctx.pack_path.name or "unknown",
            domain_pack_hash=self.pack_hash or "unknown",
        )
        return RunReport(
            run_id=self.run_id,
            kind=self.request.kind,
            requested_by=self.request.requested_by,
            status=status,  # type: ignore[arg-type]
            started_at=self.started,
            finished_at=None if status == "running" else now,
            audience=self.audience,  # type: ignore[arg-type]
            release_id=release_id,
            previous_release_id=self.previous.release_id,
            messages=self.request.messages,
            counts=counts,
            stages=self.clock.reports(),
            gates=list(gates),
            versions=versions,
            cost=cost_receipt(
                self.cursor, duration_s=duration, content_understanding=self._cu_usage()
            ),
            errors=list(self.errors),
            warnings=[*self.warnings, *self.ctx.notices()],
        )

    def _write_report(self, status: str, **kwargs: Any) -> RunReport:
        report = self._report(status, **kwargs)
        try:
            self.ctx.storage.write_bytes(
                run_report_key(self.run_id), report.to_json().encode("utf-8")
            )
        except StorageError as exc:
            logger.error("cannot write the run report %s: %s", self.run_id, exc)
        return report

    def _finish(
        self,
        status: Literal["succeeded", "failed", "no-op"],
        *,
        gates: Sequence[GateResult] = (),
        release_id: str | None = None,
        published: bool = False,
        staged: Path | None = None,
        deterministic: bool = False,
    ) -> RunOutcome:
        self.clock.abort()
        if deterministic:
            self.errors.append(DETERMINISTIC_NOTE)
        report = self._write_report(
            status, gates=gates, release_id=release_id if published else None
        )
        logger.info(
            "run %s %s (release %s, published=%s)", self.run_id, status, release_id, published
        )
        return RunOutcome(
            run_id=self.run_id,
            status=status,
            report=report,
            release_id=release_id,
            published=published,
            staged_root=staged,
            gates=list(gates),
            errors=list(self.errors),
            plan=self.plan,
            deterministic=deterministic,
        )

    def finish_no_op(self) -> RunOutcome:
        logger.info(
            "run %s: nothing changed since release %s", self.run_id, self.previous.release_id
        )
        return self._finish("no-op")

    def fail(self, exc: BaseException) -> RunOutcome:
        self.errors.append(_error_text(exc))
        logger.error("run %s failed: %s", self.run_id, _error_text(exc))
        return self._finish("failed", deterministic=is_deterministic(exc))


# -- research answers carried from the previous release ------------------------------------

_FOOTNOTE_REF_RE = re.compile(r"\[\^(?P<label>[^\]\s]+)\](?!:)")
_FOOTNOTE_DEF_LINE_RE = re.compile(r"^\[\^(?P<label>[^\]\s]+)\]:")


def _drop_footnotes(body: str, drop: set[str]) -> str:
    refs, _ = extract_footnotes(body)
    order: list[str] = []
    for label, _ in refs:
        if label not in drop and label not in order:
            order.append(label)
    mapping = {old: f"c{index}" for index, old in enumerate(order, start=1)}
    out: list[str] = []
    fence = False
    for line in body.split("\n"):
        if line.lstrip().startswith(("```", "~~~")):
            fence = not fence
            out.append(line)
            continue
        if fence:
            out.append(line)
            continue
        definition = _FOOTNOTE_DEF_LINE_RE.match(line)
        if definition:
            label = definition.group("label")
            if label in drop or label not in mapping:
                continue
            out.append(f"[^{mapping[label]}]:" + line[definition.end() :])
            continue
        out.append(
            _FOOTNOTE_REF_RE.sub(
                lambda m: (
                    ""
                    if m.group("label") in drop
                    else f"[^{mapping.get(m.group('label'), m.group('label'))}]"
                ),
                line,
            )
        )
    return "\n".join(out)


def carry_queries(
    queries: Sequence[Page],
    source_pages: Mapping[str, Page],
    docs: Mapping[str, Any],
    *,
    stamp: DocwikiStamp,
    day: date,
) -> tuple[list[Page], list[CitedLocator]]:
    """Research answers of the previous release, restamped, with their evidence re-cited.

    Citations whose source or locator is gone are removed and the page gets a warning banner
    (wiki-contract §9 withdrawal).
    """
    pages: list[Page] = []
    cited: list[CitedLocator] = []
    for query in queries:
        fm = query.frontmatter
        if not isinstance(fm, QueryFrontmatter):
            continue
        _, definitions = extract_footnotes(query.body)
        drop: set[str] = set()
        keep: list[CitedLocator] = []
        for definition in definitions:
            target = None
            for link in extract_links(definition.content):
                target = resolve_href(query.path, link.href).path
                break
            parts = (target or "").split("/")
            if len(parts) != 3 or parts[0] != "evidence":
                continue
            source_id, key = parts[1], parts[2].removesuffix(".md")
            doc = docs.get(source_id)
            blocks = [block for block in doc.blocks if block.locator_key == key] if doc else []
            if source_id not in source_pages or not blocks:
                drop.add(definition.label)
                continue
            keep.append(
                CitedLocator(
                    source_id=source_id,
                    locator=blocks[0].locator,
                    block_ids=tuple(block.id for block in blocks),
                    provenance=blocks[0].provenance,
                )
            )
        sources = [source_id for source_id in fm.sources if source_id in source_pages]
        page = restamp(query, stamp, day)
        if drop or len(sources) != len(fm.sources):
            body = _drop_footnotes(query.body, drop)
            if _WITHDRAWN_BANNER not in body:
                lines = body.split("\n")
                position = next(
                    (index + 1 for index, line in enumerate(lines) if line.startswith("# ")), 0
                )
                banner = f"{_WITHDRAWN_BANNER}; their citations were removed."
                lines[position:position] = ["", banner, ""]
                body = "\n".join(lines)
            tiers = [source_pages[s].frontmatter.sensitivity for s in sources]
            updates: dict[str, Any] = {"sources": sorted(sources)}
            if tiers:
                updates["sensitivity"] = max_sensitivity(*tiers)
            page = replace_frontmatter(
                Page(path=page.path, frontmatter=page.frontmatter, body=body), **updates
            )
        pages.append(page)
        cited.extend(keep)
    return pages, cited
