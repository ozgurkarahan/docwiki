from __future__ import annotations

from pathlib import Path

from docwiki.contracts.enums import STAGE_NAMES
from docwiki.contracts.frontmatter import read_frontmatter
from docwiki.site.process_page import (
    DOCUMENTS_SLUG,
    PROCESS_SLUG,
    STAGES,
    process_markdown,
    write_documents_page,
    write_process_page,
)


def test_the_steps_are_the_pipeline_stages_in_order() -> None:
    assert tuple(stage for stage, _text in STAGES) == STAGE_NAMES
    assert all(text for _stage, text in STAGES)
    # The 14 steps are in a disclosure of the Process component, not in the page text.
    assert process_markdown().rstrip().endswith("## Live")


def test_the_tab_pages_have_their_slugs() -> None:
    assert (PROCESS_SLUG, DOCUMENTS_SLUG) == ("pipeline", "documents")


def test_written_once_and_never_over_a_page_of_the_release(tmp_path: Path) -> None:
    for write, slug, title in (
        (write_process_page, PROCESS_SLUG, "Pipeline"),
        (write_documents_page, DOCUMENTS_SLUG, "Documents"),
    ):
        assert write(tmp_path) is True
        page = tmp_path / f"{slug}.md"
        meta, _body = read_frontmatter(page.read_text(encoding="utf-8"))
        assert meta["title"] == title
        page.write_text("---\ntitle: Own page\n---\n", encoding="utf-8")
        assert write(tmp_path) is False
        assert "Own page" in page.read_text(encoding="utf-8")
