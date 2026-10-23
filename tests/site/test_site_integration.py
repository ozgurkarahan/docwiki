"""Real Quartz build of the mock release (slow, needs git, Node 22+ and network on first run).

Run with ``DOCWIKI_SITE_BUILD=1 uv run pytest tests/site/test_site_integration.py -s``
(``true`` works too: the same setting enables site builds in the pipeline).
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path

import pytest
from site_testkit import (
    MINUTES_PAGE,
    MOCK_RELEASE,
    MOCK_RELEASE_DIR,
    MOCK_RELEASE_ID,
    PLAN_A,
    PLAN_A_PAGE,
    PLAN_B,
    PLAN_B_PAGE,
    make_portable,
    make_scoped,
)

from docwiki.site import (
    REPO_URL,
    build_site,
    check_links,
    default_allowed_hosts,
    resolve_site_path,
    scan_site,
)
from docwiki.site.html import parse_html

pytestmark = pytest.mark.skipif(
    os.environ.get("DOCWIKI_SITE_BUILD", "").strip().lower() not in {"1", "true", "yes"},
    reason="set DOCWIKI_SITE_BUILD=1 to build the site with the pinned Quartz",
)

BASE_URL = "docwiki.example.com"


@pytest.fixture(scope="module")
def built_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    out = tmp_path_factory.mktemp("site") / "public"
    started = time.monotonic()
    build_site(MOCK_RELEASE, out, base_url=BASE_URL, log=print)
    files = [p for p in out.rglob("*") if p.is_file()]
    size = sum(p.stat().st_size for p in files)
    print(
        f"\nsite build: {time.monotonic() - started:.1f} s, {len(files)} files, "
        f"{size / 1024:.0f} KiB"
    )
    return out


def html(site: Path, rel: str) -> str:
    return (site / rel).read_text(encoding="utf-8")


def test_every_link_and_anchor_resolves(built_site: Path) -> None:
    report = check_links(built_site)
    print(report.summary())
    assert report.ok, report.problems
    assert report.pages >= 30 and report.links > 500


def test_security_scan_is_clean(built_site: Path) -> None:
    findings = scan_site(
        built_site, default_allowed_hosts(BASE_URL, REPO_URL), canaries=["DOCWIKI-CANARY"]
    )
    assert findings == []


def test_every_footnote_opens_an_existing_evidence_sidecar(built_site: Path) -> None:
    checked = 0
    for page in built_site.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        for section in re.findall(r"<section data-footnotes.*?</section>", text, re.DOTALL):
            for tag in parse_html(section):
                href = tag.get("href") or ""
                if tag.name != "a" or tag.get("data-footnote-backref") is not None:
                    continue
                if href.startswith("#"):
                    continue
                assert "evidence/src-" in href, f"{page}: footnote outside evidence: {href}"
                target = (page.parent / f"{href.split('#')[0]}.html").resolve()
                assert target.is_file(), f"{page}: {href}"
                assert target.is_relative_to((built_site / "evidence").resolve())
                checked += 1
    print(f"footnote links to evidence sidecars: {checked}")
    wiki = MOCK_RELEASE_DIR / "wiki"
    definitions = sum(
        len(re.findall(r"^\[\^c\d+\]: ", md.read_text(encoding="utf-8"), re.MULTILINE))
        for md in wiki.rglob("*.md")
        if not md.relative_to(wiki).as_posix().startswith(".")
    )
    assert checked == definitions > 0


def test_pages_render_the_docwiki_overlay(built_site: Path) -> None:
    source = html(built_site, f"{MINUTES_PAGE}.html")
    assert "Referenced by" not in source  # DocWiki backlinks block stripped
    assert "docwiki:backlinks" not in source
    assert source.count('<h1 class="article-title">') == 1  # body title deduplicated
    assert 'class="docwiki-badge docwiki-badge--verified"' in source
    assert 'class="docwiki-badge-legend"' in source
    assert 'class="docwiki-banner"' in source
    assert "docwiki-notice--fictional" in source
    topic = html(built_site, "topics/schedule-and-window-delivery.html")
    assert "docwiki-badge--table" in topic
    superseded = html(built_site, f"{PLAN_A_PAGE}.html")
    assert "docwiki-notice--superseded" in superseded
    home = html(built_site, "index.html")
    assert "About DocWiki" in home and REPO_URL in home
    assert "About DocWiki" not in source
    # one fictional notice on the home page (the site banner); the provenance line comes first
    assert 'class="docwiki-banner"' in home and "docwiki-notice--fictional" not in home
    assert 'class="docwiki-about"' in home and "Compiled by" in home
    assert "quality gates: 12 passed, 4 skipped" in home and "quality report" in home
    assert home.index('class="docwiki-about"') < home.index('id="how-to-navigate"')
    # the story first: the pattern, documents → pipeline → cited pages, a question to try
    assert 'class="docwiki-story"' in home and "docwiki-story" not in source
    assert home.index('class="docwiki-story"') < home.index('class="docwiki-about"')
    assert "3 documents" in home and "13-step pipeline" in home and "8 cited pages" in home
    assert 'href="./documents"' in home and 'href="./pipeline"' in home
    assert 'href="#docwiki-wiki"' in home and 'id="docwiki-wiki"' in home
    assert 'data-question="When are the windows of the extension delivered?"' in home
    assert home.index('id="docwiki-wiki"') < home.index('id="how-to-navigate"')


def test_evidence_microscope_pages(built_site: Path) -> None:
    pdf = html(built_site, f"evidence/{PLAN_A}/p0001.html")
    assert 'class="docwiki-specimen"' in pdf and "docwiki-zoom" in pdf
    assert "docwiki-verbatim" in pdf
    assert (built_site / "evidence" / PLAN_A / "img" / "p0001.png").is_file()
    rows = html(built_site, f"evidence/{PLAN_B}/sheet-planning-r0006-r0009.html")
    assert all(f'id="row-{n}"' in rows for n in (6, 7, 8, 9))
    assert f'href="../../{PLAN_B_PAGE}"' in rows


def test_no_third_party_requests_or_analytics(built_site: Path) -> None:
    for page in built_site.rglob("*.html"):
        text = page.read_text(encoding="utf-8")
        assert "fonts.googleapis" not in text and "cdnjs" not in text, page
        scripts = [tag for tag in parse_html(text) if tag.name == "script"]
        assert scripts and all(tag.get("src") for tag in scripts), f"inline script in {page}"
    css = html(built_site, "index.css")
    assert "fonts.g" not in css and "@import" not in css
    for name in ("plausible", "googletagmanager", "umami"):
        assert name not in html(built_site, "postscript.js")
    assert not (built_site / "static" / "giscus").exists()


def test_ask_panel_on_every_page(built_site: Path) -> None:
    """ADR 0007: the drawer's button and empty panel on every page, its data next to them."""
    payload = json.loads(html(built_site, "static/docwiki/answers.json"))
    assert payload["schema"] == 1 and payload["release"] == MOCK_RELEASE_ID
    [answer] = payload["answers"]
    files = {p.relative_to(built_site).as_posix() for p in built_site.rglob("*") if p.is_file()}
    targets = [answer["slug"], *(c["href"] for c in answer["citations"]), *answer["pages"]]
    for target in targets:
        assert resolve_site_path(files, target.partition("#")[0]), f"no page for {target}"
    pages = 0
    for page in sorted(built_site.rglob("*.html")):
        rel = page.relative_to(built_site).as_posix()
        text = page.read_text(encoding="utf-8")
        tags = parse_html(text)
        fabs = [t for t in tags if t.name == "button" and t.get("class") == "docwiki-ask-fab"]
        panels = [t for t in tags if t.name == "aside" and t.get("id") == "docwiki-ask"]
        if rel == "404.html":  # served at any path: no relative links there
            assert not fabs and not panels
            continue
        assert len(fabs) == 1 and len(panels) == 1, rel
        assert fabs[0].get("aria-expanded") == "false"
        assert fabs[0].get("aria-controls") == "docwiki-ask"
        attrs = dict(panels[0].attrs)
        assert "hidden" in attrs and attrs["aria-label"] == "Ask this wiki", rel
        assert attrs["data-repo-url"] == REPO_URL
        assert re.search(r'<aside id="docwiki-ask"[^>]*></aside>', text), f"panel not empty: {rel}"
        pages += 1
    assert pages >= 30
    postscript = html(built_site, "postscript.js")
    assert "static/docwiki/answers.json" in postscript and "docwiki-ask" in postscript


def test_open_drawer_keeps_the_article_readable(built_site: Path) -> None:
    """The open drawer pushes the page above 1200 px and collapses on a link up to it."""
    css = re.sub(r"\s+", "", html(built_site, "index.css"))
    drawer = re.search(r"\.docwiki-ask\{[^}]*?width:min\((\d+)px,100vw\)", css)
    push = re.search(
        r"@mediascreenand\(min-width:(\d+)px\)\{\.page:has\(\.docwiki-ask:not\(\[hidden\]\)\)"
        r"\{margin-right:max\((\d+)px\+2rem,",
        css,
    )
    assert drawer and push, "the drawer width or the push rule is missing from index.css"
    assert int(push.group(1)) == 1201  # Quartz's tablet layout ends at 1200 px included
    assert int(push.group(2)) == int(drawer.group(1)) - 320  # Quartz's right-hand panel
    assert "(max-width: 1200px)" in html(built_site, "postscript.js")  # NARROW_QUERY


def test_phone_header_title_shrinks_and_wraps(built_site: Path) -> None:
    """On phones the title gives way so that the header row never widens the page."""
    css = re.sub(r"\s+", "", html(built_site, "index.css"))
    rule = re.search(
        r"@media\(max-width:800px\)\{\.sidebar\.left\.page-title\{([^}]*)\}([^@]*)", css
    )
    assert rule, "the phone title rule is missing from index.css"
    assert "min-width:0" in rule.group(1)
    assert ".sidebar.left.page-titlea{overflow-wrap:anywhere}" in rule.group(2)
    # The open phone menu covers the screen (fixed, not inset by the page padding) and its list
    # starts below the menu button, which sits at the top of the header row.
    assert ".sidebar.left.explorer{margin-top:0}" in rule.group(2)
    menu = re.search(r"\.explorer\.explorer-content\{([^}]*)\}", rule.group(2))
    assert menu and "position:fixed" in menu.group(1) and "padding-left:1rem" in menu.group(1)


@pytest.fixture(scope="module")
def built_portable_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("portable")
    wiki = make_portable(root / "wiki")
    out = root / "public"
    started = time.monotonic()
    build_site(wiki, out, base_url=BASE_URL, log=print)
    print(f"\nportable site build: {time.monotonic() - started:.1f} s")
    return out


def test_portable_folder_builds_the_same_site(built_site: Path, built_portable_site: Path) -> None:
    def pages(root: Path) -> set[str]:
        return {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}

    assert pages(built_portable_site) == pages(built_site)
    assert check_links(built_portable_site).ok
    allowed = default_allowed_hosts(BASE_URL, REPO_URL)
    assert scan_site(built_portable_site, allowed) == []
    assert not (built_portable_site / ".docwiki").exists()
    assert html(built_portable_site, f"{PLAN_B_PAGE}.html") == html(
        built_site, f"{PLAN_B_PAGE}.html"
    )


def _explorer_fns(page: str) -> dict[str, str]:
    found = re.search(r'data-data-fns="([^"]*)"', page)
    assert found, "explorer functions"
    return json.loads(found.group(1).replace("&quot;", '"').replace("&amp;", "&"))


def test_register_and_explorer_without_scopes(built_site: Path) -> None:
    documents = html(built_site, "documents.html")
    assert "docwiki-documents-list" in documents and "docwiki-documents-scope" not in documents
    fns = _explorer_fns(documents)
    assert "const hubs = []" in fns["sortFn"] and "const entitiesTitle = null" in fns["mapFn"]


@pytest.fixture(scope="module")
def built_scoped_site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("scoped")
    release = make_scoped(root / "release")
    out = root / "public"
    started = time.monotonic()
    build_site(release, out, base_url=BASE_URL, log=print)
    print(f"\nscoped site build: {time.monotonic() - started:.1f} s")
    return out


def test_scoped_register_and_explorer(built_scoped_site: Path) -> None:
    """v1.7 (ADR 0011): the register by chantier, phase and type; hubs first in the explorer."""
    documents = html(built_scoped_site, "documents.html")
    scopes = re.findall(r'<h2 class="docwiki-documents-scope-title">(.*?)</h2>', documents)
    assert len(scopes) == 2
    assert 'href="./chantiers/moreau"' in scopes[0] and "Chantier Moreau" in scopes[0]
    assert "2 documents" in scopes[0]
    assert scopes[1].startswith("Entreprise") and "1 document" in scopes[1]
    assert '<h3 class="docwiki-documents-phase-title">Phase 3</h3>' in documents
    assert '<h4 class="docwiki-documents-type-title">Schedule</h4>' in documents
    assert documents.index("indice A") < documents.index("indice B")
    fns = _explorer_fns(documents)
    assert 'const hubs = ["chantiers"]' in fns["sortFn"]
    assert 'const entitiesTitle = "Entreprise"' in fns["mapFn"]
    assert (built_scoped_site / "chantiers" / "moreau.html").is_file()
    assert check_links(built_scoped_site).ok
