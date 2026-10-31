"""``answer_context``: one call that returns the best sections with their citations, the home
index, the hub of the chantier and the computed views (index-first Researcher, ADR 0013)."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any

import pytest
from mcp_testkit import MINUTES, PLAN_A, PLAN_B, RELEASE_ID
from test_mcp_within import HUB, scoped  # noqa: F401 - the scoped release fixture

from docwiki.mcp.config import McpConfig
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import ReadTools, ToolInputError, _dominant_scope

Json = Callable[[str], dict[str, Any]]
QUESTION = "date de livraison des fenêtres"
CITATION_FIELDS = {
    "source_title",
    "locator_label",
    "source_id",
    "locator_key",
    "evidence_path",
    "provenance",
}


def test_one_call_returns_sections_citations_and_the_home_index(
    reads: ReadTools, as_json: Json
) -> None:
    data = as_json(reads.answer_context(QUESTION))
    assert data["ok"] is True and data["release_id"] == RELEASE_ID
    assert data["question"] == QUESTION and data["offset"] == 0
    hits = data["hits"]
    assert hits and [hit["rank"] for hit in hits] == list(range(1, len(hits) + 1))
    assert len(hits) <= 5
    for hit in hits:
        assert {"page_id", "path", "title", "section", "text", "citations"} <= set(hit)
        assert "snippet" not in hit, "the section text replaces the snippet"
        for citation in hit["citations"]:
            assert set(citation) >= CITATION_FIELDS
            assert citation["evidence_path"].startswith("evidence/")
    # a source hit carries its evidence sidecar verbatim, as a ready-made citation
    minutes = next(hit for hit in hits if hit.get("locator_key") == "para-0011")
    assert minutes["origin"] == "source" and minutes["source_id"] == MINUTES
    assert "du 30/03/2026 au 20/04/2026" in minutes["text"]
    assert minutes["text"].startswith("## Text"), "the sidecar header is left out"
    assert "FICTIONAL" not in minutes["text"]
    (citation,) = minutes["citations"]
    assert citation["evidence_path"] == f"evidence/{MINUTES}/para-0011.md"
    assert citation["locator_label"] == "¶ 11" and citation["provenance"] == "native-text"
    # a wiki hit gives its own section, with the citations of its footnotes
    data = as_json(reads.answer_context("When are the windows delivered?"))
    wiki = [hit for hit in data["hits"] if hit["origin"] == "wiki" and hit["citations"]]
    assert wiki
    assert {c["source_id"] for hit in wiki for c in hit["citations"]} & {PLAN_B, MINUTES}
    assert all(hit["page_id"] not in ("log", "index:home") for hit in data["hits"])
    home = data["home_index"]
    assert home["page_id"] == "index:home" and home["markdown"].startswith("#")
    assert len(home["markdown"]) <= 1500 + 3
    assert data["views"] == [], "the mock release has no computed views"
    assert "hub" not in data, "the mock release has no scopes"
    assert "get_evidence only to quote" in data["hint"]


def test_size_is_bounded_and_pages(source: FolderReleaseSource, as_json: Json) -> None:
    small = ReadTools(source, McpConfig(max_chars=4000))
    out = small.answer_context(QUESTION, limit=10)
    assert len(out) <= 4000
    data = as_json(out)
    assert data["hits"]
    assert all(len(hit["text"]) <= 1600 + 3 for hit in data["hits"])
    if data["truncated"] or data["next_offset"] is not None:
        more = as_json(small.answer_context(QUESTION, limit=10, offset=data["next_offset"]))
        assert more["offset"] == data["next_offset"]
        assert "home_index" not in more and "views" not in more, "context only on offset 0"
        assert more["hits"][0]["rank"] == data["next_offset"] + 1
    roomy = as_json(ReadTools(source, McpConfig()).answer_context(QUESTION, limit=2))
    assert len(roomy["hits"]) == 2 and roomy["next_offset"] == 2


def test_within_keeps_one_scope_and_adds_its_hub(scoped: ReadTools, as_json: Json) -> None:  # noqa: F811
    data = as_json(scoped.answer_context("livraison des menuiseries", within="moreau"))
    assert data["within"] == "moreau"
    assert data["hits"]
    assert {hit["page_id"] for hit in data["hits"]} <= {PLAN_A, PLAN_B, HUB}
    assert all(hit["scope"] == "moreau" for hit in data["hits"])
    assert data["hub"]["page_id"] == HUB and data["hub"]["scope"] == "moreau"
    filtered = as_json(scoped.get_index("home", within="moreau"))["markdown"]
    assert filtered.startswith(data["home_index"]["markdown"].removesuffix("\n…\n").rstrip())

    company = as_json(scoped.answer_context("livraison des menuiseries", within="entreprise"))
    assert {hit["page_id"] for hit in company["hits"]} == {MINUTES}
    assert "hub" not in company, "the default scope has no hub here"


def test_restricted_content_never_appears(reads: ReadTools, as_json: Json) -> None:
    """Defence in depth: a page above the release's audience is dropped from the hits, even if
    a release ever contained one (the release gates keep it out of a public build)."""
    snap = reads.snapshot()
    assert snap.audience == "public"
    before = as_json(reads.answer_context(QUESTION))
    assert any(hit.get("source_id") == MINUTES for hit in before["hits"])
    for key in ("pages-by-id:", "pages-by-path"):
        pages = reads._by_id(snap) if key == "pages-by-id:" else reads._by_path(snap)
        for name, page in list(pages.items()):
            if page.id == MINUTES:
                pages[name] = page.model_copy(update={"sensitivity": "restricted"})
    after = as_json(reads.answer_context(QUESTION, limit=10))
    assert after["hits"]
    assert all(hit["page_id"] != MINUTES for hit in after["hits"])
    assert all(hit.get("source_id") != MINUTES for hit in after["hits"])
    assert "VanArsdel Menuiseries a annoncé" not in json.dumps(after, ensure_ascii=False)


@pytest.mark.parametrize("question", ["", "   ", "\n"])
def test_empty_question_is_an_invalid_argument(reads: ReadTools, question: str) -> None:
    with pytest.raises(ToolInputError, match="question must not be empty") as error:
        reads.answer_context(question)
    assert error.value.code == "invalid_argument"


def test_unknown_scope_and_language_errors(reads: ReadTools) -> None:
    with pytest.raises(ToolInputError) as scope:
        reads.answer_context(QUESTION, within="nowhere")
    assert scope.value.code == "not_found"
    with pytest.raises(ToolInputError) as lang:
        reads.answer_context(QUESTION, lang="xx")
    assert lang.value.code == "invalid_argument"


def test_dominant_scope_names_the_hub_to_add() -> None:
    assert _dominant_scope([{"scope": "a"}, {"scope": "a"}, {}, {"scope": "b"}]) == "a"
    assert _dominant_scope([{"scope": "a"}, {"scope": "b"}]) is None, "no majority"
    assert _dominant_scope([{"scope": "a"}, {}, {}, {}, {}]) is None, "one hit is not enough"
    assert _dominant_scope([{}, {}]) is None


def test_no_hits_suggests_abstaining(reads: ReadTools, as_json: Json) -> None:
    data = as_json(reads.answer_context("zzqx unrelated vocabulary"))
    assert data["hits"] == [] and data["next_offset"] is None
    assert "Not found in the wiki." in data["hint"]
