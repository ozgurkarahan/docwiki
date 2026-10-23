"""Real Quartz build of a two-language release (ADR 0012, slice G): French canonical pages at the
root, the English mirror under ``en/``.

Run with ``DOCWIKI_SITE_BUILD=1 uv run pytest tests/site/test_site_bilingual.py -s``.
"""

from __future__ import annotations

import html as html_lib
import json
import os
import re
from pathlib import Path

import pytest
from site_testkit import (
    FR_HOME_TITLE,
    FR_MINUTES_TITLE,
    MINUTES,
    MINUTES_PAGE,
    MOCK_TITLE,
    PLAN_A_PAGE,
    UNTRANSLATED_SUMMARY,
    make_bilingual,
    make_untranslated,
)

from docwiki.site import REPO_URL, build_site, check_links, default_allowed_hosts, scan_site

pytestmark = pytest.mark.skipif(
    os.environ.get("DOCWIKI_SITE_BUILD", "").strip().lower() not in {"1", "true", "yes"},
    reason="set DOCWIKI_SITE_BUILD=1 to build the site with the pinned Quartz",
)

BASE_URL = "docwiki.example.com"
EN_MINUTES = f"en/{MINUTES_PAGE}"
EVIDENCE = f"evidence/{MINUTES}/para-0007"


@pytest.fixture(scope="module")
def site(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("bilingual")
    release = make_bilingual(root / "release")
    make_untranslated(release, PLAN_A_PAGE)
    return build_site(release, root / "public", base_url=BASE_URL, log=print)


def page(site: Path, slug: str) -> str:
    rel = "index.html" if slug == "index" else f"{slug.removesuffix('/index')}"
    path = site / rel if rel.endswith(".html") else site / f"{rel}.html"
    if not path.is_file():
        path = site / rel / "index.html"
    return path.read_text(encoding="utf-8")


def html_lang(text: str) -> str:
    found = re.search(r'<html lang="([^"]+)"', text)
    assert found
    return found.group(1)


def switch(text: str) -> dict[str, tuple[str, bool]]:
    """The language switch: language → (href, current)."""
    nav = re.search(r'<nav class="docwiki-lang"[^>]*>(.*?)</nav>', text)
    assert nav, "no language switch"
    links = re.findall(r"<a ([^>]*)>", nav.group(1))
    result: dict[str, tuple[str, bool]] = {}
    for attributes in links:
        lang = re.search(r'hreflang="([^"]+)"', attributes)
        href = re.search(r'href="([^"]*)"', attributes)
        assert lang and href
        result[lang.group(1)] = (href.group(1), 'aria-current="true"' in attributes)
    return result


def alternates(text: str) -> dict[str, str]:
    return dict(re.findall(r'<link rel="alternate" hreflang="([^"]+)" href="([^"]+)"', text))


def explorer_fns(text: str) -> dict[str, str]:
    found = re.search(r'data-data-fns="([^"]+)"', text)
    assert found
    return json.loads(html_lib.unescape(found.group(1)))


def test_links_and_scan(site: Path) -> None:
    report = check_links(site)
    assert report.ok, report.problems
    assert scan_site(site, default_allowed_hosts(BASE_URL, REPO_URL)) == []
    assert (site / "en" / "index.html").is_file()
    assert (site / "en" / "pipeline.html").is_file()
    assert (site / "en" / "documents.html").is_file()
    assert not (site / "en" / "evidence").exists()
    languages = json.loads((site / "static" / "docwiki" / "languages.json").read_text("utf-8"))
    assert languages == {"schema": 1, "canonical": "fr", "languages": ["fr", "en"]}


@pytest.mark.parametrize(
    ("slug", "lang"),
    [
        ("index", "fr"),
        ("en/index", "en"),
        (MINUTES_PAGE, "fr"),
        (EN_MINUTES, "en"),
        ("pipeline", "fr"),
        ("en/pipeline", "en"),
        ("documents", "fr"),
        ("en/documents", "en"),
        (EVIDENCE, "fr"),
    ],
)
def test_html_lang_follows_the_page(site: Path, slug: str, lang: str) -> None:
    assert html_lang(page(site, slug)) == lang


def test_hreflang_alternates(site: Path) -> None:
    expected = {
        "fr": f"https://{BASE_URL}/{MINUTES_PAGE}",
        "en": f"https://{BASE_URL}/{EN_MINUTES}",
        "x-default": f"https://{BASE_URL}/{MINUTES_PAGE}",
    }
    assert alternates(page(site, MINUTES_PAGE)) == expected
    assert alternates(page(site, EN_MINUTES)) == expected
    assert alternates(page(site, "en/index")) == {
        "fr": f"https://{BASE_URL}/",
        "en": f"https://{BASE_URL}/en/",
        "x-default": f"https://{BASE_URL}/",
    }
    # Evidence and filed answers have no twin: no alternates.
    assert alternates(page(site, EVIDENCE)) == {}


def test_switch_keeps_the_slug(site: Path) -> None:
    name = MINUTES_PAGE.split("/")[1]
    assert switch(page(site, MINUTES_PAGE)) == {
        "fr": (f"../sources/{name}", True),
        "en": (f"../en/sources/{name}", False),
    }
    assert switch(page(site, EN_MINUTES)) == {
        "fr": (f"../../sources/{name}", False),
        "en": (f"../../en/sources/{name}", True),
    }
    assert switch(page(site, "index"))["en"] == ("./en/", False)
    assert switch(page(site, "en/pipeline"))["fr"] == ("../pipeline", False)
    # A document's own pages are not translated: English leads to its documents page.
    assert switch(page(site, EVIDENCE))["en"] == ("../../en/documents", False)
    for text in (page(site, "index"), page(site, EN_MINUTES)):
        nav = re.search(r'<nav class="docwiki-lang".*?</nav>', text)
        assert nav and nav.group(0).count('data-router-ignore="true"') == 2


def test_ui_strings_in_the_page_language(site: Path) -> None:
    french, english = page(site, MINUTES_PAGE), page(site, EN_MINUTES)
    for text, words in (
        (french, ["Aller au contenu", "Traitement", "Parcourir", "Rechercher", "Table des matières",
                  "Exemple fictif.", "Voir le document", 'aria-label="Langue"',
                  'aria-label="Fil d']),
        (english, ["Skip to content", "Pipeline", "Browse", "Search", "Table of Contents",
                   "Fictional sample.", "View document", 'aria-label="Language"',
                   'aria-label="Breadcrumbs"']),
    ):  # fmt: skip
        for word in words:
            assert word in text, word
    assert "Skip to content" not in french and "Aller au contenu" not in english
    assert f"<title>{FR_MINUTES_TITLE}</title>" in french
    home = page(site, "index")
    assert "Comment ce wiki est fait" in home and "Compilé par" in home
    en_home = page(site, "en/index")
    assert "How this wiki is made" in en_home and "Compiled by" in en_home
    # The mirror's home reads like the home page: no listing of its folder.
    assert "page-listing" not in en_home and "page-listing" not in home
    assert "Les 14 étapes techniques" in page(site, "pipeline")
    assert "The 14 technical steps" in page(site, "en/pipeline")
    assert "documents dans cette version" in page(site, "documents")
    assert "documents in this release" in page(site, "en/documents")


def test_mirror_chrome_leads_to_the_mirror(site: Path) -> None:
    english = page(site, EN_MINUTES)
    # The site title and the first breadcrumb lead to the mirror's home.
    assert f'<h2 class="page-title"><a href="../../en/">{MOCK_TITLE}</a></h2>' in english
    assert '<div class="breadcrumb-element"><a href="../../en/">Wiki</a>' in english
    # The tabs lead to the mirror's documents and pipeline pages.
    assert 'href="../../en/documents" class="docwiki-tab"' in english
    assert 'href="../../en/pipeline" class="docwiki-tab"' in english
    assert 'data-lang="en" data-root="en/"' in english
    french = page(site, MINUTES_PAGE)
    assert f'<h2 class="page-title"><a href="..">{FR_HOME_TITLE}</a></h2>' in french
    assert 'data-lang="fr" data-root' in french
    # The documents register links each language's wiki pages; documents are shared.
    name = MINUTES_PAGE.split("/")[1]
    assert f'<a href="../en/sources/{name}">Wiki page</a>' in page(site, "en/documents")
    assert f'<a href="./sources/{name}">Page du wiki</a>' in page(site, "documents")
    assert f'href="../evidence/{MINUTES}/"' in page(site, "en/documents")


def test_explorer_per_language(site: Path) -> None:
    french = explorer_fns(page(site, MINUTES_PAGE))
    english = explorer_fns(page(site, EN_MINUTES))
    assert 'const mirrors = ["en"]' in french["filterFn"]
    assert "const root = null" in french["mapFn"]
    assert "const mirrors = []" in english["filterFn"]
    assert 'const root = "en"' in english["mapFn"]
    assert 'const at = "en/"' in english["sortFn"]
    assert "<h2>Parcourir</h2>" in page(site, MINUTES_PAGE)
    assert "<h2>Browse</h2>" in page(site, EN_MINUTES)


def test_search_index_per_language(site: Path) -> None:
    """The content index has both trees; the loader keeps the pages of the reader's language."""
    index = json.loads((site / "static" / "contentIndex.json").read_text(encoding="utf-8"))
    assert MINUTES_PAGE in index and EN_MINUTES in index
    assert index[EN_MINUTES]["title"] == "Site meeting minutes n°3"
    assert index[MINUTES_PAGE]["title"] == FR_MINUTES_TITLE
    loader = re.search(
        r'<script src="[^"]*static/docwiki/content-index\.js"[^>]*data-languages="([^"]+)"',
        page(site, "index"),
    )
    assert loader and loader.group(1) == "fr en"


def test_document_quotations_marked_only_in_the_mirror(site: Path) -> None:
    """The minutes are a French document: quoted on an English page they are marked `lang`."""
    english = page(site, EN_MINUTES)
    french = page(site, MINUTES_PAGE)
    article = re.compile(r"<article.*?</article>", re.S)
    en_article = article.search(english)
    fr_article = article.search(french)
    assert en_article and fr_article
    assert 'lang="fr"' in en_article.group(0)
    assert 'lang="fr"' not in fr_article.group(0)


def article(text: str) -> str:
    found = re.search(r"<article.*?</article>", text, re.S)
    assert found
    return found.group(0)


def start_tags(text: str, tag: str) -> list[str]:
    return re.findall(rf"<{tag}(?:\s[^>]*)?>", text)


def test_footnotes_speak_the_page_language(site: Path) -> None:
    """remark-rehype's English "Footnotes" and "Back to reference N" follow the page (B2)."""
    french = html_lib.unescape(page(site, MINUTES_PAGE))
    english = page(site, EN_MINUTES)
    assert '<h2 class="sr-only" id="footnote-label">Notes<' in french
    assert '<h2 class="sr-only" id="footnote-label">Footnotes<' in english
    assert "aria-label=\"Retour à l'appel de note 1\"" in french
    assert "Back to reference" not in french
    assert 'aria-label="Back to reference 1"' in english


def test_untranslated_mirror_is_marked_in_the_canonical_language(site: Path) -> None:
    """An English page kept untranslated shows French text: its body and title are marked
    `lang="fr"`, the English notice that says so is not (B3, WCAG 3.1.2)."""
    text = page(site, f"en/{PLAN_A_PAGE}")
    assert html_lang(text) == "en"
    body = article(text)
    notice = re.search(r"<blockquote([^>]*)>\s*<p><strong>Untranslated:", body)
    assert notice, "no untranslated notice"
    assert "docwiki-notice--untranslated" in notice.group(1)
    assert "lang=" not in notice.group(1)
    # Every section heading and list of the body is marked; the hidden footnotes
    # heading is the page's own word.
    for tag in ("h2", "h3", "ul"):
        tags = [t for t in start_tags(body, tag) if 'id="footnote-label"' not in t]
        tags = [t for t in tags if "docwiki-badge-legend" not in t]
        assert tags and all('lang="fr"' in t for t in tags), (tag, tags)
    h1 = start_tags(text, "h1")
    assert len(h1) == 1 and 'lang="fr"' in h1[0]
    # Footnotes: the citations are marked, their badges are in the page's language.
    assert any('lang="fr"' in t for t in start_tags(body, "ol"))
    badges = [t for t in start_tags(body, "span") if '"docwiki-badge docwiki-badge--' in t]
    assert badges and all('lang="fr"' not in t for t in badges)
    # A translated mirror page keeps its own language, French quotations aside.
    translated = page(site, EN_MINUTES)
    assert not any('lang="fr"' in t for t in start_tags(article(translated), "h2"))
    assert 'lang="fr"' not in start_tags(translated, "h1")[0]


def test_untranslated_pages_listed_in_the_canonical_language(site: Path) -> None:
    """The mirror's home lists the untranslated page: its title and French summary are marked;
    the sources index's own (English) words after the same link are not."""
    name = PLAN_A_PAGE.split("/")[1]
    home = article(page(site, "en/index"))
    assert re.search(rf'<a href="[^"]*/{name}"[^>]* lang="fr"', home)
    assert f'<span lang="fr">: {UNTRANSLATED_SUMMARY}</span>' in home
    index = article(page(site, "en/sources/index"))
    assert re.search(rf'<a href="[^"]*/{name}"[^>]* lang="fr"', index)
    assert ": superseded by" in index and '<span lang="fr">: superseded' not in index


def test_quartz_words_follow_the_page_language(site: Path) -> None:
    """The words Quartz writes in English whatever the locale: the search icon's title (the
    button was named "Search Recherche"), the global graph button, the RSS link."""
    french, english = page(site, MINUTES_PAGE), page(site, EN_MINUTES)
    for text in (french, english):
        assert "<title>Search</title>" not in text
        assert 'aria-label="Global Graph"' not in text
    assert 'aria-label="Graphe global"' in french and 'aria-label="Global graph"' in english
    assert 'title="Flux RSS"' in french and 'title="RSS feed"' in english
    assert "Table des Matières" not in french


def test_collapsed_explorer_folders_leave_the_tab_order(site: Path) -> None:
    """Links in a collapsed folder (0 px tall) leave the Tab order once it has collapsed (B4)."""
    css = re.sub(r"\s*([{}>:;,])\s*", r"\1", (site / "index.css").read_text(encoding="utf-8"))
    assert ".explorer .folder-outer:not(.open)>ul{visibility:hidden" in css
    # An open folder's links come back at once; nothing sets them visible inside a closed one.
    assert ".explorer .folder-outer>ul{transition:visibility" in css
