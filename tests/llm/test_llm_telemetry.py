from __future__ import annotations

import pytest
from pydantic import BaseModel

from docwiki.llm import FakeLlmClient, LlmInvalidOutput
from docwiki.llm.telemetry import SPAN_NAME, get_tracer

trace = pytest.importorskip("opentelemetry.trace")
sdk_trace = pytest.importorskip("opentelemetry.sdk.trace")
in_memory = pytest.importorskip("opentelemetry.sdk.trace.export.in_memory_span_exporter")
export = pytest.importorskip("opentelemetry.sdk.trace.export")

SECRET_TEXT = "Confidential internal price study notes"


class Verdict(BaseModel):
    verdict: str


def provider_with_exporter() -> tuple[object, object]:
    exporter = in_memory.InMemorySpanExporter()
    provider = sdk_trace.TracerProvider()
    provider.add_span_processor(export.SimpleSpanProcessor(exporter))
    return provider, exporter


async def test_one_span_per_call_with_usage_attributes() -> None:
    provider, exporter = provider_with_exporter()
    client = FakeLlmClient({"verdict": Verdict(verdict="ok")}, tracer_provider=provider)

    result = await client.structured(
        "fast", "Judge.", SECRET_TEXT, Verdict, "verdict", "verdict-v2", 64, {"stage": "verify"}
    )

    (span,) = exporter.get_finished_spans()
    attributes = dict(span.attributes)
    assert span.name == SPAN_NAME
    assert attributes["docwiki.llm.tier"] == "fast"
    assert attributes["docwiki.llm.deployment"] == "fake-fast"
    assert attributes["docwiki.llm.model"] == "fake-model"
    assert attributes["docwiki.llm.schema_name"] == "verdict"
    assert attributes["docwiki.llm.prompt_version"] == "verdict-v2"
    assert attributes["docwiki.llm.input_tokens"] == result.usage.input_tokens
    assert attributes["docwiki.llm.output_tokens"] == result.usage.output_tokens
    assert attributes["docwiki.llm.retries"] == 0
    assert attributes["docwiki.llm.latency_ms"] == 0.0
    assert attributes["docwiki.llm.outcome"] == "ok"
    assert attributes["docwiki.llm.metadata.stage"] == "verify"
    assert attributes["gen_ai.usage.input_tokens"] == result.usage.input_tokens
    assert all(SECRET_TEXT not in str(value) for value in attributes.values())
    assert span.status.status_code == trace.StatusCode.UNSET


async def test_failed_calls_mark_the_span_as_error() -> None:
    provider, exporter = provider_with_exporter()
    client = FakeLlmClient({"verdict": {"wrong": "shape"}}, tracer_provider=provider)
    with pytest.raises(LlmInvalidOutput):
        await client.structured("smart", "Judge.", "text", Verdict, "verdict", "verdict-v2", 64)
    (span,) = exporter.get_finished_spans()
    assert span.status.status_code == trace.StatusCode.ERROR
    assert span.attributes["docwiki.llm.outcome"] == "LlmInvalidOutput"


def test_tracing_is_off_without_a_real_provider() -> None:
    assert get_tracer(trace.NoOpTracerProvider()) is None
    assert get_tracer(trace.ProxyTracerProvider()) is None
    provider, _ = provider_with_exporter()
    assert get_tracer(provider) is not None
