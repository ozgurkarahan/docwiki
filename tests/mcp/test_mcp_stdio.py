"""stdio mode: spawn the real server process and talk to it with the MCP SDK client."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from mcp_testkit import FIXTURE_ROOT, RELEASE_ID, stdio_session, tool_payload

from docwiki.mcp import OPS_TOOLS, READ_TOOLS
from mcp import StdioServerParameters

REPO_ROOT = Path(__file__).resolve().parents[2]


def stdio_params(release: Path, *extra: str) -> StdioServerParameters:
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", "docwiki.mcp.server", "--stdio", "--release", str(release), *extra],
        env={"DOCWIKI_AUTH_MODE": "none", "PYTHONUTF8": "1"},
        cwd=str(REPO_ROOT),
    )


@pytest.mark.parametrize("mode", ["legacy", "auto"])
async def test_stdio_server_lists_read_tools_and_searches(mode: str) -> None:
    async with stdio_session(stdio_params(FIXTURE_ROOT), mode=mode) as client:
        assert client.server_info is None or client.server_info.name == "docwiki"
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == set(READ_TOOLS)
        data = tool_payload(
            await client.call_tool("search", {"query": "date de livraison des fenêtres"})
        )
        assert data["release_id"] == RELEASE_ID and data["hits"]
        skills = tool_payload(await client.call_tool("list_skills", {}))
        assert "wiki-navigator" in {skill["name"] for skill in skills["skills"]}


async def test_stdio_allow_ops_exposes_operations(tmp_path: Path) -> None:
    params = stdio_params(FIXTURE_ROOT, "--allow-ops", "--work-dir", str(tmp_path / "work"))
    async with stdio_session(params) as client:
        listed = await client.list_tools()
        assert {tool.name for tool in listed.tools} == {*READ_TOOLS, *OPS_TOOLS}
        result = tool_payload(
            await client.call_tool("write_health_report", {"markdown": "# Health\n\nok"})
        )
        assert result["ok"] is True, json.dumps(result)
        assert (tmp_path / "work" / Path(result["written"])).is_file()
