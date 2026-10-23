"""A two-language wiki end to end (v1.7, ADR 0012): French canonical pages, an English mirror.

The real compile lane runs behind stub extraction on the scoped corpus, with a copy of the scoped
test pack that declares ``wiki_languages: [fr, en]`` and one locked trade term. The fake model
"translates" every segment by prefixing it with ``EN:``, which keeps every placeholder, number
and locked term, so the preservation check accepts it unless a test breaks it on purpose.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from engine_stubs import CANARY, build_evidence, extract_source, write_scoped_corpus
from test_real_compile_lane import real_lane_llm

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.i18n import untranslated_marker
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.manifest import ReleaseManifest
from docwiki.contracts.pages import Page
from docwiki.llm import FakeLlmClient, LlmRequest
from docwiki.mcp.config import McpConfig
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import ReadTools, ToolInputError
from docwiki.orchestration.registry import load_engine
from docwiki.release.reader import ReleaseReader
from docwiki.release.validate import validate_release
from docwiki.search.index import SearchIndex

pytest.importorskip("docwiki.stages.compile")

SCOPED_PACK = Path(__file__).resolve().parent / "fixtures" / "scoped-pack"
ALPHA_A = source_id_for("chantiers/alpha/1-marche/quote/DEV-2026-014 indice A.txt")
TERMS = """\
terms:
  - term: devis
    gloss: quotation
    banned: [estimate]
"""
_SEGMENTS_RE = re.compile(r"BEGIN SEGMENTS (\w+)\n(.*)\nEND SEGMENTS \1", re.S)


def two_language_pack(root: Path) -> Path:
    pack = root / "pack-fr-en"
    shutil.copytree(SCOPED_PACK, pack)
    info = pack / "pack.yaml"
    text = info.read_text(encoding="utf-8")
    info.write_text(text + "wiki_languages: [fr, en]\n", encoding="utf-8", newline="\n")
    (pack / "terms.yaml").write_text(TERMS, encoding="utf-8", newline="\n")
    return pack


class Translator:
    """The fake ``translate_page`` model: ``EN: <text>`` for every segment, counted."""

    def __init__(self, change: Any = None) -> None:
        self.calls = 0
        self.change = change

    def __call__(self, request: LlmRequest) -> dict[str, Any]:
        self.calls += 1
        match = _SEGMENTS_RE.search(request.text)
        assert match is not None, "the request carries its segments between nonce lines"
        segments = json.loads(match.group(2))["segments"]
        out = []
        for segment in segments:
            text = f"EN: {segment['text']}"
            if self.change is not None:
                text = self.change(segment, text)
            out.append({"id": segment["id"], "text": text})
        return {"segments": out}


def llm_with(translator: Translator) -> FakeLlmClient:
    llm = real_lane_llm()
    llm.register("translate_page", translator)
    return llm


@pytest.fixture
def run_two_languages(make_harness, tmp_path: Path):
    corpus = write_scoped_corpus(tmp_path / "scoped-input")
    pack = two_language_pack(tmp_path)

    def factory(translator: Translator):
        engine = load_engine({"extract_source": extract_source, "build_evidence": build_evidence})
        return make_harness(
            engine=engine, llm=llm_with(translator), pack=pack, domain=str(pack), input_dir=corpus
        )

    return factory


def _problems(root: Path) -> list[str]:
    return [
        f"{v.gate} {v.severity} {v.code} {v.path}:{v.line} {v.message}"
        for v in validate_release(
            root, canaries=[CANARY], glossary_seeded=True, locked_terms={"devis": ["estimate"]}
        )
    ]


def _pages(root: Path) -> dict[str, Page]:
    wiki = root / "wiki"
    pages: dict[str, Page] = {}
    for file in sorted(wiki.rglob("*.md")):
        rel = file.relative_to(wiki).as_posix()
        if rel.startswith((".agents/", ".claude/", ".github/")):
            continue
        pages[rel] = Page.parse(file.read_text(encoding="utf-8"), rel)
    return pages


async def test_two_languages_produce_both_trees_and_a_valid_release(run_two_languages):
    translator = Translator()
    harness = run_two_languages(translator)
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    assert translator.calls > 0
    root = harness.current_release()
    assert _problems(root) == []

    pages = _pages(root)
    canonical = {rel: page for rel, page in pages.items() if not rel.startswith("en/")}
    mirror = {rel: page for rel, page in pages.items() if rel.startswith("en/")}
    # canonical pages are French, generated headings included
    source = canonical[next(rel for rel, p in canonical.items() if p.frontmatter.id == ALPHA_A)]
    assert source.frontmatter.lang == "fr" and source.frontmatter.translation_of is None
    assert "## Faits clés" in source.body and "## Voir aussi" in source.body
    assert "## Contradictions ouvertes" in canonical["chantiers/alpha.md"].body
    # every source, entity, topic, view, hub and index page has its mirror at the same path
    mirrored_types = {"source", "entity", "topic", "view", "hub", "index", "glossary", "log"}
    for rel, page in canonical.items():
        if page.frontmatter.type in mirrored_types:
            twin = mirror.get(f"en/{rel}")
            assert twin is not None, rel
            assert twin.frontmatter.lang == "en"
            assert twin.frontmatter.translation_of == page.frontmatter.id == twin.frontmatter.id
            if page.frontmatter.type in {"source", "entity", "topic", "view", "hub"}:
                assert twin.frontmatter.title == page.frontmatter.title  # never translated
    for rel in mirror:
        assert rel.removeprefix("en/") in canonical
    assert "en/AGENTS.md" not in pages and not any(r.startswith("en/_meta/") for r in pages)
    # the mirror: translated prose, English headings, links inside the mirror, canonical evidence
    twin = mirror[f"en/{source.path}"]
    assert "## Key facts" in twin.body and "## Related" in twin.body and "EN: " in twin.body
    assert twin.frontmatter.summary.startswith("EN: ")
    assert "](../../evidence/" in twin.body  # sidecars stay canonical, untranslated
    assert "## Open contradictions" in mirror["en/chantiers/alpha.md"].body
    assert "| Chantier | Phase | Open contradictions |" in mirror["en/index.md"].body
    assert "| Chantier | Phase | Contradictions ouvertes |" in canonical["index.md"].body
    # catalog and manifest state the languages
    catalog = Catalog.from_json((root / "catalog.json").read_bytes())
    assert catalog.wiki_languages == ["fr", "en"]
    assert {entry.lang for entry in catalog.pages if entry.path.startswith("en/")} == {"en"}
    keys = [(entry.id, entry.lang) for entry in catalog.pages]
    assert len(keys) == len(set(keys))
    manifest = ReleaseManifest.from_json((root / "manifest.json").read_bytes())
    assert manifest.wiki_languages == ["fr", "en"] and manifest.canonical_lang == "fr"
    assert manifest.counts["mirror_pages"] == len(mirror)
    # gates: G17 passes, G16 covers the mirror
    gates = {gate.gate: gate for gate in manifest.gates}
    assert gates["G17"].status == "pass" and gates["G16"].status == "pass"
    # the reader and the search index know both languages
    reader = ReleaseReader.open(harness.settings.work_dir)
    assert reader.read_page(ALPHA_A).frontmatter.lang == "fr"
    english = reader.read_page(ALPHA_A, lang="en")
    assert english.path == twin.path and english.frontmatter.lang == "en"
    with SearchIndex.open(root / "search.db") as index:
        assert index.languages == ["fr", "en"]
        french = index.search("Alpha", limit=50)
        mirrored = index.search("Alpha", limit=50, lang="en")
    assert french and all(not hit.path.startswith("en/") for hit in french)
    assert any(hit.path.startswith("en/") for hit in mirrored)
    assert all(
        hit.path.startswith("en/") or hit.kind == "source-block" or hit.lang == "fr"
        for hit in mirrored
    )
    # the run report counts the translate stage
    stage = next(item for item in outcome.report.stages if item.stage == "translate")
    assert stage.items > 0 and stage.llm_calls == translator.calls
    assert stage.input_tokens > 0 and stage.output_tokens > 0
    # the MCP read tools take lang and say the page language
    reads = ReadTools(FolderReleaseSource(harness.settings.work_dir), McpConfig())
    page = json.loads(reads.read_page(ALPHA_A))
    assert page["lang"] == "fr" and "translation_of" not in page
    mirror_page = json.loads(reads.read_page(ALPHA_A, lang="en"))
    assert mirror_page["lang"] == "en" and mirror_page["translation_of"] == ALPHA_A
    assert mirror_page["path"].startswith("en/") and "## Key facts" in mirror_page["markdown"]
    home = json.loads(reads.get_index("home", lang="en"))
    assert home["path"] == "en/index.md" and home["languages"] == ["fr", "en"]
    hits = json.loads(reads.search("Alpha", lang="en", limit=50))["hits"]
    assert hits and all("lang" in hit for hit in hits)
    with pytest.raises(ToolInputError) as raised:
        reads.search("Alpha", lang="de")
    assert raised.value.code == "invalid_argument"
    assert raised.value.details["languages"] == ["fr", "en"]


async def test_a_rebuild_without_changes_makes_no_translate_call(run_two_languages):
    first = Translator()
    harness = run_two_languages(first)
    assert (await harness.run()).status == "succeeded"
    assert first.calls > 0
    again = Translator()
    harness.llm.register("translate_page", again)
    outcome = await harness.run(kind="rebuild")
    assert outcome.status == "succeeded", outcome.errors
    assert again.calls == 0
    stage = next(item for item in outcome.report.stages if item.stage == "translate")
    assert stage.llm_calls == 0 and stage.cache_hits > 0
    assert _problems(harness.current_release()) == []


async def test_a_translation_that_changes_a_number_is_kept_untranslated(run_two_languages):
    def change(segment: dict[str, Any], text: str) -> str:
        return re.sub(r"\d+", lambda m: str(int(m.group(0)) + 1), text) if "2026" in text else text

    translator = Translator(change)
    harness = run_two_languages(translator)
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    warnings = [w for w in outcome.report.warnings if w.startswith("translate:")]
    assert warnings and "kept untranslated in en" in warnings[0]
    pages = _pages(root)
    marked = [rel for rel, page in pages.items() if untranslated_marker("en") in page.body]
    assert marked and all(rel.startswith("en/") for rel in marked)
    manifest = ReleaseManifest.from_json((root / "manifest.json").read_bytes())
    g17 = next(gate for gate in manifest.gates if gate.gate == "G17")
    assert g17.status == "warn" and not g17.blocking
    assert {detail.code for detail in g17.details} == {"mirror-untranslated"}


async def test_a_banned_rendering_in_a_translation_never_reaches_the_mirror(run_two_languages):
    def change(segment: dict[str, Any], text: str) -> str:
        return re.sub(r"\bdevis\b", "estimate", text, flags=re.I)

    harness = run_two_languages(Translator(change))
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    for rel, page in _pages(root).items():
        assert not re.search(r"estimates?", page.body, re.I), rel
    assert _problems(root) == [] or all("G17" in problem for problem in _problems(root))
