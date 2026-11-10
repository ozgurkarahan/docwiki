"""A3 `wiki-long-context`: context packing, citation mapping, registration and CLI wiring."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from evals.registry import get_system, system_names
from evals.runner import _parser
from evals.systems import SystemNotConfigured
from evals.systems_wiki_lc import WIKI_LONG_CONTEXT_SCHEMA, WikiLongContextSystem
from evals_testkit import question

from docwiki.llm import FakeLlmClient, LlmRequest


def run(coro: Any) -> Any:
    return asyncio.run(coro)


def mock_release(repo_root: Path) -> Path:
    releases = repo_root / "samples" / "fixtures" / "mock-release" / "releases"
    release_id = json.loads((releases / "current.json").read_text(encoding="utf-8"))["release_id"]
    return releases / release_id


def test_wiki_long_context_orders_pages_and_keeps_source_frontmatter(repo_root: Path) -> None:
    captured: list[str] = []

    def handler(request: LlmRequest) -> dict[str, Any]:
        captured.append(request.text)
        return {"answer": "Not found in the wiki.", "citations": []}

    llm = FakeLlmClient({WIKI_LONG_CONTEXT_SCHEMA: handler})
    system = WikiLongContextSystem(release_dir=mock_release(repo_root), llm=llm)
    run(system.setup())
    result = run(system.answer(question()))

    text = captured[0]
    home = text.index('path="wiki/index.md"')
    topic = text.index('path="wiki/topics/planning.md"')
    source = text.index('path="wiki/sources/pln-2026-003-indice-b-planning-et-suivi-des-achats.md"')
    assert home < topic < source
    assert "source_frontmatter:" in text and "supersedes:" in text
    assert result.abstained and result.citations == []
    assert system.config()["context"]["included_pages"] > 0


def test_wiki_long_context_records_budget_truncation_on_mock_release(repo_root: Path) -> None:
    llm = FakeLlmClient(
        {WIKI_LONG_CONTEXT_SCHEMA: {"answer": "Not found in the wiki.", "citations": []}}
    )
    system = WikiLongContextSystem(
        release_dir=mock_release(repo_root),
        budget_tokens=800,
        max_output_tokens=120,
        llm=llm,
    )
    system.question_margin_tokens = 100
    run(system.setup())

    context = system.config()["context"]
    groups = context["groups"]
    assert context["included_pages"] > 0
    assert context["excluded_pages"] > 0
    assert "wiki/topics/planning.md" in set(context["truncated_pages"])
    assert groups["topics"]["included_pages"] >= 1
    assert groups["sources"]["excluded_pages"] >= 1


def test_wiki_long_context_maps_footnotes_and_keeps_unknown(repo_root: Path) -> None:
    llm = FakeLlmClient(
        {
            WIKI_LONG_CONTEXT_SCHEMA: {
                "answer": "The delivery date moved to 2026-04-20.",
                "citations": [
                    {"page_path": "wiki/topics/planning.md", "footnote": "c1"},
                    {"page_path": "wiki/topics/planning.md", "footnote": "c999"},
                    {"page_path": "wiki/missing.md", "footnote": "c1"},
                ],
            }
        }
    )
    system = WikiLongContextSystem(release_dir=mock_release(repo_root), llm=llm)
    run(system.setup())
    result = run(system.answer(question(question="When were the windows postponed to?")))

    assert result.citations[0].source_id == "src-59cf9366e50c"
    assert result.citations[0].locator_key == "sheet-planning-r0006-r0009"
    assert result.citations[0].title == "Planning and purchase tracking, indice B"
    assert result.citations[1].label == "unknown footnote wiki/topics/planning.md#c999"
    assert result.citations[2].label == "unknown citation wiki/missing.md#c1"
    assert "Sources:\n[1] Planning and purchase tracking, indice B" in result.text
    assert "evidence/src-59cf9366e50c/sheet-planning-r0006-r0009.md" in result.text


def test_wiki_long_context_is_registered_and_cli_accepts_it() -> None:
    assert "wiki-long-context" in system_names()
    spec = get_system("wiki-long-context")
    assert spec.indexes_documents is False
    args = _parser().parse_args(
        [
            "--system",
            "wiki-long-context",
            "--questions",
            "evals/golden/dev.jsonl",
            "--catalog",
            "samples/fixtures/mock-release/releases/20260401T090000Z-8a41b109",
        ]
    )
    assert args.system == "wiki-long-context"


def test_wiki_long_context_requires_a_release_folder_with_wiki(repo_root: Path) -> None:
    factory = get_system("wiki-long-context").factory
    with pytest.raises(SystemNotConfigured, match="release folder containing wiki"):
        factory(SimpleNamespace(catalog=repo_root, budget_tokens=120_000), None)
