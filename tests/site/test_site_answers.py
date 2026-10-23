"""``answers.json`` for the "Ask this wiki" drawer (ADR 0007), built from ``queries/`` pages."""

from __future__ import annotations

import json
import re
import shutil
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest
from site_testkit import MOCK_RELEASE, MOCK_RELEASE_DIR, OVERLAY, FakeTools, make_portable

from docwiki.contracts.pages import Page
from docwiki.site import (
    ANSWERS_SITE_PATH,
    SiteBuildError,
    answer_for_page,
    build_answers,
    build_site,
    notice_kind,
    open_release,
    query_pages,
    site_settings,
    write_answers,
)

RELEASE_ID = "20260401T090000Z-8a41b109"
MOCK_QUERY = "queries/2026-03-31-window-delivery-date"
SIDECARS = (
    "evidence/src-f0757603684a/para-0011",
    "evidence/src-59cf9366e50c/sheet-planning-r0006-r0009",
)
COMPONENT_DIR = OVERLAY / "quartz" / "components" / "docwiki"


def frontmatter(
    query_id: str,
    question: str,
    *,
    day: str,
    sources: tuple[str, ...] = (),
    page_type: str = "query",
) -> str:
    listed = "".join(f"\n- {source}" for source in sources) or " []"
    return (
        f"---\nid: {query_id}\ntype: {page_type}\ntitle: {question}\nsummary: A filed answer.\n"
        f"lang: en\nsensitivity: public\nupdated: {day}\ntags: []\n"
        f"docwiki:\n  schema: 1\n  release: {RELEASE_ID}\n"
        f"question: {question}\nasked_by: human\nsources:{listed}\napproved_by: owner\n---\n"
    )


SUPERSEDED_QUESTION = "Which date does the revised schedule give for the windows of lot 5?"
SUPERSEDED_PAGE = frontmatter(
    "query:2026-04-02-windows-lot-5",
    SUPERSEDED_QUESTION,
    day="2026-04-02",
    sources=("src-59cf9366e50c", "src-7630d0741377"),
) + (
    f"\n# {SUPERSEDED_QUESTION}\n\n"
    "> **Superseded:** this answer cites [Planning and purchase tracking, indice A]"
    "(../sources/pln-2026-003-indice-a-planning-et-suivi-des-achats.md), superseded by "
    "[Planning and purchase tracking, indice B]"
    "(../sources/pln-2026-003-indice-b-planning-et-suivi-des-achats.md). Check the current "
    "revision.\n\n"
    "> **Warning:** this answer cited sources that were withdrawn; their citations were "
    "removed.\n\n"
    "> FICTIONAL - NOT FOR OPERATIONAL USE. Sample content about a fictional building job.\n\n"
    "The *revised schedule* plans the **delivery** for "
    "[lot 5](../entities/work-package/lot-5-menuiseries-exterieures.md), written `T07`.[^c1]\n"
    "Indice A gave an earlier date.[^c2] <!-- reviewer note -->\n\n"
    "- Planning rows 6–9[^c1]\n"
    "- Indice A, page 1\n\n"
    "1. Check the schedule\n"
    "2. Check the minutes[^c9]\n\n"
    "## How this answer was produced\n\n"
    "Answered by the Researcher agent (`docwiki-researcher` version 3) on 2026-04-02 from "
    f"release `{RELEASE_ID}`, then reviewed and filed by the owner on 2026-04-02. The agent "
    "made 2 tool calls:\n\n"
    "- search `window delivery T07`\n"
    "- read_page `topics/planning.md`\n\n"
    "## Sources\n\n"
    '[^c1]: [Planning and purchase tracking, indice B — sheet "Planning", rows 6–9]'
    "(../evidence/src-59cf9366e50c/sheet-planning-r0006-r0009.md) · table\n"
    "[^c2]: [Planning and purchase tracking, indice A — p. 1]"
    "(../evidence/src-7630d0741377/p0001.md) · ✓ quote verified\n"
)
NOT_FOUND_QUESTION = "What energy-performance rating (DPE) will the house have after the works?"
NOT_FOUND_PAGE = frontmatter(
    "query:2026-04-02-dpe-rating", NOT_FOUND_QUESTION, day="2026-04-02"
) + (
    f"\n# {NOT_FOUND_QUESTION}\n\nNot found in the wiki.\n\n"
    "## How this answer was produced\n\nNo source of that release answers the question.\n"
)
QUERIES_INDEX = (
    "---\nid: index:queries\ntype: index\ntitle: Queries\nsummary: Filed answers.\nlang: en\n"
    f"sensitivity: public\nupdated: 2026-04-02\ntags: []\n"
    f"docwiki:\n  schema: 1\n  release: {RELEASE_ID}\n---\n\n# Queries\n\n"
    f"- [{SUPERSEDED_QUESTION}](2026-04-02-windows-lot-5.md)\n"
)


def release_with(tmp_path: Path, pages: dict[str, str]) -> Path:
    """A copy of the mock release with extra wiki pages (``path → text``)."""
    release = tmp_path / "release"
    shutil.copytree(MOCK_RELEASE_DIR, release)
    for rel, text in pages.items():
        (release / "wiki" / rel).write_text(text, encoding="utf-8")
    return release


def settings_of(location: Path, **extra: object) -> dict[str, object]:
    return site_settings(
        open_release(location),
        base_url=None,
        page_title=None,
        banner=None,
        repo_url="https://github.com/ozgurkarahan/docwiki",
        quartz_version="v4.5.2",
        **extra,  # type: ignore[arg-type]
    )


def test_answers_of_the_mock_release() -> None:
    payload = build_answers(open_release(MOCK_RELEASE))
    assert payload["schema"] == 1 and payload["release"] == RELEASE_ID
    [answer] = payload["answers"]
    assert answer["id"] == "query:2026-03-31-window-delivery-date"
    assert answer["slug"] == MOCK_QUERY
    assert answer["question"] == "When are the windows of the extension delivered?"
    assert answer["date"] == "2026-04-01"
    assert answer["banners"] == []  # the fictional stamp is the site banner's job
    assert answer["paragraphs"] == [
        [
            {
                "text": "On 2026-04-20. Indice B of the schedule PLN-2026-003 plans the delivery "
                "of the windows (task T07) on that date and their installation from 2026-04-21 "
                "to 2026-04-23."
            },
            {"cite": 1},
            {
                "text": " The minutes of site meeting n°3 record the postponement from 2026-03-30 "
                "to 2026-04-20."
            },
            {"cite": 2},
            {"text": " Indice A, now superseded, still showed 2026-03-30."},
            {"cite": 3},
        ]
    ]
    assert answer["citations"] == [
        {
            "n": 1,
            "title": "Planning and purchase tracking, indice B",
            "label": 'sheet "Planning", rows 6–9',
            "href": "evidence/src-59cf9366e50c/sheet-planning-r0006-r0009",
            "badge": "table",
        },
        {
            "n": 2,
            "title": "Site meeting minutes n°3",
            "label": "¶ 11",
            "href": "evidence/src-f0757603684a/para-0011",
            "badge": "✓ quote verified",
        },
        {
            "n": 3,
            "title": "Planning and purchase tracking, indice A",
            "label": "p. 1",
            "href": "evidence/src-7630d0741377/p0001",
            "badge": "✓ quote verified",
        },
    ]
    assert answer["steps"] == [
        'search "date de livraison des fenêtres"',
        "get_evidence src-59cf9366e50c/sheet-planning-r0006-r0009",
    ]
    assert answer["provenance"] == (
        "The Researcher searched the wiki in French for the delivery date of the windows, then "
        "opened the evidence of the cited schedule rows before answering."
    )
    assert answer["pages"] == [
        MOCK_QUERY,
        "evidence/src-59cf9366e50c/sheet-planning-r0006-r0009",
        "evidence/src-f0757603684a/para-0011",
        "evidence/src-7630d0741377/p0001",
        "sources/pln-2026-003-indice-b-planning-et-suivi-des-achats",
        "sources/pln-2026-003-indice-a-planning-et-suivi-des-achats",
        "sources/2026-03-24-compte-rendu-de-chantier-n3",
        "topics/planning",
        "entities/organisation/vanarsdel-menuiseries",
        "entities/work-package/lot-3-gros-oeuvre",
        "entities/work-package/lot-5-menuiseries-exterieures",
    ]


def test_banners_inline_markdown_steps_and_order(tmp_path: Path) -> None:
    release = release_with(
        tmp_path,
        {
            "queries/2026-04-02-windows-lot-5.md": SUPERSEDED_PAGE,
            "queries/2026-04-02-dpe-rating.md": NOT_FOUND_PAGE,
            "queries/index.md": QUERIES_INDEX,
        },
    )
    answers = build_answers(open_release(release))["answers"]
    # newest first, then by question; queries/index.md is not an answer
    assert [answer["question"] for answer in answers] == [
        NOT_FOUND_QUESTION,
        SUPERSEDED_QUESTION,
        "When are the windows of the extension delivered?",
    ]
    not_found, filed = answers[0], answers[1]
    assert not_found["paragraphs"] == [[{"text": "Not found in the wiki."}]]
    assert not_found["citations"] == [] and not_found["steps"] == []
    assert not_found["provenance"] == "No source of that release answers the question."
    assert not_found["pages"] == ["queries/2026-04-02-dpe-rating"]

    assert filed["banners"] == [
        "Superseded: this answer cites Planning and purchase tracking, indice A, superseded by "
        "Planning and purchase tracking, indice B. Check the current revision.",
        "Warning: this answer cited sources that were withdrawn; their citations were removed.",
    ]
    assert filed["paragraphs"] == [
        [
            {"text": "The revised schedule plans the delivery for lot 5, written T07."},
            {"cite": 1},
            {"text": " Indice A gave an earlier date."},
            {"cite": 2},
        ],
        [{"text": "• Planning rows 6–9"}, {"cite": 1}],
        [{"text": "• Indice A, page 1"}],
        [{"text": "1. Check the schedule"}],
        [{"text": "2. Check the minutes"}],  # [^c9] has no definition
    ]
    assert filed["steps"] == [
        'search "window delivery T07"',
        "read_page topics/planning.md",
    ]
    assert filed["provenance"] == (
        "Answered by the Researcher agent (docwiki-researcher version 3) on 2026-04-02 from "
        f"release {RELEASE_ID}, then reviewed and filed by the owner on 2026-04-02. The agent "
        "made 2 tool calls:"
    )
    assert [(c["n"], c["label"], c["href"], c["badge"]) for c in filed["citations"]] == [
        (
            1,
            'sheet "Planning", rows 6–9',
            "evidence/src-59cf9366e50c/sheet-planning-r0006-r0009",
            "table",
        ),
        (2, "p. 1", "evidence/src-7630d0741377/p0001", "✓ quote verified"),
    ]
    assert filed["pages"] == [
        "queries/2026-04-02-windows-lot-5",
        "evidence/src-59cf9366e50c/sheet-planning-r0006-r0009",
        "evidence/src-7630d0741377/p0001",
        "sources/pln-2026-003-indice-b-planning-et-suivi-des-achats",
        "sources/pln-2026-003-indice-a-planning-et-suivi-des-achats",
        "topics/planning",
        "entities/organisation/vanarsdel-menuiseries",
        "entities/work-package/lot-3-gros-oeuvre",
        "entities/work-package/lot-5-menuiseries-exterieures",
    ]
    assert settings_of(release)["answers"] == 3


@pytest.mark.parametrize(
    ("section", "provenance", "steps"),
    [
        ("", "", []),
        ("## How this answer was produced\n\n- search `window`\n", "", ["search window"]),
        (
            "## How this answer was produced\n\nAnswered by the *Researcher* agent "
            "([`docwiki-researcher`](../AGENTS.md) version 7)\non 2026-10-20.[^c1]\n\n"
            "Reviewed by the owner.\n\n- search `window date`\n\nA note after the steps.\n",
            "Answered by the Researcher agent (docwiki-researcher version 7) on 2026-10-20. "
            "Reviewed by the owner.",
            ['search "window date"'],
        ),
        ("## Related\n\nA paragraph of another section.\n", "", []),
    ],
)
def test_provenance_is_the_paragraphs_under_the_heading(
    section: str, provenance: str, steps: list[str]
) -> None:
    text = frontmatter("query:2026-04-02-window", "Which window?", day="2026-04-02") + (
        f"\n# Which window?\n\nDue 2026-04-20.\n\n{section}"
    )
    page = Page.parse(text, "queries/2026-04-02-window.md")
    answer = answer_for_page(page, open_release(MOCK_RELEASE).catalog)
    assert answer["provenance"] == provenance
    assert answer["steps"] == steps
    assert answer["paragraphs"] == [[{"text": "Due 2026-04-20."}]]


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("Text.[^c1]\n\n## Sources\n\n[^c1]: see the plan\n", "is not a citation"),
        (
            "Text.[^c1]\n\n## Sources\n\n"
            "[^c1]: [Planning — sheet]"
            "(../sources/pln-2026-003-indice-b-planning-et-suivi-des-achats.md) · table\n",
            "does not open an evidence sidecar",
        ),
        (
            "Text.[^c1]\n\n## Sources\n\n"
            "[^c1]: [Planning — sheet](https://example.org/planning) · table\n",
            "does not open an evidence sidecar",
        ),
    ],
)
def test_malformed_citations_fail_the_build(tmp_path: Path, body: str, message: str) -> None:
    page = frontmatter("query:2026-04-02-broken", "Broken?", day="2026-04-02") + body
    release = release_with(tmp_path, {"queries/2026-04-02-broken.md": page})
    with pytest.raises(SiteBuildError, match=message):
        build_answers(open_release(release))


def test_other_pages_in_queries_fail_the_build(tmp_path: Path) -> None:
    topic = MOCK_RELEASE_DIR / "wiki" / "topics" / "planning.md"
    release = release_with(tmp_path, {"queries/window-delivery.md": topic.read_text("utf-8")})
    with pytest.raises(SiteBuildError, match="a topic page in queries/"):
        build_answers(open_release(release))
    (release / "wiki" / "queries" / "window-delivery.md").write_text("# No frontmatter\n", "utf-8")
    with pytest.raises(SiteBuildError, match="is not a valid query page"):
        build_answers(open_release(release))


def test_a_wiki_without_answers(tmp_path: Path) -> None:
    portable = make_portable(tmp_path / "wiki")
    shutil.rmtree(portable / "queries")
    assert query_pages(portable) == []
    assert build_answers(open_release(portable)) == {
        "schema": 1,
        "release": RELEASE_ID,
        "answers": [],
    }
    assert settings_of(portable)["answers"] == 0
    assert settings_of(MOCK_RELEASE)["answers"] == 1
    assert settings_of(MOCK_RELEASE, answers=7)["answers"] == 7


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("FICTIONAL - NOT FOR OPERATIONAL USE.", "fictional"),
        ("  Superseded: this answer cites a revision.", "superseded"),
        ("FICTIONAL SAMPLE - every name in this wiki is invented.", "fictional"),
        ("Superseded by Planning and purchase tracking, indice B.", "superseded"),
        ("WARNING: withdrawn sources.", "warning"),
        ("Withdrawn source.", "warning"),
        ("Fictional characters appear here.", None),
        ("Supersededness", None),
        ("The procedure was superseded.", None),
    ],
)
def test_notice_kind(text: str, kind: str | None) -> None:
    assert notice_kind(text) == kind


def test_write_answers_is_utf8_with_lf(tmp_path: Path) -> None:
    payload = build_answers(open_release(MOCK_RELEASE))
    target = write_answers(payload, tmp_path / "quartz-checkout")
    assert target == tmp_path / "quartz-checkout" / "quartz" / ANSWERS_SITE_PATH
    data = target.read_bytes()
    assert b"\r" not in data and data.endswith(b"}\n")
    assert "✓ quote verified".encode() in data  # not escaped
    assert json.loads(data) == payload


def test_build_site_publishes_the_answers(tmp_path: Path, tools: FakeTools) -> None:
    cache = tmp_path / "cache"
    build_site(MOCK_RELEASE, tmp_path / "out", cache_dir=cache, runner=tools, env={})
    checkout = cache / "v4.5.2"
    written = json.loads((checkout / "quartz" / ANSWERS_SITE_PATH).read_text(encoding="utf-8"))
    assert written == build_answers(open_release(MOCK_RELEASE))
    settings = json.loads((checkout / "docwiki-site.json").read_text(encoding="utf-8"))
    assert settings["answers"] == 1
    assert (checkout / "quartz" / "components" / "docwiki" / "AskPanel.tsx").is_file()
    inline = checkout / "quartz" / "components" / "docwiki" / "scripts" / "askPanel.inline.ts"
    assert inline.is_file()


def test_a_bad_query_page_fails_before_quartz_runs(tmp_path: Path, tools: FakeTools) -> None:
    page = frontmatter("query:2026-04-02-broken", "Broken?", day="2026-04-02") + (
        "Text.[^c1]\n\n## Sources\n\n[^c1]: see the plan\n"
    )
    release = release_with(tmp_path, {"queries/2026-04-02-broken.md": page})
    with pytest.raises(SiteBuildError, match="is not a citation"):
        build_site(release, tmp_path / "out", cache_dir=tmp_path / "cache", runner=tools, env={})
    assert tools.commands == []


def test_an_answer_filed_by_the_answers_lane_reaches_the_drawer(tmp_path: Path) -> None:
    """The query page written by ``docwiki.answers.build_query_page`` (ADR 0007 filing path)."""
    filing = pytest.importorskip("docwiki.answers")
    minutes, plan = SIDECARS
    researcher = SimpleNamespace(
        text=(
            "The windows of the extension are delivered on 2026-04-20 [1]. Their installation is "
            "planned from 2026-04-21 to 2026-04-23 [2].\n\nSources:\n"
            f"[1] Site meeting minutes n°3 — ¶ 11 (native-text) — {minutes}.md\n"
            f"[2] Planning and purchase tracking, indice B — rows 6–9 (deterministic-table) — "
            f"{plan}.md\n"
        ),
        sources=None,
        tool_calls=[
            SimpleNamespace(name="search", arguments={"query": "window delivery date"}, status=""),
            SimpleNamespace(
                name="read_page", arguments={"path": "topics/planning.md"}
            ),
        ],
        agent="docwiki-researcher",
        version="7",
        latency_s=21.4,
    )
    filed = filing.build_query_page(
        researcher,
        question="When are the windows delivered?",
        release=filing.FolderRelease(MOCK_RELEASE_DIR),
        filed_on=date(2026, 10, 20),
    ).page
    release = release_with(tmp_path, {filed.path: filed.render()})
    newest = build_answers(open_release(release))["answers"][0]
    assert newest["slug"] == filed.path.removesuffix(".md")
    assert newest["question"] == "When are the windows delivered?"
    assert newest["date"] == "2026-10-20" and newest["banners"] == []
    assert newest["paragraphs"] == [
        [
            {"text": "The windows of the extension are delivered on 2026-04-20"},
            {"cite": 1},
            {"text": ". Their installation is planned from 2026-04-21 to 2026-04-23"},
            {"cite": 2},
            {"text": "."},
        ]
    ]
    assert [(c["n"], c["href"]) for c in newest["citations"]] == [(1, minutes), (2, plan)]
    assert all(c["title"] and c["label"] and c["badge"] for c in newest["citations"])
    assert newest["steps"] == [
        'search "window delivery date"',
        "read_page topics/planning.md",
    ]
    provenance = newest["provenance"]
    assert provenance.startswith(
        "Answered by the Researcher agent (docwiki-researcher version 7) on 2026-10-20 from "
        f"release {RELEASE_ID}, then reviewed and filed by the owner on 2026-10-20. "
        "Numbers checked against the cited evidence: "
    )
    assert provenance.endswith(" The agent made 2 tool calls in 21 s:")
    assert "`" not in provenance and "\n" not in provenance
    expected = {
        "topics/planning",
        "entities/work-package/lot-5-menuiseries-exterieures",
        minutes,
        plan,
    }
    assert expected <= set(newest["pages"])


def test_the_drawer_renders_with_dom_apis_only() -> None:
    """Answers are data: no HTML parsing, no code from strings (site.md §6, ADR 0007)."""
    script = (COMPONENT_DIR / "scripts" / "askPanel.inline.ts").read_text(encoding="utf-8")
    component = (COMPONENT_DIR / "AskPanel.tsx").read_text(encoding="utf-8")
    for source in (script, component):
        for forbidden in (
            "innerHTML",
            "outerHTML",
            "insertAdjacentHTML",
            "dangerouslySetInnerHTML",
            "document.write",
            "eval(",
            "new Function",
            "setAttribute(\"style\"",
        ):
            assert forbidden not in source, forbidden
    # Quartz's inline-script loader deletes the first "export" of the file it bundles.
    assert "export" not in script
    assert "textContent" in script and "sessionStorage" in script


def test_the_drawer_is_always_built_and_the_client_decides_whether_to_show_it() -> None:
    """ADR 0008: the button is on every page, hidden when there is nothing to ask or read."""
    script = (COMPONENT_DIR / "scripts" / "askPanel.inline.ts").read_text(encoding="utf-8")
    component = (COMPONENT_DIR / "AskPanel.tsx").read_text(encoding="utf-8")
    assert "return null" in component and component.count("return null") == 1  # the 404 page
    assert "hidden={settings.answers === 0}" in component
    assert "data-filed-answers={String(settings.answers)}" in component
    # Every request of the drawer is relative to the current page: no absolute URL is fetched.
    calls = re.findall(r"fetch\(([^,)]*)", script)
    assert calls and all(call.startswith(("relativeHref(", "target")) for call in calls)
