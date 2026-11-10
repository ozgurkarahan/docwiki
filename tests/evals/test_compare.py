from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from evals.compare import _holm, build_report, load_arm_runs

from evals import RESULT_FORMAT


def _record(
    qid: str,
    *,
    category: str = "single-hop",
    abstain: bool = False,
    answer_accuracy: float = 1.0,
    abstention_accuracy: float = 1.0,
    restricted_exclusion: float = 1.0,
    injection_resistance: float | None = None,
    answer_text: str = "Answer",
) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "answer_accuracy": answer_accuracy,
        "abstention_accuracy": abstention_accuracy,
        "restricted_exclusion": restricted_exclusion,
        "numeric_exactness": 1.0 if answer_accuracy >= 1.0 else 0.0,
        "citation_precision": 1.0 if answer_accuracy >= 1.0 else 0.0,
        "citation_recall": 1.0 if answer_accuracy >= 1.0 else 0.0,
    }
    if injection_resistance is not None:
        metrics["injection_resistance"] = injection_resistance
    return {
        "id": qid,
        "category": category,
        "abstain": abstain,
        "question": f"Question {qid}",
        "answer": {"text": answer_text, "abstained": abstain, "citations": []},
        "tool_calls": [{"name": "search", "status": "completed"}],
        "metrics": metrics,
        "cost_usd": 0.01,
        "latency_s": 1.0,
    }


def _write_result(
    path: Path, system: str, rows: list[dict[str, Any]], *, split: str = "dev"
) -> None:
    payload = {
        "format": RESULT_FORMAT,
        "system": system,
        "split": split,
        "questions": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load(tmp_path: Path, mapping: dict[str, list[Path]]) -> dict[str, Any]:
    return load_arm_runs({name: [Path(path) for path in paths] for name, paths in mapping.items()})


def test_bootstrap_is_deterministic(tmp_path: Path) -> None:
    a1 = tmp_path / "a-r1.json"
    a2 = tmp_path / "a-r2.json"
    _write_result(a1, "A", [_record("q1"), _record("q2", answer_accuracy=0.0)])
    _write_result(a2, "A", [_record("q1"), _record("q2", answer_accuracy=1.0)])
    b1 = tmp_path / "b-r1.json"
    b2 = tmp_path / "b-r2.json"
    _write_result(b1, "B", [_record("q1", answer_accuracy=0.0), _record("q2", answer_accuracy=0.0)])
    _write_result(b2, "B", [_record("q1"), _record("q2", answer_accuracy=0.0)])
    arms = _load(tmp_path, {"A": [a1, a2], "B": [b1, b2]})
    left = build_report(
        arms,
        reference="A",
        seed=7,
        bootstrap=400,
        permutations=800,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    right = build_report(
        arms,
        reference="A",
        seed=7,
        bootstrap=400,
        permutations=800,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    assert left["arms"]["A"]["primary"] == right["arms"]["A"]["primary"]
    assert left["arms"]["B"]["primary"] == right["arms"]["B"]["primary"]


def test_permutation_p_values_sanity(tmp_path: Path) -> None:
    ref = tmp_path / "ref.json"
    same = tmp_path / "same.json"
    good = tmp_path / "good.json"
    bad = tmp_path / "bad.json"
    rows = [_record(f"q{i}", answer_accuracy=float(i % 2 == 0)) for i in range(1, 17)]
    _write_result(ref, "ref", rows)
    _write_result(same, "same", rows)
    _write_result(good, "good", [_record(f"q{i}") for i in range(1, 17)])
    _write_result(bad, "bad", [_record(f"q{i}", answer_accuracy=0.0) for i in range(1, 17)])
    identical = build_report(
        _load(tmp_path, {"R": [ref], "S": [same]}),
        reference="R",
        seed=11,
        bootstrap=300,
        permutations=2000,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    diff = build_report(
        _load(tmp_path, {"G": [good], "B": [bad]}),
        reference="B",
        seed=11,
        bootstrap=300,
        permutations=2000,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    assert identical["tests"][0]["raw_p"] == pytest.approx(1.0, abs=1e-6)
    assert diff["tests"][0]["raw_p"] < 0.01


def test_holm_adjustment_ordering() -> None:
    assert _holm([0.01, 0.02, 0.20]) == [0.03, 0.04, 0.2]


def test_safety_exclusion_flags_arm(tmp_path: Path) -> None:
    safe = tmp_path / "safe.json"
    leak = tmp_path / "leak.json"
    _write_result(safe, "safe", [_record("q1"), _record("q2")])
    _write_result(
        leak,
        "leak",
        [_record("q1"), _record("q2", restricted_exclusion=0.0)],
    )
    report = build_report(
        _load(tmp_path, {"safe": [safe], "leak": [leak]}),
        reference="safe",
        seed=3,
        bootstrap=200,
        permutations=500,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    assert report["arms"]["leak"]["excluded"] is True
    assert report["arms"]["leak"]["excluded_question_ids"] == ["q2"]


def test_decision_winner_set_and_unresolved(tmp_path: Path) -> None:
    winner = tmp_path / "winner.json"
    other = tmp_path / "other.json"
    third = tmp_path / "third.json"
    _write_result(winner, "winner", [_record(f"q{i}") for i in range(1, 25)])
    _write_result(other, "other", [_record(f"q{i}", answer_accuracy=0.0) for i in range(1, 25)])
    _write_result(third, "third", [_record(f"q{i}", answer_accuracy=0.0) for i in range(1, 25)])
    decided = build_report(
        _load(tmp_path, {"W": [winner], "O": [other], "T": [third]}),
        reference="W",
        seed=5,
        bootstrap=300,
        permutations=3000,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    assert decided["decision"]["status"] == "winner"
    assert decided["decision"]["winner"] == "W"

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    c = tmp_path / "c.json"
    _write_result(
        a,
        "a",
        [_record("q1"), _record("q2"), _record("q3", answer_accuracy=0.0)],
    )
    _write_result(
        b,
        "b",
        [_record("q1"), _record("q2", answer_accuracy=0.0), _record("q3", answer_accuracy=0.0)],
    )
    _write_result(c, "c", [_record("q1", answer_accuracy=0.0), _record("q2"), _record("q3")])
    set_report = build_report(
        _load(tmp_path, {"A": [a], "B": [b], "C": [c]}),
        reference="A",
        seed=9,
        bootstrap=200,
        permutations=1200,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    assert set_report["decision"]["status"] in {"set", "unresolved"}

    unresolved = build_report(
        _load(tmp_path, {"A": [a], "B": [a], "C": [c]}),
        reference="A",
        seed=9,
        bootstrap=200,
        permutations=1200,
        abstention="v1",
        contrasts=[],
        judges={"A": 0.8, "B": 0.8},
        per_question=False,
    )
    assert unresolved["decision"]["status"] == "unresolved"


def test_abstention_v2_changes_scores(tmp_path: Path) -> None:
    arm = tmp_path / "arm.json"
    _write_result(
        arm,
        "arm",
        [
            _record(
                "q1",
                category="abstain",
                abstain=True,
                answer_accuracy=0.0,
                abstention_accuracy=0.0,
                answer_text="Not found in the documents.\n\nSources:\n[1] placeholder",
            )
        ],
    )
    report_v1 = build_report(
        _load(tmp_path, {"A": [arm]}),
        reference="A",
        seed=1,
        bootstrap=100,
        permutations=100,
        abstention="v1",
        contrasts=[],
        judges={},
        per_question=False,
    )
    report_v2 = build_report(
        _load(tmp_path, {"A": [arm]}),
        reference="A",
        seed=1,
        bootstrap=100,
        permutations=100,
        abstention="v2",
        contrasts=[],
        judges={},
        per_question=False,
    )
    assert report_v1["arms"]["A"]["primary"]["mean_accuracy"] == 0.0
    assert report_v2["arms"]["A"]["primary"]["mean_accuracy"] == 1.0
    assert report_v2["arms"]["A"]["secondary"]["abstention_accuracy_v1"] == 0.0
    assert report_v2["arms"]["A"]["secondary"]["abstention_accuracy_v2"] == 1.0
