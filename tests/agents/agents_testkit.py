"""Test helpers for docwiki.agents_client: fake Foundry project/OpenAI clients, response builders.

No test talks to Azure: the fakes implement only the SDK calls the package uses, and the
end-to-end client test serves HTTP with ``httpx2.MockTransport`` behind the real SDK clients.
"""

from __future__ import annotations

import asyncio
import json
import shutil
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import httpx2
from azure.core.credentials import AccessToken, AccessTokenInfo
from azure.core.exceptions import HttpResponseError, ResourceNotFoundError

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENTS_DIR = REPO_ROOT / "agents"
TEST_ENDPOINT = "https://example.com/api/projects/demo"
MCP_URL = "https://docwiki-mcp.example/mcp"
CONNECTION = "docwiki-mcp"
TOKEN_EXPIRY = 4_102_444_800  # 2100-01-01

DEPLOY_ENV: dict[str, str] = {
    "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": TEST_ENDPOINT,
    "DOCWIKI_SMART_DEPLOYMENT": "smart-deployment",
    "DOCWIKI_MCP_URL": MCP_URL,
    "DOCWIKI_MCP_CONNECTION": CONNECTION,
}

ANSWER_TEXT = (
    "The walls of the extension are 70 % complete [1]. Planning indice B still lists 100 % for "
    "task T05 [2]; the minutes have the higher authority (authority, then recency) [1][2].\n\n"
    "Sources:\n"
    "[1] Site meeting minutes n°3 — ¶ 7 (native-text) — "
    "evidence/src-165f1d3a109c/para-0007.md\n"
    '[2] Planning and purchase tracking, indice B — sheet "Planning", rows 6–9 '
    "(deterministic-table) — evidence/src-86eabe3d6d0d/sheet-planning-r0006-r0009.md"
)


def copy_agents(tmp_path: Path) -> Path:
    """A writable copy of the committed agent definitions (YAML and instructions)."""
    target = tmp_path / "agents"
    shutil.copytree(AGENTS_DIR, target, ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    return target


def edit_file(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, f"{old!r} not in {path}"
    path.write_text(text.replace(old, new), encoding="utf-8")


# ---------------------------------------------------------------------- Responses API items


def message(text: str, *, item_id: str = "msg_1") -> dict[str, Any]:
    return {
        "type": "message",
        "id": item_id,
        "role": "assistant",
        "status": "completed",
        "content": [{"type": "output_text", "text": text, "annotations": []}],
    }


def list_tools(*names: str, error: str | None = None) -> dict[str, Any]:
    return {
        "type": "mcp_list_tools",
        "id": "mcpl_1",
        "server_label": "docwiki",
        "tools": [{"name": name, "input_schema": {"type": "object"}} for name in names],
        "error": error,
    }


def mcp_call(
    name: str,
    arguments: dict[str, Any],
    *,
    output: str | None = "ok",
    error: Any = None,
    status: str | None = "completed",
    item_id: str = "mcp_1",
    approval_request_id: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "type": "mcp_call",
        "id": item_id,
        "server_label": "docwiki",
        "name": name,
        "arguments": json.dumps(arguments),
        "output": output,
        "error": error,
        "approval_request_id": approval_request_id,
    }
    if status is not None:
        item["status"] = status
    return item


def approval_request(request_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "mcp_approval_request",
        "id": request_id,
        "server_label": "docwiki",
        "name": name,
        "arguments": json.dumps(arguments),
    }


def response(
    *items: dict[str, Any],
    response_id: str = "resp_1",
    status: str = "completed",
    input_tokens: int = 100,
    output_tokens: int = 20,
    cached_tokens: int = 0,
    reasoning_tokens: int = 0,
    error: dict[str, Any] | None = None,
    incomplete_reason: str | None = None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """A Responses API JSON body as returned by the service."""
    return {
        "id": response_id,
        "object": "response",
        "created_at": 1_700_000_000,
        "status": status,
        "model": "smart-deployment",
        "error": error,
        "incomplete_details": {"reason": incomplete_reason} if incomplete_reason else None,
        "conversation": {"id": conversation_id} if conversation_id else None,
        "output": list(items),
        "usage": {
            "input_tokens": input_tokens,
            "input_tokens_details": {"cached_tokens": cached_tokens},
            "output_tokens": output_tokens,
            "output_tokens_details": {"reasoning_tokens": reasoning_tokens},
            "total_tokens": input_tokens + output_tokens,
        },
        "parallel_tool_calls": True,
        "tool_choice": "auto",
        "tools": [],
    }


# ---------------------------------------------------------------------- fake SDK clients


class FakeResponses:
    """``AsyncOpenAI.responses`` serving scripted results in order."""

    def __init__(self, *steps: Any) -> None:
        self.steps = list(steps)
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        if not self.steps:
            raise AssertionError("unexpected responses.create call")
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        return step


class FakeOpenAI:
    def __init__(self, *steps: Any) -> None:
        self.responses = FakeResponses(*steps)
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeAgents:
    """``AIProjectClient.agents``: versions are dicts keyed like the REST payloads."""

    def __init__(self, versions: dict[str, list[dict[str, Any]]] | None = None) -> None:
        self.versions: dict[str, list[dict[str, Any]]] = versions or {}
        self.get_calls: list[str] = []
        self.created: list[tuple[str, dict[str, Any]]] = []
        self.deleted: list[str] = []
        self.create_error: BaseException | None = None
        self.get_error: BaseException | None = None
        self.version_identity = True  # False: only the agent object carries instance_identity

    @staticmethod
    def identity(agent_name: str) -> dict[str, str]:
        return {"principal_id": f"principal-{agent_name}", "client_id": f"client-{agent_name}"}

    async def get(self, agent_name: str) -> dict[str, Any]:
        self.get_calls.append(agent_name)
        if self.get_error is not None:
            raise self.get_error
        if not self.versions.get(agent_name):
            raise ResourceNotFoundError(f"agent {agent_name} not found")
        return {
            "object": "agent",
            "id": agent_name,
            "name": agent_name,
            "versions": {"latest": self.versions[agent_name][-1]},
            "instance_identity": self.identity(agent_name),
        }

    async def create_version(self, agent_name: str, body: dict[str, Any]) -> dict[str, Any]:
        if self.create_error is not None:
            raise self.create_error
        self.created.append((agent_name, json.loads(json.dumps(body))))
        versions = self.versions.setdefault(agent_name, [])
        created = {
            "object": "agent.version",
            "id": f"{agent_name}:{len(versions) + 1}",
            "name": agent_name,
            "version": str(len(versions) + 1),
            "metadata": dict(body["metadata"]),
            "definition": body["definition"],
            "description": body.get("description"),
            "created_at": 1_700_000_000,
        }
        if self.version_identity:
            created["instance_identity"] = self.identity(agent_name)
        versions.append(created)
        return created

    async def delete(self, agent_name: str) -> dict[str, Any]:
        self.deleted.append(agent_name)
        if agent_name not in self.versions:
            raise ResourceNotFoundError(f"agent {agent_name} not found")
        del self.versions[agent_name]
        return {"object": "agent.deleted", "name": agent_name, "deleted": True}


def connection(
    *, target: str = MCP_URL, auth_type: str = "AgenticIdentityToken_Preview"
) -> dict[str, Any]:
    return {
        "name": CONNECTION,
        "id": f"connections/{CONNECTION}",
        "type": "RemoteTool_Preview",
        "target": target,
        "isDefault": False,
        "credentials": {"type": auth_type},
        "metadata": {},
    }


class FakeConnections:
    def __init__(self, connections: dict[str, dict[str, Any]] | None = None) -> None:
        self.connections = connections if connections is not None else {CONNECTION: connection()}
        self.calls: list[str] = []

    async def get(self, name: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(name)
        if name not in self.connections:
            raise ResourceNotFoundError(f"connection {name} not found")
        return self.connections[name]


class FakeRoutines:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def create_or_update(self, routine_name: str, body: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((routine_name, body))
        return {"name": routine_name, **body}


class FakeProject:
    """Duck-typed ``azure.ai.projects.aio.AIProjectClient``."""

    def __init__(
        self,
        *,
        versions: dict[str, list[dict[str, Any]]] | None = None,
        connections: dict[str, dict[str, Any]] | None = None,
        openai: Any = None,
    ) -> None:
        self.agents = FakeAgents(versions)
        self.connections = FakeConnections(connections)
        self.beta = SimpleNamespace(routines=FakeRoutines())
        self.openai = openai
        self.openai_options: dict[str, Any] | None = None
        self.closed = False

    def get_openai_client(self, **options: Any) -> Any:
        self.openai_options = options
        return self.openai

    async def close(self) -> None:
        self.closed = True


def agent_version(version: str, definition_sha256: str = "abc") -> dict[str, Any]:
    return {
        "object": "agent.version",
        "id": f"v{version}",
        "name": "docwiki-researcher",
        "version": version,
        "metadata": {"docwiki_definition_sha256": definition_sha256},
        "created_at": 1_700_000_000,
        "definition": {"kind": "prompt", "model": "smart-deployment"},
    }


def http_error(status: int, message: str = "simulated") -> HttpResponseError:
    error = HttpResponseError(message=message)
    error.status_code = status
    return error


# ---------------------------------------------------------------------- HTTP-level fakes


class StaticCredential:
    """AsyncTokenCredential returning a fixed fake token; records requested scopes."""

    def __init__(self) -> None:
        self.scopes: list[tuple[str, ...]] = []

    async def get_token(self, *scopes: str, **kwargs: Any) -> AccessToken:
        self.scopes.append(scopes)
        return AccessToken("unit-test-token", TOKEN_EXPIRY)

    async def get_token_info(self, *scopes: str, options: Any = None) -> AccessTokenInfo:
        self.scopes.append(scopes)
        return AccessTokenInfo("unit-test-token", TOKEN_EXPIRY)

    async def close(self) -> None:
        return None


Step = httpx2.Response | Callable[[httpx2.Request], httpx2.Response]


class Script:
    """``httpx2.MockTransport`` handler serving scripted HTTP responses in order."""

    def __init__(self, *steps: Step) -> None:
        self.steps = list(steps)
        self.requests: list[httpx2.Request] = []
        self.bodies: list[dict[str, Any]] = []

    async def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        self.bodies.append(json.loads(request.content))
        await asyncio.sleep(0)
        step = self.steps.pop(0)
        return step(request) if callable(step) else step
