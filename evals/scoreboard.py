"""Scoreboard (docs/spec/evals.md §3): the latest result of every system, as JSON and Markdown.

    uv run python evals/scoreboard.py           # latest.json, SCOREBOARD.md and the README block
    uv run python evals/scoreboard.py --check   # exit 1 when one of them is out of date

The Markdown table (systems × metrics with denominators, plus tokens, cost and latency) is written
to ``evals/SCOREBOARD.md`` between ``<!-- scoreboard:start -->`` and ``<!-- scoreboard:end -->``;
a compact variant (headline metrics, cost and median latency, with a link to the full table) is
injected into ``README.md`` between the same markers when the README has them. Dev and holdout
results are reported in separate tables; holdout results only ever carry aggregates.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

if __package__ in (None, ""):  # run as a script: make the repository root importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals import RESULT_FORMAT
from evals.metrics import BINARY_METRICS, METRICS

__all__ = [
    "END_MARKER",
    "LATEST_FORMAT",
    "START_MARKER",
    "build_latest",
    "format_metric",
    "inject",
    "main",
    "render_markdown",
    "snippet",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
LATEST_FORMAT = "docwiki.evals.latest/v1"
LATEST_NAME = "latest.json"
START_MARKER = "<!-- scoreboard:start -->"
END_MARKER = "<!-- scoreboard:end -->"
SYSTEM_ORDER = ("docwiki-researcher", "docwiki-local", "baseline-rag", "baseline-long-context")
DASH = "–"


# ------------------------------------------------------------------------------ results


def load_results(results_dir: Path) -> list[tuple[str, dict[str, Any]]]:
    """Every result file of ``results_dir`` (``latest.json`` and foreign JSON ignored)."""
    found: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(Path(results_dir).glob("*.json")):
        if path.name == LATEST_NAME:
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(data, dict) and data.get("format") == RESULT_FORMAT:
            found.append((path.name, data))
    return found


def _rank(result: Mapping[str, Any]) -> tuple[bool, bool, str]:
    run = result.get("run") or {}
    return (
        result.get("status") in ("ok", "skipped"),
        bool(run.get("complete")),
        str(run.get("started_at") or ""),
    )


def _summary(name: str, result: Mapping[str, Any]) -> dict[str, Any]:
    run = result.get("run") or {}
    versions = result.get("versions") or {}
    aggregates = result.get("aggregates") or {}
    judge = result.get("judge") or {}
    entry: dict[str, Any] = {
        "file": name,
        "status": result.get("status"),
        "skipped": result.get("skipped"),
        "date": run.get("date"),
        "started_at": run.get("started_at"),
        "questions": run.get("questions"),
        "questions_total": run.get("questions_total"),
        "complete": run.get("complete"),
        "overall": aggregates.get("overall"),
        "by_category": aggregates.get("by_category"),
        "cost": result.get("cost"),
        "latency": result.get("latency"),
        "judge": judge.get("summary"),
        "versions": {
            "git_sha": versions.get("git_sha"),
            "release_id": versions.get("release_id"),
            "metrics": versions.get("metrics"),
            "system": versions.get("system"),
        },
    }
    if "failures" in result:
        entry["failures"] = result["failures"]
        entry["errors"] = result.get("errors", [])
    return entry


def build_latest(results_dir: Path) -> dict[str, Any]:
    """The latest result per split and system: complete runs first, then the newest."""
    best: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for name, result in load_results(results_dir):
        key = (str(result.get("split")), str(result.get("system")))
        if key not in best or _rank(result) > _rank(best[key][1]):
            best[key] = (name, result)
    splits: dict[str, dict[str, Any]] = {}
    for (split, system), (name, result) in sorted(best.items()):
        splits.setdefault(split, {})[system] = _summary(name, result)
    return {"format": LATEST_FORMAT, "splits": splits}


# ----------------------------------------------------------------------------- markdown


def format_metric(summary: Mapping[str, Any] | None, *, binary: bool) -> str:
    """``72.7 % (24/33)`` for 0/1 metrics, ``81.2 % (n=31)`` for shares, ``–`` when n = 0."""
    if not summary or not summary.get("n") or summary.get("value") is None:
        return DASH
    percent = f"{float(summary['value']) * 100:.1f} %"
    if binary:
        return f"{percent} ({summary.get('passed', 0)}/{summary['n']})"
    return f"{percent} (n={summary['n']})"


def _tokens(cost: Mapping[str, Any] | None, questions: int | None) -> str:
    if not cost or not questions:
        return DASH
    total = int(cost.get("input_tokens") or 0) + int(cost.get("output_tokens") or 0)
    per_question = total / questions
    return f"{per_question / 1000:.1f}k" if per_question >= 1000 else f"{per_question:.0f}"


def _cost(cost: Mapping[str, Any] | None) -> str:
    if not cost or cost.get("estimated_cost_usd") is None:
        return "n/a"
    mark = "" if cost.get("prices_verified") else "*"
    per_question = cost.get("per_question_usd")
    total = float(cost["estimated_cost_usd"])
    if per_question is None:
        return f"${total:.2f}{mark}"
    return f"${float(per_question):.4f}/q (${total:.2f}){mark}"


def _latency(latency: Mapping[str, Any] | None) -> str:
    if not latency or latency.get("p50_s") is None:
        return DASH
    return f"{float(latency['p50_s']):.1f} s / {float(latency['p95_s']):.1f} s"


def _judge(judge: Mapping[str, Any] | None) -> str:
    score = (judge or {}).get("answer_score") or {}
    if not score.get("n") or score.get("mean") is None:
        return DASH
    return f"{float(score['mean']):.2f} (n={score['n']})"


def _run(entry: Mapping[str, Any]) -> str:
    versions = entry.get("versions") or {}
    parts = [str(entry.get("date") or "?")]
    if versions.get("git_sha"):
        parts.append(f"`{str(versions['git_sha'])[:7]}`")
    if versions.get("release_id"):
        parts.append(f"release `{versions['release_id']}`")
    if not entry.get("complete") and entry.get("status") == "ok":
        parts.append(f"partial {entry.get('questions')}/{entry.get('questions_total')}")
    return " · ".join(parts)


def _systems(split: Mapping[str, Any]) -> list[str]:
    known = [name for name in SYSTEM_ORDER if name in split]
    return known + sorted(name for name in split if name not in SYSTEM_ORDER)


_HEADER = (
    ["System"]
    + [title for _, title in METRICS]
    + ["Judge answer score", "Tokens / question", "Cost (USD)", "Latency p50 / p95", "Run"]
)


def _row(system: str, entry: Mapping[str, Any]) -> list[str]:
    if entry.get("status") == "skipped":
        skipped = entry.get("skipped") or {}
        reason = str(skipped.get("reason") or "skipped")
        detail = ""
        if skipped.get("estimated_tokens") and skipped.get("budget_tokens"):
            detail = (
                f" (≈{int(skipped['estimated_tokens']):,} tokens > budget "
                f"{int(skipped['budget_tokens']):,})"
            )
        cells = [f"skipped: {reason}{detail}"] + [DASH] * (len(_HEADER) - 3)
        return [f"`{system}`", *cells, _run(entry)]
    overall = entry.get("overall") or {}
    cells = [format_metric(overall.get(key), binary=key in BINARY_METRICS) for key, _ in METRICS]
    return [
        f"`{system}`",
        *cells,
        _judge(entry.get("judge")),
        _tokens(entry.get("cost"), entry.get("questions")),
        _cost(entry.get("cost")),
        _latency(entry.get("latency")),
        _run(entry),
    ]


def _table(split: Mapping[str, Any]) -> list[str]:
    lines = ["| " + " | ".join(_HEADER) + " |", "|" + "---|" * len(_HEADER)]
    for system in _systems(split):
        lines.append("| " + " | ".join(_row(system, split[system])) + " |")
    return lines


_COMPACT_METRICS = (
    "answer_accuracy",
    "numeric_exactness",
    "citation_precision",
    "citation_recall",
    "abstention_accuracy",
    "injection_resistance",
    "restricted_exclusion",
)


def _compact_table(split: Mapping[str, Any]) -> list[str]:
    """README variant: the headline metrics, cost and latency (details in SCOREBOARD.md)."""
    titles = dict(METRICS)
    header = ["System", *(titles[key] for key in _COMPACT_METRICS), "Cost (USD)", "Latency p50"]
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for system in _systems(split):
        entry = split[system]
        if entry.get("status") == "skipped":
            cells = [f"skipped: {(entry.get('skipped') or {}).get('reason') or 'skipped'}"]
            cells += [DASH] * (len(header) - 2)
        else:
            overall = entry.get("overall") or {}
            cells = [
                format_metric(overall.get(key), binary=key in BINARY_METRICS)
                for key in _COMPACT_METRICS
            ]
            cost = entry.get("cost") or {}
            per_question = cost.get("per_question_usd")
            mark = "" if cost.get("prices_verified") else "*"
            cells.append(DASH if per_question is None else f"${float(per_question):.3f}/q{mark}")
            p50 = (entry.get("latency") or {}).get("p50_s")
            cells.append(DASH if p50 is None else f"{float(p50):.1f} s")
        lines.append("| " + " | ".join([f"`{system}`", *cells]) + " |")
    return lines


def _failures(split: Mapping[str, Any]) -> list[str]:
    titles = dict(METRICS)
    lines: list[str] = []
    for system in _systems(split):
        entry = split[system]
        failures: Mapping[str, Mapping[str, Sequence[str]]] = entry.get("failures") or {}
        parts = []
        for key, title in titles.items():
            per_category = failures.get(key)
            if per_category:
                listed = "; ".join(
                    f"{category} {', '.join(ids)}" for category, ids in sorted(per_category.items())
                )
                parts.append(f"{title.lower()}: {listed}")
        if entry.get("errors"):
            parts.append(f"errors: {', '.join(entry['errors'])}")
        if parts:
            lines.append(f"- `{system}` — " + " · ".join(parts))
    return lines


def _questions(split: Mapping[str, Any]) -> int | None:
    totals = {
        entry.get("questions_total") for entry in split.values() if entry.get("questions_total")
    }
    return next(iter(totals)) if len(totals) == 1 else None


def render_markdown(latest: Mapping[str, Any], *, compact: bool = False) -> str:
    """The scoreboard block (without markers); ``compact`` is the README variant."""
    splits: Mapping[str, Any] = latest.get("splits") or {}
    lines = [] if compact else ["## Evaluation", ""]
    if not splits:
        lines += [
            "No evaluation results yet. Run `uv run python evals/run.py --system <system> "
            "--questions evals/golden/dev.jsonl`, then `uv run python evals/scoreboard.py` "
            "(see `evals/README.md`).",
        ]
        return "\n".join(lines) + "\n"
    lines += [
        "Each cell gives the score and its denominator: 0/1 metrics show passed / applicable "
        "questions, share metrics (coverage, citation precision and recall) the mean over the n "
        "applicable questions. Definitions, systems and honesty rules: `evals/README.md`.",
        "",
    ]
    ordered = [name for name in ("dev", "holdout") if name in splits]
    ordered += sorted(name for name in splits if name not in ordered)
    for name in ordered:
        split = splits[name]
        total = _questions(split)
        title = f"### {name.capitalize()} split"
        if name == "dev":
            title += " (`evals/golden/dev.jsonl`"
            title += f", {total} questions)" if total else ")"
        else:
            title += " (private questions, aggregates only"
            title += f", {total} questions)" if total else ")"
        lines += [title, "", *(_compact_table(split) if compact else _table(split)), ""]
        failures = [] if compact else _failures(split)
        if failures:
            lines += ["Failed question ids per metric and category:", "", *failures, ""]
    if compact:
        lines += [
            "Must-include coverage, tokens per question, p95 latency, versions, release ids and "
            "the ids of failed questions per metric and category: "
            "[evals/SCOREBOARD.md](evals/SCOREBOARD.md).",
            "",
        ]
    lines += _footnotes(splits)
    lines += [
        "Dev and holdout scores are reported separately and prompts are never tuned on holdout "
        "results. The baselines measure trade-offs; DocWiki is not presented as a replacement "
        "for retrieval systems.",
    ]
    return "\n".join(lines) + "\n"


def _footnotes(splits: Mapping[str, Any]) -> list[str]:
    unverified = any(
        (entry.get("cost") or {}).get("estimated_cost_usd") is not None
        and not (entry.get("cost") or {}).get("prices_verified")
        for split in splits.values()
        for entry in split.values()
    )
    if not unverified:
        return []
    return [
        "\\* Estimated with unverified prices (the packaged `prices.yaml` holds placeholders; "
        "see `src/docwiki/llm/README.md`).",
        "",
    ]


def snippet(latest: Mapping[str, Any]) -> str:
    return f"{START_MARKER}\n{render_markdown(latest)}{END_MARKER}\n"


def inject(text: str, block: str) -> str | None:
    """``text`` with the content between the markers replaced by ``block`` (``None`` when the
    markers are missing or out of order)."""
    start = text.find(START_MARKER)
    end = text.find(END_MARKER, start + len(START_MARKER)) if start >= 0 else -1
    if start < 0 or end < 0:
        return None
    return text[: start + len(START_MARKER)] + "\n" + block + text[end:]


# ---------------------------------------------------------------------------------- cli


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _read(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--results", type=Path, default=REPO_ROOT / "evals" / "results")
    parser.add_argument("--readme", type=Path, default=REPO_ROOT / "README.md")
    parser.add_argument("--snippet", type=Path, default=REPO_ROOT / "evals" / "SCOREBOARD.md")
    parser.add_argument("--check", action="store_true", help="exit 1 when an output is out of date")
    args = parser.parse_args(argv)

    latest = build_latest(args.results)
    latest_text = json.dumps(latest, ensure_ascii=False, indent=2) + "\n"
    block = render_markdown(latest, compact=True)
    snippet_text = snippet(latest)
    readme = _read(args.readme)
    readme_text = inject(readme, block) if readme is not None else None

    outputs = [(args.results / LATEST_NAME, latest_text), (args.snippet, snippet_text)]
    if readme_text is not None:
        outputs.append((args.readme, readme_text))
    stale = [path for path, text in outputs if _read(path) != text]
    if args.check:
        for path in stale:
            print(f"out of date: {path.name}", file=sys.stderr)
        return 1 if stale else 0
    for path, text in outputs:
        if path in stale:
            _write(path, text)
    if readme_text is None:
        print(
            f"{args.readme.name} has no {START_MARKER} / {END_MARKER} markers: the scoreboard "
            f"is in {args.snippet.name} only (add the markers to inject it).",
            file=sys.stderr,
        )
    systems = sum(len(split) for split in latest["splits"].values())
    print(f"scoreboard: {systems} result(s), {len(stale)} file(s) updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
