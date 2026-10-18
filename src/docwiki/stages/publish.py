"""Stage 13 — ``publish``: finalize the release, publish it atomically and keep the last N.

``ReleaseWriter.finalize`` hashes every file into ``manifest.json`` with the gate results; the
finalized folder is validated once more (manifest included); then
:func:`docwiki.release.publish_release` uploads it to the work storage (manifest last) and swaps
``releases/current.json`` with ``If-Match``; retention of old releases follows, best effort. A
release with a failing blocking gate is never published and the previous release stays current.

This module also renders the run receipt page ``_meta/runs/<run_id>.md`` (architecture §7).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal

from docwiki.contracts.gates import GateResult, Violation
from docwiki.contracts.manifest import CurrentPointer
from docwiki.contracts.pages import DocwikiStamp, Page
from docwiki.contracts.runs import RunReport
from docwiki.contracts.storage import Storage
from docwiki.release.publish import publish_release
from docwiki.release.validate import validate_release
from docwiki.release.writer import ReleaseWriter, StagedRelease
from docwiki.stages.indexes import meta_page, run_page_path
from docwiki.stages.links import inline_text

__all__ = [
    "STAGE_VERSION",
    "PublishResult",
    "finalize_and_publish",
    "run_receipt_page",
]

STAGE_VERSION = "1"


@dataclass
class PublishResult:
    status: Literal["published", "blocked", "dry-run"]
    staged: StagedRelease
    pointer: CurrentPointer | None = None
    reason: str | None = None
    final_violations: list[Violation] = field(default_factory=list)

    @property
    def published(self) -> bool:
        return self.status == "published"


def finalize_and_publish(
    writer: ReleaseWriter,
    *,
    gates: Sequence[GateResult],
    counts: dict[str, int],
    storage: Storage | None,
    canaries: Sequence[str] = (),
    retention: int | None = 10,
    now: datetime | None = None,
    glossary_seeded: bool = False,
) -> PublishResult:
    """Finalize ``writer`` and publish it unless a blocking gate failed.

    ``storage=None`` finalizes and validates without publishing (dry run). Retention is best
    effort after the pointer swap; ``retention=None`` leaves it to the caller
    (:func:`docwiki.release.try_retention`), e.g. after recording the build state.
    """
    staged = writer.finalize(gates=list(gates), counts=counts)
    blocking = [gate for gate in gates if gate.blocks_publish]
    if blocking:
        names = ", ".join(f"{gate.gate} ({gate.name})" for gate in blocking)
        return PublishResult("blocked", staged, reason=f"blocking gates failed: {names}")
    final = validate_release(
        staged.root,
        canaries=list(canaries),
        audience=staged.manifest.audience,
        glossary_seeded=glossary_seeded or None,
    )
    errors = [violation for violation in final if violation.severity == "error"]
    if errors:
        first = errors[0]
        return PublishResult(
            "blocked",
            staged,
            reason=f"final validation failed: {first.gate} {first.code} {first.path}: "
            f"{first.message}",
            final_violations=final,
        )
    if storage is None:
        return PublishResult("dry-run", staged, final_violations=final)
    pointer = publish_release(storage, staged, keep=retention, now=now)
    return PublishResult("published", staged, pointer=pointer, final_violations=final)


def _seconds(value: float) -> str:
    return f"{value:.2f}"


def _code(value: object) -> str:
    """Text for a code span (backticks, pipes and line breaks removed)."""
    return " ".join(str(value).replace("`", "'").replace("|", "/").split())


def _money(value: float | None) -> str:
    return "unpriced" if value is None else f"{value:.6f}"


def _total(value: float | None) -> str:
    return "not available (unpriced calls)" if value is None else f"{value:.6f} USD"


def run_receipt_page(
    report: RunReport,
    *,
    stamp: DocwikiStamp,
    updated: date,
    sensitivity: str,
    final: bool = True,
) -> Page:
    """``_meta/runs/<run_id>.md``: durations, cache hits, tokens, costs and versions."""
    lines = [f"# Run {report.run_id}", ""]
    if not final:
        lines += ["The receipt of this run is written when its quality gates are known.", ""]
    started = report.started_at.strftime("%Y-%m-%d %H:%M:%S UTC")
    counts = report.counts
    lines += [
        f"- Kind: {report.kind}, requested by {report.requested_by}, "
        f"{report.messages} queue {'message' if report.messages == 1 else 'messages'}",
        f"- Started: {started}; duration until verification: {_seconds(report.cost.duration_s)} s",
        f"- Release: `{stamp.release}`"
        + (
            f"; previous release `{report.previous_release_id}`"
            if report.previous_release_id
            else ""
        ),
        f"- Audience: {report.audience}",
        f"- Sources: {counts.sources_total} total, {counts.new} new, {counts.changed} changed, "
        f"{counts.deleted} deleted, {counts.unchanged} unchanged, {counts.quarantined} "
        f"quarantined, {counts.failed} failed",
        "",
        "## Stages",
        "",
        "| Stage | Status | Items | Cache hits | Failures | Duration (s) |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for stage in report.stages:
        lines.append(
            f"| {stage.stage} | {stage.status} | {stage.items} | {stage.cache_hits} | "
            f"{stage.failures} | {_seconds(stage.duration_s)} |"
        )
    if report.gates:
        failed = [gate.gate for gate in report.gates if gate.status == "fail"]
        warned = [gate.gate for gate in report.gates if gate.status == "warn"]
        summary = (
            "all blocking gates passed"
            if not any(g.blocks_publish for g in report.gates)
            else ("blocking gates failed: " + ", ".join(failed))
        )
        if warned:
            summary += "; warnings: " + ", ".join(warned)
        lines += [
            "",
            "## Gates",
            "",
            f"{summary.capitalize()} (see the [quality report](../quality.md)).",
        ]
    cost = report.cost
    lines += [
        "",
        "## Cost receipt",
        "",
        "| Tier | Deployment | Model | Calls | Input tokens | Cached input | Output tokens "
        "| Cost (USD) |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for usage in cost.llm:
        lines.append(
            f"| {usage.role} | `{_code(usage.deployment)}` | `{_code(usage.model)}` | "
            f"{usage.calls} | {usage.input_tokens} | {usage.cached_input_tokens} | "
            f"{usage.output_tokens} | {_money(usage.cost)} |"
        )
    if not cost.llm:
        lines.append("| - | - | - | 0 | 0 | 0 | 0 | 0.000000 |")
    for item in cost.content_understanding:
        lines += [
            "",
            f"Content Understanding (`{_code(item.analyzer)}`): {item.pages} pages, "
            f"cost {_total(item.cost)}.",
        ]
    lines += [
        "",
        f"Total estimated cost: {_total(cost.total_cost)} (price table "
        f"`{_code(cost.price_table)}`).",
    ]
    for note in cost.notes:
        lines.append(f"- {inline_text(note)}")
    versions = report.versions
    lines += [
        "",
        "## Versions",
        "",
        f"- DocWiki {_code(versions.docwiki)}, wiki schema {versions.wiki_schema}",
        f"- Domain pack `{_code(versions.domain_pack)}` (`{versions.domain_pack_hash[:12]}`)",
    ]
    for role, model in sorted(versions.models.items()):
        version = f" version `{_code(model.version)}`" if model.version else ""
        lines.append(
            f"- Model {role}: deployment `{_code(model.deployment)}`, model "
            f"`{_code(model.model)}`{version}"
        )
    for name, value in sorted(versions.prompts.items()):
        lines.append(f"- Prompt `{_code(name)}`: `{_code(value)}`")
    for name, value in sorted(versions.extractors.items()):
        lines.append(f"- Stage `{_code(name)}`: `{_code(value)}`")
    if report.errors:
        lines += [
            "",
            "## Errors",
            "",
            f"{len(report.errors)} {'error' if len(report.errors) == 1 else 'errors'} recorded; "
            "the details are in the run report of the work storage "
            f"(`work/runs/{report.run_id}/report.json`).",
        ]
    if report.warnings:
        count = len(report.warnings)
        lines += [
            "",
            "## Warnings",
            "",
            f"{count} {'warning' if count == 1 else 'warnings'} recorded; the details are in the "
            f"run report of the work storage (`work/runs/{report.run_id}/report.json`).",
        ]
    return meta_page(
        f"meta:runs/{report.run_id}",
        run_page_path(report.run_id),
        f"Run {report.run_id}",
        "Run receipt: durations, cache hits, tokens, costs and versions.",
        "\n".join(lines) + "\n",
        stamp=stamp,
        updated=updated,
        sensitivity=sensitivity,
    )
