"""Text and JSON reports.

Redact mode (default when the environment variable ``CI`` is true) never prints matched text,
deny-list patterns, extracted values or locations inside documents: only the severity, the
rule, the file and the line.
"""

from __future__ import annotations

import json
from collections import Counter
from typing import Any

from . import __version__
from .model import Finding
from .scanner import ScanReport


def _where(finding: Finding, redact: bool) -> str:
    if finding.line is not None and (redact or finding.location == f"line {finding.line}"):
        return f"{finding.file}:{finding.line}"
    if redact or finding.location in {"path", "file", "configuration"}:
        return finding.file
    return f"{finding.file} [{finding.location}]"


def _finding_line(finding: Finding, redact: bool) -> str:
    head = f"{finding.severity:<7} rule={finding.rule}  {_where(finding, redact)}"
    if finding.sensitive and redact:
        return head
    text = f"{head}  {finding.message}"
    if not redact:
        if finding.match is not None:
            text += f': "{finding.match}"'
        if finding.detail:
            text += f' (in "{finding.detail}")'
    if finding.count > 1:
        text += f" x{finding.count}"
    return f"{text}  [{finding.id}]"


def _summary_line(report: ScanReport) -> str:
    outcome = "FAIL" if report.exit_code else "PASS"
    strict = " --strict" if report.strict else ""
    return (
        f"result: {report.errors} error(s), {report.warnings} warning(s), "
        f"{len(report.suppressed)} suppressed, {len(report.notices)} notice(s){strict} "
        f"-> {outcome} (exit {report.exit_code})"
    )


def render_text(report: ScanReport) -> str:
    stats = report.stats
    files = sum(value for key, value in stats.items() if key.startswith("files_"))
    names = ("worktree", "untracked", "site")
    parts = [f"{stats.get('files_' + name, 0)} {name}" for name in names]
    history = stats.get("history_commits")
    lines = [
        f"leakguard {__version__}: scanned {files} file(s) ({', '.join(parts)}); "
        f"history: {f'{history} commit(s)' if history is not None else 'not scanned'}; "
        f"deny-list patterns: {stats.get('denylist_patterns', 0)}"
        + ("; redacted output" if report.redact else "")
    ]
    lines.extend(_finding_line(finding, report.redact) for finding in report.findings)
    if report.notices:
        grouped = Counter(notice.message for notice in report.notices)
        lines.append(f"notices ({len(report.notices)}):")
        for message, count in sorted(grouped.items()):
            examples = [n.file for n in report.notices if n.message == message][:3]
            suffix = "" if report.redact else f" e.g. {', '.join(examples)}"
            lines.append(f"  {count} x {message}{suffix}")
    lines.append(_summary_line(report))
    return "\n".join(lines) + "\n"


def _finding_json(finding: Finding, redact: bool) -> dict[str, Any]:
    if finding.sensitive and redact:
        return {
            "rule": finding.rule,
            "severity": finding.severity,
            "file": finding.file,
            "line": finding.line,
            "source": finding.source,
        }
    data: dict[str, Any] = {
        "id": finding.id,
        "rule": finding.rule,
        "severity": finding.severity,
        "file": finding.file,
        "path": finding.path,
        "line": finding.line,
        "message": finding.message,
        "source": finding.source,
        "commit": finding.commit,
        "count": finding.count,
    }
    if not redact:
        data["location"] = finding.location
        data["match"] = finding.match
        data["detail"] = finding.detail
    return data


def render_json(report: ScanReport) -> str:
    payload = {
        "tool": "leakguard",
        "version": __version__,
        "strict": report.strict,
        "redacted": report.redact,
        "stats": report.stats,
        "summary": {
            "errors": report.errors,
            "warnings": report.warnings,
            "suppressed": len(report.suppressed),
            "notices": len(report.notices),
            "exit_code": report.exit_code,
        },
        "findings": [_finding_json(finding, report.redact) for finding in report.findings],
        "notices": [
            {"file": notice.file, "kind": notice.kind, "message": notice.message}
            for notice in report.notices
        ],
    }
    # ASCII-only JSON (non-ASCII as \uXXXX escapes) stays valid whatever the console or pipe
    # encoding is (Windows pipes use the locale code page).
    return json.dumps(payload, indent=2, ensure_ascii=True) + "\n"
