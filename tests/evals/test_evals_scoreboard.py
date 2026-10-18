"""Scoreboard: latest result per system, Markdown with denominators, README injection."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from evals.scoreboard import (
    END_MARKER,
    START_MARKER,
    build_latest,
    format_metric,
    inject,
    main,
    render_markdown,
    snippet,
)

from evals import RESULT_FORMAT


def result(
    system: str,
    *,
    split: str = "dev",
    started: str = "2026-10-18T08:00:00Z",
    complete: bool = True,
    status: str = "ok",
    accuracy: float = 0.75,
) -> dict[str, Any]:
    overall = {
        "questions": 4,
        "errors": 0,
        "answer_accuracy": {"value": accuracy, "n": 4, "passed": round(accuracy * 4)},
        "must_include_coverage": {"value": 0.8125, "n": 4, "passed": 2},
        "numeric_exactness": {"value": 1.0, "n": 1, "passed": 1},
        "citation_precision": {"value": 0.5, "n": 3, "passed": 1},
        "citation_recall": {"value": 0.6667, "n": 3, "passed": 2},
        "abstention_accuracy": {"value": 1.0, "n": 4, "passed": 4},
        "injection_resistance": {"value": None, "n": 0, "passed": 0},
        "restricted_exclusion": {"value": 1.0, "n": 4, "passed": 4},
    }
    data: dict[str, Any] = {
        "format": RESULT_FORMAT,
        "system": system,
        "split": split,
        "status": status,
        "skipped": None,
        "run": {
            "started_at": started,
            "date": started[:10],
            "questions": 4 if complete else 2,
            "questions_total": 4,
            "complete": complete,
        },
        "versions": {"git_sha": "0123456789abcdef", "release_id": "20261018T080000Z-0a1b2c3d"},
        "aggregates": {"overall": overall, "by_category": {}},
        "cost": {
            "input_tokens": 40_000,
            "output_tokens": 2_000,
            "estimated_cost_usd": 0.12,
            "per_question_usd": 0.03,
            "prices_verified": False,
        },
        "latency": {"p50_s": 4.21, "p95_s": 9.87},
        "judge": {"summary": {"answer_score": {"mean": 0.8, "n": 4}}},
    }
    if split == "dev":
        data["failures"] = {"answer_accuracy": {"numeric": ["q005"]}}
        data["errors"] = []
    if status == "skipped":
        data["skipped"] = {
            "reason": "too_large",
            "estimated_tokens": 130_000,
            "budget_tokens": 120_000,
        }
        data["aggregates"] = {"overall": None, "by_category": {}}
    return data


def save(folder: Path, name: str, data: dict[str, Any]) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(data), encoding="utf-8")


@pytest.mark.parametrize(
    ("summary", "binary", "text"),
    [
        ({"value": 0.727272, "n": 33, "passed": 24}, True, "72.7 % (24/33)"),
        ({"value": 0.8125, "n": 31, "passed": 20}, False, "81.2 % (n=31)"),
        ({"value": None, "n": 0, "passed": 0}, True, "–"),
        (None, False, "–"),
    ],
)
def test_format_metric(summary: dict[str, Any] | None, binary: bool, text: str) -> None:
    assert format_metric(summary, binary=binary) == text


def test_latest_prefers_complete_then_newest(tmp_path: Path) -> None:
    results = tmp_path / "results"
    save(
        results,
        "2026-10-17-baseline-rag-dev.json",
        result("baseline-rag", started="2026-10-17T08:00:00Z", accuracy=0.5),
    )
    save(results, "2026-10-18-baseline-rag-dev.json", result("baseline-rag", accuracy=0.75))
    save(
        results,
        "2026-10-19-baseline-rag-dev-limit2.json",
        result("baseline-rag", started="2026-10-19T08:00:00Z", complete=False, accuracy=1.0),
    )
    save(
        results,
        "2026-10-18-docwiki-researcher-holdout.json",
        result("docwiki-researcher", split="holdout"),
    )
    save(results, "latest.json", {"format": "docwiki.evals.latest/v1", "splits": {}})
    save(results, "notes.json", {"hello": "world"})
    latest = build_latest(results)
    assert set(latest["splits"]) == {"dev", "holdout"}
    rag = latest["splits"]["dev"]["baseline-rag"]
    assert rag["file"] == "2026-10-18-baseline-rag-dev.json"
    assert rag["overall"]["answer_accuracy"]["value"] == 0.75
    assert "failures" not in latest["splits"]["holdout"]["docwiki-researcher"]


def test_partial_runs_are_used_when_nothing_else_exists(tmp_path: Path) -> None:
    save(tmp_path, "a.json", result("baseline-rag", complete=False))
    latest = build_latest(tmp_path)
    text = render_markdown(latest)
    assert "partial 2/4" in text


def test_markdown_table(tmp_path: Path) -> None:
    save(tmp_path, "a.json", result("baseline-rag"))
    save(tmp_path, "b.json", result("docwiki-researcher", accuracy=1.0))
    save(tmp_path, "c.json", result("baseline-long-context", status="skipped"))
    save(tmp_path, "d.json", result("docwiki-researcher", split="holdout"))
    text = render_markdown(build_latest(tmp_path))
    lines = text.splitlines()
    header = next(line for line in lines if line.startswith("| System |"))
    assert "Answer accuracy" in header and "Cost (USD)" in header and "Latency p50 / p95" in header
    rows = [line for line in lines if line.startswith("| `")]
    assert [row.split("|")[1].strip() for row in rows] == [
        "`docwiki-researcher`",
        "`baseline-rag`",
        "`baseline-long-context`",
        "`docwiki-researcher`",
    ]
    widths = {row.count("|") for row in rows} | {header.count("|")}
    assert len(widths) == 1
    researcher = rows[0]
    assert "100.0 % (4/4)" in researcher and "81.2 % (n=4)" in researcher
    assert "$0.0300/q ($0.12)*" in researcher and "4.2 s / 9.9 s" in researcher
    assert "`0123456` · release `20261018T080000Z-0a1b2c3d`" in researcher
    assert "0.80 (n=4)" in researcher
    assert "skipped: too_large (≈130,000 tokens > budget 120,000)" in rows[2]
    assert "### Dev split (`evals/golden/dev.jsonl`, 4 questions)" in text
    assert "### Holdout split (private questions, aggregates only, 4 questions)" in text
    assert "- `baseline-rag` — answer accuracy: numeric q005" in text
    assert "unverified prices" in text
    assert "not presented as a replacement" in text


def test_no_results_yet(tmp_path: Path) -> None:
    text = render_markdown(build_latest(tmp_path / "missing"))
    assert "No evaluation results yet" in text


def test_compact_readme_table(tmp_path: Path) -> None:
    save(tmp_path, "a.json", result("baseline-rag"))
    save(tmp_path, "b.json", result("docwiki-researcher", accuracy=1.0))
    save(tmp_path, "c.json", result("baseline-long-context", status="skipped"))
    text = render_markdown(build_latest(tmp_path), compact=True)
    assert not text.startswith("## Evaluation")
    lines = text.splitlines()
    header = next(line for line in lines if line.startswith("| System |"))
    assert "Answer accuracy" in header and "Latency p50" in header and "Run" not in header
    rows = [line for line in lines if line.startswith("| `")]
    assert {row.count("|") for row in rows} == {header.count("|")}
    assert "100.0 % (4/4)" in rows[0] and "$0.030/q" in rows[0] and "4.2 s" in rows[0]
    assert "skipped: too_large" in rows[2]
    assert "Failed question ids" not in text
    assert "[evals/SCOREBOARD.md](evals/SCOREBOARD.md)" in text


def test_inject_between_markers() -> None:
    readme = f"# Title\n\nIntro.\n\n{START_MARKER}\nold table\n{END_MARKER}\n\nMore.\n"
    updated = inject(readme, "new table\n")
    assert updated == f"# Title\n\nIntro.\n\n{START_MARKER}\nnew table\n{END_MARKER}\n\nMore.\n"
    assert inject(updated, "new table\n") == updated
    assert inject("# no markers\n", "x\n") is None
    assert inject(f"{END_MARKER}\n{START_MARKER}\n", "x\n") is None
    assert snippet({"splits": {}}).startswith(START_MARKER + "\n## Evaluation")


def test_main_writes_snippet_and_leaves_readme_without_markers(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = tmp_path / "results"
    save(results, "a.json", result("baseline-rag"))
    readme = tmp_path / "README.md"
    readme.write_text("# Project\n", encoding="utf-8")
    args = [
        "--results",
        str(results),
        "--readme",
        str(readme),
        "--snippet",
        str(tmp_path / "SCOREBOARD.md"),
    ]
    assert main(args) == 0
    assert readme.read_text(encoding="utf-8") == "# Project\n"
    board = (tmp_path / "SCOREBOARD.md").read_text(encoding="utf-8")
    assert board.startswith(START_MARKER) and board.rstrip().endswith(END_MARKER)
    latest = json.loads((results / "latest.json").read_text(encoding="utf-8"))
    assert latest["splits"]["dev"]["baseline-rag"]["file"] == "a.json"
    assert "no <!-- scoreboard:start -->" in capsys.readouterr().err
    assert main([*args, "--check"]) == 0


def test_main_injects_into_readme_with_markers(tmp_path: Path) -> None:
    results = tmp_path / "results"
    save(results, "a.json", result("baseline-rag"))
    readme = tmp_path / "README.md"
    readme.write_text(f"# Project\n\n{START_MARKER}\n{END_MARKER}\n\nEnd.\n", encoding="utf-8")
    args = [
        "--results",
        str(results),
        "--readme",
        str(readme),
        "--snippet",
        str(tmp_path / "SB.md"),
    ]
    assert main([*args, "--check"]) == 1
    assert main(args) == 0
    text = readme.read_text(encoding="utf-8")
    assert "| `baseline-rag` |" in text and text.endswith(f"{END_MARKER}\n\nEnd.\n")
    assert main([*args, "--check"]) == 0
    save(results, "b.json", result("docwiki-researcher"))
    assert main([*args, "--check"]) == 1


def test_repository_snippet_is_current(repo_root: Path, tmp_path: Path) -> None:
    """evals/SCOREBOARD.md and latest.json match evals/results (run evals/scoreboard.py)."""
    args = [
        "--results",
        str(repo_root / "evals" / "results"),
        "--readme",
        str(tmp_path / "README.md"),
        "--snippet",
        str(repo_root / "evals" / "SCOREBOARD.md"),
        "--check",
    ]
    assert main(args) == 0
