"""Local agent configurations launch the stdio server the same way the tests do."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docwiki.mcp.config import McpConfig
from docwiki.mcp.server import _parser
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import ReadTools

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize(
    ("relative", "key"),
    [(".vscode/mcp.json", "servers"), (".mcp.json", "mcpServers")],
)
def test_local_agent_configs_launch_the_stdio_server(relative: str, key: str) -> None:
    config = json.loads((REPO_ROOT / relative).read_text(encoding="utf-8"))
    server = config[key]["docwiki"]
    assert server["type"] == "stdio" and server["command"] == "uv"
    args = server["args"]
    assert args[:3] == ["run", "--extra", "mcp"]
    module = args.index("-m")
    assert args[module + 1] == "docwiki.mcp.server"
    parsed = _parser().parse_args(args[module + 2 :])
    assert parsed.stdio and not parsed.allow_ops
    # Clone-and-ask works without Azure: the shipped configs serve the committed mock release.
    assert parsed.release == "samples/fixtures/mock-release"
    assert (REPO_ROOT / parsed.release / "releases" / "current.json").is_file() or (
        REPO_ROOT / parsed.release / "manifest.json"
    ).is_file() or any((REPO_ROOT / parsed.release).glob("**/manifest.json"))


def test_mock_release_is_servable_by_the_documented_local_command() -> None:
    source = FolderReleaseSource(REPO_ROOT / "samples" / "fixtures" / "mock-release")
    reads = ReadTools(source, McpConfig())
    assert json.loads(reads.list_skills())["skills"]
    assert json.loads(reads.get_index("home"))["ok"] is True
