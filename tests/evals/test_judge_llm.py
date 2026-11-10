from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from evals.judge_llm import judge_result
from evals_testkit import QUOTE

from docwiki.llm import FakeLlmClient, LlmRequest
from evals import RESULT_FORMAT


def _result_payload() -> dict[str, Any]:
    return {
        "format": RESULT_FORMAT,
        "system": "arm-secret-name",
        "split": "dev",
        "questions": [
            {
                "id": "q001",
                "category": "single-hop",
                "abstain": False,
                "question": "What is the total price including VAT?",
                "expected_answer": "44943,60 € including VAT.",
                "answer": {
                    "text": "The total is 44943,60 € [1].\n\nSources:\n[1] quote page 2",
                    "abstained": False,
                    "citations": [{"source_path": QUOTE, "locator_key": "p0002", "unit": "[1]"}],
                },
                "details": {"must_include": [{"item": "44943,60 €", "found": True}]},
                "metrics": {
                    "answer_accuracy": 1.0,
                    "abstention_accuracy": 1.0,
                    "restricted_exclusion": 1.0,
                },
                "tool_calls": [],
                "latency_s": 1.0,
                "cost_usd": 0.01,
            }
        ],
    }


def test_judge_schema_and_prompt_blinding(corpus: Any, tmp_path: Path) -> None:
    seen: list[LlmRequest] = []

    def handler(request: LlmRequest) -> dict[str, Any]:
        seen.append(request)
        assert "arm-secret-name" not in request.system
        assert "arm-secret-name" not in request.text
        assert "44943,60 €" in request.text
        return {
            "verdict": "correct",
            "values_assigned_correctly": True,
            "contradicts_itself": False,
            "claims_supported": 1.0,
            "abstained_correctly": None,
            "rationale": "Evidence and answer match.",
        }

    llm = FakeLlmClient({"eval_knowledge_access_judge": handler})
    judged = asyncio.run(
        judge_result(
            result=_result_payload(),
            result_path=tmp_path / "run.json",
            corpus=corpus,
            llm=llm,
            tier="smart",
            concurrency=1,
            max_evidence_chars=2000,
        )
    )
    question = judged["questions"][0]
    assert question["verdict"] == "correct"
    assert question["claims_supported"] == 1.0
    assert judged["aggregates"]["correct_share"] == 1.0
    assert judged["aggregates"]["supported_mean"] == 1.0
    assert seen and "44943,60 €" in seen[0].text
