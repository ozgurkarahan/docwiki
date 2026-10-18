"""MCP SDK client round trips (in-process and streamable HTTP) and server entry points."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx2
import pytest
from mcp.client.streamable_http import streamable_http_client
from mcp_testkit import (
    FIXTURE_ROOT,
    MINT,
    NOW,
    PLAN,
    RELEASE_ID,
    SOP_B,
    TENANT_ID,
    bearer_headers,
    tool_payload,
)

from docwiki.contracts.storage import FolderStorage
from docwiki.mcp import OPS_TOOLS, READ_TOOLS
from docwiki.mcp.config import McpConfig
from docwiki.mcp.ingest_queue import FolderQueue
from docwiki.mcp.server import build_server, create_app, main
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_ops import OpsTools
from docwiki.mcp.workstore import WorkStore
from mcp import Client

SPEC_TOOLS = {
    "search",
    "read_page",
    "get_index",
    "get_links",
    "glossary",
    "get_evidence",
    "query_table",
    "get_skill",
    "list_skills",
    "recent_changes",
    "ingest_start",
    "run_status",
    "list_sources",
    "quality_report",
    "explain_source",
    "recompile",
    "list_proposals",
    "decide_proposal",
    "write_health_report",
}


def _ops(work: FolderStorage, config: McpConfig) -> OpsTools:
    return OpsTools(
        FolderReleaseSource(FIXTURE_ROOT),
        config,
        store_factory=lambda: WorkStore(work),
        queue_factory=lambda: FolderQueue(work),
        clock=lambda: NOW,
    )


def _text(result: Any) -> dict[str, Any]:
    data = tool_payload(result)
    assert data["ok"] is True, data
    return data


async def test_tool_registry_matches_the_spec(tmp_path: Path) -> None:
    config = McpConfig(allow_ops=True)
    server = build_server(
        FolderReleaseSource(FIXTURE_ROOT),
        config=config,
        ops=_ops(FolderStorage(tmp_path, fsync=False), config),
    )
    tools = {tool.name: tool for tool in await server.list_tools()}
    assert set(tools) == SPEC_TOOLS == {*READ_TOOLS, *OPS_TOOLS}
    for name, tool in tools.items():
        assert tool.description and len(tool.description) > 80, name
        schema = tool.input_schema
        assert schema["type"] == "object" and "$defs" not in json.dumps(schema), name
        for prop in schema["properties"].values():
            assert prop.get("description"), f"{name}: every parameter is described"
        assert tool.annotations is not None
        assert tool.annotations.read_only_hint is (
            name
            not in {
                "ingest_start",
                "recompile",
                "decide_proposal",
                "write_health_report",
            }
        )
    scope = tools["ingest_start"].input_schema["properties"]["scope"]
    assert "source_ids" in json.dumps(scope) and "prefix" in json.dumps(scope)
    assert tools["search"].input_schema["required"] == ["query"]
    assert server.instructions and "get_evidence" in server.instructions


async def test_in_process_round_trip_with_every_read_tool() -> None:
    server = build_server(FolderReleaseSource(FIXTURE_ROOT), config=McpConfig())
    async with Client(server) as client:
        calls: dict[str, dict[str, Any]] = {
            "search": {"query": "WTG-07 oil"},
            "read_page": {"page": "topic:gearbox-oil", "section": "Contradictions"},
            "get_index": {"scope": "topics"},
            "get_links": {"page": SOP_B},
            "glossary": {"term": "SOP"},
            "get_evidence": {"source_id": SOP_B, "locator_key": "para-0004"},
            "query_table": {"source_id": PLAN, "sql": "SELECT row_id, due FROM t01"},
            "get_skill": {"name": "cite-sources"},
            "list_skills": {},
            "recent_changes": {"since": "2026-02-01", "limit": 3},
        }
        for name, arguments in calls.items():
            data = _text(await client.call_tool(name, arguments))
            assert data["release_id"] == RELEASE_ID, name
        bad = tool_payload(
            await client.call_tool("query_table", {"source_id": PLAN, "sql": "DROP TABLE t01"})
        )
        assert bad["error"]["code"] == "invalid_argument"
        assert "query rejected" in bad["error"]["message"]
        invalid = tool_payload(await client.call_tool("search", {"query": "x", "limit": 500}))
        assert invalid["error"]["code"] == "invalid_argument", "validated against the schema"
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == set(READ_TOOLS)


async def test_in_process_easyauth_without_http_fails_closed() -> None:
    server = build_server(FolderReleaseSource(FIXTURE_ROOT), config=McpConfig(auth_mode="easyauth"))
    async with Client(server) as client:
        assert (await client.list_tools()).tools == [], "no caller, no tools"
        denied = tool_payload(await client.call_tool("search", {"query": "oil"}))
        assert denied["ok"] is False and denied["error"]["code"] == "forbidden"


@pytest.mark.parametrize("mode", ["legacy", "auto"])
async def test_streamable_http_round_trip_with_roles(tmp_path: Path, mode: str) -> None:
    config = MINT.config()
    work = FolderStorage(tmp_path / "work", fsync=False)
    app = create_app(
        FIXTURE_ROOT,
        config=config,
        ops=_ops(work, config),
        bind_host="0.0.0.0",
        token_validator=MINT.validator(config),
    )

    async def session(headers: dict[str, str]) -> Client:
        http = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            base_url="http://mcp.example",
            headers=headers,
        )
        return Client(streamable_http_client("http://mcp.example/mcp", http_client=http), mode=mode)

    async with app.state.mcp_server.session_manager.run():
        async with await session(bearer_headers("Wiki.Read")) as researcher:
            listed = await researcher.list_tools()
            # Every tool is listed to a role holder (Agent Service shares a connection's tool
            # list across agents); the operations tools still answer forbidden.
            assert {tool.name for tool in listed.tools} == {*READ_TOOLS, *OPS_TOOLS}
            data = _text(
                await researcher.call_tool(
                    "get_evidence", {"source_id": SOP_B, "locator_key": "para-0004"}
                )
            )
            assert data["badge"] == "✓ quote verified"
            denied = tool_payload(await researcher.call_tool("run_status", {}))
            assert denied["error"]["code"] == "forbidden"
            assert denied["error"]["details"] == {"required_role": "Wiki.Operate"}
        librarian_headers = bearer_headers("Wiki.Read", "Wiki.Operate", subject="librarian")
        async with await session(librarian_headers) as librarian:
            status = _text(await librarian.call_tool("run_status", {}))
            assert status["runs"] == [] and status["served_release_id"] == RELEASE_ID
            report = _text(await librarian.call_tool("write_health_report", {"markdown": "# ok"}))
            assert report["written"] == "work/reports/health-2026-03-01.md"


def test_main_refuses_unsafe_or_invalid_configurations(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    for key in (
        "DOCWIKI_AUTH_MODE",
        "DOCWIKI_MODE",
        "DOCWIKI_RELEASE",
        "DOCWIKI_STORAGE_ACCOUNT",
        "DOCWIKI_MCP_TENANT_ID",
        "DOCWIKI_MCP_AUDIENCE",
        "DOCWIKI_MCP_ALLOWED_CLIENT_IDS",
        "DOCWIKI_MCP_TOKEN_VALIDATION",
    ):
        monkeypatch.delenv(key, raising=False)
    assert main(["--http", "0.0.0.0:8080", "--release", str(FIXTURE_ROOT)]) == 2
    assert "refusing DOCWIKI_AUTH_MODE=none" in capsys.readouterr().err
    assert main(["--http", ":8080", "--release", str(FIXTURE_ROOT)]) == 2
    assert main(["--http", "nonsense", "--release", str(FIXTURE_ROOT)]) == 2
    assert main(["--stdio", "--release", str(tmp_path / "missing")]) == 2
    assert "cannot load the release" in capsys.readouterr().err
    assert main(["--stdio", "--storage", "blob"]) == 2
    assert "DOCWIKI_STORAGE_ACCOUNT" in capsys.readouterr().err
    monkeypatch.setenv("DOCWIKI_AUTH_MODE", "easyauth")
    assert main(["--stdio", "--release", str(FIXTURE_ROOT)]) == 2
    assert "needs --http" in capsys.readouterr().err
    # easyauth validates bearer tokens: without a tenant and an audience the server refuses.
    assert main(["--http", "0.0.0.0:8080", "--release", str(FIXTURE_ROOT)]) == 2
    err = capsys.readouterr().err
    assert "DOCWIKI_MCP_TENANT_ID and DOCWIKI_MCP_AUDIENCE" in err
    assert "DOCWIKI_MCP_TOKEN_VALIDATION=off" in err
    monkeypatch.setenv("DOCWIKI_MCP_TENANT_ID", TENANT_ID)
    assert main(["--http", "0.0.0.0:8080", "--release", str(FIXTURE_ROOT)]) == 2
    assert "set DOCWIKI_MCP_AUDIENCE (or" in capsys.readouterr().err
    monkeypatch.setenv("DOCWIKI_MCP_TENANT_ID", "not-a-tenant")
    assert main(["--http", "0.0.0.0:8080", "--release", str(FIXTURE_ROOT)]) == 2
    assert "must be a tenant ID" in capsys.readouterr().err
    monkeypatch.setenv("DOCWIKI_MCP_TENANT_ID", TENANT_ID)
    monkeypatch.setenv("DOCWIKI_MCP_TOKEN_VALIDATION", "sometimes")
    assert main(["--http", "0.0.0.0:8080", "--release", str(FIXTURE_ROOT)]) == 2
    assert "must be 'required' or 'off'" in capsys.readouterr().err
    monkeypatch.setenv("DOCWIKI_AUTH_MODE", "bogus")
    assert main(["--stdio"]) == 2
