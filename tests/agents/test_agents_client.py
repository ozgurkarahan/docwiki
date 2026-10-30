"""docwiki.agents_client.ask: Responses API with an agent reference, MCP approvals, errors."""

from __future__ import annotations

import json
from typing import Any

import httpx2
import openai
import pytest
from agents_testkit import (
    ANSWER_TEXT,
    TEST_ENDPOINT,
    FakeOpenAI,
    FakeProject,
    Script,
    StaticCredential,
    agent_version,
    approval_request,
    http_error,
    list_tools,
    mcp_call,
    message,
    response,
)
from azure.core.exceptions import ClientAuthenticationError, ResourceNotFoundError

from docwiki.agents_client import (
    AgentAnswer,
    AgentAuthError,
    AgentClient,
    AgentClientSettings,
    AgentConfigurationError,
    AgentInvocationError,
    AgentNotFoundError,
    ApprovalRequest,
    ask,
    format_answer,
)
from docwiki.agents_client.client import VERSION_CACHE_S

QUESTION = "When are the windows of the extension delivered?"
SETTINGS = AgentClientSettings(project_endpoint=TEST_ENDPOINT, timeout_s=30.0)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        self.now += 0.5
        return self.now


def _client(*steps: Any, versions: dict[str, list[dict[str, Any]]] | None = None) -> AgentClient:
    project = FakeProject(
        versions=versions
        if versions is not None
        else {
            "docwiki-researcher": [agent_version("3", "sha-3")],
            "docwiki-librarian": [agent_version("5", "sha-5")],
        },
        openai=FakeOpenAI(*steps),
    )
    return AgentClient(SETTINGS, project_client=project, clock=Clock())


def _calls(client: AgentClient) -> list[dict[str, Any]]:
    return client._ensure_openai().responses.calls


async def test_normal_answer_pins_the_latest_version_and_parses_sources() -> None:
    client = _client(
        response(
            list_tools("search", "get_evidence"),
            mcp_call("search", {"query": "window delivery date"}, item_id="mcp_1"),
            mcp_call(
                "get_evidence",
                {"source_id": "src-165f1d3a109c", "locator_key": "para-0011"},
                output="Delivery of the windows postponed to 2026-04-20.",
                item_id="mcp_2",
            ),
            message(ANSWER_TEXT),
            input_tokens=900,
            output_tokens=120,
            cached_tokens=300,
            reasoning_tokens=40,
        )
    )
    answer = await ask(QUESTION, client=client)

    (call,) = _calls(client)
    assert call == {
        "input": QUESTION,
        "extra_body": {
            "agent_reference": {
                "type": "agent_reference",
                "name": "docwiki-researcher",
                "version": "3",
            }
        },
    }
    project = client._project
    assert project.agents.get_calls == ["docwiki-researcher"]
    assert project.openai_options == {"timeout": 30.0, "max_retries": 2}
    assert isinstance(answer, AgentAnswer)
    assert (answer.agent, answer.version, answer.definition_sha256) == (
        "docwiki-researcher",
        "3",
        "sha-3",
    )
    assert answer.text == ANSWER_TEXT
    assert [(s.n, s.title, s.locator_key) for s in answer.sources] == [
        (1, "Site meeting minutes n°3", "para-0007"),
        (2, "Planning and purchase tracking, indice B", "sheet-planning-r0006-r0009"),
    ]
    assert answer.body.endswith("(authority, then recency) [1][2].")
    assert [(t.name, t.status, t.arguments) for t in answer.tool_calls] == [
        ("search", "completed", {"query": "window delivery date"}),
        (
            "get_evidence",
            "completed",
            {"source_id": "src-165f1d3a109c", "locator_key": "para-0011"},
        ),
    ]
    assert answer.tool_calls[1].output == "Delivery of the windows postponed to 2026-04-20."
    assert answer.usage.model_dump() == {
        "input_tokens": 900,
        "output_tokens": 120,
        "total_tokens": 1020,
        "cached_input_tokens": 300,
        "reasoning_tokens": 40,
        "responses": 1,
    }
    assert answer.approvals == []
    assert answer.response_id == "resp_1"
    assert answer.conversation_id is None
    assert answer.latency_s == 0.5  # two clock reads 0.5 s apart, no approval wait
    assert json.loads(answer.model_dump_json())["sources"][0]["provenance"] == "native-text"
    assert format_answer(answer).endswith(
        "[docwiki-researcher v3 · 2 tool calls · 1020 tokens · 0.5 s]"
    )


async def test_conversation_and_pinned_version_are_passed_through() -> None:
    client = _client(response(message("Not found in the wiki."), conversation_id="conv_7"))
    answer = await client.ask(QUESTION, conversation_id="conv_7", version="2")
    (call,) = _calls(client)
    assert call["conversation"] == "conv_7"
    assert call["extra_body"]["agent_reference"]["version"] == "2"
    assert client._project.agents.get_calls == []
    assert (answer.version, answer.definition_sha256, answer.conversation_id) == (
        "2",
        None,
        "conv_7",
    )
    assert answer.sources == []
    assert answer.text == "Not found in the wiki."


async def test_per_call_headers_go_to_every_responses_call() -> None:
    first, second = _ingest_flow(approved_output=True)
    client = _client(first, second)
    await ask(
        "Start the ingest",
        agent="librarian",
        approve=lambda request: True,
        headers={"X-Visitor-IP": "hash-1"},
        client=client,
    )
    first_call, second_call = _calls(client)
    assert first_call["extra_headers"] == {"X-Visitor-IP": "hash-1"}
    assert second_call["extra_headers"] == {"X-Visitor-IP": "hash-1"}


async def test_no_headers_means_no_extra_headers_argument() -> None:
    client = _client(response(message("Not found in the wiki.")))
    await client.ask(QUESTION)
    (call,) = _calls(client)
    assert "extra_headers" not in call


class _Stream:
    """An async iterator of Responses API stream events, like the SDK's stream."""

    def __init__(self, *events: dict[str, Any]) -> None:
        self.events = list(events)

    def __aiter__(self) -> _Stream:
        return self

    async def __anext__(self) -> dict[str, Any]:
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)


async def test_with_progress_the_call_streams_and_reports_allowlisted_steps() -> None:
    final = response(
        mcp_call("answer_context", {"question": "windows"}, item_id="mcp_1"),
        message(ANSWER_TEXT),
    )
    client = _client(
        _Stream(
            {"type": "response.created"},
            {"type": "response.output_item.added", "item": {"type": "mcp_list_tools"}},
            {
                "type": "response.output_item.added",
                "item": {"type": "mcp_call", "name": "answer_context"},
            },
            {
                "type": "response.output_item.added",
                "item": {"type": "mcp_call", "name": "evil name; drop"},
            },
            {"type": "response.output_item.added", "item": {"type": "message"}},
            {"type": "response.output_text.delta", "delta": "secret text"},
            {"type": "response.completed", "response": final},
        )
    )
    steps: list[str] = []
    answer = await client.ask(QUESTION, progress=steps.append)
    (call,) = _calls(client)
    assert call["stream"] is True
    assert steps == ["tool:answer_context", "tool", "writing"]
    assert answer.text == ANSWER_TEXT
    assert [t.name for t in answer.tool_calls] == ["answer_context"]


async def test_a_stream_without_a_final_response_is_an_error() -> None:
    client = _client(_Stream({"type": "response.created"}))
    with pytest.raises(AgentInvocationError, match="without a response"):
        await client.ask(QUESTION, progress=lambda step: None)


async def test_a_failing_progress_callback_never_breaks_the_answer() -> None:
    final = response(message("Not found in the wiki."))
    client = _client(
        _Stream(
            {"type": "response.output_item.added", "item": {"type": "message"}},
            {"type": "response.completed", "response": final},
        )
    )

    def broken(step: str) -> None:
        raise RuntimeError("drawer gone")

    answer = await client.ask(QUESTION, progress=broken)
    assert answer.text == "Not found in the wiki."


def _ingest_flow(*, approved_output: bool) -> tuple[Any, ...]:
    first = response(
        list_tools("ingest_start", "run_status"),
        message("I will enqueue an ingest of raw/plans/ (tool ingest_start)."),
        approval_request(
            "mcpr_1", "ingest_start", {"reason": "new plans", "scope": {"prefix": "plans/"}}
        ),
        response_id="resp_1",
        input_tokens=500,
        output_tokens=50,
    )
    if approved_output:
        items = [
            mcp_call(
                "ingest_start",
                {"reason": "new plans", "scope": {"prefix": "plans/"}},
                output='{"queued": true}',
                approval_request_id="mcpr_1",
            ),
            mcp_call("run_status", {}, output='{"status": "queued"}', item_id="mcp_2"),
            message("The ingest is queued; run status: queued (not finished)."),
        ]
    else:
        items = [message("The ingest was not approved, so nothing was enqueued.")]
    second = response(*items, response_id="resp_2", input_tokens=700, output_tokens=60)
    return first, second


async def test_approved_mcp_call_continues_with_previous_response_id() -> None:
    seen: list[ApprovalRequest] = []

    def approve(request: ApprovalRequest) -> bool:
        seen.append(request)
        return True

    client = _client(*_ingest_flow(approved_output=True))
    answer = await client.ask("Ingest the new plans", agent="librarian", approve=approve)

    first, second = _calls(client)
    reference = {"type": "agent_reference", "name": "docwiki-librarian", "version": "5"}
    assert first == {"input": "Ingest the new plans", "extra_body": {"agent_reference": reference}}
    assert second == {
        "input": [
            {"type": "mcp_approval_response", "approve": True, "approval_request_id": "mcpr_1"}
        ],
        "previous_response_id": "resp_1",
        "extra_body": {"agent_reference": reference},
    }
    assert seen == [
        ApprovalRequest(
            id="mcpr_1",
            agent="docwiki-librarian",
            server_label="docwiki",
            name="ingest_start",
            arguments={"reason": "new plans", "scope": {"prefix": "plans/"}},
        )
    ]
    assert [(d.name, d.approved) for d in answer.approvals] == [("ingest_start", True)]
    assert [(t.name, t.status) for t in answer.tool_calls] == [
        ("ingest_start", "completed"),
        ("run_status", "completed"),
    ]
    assert answer.text == (
        "I will enqueue an ingest of raw/plans/ (tool ingest_start).\n\n"
        "The ingest is queued; run status: queued (not finished)."
    )
    assert (answer.usage.responses, answer.usage.total_tokens) == (2, 1310)
    assert answer.response_id == "resp_2"


async def test_approvals_are_denied_by_default() -> None:
    client = _client(*_ingest_flow(approved_output=False))
    answer = await client.ask("Ingest the new plans", agent="librarian")
    _, second = _calls(client)
    assert second["input"] == [
        {"type": "mcp_approval_response", "approve": False, "approval_request_id": "mcpr_1"}
    ]
    assert [(d.name, d.approved) for d in answer.approvals] == [("ingest_start", False)]
    assert [(t.name, t.status) for t in answer.tool_calls] == [("ingest_start", "denied")]
    assert answer.text.endswith("nothing was enqueued.")
    assert "[denied: ingest_start]" in format_answer(answer)


@pytest.mark.parametrize(("decision", "approved"), [(True, True), (False, False), ("yes", False)])
async def test_async_callbacks_and_strict_true(decision: Any, approved: bool) -> None:
    async def approve(request: ApprovalRequest) -> Any:
        return decision

    client = _client(*_ingest_flow(approved_output=approved))
    answer = await client.ask("Ingest the new plans", agent="librarian", approve=approve)
    assert _calls(client)[1]["input"][0]["approve"] is approved
    assert answer.approvals[0].approved is approved


async def test_approval_wait_is_excluded_from_latency() -> None:
    clock = Clock()

    def slow_approve(request: ApprovalRequest) -> bool:
        clock.now += 60.0
        return True

    project = FakeProject(
        versions={"docwiki-librarian": [agent_version("5")]},
        openai=FakeOpenAI(*_ingest_flow(approved_output=True)),
    )
    client = AgentClient(SETTINGS, project_client=project, clock=clock)
    answer = await client.ask("Ingest", agent="librarian", approve=slow_approve)
    assert answer.latency_s < 5.0


async def test_too_many_approval_rounds_fail() -> None:
    loop = [
        response(approval_request(f"mcpr_{index}", "recompile", {}), response_id=f"resp_{index}")
        for index in range(4)
    ]
    project = FakeProject(
        versions={"docwiki-librarian": [agent_version("5")]}, openai=FakeOpenAI(*loop)
    )
    settings = AgentClientSettings(project_endpoint=TEST_ENDPOINT, max_approval_rounds=2)
    client = AgentClient(settings, project_client=project)
    with pytest.raises(AgentInvocationError, match="still requests approvals after 2 rounds"):
        await client.ask("Recompile everything", agent="librarian", approve=lambda r: True)


async def test_failed_mcp_calls_are_reported_not_raised() -> None:
    client = _client(
        response(
            list_tools(error="HTTP 401 from MCP server"),
            mcp_call(
                "query_table",
                {"source_id": "src-86eabe3d6d0d", "sql": "DELETE FROM t01"},
                output=None,
                error={"type": "mcp_tool_execution_error", "content": "only SELECT is allowed"},
                status=None,
            ),
            message("Not found in the wiki."),
        )
    )
    answer = await client.ask(QUESTION)
    assert [(t.name, t.status, t.error) for t in answer.tool_calls] == [
        ("mcp_list_tools", "failed", "HTTP 401 from MCP server"),
        ("query_table", "failed", "only SELECT is allowed"),
    ]


async def test_ok_false_results_from_the_mcp_server_are_failed_tool_calls() -> None:
    errors = pytest.importorskip("docwiki.mcp.errors")
    forbidden = json.dumps(
        errors.failure_payload("forbidden", "requires Wiki.Operate", tool="ingest_start")
    )
    busy = json.dumps(errors.failure_payload("unavailable", "no release yet", tool="search"))
    wrapped = json.dumps([{"type": "text", "text": busy}])
    client = _client(
        response(
            mcp_call("ingest_start", {"reason": "x"}, output=forbidden, item_id="mcp_1"),
            mcp_call("search", {"query": "delivery"}, output=wrapped, item_id="mcp_2"),
            mcp_call(
                "search", {"query": "delivery"}, output='{"ok": true, "hits": []}', item_id="m3"
            ),
            mcp_call("get_index", {"scope": "home"}, output="# Home", item_id="mcp_4"),
            message("Not found in the wiki."),
        )
    )
    answer = await client.ask(QUESTION)
    assert [(t.name, t.status, t.error) for t in answer.tool_calls] == [
        ("ingest_start", "failed", "forbidden: requires Wiki.Operate"),
        ("search", "failed", "unavailable: no release yet"),
        ("search", "completed", None),
        ("get_index", "completed", None),
    ]
    assert answer.tool_calls[0].output == forbidden


# ---------------------------------------------------------------------- errors


def _status_error(status: int, code: str = "x") -> openai.APIStatusError:
    request = httpx2.Request("POST", f"{TEST_ENDPOINT}/openai/v1/responses")
    body = {"code": code, "message": "m"}
    reply = httpx2.Response(status, request=request, json={"error": body})
    return openai.APIStatusError("simulated", response=reply, body=body)


@pytest.mark.parametrize(
    ("step", "error_type", "message_part"),
    [
        (
            response(status="failed", error={"code": "server_error", "message": "model crashed"}),
            AgentInvocationError,
            "docwiki-researcher failed: server_error: model crashed",
        ),
        (
            response(status="incomplete", incomplete_reason="max_output_tokens"),
            AgentInvocationError,
            "incomplete response \\(max_output_tokens\\)",
        ),
        (
            response({"type": "oauth_consent_request", "id": "o1", "consent_link": "x"}),
            AgentInvocationError,
            "OAuth consent",
        ),
        (_status_error(401), AgentAuthError, "Foundry User"),
        (_status_error(403), AgentAuthError, "HTTP 403"),
        (_status_error(404), AgentNotFoundError, "agents/deploy.py"),
        (_status_error(500), AgentInvocationError, "HTTP 500"),
        (
            _status_error(400, "tool_user_error"),
            AgentInvocationError,
            "Foundry ended the turn because an MCP tool call returned an error",
        ),
        (
            openai.APIConnectionError(request=httpx2.Request("POST", TEST_ENDPOINT)),
            AgentInvocationError,
            "could not reach",
        ),
    ],
)
async def test_errors_surface_as_agent_errors(
    step: Any, error_type: type[Exception], message_part: str
) -> None:
    client = _client(step)
    with pytest.raises(error_type, match=message_part) as caught:
        await client.ask(QUESTION)
    if isinstance(step, openai.APIStatusError):
        assert caught.value.status_code == step.status_code  # type: ignore[attr-defined]


@pytest.mark.parametrize(
    ("error", "error_type", "message_part"),
    [
        (ResourceNotFoundError("missing"), AgentNotFoundError, "is not deployed"),
        (ClientAuthenticationError("no credential"), AgentAuthError, "az login"),
        (http_error(403), AgentAuthError, "Foundry User"),
        (http_error(500, "boom"), AgentInvocationError, "boom"),
    ],
)
async def test_version_lookup_errors(
    error: Exception, error_type: type[Exception], message_part: str
) -> None:
    client = _client()
    client._project.agents.get_error = error
    with pytest.raises(error_type, match=message_part):
        await client.ask(QUESTION)


async def test_unexpected_errors_are_not_swallowed() -> None:
    client = _client(RuntimeError("bug"))
    with pytest.raises(RuntimeError, match="bug"):
        await client.ask(QUESTION, version="1")


async def test_empty_question_and_bad_agent_name() -> None:
    client = _client()
    with pytest.raises(ValueError, match="empty"):
        await client.ask("   ")
    with pytest.raises(ValueError, match="invalid agent name"):
        await client.ask(QUESTION, agent="not a name")


def test_settings_from_environment() -> None:
    with pytest.raises(AgentConfigurationError, match="DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"):
        AgentClientSettings.from_env({})
    with pytest.raises(AgentConfigurationError, match="https"):
        AgentClientSettings.from_env({"DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": "http://example.com/x"})
    with pytest.raises(AgentConfigurationError, match="number of seconds"):
        AgentClientSettings.from_env(
            {
                "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": TEST_ENDPOINT,
                "DOCWIKI_AGENT_TIMEOUT_SECONDS": "x",
            }
        )
    settings = AgentClientSettings.from_env(
        {"DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": TEST_ENDPOINT, "DOCWIKI_AGENT_TIMEOUT_SECONDS": "90"}
    )
    assert (settings.project_endpoint, settings.timeout_s, settings.max_retries) == (
        TEST_ENDPOINT,
        90.0,
        2,
    )


async def test_client_closes_only_what_it_created() -> None:
    client = _client(response(message("Not found in the wiki.")))
    await client.ask(QUESTION)
    openai_client = client._ensure_openai()
    project = client._project
    await client.aclose()
    assert openai_client.closed is True  # created through project.get_openai_client()
    assert project.closed is False  # injected


# ---------------------------------------------------------------------- real SDK clients


async def test_request_on_the_wire_through_azure_ai_projects_and_openai() -> None:
    """The real AIProjectClient/AsyncOpenAI stack, with HTTP served by httpx2.MockTransport."""
    from azure.ai.projects.aio import AIProjectClient

    first = response(
        list_tools("ingest_start"),
        approval_request("mcpr_9", "ingest_start", {"reason": "nightly"}),
        response_id="resp_a",
    )
    second = response(
        mcp_call("ingest_start", {"reason": "nightly"}, approval_request_id="mcpr_9"),
        message("Queued."),
        response_id="resp_b",
    )
    script = Script(httpx2.Response(200, json=first), httpx2.Response(200, json=second))
    credential = StaticCredential()
    project = AIProjectClient(endpoint=TEST_ENDPOINT, credential=credential)
    client = AgentClient(
        SETTINGS,
        project_client=project,
        http_client=httpx2.AsyncClient(transport=httpx2.MockTransport(script)),
    )
    try:
        answer = await client.ask(
            "Start the nightly ingest",
            agent="librarian",
            version="7",
            approve=lambda request: request.name == "ingest_start",
        )
    finally:
        await client.aclose()
        await project.close()

    assert [request.url.path for request in script.requests] == [
        "/api/projects/demo/openai/v1/responses",
        "/api/projects/demo/openai/v1/responses",
    ]
    assert script.requests[0].headers["authorization"] == "Bearer unit-test-token"
    assert ("https://ai.azure.com/.default",) in credential.scopes
    reference = {"type": "agent_reference", "name": "docwiki-librarian", "version": "7"}
    assert script.bodies[0] == {"input": "Start the nightly ingest", "agent_reference": reference}
    assert script.bodies[1] == {
        "input": [
            {"type": "mcp_approval_response", "approve": True, "approval_request_id": "mcpr_9"}
        ],
        "previous_response_id": "resp_a",
        "agent_reference": reference,
    }
    assert answer.text == "Queued."
    assert [(t.name, t.status, t.arguments) for t in answer.tool_calls] == [
        ("ingest_start", "completed", {"reason": "nightly"})
    ]
    assert answer.response_id == "resp_b"


async def test_a_long_lived_client_reuses_the_latest_version_until_it_expires() -> None:
    client = _client(
        response(message(ANSWER_TEXT)),
        response(message(ANSWER_TEXT)),
        response(message(ANSWER_TEXT)),
    )
    agents = client._project.agents
    first = await client.ask(QUESTION)
    agents.versions["docwiki-researcher"].append(agent_version("4", "sha-4"))
    second = await client.ask(QUESTION)
    assert (first.version, second.version, second.definition_sha256) == ("3", "3", "sha-3")
    assert agents.get_calls == ["docwiki-researcher"]

    version, sha, resolved_at = client._latest["docwiki-researcher"]
    client._latest["docwiki-researcher"] = (version, sha, resolved_at - VERSION_CACHE_S)
    third = await client.ask(QUESTION)
    assert (third.version, third.definition_sha256) == ("4", "sha-4")
    assert agents.get_calls == ["docwiki-researcher", "docwiki-researcher"]


async def test_a_cached_version_that_disappeared_is_resolved_again_once() -> None:
    client = _client(
        response(message(ANSWER_TEXT)), _status_error(404), response(message(ANSWER_TEXT))
    )
    agents = client._project.agents
    await client.ask(QUESTION)
    agents.versions["docwiki-researcher"] = [agent_version("4", "sha-4")]

    answer = await client.ask(QUESTION)

    assert answer.version == "4"
    versions = [call["extra_body"]["agent_reference"]["version"] for call in _calls(client)]
    assert versions == ["3", "3", "4"]
    assert agents.get_calls == ["docwiki-researcher", "docwiki-researcher"]


async def test_a_pinned_version_that_is_missing_is_not_retried() -> None:
    client = _client(_status_error(404))
    with pytest.raises(AgentNotFoundError):
        await client.ask(QUESTION, version="9")
    assert client._project.agents.get_calls == []
