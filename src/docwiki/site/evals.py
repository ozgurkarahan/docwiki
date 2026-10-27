"""The home page's evaluation panel (site.md §12.1): "wiki + agent vs RAG" in one small table.

The numbers come from ``evals/results/latest.json`` (``docwiki.evals.latest/v1``), the file that
``evals/scoreboard.py`` writes next to ``SCOREBOARD.md``: it already holds, per split and system,
the overall metrics (value, n, passed), the cost per question and the latency percentiles. This
module only picks the headline cells for the three systems the panel compares; it never recomputes
a metric. A missing, unreadable or foreign file gives ``None`` and the panel is left out.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

__all__ = [
    "EVALS_FILE",
    "LATEST_FORMAT",
    "PANEL_SYSTEMS",
    "SCOREBOARD_PATH",
    "default_evals_file",
    "eval_panel",
    "read_eval_panel",
]

LATEST_FORMAT = "docwiki.evals.latest/v1"
"""Same value as ``evals.scoreboard.LATEST_FORMAT`` (the evals package is not in the job image)."""
EVALS_FILE = "evals/results/latest.json"
"""Repository-relative path of the scoreboard's JSON (copied into the job image)."""
SCOREBOARD_PATH = "evals/SCOREBOARD.md"
"""Repository-relative path of the full scoreboard, linked from the panel."""
PANEL_SYSTEMS = ("docwiki-researcher", "baseline-long-context", "baseline-rag")
"""The systems of the panel, in the order shown: the wiki and its agent first."""
SPLIT = "dev"


def default_evals_file() -> Path | None:
    """``evals/results/latest.json`` of the source checkout (or image) this package runs from."""
    for parent in Path(__file__).resolve().parents:
        if (parent / "site" / "QUARTZ_VERSION").is_file():
            return parent / EVALS_FILE
    return None


def _metric(overall: Mapping[str, Any], key: str) -> dict[str, Any] | None:
    item = overall.get(key)
    if not isinstance(item, Mapping):
        return None
    value, n = item.get("value"), item.get("n")
    if not isinstance(value, int | float) or not isinstance(n, int) or n <= 0:
        return None
    passed = item.get("passed")
    return {
        "value": round(float(value), 4),
        "n": n,
        "passed": passed if isinstance(passed, int) else None,
    }


def _number(mapping: Any, key: str, digits: int) -> float | None:
    if not isinstance(mapping, Mapping):
        return None
    value = mapping.get(key)
    return round(float(value), digits) if isinstance(value, int | float) else None


def eval_panel(latest: Mapping[str, Any], repo_url: str) -> dict[str, Any] | None:
    """The panel's data from a ``latest.json`` payload, or ``None`` when it has nothing to show.

    Only complete-or-partial runs with status ``ok`` are listed; a split without the wiki's own
    system (``docwiki-researcher``) gives ``None``: the panel is a comparison against it.
    """
    if latest.get("format") != LATEST_FORMAT:
        return None
    split = (latest.get("splits") or {}).get(SPLIT)
    if not isinstance(split, Mapping):
        return None
    systems: list[dict[str, Any]] = []
    dates: list[str] = []
    questions: list[int] = []
    for name in PANEL_SYSTEMS:
        entry = split.get(name)
        if not isinstance(entry, Mapping) or entry.get("status") != "ok":
            continue
        overall = entry.get("overall") or {}
        cost = entry.get("cost")
        systems.append(
            {
                "system": name,
                "accuracy": _metric(overall, "answer_accuracy"),
                "numeric": _metric(overall, "numeric_exactness"),
                "costPerQuestion": _number(cost, "per_question_usd", 4),
                "pricesVerified": bool(isinstance(cost, Mapping) and cost.get("prices_verified")),
                "latencyP50": _number(entry.get("latency"), "p50_s", 1),
            }
        )
        if isinstance(entry.get("date"), str):
            dates.append(entry["date"])
        if isinstance(entry.get("questions"), int):
            questions.append(entry["questions"])
    if not any(item["system"] == PANEL_SYSTEMS[0] for item in systems):
        return None
    return {
        "split": SPLIT,
        "questions": max(questions) if questions else None,
        "date": max(dates) if dates else None,
        "systems": systems,
        "scoreboardUrl": f"{repo_url.rstrip('/')}/blob/main/{SCOREBOARD_PATH}",
    }


def read_eval_panel(path: Path | None, repo_url: str) -> dict[str, Any] | None:
    """:func:`eval_panel` of the file at ``path``; ``None`` when it is missing or unreadable."""
    if path is None:
        return None
    try:
        latest = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return eval_panel(latest, repo_url) if isinstance(latest, Mapping) else None
