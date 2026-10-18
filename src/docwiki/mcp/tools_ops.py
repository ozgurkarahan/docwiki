"""Operations tools (role ``Wiki.Operate``) used by the Librarian agent.

They read the run-control state in ``work/`` (state shards, run reports, proposals, extraction
artifacts) and enqueue ``docwiki.ingest/v1`` messages; they never edit wiki content or releases.
Mutating tools (``ingest_start``, ``recompile``, ``decide_proposal``) are approved by a human in
the agent platform; ``write_health_report`` only writes ``work/reports/health-<date>.md``.
Accepting an entity, glossary or topic proposal is refused (``invalid_argument``) when the domain
pack recorded by the last ingest run (``work/state/domain-pack.json``) could not apply it.
"""

from __future__ import annotations

import re
import threading
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError

from docwiki.contracts._base import canonical_json, sha256_hex
from docwiki.contracts.enums import STAGE_NAMES
from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.ids import PROPOSAL_ID_RE, RUN_ID_RE, SOURCE_ID_RE
from docwiki.contracts.locators import locator_label
from docwiki.contracts.proposals import Proposal, parse_proposal
from docwiki.contracts.queue import QueueMessage, QueueScope
from docwiki.contracts.runs import RunReport
from docwiki.contracts.safety import detect_injection, sanitize_markdown
from docwiki.contracts.state import RETRY_ATTEMPTS, SourceState
from docwiki.contracts.storage import PreconditionFailedError
from docwiki.domain.loader import PackValidationError
from docwiki.domain.models import DomainPack
from docwiki.domain.overlay import Overlay, add_proposal, apply_overlay, filter_overlay
from docwiki.mcp.bounds import clip, fit_items, result_json
from docwiki.mcp.config import MAX_REPORT_CHARS, McpConfig
from docwiki.mcp.ingest_queue import IngestQueue, QueueReceipt
from docwiki.mcp.source import ReleaseSource, ReleaseUnavailableError, Snapshot
from docwiki.mcp.tools_read import ToolInputError
from docwiki.mcp.workstore import WorkStore

__all__ = ["SOURCE_STATUSES", "OpsTools", "overall_status"]

SOURCE_STATUSES = ("failed", "quarantined", "pending", "deleted", "done")
"""Derived per-source statuses, most urgent first."""

MAX_SOURCE_IDS = 50
MAX_HINT_CHARS = 2000
MAX_REASON_CHARS = 500
MAX_NOTE_CHARS = 1000
UNKNOWN_ENTITY_TYPE = "unknown"
"""Type the compile stage gives an entity proposal when the model could not guess one."""
_OVERLAY_FIELDS = {"entity": "entities", "glossary": "glossary", "topic": "topics"}
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def overall_status(state: SourceState) -> tuple[str, str | None]:
    """``(status, stage)``: the most urgent stage status, in pipeline order."""
    if state.deleted:
        return "deleted", None
    ordered = [stage for stage in STAGE_NAMES if stage in state.stages]
    for wanted in ("quarantined", "failed", "pending"):
        for stage in ordered:
            if state.stages[stage].status == wanted:
                return wanted, stage
    return ("done", None) if ordered else ("pending", None)


def _clean_text(value: str, limit: int, what: str, *, single_line: bool = False) -> str:
    text = _CONTROL_RE.sub("", value.replace("\r\n", "\n").replace("\r", "\n")).strip()
    if single_line:
        text = " ".join(text.split())
    if not text:
        raise ToolInputError(f"{what} must not be empty")
    if len(text) > limit:
        raise ToolInputError(
            f"{what} is longer than {limit} characters; shorten it", code="too_large"
        )
    return text


def _check_prefix(prefix: str) -> str:
    value = prefix.strip()
    if (
        not value
        or len(value) > 512
        or value.startswith("/")
        or "\\" in value
        or _CONTROL_RE.search(value)
        or any(part in (".", "..") for part in value.split("/"))
    ):
        raise ToolInputError(
            "prefix must be a relative POSIX path prefix inside raw/ (for example 'procedures/')"
        )
    return value


def _clip_tree(value: Any, limit: int = 400) -> Any:
    if isinstance(value, str):
        return clip(value, limit)
    if isinstance(value, list):
        return [_clip_tree(item, limit) for item in value[:50]]
    if isinstance(value, dict):
        return {key: _clip_tree(item, limit) for key, item in value.items()}
    return value


def _proposal_summary(proposal: Proposal) -> str:
    payload: Any = proposal.payload
    if proposal.kind == "entity":
        return f"new or updated entity {payload.type}:{payload.key} ({payload.label})"
    if proposal.kind == "glossary":
        return f"glossary term {payload.term!r}: {clip(payload.definition, 120)}"
    if proposal.kind == "topic":
        return f"topic {payload.slug} ({payload.title})"
    if proposal.kind == "injection":
        return (
            f"suspected prompt injection in {payload.source_id} block {payload.block_id}: "
            f"{clip(payload.reason, 160)}"
        )
    return f"recompile {len(payload.source_ids)} source(s)"


def _proposal_view(proposal: Proposal) -> dict[str, Any]:
    data = proposal.to_json_dict()
    return {
        "id": proposal.id,
        "kind": proposal.kind,
        "status": proposal.status,
        "summary": _proposal_summary(proposal),
        "payload": _clip_tree(data["payload"]),
        "evidence": data.get("evidence", []),
        "created_at": data.get("created_at"),
        "decided_by": data.get("decided_by"),
        "decided_at": data.get("decided_at"),
        "note": data.get("note"),
    }


def _receipt(receipt: QueueReceipt) -> dict[str, Any]:
    return {
        "queue": receipt.queue,
        "location": receipt.location,
        "message_id": receipt.message_id,
        "duplicate": receipt.duplicate,
    }


class OpsTools:
    """Implementation of the operations tools (no MCP types; easy to test directly)."""

    def __init__(
        self,
        source: ReleaseSource,
        config: McpConfig,
        *,
        store_factory: Callable[[], WorkStore],
        queue_factory: Callable[[], IngestQueue],
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.source = source
        self.config = config
        self._store_factory = store_factory
        self._queue_factory = queue_factory
        self._clock = clock or (lambda: datetime.now(UTC))
        self._store: WorkStore | None = None
        self._queue: IngestQueue | None = None
        self._lock = threading.Lock()

    @property
    def max_chars(self) -> int:
        return self.config.max_chars

    def store(self) -> WorkStore:
        with self._lock:
            if self._store is None:
                self._store = self._store_factory()
            return self._store

    def queue(self) -> IngestQueue:
        with self._lock:
            if self._queue is None:
                self._queue = self._queue_factory()
            return self._queue

    def _now(self) -> datetime:
        return self._clock().astimezone(UTC).replace(microsecond=0)

    def _snapshot(self) -> Snapshot | None:
        try:
            return self.source.current()
        except ReleaseUnavailableError:
            return None

    def _message(
        self,
        kind: str,
        scope: QueueScope,
        hints: dict[str, str],
        *,
        key_basis: dict[str, Any] | None = None,
    ) -> QueueMessage:
        now = self._now()
        basis = key_basis or {
            "kind": kind,
            "scope": scope.to_json_dict(),
            "hints": hints,
            "window": f"{now:%Y%m%dT%H}{now.minute // 10}",
        }
        key = f"librarian:{kind}:{sha256_hex(canonical_json(basis))[:16]}"
        return QueueMessage(
            kind=kind,  # type: ignore[arg-type]
            scope=scope,
            hints=hints,
            requested_by="librarian",
            idempotency_key=key,
            created_at=now,
        )

    def _source_ids(self, values: Sequence[str] | None, *, required: bool) -> list[str]:
        ids = sorted({value.strip() for value in values or [] if value.strip()})
        if required and not ids:
            raise ToolInputError("source_ids must list at least one source_id")
        if len(ids) > MAX_SOURCE_IDS:
            raise ToolInputError(f"at most {MAX_SOURCE_IDS} source_ids per call", code="too_large")
        bad = [value for value in ids if not SOURCE_ID_RE.match(value)]
        if bad:
            raise ToolInputError(
                f"invalid source_id(s): {', '.join(bad)} (expected 'src-' + 12 hex digits)"
            )
        snap = self._snapshot()
        in_release = {s.source_id for s in snap.catalog.sources} if snap else set()
        unknown = [
            sid for sid in ids if sid not in in_release and self.store().source_state(sid) is None
        ]
        if unknown:
            raise ToolInputError(
                f"unknown source_id(s): {', '.join(unknown)}; use list_sources to find them",
                code="not_found",
                details={"unknown": unknown},
            )
        return ids

    # --- enqueueing tools ----------------------------------------------------------------

    def ingest_start(
        self, reason: str, source_ids: Sequence[str] | None = None, prefix: str | None = None
    ) -> str:
        why = _clean_text(reason, MAX_REASON_CHARS, "reason", single_line=True)
        ids = self._source_ids(source_ids, required=False)
        scope = QueueScope(source_ids=ids, prefix=_check_prefix(prefix) if prefix else None)
        message = self._message("ingest", scope, {"reason": why})
        receipt = self.queue().send(message)
        return result_json(
            {
                "queued": not receipt.duplicate,
                "kind": "ingest",
                "scope": scope.to_json_dict(),
                "idempotency_key": message.idempotency_key,
                "created_at": message.to_json_dict()["created_at"],
                **_receipt(receipt),
                "next": (
                    "The ingest job starts after a short debounce; call run_status in a few "
                    "minutes and never report success before it shows status 'succeeded'."
                    if not receipt.duplicate
                    else "An identical request is already pending; no new message was queued."
                ),
            }
        )

    def recompile(self, source_ids: Sequence[str], hints: str) -> str:
        ids = self._source_ids(source_ids, required=True)
        notes = _clean_text(hints, MAX_HINT_CHARS, "hints")
        flags = detect_injection(notes)
        if flags:
            rules = ", ".join(sorted({flag.rule or flag.kind for flag in flags}))
            raise ToolInputError(
                f"hints look like instructions addressed to an AI system ({rules}); write "
                "factual operator notes about the source instead (layout, columns, language, "
                "known extraction problems, which revision is current)"
            )
        scope = QueueScope(source_ids=ids)
        message = self._message("recompile", scope, {"operator_notes": notes})
        receipt = self.queue().send(message)
        return result_json(
            {
                "queued": not receipt.duplicate,
                "kind": "recompile",
                "scope": scope.to_json_dict(),
                "operator_notes_chars": len(notes),
                "idempotency_key": message.idempotency_key,
                "created_at": message.to_json_dict()["created_at"],
                **_receipt(receipt),
                "next": "Call run_status later; the recompiled pages appear in the next release.",
            }
        )

    # --- runs and sources ------------------------------------------------------------------

    @staticmethod
    def _run_summary(report: RunReport) -> dict[str, Any]:
        data = report.to_json_dict()
        gates = Counter(gate.status for gate in report.gates)
        cost = report.cost
        return {
            "run_id": report.run_id,
            "kind": report.kind,
            "requested_by": report.requested_by,
            "status": report.status,
            "started_at": data["started_at"],
            "finished_at": data.get("finished_at"),
            "audience": report.audience,
            "release_id": report.release_id,
            "previous_release_id": report.previous_release_id,
            "messages": report.messages,
            "counts": data["counts"],
            "stages": [
                {
                    "stage": stage.stage,
                    "status": stage.status,
                    "duration_s": stage.duration_s,
                    "items": stage.items,
                    "cache_hits": stage.cache_hits,
                    "failures": stage.failures,
                    "errors": [clip(error, 300) for error in stage.errors[:3]],
                }
                for stage in report.stages
            ],
            "gates": {
                "summary": dict(sorted(gates.items())),
                "not_passing": [
                    {
                        "gate": gate.gate,
                        "name": gate.name,
                        "status": gate.status,
                        "blocking": gate.blocking,
                        "violations": gate.violations,
                    }
                    for gate in report.gates
                    if gate.status in ("fail", "warn")
                ],
            },
            "cost": {
                "currency": cost.currency,
                "total_cost": cost.total_cost,
                "duration_s": cost.duration_s,
                "llm": [
                    {
                        "role": usage.role,
                        "deployment": usage.deployment,
                        "calls": usage.calls,
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "cost": usage.cost,
                    }
                    for usage in cost.llm
                ],
                "content_understanding_pages": sum(u.pages for u in cost.content_understanding),
            },
            "errors": [clip(error, 400) for error in report.errors[:5]],
            "errors_total": len(report.errors),
            "warnings": [clip(warning, 400) for warning in report.warnings[:5]],
            "warnings_total": len(report.warnings),
        }

    def run_status(self, run_id: str | None = None) -> str:
        store = self.store()
        ids = store.run_ids()
        snap = self._snapshot()
        served = snap.release_id if snap else None
        if run_id:
            wanted = run_id.strip()
            if not RUN_ID_RE.match(wanted):
                raise ToolInputError(
                    f"invalid run_id {run_id!r} (expected run-YYYYMMDD-HHMMSS-<8 hex>)"
                )
            report = store.run_report(wanted)
            if report is None:
                raise ToolInputError(
                    f"unknown run {wanted}; recent runs: {', '.join(reversed(ids[-5:])) or 'none'}",
                    code="not_found",
                )
        elif not ids:
            return result_json(
                {
                    "runs": [],
                    "served_release_id": served,
                    "message": "No run report exists yet (work/runs/ is empty).",
                }
            )
        else:
            report = store.run_report(ids[-1])
            assert report is not None
        summary = self._run_summary(report)
        stages = summary.pop("stages")
        extra = {
            "served_release_id": served,
            "release_is_served": bool(report.release_id) and report.release_id == served,
            "recent_runs": list(reversed(ids[-5:])),
        }

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            return {**summary, "stages": list(items), "stages_truncated": truncated, **extra}

        out, _ = fit_items(stages, build, self.max_chars)
        return out

    def _source_rows(self) -> tuple[list[dict[str, Any]], bool, list[str]]:
        snap = self._snapshot()
        by_id = snap.catalog.page_by_id() if snap else {}
        in_release = {s.source_id: s for s in snap.catalog.sources} if snap else {}
        states, broken = self.store().source_states()
        rows: list[dict[str, Any]] = []
        for state in states:
            status, stage = overall_status(state)
            page = by_id.get(state.source_id)
            rows.append(
                {
                    "source_id": state.source_id,
                    "raw_path": state.raw_path,
                    "status": status,
                    "stage": stage,
                    "last_error": clip(state.last_error, 300),
                    "sensitivity": state.sensitivity,
                    "media_type": state.media_type,
                    "size": state.size,
                    "updated_at": state.to_json_dict()["updated_at"],
                    "stages": {
                        name: item.status
                        for name, item in state.stages.items()
                        if item.status != "done"
                    },
                    "in_release": state.source_id in in_release,
                    "page_path": page.path if page else None,
                    "wiki_status": page.status if page else None,
                }
            )
        if states:
            return rows, True, broken
        for source in in_release.values():
            page = by_id.get(source.source_id)
            rows.append(
                {
                    "source_id": source.source_id,
                    "raw_path": source.path,
                    "status": "done",
                    "stage": None,
                    "last_error": None,
                    "sensitivity": page.sensitivity if page else None,
                    "media_type": source.media_type,
                    "in_release": True,
                    "page_path": page.path if page else None,
                    "wiki_status": source.status,
                }
            )
        return rows, False, broken

    def list_sources(self, status: str | None = None, limit: int = 50, offset: int = 0) -> str:
        rows, from_state, broken = self._source_rows()
        counts = Counter(row["status"] for row in rows)
        if status:
            rows = [row for row in rows if row["status"] == status]
        rows.sort(key=lambda row: (SOURCE_STATUSES.index(row["status"]), row["raw_path"]))
        window = rows[offset : offset + limit]
        more = offset + limit < len(rows)

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "counts": {key: counts.get(key, 0) for key in SOURCE_STATUSES},
                "total": len(rows),
                "status_filter": status,
                "sources": list(items),
                "offset": offset,
                "truncated": truncated or more,
                "next_offset": offset + len(items) if truncated or more else None,
                "state_available": from_state,
            }
            if not from_state:
                payload["note"] = (
                    "No state shards in work/state/sources/; listing the sources of the served "
                    "release instead."
                )
            if broken:
                payload["unreadable_state_shards"] = broken[:10]
            return payload

        out, _ = fit_items(window, build, self.max_chars)
        return out

    def quality_report(self, release: str | None = None) -> str:
        snap = self._snapshot()
        if release and (snap is None or release.strip() != snap.release_id):
            try:
                manifest = self.source.manifest_for(release.strip())
            except KeyError:
                try:
                    known = self.source.release_ids()[-10:]
                except Exception:
                    known = []
                raise ToolInputError(
                    f"unknown release {release!r}; recent releases: {', '.join(known) or 'none'}",
                    code="not_found",
                ) from None
        elif snap is not None:
            manifest = snap.reader.manifest
        else:
            raise ToolInputError(
                "no release is available yet; check run_status", code="unavailable"
            )
        order = {"fail": 0, "warn": 1, "pass": 2, "skipped": 3}
        gates = sorted(manifest.gates, key=lambda gate: (order.get(gate.status, 9), gate.gate))
        rows = [
            {
                "gate": gate.gate,
                "name": gate.name,
                "blocking": gate.blocking,
                "status": gate.status,
                "violations": gate.violations,
                "metric": gate.metric,
                "threshold": gate.threshold,
                "rule": gate.message,
                "details": [
                    {
                        "code": item.code,
                        "severity": item.severity,
                        "path": item.path,
                        "line": item.line,
                        "message": clip(item.message, 200),
                    }
                    for item in gate.details[:5]
                ],
            }
            for gate in gates
        ]
        summary = Counter(gate.status for gate in manifest.gates)

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            return {
                "release_id": manifest.release_id,
                "served_release_id": snap.release_id if snap else None,
                "audience": manifest.audience,
                "created_at": manifest.to_json_dict()["created_at"],
                "run_id": manifest.run_id,
                "counts": manifest.counts,
                "summary": {
                    key: summary.get(key, 0) for key in ("pass", "fail", "warn", "skipped")
                },
                "blocking_failures": [gate.gate for gate in manifest.blocking_failures],
                "gates": list(items),
                "truncated": truncated,
            }

        out, _ = fit_items(rows, build, self.max_chars)
        return out

    def explain_source(self, source_id: str) -> str:
        sid = source_id.strip()
        if not SOURCE_ID_RE.match(sid):
            raise ToolInputError(
                f"invalid source_id {source_id!r} (expected 'src-' followed by 12 hex digits)"
            )
        store = self.store()
        state = store.source_state(sid)
        snap = self._snapshot()
        page = snap.catalog.page_by_id().get(sid) if snap else None
        catalog_source = (
            next((s for s in snap.catalog.sources if s.source_id == sid), None) if snap else None
        )
        if state is None and page is None and catalog_source is None:
            raise ToolInputError(
                f"unknown source {sid}; use list_sources to find source ids", code="not_found"
            )
        payload: dict[str, Any] = {"source_id": sid}
        if state is not None:
            status, stage = overall_status(state)
            payload.update(
                {
                    "raw_path": state.raw_path,
                    "status": status,
                    "failed_stage": stage if status in ("failed", "quarantined") else None,
                    "last_error": clip(state.last_error, 800),
                    "media_type": state.media_type,
                    "size": state.size,
                    "sensitivity": state.sensitivity,
                    "deleted": state.deleted,
                    "stages": [
                        {
                            "stage": name,
                            "status": item.status,
                            "error": clip(item.error, 500),
                            "updated_at": item.to_json_dict().get("updated_at"),
                        }
                        for name in STAGE_NAMES
                        if (item := state.stages.get(name)) is not None  # type: ignore[call-overload]
                    ],
                }
            )
            quarantine = state.quarantine
            if quarantine is not None:
                payload["quarantine"] = {
                    "stage": quarantine[0],
                    "retryable": quarantine[1].retryable,
                    "attempts": quarantine[1].attempts,
                    "max_attempts": RETRY_ATTEMPTS,
                    "retried_automatically": state.retry_pending,
                }
        else:
            payload["state"] = None
            payload["raw_path"] = catalog_source.path if catalog_source else None
        samples, extraction = self._extraction(store, state)
        payload["extraction"] = extraction
        payload["release"] = {
            "served_release_id": snap.release_id if snap else None,
            "in_release": page is not None,
            "page_path": page.path if page else None,
            "wiki_status": page.status if page else None,
            "evidence_sidecars": len(snap.reader.list_evidence(sid)) if snap and page else 0,
        }
        proposals, _ = store.proposals()
        payload["proposals"] = [
            {"id": p.id, "kind": p.kind, "status": p.status, "summary": _proposal_summary(p)}
            for p in proposals
            if sid in self._proposal_sources(p)
        ][:10]
        payload["next_steps"] = self._next_steps(payload)

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            return {**payload, "sample_blocks": list(items), "sample_blocks_truncated": truncated}

        out, _ = fit_items(samples, build, self.max_chars)
        return out

    @staticmethod
    def _proposal_sources(proposal: Proposal) -> set[str]:
        found = {item.source_id for item in proposal.evidence}
        payload: Any = proposal.payload
        if proposal.kind == "injection":
            found.add(payload.source_id)
        elif proposal.kind == "recompile":
            found.update(payload.source_ids)
        return found

    @staticmethod
    def _extraction(
        store: WorkStore, state: SourceState | None
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        extract = state.stages.get("extract") if state else None
        if extract is None or not extract.cache_key:
            return [], None
        doc: ExtractedDoc | None = None
        artifact = None
        for key, data in store.artifact_files("extract", extract.cache_key):
            try:
                doc = ExtractedDoc.from_json(data)
            except (ValidationError, ValueError):
                continue
            artifact = key
            break
        if doc is None:
            return [], {"artifact": None, "note": "no ExtractedDoc artifact found for this source"}
        samples = []
        for block in doc.blocks:
            if not block.text.strip():
                continue
            flags = sorted({flag.rule or flag.kind for flag in detect_injection(block.text)})
            samples.append(
                {
                    "block_id": block.id,
                    "kind": block.kind,
                    "locator_key": block.locator_key,
                    "locator_label": locator_label(block.locator),
                    "provenance": block.provenance,
                    "text": clip(block.text, 300),
                    "suspected_injection": flags,
                }
            )
            if len(samples) == 5:
                break
        info = {
            "artifact": artifact,
            "adapter": doc.extraction.adapter,
            "adapter_version": doc.extraction.adapter_version,
            "analyzer": doc.extraction.analyzer,
            "warnings": [clip(warning, 300) for warning in doc.extraction.warnings[:10]],
            "warnings_total": len(doc.extraction.warnings),
            "blocks": len(doc.blocks),
            "empty_blocks": sum(1 for block in doc.blocks if not block.text.strip()),
            "tables": len(doc.tables),
            "figures": len(doc.figures),
            "page_count": doc.metadata.page_count,
            "provenance_mix": dict(Counter(block.provenance for block in doc.blocks)),
        }
        return samples, info

    @staticmethod
    def _next_steps(payload: dict[str, Any]) -> list[str]:
        status = payload.get("status")
        stage = payload.get("failed_stage")
        steps: list[str] = []
        retry = payload.get("quarantine") or {}
        if status == "quarantined" and retry.get("retried_automatically"):
            steps.append(
                "The failure looks transient: the next ingest run retries this source "
                f"automatically (attempt {retry['attempts'] + 1} of {retry['max_attempts']}). "
                "Call ingest_start to retry now; do not propose a recompile for it."
            )
        if status in ("failed", "quarantined"):
            if stage == "extract":
                steps.append(
                    "Extraction failed: check the file (encrypted, corrupt, scan without text "
                    "layer). Replace it in raw/ and call ingest_start for this source."
                )
            else:
                steps.append(
                    f"Stage {stage} failed: read last_error and the sample blocks, then propose "
                    "recompile with precise operator notes (layout, columns, language)."
                )
        elif status == "pending":
            steps.append("Processing is pending: check run_status before acting.")
        elif status == "deleted":
            steps.append("The raw file was deleted; its pages are withdrawn in the next release.")
        if payload.get("proposals"):
            steps.append("Review the related proposals with list_proposals.")
        return steps

    # --- proposals and reports ---------------------------------------------------------------

    def list_proposals(self, status: str | None = None, limit: int = 20, offset: int = 0) -> str:
        proposals, broken = self.store().proposals()
        counts = Counter(p.status for p in proposals)
        selected = [p for p in proposals if not status or p.status == status]
        selected.sort(key=lambda p: (p.status != "open", p.to_json_dict()["created_at"], p.id))
        window = [_proposal_view(p) for p in selected[offset : offset + limit]]
        more = offset + limit < len(selected)

        def build(items: Sequence[dict[str, Any]], truncated: bool) -> dict[str, Any]:
            payload: dict[str, Any] = {
                "counts": {key: counts.get(key, 0) for key in ("open", "accepted", "rejected")},
                "status_filter": status,
                "total": len(selected),
                "proposals": list(items),
                "offset": offset,
                "truncated": truncated or more,
                "next_offset": offset + len(items) if truncated or more else None,
            }
            if broken:
                payload["unreadable"] = broken[:10]
            return payload

        out, _ = fit_items(window, build, self.max_chars)
        return out

    def decide_proposal(self, proposal_id: str, decision: str, note: str, *, actor: str) -> str:
        pid = proposal_id.strip()
        if not PROPOSAL_ID_RE.match(pid):
            raise ToolInputError(f"invalid proposal id {proposal_id!r} (expected prop-<12 hex>)")
        if decision not in ("accept", "reject"):
            raise ToolInputError("decision must be 'accept' or 'reject'")
        text = _clean_text(note, MAX_NOTE_CHARS, "note")
        store = self.store()
        found = store.proposal(pid)
        if found is None:
            raise ToolInputError(f"unknown proposal {pid}; use list_proposals", code="not_found")
        proposal, etag = found
        target = "accepted" if decision == "accept" else "rejected"
        already = proposal.status != "open"
        if already and proposal.status != target:
            raise ToolInputError(
                f"proposal {pid} is already {proposal.status}; decisions are final",
                code="conflict",
            )
        if not already:
            data = proposal.to_json_dict()
            data.update(
                status=target,
                decided_by=actor,
                decided_at=self._now().strftime("%Y-%m-%dT%H:%M:%SZ"),
                note=text,
            )
            updated = parse_proposal(data)
            if target == "accepted" and updated.kind in _OVERLAY_FIELDS:
                # refuse before recording the decision: the next ingest could not apply it
                overlay, _ = store.overlay()
                self._check_overlay_proposal(self._domain_pack(), overlay, updated)
            try:
                store.save_proposal(updated, if_match=etag)
            except PreconditionFailedError:
                raise ToolInputError(
                    f"proposal {pid} changed while deciding; call list_proposals and retry",
                    code="conflict",
                ) from None
            proposal = updated
        effects = self._apply(proposal) if proposal.status == "accepted" else []
        view = _proposal_view(proposal)
        return result_json(
            {
                "id": proposal.id,
                "kind": proposal.kind,
                "status": proposal.status,
                "decided_by": view["decided_by"],
                "decided_at": view["decided_at"],
                "note": view["note"],
                "already_decided": already,
                "effects": effects,
            }
        )

    def _domain_pack(self) -> DomainPack:
        pack = self.store().domain_pack()
        if pack is None:
            raise ToolInputError(
                "the domain pack used by the pipeline is not recorded yet (every ingest run "
                "writes work/state/domain-pack.json); call ingest_start, wait until run_status "
                "shows the run finished, then decide again",
                code="unavailable",
            )
        return pack

    @staticmethod
    def _check_overlay_proposal(pack: DomainPack, overlay: Overlay, proposal: Proposal) -> None:
        """Refuse an entity/glossary/topic proposal that the next ingest could not apply."""
        if proposal.kind == "entity":
            payload: Any = proposal.payload
            entity_type = payload.type
            known = sorted(item.key for item in pack.entities.types)
            if entity_type not in known:
                why = (
                    "the compiler could not tell what kind of entity it is"
                    if entity_type == UNKNOWN_ENTITY_TYPE
                    else "the domain pack does not define this entity type"
                )
                raise ToolInputError(
                    f"proposal {proposal.id} cannot be accepted: its entity type "
                    f"{entity_type!r} is not an entity type of the domain pack {pack.name!r} "
                    f"({why}; known types: {', '.join(known)}). Reject it, or ask an operator to "
                    "add the type to the pack's entities.yaml first.",
                    code="invalid_argument",
                    details={"entity_type": entity_type, "known_types": known},
                )
        usable, _ = filter_overlay(pack, overlay)
        try:
            apply_overlay(pack, add_proposal(usable, proposal))
        except PackValidationError as exc:
            problems = [error.message for error in exc.errors[:5]] or [str(exc)]
            raise ToolInputError(
                f"proposal {proposal.id} cannot be accepted: the domain pack {pack.name!r} "
                f"would not apply it ({problems[0]}). Reject it, or ask an operator to correct "
                "the domain pack first.",
                code="invalid_argument",
                details={"errors": problems},
            ) from None

    def _apply(self, proposal: Proposal) -> list[str]:
        payload: Any = proposal.payload
        if proposal.kind in _OVERLAY_FIELDS:
            store = self.store()
            pack = self._domain_pack()
            field = _OVERLAY_FIELDS[proposal.kind]
            for _ in range(3):
                overlay, etag = store.overlay()
                try:
                    item = getattr(add_proposal(Overlay(), proposal), field)[0]
                except PackValidationError:
                    item = None
                if item is not None and item in getattr(overlay, field):
                    return ["already present in work/state/overlay.yaml"]
                self._check_overlay_proposal(pack, overlay, proposal)
                try:
                    store.save_overlay(add_proposal(overlay, proposal), etag=etag)
                except PreconditionFailedError:
                    continue
                return ["merged into work/state/overlay.yaml (applied by the next ingest run)"]
            raise ToolInputError(
                "the overlay kept changing concurrently; call decide_proposal again with the "
                "same decision to finish applying it",
                code="conflict",
            )
        if proposal.kind == "recompile":
            hints = {"operator_notes": payload.hints} if payload.hints.strip() else {}
            message = self._message(
                "recompile",
                QueueScope(source_ids=sorted(set(payload.source_ids))),
                hints,
                key_basis={"proposal": proposal.id},
            )
            receipt = self.queue().send(message)
            state = "already queued" if receipt.duplicate else "queued"
            return [
                f"recompile of {len(payload.source_ids)} source(s) {state} ({receipt.location})"
            ]
        return ["recorded as confirmed; the flagged text stays neutralised in the wiki"]

    def write_health_report(self, markdown: str) -> str:
        if len(markdown) > MAX_REPORT_CHARS:
            raise ToolInputError(
                f"the report has {len(markdown)} characters; the limit is {MAX_REPORT_CHARS}. "
                "Summarise and link pages instead of quoting them.",
                code="too_large",
            )
        clean, findings = sanitize_markdown(
            markdown.replace("\r\n", "\n").replace("\r", "\n"), allow_markers=False
        )
        text = clean.strip()
        if not text:
            raise ToolInputError("the report is empty")
        day = self._now().date().isoformat()
        key, replaced = self.store().write_health_report(day, text + "\n")
        return result_json(
            {
                "written": key,
                "date": day,
                "chars": len(text) + 1,
                "replaced": replaced,
                "sanitized": bool(findings),
                "findings": dict(Counter(finding.kind for finding in findings)),
            }
        )
