"""French canonical pages and an English mirror (ADR 0012, slice G): the release contract the site
reads, the settings of each language, the pages written per language, and the overlay's pure
language helpers and string tables (run with Node; skipped when Node cannot strip types)."""

from __future__ import annotations

import json
import shutil
import subprocess
from functools import cache
from pathlib import Path

import pytest
from site_testkit import (
    FR_HOME_TITLE,
    FR_MINUTES_TITLE,
    MINUTES,
    MINUTES_PAGE,
    MOCK_RELEASE,
    MOCK_RELEASE_DIR,
    MOCK_TITLE,
    OVERLAY,
    PLAN_B,
    FakeTools,
    make_bilingual,
)

from docwiki.site import build_site, open_release, site_settings
from docwiki.site.build import LANGUAGES_FILE, Languages
from docwiki.site.process_page import documents_markdown, process_markdown, stages
from docwiki.site.register import register_groups

I18N = OVERLAY / "quartz" / "components" / "docwiki" / "i18n"
CONTENT_INDEX = OVERLAY / "quartz" / "static" / "docwiki" / "content-index.js"


def _settings(release_root: Path) -> dict[str, object]:
    return site_settings(
        open_release(release_root),
        base_url=None,
        page_title=None,
        banner=None,
        repo_url="https://example.invalid/docwiki",
        quartz_version="v4.5.2",
    )


@pytest.fixture
def bilingual(tmp_path: Path) -> Path:
    return make_bilingual(tmp_path / "release")


# ----- The release contract -----


def test_a_release_without_a_mirror_reads_as_before() -> None:
    release = open_release(MOCK_RELEASE)
    assert release.languages == Languages("en", ())
    assert release.mirrors == {}
    settings = _settings(MOCK_RELEASE)
    assert settings["languages"] == ["en"]
    assert settings["mirrors"] == {}
    assert settings["steps"][0]["text"].startswith("Lists the documents")  # type: ignore[index]


def test_two_languages_split_the_catalog(bilingual: Path) -> None:
    release = open_release(bilingual)
    assert release.languages == Languages("fr", ("en",))
    ids = [page.id for page in release.catalog.pages]
    assert len(ids) == len(set(ids))
    assert not any(page.path.startswith("en/") for page in release.catalog.pages)
    assert release.catalog.page_by_id()["index:home"].title == FR_HOME_TITLE
    mirror = release.mirrors["en"]
    by_id = mirror.page_by_id()
    # Same ids, paths relative to the mirror's folder, the mirror's own titles.
    assert by_id["index:home"].path == "index.md"
    assert by_id[MINUTES].path == f"{MINUTES_PAGE}.md"
    assert by_id[MINUTES].title == "Site meeting minutes n°3"
    assert "query:2026-03-31-window-delivery-date" not in by_id
    # The manifest's `wiki_languages` does not break the strict manifest model.
    assert release.manifest() is not None


def test_languages_without_a_manifest_come_from_the_catalog(bilingual: Path) -> None:
    (bilingual / "manifest.json").unlink()
    release = open_release(bilingual)
    assert release.languages == Languages("fr", ("en",))


def test_a_mirror_needs_its_folder(bilingual: Path) -> None:
    shutil.rmtree(bilingual / "wiki" / "en")
    for path in (bilingual / "catalog.json", bilingual / "wiki" / "catalog.json"):
        catalog = json.loads(path.read_text(encoding="utf-8"))
        catalog["pages"] = [page for page in catalog["pages"] if page.get("lang") != "en"]
        path.write_text(json.dumps(catalog), encoding="utf-8")
    release = open_release(bilingual)
    assert release.languages == Languages("fr", ())
    assert _settings(bilingual)["mirrors"] == {}


def test_settings_of_each_language(bilingual: Path) -> None:
    settings = _settings(bilingual)
    assert settings["languages"] == ["fr", "en"]
    assert settings["pageTitle"] == FR_HOME_TITLE
    sources = settings["sources"]
    assert sources[MINUTES]["page"] == MINUTES_PAGE  # type: ignore[index]
    assert sources[MINUTES]["title"] == FR_MINUTES_TITLE  # type: ignore[index]
    assert settings["steps"][0]["text"].startswith("Liste les documents")  # type: ignore[index]
    mirror = settings["mirrors"]["en"]  # type: ignore[index]
    assert mirror["pageTitle"] == MOCK_TITLE
    assert mirror["sources"][MINUTES]["page"] == f"en/{MINUTES_PAGE}"
    assert mirror["sources"][MINUTES]["title"] == "Site meeting minutes n°3"
    # The documents themselves are shared: same document page and original.
    assert mirror["sources"][PLAN_B]["document"] == sources[PLAN_B]["document"]  # type: ignore[index]
    assert mirror["sources"][PLAN_B]["original"] == sources[PLAN_B]["original"]  # type: ignore[index]
    assert mirror["steps"][0]["text"].startswith("Lists the documents")
    assert mirror["explorer"] == {"hubFolders": [], "entitiesTitle": None, "folderTitles": {}}


def test_register_words_follow_the_language() -> None:
    sources = {
        "a": {"scope": None, "phase": None, "docType": None, "title": "A"},
        "b": {"scope": "moreau", "phase": "3", "docType": None, "title": "B"},
    }
    scopes = {"moreau": {"title": "Chantier Moreau", "hub": "chantiers/moreau"}}
    french = register_groups(sources, scopes, "fr")
    assert french is not None
    assert [group["title"] for group in french] == ["Chantier Moreau", "Autres documents"]
    assert french[0]["phases"][0]["title"] == "Phase 3"
    assert french[1]["phases"][0]["title"] == "Sans phase"
    assert french[1]["phases"][0]["types"][0]["title"] == "Autres documents"
    english = register_groups(sources, scopes)
    assert english is not None and english[1]["phases"][0]["title"] == "No phase"


def test_pipeline_and_documents_pages_in_each_language() -> None:
    assert process_markdown().startswith("---\nlang: en\ntitle: Pipeline\n")
    assert process_markdown("fr").startswith("---\nlang: fr\ntitle: Traitement\n")
    assert process_markdown("fr").rstrip().endswith("## En direct")
    assert documents_markdown("fr").startswith("---\nlang: fr\ntitle: Documents\n")
    # Any other language gets the English text, marked with its own code.
    assert process_markdown("de").startswith("---\nlang: de\ntitle: Pipeline\n")
    assert [name for name, _ in stages("fr")] == [name for name, _ in stages("en")]


def test_build_writes_both_trees_and_the_languages_file(
    bilingual: Path, tmp_path: Path, tools: FakeTools
) -> None:
    cache = tmp_path / "cache"
    build_site(bilingual, tmp_path / "out", cache_dir=cache, runner=tools, env={})
    checkout = cache / "v4.5.2"
    content = checkout / "content"
    assert (
        (content / "pipeline.md")
        .read_text(encoding="utf-8")
        .startswith("---\nlang: fr\ntitle: Traitement\n")
    )
    assert (
        (content / "en" / "pipeline.md")
        .read_text(encoding="utf-8")
        .startswith("---\nlang: en\ntitle: Pipeline\n")
    )
    assert (content / "en" / "documents.md").is_file()
    assert (content / "en" / "sources" / f"{MINUTES_PAGE.split('/')[1]}.md").is_file()
    assert (content / "evidence" / PLAN_B / "index.md").is_file()
    assert not (content / "en" / "evidence").exists()
    languages = json.loads((checkout / "quartz" / LANGUAGES_FILE).read_text(encoding="utf-8"))
    assert languages == {"schema": 1, "canonical": "fr", "languages": ["fr", "en"]}
    settings = json.loads((checkout / "docwiki-site.json").read_text(encoding="utf-8"))
    assert settings["languages"] == ["fr", "en"] and "en" in settings["mirrors"]


def test_build_of_a_release_without_a_mirror_has_one_tree(tmp_path: Path, tools: FakeTools) -> None:
    cache = tmp_path / "cache"
    build_site(MOCK_RELEASE, tmp_path / "out", cache_dir=cache, runner=tools, env={})
    checkout = cache / "v4.5.2"
    assert (
        (checkout / "content" / "pipeline.md")
        .read_text(encoding="utf-8")
        .startswith("---\nlang: en\ntitle: Pipeline\n")
    )
    assert not (checkout / "content" / "en").exists()
    assert not (checkout / "quartz" / LANGUAGES_FILE).exists()


def test_fixture_mirror_links_reach_the_shared_evidence(bilingual: Path) -> None:
    text = (bilingual / "wiki" / "en" / f"{MINUTES_PAGE}.md").read_text(encoding="utf-8")
    assert "lang: en" in text and f"translation_of: {MINUTES}" in text
    assert "](../../evidence/" in text
    canonical = (bilingual / "wiki" / f"{MINUTES_PAGE}.md").read_text(encoding="utf-8")
    assert "lang: fr" in canonical and "](../evidence/" in canonical
    assert MOCK_RELEASE_DIR.is_dir()  # the fixture is a copy: the mock release is untouched
    assert "lang: en" in (MOCK_RELEASE_DIR / "wiki" / f"{MINUTES_PAGE}.md").read_text(
        encoding="utf-8"
    )


# ----- The overlay's language helpers and string tables (Node) -----


@cache
def _node() -> tuple[str, ...] | None:
    node = shutil.which("node")
    if node is None:
        return None
    probe = f"await import({json.dumps((I18N / 'index.ts').as_uri())})"
    for flags in ((), ("--experimental-strip-types",)):
        command = (node, *flags, "--no-warnings", "--input-type=module")
        completed = subprocess.run(
            [*command, "-e", probe], capture_output=True, text=True, check=False
        )
        if completed.returncode == 0:
            return command
    return None


def run(script: str) -> object:
    command = _node()
    if command is None:
        pytest.skip("Node 22.6+ (type stripping) is not available")
    program = (
        f"const m = await import({json.dumps((I18N / 'index.ts').as_uri())});\n"
        f"const text = await import({json.dumps((OVERLAY / 'quartz' / 'plugins' / 'transformers' / 'docwiki-text.ts').as_uri())});\n"  # noqa: E501
        f"const pipe = await import({json.dumps((OVERLAY / 'quartz' / 'components' / 'docwiki' / 'scripts' / 'pipeline.ts').as_uri())});\n"  # noqa: E501
        f"{script}"
    )
    completed = subprocess.run(
        [*command, "-e", program], capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_both_tables_have_the_same_keys() -> None:
    result = run(
        """const shape = (value) => {
          if (typeof value === "function") return "fn"
          if (Array.isArray(value)) return "array"
          if (value && typeof value === "object") {
            return Object.fromEntries(Object.keys(value).sort().map((k) => [k, shape(value[k])]))
          }
          return typeof value
        }
        const en = m.stringsFor("en"), fr = m.stringsFor("fr")
        // Maps of the portal's words are optional per language (English shows the word itself).
        const open = ["stageStatus", "runCounts", "gateWords", "runKinds", "runStatus"]
        for (const t of [en, fr]) for (const key of open) t.pipeline[key] = {}
        console.log(JSON.stringify([shape(en), shape(fr), en.ask.examples.length,
          fr.ask.examples.length, m.stringsFor("de").lang, m.stringsFor(null).lang]))"""
    )
    assert isinstance(result, list)
    en, fr, en_examples, fr_examples, other, none = result
    assert en == fr
    assert en_examples == fr_examples == 3
    assert other == none == "en"


def test_language_helpers() -> None:
    result = run(
        """const langs = ["fr", "en"]
        const has = (slug) => ["en/sources/x", "en/index", "en/documents"].includes(slug)
        console.log(JSON.stringify([
          m.treeOf("en/sources/x", langs), m.treeOf("sources/x", langs),
          m.treeOf("evidence/src-1/p1", langs), m.treeOf("en", langs),
          m.baseSlug("en/sources/x", langs), m.baseSlug("en/index", langs),
          m.baseSlug("sources/x", langs),
          m.slugIn("index", "en", langs), m.slugIn("index", "fr", langs),
          m.pageLanguage("sources/x", "en", langs), m.pageLanguage("en/x", null, langs),
          m.pageLanguage("x", "de", langs),
          m.switchTarget("sources/x", "en", langs, has),
          m.switchTarget("en/sources/x", "fr", langs, (slug) => slug === "sources/x"),
          m.switchTarget("sources/y", "en", langs, has),
          m.switchTarget("evidence/src-1/p1", "en", langs, has),
          m.switchTarget("sources/x", "fr", langs, has),
          m.localUrl("/sources/x", "en/"), m.localUrl("/", "en/"),
          m.localUrl("/evidence/src-1/index", "en/"),
          m.localUrl("/evidence/src-1/original.pdf", "en/"),
          m.localUrl("/static/docwiki/answers.json", "en/"), m.localUrl("/sources/x", ""),
          m.localUrl("//evil.example/x", "en/"),
          m.langCookie("en", true), m.langCookie("fr", false),
        ]))"""
    )
    assert result == [
        "en", "fr", "fr", "en",
        "sources/x", "index", "sources/x",
        "en/index", "index",
        "en", "en", "fr",
        "en/sources/x", "sources/x", "en/index", "en/documents", "sources/x",
        "/en/sources/x", "/en/", "/evidence/src-1/index", "/evidence/src-1/original.pdf",
        "/static/docwiki/answers.json", "/sources/x", "//evil.example/x",
        "docwiki_lang=en; path=/; max-age=31536000; samesite=lax; secure",
        "docwiki_lang=fr; path=/; max-age=31536000; samesite=lax",
    ]  # fmt: skip


def test_french_words_of_the_pure_helpers() -> None:
    result = run(
        """const fr = m.stringsFor("fr")
        console.log(JSON.stringify([
          text.documentsPhrase(36, 1, fr), text.documentsPhrase(1, 0, fr),
          text.qualityPhrase({passed: 12, warned: 1, skipped: 2, failed: 0, gates: 15,
            blockingFailed: 0}, fr),
          text.qualityPhrase({passed: 0, warned: 0, skipped: 0, failed: 1, gates: 1,
            blockingFailed: 1}, fr),
          text.money(1.37, null, fr), text.money(0.001, "USD", fr), text.money(2, "EUR", fr),
          text.lastRunLine({runs: [{is_current: true, cost: {total: 1.37, duration_s: 240}}]}, fr),
          text.stepsLabel(1, fr), text.waitingLabel(12.7, fr), text.provenanceLine(
            {provenance: "", date: "2026-04-01"}, fr),
          text.liveQuestion("ab", fr), text.groupAnswers([], "index", fr),
          text.shownBadge(text.badgeForText("✓ quote verified"), fr).text,
          text.provenanceBadge("native-text", fr).text,
          pipe.phaseText("processing", "write", 4, 13, "compile", fr),
          pipe.phaseText("failed", null, null, null, "classify", fr),
          pipe.changeSummary(
            {added: [1, 2], changed: [1], removed: [], opened: [1], closed: [1]}, fr),
          pipe.runAtWork("compile", fr),
          pipe.docSentence({path: "a.pdf", title: null, state: "in_wiki", phase: null,
            step: null, steps: null, stage: null, hidden: false}, fr),
          pipe.docSentence({path: "a.pdf", title: "PV", state: "processing", phase: "write",
            step: 4, steps: 13, stage: "compile", hidden: false}, fr),
          pipe.andMore(3, fr),
          // English stays the default, as before.
          text.documentsPhrase(36, 1), pipe.phaseText("processing", "write", 4, 13, "compile"),
        ]))"""
    )
    assert result == [
        "37 documents (1 remplacé)", "1 document",
        "12 réussis, 1 avertissement, 2 non exécutés", "1 contrôle bloquant en échec",
        "1,37 $", "< 0,01 $", "2,00 EUR",
        "dernière exécution 4 min · 1,37 $",
        "Comment l'agent a travaillé (1 étape)", "Le Researcher lit le wiki… 12 s",
        "Classée le 2026-04-01",
        {"error": "Posez une question complète."}, [],
        "✓ citation vérifiée", "texte natif",
        "Phase 3 sur 4 : Rédiger, étape 4/13 compile",
        "Échec à la phase 2 sur 4 : Classer",
        "2 pages ajoutées · 1 modifiée · 1 contradiction ouverte · 1 résolue",
        "Exécution en cours : compile (étape 4/13)",
        "a.pdf est dans le wiki",
        "PV : Rédiger (étape 4/13)",
        "et 3 de plus",
        "37 documents (1 superseded)", "Phase 3 of 4: Write, step 4/13 compile",
    ]  # fmt: skip


def test_search_and_explorer_data_follow_the_page_language() -> None:
    """``static/docwiki/content-index.js``: each read of ``fetchData`` gives the pages of the
    language of the page on screen (evidence is shared); one language keeps every page."""
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is not available")
    script = CONTENT_INDEX.read_text(encoding="utf-8")
    program = """
const vm = require("node:vm")
const index = {"index": 1, "sources/x": 1, "tags/t": 1, "evidence/src-1/p1": 1,
  "en/index": 1, "en/sources/x": 1}
async function load(languages, slug) {
  const body = {getAttribute: () => slug}
  const context = {
    URL, Promise, Object, String,
    fetch: async () => ({json: async () => index}),
    document: {currentScript: {src: "https://site.invalid/static/docwiki/content-index.js",
      getAttribute: () => languages}, body},
  }
  context.window = context
  vm.createContext(context)
  vm.runInContext(SCRIPT, context)
  return Object.keys(await context.window.fetchData).sort()
}
;(async () => {
  console.log(JSON.stringify([
    await load("fr en", "sources/x"), await load("fr en", "en/sources/x"),
    await load("fr en", "evidence/src-1/p1"), await load(null, "sources/x"),
  ]))
})()
""".replace("SCRIPT", json.dumps(script))
    completed = subprocess.run(
        [node, "-e", program], capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert completed.returncode == 0, completed.stderr
    french, english, evidence, single = json.loads(completed.stdout)
    assert french == ["evidence/src-1/p1", "index", "sources/x", "tags/t"]
    assert english == ["en/index", "en/sources/x", "evidence/src-1/p1"]
    assert evidence == french
    assert single == sorted(["index", "sources/x", "tags/t", "evidence/src-1/p1", "en/index",
                             "en/sources/x"])  # fmt: skip
