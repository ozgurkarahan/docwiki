"""Concurrent dense queries, interactive deadlines, and precise raw-ablation recovery."""

from __future__ import annotations

import asyncio
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
import httpx
import numpy as np
import pytest
from mcp_testkit import RELEASE_ID, TOPIC_ID, tool_payload
from openai import RateLimitError
from test_mcp_v2 import vectors as vectors

from docwiki.llm.embeddings import EmbeddingBatch, EmbeddingInfo, EmbedRequest, FakeEmbeddingClient
from docwiki.llm.errors import LlmRateLimited
from docwiki.llm.settings import LlmSettings
from docwiki.mcp.config import McpConfig
from docwiki.mcp.dense import QUERY_INPUT_VERSION, DenseLane, query_embedding_client
from docwiki.mcp.server import build_server, create_app
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import ReadTools, ToolInputError
from mcp import Client


@pytest.mark.parametrize("value", ["0", "-1", "61", "nan", "inf", "not-a-number"])
def test_dense_timeout_rejects_unbounded_or_invalid_values(value: str) -> None:
    with pytest.raises(ValueError, match="DOCWIKI_MCP_DENSE_TIMEOUT_SECONDS"):
        McpConfig.from_env({"DOCWIKI_MCP_DENSE_TIMEOUT_SECONDS": value})


def test_dense_timeout_default_and_override() -> None:
    assert McpConfig.from_env({}).dense_timeout_s == 20
    assert McpConfig.from_env({"DOCWIKI_MCP_DENSE_TIMEOUT_SECONDS": "0.05"}).dense_timeout_s == 0.05


@pytest.mark.parametrize("fail_first", [False, True])
def test_different_queries_do_not_block_and_identical_queries_share_a_future(
    source: FolderReleaseSource,
    vectors: Path,
    monkeypatch: pytest.MonkeyPatch,
    fail_first: bool,
) -> None:
    from docwiki.mcp import dense

    started, release, waiting = threading.Event(), threading.Event(), threading.Event()
    calls: list[str] = []

    class ObservedFuture(Future[np.ndarray]):
        def result(self, timeout: float | None = None) -> np.ndarray:
            waiting.set()
            return super().result(timeout)

    class ControlledClient(FakeEmbeddingClient):
        async def _run(self, request: EmbedRequest) -> EmbeddingBatch:
            text = request.texts[0]
            calls.append(text)
            if text == "slow":
                started.set()
                while not release.is_set():
                    await asyncio.sleep(0.005)
                if fail_first and calls.count("slow") == 1:
                    raise RuntimeError("controlled embedding failure")
            return await super()._run(request)

    monkeypatch.setattr(dense, "Future", ObservedFuture)
    lane = DenseLane(
        source.current(),
        source,
        McpConfig(vectors=str(vectors), dense_timeout_s=5),
        lambda: ControlledClient(dimensions=4),
    )
    with ThreadPoolExecutor(max_workers=3) as pool:
        first = pool.submit(lane.query, "slow")
        try:
            assert started.wait(2)
            duplicate = pool.submit(lane.query, "slow")
            assert waiting.wait(2), "the identical request must join the in-flight future"
            different = pool.submit(lane.query, "fast")
            fast = different.result(timeout=2)
            assert lane.query("fast") is fast, "cached reads must not wait for another key"
            assert not first.done() and not duplicate.done()
        finally:
            release.set()
        if fail_first:
            for result in (first, duplicate):
                with pytest.raises(RuntimeError, match="controlled embedding failure"):
                    result.result(timeout=2)
            assert "slow" not in lane._queries and not lane._inflight
            lane.query("slow")
            assert calls.count("slow") == 2, "a failed shared call must be retryable"
        else:
            assert first.result(timeout=2) is duplicate.result(timeout=2)
            assert calls.count("slow") == 1
        assert calls.count("fast") == 1 and not lane._inflight


@pytest.mark.parametrize("slow_stage", ["describe", "embed", "close"])
async def test_dense_deadline_cancels_work_and_surfaces_unavailable(
    source: FolderReleaseSource,
    vectors: Path,
    monkeypatch: pytest.MonkeyPatch,
    slow_stage: str,
) -> None:
    from docwiki.llm import foundry_embeddings

    cancelled, closed = threading.Event(), threading.Event()

    async def pause() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            cancelled.set()

    class SlowClient(FakeEmbeddingClient):
        async def describe(self) -> EmbeddingInfo:
            if slow_stage == "describe":
                await pause()
            return await super().describe()

        async def _run(self, request: EmbedRequest) -> EmbeddingBatch:
            if slow_stage == "embed":
                await pause()
            return await super()._run(request)

        async def aclose(self) -> None:
            closed.set()
            if slow_stage == "close":
                await pause()
            await super().aclose()

    monkeypatch.setattr(
        foundry_embeddings,
        "FoundryEmbeddingClient",
        lambda *args, **kwargs: SlowClient(dimensions=4),
    )
    server = build_server(
        source,
        config=McpConfig(
            dense=True,
            vectors=str(vectors),
            dense_timeout_s=0.03,
        ),
    )
    async with Client(server) as client:
        response = await asyncio.wait_for(
            client.call_tool("search", {"query": "menuiseries"}), timeout=2
        )
    result = tool_payload(response)
    assert not result["ok"] and result["error"]["code"] == "unavailable"
    assert result["error"]["details"]["cause"] == "TimeoutError"
    assert cancelled.is_set() and closed.is_set()


async def test_query_client_disables_retry_after_and_caps_sdk_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = LlmSettings(
        project_endpoint="https://example.services.ai.azure.com/api/projects/demo",
        embed_deployment="embed-deployment",
        embed_dimensions=4,
        timeout_s=300,
        max_retries=9,
        max_retry_after_s=999,
    )
    monkeypatch.setattr(LlmSettings, "from_env", lambda: settings)
    client = query_embedding_client(0.05)
    assert client.settings.timeout_s == 0.05
    assert client._retry.max_retries == 0 and client._retry.max_retry_after_s == 0
    calls: list[str] = []
    sleeps: list[float] = []

    async def throttled(**kwargs: Any) -> Any:
        calls.append("request")
        response = httpx.Response(
            429,
            headers={"Retry-After": "120"},
            request=httpx.Request("POST", "https://example.com/embeddings"),
        )
        raise RateLimitError("throttled", response=response, body=None)

    async def sleep(seconds: float) -> None:
        sleeps.append(seconds)

    monkeypatch.setattr(
        client,
        "_ensure_openai",
        lambda: SimpleNamespace(embeddings=SimpleNamespace(create=throttled)),
    )
    monkeypatch.setattr(client, "_sleep", sleep)
    try:
        with pytest.raises(LlmRateLimited):
            await client.embed(["question"], "query", QUERY_INPUT_VERSION)
    finally:
        await client.aclose()
    assert calls == ["request"] and sleeps == []


async def test_slow_dense_request_leaves_healthz_default_worker_capacity(
    source: FolderReleaseSource,
    vectors: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from docwiki.llm import foundry_embeddings

    started, release = threading.Event(), threading.Event()

    class SlowClient(FakeEmbeddingClient):
        async def _run(self, request: EmbedRequest) -> EmbeddingBatch:
            started.set()
            while not release.is_set():
                await asyncio.sleep(0.005)
            return await super()._run(request)

    monkeypatch.setattr(
        foundry_embeddings,
        "FoundryEmbeddingClient",
        lambda *args, **kwargs: SlowClient(dimensions=4),
    )
    app = create_app(
        source,
        config=McpConfig(dense=True, vectors=str(vectors), dense_timeout_s=5),
        ops=None,
    )
    default = anyio.to_thread.current_default_thread_limiter()
    original_tokens = default.total_tokens
    default.total_tokens = 1
    pending: asyncio.Task[Any] | None = None
    try:
        async with (
            app.router.lifespan_context(app),
            Client(app.state.mcp_server) as client,
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://localhost"
            ) as http,
        ):
            pending = asyncio.create_task(client.call_tool("search", {"query": "menuiseries"}))
            try:
                assert await asyncio.to_thread(started.wait, 2)
                assert default.borrowed_tokens == 0
                response = await asyncio.wait_for(http.get("/healthz"), timeout=1)
                assert response.status_code == 200 and response.json()["release_id"] == RELEASE_ID
                assert not pending.done(), "healthz must respond before the slow embedding ends"
            finally:
                release.set()
                await asyncio.wait_for(pending, timeout=2)
    finally:
        release.set()
        default.total_tokens = original_tokens


def test_not_found_recovery_distinguishes_raw_tools_from_bad_arguments(
    source: FolderReleaseSource,
) -> None:
    normal = ReadTools(source, McpConfig())
    with pytest.raises(ToolInputError) as unknown:
        normal.read_page("topic:plannin")
    assert unknown.value.code == "not_found"
    assert TOPIC_ID in unknown.value.details["suggestions"]
    assert "wiki_ablation" not in unknown.value.details
    # Recovery on the same tool remains valid for a corrected page argument.
    assert normal.read_page(TOPIC_ID)
    raw = ReadTools(source, McpConfig(wiki_ablation="raw"))
    with pytest.raises(ToolInputError) as unavailable:
        raw.read_page(TOPIC_ID)
    assert unavailable.value.code == "not_found"
    assert unavailable.value.details == {"wiki_ablation": "raw"}


def test_v2_instructions_keep_recovery_and_answer_policy() -> None:
    root = Path(__file__).resolve().parents[2]
    original = (root / "agents" / "researcher" / "instructions.md").read_text(encoding="utf-8")
    variant = (root / "agents" / "variants" / "v2" / "instructions.md").read_text(encoding="utf-8")
    assert original.split("## Evidence rules", 1)[1] == variant.split("## Evidence rules", 1)[1]
    protocol = variant.split("## Protocol", 1)[1].split("## Scopes", 1)[0]
    results = variant.split("## Tool results", 1)[1].split("## Evidence rules", 1)[0]
    for section in (protocol, results):
        assert 'error.details.wiki_ablation == "raw"' in section
        assert "suggestions in `error.details`" in section
    assert (
        "search or browse an index starting with the suggestions in `error.details` (`not_found`)"
        in " ".join(results.split())
    )
    assert "A tool returning `not_found` on this server is unavailable" not in " ".join(
        protocol.split()
    )
