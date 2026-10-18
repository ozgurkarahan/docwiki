"""Optional judge metrics with ``azure-ai-evaluation`` (docs/spec/evals.md §2, built-in evaluators).

Evaluators: groundedness (answer vs the cited evidence text), relevance, response completeness
(vs the expected answer: the judge score for semantic correctness), task adherence, intent
resolution and tool call accuracy (Researcher only). The judge is the ``smart`` deployment,
reached with Entra ID (``DefaultAzureCredential``), never with keys.

``azure-ai-evaluation`` depends on ``pandas``, which has no Windows ARM64 wheel: it is imported
lazily, only here, and only when ``--judge`` is requested. Without it the run continues with a
notice. Run judged evaluations on Linux CI or an x64 Python (``uv sync --extra evals``).

Settings: ``DOCWIKI_JUDGE_ENDPOINT`` (Azure OpenAI or AI Services endpoint; default: the scheme
and host of ``DOCWIKI_FOUNDRY_PROJECT_ENDPOINT``), ``DOCWIKI_JUDGE_DEPLOYMENT`` (default:
``DOCWIKI_SMART_DEPLOYMENT``) and ``DOCWIKI_JUDGE_API_VERSION`` (optional).
"""

from __future__ import annotations

import asyncio
import importlib
import importlib.metadata
import os
import statistics
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

__all__ = [
    "EVALUATORS",
    "Judge",
    "JudgeUnavailable",
    "aggregate_judge",
    "judge_tool_calls",
    "tool_definitions",
]

EVALUATORS: dict[str, str] = {
    "groundedness": "GroundednessEvaluator",
    "relevance": "RelevanceEvaluator",
    "response_completeness": "ResponseCompletenessEvaluator",
    "task_adherence": "TaskAdherenceEvaluator",
    "intent_resolution": "IntentResolutionEvaluator",
    "tool_call_accuracy": "ToolCallAccuracyEvaluator",
}
"""Result key → ``azure.ai.evaluation`` class name."""

MAX_REASON_CHARS = 400


class JudgeUnavailable(RuntimeError):
    """The judge cannot run here; the message is the notice recorded in the results."""


@dataclass
class Judge:
    """Callable evaluators by name (``evaluator(**inputs) -> dict``) plus their versions."""

    evaluators: Mapping[str, Callable[..., Mapping[str, Any]]]
    versions: dict[str, Any] = field(default_factory=dict)
    notices: list[str] = field(default_factory=list)

    @classmethod
    def from_env(
        cls,
        env: Mapping[str, str] | None = None,
        *,
        names: Sequence[str] = tuple(EVALUATORS),
        credential: Any | None = None,
    ) -> Judge:
        values = os.environ if env is None else env
        try:
            module = importlib.import_module("azure.ai.evaluation")
        except ImportError as exc:
            raise JudgeUnavailable(
                "judge skipped: azure-ai-evaluation is not installed (install the evals extra "
                "on Linux or an x64 Python: uv sync --extra evals)"
            ) from exc
        endpoint = (values.get("DOCWIKI_JUDGE_ENDPOINT") or "").strip() or _host(
            values.get("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT") or ""
        )
        deployment = (values.get("DOCWIKI_JUDGE_DEPLOYMENT") or "").strip() or (
            values.get("DOCWIKI_SMART_DEPLOYMENT") or ""
        ).strip()
        if not endpoint or not deployment:
            raise JudgeUnavailable(
                "judge skipped: set DOCWIKI_FOUNDRY_PROJECT_ENDPOINT (or DOCWIKI_JUDGE_ENDPOINT) "
                "and DOCWIKI_SMART_DEPLOYMENT (or DOCWIKI_JUDGE_DEPLOYMENT)"
            )
        if credential is None:
            try:
                identity = importlib.import_module("azure.identity")
            except ImportError as exc:
                raise JudgeUnavailable("judge skipped: azure-identity is not installed") from exc
            credential = identity.DefaultAzureCredential()
        model_config: dict[str, Any] = {"azure_endpoint": endpoint, "azure_deployment": deployment}
        api_version = (values.get("DOCWIKI_JUDGE_API_VERSION") or "").strip()
        if api_version:
            model_config["api_version"] = api_version
        evaluators: dict[str, Callable[..., Mapping[str, Any]]] = {}
        notices: list[str] = []
        for name in names:
            class_name = EVALUATORS[name]
            evaluator_class = getattr(module, class_name, None)
            if evaluator_class is None:
                notices.append(f"{name}: {class_name} is not available in this version")
                continue
            try:
                evaluators[name] = evaluator_class(model_config, credential=credential)
            except Exception as exc:  # one evaluator must not stop the others
                notices.append(f"{name}: {type(exc).__name__}")
        if not evaluators:
            raise JudgeUnavailable("judge skipped: no evaluator could be created")
        try:
            package_version = importlib.metadata.version("azure-ai-evaluation")
        except importlib.metadata.PackageNotFoundError:  # pragma: no cover
            package_version = None
        return cls(
            evaluators=evaluators,
            versions={
                "azure-ai-evaluation": package_version,
                "judge_deployment": deployment,
                "evaluators": sorted(evaluators),
            },
            notices=notices,
        )

    async def evaluate(
        self,
        *,
        query: str,
        response: str,
        ground_truth: str = "",
        context: str = "",
        tool_calls: Sequence[Mapping[str, Any]] = (),
        definitions: Sequence[Mapping[str, Any]] = (),
    ) -> dict[str, dict[str, Any]]:
        """Run every evaluator that has its inputs; failures are recorded, never raised."""
        results: dict[str, dict[str, Any]] = {}
        for name, evaluator in self.evaluators.items():
            inputs = _inputs(name, query, response, ground_truth, context, tool_calls, definitions)
            if inputs is None:
                continue
            try:
                raw = await asyncio.to_thread(evaluator, **inputs)
            except Exception as exc:  # the judge never stops the run
                results[name] = {"score": None, "result": None, "error": type(exc).__name__}
                continue
            results[name] = _parse(name, raw)
        return results


def _host(endpoint: str) -> str:
    parts = urlsplit(endpoint.strip())
    return f"{parts.scheme}://{parts.netloc}" if parts.scheme == "https" and parts.netloc else ""


def _inputs(
    name: str,
    query: str,
    response: str,
    ground_truth: str,
    context: str,
    tool_calls: Sequence[Mapping[str, Any]],
    definitions: Sequence[Mapping[str, Any]],
) -> dict[str, Any] | None:
    match name:
        case "groundedness":
            return {"query": query, "response": response, "context": context} if context else None
        case "response_completeness":
            return {"response": response, "ground_truth": ground_truth} if ground_truth else None
        case "tool_call_accuracy":
            if not tool_calls or not definitions:
                return None
            return {
                "query": query,
                "response": response,
                "tool_calls": list(tool_calls),
                "tool_definitions": list(definitions),
            }
        case _:
            return {"query": query, "response": response}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, int | float):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse(name: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    score = None
    for key in (name, f"{name}_score", f"gpt_{name}"):
        if key in raw:
            score = _number(raw[key])
            if score is not None:
                break
    reason = raw.get(f"{name}_reason")
    return {
        "score": score,
        "result": raw.get(f"{name}_result"),
        "threshold": _number(raw.get(f"{name}_threshold")),
        "reason": str(reason)[:MAX_REASON_CHARS] if reason else None,
    }


def tool_definitions(names: Sequence[str]) -> list[dict[str, Any]]:
    """Name and description of the DocWiki MCP tools that were called (for tool call accuracy)."""
    from docwiki.mcp.descriptions import TOOLS

    return [
        {"name": name, "description": TOOLS[name], "parameters": {"type": "object"}}
        for name in dict.fromkeys(names)
        if name in TOOLS
    ]


def judge_tool_calls(calls: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Tool calls in the format of the agent evaluators."""
    return [
        {
            "type": "tool_call",
            "tool_call_id": f"call_{index}",
            "name": call["name"],
            "arguments": call.get("arguments") if isinstance(call.get("arguments"), dict) else {},
        }
        for index, call in enumerate(calls, 1)
        if call.get("name") and call.get("name") != "mcp_list_tools"
    ]


def aggregate_judge(per_question: Sequence[Mapping[str, Mapping[str, Any]]]) -> dict[str, Any]:
    """Mean score, pass rate and denominator per evaluator; ``answer_score`` is the response
    completeness mapped from 1–5 to 0–1 (the judge score for semantic correctness)."""
    names = sorted({name for item in per_question for name in item})
    summary: dict[str, Any] = {}
    for name in names:
        scores = [
            score
            for item in per_question
            if (score := (item.get(name) or {}).get("score")) is not None
        ]
        outcomes = [
            outcome
            for item in per_question
            if (outcome := (item.get(name) or {}).get("result")) in ("pass", "fail")
        ]
        summary[name] = {
            "mean": round(statistics.fmean(scores), 4) if scores else None,
            "n": len(scores),
            "pass_rate": round(outcomes.count("pass") / len(outcomes), 4) if outcomes else None,
            "errors": sum(1 for item in per_question if (item.get(name) or {}).get("error")),
        }
    completeness = [
        (score - 1.0) / 4.0
        for item in per_question
        if (score := (item.get("response_completeness") or {}).get("score")) is not None
    ]
    summary["answer_score"] = {
        "mean": round(statistics.fmean(completeness), 4) if completeness else None,
        "n": len(completeness),
    }
    return summary
