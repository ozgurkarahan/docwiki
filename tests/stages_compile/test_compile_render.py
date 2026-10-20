"""Source page rendering: frontmatter, body structure, footnotes, tables and safety."""

from __future__ import annotations

import logging
import re

import pytest
from compile_testkit import (
    QUOTE_A,
    QUOTE_B,
    STAMP,
    compile_handler,
    compiled,
    fact,
    make_state,
    no_repair,
    plan_doc,
    quote_a_doc,
    quote_b_doc,
    section,
)

from docwiki.contracts import Page, find_violations, parse_frontmatter
from docwiki.contracts.compiled import CompiledSection
from docwiki.contracts.enums import badge_for
from docwiki.contracts.locators import locator_key, locator_label
from docwiki.contracts.markdown import (
    BACKLINKS_START,
    extract_footnotes,
    extract_headings,
    relative_link,
)
from docwiki.contracts.pages import SourceFrontmatter
from docwiki.domain import DomainPack
from docwiki.engine_types import CitedLocator, CompiledResult
from docwiki.llm import FakeLlmClient
from docwiki.release.validate import CITATION_RE
from docwiki.stages.classify import classify_source
from docwiki.stages.compile import compile_source
from docwiki.stages.render import link_source_refs, render_source_page

HONEST = {
    "native-text": {"✓ quote verified", "paraphrase", "generated description"},
    "deterministic-table": {"table"},
    "ocr": {"OCR", "generated description"},
    "model-description": {"generated description"},
}


async def compile_and_render(
    doc, pack: DomainPack, llm: FakeLlmClient, slug: str, **kwargs
) -> tuple[Page, list[CitedLocator], CompiledResult]:
    classification = await classify_source(doc, pack, llm)
    result = await compile_source(doc, classification, pack, llm)
    page, cited = render_source_page(
        result, doc, classification, make_state(doc), slug=slug, stamp=STAMP, pack=pack, **kwargs
    )
    return page, cited, result


def client() -> FakeLlmClient:
    return FakeLlmClient({"compile": compile_handler(), "compile_repair": no_repair})


def check_footnotes(page: Page, cited: list[CitedLocator], title: str) -> list[str]:
    refs, defs = extract_footnotes(page.body)
    order: list[str] = []
    for label, _ in refs:
        if label not in order:
            order.append(label)
    assert order == [f"c{n}" for n in range(1, len(order) + 1)]
    assert [d.label for d in defs] == order
    keys = {(c.source_id, locator_key(c.locator)): c for c in cited}
    badges = []
    for definition in defs:
        match = CITATION_RE.match(definition.content)
        assert match, definition.content
        assert match.group("title") == title
        href = match.group("href")
        source_id, key = href.split("/")[-2], href.split("/")[-1].removesuffix(".md")
        assert href == relative_link(page.path, f"evidence/{source_id}/{key}.md")
        locator = keys[(source_id, key)].locator
        assert match.group("label") == locator_label(locator)
        provenances = {
            c.provenance for c in cited if (c.source_id, locator_key(c.locator)) == (source_id, key)
        }
        assert any(match.group("badge") in HONEST[p] for p in provenances)
        badges.append(match.group("badge"))
    return badges


async def test_source_page(pack: DomainPack) -> None:
    page, cited, result = await compile_and_render(
        quote_b_doc(), pack, client(), "dev-2026-014-indice-b", supersedes=[QUOTE_A]
    )
    assert page.path == "sources/dev-2026-014-indice-b.md"
    reparsed = Page.parse(page.render(), page.path)
    assert reparsed == page
    fm = page.frontmatter
    assert isinstance(fm, SourceFrontmatter)
    assert parse_frontmatter(fm.model_dump(mode="python", by_alias=True)) == fm
    assert (fm.id, fm.title, fm.status, fm.supersedes, fm.superseded_by) == (
        QUOTE_B,
        "Quote DEV-2026-014 indice B",
        "current",
        [QUOTE_A],
        [],
    )
    assert (fm.doc_type, fm.category, fm.doc_number, fm.revision, fm.authority) == (
        "quote",
        "contract-documents",
        "DEV-2026-014",
        "B",
        8,
    )
    assert fm.entities == sorted(m.entity_id for m in result.compiled.entity_mentions)
    assert (fm.topics, fm.tags, fm.pages, str(fm.updated)) == (
        [],
        ["contract-documents", "quote"],
        2,
        "2026-04-01",
    )
    assert fm.extraction.provenance_mix == {"native-text": 6}
    assert find_violations(page.body) == []
    headings = [(h.level, h.text) for h in extract_headings(page.body)]
    assert headings == [
        (1, "Quote DEV-2026-014 indice B"),
        (2, "Key facts"),
        (2, "Contents"),
        (3, "Winter conditions"),
        (3, "Installation"),
        (2, "Figures"),
        (2, "Sources"),
    ]
    assert page.body.splitlines()[2] == "> FICTIONAL - NOT FOR OPERATIONAL USE"
    assert BACKLINKS_START not in page.body and "## Related" not in page.body
    facts = page.body.split("## Key facts\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert len(facts) == 4 and all(line.startswith("- ") and "[^c" in line for line in facts)
    badges = check_footnotes(page, cited, fm.title)
    assert set(badges) == {"✓ quote verified", "paraphrase", "generated description"}
    assert "Ignore previous" not in page.body and "system prompt" not in page.body
    figure = next(line for line in page.body.splitlines() if line.startswith("- **Figure f01**"))
    assert "Generated description: Elevation of the sliding bay window" in figure


async def test_tables_are_rendered_from_extracted_data(pack: DomainPack) -> None:
    page, _, _ = await compile_and_render(quote_b_doc(), pack, client(), "quote-b")
    assert "| Row | Repère | Poste | Montant HT |\n| --- | --- | --- | --- |\n" in page.body
    assert "| 2 | Baie F1 | 5.1 | 4140,00 € |" in page.body
    assert "| 3 | Fenêtre F2 | 5.2 | 1020,00 € |" in page.body
    assert "Agents can query this table as `t01` with the `query_table` tool." in page.body


async def test_table_source_badges_and_unreferenced_tables(pack: DomainPack) -> None:
    doc = plan_doc()

    def output() -> dict:
        return compiled(
            "Schedule and purchase tracking",
            "Orders of the windows.",
            [fact("The window F2 is delivered on 2026-03-30.", "t01:r0004", "F2 | 2026-03-30")],
            [section("Orders", "The sheet lists the orders.[[cite:t01:r0004]]")],
        )

    llm = FakeLlmClient({"compile": compile_handler({doc.source_id: output})})
    page, cited, _ = await compile_and_render(doc, pack, llm, "planning-et-suivi-des-achats")
    badges = check_footnotes(page, cited, "Schedule and purchase tracking")
    assert badges == ["table"]
    assert '[Schedule and purchase tracking — sheet "Achats", row 4]' in page.body
    assert "### Tables" in page.body, "tables no section references are still rendered"
    assert "| 4 | BC-2026-009 | Fenêtre F2 PVC | F2 | 2026-03-30 | 1 |" in page.body
    assert find_violations(page.body) == []


async def test_superseded_banner_and_links(pack: DomainPack) -> None:
    llm = client()
    old_page, _, _ = await compile_and_render(
        quote_a_doc(), pack, llm, "dev-2026-014-indice-a", superseded_by=[QUOTE_B]
    )
    fm = old_page.frontmatter
    assert isinstance(fm, SourceFrontmatter)
    assert (fm.status, fm.superseded_by) == ("superseded", [QUOTE_B])
    banner = f"> **Superseded** by `{QUOTE_B}`. Use the current revision."
    assert banner in old_page.body
    assert old_page.body.index(banner) < old_page.body.index("## Key facts")
    new_page, _, _ = await compile_and_render(
        quote_b_doc(), pack, llm, "dev-2026-014-indice-b", supersedes=[QUOTE_A]
    )
    linked = link_source_refs(old_page, {QUOTE_B: new_page, QUOTE_A: old_page})
    assert (
        "> **Superseded** by [Quote DEV-2026-014 indice B](dev-2026-014-indice-b.md). "
        "Use the current revision." in linked.body
    )
    assert link_source_refs(new_page, {}) is new_page


async def test_unsafe_model_markdown_is_neutralised(pack: DomainPack) -> None:
    doc = quote_b_doc()

    def output() -> dict:
        return compiled(
            "Quote <b>DEV-2026-014</b> [indice](http://example.com) B",
            "Summary with <script>alert(1)</script> markup and a [link](../../x.md).",
            [
                fact(
                    "The bay window F1 is installed first [^9].",
                    "b0003",
                    "La baie F1 est posée en premier",
                )
            ],
            [
                section(
                    "Sources",
                    "# Heading\nThe bay window F1 is installed first.[[cite:b0003]] "
                    "<img src=x onerror=alert(1)>\n"
                    "See [docs](javascript:alert(1)) and http://example.com/x. "
                    "Write `x [[cite:b0004]]` verbatim.\n"
                    "[^1]: fake footnote\n| a | b |\n| --- | --- |\n```\nunclosed [[cite:b0003]]",
                ),
                section("Key facts", "Masonry is suspended in frost.[[cite:b0003]]"),
            ],
        )

    llm = FakeLlmClient({"compile": compile_handler({doc.source_id: output})})
    page, cited, _ = await compile_and_render(doc, pack, llm, "quote-b")
    assert find_violations(page.body) == []
    assert page.frontmatter.title == "Quote DEV-2026-014 indice B"
    headings = [h.text for h in extract_headings(page.body)]
    assert headings.count("Sources") == 1
    assert "Sources (document section)" in headings
    assert "Key facts (document section)" in headings
    assert "#### Heading" in page.body
    assert "fake footnote" not in page.body and "| a | b |" not in page.body
    assert page.body.count("```") % 2 == 0
    assert "```\nunclosed" in page.body and "Write `x ` verbatim." in page.body
    assert "[[cite" not in page.body
    check_footnotes(page, cited, page.frontmatter.title)


async def test_render_rejects_mismatched_inputs(pack: DomainPack) -> None:
    llm = client()
    doc = quote_b_doc()
    classification = await classify_source(doc, pack, llm)
    result = await compile_source(doc, classification, pack, llm)
    with pytest.raises(ValueError):
        render_source_page(
            result, quote_a_doc(), classification, make_state(doc), slug="x", stamp=STAMP, pack=pack
        )
    broken = CompiledResult(QUOTE_B, result.compiled, result.citations[1:], [], {})
    with pytest.raises(ValueError):
        render_source_page(
            broken, doc, classification, make_state(doc), slug="x", stamp=STAMP, pack=pack
        )
    assert badge_for("native-text", "unverified-paraphrase") == "paraphrase"


async def test_fence_length_mismatch_renders_the_verified_marker(pack: DomainPack) -> None:
    doc = quote_b_doc()
    body = "````\n```\n````\nThe slab is cleaned before the pose [[cite:b4]]."

    def output() -> dict:
        return compiled(
            "Quote DEV-2026-014 indice B", "Slab cleaning.", [], [section("Installation", body)]
        )

    llm = FakeLlmClient({"compile": compile_handler({doc.source_id: output})})
    page, cited, result = await compile_and_render(doc, pack, llm, "quote-b")
    assert result.compiled.sections[0].body == (
        "````\n```\n````\nThe slab is cleaned before the pose [[cite:b0004]]."
    )
    [marker] = [c for c in result.citations if c.ref == "s1"]
    assert marker.block_ids == ("b0004",)
    assert "````\n```\n````\nThe slab is cleaned before the pose[^c1]." in page.body
    assert "[[cite" not in page.body
    check_footnotes(page, cited, page.frontmatter.title)


async def test_unverified_markers_are_dropped_with_a_warning(
    pack: DomainPack, caplog: pytest.LogCaptureFixture
) -> None:
    llm = client()
    doc = quote_b_doc()
    classification = await classify_source(doc, pack, llm)
    result = await compile_source(doc, classification, pack, llm)
    sections = list(result.compiled.sections)
    assert sections[1].body == "The bay window F1 is widened to 3,00 m.[[cite:b0004]]"
    sections[1] = sections[1].model_copy(
        update={"body": sections[1].body + " The slab is cleaned before the pose.[[cite:b0004]]"}
    )
    sections.append(
        CompiledSection(
            heading="Extra",
            body="Masonry is suspended in frost.[[cite:b0003]] Invented step.[[cite:b0099]]",
            table_refs=[],
        )
    )
    stale = CompiledResult(
        QUOTE_B,
        result.compiled.model_copy(update={"sections": sections}),
        result.citations,
        result.proposals,
        result.usage,
    )
    with caplog.at_level(logging.WARNING, logger="docwiki.stages.render"):
        page, cited = render_source_page(
            stale, doc, classification, make_state(doc), slug="quote-b", stamp=STAMP, pack=pack
        )
    installation = page.body.split("### Installation\n\n", 1)[1].split("\n", 1)[0]
    assert re.fullmatch(
        r"The bay window F1 is widened to 3,00 m\.\[\^c\d+\] "
        r"The slab is cleaned before the pose\.",
        installation,
    )
    assert "### Extra\n\nMasonry is suspended in frost. Invented step.\n" in page.body
    assert "[[cite" not in page.body and find_violations(page.body) == []
    check_footnotes(page, cited, page.frontmatter.title)
    warnings = [r.getMessage() for r in caplog.records if r.name == "docwiki.stages.render"]
    assert warnings == [
        f"{QUOTE_B} section 2: 2 citation marker(s) but 1 verified citation(s); 1 unmatched "
        "marker(s) dropped",
        f"{QUOTE_B} section 3: 2 citation marker(s) but 0 verified citation(s); 2 unmatched "
        "marker(s) dropped",
    ]
