"""Portable wiki folders (CONTRACT.md section 19): served from disk over stdio and HTTP.

The committed sample wiki is a portable folder (wiki at the root, ``evidence/``, machine files
in ``.docwiki/``) and the local agent configurations point the stdio server at it.
"""

from __future__ import annotations

import json
import sys
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from mcp_testkit import (
    FIXTURE_ROOT,
    NOW,
    PLAN,
    READ_CALLS,
    RELEASE_ID,
    check_read_results,
    stage_release,
    stdio_session,
    tool_payload,
)
from starlette.testclient import TestClient

from docwiki.mcp import READ_TOOLS
from docwiki.mcp.config import McpConfig
from docwiki.mcp.server import create_app
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import ReadTools, ToolInputError
from docwiki.release import export_portable, is_portable
from mcp import StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def portable_wiki(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A portable export of the mock release (read-only for the tests that use it)."""
    folder = export_portable(FIXTURE_ROOT, tmp_path_factory.mktemp("portable") / "wiki")
    assert is_portable(folder) and not (folder / "manifest.json").exists()
    assert (folder / "index.md").is_file() and (folder / ".docwiki" / "search.db").is_file()
    return folder


def _files(root: Path) -> dict[str, tuple[int, int]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_folder_source_serves_a_portable_folder(portable_wiki: Path) -> None:
    before = _files(portable_wiki)
    source = FolderReleaseSource(portable_wiki)
    snapshot = source.current()
    assert snapshot.release_id == RELEASE_ID and snapshot.reader.portable
    assert source.release_ids() == [RELEASE_ID]
    assert source.manifest_for(RELEASE_ID).release_id == RELEASE_ID
    with pytest.raises(KeyError):
        source.manifest_for("20990101T000000Z-00000000")
    reads = ReadTools(source, McpConfig())
    tables = json.loads(reads.query_table(PLAN, "SELECT count(*) AS n FROM t01"))
    assert tables["rows"] == [[3]]
    with pytest.raises(ToolInputError, match="sources with tables: src-43c97f7dfcde") as missing:
        reads.query_table("src-4d9c65e05302", "SELECT 1")
    assert missing.value.code == "not_found"
    assert missing.value.details == {"sources_with_tables": [PLAN]}
    assert _files(portable_wiki) == before, "serving never writes to the folder"


def test_reexported_portable_folder_is_reloaded(tmp_path: Path) -> None:
    """Re-exporting in place works while the server runs (no release file stays open) and the
    new release is served after the pointer TTL."""
    folder = export_portable(FIXTURE_ROOT, tmp_path / "wiki")
    now = [1000.0]
    source = FolderReleaseSource(folder, ttl_s=30, clock=lambda: now[0])
    reads = ReadTools(source, McpConfig())
    first = source.current()
    assert json.loads(reads.search("gearbox"))["release_id"] == RELEASE_ID
    staged = stage_release(
        tmp_path / "staged", created_at=NOW + timedelta(days=1), topic_note="Re-exported note."
    )
    export_portable(staged.root, folder)
    assert source.current() is first, "re-checked at most every ttl_s"
    now[0] += 31
    assert source.current().release_id == staged.release_id
    assert "Re-exported note." in json.loads(reads.read_page("topic:gearbox-oil"))["markdown"]
    assert json.loads(reads.search("re-exported note"))["hits"]


def test_portable_folder_over_http(portable_wiki: Path) -> None:
    app = create_app(portable_wiki, config=McpConfig(), bind_host="127.0.0.1")
    headers = {
        "accept": "application/json, text/event-stream",
        "content-type": "application/json",
        "mcp-protocol-version": "2025-11-25",
    }

    def rpc(method: str, params: dict[str, Any]) -> dict[str, Any]:
        body = {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}
        response = client.post("/mcp", json=body, headers=headers)
        assert response.status_code == 200, response.text
        return response.json()["result"]

    with TestClient(app, base_url="http://127.0.0.1:8765") as client:
        health = client.get("/healthz").json()
        assert health["status"] == "ok" and health["release_id"] == RELEASE_ID
        assert {tool["name"] for tool in rpc("tools/list", {})["tools"]} == set(READ_TOOLS)
        results = {}
        for name, arguments in READ_CALLS.items():
            result = rpc("tools/call", {"name": name, "arguments": arguments})
            assert result.get("isError") in (None, False)
            results[name] = json.loads(result["content"][0]["text"])
    check_read_results(results)


async def test_portable_folder_over_stdio(portable_wiki: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "docwiki.mcp.server", "--stdio", "--release", str(portable_wiki)],
        env={"DOCWIKI_AUTH_MODE": "none", "PYTHONUTF8": "1"},
        cwd=str(REPO_ROOT),
    )
    async with stdio_session(params) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == set(READ_TOOLS)
        results = {
            name: tool_payload(await client.call_tool(name, arguments))
            for name, arguments in READ_CALLS.items()
        }
        pdf = tool_payload(
            await client.call_tool(
                "get_evidence", {"source_id": "src-f2750f41f3fa", "locator_key": "p0001"}
            )
        )
    check_read_results(results)
    assert pdf["provenance"] == "native-text" and "img/p0001.png" in pdf["content"]
    assert (portable_wiki / "evidence" / "src-f2750f41f3fa" / "img" / "p0001.png").is_file()
