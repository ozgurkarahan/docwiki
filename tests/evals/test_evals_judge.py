"""Optional judge: lazy azure-ai-evaluation import, inputs, parsing and aggregation."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import types
from pathlib import Path
from typing import Any, ClassVar

import pytest
from evals.judge import (
    EVALUATORS,
    Judge,
    JudgeUnavailable,
    aggregate_judge,
    judge_tool_calls,
    tool_definitions,
)

ENV = {
    "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": (
        "https://contoso-docwiki.services.ai.azure.com/api/projects/docwiki"
    ),
    "DOCWIKI_SMART_DEPLOYMENT": "docwiki-smart",
}


class FakeEvaluator:
    created: ClassVar[list[dict[str, Any]]] = []
    key = "fake"

    def __init__(self, model_config: dict[str, Any], *, credential: Any = None) -> None:
        FakeEvaluator.created.append(
            {"config": model_config, "credential": credential, "key": self.key}
        )

    def __call__(self, **inputs: Any) -> dict[str, Any]:
        return {self.key: 4, f"{self.key}_result": "pass", f"{self.key}_reason": "x" * 1000}


def fake_module(*, missing: tuple[str, ...] = (), broken: tuple[str, ...] = ()) -> types.ModuleType:
    module = types.ModuleType("azure.ai.evaluation")
    for key, class_name in EVALUATORS.items():
        if class_name in missing:
            continue
        if class_name in broken:

            def explode(*args: Any, **kwargs: Any) -> None:
                raise RuntimeError("no credential")

            setattr(module, class_name, explode)
            continue
        setattr(module, class_name, type(class_name, (FakeEvaluator,), {"key": key}))
    return module


@pytest.fixture(autouse=True)
def _reset() -> None:
    FakeEvaluator.created = []


def test_missing_package_gives_a_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "azure.ai.evaluation", None)
    with pytest.raises(JudgeUnavailable, match="azure-ai-evaluation is not installed"):
        Judge.from_env(ENV, credential=object())


def test_missing_settings_give_a_notice(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "azure.ai.evaluation", fake_module())
    with pytest.raises(JudgeUnavailable, match="DOCWIKI_SMART_DEPLOYMENT"):
        Judge.from_env(
            {"DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": ENV["DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"]}
        )
    with pytest.raises(JudgeUnavailable):
        Judge.from_env({"DOCWIKI_SMART_DEPLOYMENT": "docwiki-smart"}, credential=object())


def test_evaluators_use_the_smart_deployment_and_entra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(
        sys.modules,
        "azure.ai.evaluation",
        fake_module(missing=("TaskAdherenceEvaluator",), broken=("IntentResolutionEvaluator",)),
    )
    credential = object()
    judge = Judge.from_env(
        {**ENV, "DOCWIKI_JUDGE_API_VERSION": "2025-04-01-preview"}, credential=credential
    )
    assert set(judge.evaluators) == {
        "groundedness",
        "relevance",
        "response_completeness",
        "tool_call_accuracy",
    }
    assert any("task_adherence" in notice for notice in judge.notices)
    assert any("intent_resolution: RuntimeError" in notice for notice in judge.notices)
    config = FakeEvaluator.created[0]["config"]
    assert config == {
        "azure_endpoint": "https://contoso-docwiki.services.ai.azure.com",
        "azure_deployment": "docwiki-smart",
        "api_version": "2025-04-01-preview",
    }
    assert "api_key" not in config and FakeEvaluator.created[0]["credential"] is credential
    assert judge.versions["judge_deployment"] == "docwiki-smart"


def test_judge_endpoint_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "azure.ai.evaluation", fake_module())
    env = {
        **ENV,
        "DOCWIKI_JUDGE_ENDPOINT": "https://judge.example",
        "DOCWIKI_JUDGE_DEPLOYMENT": "judge",
    }
    Judge.from_env(env, credential=object())
    assert FakeEvaluator.created[0]["config"]["azure_endpoint"] == "https://judge.example"
    assert FakeEvaluator.created[0]["config"]["azure_deployment"] == "judge"


def test_evaluate_routes_inputs_and_parses_outputs() -> None:
    seen: dict[str, dict[str, Any]] = {}

    def make(name: str, output: dict[str, Any] | Exception) -> Any:
        def evaluator(**inputs: Any) -> dict[str, Any]:
            seen[name] = inputs
            if isinstance(output, Exception):
                raise output
            return output

        return evaluator

    judge = Judge(
        {
            "groundedness": make(
                "groundedness", {"groundedness": 5.0, "groundedness_result": "pass"}
            ),
            "relevance": make("relevance", {"gpt_relevance": "3"}),
            "response_completeness": make("response_completeness", {"response_completeness": 2}),
            "tool_call_accuracy": make("tool_call_accuracy", {"tool_call_accuracy": 4}),
            "intent_resolution": make("intent_resolution", TimeoutError("slow")),
        }
    )
    results = asyncio.run(
        judge.evaluate(query="Q?", response="A.", ground_truth="", context="", tool_calls=())
    )
    assert set(seen) == {"relevance", "intent_resolution"}
    assert results["relevance"]["score"] == 3.0
    assert results["intent_resolution"] == {"score": None, "result": None, "error": "TimeoutError"}
    calls = judge_tool_calls([{"name": "search", "arguments": {"query": "oil"}}])
    full = asyncio.run(
        judge.evaluate(
            query="Q?",
            response="A.",
            ground_truth="Expected.",
            context="evidence",
            tool_calls=calls,
            definitions=tool_definitions(["search"]),
        )
    )
    assert full["groundedness"]["result"] == "pass"
    assert seen["response_completeness"] == {"response": "A.", "ground_truth": "Expected."}
    assert seen["tool_call_accuracy"]["tool_calls"][0]["name"] == "search"


def test_tool_call_formats() -> None:
    calls = judge_tool_calls(
        [
            {"name": "search", "arguments": {"query": "oil"}},
            {"name": "mcp_list_tools", "arguments": {}},
            {"name": "get_evidence", "arguments": "not json"},
        ]
    )
    assert calls == [
        {
            "type": "tool_call",
            "tool_call_id": "call_1",
            "name": "search",
            "arguments": {"query": "oil"},
        },
        {"type": "tool_call", "tool_call_id": "call_3", "name": "get_evidence", "arguments": {}},
    ]
    definitions = tool_definitions(["search", "search", "unknown_tool", "get_evidence"])
    assert [item["name"] for item in definitions] == ["search", "get_evidence"]
    assert all(item["description"] for item in definitions)


def test_aggregate_judge() -> None:
    summary = aggregate_judge(
        [
            {
                "response_completeness": {"score": 5.0, "result": "pass"},
                "groundedness": {"score": 4.0},
            },
            {"response_completeness": {"score": 3.0, "result": "fail"}},
            {"response_completeness": {"score": None, "error": "TimeoutError"}},
        ]
    )
    assert summary["response_completeness"] == {"mean": 4.0, "n": 2, "pass_rate": 0.5, "errors": 1}
    assert summary["groundedness"]["mean"] == 4.0 and summary["groundedness"]["pass_rate"] is None
    assert summary["answer_score"] == {"mean": 0.75, "n": 2}


def test_evals_never_import_pandas_or_the_judge_package(repo_root: Path) -> None:
    code = (
        "import sys; import evals.runner, evals.scoreboard, evals.judge; "
        "print('pandas' in sys.modules, 'azure.ai.evaluation' in sys.modules)"
    )
    done = subprocess.run(
        [sys.executable, "-c", code], cwd=repo_root, capture_output=True, text=True, check=True
    )
    assert done.stdout.strip() == "False False"
