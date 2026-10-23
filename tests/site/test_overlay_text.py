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
        answers[0].pages.push("topics/planning")
        answers[2].pages.push("topics/planning")
        const groups = (slug) =>
          m.groupAnswers(answers, slug).map((g) => [g.title, g.answers.map((a) => a.id)])
        console.log(JSON.stringify({
          topic: groups("topics/planning"),
          home: groups("index"),
          own: groups("queries/b"),
          empty: m.groupAnswers([], "index"),
          hrefs: [
            ["index", "evidence/src-1/p0001"],
            ["topics/planning", "evidence/src-1/p0001"],
            ["evidence/src-1/p0002", "evidence/src-1/sheet-plan-r0002-r0004#row-3"],
            ["entities/work-package/lot-5", "queries/2026-02-12-a"],
            ["sources/index", "queries/2026-02-12-a"],
            ["topics/planning", "index"],
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


# ----- Live questions (ADR 0008): the pure side of the drawer's Ask form -----

LIVE_ANSWER = {
    "id": "live:0123456789abcdef0123456789abcdef",
    "slug": "index",
    "question": "When are the windows delivered?",
    "date": "2026-10-21",
    "banners": ["Live answer from the Researcher agent — not reviewed by the owner."],
    "paragraphs": [[{"text": "Delivery is due in April"}, {"cite": 1}, {"text": "."}]],
    "citations": [
        {
            "n": 1,
            "title": "Site meeting minutes",
            "label": "¶ 7",
            "href": "evidence/src-f0757603684a/para-0007",
            "badge": "paraphrase",
        }
    ],
    "steps": ["search `window delivery`"],
    "provenance": "Answered live by the Researcher agent.",
    "pages": [],
    "live": True,
}


def test_live_status_questions_job_ids_and_messages() -> None:
    result = run_helpers(
        """
        console.log(JSON.stringify({
          status: [{enabled: true}, {enabled: false}, {enabled: "yes"}, {}, null, "x", []]
            .map(m.parseLiveStatus),
          questions: ["", "  ab ", "abc", "  When is it?  ", "x".repeat(500), "x".repeat(501),
            " ".repeat(10) + "x".repeat(500)].map(m.liveQuestion),
          jobs: ["0123456789abcdef0123456789abcdef", "../../etc", "0123", "", 7, null]
            .map((id) => { try { return m.parseJobId({job_id: id}) } catch { return null } }),
          noJob: (() => { try { return m.parseJobId(null) } catch { return "throws" } })(),
          refusals: [
            {message: "  Your previous question is still being answered. "},
            {message: ""},
            {message: 7},
            {message: "x".repeat(400)},
            null,
          ].map(m.refusalMessage),
          waiting: [0, 3.9, 61, -2].map(m.waitingLabel),
          paths: [m.LIVE_STATUS_PATH, m.LIVE_ASK_PATH, m.LIVE_POLL_MS, m.LIVE_QUESTION_MAX],
        }))
        """
    )
    assert isinstance(result, dict)
    assert result["status"] == [True, False, False, False, False, False, False]
    assert result["questions"] == [
        {"error": "Please ask a complete question."},
        {"error": "Please ask a complete question."},
        {"question": "abc"},
        {"question": "When is it?"},
        {"question": "x" * 500},
        {"error": "Please keep the question under 500 characters."},
        {"question": "x" * 500},
    ]
    assert result["jobs"] == ["0123456789abcdef0123456789abcdef", None, None, None, None, None]
    assert result["noJob"] == "throws"
    generic = "The live agent could not be reached. Please try again later."
    assert result["refusals"] == [
        "Your previous question is still being answered.",
        generic,
        generic,
        "x" * 300,
        generic,
    ]
    assert result["waiting"] == [
        "The Researcher is reading the wiki… 0 s",
        "The Researcher is reading the wiki… 3 s",
        "The Researcher is reading the wiki… 61 s",
        "The Researcher is reading the wiki… 0 s",
    ]
    assert result["paths"] == ["api/ask/status", "api/ask", 2000, 500]


def test_live_poll_replies_are_parsed_as_data() -> None:
    unverified = {
        **LIVE_ANSWER,
        "banners": [LIVE_ANSWER["banners"][0]],
    }
    replies = [
        {"status": "running", "elapsed_s": 4.2},
        {"status": "running"},
        {"status": "busy", "elapsed_s": 1, "message": "The live agent has reached its limit."},
        {"status": "error", "message": "  "},
        {"status": "done", "elapsed_s": 30, "answer": LIVE_ANSWER},
        {
            "status": "done",
            "answer": {**LIVE_ANSWER, "live": False, "slug": "index", "id": "live:x"},
        },
        {
            "status": "unverified",
            "message": "This answer could not be checked against the sources.",
            "answer": unverified,
        },
        {"status": "unverified", "answer": {**unverified, "paragraphs": [[{"cite": 1}]]}},
    ]
    broken = [
        None,
        "done",
        {},
        {"status": "finished"},
        {"status": "done"},
        {"status": "done", "answer": {"id": ""}},
        {"status": "done", "answer": {**LIVE_ANSWER, "slug": "https://example.org/x"}},
    ]
    result = run_helpers(
        f"""
        const parsed = {json.dumps(replies)}.map(m.parseLivePoll)
        const errors = {json.dumps(broken)}.map((payload) => {{
          try {{ m.parseLivePoll(payload); return null }} catch (error) {{ return error.message }}
        }})
        console.log(JSON.stringify({{parsed, errors}}))
        """
    )
    assert isinstance(result, dict)
    running, running_bare, busy, error, done, forced, unchecked, citation_only = result["parsed"]
    assert running == {"state": "running", "elapsed": 4.2}
    assert running_bare == {"state": "running", "elapsed": 0}
    assert busy == {
        "state": "failed",
        "status": "busy",
        "message": "The live agent has reached its limit.",
    }
    assert error == {
        "state": "failed",
        "status": "error",
        "message": "The live agent could not be reached. Please try again later.",
    }
    assert done == {"state": "answer", "status": "done", "answer": LIVE_ANSWER}
    assert forced["answer"]["live"] is True  # the client marks every live answer, whatever it says
    assert unchecked["status"] == "unverified"
    answer = unchecked["answer"]
    assert answer["citations"] == []  # no citation links, even if the server sent them
    assert answer["paragraphs"] == [[{"text": "Delivery is due in April"}, {"text": "."}]]
    assert answer["banners"] == [
        LIVE_ANSWER["banners"][0],
        "This answer could not be checked against the sources.",
    ]
    assert answer["live"] is True
    assert citation_only["answer"]["paragraphs"] == []
    assert all(isinstance(message, str) for message in result["errors"])


def test_live_flag_survives_the_answers_parser_only_when_true() -> None:
    result = run_helpers(
        f"""
        const base = {json.dumps(LIVE_ANSWER)}
        const answers = m.parseAnswers({{schema: 1, answers: [
          base, {{...base, id: "a", live: "yes"}}, {{...base, id: "b", live: false}},
        ]}})
        console.log(JSON.stringify(answers.map((item) => item.live ?? null)))
        """
    )
    assert result == [True, None, None]


def test_citations_are_renumbered_in_order_of_first_appearance() -> None:
    result = run_helpers(
        """
        const cite = (n, title) => ({n, title, label: "p. 1", href: `evidence/s/${n}`, badge: ""})
        const item = {
          id: "x", slug: "queries/x", question: "q", date: "", banners: [], steps: [],
          provenance: "", pages: [],
          paragraphs: [
            [{text: "A"}, {cite: 3}, {cite: 1}, {text: " B"}, {cite: 3}],
            [{text: "C"}, {cite: 7}],
          ],
          citations: [cite(1, "one"), cite(2, "two"), cite(3, "three")],
        }
        const out = m.renumberCitations(item)
        console.log(JSON.stringify({
          marks: out.paragraphs.map((p) => p.map((s) => s.cite ?? s.text)),
          sources: out.citations.map((c) => [c.n, c.title]),
          untouched: item.paragraphs[0][1].cite,
          empty: m.renumberCitations({...item, paragraphs: [], citations: []}).citations,
        }))
        """
    )
    assert result == {
        "marks": [["A", 1, 2, " B", 1], ["C", 4]],
        "sources": [[1, "three"], [2, "one"], [3, "two"]],  # 4: cited but not listed
        "untouched": 3,
        "empty": [],
    }


def test_drawer_phone_state_examples_and_stored_live_answers() -> None:
    result = run_helpers(
        f"""
        const open = {{open: true, answer: "a", scroll: 4, resume: false}}
        const base = {json.dumps(LIVE_ANSWER)}
        const filed = {{...base, id: "f", live: undefined,
          question: "When are the windows of the extension delivered?"}}
        const stored = JSON.stringify([base, {{id: 1}}, {{...base, id: "b", live: false}}])
        console.log(JSON.stringify({{
          phone: m.restoredState(open, true),
          desktop: m.restoredState(open, false) === open,
          liveNotice: m.isLiveNotice(base.banners[0]),
          allExamples: m.exampleQuestions(null, true).length,
          filedExamples: m.exampleQuestions([filed], false),
          none: m.exampleQuestions(null, false),
          match: m.filedAnswerFor([filed], " when ARE the windows of the extension delivered?")?.id,
          stored: m.parseStoredLive(stored).map((item) => [item.id, item.live]),
          bad: [
            m.parseStoredLive("{{"), m.parseStoredLive('{{"a":1}}'), m.parseStoredLive(null),
          ],
        }}))
        """
    )
    assert isinstance(result, dict)
    assert result["phone"] == {"open": False, "answer": "a", "scroll": 4, "resume": False}
    assert result["desktop"] is True
    assert result["liveNotice"] is True
    assert result["allExamples"] == 3
    assert result["filedExamples"] == ["When are the windows of the extension delivered?"]
    assert result["none"] == []
    assert result["match"] == "f"
    assert result["stored"] == [[LIVE_ANSWER["id"], True], ["b", True]]
    assert result["bad"] == [[], [], []]


def test_story_home_last_run_line_and_ask_hook() -> None:
    result = run_helpers(
        """
        const run = (extra) => ({run_id: "r1", is_current: false, cost: {}, ...extra})
        const current = (cost, extra = {}) => run({is_current: true, cost, ...extra})
        const payload = {runs: [
          run({cost: {currency: "USD", total: 9.99, duration_s: 30}}),
          current({currency: "USD", total: 1.374, duration_s: 252}),
          current({currency: "USD", total: 5, duration_s: 9}),
        ]}
        console.log(JSON.stringify({
          event: m.ASK_EVENT,
          line: m.lastRunLine(payload),
          dates: m.lastRunLine({runs: [current({}, {
            started_at: "2026-04-01T09:00:00Z", finished_at: "2026-04-01T10:05:00Z"})]}),
          costOnly: m.lastRunLine({runs: [current({total: 0.001})]}),
          euro: m.lastRunLine({runs: [current({currency: "EUR", total: 2})]}),
          odd: m.lastRunLine({runs: [current({currency: "<b>", total: "1", duration_s: -3})]}),
          none: [
            m.lastRunLine(null), m.lastRunLine({runs: "x"}), m.lastRunLine({runs: [null, 3]}),
            m.lastRunLine({runs: [run({cost: {total: 1}})]}),
            m.lastRunLine({runs: [current(null)]}),
          ],
          durations: [0.2, 42, 59.4, 59.6, 252, 3600, 3900].map(m.shortDuration),
          badDuration: [m.shortDuration(-1), m.shortDuration(Number.NaN)],
          questions: [
            m.askEventQuestion({question: "  When are\\n the windows delivered? "}),
            m.askEventQuestion({question: ""}), m.askEventQuestion({question: 3}),
            m.askEventQuestion("text"), m.askEventQuestion(null),
            m.askEventQuestion({question: "x".repeat(501)}),
          ],
          plural: [m.plural(1, "cited page"), m.plural(8, "cited page")],
        }))
        """
    )
    assert result == {
        "event": "docwiki:ask",
        "line": "last run 4 min · $1.37",  # the first current run; 252 s rounds to 4 min
        "dates": "last run 1 h 5 min",  # no receipt duration: from its start to its end
        "costOnly": "last run <$0.01",
        "euro": "last run EUR 2.00",
        "odd": None,
        "none": [None, None, None, None, None],
        "durations": ["1 s", "42 s", "59 s", "1 min", "4 min", "1 h", "1 h 5 min"],
        "badDuration": [None, None],
        "questions": ["When are the windows delivered?", None, None, None, None, None],
        "plural": ["1 cited page", "8 cited pages"],
    }
