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

MINUTES = "evidence/src-165f1d3a109c/para-0007.md"
PLAN = "evidence/src-86eabe3d6d0d/sheet-planning-r0006-r0009.md"


def test_canonical_answer_is_parsed() -> None:
    assert parse_answer(ANSWER_TEXT) == [
        Source(
            n=1,
            title="Site meeting minutes n°3",
            locator_label="¶ 7",
            provenance="native-text",
            path=MINUTES,
            source_id="src-165f1d3a109c",
            locator_key="para-0007",
        ),
        Source(
            n=2,
            title="Planning and purchase tracking, indice B",
            locator_label='sheet "Planning", rows 6–9',
            provenance="deterministic-table",
            path=PLAN,
            source_id="src-86eabe3d6d0d",
            locator_key="sheet-planning-r0006-r0009",
        ),
    ]


@pytest.mark.parametrize(
    "line",
    [
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}",
        f"[1] Site meeting minutes n°3 – ¶ 7 (native-text) – {MINUTES}",
        f"[1] Site meeting minutes n°3 - ¶ 7 (native-text) - {MINUTES}",
        f"[1] Site meeting minutes n°3 -- ¶ 7 (native-text) -- {MINUTES}",
        f"[1] Site meeting minutes n°3 | ¶ 7 (native-text) | {MINUTES}",
        f"- [1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}",
        f"* **[1]** Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}",
        f"1. [1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}",
        f"[1]: Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}",
        f"[^1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}",
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — `{MINUTES}`",
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — <{MINUTES}>",
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — ../{MINUTES}",
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — ./{MINUTES}#text",
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — [{MINUTES}]({MINUTES})",
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}.",
        f"[1] Site meeting minutes n°3 — ¶ 7 (✓ quote verified) — {MINUTES}",
        f"[1] Site meeting minutes n°3 — ¶ 7 (Native text) — {MINUTES}",
        f"[1] [Site meeting minutes n°3 — ¶ 7](../{MINUTES}) · ✓ quote verified",
        "[1] [Site meeting minutes n°3](../sources/2026-03-24-compte-rendu-de-chantier-n3.md)"
        f" — ¶ 7 (native-text) — {MINUTES}",
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — https://wiki.example/{MINUTES}",
        f"  [1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}  ",
    ],
)
def test_source_line_variants(line: str) -> None:
    source = parse_source_line(line)
    assert source is not None
    assert (source.n, source.title, source.locator_label) == (
        1,
        "Site meeting minutes n°3",
        "¶ 7",
    )
    assert source.provenance == "native-text"
    assert source.path == MINUTES
    assert (source.source_id, source.locator_key) == ("src-165f1d3a109c", "para-0007")


def test_title_with_dashes_keeps_everything_before_the_locator() -> None:
    line = f"[3] DEV-2026-014 — Extension quote - indice B — p. 1 (native-text) — {MINUTES}"
    source = parse_source_line(line)
    assert source is not None
    assert source.title == "DEV-2026-014 — Extension quote - indice B"
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
    source = parse_source_line(
        f"[2] Planning and purchase tracking, indice B — rows 6–9 ({badge}) — {PLAN}"
    )
    assert source is not None
    assert source.provenance == provenance


def test_partial_source_lines() -> None:
    no_path = parse_source_line("[1] Site meeting minutes n°3 — ¶ 7 (native-text)")
    assert no_path == Source(
        n=1, title="Site meeting minutes n°3", locator_label="¶ 7", provenance="native-text"
    )
    computed = parse_source_line(
        "[3] Planning and purchase tracking, indice B — table t01, rows r0006–r0009 "
        "(deterministic-table) — -"
    )
    assert computed == Source(
        n=3,
        title="Planning and purchase tracking, indice B",
        locator_label="table t01, rows r0006–r0009",
        provenance="deterministic-table",
    )
    no_provenance = parse_source_line(f"[1] Site meeting minutes n°3 — p. 3 — {MINUTES}")
    assert no_provenance is not None
    assert (no_provenance.locator_label, no_provenance.provenance) == ("p. 3", "")
    no_locator = parse_source_line(f"[1] Site meeting minutes n°3 (native-text) {MINUTES}")
    assert no_locator is not None
    assert (no_locator.title, no_locator.locator_label) == ("Site meeting minutes n°3", "")
    title_with_parentheses = parse_source_line(f"[1] Quote DEV-2026-014 (indice B) — {MINUTES}")
    assert title_with_parentheses is not None
    assert (title_with_parentheses.title, title_with_parentheses.provenance) == (
        "Quote DEV-2026-014 (indice B)",
        "",
    )


def test_wiki_page_paths_are_kept_but_have_no_evidence_ids() -> None:
    source = parse_source_line(
        "[1] Schedule and window delivery — Overview (native-text) — "
        "../topics/schedule-and-window-delivery.md"
    )
    assert source is not None
    assert source.path == "topics/schedule-and-window-delivery.md"
    assert source.source_id is None and source.locator_key is None
    odd_key = parse_source_line(
        "[1] Minutes — p. 3 (native-text) — evidence/src-165f1d3a109c/page3.md"
    )
    assert odd_key is not None
    assert (odd_key.source_id, odd_key.locator_key) == ("src-165f1d3a109c", None)


def test_body_sentences_starting_with_a_number_are_not_sources() -> None:
    sentence = "[1] The minutes record the walls of the extension at 70 % progress."
    text = (
        f"{sentence}\n"
        "More details follow [1].\n\n"
        "Sources:\n"
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}\n"
    )
    assert [source.title for source in parse_answer(text)] == ["Site meeting minutes n°3"]
    assert parse_source_line(sentence) is None


@pytest.mark.parametrize(
    "heading", ["Sources:", "**Sources:**", "**Sources**:", "## Sources", "Sources :", "Quellen:"]
)
def test_source_block_headings_and_lenient_lines(heading: str) -> None:
    text = (
        "Les murs de l'extension sont réalisés à 70 % [1].\n\n"
        f"{heading}\n"
        "1. Site meeting minutes n°3\n"
        '[2] Planning and purchase tracking, indice B — sheet "Planning", rows 6–9 (table) — '
        f"{PLAN}\n"
    )
    sources = parse_answer(text)
    assert [(source.n, source.title) for source in sources] == [
        (1, "Site meeting minutes n°3"),
        (2, "Planning and purchase tracking, indice B"),
    ]
    assert sources[1].provenance == "deterministic-table"


def test_trailing_block_without_heading_and_crlf() -> None:
    text = ANSWER_TEXT.replace("Sources:\n", "").replace("\n", "\r\n")
    assert [source.n for source in parse_answer(text)] == [1, 2]


def test_duplicate_numbers_keep_the_first_and_results_are_sorted() -> None:
    text = (
        "Answer [2][1].\n\nSources:\n"
        f"[2] Planning and purchase tracking, indice B — rows 6–9 (deterministic-table) — {PLAN}\n"
        f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — {MINUTES}\n"
        f"[1] Duplicate — p. 9 (native-text) — {MINUTES}\n"
    )
    sources = parse_answer(text)
    assert [(source.n, source.title) for source in sources] == [
        (1, "Site meeting minutes n°3"),
        (2, "Planning and purchase tracking, indice B"),
    ]


def test_abstention_has_no_sources() -> None:
    text = "Not found in the wiki. I searched for the architect of the project and found nothing."
    assert parse_answer(text) == []
    assert inline_citations(text) == []


def test_split_answer_and_inline_citations() -> None:
    body, block = split_answer(ANSWER_TEXT)
    assert body.endswith("(authority, then recency) [1][2].")
    assert block.startswith("Sources:\n[1] Site meeting minutes n°3")
    assert inline_citations(ANSWER_TEXT) == [1, 2]
    assert inline_citations("See [2], then [1](link) and [1]: x and [3][2].") == [2, 3]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../evidence/src-165f1d3a109c/p0003.md", "evidence/src-165f1d3a109c/p0003.md"),
        ("../../evidence/src-165f1d3a109c/p0003.md#page-3", "evidence/src-165f1d3a109c/p0003.md"),
        ("/evidence/src-165f1d3a109c/p0003.md", "evidence/src-165f1d3a109c/p0003.md"),
        ("releases/r1/evidence/src-165f1d3a109c/p0003.md", "evidence/src-165f1d3a109c/p0003.md"),
        (
            "https://wiki.example/evidence/src-165f1d3a109c/p0003.md",
            "evidence/src-165f1d3a109c/p0003.md",
        ),
        ("..\\evidence\\src-165f1d3a109c\\p0003.md", "evidence/src-165f1d3a109c/p0003.md"),
        (
            "`sources/2026-03-24-compte-rendu-de-chantier-n3.md`",
            "sources/2026-03-24-compte-rendu-de-chantier-n3.md",
        ),
    ],
)
def test_normalize_path(raw: str, expected: str) -> None:
    assert normalize_path(raw) == expected
