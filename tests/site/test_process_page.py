from __future__ import annotations

from pathlib import Path

from docwiki.contracts.enums import STAGE_NAMES
from docwiki.contracts.frontmatter import read_frontmatter
from docwiki.site.process_page import PROCESS_SLUG, STAGES, process_markdown, write_process_page


def test_the_page_lists_every_pipeline_stage_in_order() -> None:
    assert tuple(stage for stage, _text in STAGES) == STAGE_NAMES
    text = process_markdown()
    for stage in STAGE_NAMES:
        assert f"`{stage}`" in text
    assert text.rstrip().endswith("## Live")


def test_written_once_and_never_over_a_page_of_the_release(tmp_path: Path) -> None:
    assert write_process_page(tmp_path) is True
    page = tmp_path / f"{PROCESS_SLUG}.md"
    meta, _body = read_frontmatter(page.read_text(encoding="utf-8"))
    assert meta["title"] == "How it works"
    page.write_text("---\ntitle: Own page\n---\n", encoding="utf-8")
    assert write_process_page(tmp_path) is False
    assert "Own page" in page.read_text(encoding="utf-8")
