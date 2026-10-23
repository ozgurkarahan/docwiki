"""Filed research answers: contract query pages built from a Researcher answer (ADR 0007)."""

from __future__ import annotations

import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from docwiki.answers import (
    APPROVED_BY,
    FilingError,
    FolderRelease,
    StorageRelease,
    build_query_page,
)
from docwiki.answers.filing import query_slug
from docwiki.contracts.locators import locator_label
from docwiki.contracts.markdown import extract_footnotes
from docwiki.contracts.pages import EvidenceFrontmatter, EvidencePage, QueryFrontmatter
from docwiki.contracts.storage import FolderStorage
from docwiki.release.validate import CITATION_RE

MOCK = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"
MOCK_ID = "20260401T090000Z-8a41b109"
MOCK_DIR = MOCK / "releases" / MOCK_ID
MINUTES = "evidence/src-f0757603684a/para-0011.md"
PLAN = "evidence/src-59cf9366e50c/sheet-planning-r0006-r0009.md"
DAY = date(2026, 10, 20)


def answer(text: str, *, calls: tuple[Any, ...] = (), sources: Any = None) -> SimpleNamespace:
    return SimpleNamespace(
        text=text,
        sources=sources,
        tool_calls=list(calls),
        agent="docwiki-researcher",
        version="7",
        latency_s=21.4,
    )


def call(name: str, arguments: Any, status: str = "completed") -> SimpleNamespace:
    return SimpleNamespace(name=name, arguments=arguments, status=status)


CITED = (
    "The windows of the extension are delivered on 2026-04-20 [1]. Their installation is "
    "planned from 2026-04-21 to 2026-04-23 [2].\n\n"
    "Sources:\n"
    f"[1] Site meeting minutes n°3 — ¶ 11 (native-text) — {MINUTES}\n"
    f"[2] Planning and purchase tracking, indice B — rows 6–9 (deterministic-table) — {PLAN}\n"
)


@pytest.fixture(scope="module")
def release() -> FolderRelease:
    return FolderRelease(MOCK_DIR)


def sidecar(path: str) -> EvidenceFrontmatter:
    page = EvidencePage.parse((MOCK_DIR / path).read_text(encoding="utf-8"), path)
    assert isinstance(page.frontmatter, EvidenceFrontmatter)
    return page.frontmatter


def test_a_cited_answer_becomes_a_contract_query_page(release: FolderRelease) -> None:
    filed = build_query_page(
        answer(
            CITED,
            calls=(
                call("search", {"query": "window delivery `date`"}),
                call("get_evidence", f'{{"path": "{MINUTES}"}}'),
                call("query_table", {"source_id": "src-59cf9366e50c", "sql": "SELECT 1"}, "failed"),
            ),
        ),
        question="  When are the windows of the extension delivered? ",
        release=release,
        filed_on=DAY,
    )
    page = filed.page
    fm = page.frontmatter
    assert isinstance(fm, QueryFrontmatter)
    assert page.path == "queries/2026-10-20-when-are-the-windows-of-the-extension-delivered.md"
    assert fm.id == "query:2026-10-20-when-are-the-windows-of-the-extension-delivered"
    assert fm.question == fm.title == "When are the windows of the extension delivered?"
    assert fm.asked_by == "human" and fm.approved_by == APPROVED_BY == "owner"
    assert fm.sources == ["src-59cf9366e50c", "src-f0757603684a"]
    assert fm.sensitivity == "public" and fm.updated == DAY and fm.lang == "en"
    assert fm.docwiki.release == MOCK_ID
    assert fm.summary == "The windows of the extension are delivered on 2026-04-20."
    assert (
        "on 2026-04-20[^c1]. Their installation" in page.body
    )  # markers renumbered, no space before
    refs, definitions = extract_footnotes(page.body)
    assert [label for label, _ in refs] == ["c1", "c2"]
    expected = {"c1": (MINUTES, "paraphrase"), "c2": (PLAN, "table")}
    for definition in definitions:
        match = CITATION_RE.match(definition.content)
        assert match, definition.content
        path, badge = expected[definition.label]
        assert match["href"] == f"../{path}"
        assert match["badge"] == badge
        assert match["label"] == locator_label(sidecar(path).locator)
    assert (
        match["title"] == "Planning and purchase tracking, indice B"
    )  # the catalog title, not the model's
    assert "## How this answer was produced" in page.body
    assert "`docwiki-researcher` version 7" in page.body and f"`{MOCK_ID}`" in page.body
    assert "reviewed and filed by the owner on 2026-10-20" in page.body
    assert "- search `window delivery 'date'`" in page.body
    assert f"- get_evidence `{MINUTES}`" in page.body
    assert "- query_table `src-59cf9366e50c SELECT 1` (failed)" in page.body
    assert "3 tool calls in 21 s" in page.body
    assert filed.numbers_checked == 2 and filed.warnings == () and not filed.not_found


def test_the_same_sidecar_cited_twice_shares_one_footnote(release: FolderRelease) -> None:
    text = (
        "The windows arrive on 2026-04-20 [1]. That is the postponed date [3].\n\nSources:\n"
        f"[1] Minutes — ¶ 11 — {MINUTES}\n[2] Planning — rows 6–9 — {PLAN}\n"
        f"[3] Minutes again — ¶ 11 — {MINUTES}\n"
    )
    filed = build_query_page(
        answer(text), question="Window delivery?", release=release, filed_on=DAY
    )
    refs, definitions = extract_footnotes(filed.page.body)
    assert [label for label, _ in refs] == ["c1", "c1"] and len(definitions) == 1
    assert filed.page.frontmatter.sources == ["src-f0757603684a"]
    assert filed.warnings == ("sources listed but never cited in the text were left out: [2]",)


def test_an_honest_abstention_files_without_sources(release: FolderRelease) -> None:
    filed = build_query_page(
        answer("Not found in the wiki. I searched the contract and the schedule."),
        question="Who is the architect?",
        release=release,
        filed_on=DAY,
    )
    fm = filed.page.frontmatter
    assert isinstance(fm, QueryFrontmatter)
    assert filed.not_found and fm.sources == [] and fm.sensitivity == "public"
    assert "No source of that release answers the question." in filed.page.body
    assert "## Sources" not in filed.page.body


def test_numbers_missing_from_the_cited_evidence_are_reported(release: FolderRelease) -> None:
    text = (
        f"The windows are delivered in week 99 [1].\n\nSources:\n[1] Minutes — ¶ 11 — {MINUTES}\n"
    )
    filed = build_query_page(answer(text), question="Delivery?", release=release, filed_on=DAY)
    assert len(filed.warnings) == 1 and "evidence: 99 (in" in filed.warnings[0]
    assert "0 of 1 cited sentences match" in filed.page.body


def test_an_abbreviation_does_not_end_the_cited_sentence(release: FolderRelease) -> None:
    """The period of "no." or "M." does not split the sentence: its numbers stay checked."""
    text = (
        "Lot 77 goes with amendment no. 1, as M. Ancelin noted [1].\n\n"
        f"Sources:\n[1] Minutes — ¶ 11 — {MINUTES}\n"
    )
    filed = build_query_page(answer(text), question="Lot?", release=release, filed_on=DAY)
    assert filed.numbers_checked == 1
    (warning,) = filed.warnings
    assert warning.startswith("numbers not found in the cited evidence: 77, 1 (in")


def test_unsafe_markdown_is_removed_and_headings_are_demoted(release: FolderRelease) -> None:
    text = (
        "## Answer\n\nThe windows arrive on 2026-04-20 [1]. <script>alert(1)</script> See "
        "[the vendor](https://vendor.example/windows).\n\n"
        f"Sources:\n[1] Minutes — ¶ 11 — {MINUTES}\n"
    )
    filed = build_query_page(answer(text), question="Delivery?", release=release, filed_on=DAY)
    body = filed.page.body
    assert "<script" not in body and "https://vendor.example" not in body
    assert "**Answer**" in body and "\n## Answer" not in body
    assert any("removed from the answer" in warning for warning in filed.warnings)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("The windows arrive on 2026-04-20.", "cites nothing"),
        (
            f"They arrive on 2026-04-20 [2].\n\nSources:\n[1] Minutes — ¶ 11 — {MINUTES}\n",
            "not in the answer",
        ),
        (
            "They arrive on 2026-04-20 [1].\n\nSources:\n[1] Minutes — ¶ 11 (native-text)\n",
            "evidence sidecar",
        ),
        (
            "They arrive on 2026-04-20 [1].\n\nSources:\n"
            "[1] Minutes — ¶ 99 — evidence/src-f0757603684a/para-0099.md\n",
            "no evidence sidecar",
        ),
    ],
)
def test_answers_that_cannot_be_filed(release: FolderRelease, text: str, message: str) -> None:
    with pytest.raises(FilingError, match=message):
        build_query_page(answer(text), question="Delivery?", release=release, filed_on=DAY)


def test_the_question_is_required(release: FolderRelease) -> None:
    with pytest.raises(FilingError, match="empty"):
        build_query_page(answer(CITED), question="   ", release=release, filed_on=DAY)


def test_long_questions_that_start_alike_get_distinct_pages(release: FolderRelease) -> None:
    quoted = "What does the kitchen renovation include, and at which VAT rate is it quoted?"
    invoiced = "What does the kitchen renovation include, and at which VAT rate is it invoiced?"

    def path_of(question: str) -> str:
        filed = build_query_page(answer(CITED), question=question, release=release, filed_on=DAY)
        return filed.page.path

    first, second = path_of(quoted), path_of(invoiced)
    assert first != second
    assert path_of(f"  {quoted} ") == first  # the same question keeps its page
    slug = first.removeprefix("queries/2026-10-20-").removesuffix(".md")
    assert len(slug) == 60 and slug[-7] == "-" and int(slug[-6:], 16) >= 0
    assert slug.startswith("what-does-the-kitchen-renovation-include-and-at-which")
    short = "When are the windows of the extension delivered?"  # not cut: no hash
    assert query_slug(short) == "when-are-the-windows-of-the-extension-delivered"
    assert query_slug("???") == "answer"


def test_storage_release_reads_the_current_release(tmp_path: Path) -> None:
    shutil.copytree(MOCK, tmp_path / "store", ignore=shutil.ignore_patterns("*.py", "__pycache__"))
    release = StorageRelease(FolderStorage(tmp_path / "store"))
    assert release.release_id == MOCK_ID
    assert release.evidence(MINUTES) is not None
    assert release.evidence("evidence/../wiki/index.md") is None
    filed = build_query_page(answer(CITED), question="Delivery?", release=release, filed_on=DAY)
    assert filed.page.frontmatter.sources == ["src-59cf9366e50c", "src-f0757603684a"]
    with pytest.raises(FilingError, match="no release"):
        StorageRelease(FolderStorage(tmp_path / "empty"))
