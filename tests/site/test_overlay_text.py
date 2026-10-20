"""The overlay's pure TypeScript helpers, run with Node (skipped when Node cannot strip types)."""

from __future__ import annotations

import json
import shutil
import subprocess
from functools import cache

import pytest
from site_testkit import MOCK_RELEASE, OVERLAY

from docwiki.contracts.markdown import BACKLINKS_END, BACKLINKS_START, strip_backlinks_block
from docwiki.site import build_answers, notice_kind, open_release

TEXT_MODULE = OVERLAY / "quartz" / "plugins" / "transformers" / "docwiki-text.ts"

BACKLINK_CASES = [
    "no block at all\n",
    f"# T\n\nBody.\n\n{BACKLINKS_START}\n## Referenced by\n\n- [A](a.md)\n\n{BACKLINKS_END}\n\n"
    "## Sources\n\n[^c1]: x\n",
    f"a\n{BACKLINKS_START}\nfirst\n{BACKLINKS_END}\nb\n{BACKLINKS_START}\nsecond\n{BACKLINKS_END}\n",
    f"unterminated {BACKLINKS_START}\nstays\n",
    f"crlf{BACKLINKS_START}\r\nx\r\n{BACKLINKS_END}\r\n",
]


@cache
def _node() -> tuple[str, ...] | None:
    """Node command able to import the ``.ts`` module (type stripping), or ``None``."""
    node = shutil.which("node")
    if node is None:
        return None
    probe = f"await import({json.dumps(TEXT_MODULE.as_uri())})"
    for flags in ((), ("--experimental-strip-types",)):
        command = (node, *flags, "--no-warnings", "--input-type=module")
        completed = subprocess.run(
            [*command, "-e", probe], capture_output=True, text=True, check=False
        )
        if completed.returncode == 0:
            return command
    return None


def run_helpers(script: str) -> object:
    command = _node()
    if command is None:
        pytest.skip("Node 22.6+ (type stripping) is not available")
    program = f"const m = await import({json.dumps(TEXT_MODULE.as_uri())});\n{script}"
    completed = subprocess.run(
        [*command, "-e", program],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_strip_backlinks_block_matches_the_python_contract() -> None:
    cases = json.dumps(BACKLINK_CASES)
    result = run_helpers(
        f"console.log(JSON.stringify({cases}.map((text) => m.stripBacklinksBlock(text))))"
    )
    assert result == [strip_backlinks_block(case) for case in BACKLINK_CASES]


def test_footnote_and_sidecar_badges() -> None:
    result = run_helpers(
        """console.log(JSON.stringify([
          m.splitTrailingBadge(" · ✓ quote verified"),
          m.splitTrailingBadge(" · table "),
          m.splitTrailingBadge(" · generated description"),
          m.splitTrailingBadge(" · OCR"),
          m.splitTrailingBadge(" · paraphrase"),
          m.splitTrailingBadge(" · a table of contents"),
          m.splitTrailingBadge("plain text"),
          m.splitProvenanceBadge(" · Provenance: ✓ quote verified (native text)"),
          m.splitProvenanceBadge("Provenance: unknown"),
        ].map((split) => split ? [split.before, split.badge.kind, split.after] : null)))"""
    )
    assert result == [
        [" · ", "verified", ""],
        [" · ", "table", " "],
        [" · ", "generated", ""],
        [" · ", "ocr", ""],
        [" · ", "paraphrase", ""],
        None,
        None,
        [" · Provenance: ", "verified", " (native text)"],
        None,
    ]


def test_notices_document_links_and_dates() -> None:
    result = run_helpers(
        """console.log(JSON.stringify({
          notices: [
            "FICTIONAL - NOT FOR OPERATIONAL USE.",
            "Superseded by Planning and purchase tracking, indice B.",
            "Warning: this answer cites a withdrawn source.",
            "Fictional characters appear here.",
          ].map(m.noticeKind),
          documents: ["../evidence/src-1/original.pdf#page=3", "original.XLSX", "../a", "x.png"]
            .map(m.isDocumentHref),
          days: ["2026-02-15", "2026-2-15", 20260215, null].map(m.isIsoDay),
          provenance: Object.keys(m.PROVENANCE_BADGES).sort(),
        }))"""
    )
    assert result == {
        "notices": ["fictional", "superseded", "warning", None],
        "documents": [True, True, False, False],
        "days": [True, False, False, False],
        "provenance": ["deterministic-table", "model-description", "native-text", "ocr"],
    }


def test_notice_kind_matches_the_python_answers_builder() -> None:
    texts = [
        "FICTIONAL - NOT FOR OPERATIONAL USE.",
        "  Superseded: this answer cites a revision.",
        "SUPERSEDED by rev B",
        "Warning: this answer cited sources that were withdrawn.",
        "withdrawn source",
        "Fictional characters appear here.",
        "Supersededness",
        "Note: superseded",
        "",
    ]
    result = run_helpers(f"console.log(JSON.stringify({json.dumps(texts)}.map(m.noticeKind)))")
    assert result == [notice_kind(text) for text in texts]


def test_home_notice_and_provenance_phrases() -> None:
    result = run_helpers(
        """console.log(JSON.stringify({
          drops: [
            m.dropsSiteNotice("index", true, "fictional"),
            m.dropsSiteNotice("index", false, "fictional"),
            m.dropsSiteNotice("sources/a", true, "fictional"),
            m.dropsSiteNotice("index", true, "superseded"),
            m.dropsSiteNotice(undefined, true, "fictional"),
          ],
          documents: [[36, 1], [12, 0], [1, 0], [0, 2]].map(([c, s]) => m.documentsPhrase(c, s)),
          quality: [
            {gates: 15, passed: 15, warned: 0, failed: 0, skipped: 0, blockingFailed: 0},
            {gates: 15, passed: 12, warned: 0, failed: 0, skipped: 3, blockingFailed: 0},
            {gates: 15, passed: 13, warned: 1, failed: 0, skipped: 1, blockingFailed: 0},
            {gates: 15, passed: 11, warned: 2, failed: 0, skipped: 2, blockingFailed: 0},
            {gates: 15, passed: 14, warned: 0, failed: 1, skipped: 0, blockingFailed: 1},
            {gates: 15, passed: 12, warned: 1, failed: 2, skipped: 0, blockingFailed: 2},
          ].map(m.qualityPhrase),
        }))"""
    )
    assert result == {
        "drops": [True, False, False, False, False],
        "documents": [
            "37 documents (1 superseded)",
            "12 documents",
            "1 document",
            "2 documents (2 superseded)",
        ],
        "quality": [
            "15 passed",
            "12 passed, 3 skipped",
            "13 passed, 1 warning, 1 skipped",
            "11 passed, 2 warnings, 2 skipped",
            "1 blocking gate failed",
            "2 blocking gates failed",
        ],
    }


def test_answers_json_round_trips_through_the_drawer_parser() -> None:
    payload = build_answers(open_release(MOCK_RELEASE))
    result = run_helpers(f"console.log(JSON.stringify(m.parseAnswers({json.dumps(payload)})))")
    assert result == payload["answers"]


def test_the_drawer_parser_keeps_well_formed_data_only() -> None:
    good = {
        "id": "query:2026-02-12-a",
        "slug": "queries/2026-02-12-a",
        "question": "Which grade?",
        "date": "2026-02-15",
        "banners": ["Superseded: rev A", 3],
        "paragraphs": [
            [{"text": "Due 2026-04-20."}, {"cite": 1}, {"cite": 0}, {"cite": "1"}, {"html": "<b>"}],
            [],
            "text",
        ],
        "citations": [
            {"n": 1, "title": "SOP", "label": "¶ 4", "href": "evidence/src-1/para-0004",
             "badge": "✓ quote verified"},
            {"n": 2, "title": "SOP", "label": "¶ 5", "href": "javascript:alert(1)", "badge": ""},
            {"n": 3, "title": "SOP", "label": "¶ 6", "href": "../../etc/x", "badge": ""},
            {"n": 4, "title": "SOP", "label": "¶ 7", "href": "//example.org/x", "badge": ""},
            {"n": 5, "title": "Plan", "label": "rows", "href": "evidence/src-2/sheet#row-3"},
        ],
        "steps": ["search x", None],
        "provenance": ["not", "text"],
        "pages": ["queries/2026-02-12-a", {"slug": "x"}],
    }
    bad = [
        None,
        "answer",
        {**good, "slug": "https://example.org/queries/a"},
        {**good, "slug": "queries/../index"},
        {**good, "id": ""},
        {**good, "question": "  "},
    ]
    script = f"""
      const parsed = m.parseAnswers({{schema: 1, answers: {json.dumps([good, *bad])}}})
      const errors = [null, {{}}, {{schema: 2, answers: []}}, {{schema: 1}}].map((payload) => {{
        try {{ m.parseAnswers(payload); return null }} catch (error) {{ return error.message }}
      }})
      console.log(JSON.stringify({{parsed, errors}}))
    """
    result = run_helpers(script)
    assert isinstance(result, dict)
    assert result["parsed"] == [
        {
            "id": "query:2026-02-12-a",
            "slug": "queries/2026-02-12-a",
            "question": "Which grade?",
            "date": "2026-02-15",
            "banners": ["Superseded: rev A"],
            "paragraphs": [[{"text": "Due 2026-04-20."}, {"cite": 1}]],
            "citations": [
                {"n": 1, "title": "SOP", "label": "¶ 4", "href": "evidence/src-1/para-0004",
                 "badge": "✓ quote verified"},
                {"n": 5, "title": "Plan", "label": "rows", "href": "evidence/src-2/sheet#row-3",
                 "badge": ""},
            ],
            "steps": ["search x"],
            "provenance": "",
            "pages": ["queries/2026-02-12-a"],
        }
    ]
    assert result["errors"] == ["answers.json is not a schema 1 answers file"] * 4


def test_drawer_groups_links_labels_and_state() -> None:
    result = run_helpers(
        """
        const answers = ["a", "b", "c"].map((id) => ({id, pages: [`queries/${id}`]}))
        answers[0].pages.push("topics/schedule-and-window-delivery")
        answers[2].pages.push("topics/schedule-and-window-delivery")
        const groups = (slug) =>
          m.groupAnswers(answers, slug).map((g) => [g.title, g.answers.map((a) => a.id)])
        console.log(JSON.stringify({
          topic: groups("topics/schedule-and-window-delivery"),
          home: groups("index"),
          own: groups("queries/b"),
          empty: m.groupAnswers([], "index"),
          hrefs: [
            ["index", "evidence/src-1/p0001"],
            ["topics/schedule-and-window-delivery", "evidence/src-1/p0001"],
            ["evidence/src-1/p0002", "evidence/src-1/sheet-plan-r0002-r0004#row-3"],
            ["entities/work-package/lot-5", "queries/2026-02-12-a"],
            ["sources/index", "queries/2026-02-12-a"],
            ["topics/schedule-and-window-delivery", "index"],
            ["queries/2026-02-12-a", "sources/index"],
            ["queries/2026-02-12-a", "static/docwiki/answers.json"],
          ].map(([from, to]) => m.relativeHref(from, to)),
          steps: [0, 1, 4].map(m.stepsLabel),
          citation: m.citationText({
            n: 2, title: "Maintenance plan 2026", label: 'sheet "Plan", rows 2–4', href: "x",
            badge: "table",
          }),
          badges: ["✓ quote verified", "paraphrase", "table", "OCR", "generated description",
            "native text", ""].map((text) => m.badgeForText(text)?.kind ?? null),
          slugs: ["evidence/src-1/p0001", "_meta/quality", "queries/a#x", "../a", "/a",
            "a/../b", "https://example.org", "a b", "", 7].map(m.isContentSlug),
          states: [
            null,
            "",
            "{",
            "[]",
            '{"open": true, "answer": "query:2026-02-12-a", "scroll": 120.4}',
            '{"open": "yes", "answer": 7, "scroll": -3}',
            '{"open": false, "answer": "", "scroll": "12"}',
            '{"open": false, "answer": "query:2026-02-12-a", "scroll": 40, "resume": true}',
          ].map(m.parseAskState),
          key: m.ASK_STATE_KEY,
        }))
        """
    )
    assert result == {
        "topic": [["About this page", ["a", "c"]], ["More questions", ["b"]]],
        "home": [["Questions", ["a", "b", "c"]]],
        "own": [["About this page", ["b"]], ["More questions", ["a", "c"]]],
        "empty": [],
        "hrefs": [
            "./evidence/src-1/p0001",
            "../evidence/src-1/p0001",
            "../../evidence/src-1/sheet-plan-r0002-r0004#row-3",
            "../../queries/2026-02-12-a",
            "../queries/2026-02-12-a",
            "../",
            "../sources/",
            "../static/docwiki/answers.json",
        ],
        "steps": [
            "How the agent worked (0 steps)",
            "How the agent worked (1 step)",
            "How the agent worked (4 steps)",
        ],
        "citation": '[2] Maintenance plan 2026 — sheet "Plan", rows 2–4',
        "badges": ["verified", "paraphrase", "table", "ocr", "generated", None, None],
        "slugs": [True, True, True, False, False, False, False, False, False, False],
        "states": [
            {"open": False, "answer": None, "scroll": 0, "resume": False},
            {"open": False, "answer": None, "scroll": 0, "resume": False},
            {"open": False, "answer": None, "scroll": 0, "resume": False},
            {"open": False, "answer": None, "scroll": 0, "resume": False},
            {"open": True, "answer": "query:2026-02-12-a", "scroll": 120, "resume": False},
            {"open": False, "answer": None, "scroll": 0, "resume": False},
            {"open": False, "answer": None, "scroll": 0, "resume": False},
            {"open": False, "answer": "query:2026-02-12-a", "scroll": 40, "resume": True},
        ],
        "key": "docwiki-ask",
    }


def test_drawer_provenance_line_and_narrow_collapse() -> None:
    result = run_helpers(
        """
        const note = "Answered by the Researcher agent (docwiki-researcher version 7) on " +
          "2026-10-20. The agent made 3 tool calls in 21 s:"
        const open = {open: true, answer: "query:2026-02-12-a", scroll: 0, resume: false}
        console.log(JSON.stringify({
          lines: [
            {provenance: note, date: "2026-10-20"},
            {provenance: "No source of that release answers the question.", date: "2026-10-20"},
            {provenance: "  ", date: "2026-02-15"},
            {provenance: "", date: ""},
            {provenance: "Ratio 1:2 noted: ", date: "2026-02-15"},
          ].map(m.provenanceLine),
          narrow: m.followLink(open, true, 180),
          wide: m.followLink(open, false, 180),
          labels: [
            m.followLink(open, true, 0),
            m.followLink(open, false, 0),
            {open: false, answer: null, scroll: 0, resume: true},
            m.parseAskState(null),
          ].map(m.fabLabel),
          query: m.NARROW_QUERY,
        }))
        """
    )
    assert result == {
        "lines": [
            "Answered by the Researcher agent (docwiki-researcher version 7) on 2026-10-20. "
            "The agent made 3 tool calls in 21 s.",
            "No source of that release answers the question.",
            "Filed on 2026-02-15",
            "",
            "Ratio 1:2 noted.",
        ],
        "narrow": {"open": False, "answer": "query:2026-02-12-a", "scroll": 180, "resume": True},
        "wide": {"open": True, "answer": "query:2026-02-12-a", "scroll": 180, "resume": False},
        "labels": ["Back to the answer", "Ask this wiki", "Ask this wiki", "Ask this wiki"],
        "query": "(max-width: 1200px)",
    }
