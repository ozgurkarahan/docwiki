"""``within``: search and indexes restricted to one scope value (v1.7, ADR 0011).

The committed mock release has no scopes (and a schema 1 search database); a scoped copy is
staged here: the two schedule revisions belong to the chantier ``moreau``, the minutes to the
default scope ``entreprise``, with a hub page and the hubs index.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from mcp_testkit import (
    MINUTES,
    NOW,
    PLAN_A,
    PLAN_B,
    TOPIC_ID,
    copy_fixture,
    stage_release,
    tool_payload,
)

from docwiki.contracts.storage import FolderStorage
from docwiki.mcp.config import McpConfig
from docwiki.mcp.server import build_server
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import ReadTools, ToolInputError
from docwiki.release import publish_release
from mcp import Client

Json = Callable[[str], dict[str, Any]]
HUB = "hub:chantiers/moreau"
PLAN_B_PATH = "sources/pln-2026-003-indice-b-planning-et-suivi-des-achats.md"
SCOPES = {PLAN_A: "moreau", PLAN_B: "moreau", MINUTES: "entreprise"}


def _common(title: str) -> dict[str, Any]:
    return {
        "title": title,
        "summary": "Fictional sample.",
        "sensitivity": "public",
        "updated": date(2026, 4, 1),
    }


HUB_PAGE = (
    "chantiers/moreau.md",
    {
        **_common("Chantier Moreau"),
        "id": HUB,
        "type": "hub",
        "scope_type": "chantier",
        "scope": "moreau",
        "sources": sorted([PLAN_A, PLAN_B]),
    },
    "# Chantier Moreau\n\nThe hub of the chantier: its documents and its schedule.\n\n"
    f"- [Planning and purchase tracking, indice B](../{PLAN_B_PATH})\n",
)
HUBS_INDEX = (
    "chantiers/index.md",
    {**_common("Chantiers"), "id": "index:hubs/chantiers", "type": "index"},
    "# Chantiers\n\n- [Chantier Moreau](moreau.md): 2 documents\n",
)


@pytest.fixture
def scoped(tmp_path: Path) -> ReadTools:
    root = copy_fixture(tmp_path / "mock")
    staged = stage_release(
        tmp_path / "staged", created_at=NOW, scopes=SCOPES, extra_pages=[HUB_PAGE, HUBS_INDEX]
    )
    publish_release(FolderStorage(root, fsync=False), staged)
    return ReadTools(FolderReleaseSource(root), McpConfig())


def test_search_within_one_scope(scoped: ReadTools, as_json: Json) -> None:
    everything = as_json(scoped.search("menuiseries livraison chantier", limit=50))
    assert "within" not in everything
    assert {MINUTES, TOPIC_ID} <= {hit["page_id"] for hit in everything["hits"]}
    by_page = {hit["page_id"]: hit for hit in everything["hits"]}
    assert by_page[PLAN_B]["scope"] == "moreau" and by_page[MINUTES]["scope"] == "entreprise"
    assert "scope" not in by_page[TOPIC_ID], "company pages carry no scope"

    moreau = as_json(scoped.search("menuiseries livraison chantier", limit=50, within="moreau"))
    assert moreau["within"] == "moreau"
    assert moreau["hits"]
    assert {hit["page_id"] for hit in moreau["hits"]} <= {PLAN_A, PLAN_B, HUB}
    assert all(hit["scope"] == "moreau" for hit in moreau["hits"])
    assert any(hit["kind"] == "source-block" for hit in moreau["hits"]), "blocks inherit scope"
    assert any(hit["page_id"] == HUB for hit in moreau["hits"])

    company = as_json(scoped.search("menuiseries livraison", limit=50, within="entreprise"))
    assert company["hits"] and {hit["page_id"] for hit in company["hits"]} == {MINUTES}


def test_get_index_within_filters_the_entries(scoped: ReadTools, as_json: Json) -> None:
    sources = as_json(scoped.get_index("sources", within="moreau"))
    assert sources["within"] == "moreau"
    assert (sources["entries_kept"], sources["entries_removed"]) == (2, 1)
    assert "indice B" in sources["markdown"] and "indice A" in sources["markdown"]
    assert "minutes" not in sources["markdown"]
    assert "## Site records" not in sources["markdown"], "emptied sections are dropped"
    assert "## Schedule and purchase tracking" in sources["markdown"]

    unfiltered = as_json(scoped.get_index("sources"))
    assert "within" not in unfiltered and "## Site records" in unfiltered["markdown"]

    # a company topic is listed under every scope of its sources
    assert (
        "Schedule and window delivery"
        in as_json(scoped.get_index("topics", within="entreprise"))["markdown"]
    )
    home = as_json(scoped.get_index("home", within="entreprise"))
    assert "[topics](topics/index.md)" in home["markdown"], "links to indexes are kept"
    assert "indice B" not in home["markdown"]


def test_get_index_hubs(scoped: ReadTools, as_json: Json) -> None:
    hubs = as_json(scoped.get_index("hubs/chantiers"))
    assert hubs["page_id"] == "index:hubs/chantiers" and hubs["path"] == "chantiers/index.md"
    assert "hubs/chantiers" in hubs["scopes"]
    assert as_json(scoped.get_index("hubs"))["page_id"] == "index:hubs/chantiers"
    assert "Chantier Moreau" in as_json(scoped.get_index("hubs", within="moreau"))["markdown"]
    assert as_json(scoped.get_index("hubs", within="entreprise"))["entries_kept"] == 0
    hub = as_json(scoped.read_page(HUB))
    assert hub["type"] == "hub" and hub["frontmatter"]["scope"] == "moreau"
    assert {hit["page_id"] for hit in as_json(scoped.search("hub", types=["hub"]))["hits"]} == {HUB}


@pytest.mark.parametrize("value", ["Moreau", "moreau!", "chantier moreau", "-moreau", "a" * 65])
def test_invalid_within(scoped: ReadTools, value: str) -> None:
    with pytest.raises(ToolInputError, match="kebab-case") as search:
        scoped.search("menuiseries", within=value)
    assert search.value.code == "invalid_argument"
    with pytest.raises(ToolInputError, match="kebab-case") as index:
        scoped.get_index("sources", within=value)
    assert index.value.code == "invalid_argument"


def test_unknown_within_lists_the_scopes(scoped: ReadTools) -> None:
    with pytest.raises(ToolInputError, match="unknown scope") as raised:
        scoped.search("menuiseries", within="valbrise")
    assert raised.value.code == "not_found"
    assert raised.value.details["scopes"] == ["entreprise", "moreau"]


def test_a_release_without_scopes(reads: ReadTools, as_json: Json) -> None:
    """The committed mock release: no scopes, a schema 1 search database, results as before."""
    snap = reads.snapshot()
    assert snap.search.has_scopes is False and snap.search.meta["schema"] == "1"
    data = as_json(reads.search("menuiseries", limit=50))
    assert data["hits"] and all("scope" not in hit for hit in data["hits"])
    assert "within" not in data
    assert as_json(reads.search("menuiseries", limit=50, within=None)) == data
    assert as_json(reads.search("menuiseries", within=" ")) == as_json(reads.search("menuiseries"))
    with pytest.raises(ToolInputError, match="no scopes") as raised:
        reads.search("menuiseries", within="entreprise")
    assert raised.value.code == "not_found"
    with pytest.raises(ToolInputError, match="no scopes"):
        reads.get_index("sources", within="moreau")


async def test_within_through_the_server(scoped: ReadTools) -> None:
    server = build_server(scoped.source, config=McpConfig())
    async with Client(server) as client:
        result = tool_payload(
            await client.call_tool("search", {"query": "menuiseries", "within": "moreau"})
        )
        assert result["ok"] is True and result["within"] == "moreau"
        index = tool_payload(
            await client.call_tool("get_index", {"scope": "sources", "within": "moreau"})
        )
        assert index["ok"] is True and index["entries_removed"] == 1
        bad = tool_payload(
            await client.call_tool("search", {"query": "menuiseries", "within": "Not Kebab"})
        )
        assert bad["ok"] is False and bad["error"]["code"] == "invalid_argument"
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        for name in ("search", "get_index"):
            schema = json.dumps(tools[name].input_schema)
            assert "within" in schema and "hubs/<folder>" in schema
