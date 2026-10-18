"""Real Quartz build of the mock release (slow, needs git, Node 22+ and network on first run).

Run with ``DOCWIKI_SITE_BUILD=1 uv run pytest tests/site/test_site_integration.py -s``
(``true`` works too: the same setting enables site builds in the pipeline).
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import pytest
from site_testkit import MOCK_RELEASE, make_portable

from docwiki.site import REPO_URL, build_site, check_links, default_allowed_hosts, scan_site
from docwiki.site.html import parse_html

pytestmark = pytest.mark.skipif(
    os.environ.get("DOCWIKI_SITE_BUILD", "").strip().lower() not in {"1", "true", "yes"},
    reason="set DOCWIKI_SITE_BUILD=1 to build the site with the pinned Quartz",
)

BASE_URL = "docwiki.ozgurkarahan.com"


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
    wiki = MOCK_RELEASE / "releases" / "20260215T090000Z-decd4b59" / "wiki"
    definitions = sum(
        len(re.findall(r"^\[\^c\d+\]: ", md.read_text(encoding="utf-8"), re.MULTILINE))
        for md in wiki.rglob("*.md")
        if not md.relative_to(wiki).as_posix().startswith(".")
    )
    assert checked == definitions > 0


def test_pages_render_the_docwiki_overlay(built_site: Path) -> None:
    source = html(built_site, "sources/sop-gbx-010-rev-b.html")
    assert "Referenced by" not in source  # DocWiki backlinks block stripped
    assert "docwiki:backlinks" not in source
    assert source.count('<h1 class="article-title">') == 1  # body title deduplicated
    assert 'class="docwiki-badge docwiki-badge--verified"' in source
    assert 'class="docwiki-badge-legend"' in source
    assert 'class="docwiki-banner"' in source
    assert "docwiki-notice--fictional" in source
    topic = html(built_site, "topics/gearbox-oil.html")
    assert "docwiki-badge--table" in topic
    superseded = html(built_site, "sources/sop-gbx-010-rev-a.html")
    assert "docwiki-notice--superseded" in superseded
    home = html(built_site, "index.html")
    assert "About DocWiki" in home and REPO_URL in home
    assert "About DocWiki" not in source


def test_evidence_microscope_pages(built_site: Path) -> None:
    pdf = html(built_site, "evidence/src-f2750f41f3fa/p0001.html")
    assert 'class="docwiki-specimen"' in pdf and "docwiki-zoom" in pdf
    assert "docwiki-verbatim" in pdf
    assert (built_site / "evidence" / "src-f2750f41f3fa" / "img" / "p0001.png").is_file()
    rows = html(built_site, "evidence/src-43c97f7dfcde/sheet-plan-r0002-r0004.html")
    assert all(f'id="row-{n}"' in rows for n in (2, 3, 4))
    assert 'href="../../sources/maintenance-plan-2026"' in rows


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
    assert html(built_portable_site, "sources/sop-gbx-010-rev-b.html") == html(
        built_site, "sources/sop-gbx-010-rev-b.html"
    )
