"""The citation parser: ``[n] <title> — <locator label> (<provenance>) — <sidecar path>``."""

from __future__ import annotations

import pytest
from agents_testkit import ANSWER_TEXT

from docwiki.agents_client.citations import (
    Source,
    inline_citations,
    normalize_path,
    normalize_provenance,
    parse_answer,
    parse_source_line,
    split_answer,
)

SOP_B = "evidence/src-4d9c65e05302/para-0004.md"
PLAN = "evidence/src-43c97f7dfcde/sheet-plan-r0002-r0004.md"


def test_canonical_answer_is_parsed() -> None:
    assert parse_answer(ANSWER_TEXT) == [
        Source(
            n=1,
            title="Gearbox oil change SOP rev B",
            locator_label="¶ 4",
            provenance="native-text",
            path=SOP_B,
            source_id="src-4d9c65e05302",
            locator_key="para-0004",
        ),
        Source(
            n=2,
            title="Maintenance plan 2026",
            locator_label='sheet "Plan", rows 2–4',
            provenance="deterministic-table",
            path=PLAN,
            source_id="src-43c97f7dfcde",
            locator_key="sheet-plan-r0002-r0004",
        ),
    ]


@pytest.mark.parametrize(
    "line",
    [
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}",
        f"[1] Gearbox oil change SOP rev B – ¶ 4 (native-text) – {SOP_B}",
        f"[1] Gearbox oil change SOP rev B - ¶ 4 (native-text) - {SOP_B}",
        f"[1] Gearbox oil change SOP rev B -- ¶ 4 (native-text) -- {SOP_B}",
        f"[1] Gearbox oil change SOP rev B | ¶ 4 (native-text) | {SOP_B}",
        f"- [1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}",
        f"* **[1]** Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}",
        f"1. [1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}",
        f"[1]: Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}",
        f"[^1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — `{SOP_B}`",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — <{SOP_B}>",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — ../{SOP_B}",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — ./{SOP_B}#text",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — [{SOP_B}]({SOP_B})",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}.",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (✓ quote verified) — {SOP_B}",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (Native text) — {SOP_B}",
        f"[1] [Gearbox oil change SOP rev B — ¶ 4](../{SOP_B}) · ✓ quote verified",
        "[1] [Gearbox oil change SOP rev B](../sources/sop-gbx-010-rev-b.md) — ¶ 4 "
        f"(native-text) — {SOP_B}",
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — https://wiki.example/{SOP_B}",
        f"  [1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}  ",
    ],
)
def test_source_line_variants(line: str) -> None:
    source = parse_source_line(line)
    assert source is not None
    assert (source.n, source.title, source.locator_label) == (
        1,
        "Gearbox oil change SOP rev B",
        "¶ 4",
    )
    assert source.provenance == "native-text"
    assert source.path == SOP_B
    assert (source.source_id, source.locator_key) == ("src-4d9c65e05302", "para-0004")


def test_title_with_dashes_keeps_everything_before_the_locator() -> None:
    line = f"[3] SOP-GBX-010 — Gearbox oil change - rev B — p. 1 (native-text) — {SOP_B}"
    source = parse_source_line(line)
    assert source is not None
    assert source.title == "SOP-GBX-010 — Gearbox oil change - rev B"
    assert source.locator_label == "p. 1"


@pytest.mark.parametrize(
    ("badge", "provenance"),
    [
        ("table", "deterministic-table"),
        ("deterministic table", "deterministic-table"),
        ("OCR", "ocr"),
        ("generated description", "model-description"),
        ("model_description", "model-description"),
        ("paraphrase", "native-text"),
        ("scan", "scan"),
    ],
)
def test_provenance_badges_are_normalised(badge: str, provenance: str) -> None:
    assert normalize_provenance(badge) == provenance
    source = parse_source_line(f"[2] Maintenance plan 2026 — rows 2–4 ({badge}) — {PLAN}")
    assert source is not None
    assert source.provenance == provenance


def test_partial_source_lines() -> None:
    no_path = parse_source_line("[1] Gearbox oil change SOP rev B — ¶ 4 (native-text)")
    assert no_path == Source(
        n=1, title="Gearbox oil change SOP rev B", locator_label="¶ 4", provenance="native-text"
    )
    computed = parse_source_line(
        "[3] Maintenance plan 2026 — table t01, rows r0002–r0004 (deterministic-table) — -"
    )
    assert computed == Source(
        n=3,
        title="Maintenance plan 2026",
        locator_label="table t01, rows r0002–r0004",
        provenance="deterministic-table",
    )
    no_provenance = parse_source_line(f"[1] Gearbox oil change SOP rev B — p. 3 — {SOP_B}")
    assert no_provenance is not None
    assert (no_provenance.locator_label, no_provenance.provenance) == ("p. 3", "")
    no_locator = parse_source_line(f"[1] Gearbox oil change SOP rev B (native-text) {SOP_B}")
    assert no_locator is not None
    assert (no_locator.title, no_locator.locator_label) == ("Gearbox oil change SOP rev B", "")
    title_with_parentheses = parse_source_line(f"[1] Gearbox SOP (rev B) — {SOP_B}")
    assert title_with_parentheses is not None
    assert (title_with_parentheses.title, title_with_parentheses.provenance) == (
        "Gearbox SOP (rev B)",
        "",
    )


def test_wiki_page_paths_are_kept_but_have_no_evidence_ids() -> None:
    source = parse_source_line(
        "[1] Gearbox oil — Overview (native-text) — ../topics/gearbox-oil.md"
    )
    assert source is not None
    assert source.path == "topics/gearbox-oil.md"
    assert source.source_id is None and source.locator_key is None
    odd_key = parse_source_line("[1] SOP — p. 3 (native-text) — evidence/src-4d9c65e05302/page3.md")
    assert odd_key is not None
    assert (odd_key.source_id, odd_key.locator_key) == ("src-4d9c65e05302", None)


def test_body_sentences_starting_with_a_number_are_not_sources() -> None:
    text = (
        "[1] The procedure requires ISO VG 220 at cold sites.\n"
        "More details follow [1].\n\n"
        "Sources:\n"
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}\n"
    )
    assert [source.title for source in parse_answer(text)] == ["Gearbox oil change SOP rev B"]
    assert parse_source_line("[1] The procedure requires ISO VG 220 at cold sites.") is None


@pytest.mark.parametrize(
    "heading", ["Sources:", "**Sources:**", "**Sources**:", "## Sources", "Sources :", "Quellen:"]
)
def test_source_block_headings_and_lenient_lines(heading: str) -> None:
    text = (
        "Die aktuelle Vorschrift verlangt ISO VG 220 [1].\n\n"
        f"{heading}\n"
        "1. Gearbox oil change SOP rev B\n"
        f'[2] Maintenance plan 2026 — sheet "Plan", rows 2–4 (table) — {PLAN}\n'
    )
    sources = parse_answer(text)
    assert [(source.n, source.title) for source in sources] == [
        (1, "Gearbox oil change SOP rev B"),
        (2, "Maintenance plan 2026"),
    ]
    assert sources[1].provenance == "deterministic-table"


def test_trailing_block_without_heading_and_crlf() -> None:
    text = ANSWER_TEXT.replace("Sources:\n", "").replace("\n", "\r\n")
    assert [source.n for source in parse_answer(text)] == [1, 2]


def test_duplicate_numbers_keep_the_first_and_results_are_sorted() -> None:
    text = (
        "Answer [2][1].\n\nSources:\n"
        f"[2] Maintenance plan 2026 — rows 2–4 (deterministic-table) — {PLAN}\n"
        f"[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — {SOP_B}\n"
        f"[1] Duplicate — p. 9 (native-text) — {SOP_B}\n"
    )
    sources = parse_answer(text)
    assert [(source.n, source.title) for source in sources] == [
        (1, "Gearbox oil change SOP rev B"),
        (2, "Maintenance plan 2026"),
    ]


def test_abstention_has_no_sources() -> None:
    text = "Not found in the wiki. I searched for the gearbox oil of WTG-99 and found nothing."
    assert parse_answer(text) == []
    assert inline_citations(text) == []


def test_split_answer_and_inline_citations() -> None:
    body, block = split_answer(ANSWER_TEXT)
    assert body.endswith("(authority, then recency) [1][2].")
    assert block.startswith("Sources:\n[1] Gearbox oil change SOP rev B")
    assert inline_citations(ANSWER_TEXT) == [1, 2]
    assert inline_citations("See [2], then [1](link) and [1]: x and [3][2].") == [2, 3]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../evidence/src-4d9c65e05302/p0003.md", "evidence/src-4d9c65e05302/p0003.md"),
        ("../../evidence/src-4d9c65e05302/p0003.md#page-3", "evidence/src-4d9c65e05302/p0003.md"),
        ("/evidence/src-4d9c65e05302/p0003.md", "evidence/src-4d9c65e05302/p0003.md"),
        ("releases/r1/evidence/src-4d9c65e05302/p0003.md", "evidence/src-4d9c65e05302/p0003.md"),
        (
            "https://wiki.example/evidence/src-4d9c65e05302/p0003.md",
            "evidence/src-4d9c65e05302/p0003.md",
        ),
        ("..\\evidence\\src-4d9c65e05302\\p0003.md", "evidence/src-4d9c65e05302/p0003.md"),
        ("`sources/sop-gbx-010-rev-b.md`", "sources/sop-gbx-010-rev-b.md"),
    ],
)
def test_normalize_path(raw: str, expected: str) -> None:
    assert normalize_path(raw) == expected
