"""The pipeline page's pure helpers (scripts/pipeline.ts), run with Node (skipped without it)."""

from __future__ import annotations

import json
import shutil
import subprocess
from functools import cache

import pytest
from site_testkit import OVERLAY

from docwiki.contracts.enums import STAGE_NAMES

PIPELINE_MODULE = OVERLAY / "quartz" / "components" / "docwiki" / "scripts" / "pipeline.ts"


@cache
def _node() -> tuple[str, ...] | None:
    """Node command able to import the ``.ts`` module (type stripping), or ``None``."""
    node = shutil.which("node")
    if node is None:
        return None
    probe = f"await import({json.dumps(PIPELINE_MODULE.as_uri())})"
    for flags in ((), ("--experimental-strip-types",)):
        command = (node, *flags, "--no-warnings", "--input-type=module")
        completed = subprocess.run(
            [*command, "-e", probe], capture_output=True, text=True, check=False
        )
        if completed.returncode == 0:
            return command
    return None


def run(expression: str) -> object:
    """Evaluate ``expression`` with the module as ``m`` and return its JSON value."""
    command = _node()
    if command is None:
        pytest.skip("Node 22.6+ (type stripping) is not available")
    program = (
        f"const m = await import({json.dumps(PIPELINE_MODULE.as_uri())});\n"
        f"console.log(JSON.stringify({expression}))"
    )
    completed = subprocess.run(
        [*command, "-e", program], capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_the_stages_and_phases_match_the_pipeline() -> None:
    result = run("{stages: m.STAGES, phases: m.PHASES.map((p) => [p.key, p.word, p.stages])}")
    assert isinstance(result, dict)
    assert tuple(result["stages"]) == STAGE_NAMES
    phases = result["phases"]
    assert [key for key, _word, _stages in phases] == ["read", "file", "write", "check"]
    assert [word for _key, word, _stages in phases] == [
        "Read",
        "File",
        "Write",
        "Check and publish",
    ]
    # The four phases cover the 13 stages once, in order.
    assert tuple(stage for _key, _word, stages in phases for stage in stages) == STAGE_NAMES


def test_phase_marks() -> None:
    result = run(
        """[
          m.phaseMarks("processing", "write", 4, "compile"),
          m.phaseMarks("processing", "read", 1, "discover"),
          m.phaseMarks("processing", null, 3, "classify"),
          m.phaseMarks("processing", null, 13, null),
          m.phaseMarks("processing", null, null, null),
          m.phaseMarks("in_wiki", null),
          m.phaseMarks("superseded", null),
          m.phaseMarks("received", null),
          m.phaseMarks("queued", null),
          m.phaseMarks("failed", null),
          m.phaseMarks("held_back", null),
          m.phaseMarks("removed", null),
        ]"""
    )
    done, current, todo = "done", "current", "todo"
    assert result == [
        [done, done, current, todo],
        [current, todo, todo, todo],
        [done, current, todo, todo],
        [done, done, done, current],
        [done, done, done, current],
        [done] * 4,
        [done] * 4,
        [todo] * 4,
        [todo] * 4,
        None,
        None,
        None,
    ]


def test_phase_text_and_stage_lookup() -> None:
    result = run(
        """[
          m.phaseText("processing", "write", 4, 13, "compile"),
          m.phaseText("processing", "check", 13, 13, "publish"),
          m.phaseText("processing", "file", null, null, null),
          m.phaseText("in_wiki", null),
          m.phaseText("queued", null),
          m.phaseText("failed", null),
          m.phaseOfStage("agentkit"), m.phaseOfStage(null, 10), m.phaseOfStage("nope"),
          m.asPhase("write"), m.asPhase("publish"),
        ]"""
    )
    assert result == [
        "Phase 3 of 4: Write, step 4/13 compile",
        "Phase 4 of 4: Check and publish, step 13/13 publish",
        "Phase 2 of 4: File",
        "All 4 phases done",
        "Not started: 4 phases to go",
        "",
        "write",
        "check",
        None,
        "write",
        None,
    ]


def test_last_change_and_release_changes_are_checked() -> None:
    result = run(
        """{
          last: m.parseLastChange({
            run_id: "r1", finished_at: "2026-10-22T10:00:00Z", change: "changed",
            pages: [
              {title: "Planning PLN-2026-003", url: "/sources/pln-2026-003", change: "changed",
               type: "source"},
              {title: "Old page", url: "/topics/old", change: "removed", type: "topic"},
              {title: "Evil", url: "https://example.invalid/x", change: "added", type: "entity"},
              {title: "Odd", url: "/x", change: "renamed"},
              {url: "/no-title", change: "added"},
            ],
          }),
          oddChange: m.parseLastChange({change: "exploded", pages: "no"}),
          none: m.parseLastChange(null),
          changes: m.parseChanges({
            added: [{title: "A", url: "/a", type: "entity"}, {title: "B", url: "//host/b"}],
            changed: [], removed: [{title: "C", url: "/c"}],
            contradictions: {opened: [{title: "D", url: "/d"}]},
          }),
          docs: m.parseRunDocuments([{path: "planning/x.xlsx", title: null, change: "new"}, {}]),
          urls: ["/a", "//b", "https://c", "/d\\\\e", 3].map(m.siteUrl),
        }"""
    )
    assert isinstance(result, dict)
    assert result["last"] == {
        "finishedAt": "2026-10-22T10:00:00Z",
        "change": "changed",
        "pages": [
            {
                "title": "Planning PLN-2026-003",
                "url": "/sources/pln-2026-003",
                "type": "source",
                "change": "changed",
            },
            {"title": "Old page", "url": None, "type": "topic", "change": "removed"},
            {"title": "Evil", "url": None, "type": "entity", "change": "added"},
        ],
    }
    assert result["oddChange"] == {"finishedAt": None, "change": None, "pages": []}
    assert result["none"] is None
    assert result["changes"] == {
        "added": [
            {"title": "A", "url": "/a", "type": "entity"},
            {"title": "B", "url": None, "type": None},
        ],
        "changed": [],
        "removed": [{"title": "C", "url": None, "type": None}],
        "opened": [{"title": "D", "url": "/d", "type": None}],
        "closed": [],
    }
    assert result["docs"] == [{"path": "planning/x.xlsx", "title": None, "change": "new"}]
    assert result["urls"] == ["/a", None, None, None, None]


def test_change_summaries_and_capping() -> None:
    result = run(
        """(() => {
          const pages = (n) => Array.from({length: n}, (_, i) => ({title: `P${i}`, url: null}))
          const empty = {added: [], changed: [], removed: [], opened: [], closed: []}
          return {
            full: m.changeSummary({added: pages(4), changed: pages(2), removed: pages(1),
                                   opened: pages(1), closed: pages(2)}),
            one: m.changeSummary({...empty, changed: pages(1)}),
            closedOnly: m.changeSummary({...empty, closed: pages(1)}),
            none: m.changeSummary(empty),
            count: m.changeCount({...empty, added: pages(3), closed: pages(1)}),
            rebuild: m.noChangeSentence("rebuild"),
            ingest: m.noChangeSentence("ingest"),
            capped: [m.capped(pages(12)), m.capped(pages(3)), m.capped(pages(10))]
              .map(({shown, more}) => [shown.length, more, m.andMore(more)]),
          }
        })()"""
    )
    assert result == {
        "full": "4 pages added · 2 changed · 1 removed · 1 contradiction opened · 2 closed",
        "one": "1 page changed",
        "closedOnly": "1 contradiction closed",
        "none": "",
        "count": 4,
        "rebuild": "This release rebuilt the site; no page changed.",
        "ingest": "No page changed in this release.",
        "capped": [[10, 2, "and 2 more"], [3, 0, ""], [10, 0, ""]],
    }


def test_run_at_work() -> None:
    result = run(
        """[
          m.runAtWork("compile"), m.runAtWork(null), m.runAtWork("mystery"),
          m.runDocumentsText([{path: "planning/a.xlsx", title: "PLN-2026-003 indice B"}]),
          m.runDocumentsText(["a", "b", "c", "d", "e"].map((path) => ({path, title: null}))),
          m.runDocumentsText([]),
        ]"""
    )
    assert result == [
        "Run at work: compile (step 4/13)",
        "Run at work",
        "Run at work: mystery",
        "1 document: PLN-2026-003 indice B",
        "5 documents: a, b, c, and 2 more",
        "",
    ]


def test_rows_are_planned_by_key() -> None:
    result = run(
        """{
          keys: m.rowKeys(["a", "hidden", "b", "hidden", "hidden"]),
          plan: m.planRows(
            [{key: "a", sig: "1"}, {key: "b", sig: "1"}, {key: "c", sig: "1"}],
            [{key: "c", sig: "1"}, {key: "a", sig: "2"}, {key: "d", sig: "1"}],
          ),
          first: m.planRows([], [{key: "a", sig: "1"}]),
        }"""
    )
    assert result == {
        "keys": ["a", "hidden", "b", "hidden#2", "hidden#3"],
        "plan": {
            "items": [
                {"key": "c", "action": "keep"},
                {"key": "a", "action": "update"},
                {"key": "d", "action": "insert"},
            ],
            "removed": ["b"],
        },
        "first": {"items": [{"key": "a", "action": "insert"}], "removed": []},
    }


def test_only_real_changes_are_announced() -> None:
    result = run(
        """(() => {
          const doc = (path, state, extra = {}) => ({path, title: null, state, phase: null,
            step: null, steps: 13, stage: null, hidden: false, ...extra})
          const before = [
            doc("planning/b.xlsx", "processing",
                {title: "PLN-2026-003 indice B", phase: "write", step: 4, stage: "compile"}),
            doc("devis/d.pdf", "processing", {phase: "check", step: 10, stage: "evidence"}),
            doc("achats/c.csv", "in_wiki"),
            doc("secret", "held_back", {hidden: true}),
          ]
          const after = [
            doc("planning/b.xlsx", "processing",
                {title: "PLN-2026-003 indice B", phase: "write", step: 5, stage: "entities"}),
            doc("devis/d.pdf", "in_wiki", {title: "Devis D"}),
            doc("achats/c.csv", "in_wiki"),
            doc("secret", "processing", {hidden: true}),
            doc("planning/new.xlsx", "received"),
          ]
          const moving = [doc("planning/b.xlsx", "processing",
                {title: "PLN-2026-003 indice B", phase: "check", step: 10, stage: "evidence"})]
          const many = ["a", "b", "c", "d", "e"].map((p) => doc(p, "failed"))
          return {
            first: m.announcements(null, after),
            next: m.announcements(before, after),
            phase: m.announcements(before.slice(0, 1), moving),
            capped: m.announcements([], many),
            words: ["queued", "superseded", "held_back", "failed", "removed"]
              .map((state) => m.docSentence(doc("x.pdf", state))),
          }
        })()"""
    )
    assert result == {
        "first": [],
        # The step moved inside the same phase: not announced. Hidden rows never are.
        "next": ["Devis D is in the wiki", "planning/new.xlsx received"],
        "phase": ["PLN-2026-003 indice B: Check and publish (step 10/13)"],
        "capped": ["a failed", "b failed", "c failed", "and 2 more changes"],
        "words": [
            "x.pdf is queued",
            "x.pdf is superseded",
            "x.pdf is held back",
            "x.pdf failed",
            "x.pdf was removed",
        ],
    }
