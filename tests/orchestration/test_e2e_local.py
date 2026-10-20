"""End-to-end local runs on a tiny synthetic corpus with the stub engine and a fake LLM."""

from __future__ import annotations

from pathlib import Path

import pytest
from engine_stubs import CANARY

from docwiki.contracts.layout import SKILL_PROJECTIONS
from docwiki.release.reader import ReleaseReader
from docwiki.release.validate import validate_release


def _problems(root: Path) -> list[str]:
    return [
        f"{v.gate} {v.severity} {v.code} {v.path}:{v.line} {v.message}"
        for v in validate_release(root, canaries=[CANARY], glossary_seeded=True)
    ]


@pytest.mark.parametrize("orchestrator", ["async", "af"])
async def test_end_to_end_release_validates_with_zero_violations(make_harness, orchestrator):
    harness = make_harness(orchestrator=orchestrator)
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    assert outcome.published
    root = harness.current_release()
    assert _problems(root) == []

    reader = ReleaseReader.open(harness.settings.work_dir)
    assert reader.release_id == outcome.release_id
    sources = {page.title: page for page in reader.list_pages("source")}
    assert set(sources) == {
        "DEV-2026-014 indice A",
        "DEV-2026-014 indice B",
        "Purchase plan",
        "Supplier note",
    }
    rev_a = reader.read_page(sources["DEV-2026-014 indice A"].id)
    assert rev_a.frontmatter.status == "superseded"
    assert "**Superseded** by" in rev_a.body
    assert "## Related" in rev_a.body
    assert "docwiki:backlinks:start" in rev_a.body
    assert rev_a.frontmatter.topics == ["topic:schedule-and-window-delivery"]
    assert {page.id for page in reader.list_pages("entity")} == {
        "building-element:baie-f1",
        "building-element:fenetre-f2",
        "organisation:vanarsdel-menuiseries",
    }
    assert [page.id for page in reader.list_pages("topic")] == [
        "topic:schedule-and-window-delivery"
    ]
    assert reader.tables(sources["Purchase plan"].id).tables[0].row_count == 2
    assert {skill.name for skill in reader.list_skills()} == {
        "cite-sources",
        "deep-research",
        "prepare-site-meeting",
        "wiki-maintainer",
        "wiki-navigator",
    }
    hits = reader.open_search().search("sliding window")
    assert any(hit.kind == "source-block" and hit.source_id for hit in hits)
    assert any(hit.page_id == "glossary" for hit in hits)
    # the restricted price study never reaches an internal build
    assert all("study" not in page.path for page in reader.catalog.pages)
    report = outcome.report
    assert report.status == "succeeded"
    assert report.counts.sources_total == 5
    assert {stage.stage for stage in report.stages} >= {
        "discover",
        "extract",
        "classify",
        "compile",
        "entities",
        "topics",
        "links",
        "indexes",
        "agentkit",
        "evidence",
        "verify",
        "publish",
    }
    assert report.cost.llm and sum(item.calls for item in report.cost.llm) > 0
    gates = {gate.gate: gate.status for gate in outcome.gates}
    assert all(status in ("pass", "skipped") for status in gates.values()), gates
    assert gates["G08"] == "pass"


async def test_skill_projections_are_identical(harness):
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    wiki = harness.current_release() / "wiki"
    contents = [
        {
            path.relative_to(wiki / projection).as_posix(): path.read_bytes()
            for path in (wiki / projection).rglob("*")
            if path.is_file()
        }
        for projection in SKILL_PROJECTIONS
    ]
    assert contents[0] == contents[1] == contents[2]
    assert len(contents[0]) == 5


async def test_injection_canary_never_reaches_the_agent_kit_or_indexes(harness):
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    wiki = harness.current_release() / "wiki"
    checked = [
        wiki / "AGENTS.md",
        wiki / "index.md",
        wiki / "llms.txt",
        wiki / "log.md",
        wiki / "glossary.md",
        wiki / "sources" / "index.md",
        wiki / "entities" / "index.md",
        wiki / "topics" / "index.md",
        wiki / "catalog.json",
        *wiki.glob(".*/skills/*/SKILL.md"),
    ]
    for path in checked:
        assert CANARY not in path.read_text(encoding="utf-8"), path
    quality = (wiki / "_meta" / "quality.md").read_text(encoding="utf-8")
    assert "## Injection flags" in quality
    assert CANARY not in quality
    proposals = harness.storage.list("work/proposals/")
    assert proposals, "the flagged block must be filed as an injection proposal"


async def test_injection_source_is_contained_in_a_public_build(make_harness):
    from docwiki.contracts.ids import source_id_for

    harness = make_harness(audience="public")
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    assert _problems(root) == []
    note = source_id_for("notes/supplier-note.txt")
    quote = source_id_for("devis/DEV-2026-014 indice A.txt")
    # originals are published for the fictional public sample, never for a flagged source
    assert (root / "evidence" / quote / "original.txt").is_file()
    assert not list((root / "evidence" / note).glob("original.*"))
    # the canary is nowhere in the release, whatever the file type (search.db included)
    needle = CANARY.encode("utf-8")
    leaks = [
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and needle in path.read_bytes()
    ]
    assert leaks == []
    quality = (root / "wiki" / "_meta" / "quality.md").read_text(encoding="utf-8")
    flags = quality.split("## Injection flags", 1)[1].split("\n## ", 1)[0]
    entries = [line for line in flags.split("\n") if line.startswith("- ")]
    assert entries and all(line.startswith(f"- source `{note}`, block `b") for line in entries)
    assert "Ignore previous instructions" not in quality
    assert "## Citations" in quality
