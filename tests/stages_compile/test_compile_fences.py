"""Fenced code: one CommonMark tracker shared by citation verification and rendering."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from compile_testkit import (
    FIXED_NOW,
    block,
    compile_handler,
    compiled,
    make_doc,
    make_state,
    quote_b_doc,
    section,
)
from test_compile_release import write_sidecars

from docwiki.contracts import ExtractedDoc, find_violations
from docwiki.contracts.fences import (
    FenceTracker,
    closes_fence,
    escape_fence,
    opening_fence,
    widen_fences,
)
from docwiki.contracts.markdown import extract_footnotes
from docwiki.contracts.runs import VersionInfo
from docwiki.domain import DomainPack
from docwiki.llm import FakeLlmClient
from docwiki.release import ReleaseWriter, validate_release
from docwiki.stages.classify import classify_source
from docwiki.stages.compile import compile_source
from docwiki.stages.render import clean_block_markdown, render_source_page
from docwiki.stages.verify_citations import DocIndex, verify_section_body

MARKER_RE = re.compile(r"\[\[\s*cite\s*:\s*([^\]\n]*?)\s*\]\]", re.IGNORECASE)
SIMPLE_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
CLOSING = "Close the temporary opening [[cite:b1]]."


def site_doc() -> ExtractedDoc:
    return make_doc(
        "chantier/consignes.pdf",
        [
            block(
                "b0001",
                "FICTIONAL - NOT FOR OPERATIONAL USE. Fermer l'ouverture provisoire après le "
                "passage du camion-grue.",
            )
        ],
    )


def code_mask(lines: list[str]) -> list[bool]:
    tracker = FenceTracker()
    return [tracker.feed(line) for line in lines]


def simple_mask(lines: list[str]) -> list[bool]:
    """Code lines for a parser without CommonMark's info-string rules (the validator's scan)."""
    mask: list[bool] = []
    fence: str | None = None
    for line in lines:
        match = SIMPLE_FENCE_RE.match(line)
        if fence is None:
            fence = match.group(1) if match else None
            mask.append(fence is not None)
            continue
        mask.append(True)
        if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= len(fence):
            fence = None
    return mask


@pytest.mark.parametrize(
    ("lines", "mask"),
    [
        (["````", "```", "````", "after"], [True, True, True, False]),
        (["~~~", "```", "~~~", "after"], [True, True, True, False]),
        (["~~~~", "~~~", "~~~~~", "after"], [True, True, True, False]),
        (["```python", "x = 1", "```", "after"], [True, True, True, False]),
        (["```", "```python", "x = 1", "```", "after"], [True, True, True, True, False]),
        (["```", "````", "after"], [True, True, False]),
        (["```", "```  \t", "after"], [True, True, False]),
        (["   ```", "x", "   ```", "after"], [True, True, True, False]),
        (["```", "x", "    ```", "y"], [True, True, True, True]),
        (["    ```", "after"], [False, False]),
        (["``` a`b", "after"], [False, False]),
        (["~~~ a`b", "x", "~~~", "after"], [True, True, True, False]),
        (["``", "after"], [False, False]),
        (["```", "never closed"], [True, True]),
    ],
)
def test_fence_tracker_follows_commonmark(lines: list[str], mask: list[bool]) -> None:
    assert code_mask(lines) == mask


def test_fence_helpers() -> None:
    assert opening_fence("  ````json") == "````"
    assert opening_fence("~~~ with `ticks`") == "~~~"
    assert opening_fence("```js `x`") is None
    assert closes_fence("````", "```") and not closes_fence("```", "````")
    assert not closes_fence("~~~", "```") and not closes_fence("``` js", "```")
    assert escape_fence("```js `x` [[cite:b1]]") == "\\```js `x` [[cite:b1]]"
    assert escape_fence("  ~~~ x") == "  \\~~~ x"
    assert escape_fence("Plain text.") == "Plain text."
    assert widen_fences(["```js", "```python", "x", "```", "after"]) == [
        "````js",
        "```python",
        "x",
        "````",
        "after",
    ]
    assert widen_fences(["```", "````", "x"]) == ["```", "````", "x"]


def test_fence_length_mismatch_does_not_hide_later_markers() -> None:
    body = f"````\n```\n````\n{CLOSING}"
    check = verify_section_body(DocIndex(site_doc()), body)
    assert [marker.cited.ref for marker in check.markers] == ["b0001"]  # type: ignore[union-attr]
    assert check.body == "````\n```\n````\nClose the temporary opening [[cite:b0001]]."
    assert check.failed == [] and check.dropped_sentences == 0


TRICKY_BODIES = [
    f"````\n```\n````\n{CLOSING}",
    f"~~~\n```\n~~~\n{CLOSING}",
    f"~~~\n~~~ end\nx\n~~~\n{CLOSING}",
    f"```\n```python\nraw [[cite:b1]]\n```\n{CLOSING}",
    f"```\n````\n{CLOSING}",
    f"``` a`b\n{CLOSING}",
    f"    ```\n{CLOSING}",
    f"{CLOSING}\n```\nnever closed [[cite:b1]]",
    f"```\ncode\n```[[cite:b1]]\n# Heading\n| a | b |\n[^1]: note\n{CLOSING}",
    f"[^1]```python\n{CLOSING}",
]


@pytest.mark.parametrize("body", TRICKY_BODIES)
def test_verification_and_rendering_count_the_same_markers(body: str) -> None:
    check = verify_section_body(DocIndex(site_doc()), clean_block_markdown(body))
    rendered = MARKER_RE.findall(clean_block_markdown(check.body))
    assert len(rendered) == len(check.markers) == 1


@pytest.mark.parametrize("body", TRICKY_BODIES)
def test_cleaned_bodies_read_the_same_for_simpler_parsers(body: str) -> None:
    cleaned = clean_block_markdown(body)
    lines = cleaned.split("\n")
    assert code_mask(lines) == simple_mask(lines), cleaned
    tracker = FenceTracker()
    for line in lines:
        tracker.feed(line)
    assert not tracker.inside, "fences are balanced"
    assert clean_block_markdown(cleaned) == cleaned


def test_a_marker_on_the_closing_fence_closes_the_block() -> None:
    body = f"```\ncode\n```[[cite:b1]]\n# Heading\n| a | b |\n[^1]: note\n{CLOSING}"
    assert clean_block_markdown(body) == f"```\ncode\n```\n#### Heading\n{CLOSING}"


def test_text_lines_that_look_like_fences_are_escaped() -> None:
    assert clean_block_markdown(f"``` a`b [[cite:b1]]\n{CLOSING}") == (
        f"\\``` a`b [[cite:b1]]\n{CLOSING}"
    )
    assert clean_block_markdown(f"[^1]```python\n{CLOSING}") == f"\\```python\n{CLOSING}"
    assert clean_block_markdown(f"```\n```python\nx\n```\n{CLOSING}") == (
        f"````\n```python\nx\n````\n{CLOSING}"
    )


async def test_tricky_fences_pass_the_release_validator(tmp_path: Path, pack: DomainPack) -> None:
    doc = quote_b_doc()
    body = "\n".join(
        [
            "In frost the masonry work is suspended [[cite:b3]].",
            "```",
            "```python",
            "print('slab') [[cite:b4]]",
            "```",
            "The bay window F1 is widened to 3,00 m [[cite:b4]].",
            "``` a`b [[cite:b3]]",
            "~~~",
            "~~~ end",
            "~~~",
            "The bay window F1 is installed first [[cite:b3]].",
        ]
    )

    def output() -> dict:
        return compiled(
            "Quote DEV-2026-014 indice B", "Slab cleaning.", [], [section("Notes", body)]
        )

    llm = FakeLlmClient({"compile": compile_handler({doc.source_id: output})})
    classification = await classify_source(doc, pack, llm)
    result = await compile_source(doc, classification, pack, llm)
    assert len([c for c in result.citations if c.ref == "s1"]) == 4
    writer = ReleaseWriter(
        tmp_path / "release",
        created_at=FIXED_NOW,
        audience="internal",
        versions=VersionInfo(
            docwiki="0.1.0", domain_pack=pack.name, domain_pack_hash=pack.content_hash()
        ),
    )
    page, cited = render_source_page(
        result,
        doc,
        classification,
        make_state(doc),
        slug="quote-b",
        stamp=writer.stamp,
        pack=pack,
    )
    writer.write_page(page)
    write_sidecars(writer, cited, {doc.source_id: page.frontmatter.title})
    assert "[[cite" not in page.body and find_violations(page.body) == []
    assert "````\n```python\nprint('slab') \n````" in page.body
    assert "\\``` a`b[^c1]" in page.body and "~~~~\n~~~ end\n~~~~" in page.body
    refs, definitions = extract_footnotes(page.body)
    assert {label for label, _ in refs} == {d.label for d in definitions} == {"c1", "c2"}
    violations = validate_release(writer.root, require_manifest=False, audience="internal")
    gates = {"G02", "G03", "G05", "G06"}
    relevant = [v for v in violations if v.gate in gates and "quote-b" in (v.path or "")]
    assert relevant == []
