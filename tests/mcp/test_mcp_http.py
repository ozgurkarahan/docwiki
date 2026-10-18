"""HTTP app: /healthz, 401 without a valid bearer token, role enforcement per tool as structured
results, auth-mode policy."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from mcp_testkit import FIXTURE_ROOT, MINT, NOW, RELEASE_ID, bearer_headers, principal_header
from starlette.testclient import TestClient

from docwiki.contracts.storage import FolderStorage
from docwiki.mcp import OPS_TOOLS, READ_TOOLS
from docwiki.mcp.config import McpConfig
from docwiki.mcp.ingest_queue import FolderQueue
from docwiki.mcp.server import create_app
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_ops import OpsTools
from docwiki.mcp.workstore import WorkStore

HEADERS = {
    "accept": "application/json, text/event-stream",
    "content-type": "application/json",
    "mcp-protocol-version": "2025-11-25",
}
RESEARCHER = bearer_headers("Wiki.Read", subject="researcher-agent-7")
LIBRARIAN = bearer_headers("Wiki.Read", "Wiki.Operate", subject="librarian-agent-3")
ALL_TOOLS = {*READ_TOOLS, *OPS_TOOLS}


def rpc(
    client: TestClient,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    caller: dict[str, str] | None = None,
) -> Any:
    headers = {**HEADERS, **(caller or {})}
    body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}}
    return client.post("/mcp", json=body, headers=headers)


def tool_names(response: Any) -> set[str]:
    assert response.status_code == 200, response.text
    return {tool["name"] for tool in response.json()["result"]["tools"]}


def call(client: TestClient, name: str, arguments: dict[str, Any], caller: dict[str, str]) -> Any:
    """Body of a tools/call over HTTP: always a JSON-RPC result, never isError (ADR 0003 F3)."""
    response = rpc(client, "tools/call", {"name": name, "arguments": arguments}, caller=caller)
    assert response.status_code == 200, response.text
    body = response.json()
    assert "error" not in body, "tool failures are never JSON-RPC errors"
    result = body["result"]
    assert result.get("isError") in (None, False), "tool failures are never isError results"
    return json.loads(result["content"][0]["text"])


@pytest.fixture
def work(tmp_path: Path) -> FolderStorage:
    return FolderStorage(tmp_path / "work-root", fsync=False)


def _ops(config: McpConfig, work: FolderStorage) -> OpsTools:
    return OpsTools(
        FolderReleaseSource(FIXTURE_ROOT),
        config,
        store_factory=lambda: WorkStore(work),
        queue_factory=lambda: FolderQueue(work),
        clock=lambda: NOW,
    )


@pytest.fixture
def easyauth(work: FolderStorage) -> Iterator[TestClient]:
    config = MINT.config()
    app = create_app(
        FIXTURE_ROOT,
        config=config,
        ops=_ops(config, work),
        bind_host="0.0.0.0",
        token_validator=MINT.validator(config),
    )
    with TestClient(app) as client:
        yield client


def test_healthz_needs_no_principal(easyauth: TestClient) -> None:
    response = easyauth.get("/healthz")
    assert response.status_code == 200
    assert response.json()["status"] == "ok" and response.json()["release_id"] == RELEASE_ID


def test_missing_or_invalid_principal_is_401(easyauth: TestClient) -> None:
    missing = rpc(easyauth, "tools/list")
    assert missing.status_code == 401
    assert missing.headers["www-authenticate"] == "Bearer"
    assert missing.json() == {"error": "unauthorized", "message": "authentication required"}
    garbage = {**RESEARCHER, "x-ms-client-principal": "garbage!!"}
    assert rpc(easyauth, "tools/list", caller=garbage).status_code == 401
    duplicated = easyauth.post(
        "/mcp",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers=[
            *HEADERS.items(),
            ("authorization", RESEARCHER["authorization"]),
            ("x-ms-client-principal", RESEARCHER["x-ms-client-principal"]),
            ("x-ms-client-principal", LIBRARIAN["x-ms-client-principal"]),
        ],
    )
    assert duplicated.status_code == 401, "an ambiguous principal is never trusted"


def test_forged_principal_header_without_token_is_401(
    easyauth: TestClient, work: FolderStorage, caplog: pytest.LogCaptureFixture
) -> None:
    """What reaches the app when built-in auth is missing: a forged header and no token."""
    forged = {"x-ms-client-principal": principal_header("Wiki.Read", "Wiki.Operate")}
    with caplog.at_level(logging.WARNING, logger="docwiki.mcp.auth"):
        listed = rpc(easyauth, "tools/list", caller=forged)
        queued = rpc(
            easyauth,
            "tools/call",
            {"name": "ingest_start", "arguments": {"reason": "forged"}},
            caller=forged,
        )
    assert listed.status_code == 401 and queued.status_code == 401
    assert listed.json() == {"error": "unauthorized", "message": "authentication required"}
    assert work.list("work/queue/") == [], "a rejected call has no effect"
    assert "did not forward the Authorization header" in caplog.text


def test_only_bearer_tokens_are_accepted(easyauth: TestClient) -> None:
    token = RESEARCHER["authorization"].split(" ", 1)[1]
    for value in (token, f"Basic {token}", "Bearer", f"Bearer {token} extra"):
        caller = {**RESEARCHER, "authorization": value}
        assert rpc(easyauth, "tools/list", caller=caller).status_code == 401, value
    lower_case = {"authorization": f"bearer {token}"}
    assert rpc(easyauth, "tools/list", caller=lower_case).status_code == 200


def test_valid_token_without_principal_header_is_enough(easyauth: TestClient) -> None:
    token_only = {"authorization": RESEARCHER["authorization"]}
    assert tool_names(rpc(easyauth, "tools/list", caller=token_only)) == ALL_TOOLS


def test_researcher_lists_every_tool_but_calls_read_tools_only(
    easyauth: TestClient, work: FolderStorage, caplog: pytest.LogCaptureFixture
) -> None:
    # Not filtered per role: Agent Service caches a connection's tool list across the agents
    # that share it, so a Researcher's list would hide the Librarian's operations tools.
    assert tool_names(rpc(easyauth, "tools/list", caller=RESEARCHER)) == ALL_TOOLS
    found = call(easyauth, "search", {"query": "gearbox oil"}, RESEARCHER)
    assert found["ok"] is True and found["hits"]
    with caplog.at_level(logging.INFO, logger="docwiki.mcp.auth"):
        denied = call(easyauth, "ingest_start", {"reason": "try"}, RESEARCHER)
    assert denied == {
        "ok": False,
        "tool": "ingest_start",
        "error": {
            "code": "forbidden",
            "message": denied["error"]["message"],
            "retryable": False,
            "details": {"required_role": "Wiki.Operate"},
        },
    }
    assert "Wiki.Operate" in denied["error"]["message"]
    assert "do not retry" in denied["error"]["message"]
    assert work.list("work/queue/") == [], "a denied call has no effect"
    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "outcome=forbidden" in logged and "principal:" in logged
    assert "researcher-agent-7" not in logged, "only a hash of the principal id is logged"
    assert RESEARCHER["authorization"].split(" ", 1)[1] not in logged, "tokens are never logged"


def test_principal_header_cannot_add_roles_to_the_token(
    easyauth: TestClient, work: FolderStorage, caplog: pytest.LogCaptureFixture
) -> None:
    """Researcher token plus a header claiming Wiki.Operate: the token's roles win."""
    inflated = MINT.headers(
        "Wiki.Read", subject="researcher-agent-7", header_roles=("Wiki.Read", "Wiki.Operate")
    )
    with caplog.at_level(logging.WARNING, logger="docwiki.mcp.auth"):
        assert rpc(easyauth, "tools/list", caller=inflated).status_code == 200
        denied = call(easyauth, "ingest_start", {"reason": "escalate"}, inflated)
    assert denied["error"]["code"] == "forbidden"
    assert work.list("work/queue/") == []
    assert "app role(s) the bearer token does not grant: ignored" in caplog.text
    impostor = {
        **RESEARCHER,
        "x-ms-client-principal": principal_header(
            "Wiki.Read", "Wiki.Operate", subject="librarian-agent-3"
        ),
    }
    with caplog.at_level(logging.WARNING, logger="docwiki.mcp.auth"):
        assert rpc(easyauth, "tools/list", caller=impostor).status_code == 200
        denied = call(easyauth, "ingest_start", {"reason": "impersonate"}, impostor)
    assert denied["error"]["code"] == "forbidden", "the token's subject and roles win"
    assert "names another caller than the bearer token" in caplog.text


def test_forbidden_comes_before_argument_validation(easyauth: TestClient) -> None:
    denied = call(easyauth, "recompile", {"source_ids": "not-a-list"}, RESEARCHER)
    assert denied["error"]["code"] == "forbidden", "unauthorized callers learn nothing else"


def test_librarian_can_operate(easyauth: TestClient, work: FolderStorage) -> None:
    assert tool_names(rpc(easyauth, "tools/list", caller=LIBRARIAN)) == {
        *READ_TOOLS,
        *OPS_TOOLS,
    }
    queued = call(easyauth, "ingest_start", {"reason": "New documents uploaded."}, LIBRARIAN)
    assert queued["ok"] is True and queued["queued"] is True
    assert len(work.list("work/queue/")) == 1
    missing = call(easyauth, "explain_source", {"source_id": "src-000000000000"}, LIBRARIAN)
    assert missing["ok"] is False and missing["error"]["code"] == "not_found"


def test_role_checks_have_no_implication(easyauth: TestClient) -> None:
    operator = bearer_headers("Wiki.Operate", subject="ops-only")
    assert tool_names(rpc(easyauth, "tools/list", caller=operator)) == ALL_TOOLS
    denied = call(easyauth, "search", {"query": "x"}, operator)
    assert denied["error"]["code"] == "forbidden"
    assert denied["error"]["details"]["required_role"] == "Wiki.Read"
    nobody = bearer_headers(subject="no-roles")
    assert tool_names(rpc(easyauth, "tools/list", caller=nobody)) == set()
    assert call(easyauth, "list_skills", {}, nobody)["error"]["code"] == "forbidden"
    unknown = call(easyauth, "drop_everything", {}, LIBRARIAN)
    assert unknown["ok"] is False and unknown["error"]["code"] == "not_found"


def test_token_validation_off_trusts_the_principal_header(
    work: FolderStorage, caplog: pytest.LogCaptureFixture
) -> None:
    """Explicit opt-out: the previous behaviour (header only), announced with a warning."""
    config = McpConfig(auth_mode="easyauth", token_validation="off")
    with caplog.at_level(logging.WARNING, logger="docwiki.mcp.auth"):
        app = create_app(FIXTURE_ROOT, config=config, ops=_ops(config, work), bind_host="0.0.0.0")
    assert "DOCWIKI_MCP_TOKEN_VALIDATION=off" in caplog.text
    researcher = {"x-ms-client-principal": RESEARCHER["x-ms-client-principal"]}
    librarian = {"x-ms-client-principal": LIBRARIAN["x-ms-client-principal"]}
    with TestClient(app) as client:
        assert rpc(client, "tools/list").status_code == 401
        assert rpc(client, "tools/list", caller={"x-ms-client-principal": "x"}).status_code == 401
        assert tool_names(rpc(client, "tools/list", caller=researcher)) == ALL_TOOLS
        refused = call(client, "ingest_start", {"reason": "header"}, researcher)
        assert refused["error"]["code"] == "forbidden"
        assert tool_names(rpc(client, "tools/list", caller=librarian)) == ALL_TOOLS
        assert call(client, "ingest_start", {"reason": "header"}, librarian)["ok"] is True


def test_none_mode_requires_loopback_and_ignores_principal_headers() -> None:
    with pytest.raises(ValueError, match="non-loopback"):
        create_app(FIXTURE_ROOT, config=McpConfig(), bind_host="0.0.0.0")
    app = create_app(FIXTURE_ROOT, config=McpConfig(), bind_host="127.0.0.1")
    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        listed = tool_names(rpc(client, "tools/list", caller=LIBRARIAN))
        assert listed == set(READ_TOOLS), "local callers get read tools without --allow-ops"
        response = client.post(
            "/mcp",
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
            headers={**HEADERS, "host": "attacker.example"},
        )
        assert response.status_code == 421, "DNS rebinding protection on loopback"


def test_none_mode_with_allow_ops(work: FolderStorage) -> None:
    config = McpConfig(allow_ops=True)
    app = create_app(FIXTURE_ROOT, config=config, ops=_ops(config, work), bind_host="localhost")
    with TestClient(app, base_url="http://localhost:8765") as client:
        assert tool_names(rpc(client, "tools/list")) == {*READ_TOOLS, *OPS_TOOLS}


def test_healthz_reports_unavailable_release(tmp_path: Path) -> None:
    config = MINT.config()
    app = create_app(
        tmp_path / "empty",
        config=config,
        ops=None,
        bind_host="0.0.0.0",
        token_validator=MINT.validator(config),
    )
    with TestClient(app) as client:
        assert client.get("/healthz").status_code == 503
        failed = call(client, "list_skills", {}, RESEARCHER)
        assert failed["error"]["code"] == "unavailable" and failed["error"]["retryable"] is True
        assert "no release is available" in failed["error"]["message"]
        assert str(tmp_path) not in json.dumps(failed), "no machine paths leak"
