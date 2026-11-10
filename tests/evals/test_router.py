from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from evals.router import (
    ROUTER_CLASSIFY_FORMAT,
    build_routed_results,
    classify_questions,
    fit_router,
)

from docwiki.llm import FakeLlmClient, LlmRequest
from evals import RESULT_FORMAT


def _question_line(qid: str, text: str) -> str:
    return json.dumps(
        {
            "id": qid,
            "split": "dev",
            "category": "single-hop",
            "question": text,
            "lang": "en",
            "expected_answer": "",
            "must_include": [],
            "required_citations": [],
            "forbidden": [],
            "abstain": False,
            "notes": "",
        },
        ensure_ascii=False,
    )


def _record(qid: str, *, ok: bool, cost: float) -> dict[str, Any]:
    return {
        "id": qid,
        "category": "single-hop",
        "abstain": False,
        "question": f"Question {qid}",
        "answer": {"text": f"Answer {qid}", "abstained": False, "citations": []},
        "tool_calls": [],
        "metrics": {
            "answer_accuracy": 1.0 if ok else 0.0,
            "abstention_accuracy": 1.0,
            "restricted_exclusion": 1.0,
        },
        "tokens": {
            "input": 10,
            "output": 2,
            "cached_input": 0,
            "reasoning": 0,
            "total": 12,
            "calls": 1,
        },
        "cost_usd": cost,
        "latency_s": 1.0,
        "info": {},
    }


def _write_result(path: Path, system: str, records: list[dict[str, Any]]) -> None:
    payload = {"format": RESULT_FORMAT, "system": system, "split": "dev", "questions": records}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_classifications(path: Path) -> None:
    payload = {
        "format": ROUTER_CLASSIFY_FORMAT,
        "prompt_version": "knowledge-access-router-v1",
        "tier": "fast",
        "questions_file": {"file": "dev.jsonl", "sha256": "x", "count": 3},
        "questions": {
            "q1": {
                "route": "lookup",
                "usage": {
                    "input_tokens": 4,
                    "output_tokens": 1,
                    "cached_input_tokens": 0,
                    "reasoning_tokens": 0,
                    "calls": 1,
                },
                "cost_usd": 0.001,
                "latency_s": 0.2,
            },
            "q2": {
                "route": "lookup",
                "usage": {
                    "input_tokens": 4,
                    "output_tokens": 1,
                    "cached_input_tokens": 0,
                    "reasoning_tokens": 0,
                    "calls": 1,
                },
                "cost_usd": 0.001,
                "latency_s": 0.2,
            },
            "q3": {
                "route": "aggregate-or-cross",
                "usage": {
                    "input_tokens": 4,
                    "output_tokens": 1,
                    "cached_input_tokens": 0,
                    "reasoning_tokens": 0,
                    "calls": 1,
                },
                "cost_usd": 0.001,
                "latency_s": 0.2,
            },
        },
        "totals": {"questions": 3},
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_classify_uses_only_question_text(tmp_path: Path) -> None:
    questions = tmp_path / "dev.jsonl"
    questions.write_text(
        _question_line("qid-router-001", "What is the current revision status?") + "\n",
        encoding="utf-8",
    )
    seen: list[LlmRequest] = []

    def handler(request: LlmRequest) -> dict[str, Any]:
        seen.append(request)
        return {"route": "revision-or-absent"}

    llm = FakeLlmClient({"eval_router_classify": handler})
    cache = tmp_path / "classify.json"
    payload = asyncio.run(
        classify_questions(
            questions_file=questions,
            cache_file=cache,
            llm=llm,
            tier="fast",
            concurrency=1,
        )
    )
    assert payload["questions"]["qid-router-001"]["route"] == "revision-or-absent"
    assert seen[0].text == "What is the current revision status?"
    assert "qid-router-001" not in seen[0].text


def test_fit_router_with_loo_and_apply_and_oracle(tmp_path: Path) -> None:
    cls = tmp_path / "classify.json"
    _write_classifications(cls)

    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_result(
        a,
        "A",
        [
            _record("q1", ok=True, cost=0.010),
            _record("q2", ok=True, cost=0.010),
            _record("q3", ok=False, cost=0.010),
        ],
    )
    _write_result(
        b,
        "B",
        [
            _record("q1", ok=False, cost=0.020),
            _record("q2", ok=False, cost=0.020),
            _record("q3", ok=True, cost=0.020),
        ],
    )
    table = fit_router(classifications_file=cls, arm_paths={"A": [a], "B": [b]})
    assert table["routes"] == {"aggregate-or-cross": "B", "lookup": "A"}
    assert table["dev_estimate"]["loo_accuracy"] == 1.0
    assert table["fitted_on"]["hash"]

    table_file = tmp_path / "table.json"
    table_file.write_text(json.dumps(table, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    routed = build_routed_results(
        table_file=table_file,
        classifications_file=cls,
        arm_paths={"A": [a], "B": [b]},
        name="router",
        mode="router",
    )[0]
    rows = {row["id"]: row for row in routed["questions"]}
    assert rows["q1"]["info"]["router_arm"] == "A"
    assert rows["q3"]["info"]["router_arm"] == "B"
    assert rows["q1"]["cost_usd"] == 0.011
    assert rows["q1"]["latency_s"] == 1.2
    assert rows["q1"]["tokens"]["input"] == 14

    oracle = build_routed_results(
        table_file=table_file,
        classifications_file=cls,
        arm_paths={"A": [a], "B": [b]},
        name="oracle",
        mode="oracle",
    )[0]
    picked = {row["id"]: row["info"]["router_arm"] for row in oracle["questions"]}
    assert picked == {"q1": "A", "q2": "A", "q3": "B"}
