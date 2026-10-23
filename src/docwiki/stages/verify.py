"""Stage 11 — ``verify``: quality gates G01–G16 (pipeline §7) and ``_meta/quality.md``.

Structural gates come from :func:`docwiki.release.validate_release` on the candidate release;
this stage adds the gates that need pipeline data:

* G04 — share of *quoted* native-text and table citations whose quote was verified (citations
  without a quote are paraphrases: counted and reported separately, never part of the rate);
* G08 — canaries (``DOCWIKI_CANARIES`` and an optional ``<pack>/canaries.txt``): on top of the
  text scan of ``validate_release``, a byte-level scan of every release file (evidence originals,
  tables, ``search.db``, the built site…); :func:`extend_verdict` adds late findings, e.g. after
  the site is built;
* G10 — whether the pack seeds a glossary; G15 — share of quarantined sources;
* G16 — the locked trade vocabulary of the pack (``{locked term: [banned renderings]}``), passed
  to ``validate_release``; skipped when the pack locks no term.

Gate results go into the manifest and the quality report page; a failing blocking gate stops the
publish. The report never prints injected text: injection flags show the source id, the block id
and the reason only, with canaries scrubbed.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date
from pathlib import Path

from docwiki.contracts.gates import GATES, GateResult, Violation, gate_results
from docwiki.contracts.layout import WikiFiles
from docwiki.contracts.pages import DocwikiStamp, Page
from docwiki.contracts.safety import detect_injection
from docwiki.engine_types import VerifiedCitation
from docwiki.release.validate import validate_release
from docwiki.stages.indexes import meta_page, run_page_path
from docwiki.stages.links import inline_text, one_line

__all__ = [
    "CANARY_FILE",
    "G04_FAIL",
    "G04_WARN",
    "G15_WARN",
    "STAGE_VERSION",
    "CitationStats",
    "InjectionItem",
    "QuarantineItem",
    "VerifyResult",
    "citation_rate",
    "citation_stats",
    "contains_canary",
    "extend_verdict",
    "load_canaries",
    "quality_page",
    "safe_reason",
    "scan_canaries",
    "scrub",
    "verify_release",
]

STAGE_VERSION = "2"
CANARY_FILE = "canaries.txt"
G04_FAIL = 0.95
G04_WARN = 0.98
G15_WARN = 0.10
QUALITY_TITLE = "Quality report"
QUALITY_SUMMARY = "Gate results of this release."
MAX_FINDINGS = 40
MAX_REASON = 200
QUOTED_PROVENANCE = ("native-text", "deterministic-table")
GENERIC_REASON = "flagged as text addressed to AI systems"


def load_canaries(
    pack_path: Path | None = None, *, env: Mapping[str, str] | None = None
) -> tuple[str, ...]:
    """Canary strings: ``DOCWIKI_CANARIES`` (comma-separated) plus ``<pack>/canaries.txt``."""
    from docwiki.orchestration.settings import CANARIES_KEY

    source = os.environ if env is None else env
    values = [item.strip() for item in (source.get(CANARIES_KEY) or "").split(",")]
    if pack_path is not None:
        file = Path(pack_path) / CANARY_FILE
        if file.is_file():
            for line in file.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    values.append(stripped)
    return tuple(dict.fromkeys(value for value in values if value))


def scrub(text: str, canaries: Iterable[str]) -> str:
    """Replace canary strings (never echo them into generated pages)."""
    for canary in canaries:
        if canary:
            text = text.replace(canary, "[canary]")
    return text


def contains_canary(text: str, canaries: Iterable[str]) -> bool:
    return any(canary and canary in text for canary in canaries)


def safe_reason(reason: str, canaries: Sequence[str] = ()) -> str:
    """An injection reason fit for a page: no canary, no instruction-like text, bounded."""
    parts: list[str] = []
    for part in one_line(reason).split("; "):
        part = part.strip()
        if not part:
            continue
        if contains_canary(part, canaries) or detect_injection(part):
            part = GENERIC_REASON
        if part not in parts:
            parts.append(part)
    text = "; ".join(parts) or GENERIC_REASON
    if len(text) > MAX_REASON:
        text = text[: MAX_REASON - 1].rstrip() + "…"
    return inline_text(text)


@dataclass(frozen=True)
class CitationStats:
    """Citation counts of the compiled sources (G04 applies to quoted native citations only)."""

    verified: int = 0
    failed: int = 0
    paraphrases: int = 0
    unquoted_failed: int = 0
    other_quoted: int = 0

    @property
    def quoted(self) -> int:
        """Quoted native-text and deterministic-table citations (the G04 population)."""
        return self.verified + self.failed

    @property
    def rate(self) -> float | None:
        return self.verified / self.quoted if self.quoted else None


def citation_stats(citations: Iterable[VerifiedCitation]) -> CitationStats:
    """Count citations; failed ones (refs ``kf-failed`` / ``s-failed``) are included."""
    verified = failed = paraphrases = unquoted_failed = other = 0
    for citation in citations:
        if not (citation.quote or "").strip():
            if citation.status == "failed":
                unquoted_failed += 1
            else:
                paraphrases += 1
            continue
        if citation.provenance not in QUOTED_PROVENANCE:
            other += 1
        elif citation.status == "verified":
            verified += 1
        else:
            failed += 1
    return CitationStats(verified, failed, paraphrases, unquoted_failed, other)


def citation_rate(citations: Iterable[VerifiedCitation]) -> tuple[float | None, int, int]:
    """``(rate, verified, quoted)`` over quoted native-text and deterministic-table citations."""
    stats = citation_stats(citations)
    return stats.rate, stats.verified, stats.quoted


_ENCODINGS = ("utf-8", "utf-16-le", "utf-16-be")


def scan_canaries(
    root: Path, canaries: Sequence[str], *, under: Sequence[str] = ()
) -> list[Violation]:
    """Byte-level G08 scan of every file below ``root`` (or the given relative folders/files).

    Finds canaries in any file type (originals, tables, ``search.db``, site assets) encoded as
    UTF-8 or UTF-16; the text scan of ``validate_release`` covers Markdown/JSON/text only.
    """
    needles = [canary.encode(encoding) for canary in canaries if canary for encoding in _ENCODINGS]
    if not needles:
        return []
    root = Path(root)
    targets = [root / item for item in under] if under else [root]
    files: list[Path] = []
    for target in targets:
        if target.is_file():
            files.append(target)
        elif target.is_dir():
            files.extend(path for path in target.rglob("*") if path.is_file())
    found: list[Violation] = []
    for file in sorted(set(files)):
        data = file.read_bytes()
        if any(needle in data for needle in needles):
            found.append(
                Violation(
                    gate="G08",
                    code="canary-present",
                    message="injection canary found (byte scan)",
                    path=file.relative_to(root).as_posix(),
                )
            )
    return found


@dataclass
class VerifyResult:
    gates: list[GateResult]
    violations: list[Violation]
    metrics: dict[str, tuple[float | None, float | None]] = field(default_factory=dict)
    citations: CitationStats = field(default_factory=CitationStats)
    skipped: tuple[str, ...] = ()

    @property
    def blocking(self) -> list[GateResult]:
        return [gate for gate in self.gates if gate.blocks_publish]

    @property
    def passed(self) -> bool:
        return not self.blocking

    def counts(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for gate in self.gates:
            result[gate.status] = result.get(gate.status, 0) + 1
        return result


def _merge_canary_findings(
    violations: list[Violation], findings: Iterable[Violation]
) -> list[Violation]:
    reported = {(v.gate, v.path) for v in violations if v.gate == "G08"}
    merged = list(violations)
    for finding in findings:
        if (finding.gate, finding.path) not in reported:
            reported.add((finding.gate, finding.path))
            merged.append(finding)
    return merged


def extend_verdict(result: VerifyResult, findings: Iterable[Violation]) -> VerifyResult:
    """``result`` with late findings (e.g. the site scan) folded into the gate results."""
    violations = _merge_canary_findings(result.violations, findings)
    if len(violations) == len(result.violations):
        return result
    gates = gate_results(violations, skipped=result.skipped, metrics=result.metrics)
    return replace(result, gates=gates, violations=violations)


def verify_release(
    root: Path,
    *,
    audience: str,
    canaries: Sequence[str] = (),
    glossary_seeded: bool = False,
    citations: Iterable[VerifiedCitation] = (),
    sources_total: int = 0,
    quarantined: int = 0,
    require_manifest: bool = False,
    locked_terms: Mapping[str, Sequence[str]] | None = None,
) -> VerifyResult:
    """Run every gate on the release folder ``root`` (candidate or finalized).

    ``locked_terms`` (``{locked term: [banned renderings]}``) enables G16; without it the gate is
    skipped.
    """
    violations = list(
        validate_release(
            root,
            canaries=list(canaries),
            require_manifest=require_manifest,
            audience=audience,
            glossary_seeded=glossary_seeded or None,
            locked_terms=locked_terms or None,
        )
    )
    violations = _merge_canary_findings(violations, scan_canaries(root, canaries))
    metrics: dict[str, tuple[float | None, float | None]] = {}
    stats = citation_stats(citations)
    rate = stats.rate
    metrics["G04"] = (round(rate, 4) if rate is not None else None, G04_FAIL)
    if rate is not None and rate < G04_WARN:
        threshold = G04_FAIL if rate < G04_FAIL else G04_WARN
        violations.append(
            Violation(
                gate="G04",
                code="quote-verification",
                severity="error" if rate < G04_FAIL else "warning",
                message=f"{stats.verified} of {stats.quoted} quoted native-text/table citations "
                f"verified ({rate:.1%} < {threshold:.0%})",
            )
        )
    ratio = quarantined / sources_total if sources_total else 0.0
    metrics["G15"] = (round(ratio, 4), G15_WARN)
    if sources_total and ratio > G15_WARN:
        violations.append(
            Violation(
                gate="G15",
                code="quarantine-rate",
                severity="warning",
                message=f"{quarantined} of {sources_total} sources quarantined "
                f"({ratio:.0%} > {G15_WARN:.0%})",
            )
        )
    skipped: list[str] = []
    if not canaries:
        skipped.append("G08")
    if not glossary_seeded:
        skipped.append("G10")
    if not locked_terms:
        skipped.append("G16")
    gates = gate_results(violations, skipped=skipped, metrics=metrics)
    return VerifyResult(
        gates=gates,
        violations=violations,
        metrics=metrics,
        citations=stats,
        skipped=tuple(skipped),
    )


@dataclass(frozen=True)
class InjectionItem:
    """A block flagged as text addressed to AI systems (never its text)."""

    source_id: str
    block_id: str
    reason: str


@dataclass(frozen=True)
class QuarantineItem:
    source_id: str
    raw_path: str
    stage: str


def _cell(value: object) -> str:
    return "" if value is None else str(value)


def quality_page(
    result: VerifyResult | None,
    *,
    stamp: DocwikiStamp,
    updated: date,
    sensitivity: str,
    audience: str,
    run_id: str,
    injections: Sequence[InjectionItem] = (),
    quarantined: Sequence[QuarantineItem] = (),
    canaries: Sequence[str] = (),
    site: str | None = None,
) -> Page:
    """``_meta/quality.md``; with ``result=None`` a placeholder with the same frontmatter.

    ``site`` is a sentence on the site stage (built, not built and why), shown when the run
    builds a site.
    """
    path = WikiFiles.QUALITY
    run_link = f"[{run_id}]({run_page_path(run_id).removeprefix('_meta/')})"
    lines = [
        f"# {QUALITY_TITLE}",
        "",
        f"Release `{stamp.release}`, audience {audience}, built by run {run_link}.",
        "",
    ]
    if result is None:
        lines.append("The quality gates of this release have not been evaluated yet.")
    else:
        verdict = "passed" if result.passed else "failed"
        lines += [
            f"Blocking gates {verdict}. A failing blocking gate stops publication and keeps the "
            "previous release current.",
            "",
            "| Gate | Name | Blocking | Status | Metric | Threshold | Violations |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ]
        for gate in result.gates:
            lines.append(
                f"| {gate.gate} | {gate.name} | {'yes' if gate.blocking else 'no'} | "
                f"{gate.status} | {_cell(gate.metric)} | {_cell(gate.threshold)} | "
                f"{gate.violations} |"
            )
        findings = [v for v in result.violations if v.gate in GATES]
        if findings:
            lines += ["", "## Findings", ""]
            for violation in findings[:MAX_FINDINGS]:
                where = ""
                if violation.path:
                    location = violation.path + (f":{violation.line}" if violation.line else "")
                    where = f" `{scrub(location, canaries).replace('`', '')}`"
                text = violation.message
                if violation.gate == "G05":
                    # safety findings end with an excerpt of the offending text: never echo it
                    text = text.split(": ", 1)[0]
                message = inline_text(scrub(text, canaries))
                lines.append(
                    f"- {violation.gate} {violation.severity} {violation.code}{where}: {message}"
                )
            if len(findings) > MAX_FINDINGS:
                lines.append(f"- … and {len(findings) - MAX_FINDINGS} more")
        stats = result.citations
        rate = f" ({stats.rate:.1%})" if stats.rate is not None else ""
        lines += [
            "",
            "## Citations",
            "",
            "G04 applies to quoted native-text and table citations; citations without a quote "
            "are paraphrases and are counted separately.",
            "",
            f"- Quoted native-text/table citations verified: {stats.verified} of "
            f"{stats.quoted}{rate}",
            f"- Quoted native-text/table citations that failed: {stats.failed}",
            f"- Paraphrases (no quote, not verified): {stats.paraphrases}",
            f"- Citations without a quote that failed: {stats.unquoted_failed}",
            f"- Quoted citations of OCR or figure text: {stats.other_quoted}",
        ]
    if site:
        lines += ["", "## Site", "", inline_text(scrub(site, canaries))]
    if injections:
        lines += [
            "",
            "## Injection flags",
            "",
            "These blocks contain text addressed to AI systems. It was kept out of the compiled "
            "pages, the search index and the published originals.",
            "",
        ]
        unique = {(item.source_id, item.block_id): item for item in injections}
        for key in sorted(unique):
            item = unique[key]
            source_id, block_id = (value.replace("`", "") for value in key)
            lines.append(
                f"- source `{source_id}`, block `{block_id}`: {safe_reason(item.reason, canaries)}"
            )
    if quarantined:
        lines += ["", "## Quarantined sources", ""]
        for item in sorted(quarantined, key=lambda i: i.raw_path):
            raw = scrub(item.raw_path, canaries).replace("`", "")
            lines.append(f"- `{item.source_id}` (`{raw}`): failed at {item.stage}")
    return meta_page(
        "meta:quality",
        path,
        QUALITY_TITLE,
        QUALITY_SUMMARY,
        "\n".join(lines) + "\n",
        stamp=stamp,
        updated=updated,
        sensitivity=sensitivity,
    )
