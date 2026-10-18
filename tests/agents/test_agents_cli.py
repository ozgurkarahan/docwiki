"""``docwiki ask`` end to end: the CLI, docwiki.agents_client and the real SDK clients.

Only the Azure boundary is mocked: ``DefaultAzureCredential`` returns a static token, the agent
lookup returns an ``AgentDetails`` model, and the Responses API is served by
``httpx2.MockTransport`` behind the real ``AIProjectClient.get_openai_client()``.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx2
import pytest
from agents_testkit import (
    ANSWER_TEXT,
    TEST_ENDPOINT,
    Script,
    StaticCredential,
    approval_request,
    list_tools,
    mcp_call,
    message,
    response,
)
from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.aio import operations as aio_operations
from azure.ai.projects.models import AgentDetails
from azure.core.exceptions import ResourceNotFoundError
from click.testing import Result
from typer.testing import CliRunner

from docwiki.agents_client import AgentAnswer
from docwiki.cli import app

QUESTION = "Which gearbox oil grade applies to WTG-07 in winter?"


class Foundry:
    """Patches the Azure boundary for one ``docwiki ask`` invocation."""

    def __init__(
        self,
        monkeypatch: pytest.MonkeyPatch,
        *steps: dict[str, Any],
        versions: dict[str, str] | None = None,
    ) -> None:
        self.script = Script(*(httpx2.Response(200, json=step) for step in steps))
        self.versions = versions or {"docwiki-researcher": "4", "docwiki-librarian": "6"}
        self.lookups: list[str] = []
        self.credentials: list[StaticCredential] = []
        monkeypatch.setenv("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT", TEST_ENDPOINT)
        monkeypatch.setattr("azure.identity.aio.DefaultAzureCredential", self._credential)
        original = AIProjectClient.get_openai_client
        script = self.script

        def get_openai_client(project: AIProjectClient, **options: Any) -> Any:
            client = httpx2.AsyncClient(transport=httpx2.MockTransport(script))
            return original(project, http_client=client, **options)

        foundry = self

        async def get(operations: Any, agent_name: str, **kwargs: Any) -> AgentDetails:
            foundry.lookups.append(agent_name)
            if agent_name not in foundry.versions:
                raise ResourceNotFoundError(f"agent {agent_name} not found")
            version = foundry.versions[agent_name]
            latest = {
                "object": "agent.version",
                "id": f"{agent_name}:{version}",
                "name": agent_name,
                "version": version,
                "metadata": {"docwiki_definition_sha256": f"sha-{version}"},
                "created_at": 1_700_000_000,
                "definition": {"kind": "prompt", "model": "smart-deployment"},
            }
            return AgentDetails(
                {
                    "object": "agent",
                    "id": agent_name,
                    "name": agent_name,
                    "versions": {"latest": latest},
                }
            )

        monkeypatch.setattr(AIProjectClient, "get_openai_client", get_openai_client)
        monkeypatch.setattr(aio_operations.AgentsOperations, "get", get)

    def _credential(self, **kwargs: Any) -> StaticCredential:
        credential = StaticCredential()
        self.credentials.append(credential)
        return credential

    @staticmethod
    def reference(name: str, version: str) -> dict[str, str]:
        return {"type": "agent_reference", "name": name, "version": version}


def _ask(tmp_path: Path, *args: str, stdin: str | None = None) -> Result:
    env_file = tmp_path / "absent.env"  # never read a developer's local .env
    return CliRunner().invoke(app, ["--env-file", str(env_file), "ask", *args], input=stdin)


def test_ask_prints_the_answer_sources_and_receipt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    foundry = Foundry(
        monkeypatch,
        response(
            list_tools("search", "get_evidence"),
            mcp_call("search", {"query": "gearbox oil WTG-07"}, output='{"ok": true, "hits": []}'),
            mcp_call(
                "get_evidence",
                {"source_id": "src-4d9c65e05302", "locator_key": "para-0004"},
                output='{"ok": true, "locator_label": "¶ 4"}',
                item_id="mcp_2",
            ),
            message(ANSWER_TEXT),
            input_tokens=900,
            output_tokens=120,
        ),
    )
    result = _ask(tmp_path, QUESTION)

    assert result.exit_code == 0, result.output
    assert ANSWER_TEXT in result.stdout
    assert "[docwiki-researcher v4 · 2 tool calls · 1020 tokens ·" in result.stdout
    assert foundry.lookups == ["docwiki-researcher"]
    (request,) = foundry.script.requests
    assert request.url.path == "/api/projects/demo/openai/v1/responses"
    assert request.headers["authorization"] == "Bearer unit-test-token"
    assert foundry.script.bodies == [
        {"input": QUESTION, "agent_reference": foundry.reference("docwiki-researcher", "4")}
    ]
    assert ("https://ai.azure.com/.default",) in foundry.credentials[0].scopes


def test_ask_json_with_conversation_and_pinned_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    foundry = Foundry(monkeypatch, response(message(ANSWER_TEXT), conversation_id="conv_7"))
    result = _ask(tmp_path, QUESTION, "--json", "--conversation", "conv_7", "--version", "2")

    assert result.exit_code == 0, result.output
    answer = AgentAnswer.model_validate_json(result.stdout)
    assert (answer.agent, answer.version, answer.conversation_id) == (
        "docwiki-researcher",
        "2",
        "conv_7",
    )
    assert [source.locator_key for source in answer.sources] == [
        "para-0004",
        "sheet-plan-r0002-r0004",
    ]
    assert foundry.lookups == []
    assert foundry.script.bodies[0] == {
        "input": QUESTION,
        "conversation": "conv_7",
        "agent_reference": foundry.reference("docwiki-researcher", "2"),
    }


def _ingest_steps(approved: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    first = response(
        list_tools("ingest_start", "run_status"),
        message("I will enqueue an ingest of raw/plans/ with ingest_start."),
        approval_request("mcpr_1", "ingest_start", {"reason": "new plans"}),
        response_id="resp_1",
    )
    if approved:
        items = [
            mcp_call(
                "ingest_start",
                {"reason": "new plans"},
                output='{"ok": true, "queued": true}',
                approval_request_id="mcpr_1",
            ),
            message("Queued; run_status reports the run as running, not finished."),
        ]
    else:
        items = [message("The ingest was not approved: nothing was enqueued.")]
    return first, response(*items, response_id="resp_2")


@pytest.mark.parametrize(
    ("approve", "stdin", "approved"), [("prompt", "y\n", True), ("deny", None, False)]
)
def test_ask_librarian_with_approvals(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    approve: str,
    stdin: str | None,
    approved: bool,
) -> None:
    foundry = Foundry(monkeypatch, *_ingest_steps(approved))
    result = _ask(
        tmp_path, "Ingest the new plans", "--agent", "librarian", "--approve", approve, stdin=stdin
    )

    assert result.exit_code == 0, result.output
    reference = foundry.reference("docwiki-librarian", "6")
    assert foundry.script.bodies[1] == {
        "input": [
            {"type": "mcp_approval_response", "approve": approved, "approval_request_id": "mcpr_1"}
        ],
        "previous_response_id": "resp_1",
        "agent_reference": reference,
    }
    assert "I will enqueue an ingest of raw/plans/ with ingest_start." in result.stdout
    if approved:
        assert "docwiki-librarian wants to call docwiki.ingest_start" in result.stderr
        assert "run as running, not finished." in result.stdout
        assert "[denied:" not in result.stdout
    else:
        assert "[denied: ingest_start]" in result.stdout


def test_ask_json_reports_mcp_tool_failures(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    errors = pytest.importorskip("docwiki.mcp.errors")
    failure = errors.failure_payload("not_found", "unknown page 'topic:x'", tool="read_page")
    Foundry(
        monkeypatch,
        response(
            mcp_call("read_page", {"page": "topic:x"}, output=json.dumps(failure)),
            message("Not found in the wiki."),
        ),
    )
    result = _ask(tmp_path, QUESTION, "--json")

    assert result.exit_code == 0, result.output
    answer = AgentAnswer.model_validate_json(result.stdout)
    assert [(call.name, call.status, call.error) for call in answer.tool_calls] == [
        ("read_page", "failed", "not_found: unknown page 'topic:x'")
    ]
    assert answer.sources == []


@pytest.mark.parametrize(
    ("agent", "endpoint", "message_part"),
    [
        ("auditor", TEST_ENDPOINT, "agent auditor is not deployed"),
        ("researcher", "", "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT is not set"),
    ],
)
def test_ask_errors_exit_non_zero(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, agent: str, endpoint: str, message_part: str
) -> None:
    foundry = Foundry(monkeypatch)
    monkeypatch.setenv("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT", endpoint)
    result = _ask(tmp_path, QUESTION, "--agent", agent)

    assert result.exit_code == 1
    assert message_part in result.stderr
    assert foundry.script.requests == []
