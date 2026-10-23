"""Source mapping (hash, source id, path, title), locators, evidence text and extraction cache."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from evals.corpus import (
    CorpusContext,
    CorpusFile,
    CorpusManifest,
    ExtractionCache,
    ReleaseCatalog,
    SourceResolver,
)
from evals.locators import compact_keys, is_key, keys_match, locator_key_from_label
from evals.records import Citation
from evals_testkit import (
    DECK,
    HELD_BACK,
    MAIL,
    MINUTES,
    NOTE,
    ORDERS,
    PHOTO,
    PLAN,
    QUOTE,
    STUDY,
    TALK,
    cite,
    file_sha,
    mini_corpus,
    renamed_catalog,
)

from docwiki.contracts import Table, source_id_for
from docwiki.contracts.locators import CsvRowsLocator, DocxTableLocator, XlsxRowsLocator

# ------------------------------------------------------------------------------ manifest


def test_manifest_scopes_and_audience(corpus: CorpusContext) -> None:
    manifest = corpus.manifest
    full = {entry.path for entry in manifest.select("full", "public")}
    assert QUOTE in full and STUDY not in full and HELD_BACK not in full
    assert all(path.startswith("full/") for path in full)
    assert STUDY in {entry.path for entry in manifest.select("full", "restricted")}
    # "all" is full/ plus the held-back revisions of held-back/
    assert {entry.path for entry in manifest.select("all", "public")} == full | {HELD_BACK}
    assert STUDY in {entry.path for entry in manifest.select("all", "restricted")}
    for scope in ("quickstart", "everything"):
        with pytest.raises(ValueError, match="unknown corpus scope"):
            manifest.select(scope)


def test_an_empty_selection_is_an_error() -> None:
    study = CorpusFile(path="full/restricted/etude.xlsx", sha256="0" * 64, sensitivity="restricted")
    manifest = CorpusManifest([study])
    with pytest.raises(ValueError, match=r"no document in scope 'full' that the 'public' audience"):
        manifest.select("full", "public")
    assert [entry.path for entry in manifest.select("full", "restricted")] == [study.path]
    with pytest.raises(ValueError, match="no document in scope 'all'"):
        CorpusManifest([]).select("all")
    held_back_only = CorpusManifest([CorpusFile(path="held-back/planning.xlsx", sha256="1" * 64)])
    with pytest.raises(ValueError, match="no document in scope 'full'"):
        held_back_only.select("full")
    assert len(held_back_only.select("all")) == 1


def test_manifest_hashes_and_sensitivity(corpus: CorpusContext) -> None:
    manifest = corpus.manifest
    assert manifest.by_sha256("sha256:" + file_sha(QUOTE)) == QUOTE
    assert manifest.by_sha256(file_sha(QUOTE).upper()) == QUOTE
    assert manifest.by_sha256("0" * 64) is None
    assert manifest.sensitivity(STUDY) == "restricted"
    assert manifest.sensitivity(QUOTE) == "public"
    assert manifest.sensitivity("full/unknown.pdf") is None
    assert {entry.path for entry in manifest.documents()} == set(manifest.files)


def test_real_manifest_loads(repo_root: Path) -> None:
    manifest = CorpusManifest.load(repo_root / "samples" / "corpus")
    assert len(manifest.sha256) == 64
    assert len(manifest.documents()) == 42
    full = manifest.select("full")
    assert len(full) == 39 and all(entry.path.startswith("full/") for entry in full)
    restricted = [entry for entry in manifest.documents() if entry.sensitivity == "restricted"]
    assert len(restricted) == 2 and not set(restricted) & set(full)
    assert len(manifest.select("full", "restricted")) == 41
    held_back = [entry for entry in manifest.documents() if entry.held_back]
    assert len(held_back) == 1 and held_back[0].path.startswith("held-back/")
    assert {entry.path for entry in manifest.select("all")} == {
        *(entry.path for entry in full),
        held_back[0].path,
    }


# ------------------------------------------------------------------------------ resolver


def _resolve(
    corpus: CorpusContext, citation: Citation
) -> tuple[str | None, str | None, str | None]:
    resolved = corpus.resolver.resolve(citation, unit="1")
    return resolved.path, resolved.locator_key, resolved.via


@pytest.mark.parametrize(
    "raw_path",
    [
        QUOTE,
        QUOTE.removeprefix("full/"),
        "DEV-2026-014_indice-B_devis-extension-et-cuisine.pdf",
        "samples/corpus/" + QUOTE,
    ],
)
def test_source_ids_derived_from_deployment_paths(corpus: CorpusContext, raw_path: str) -> None:
    """A release built from full/, from its content or from the repository maps back to full/."""
    citation = Citation(source_id=source_id_for(raw_path), locator_key="p0002")
    assert _resolve(corpus, citation) == (QUOTE, "p0002", "source_id")


def test_hash_mapping_through_the_release_catalog() -> None:
    corpus = mini_corpus(renamed_catalog())
    path, key, via = _resolve(corpus, Citation(source_id="src-0123456789ab", locator_key="p0002"))
    assert (path, key, via) == (QUOTE, "p0002", "source_id")
    # the purchase tracking has no hash in that catalog and an unknown raw path: unresolved
    assert _resolve(corpus, Citation(source_id="src-ba9876543210", locator_key="p0001"))[0] is None
    # catalog source titles also identify sources
    title = Citation(title="Quote DEV-2026-014 (indice B)", label="p. 2")
    assert _resolve(corpus, title) == (QUOTE, "p0002", "title")


def test_sha256_wins_over_the_other_hints(corpus: CorpusContext) -> None:
    citation = Citation(sha256="sha256:" + file_sha(QUOTE), source_path=PLAN, locator_key="p0002")
    assert _resolve(corpus, citation) == (QUOTE, "p0002", "sha256")
    assert _resolve(corpus, cite(QUOTE, "p0001")) == (QUOTE, "p0001", "path")


@pytest.mark.parametrize(
    ("raw_path", "expected"),
    [
        (PLAN, PLAN),
        ("planning/PLN-2026-003_indice-A_planning-et-suivi-des-achats.xlsx", PLAN),
        ("raw/full/planning/PLN-2026-003_indice-A_planning-et-suivi-des-achats.xlsx", PLAN),
        ("full\\planning\\PLN-2026-003_indice-A_planning-et-suivi-des-achats.xlsx", PLAN),
        ("./" + PLAN, PLAN),
        ("planning/PLN-2026-003_indice-B_planning-et-suivi-des-achats.xlsx", HELD_BACK),
        ("unknown/file.pdf", None),
        ("", None),
    ],
)
def test_path_mapping(corpus: CorpusContext, raw_path: str, expected: str | None) -> None:
    assert corpus.resolver.path_for(raw_path) == expected


def test_manifest_titles_identify_sources(corpus: CorpusContext) -> None:
    citation = Citation(
        title="Report de livraison - commande BC-2026-009 (chantier Moreau, Valbrise)",
        label="message body, lines 5–9",
    )
    assert _resolve(corpus, citation) == (MAIL, "msg-body-l0005-l0009", "title")


def test_unresolvable_citation(corpus: CorpusContext) -> None:
    resolved = corpus.resolver.resolve(Citation(label="p. 3"), unit="[4]")
    assert not resolved.resolved and resolved.unit == "[4]" and resolved.via is None


def test_restricted_sources_carry_their_sensitivity(corpus: CorpusContext) -> None:
    resolved = corpus.resolver.resolve(cite(STUDY, "sheet-etude-de-prix-r0002-r0002"), unit="1")
    assert resolved.sensitivity == "restricted"


# ------------------------------------------------------------------------------ locators


@pytest.mark.parametrize(
    ("required", "cited", "match"),
    [
        ("p0003", "p0003", True),
        ("p0003", "p0004", False),
        ("para-0017", "para-0017", True),
        ("para-0017", "para-0018", False),
        ("tbl-02-r0005-r0005", "tbl-02-r0003-r0007", True),
        ("tbl-02-r0005-r0005", "tbl-01-r0005-r0005", False),
        ("tbl-02-r0005-r0005", "tbl-02-r0006-r0008", False),
        ("sheet-achats-r0002-r0002", "sheet-achats-r0001-r0024", True),
        ("sheet-achats-r0002-r0002", "sheet-planning-r0002-r0002", False),
        ("r0026-r0026", "r0020-r0030", True),
        ("r0026-r0026", "r0027-r0030", False),
        ("slide-04", "slide-04", True),
        ("slide-04", "slide-05", False),
        ("msg-body-l0010-l0012", "msg-body-l0011-l0011", True),
        ("msg-body-l0010-l0012", "msg-body", True),
        ("msg-body-l0010-l0012", "msg-body-l0013-l0020", False),
        ("msg-body-l0010-l0012", "msg-headers", False),
        ("cue-00-02-01", "cue-00-02-01", True),
        ("cue-00-02-01", "cue-00-02-10", False),
        ("l0010-l0010", "l0008-l0011", True),
        ("l0014-l0015", "l0001-l0006", False),
        ("img-b07", "img-b07", True),
        ("img-b07", "img-b02", False),
        ("*", "img-b02", True),
        ("*", "p0001", True),
        ("p0001", "para-0001", False),
        ("p0001", "not-a-key", False),
    ],
)
def test_keys_match_granularity(required: str, cited: str, match: bool) -> None:
    assert keys_match(required, cited) is match
    assert keys_match(cited, required) is match


def test_compact_keys_merges_adjacent_ranges() -> None:
    assert compact_keys(["r0002-r0002", "r0003-r0003", "r0004-r0005", "r0009-r0009"]) == [
        "r0002-r0005",
        "r0009-r0009",
    ]
    assert compact_keys(["l0001-l0006", "l0008-l0011", "l0020-l0021"]) == [
        "l0001-l0011",
        "l0020-l0021",
    ]
    assert compact_keys(["sheet-achats-r0001-r0001", "sheet-achats-r0002-r0002"]) == [
        "sheet-achats-r0001-r0002"
    ]
    assert compact_keys(["sheet-achats-r0002-r0002", "sheet-planning-r0003-r0003"]) == [
        "sheet-achats-r0002-r0002",
        "sheet-planning-r0003-r0003",
    ]
    assert compact_keys(["p0001", "p0002", "p0001"]) == ["p0001", "p0002"]
    assert compact_keys(["para-0001", "para-0002"]) == ["para-0001", "para-0002"]
    assert compact_keys(["msg-body-l0010-l0012", "msg-body-l0014-l0014"]) == [
        "msg-body-l0010-l0014"
    ]


@pytest.mark.parametrize(
    ("label", "key"),
    [
        ("p. 3", "p0003"),
        ("pp. 3–4", "p0003"),
        ("page 12", "p0012"),
        ("¶ 42", "para-0042"),
        ("table 2, rows 3–7", "tbl-02-r0003-r0007"),
        ("table 2, row 5", "tbl-02-r0005-r0005"),
        ('sheet "Achats", rows 12–20', "sheet-achats-r0012-r0020"),
        ('sheet "Planning 2026", row 4', "sheet-planning-2026-r0004-r0004"),
        ("rows 12–20", "r0012-r0020"),
        ("row 26", "r0026-r0026"),
        ("slide 5", "slide-05"),
        ("message headers", "msg-headers"),
        ("message body", "msg-body"),
        ("message body, lines 10–18", "msg-body-l0010-l0018"),
        ('attachment "report.pdf"', "msg-att-report-pdf"),
        ("lines 10–18", "l0010-l0018"),
        ("line 4", "l0004-l0004"),
        ("region 7", "img-b07"),
        ("03:15–03:42", "cue-00-03-15"),
        ("01:03:15–01:03:42", "cue-01-03-15"),
        ("`p. 3`", "p0003"),
        ("somewhere", None),
    ],
)
def test_locator_key_from_label(label: str, key: str | None) -> None:
    assert locator_key_from_label(label) == key
    assert key is None or is_key(key)


def test_query_table_labels_need_the_document(corpus: CorpusContext) -> None:
    def with_table(path: str, locator: object) -> object:
        table = Table(
            id="t01",
            locator=locator,
            provenance="deterministic-table",
            columns=["Item"],
            rows=[],
            artifact="tables/t01.parquet",
        )
        return corpus.docs[path].model_copy(update={"tables": [table]})

    csv_doc = with_table(ORDERS, CsvRowsLocator(row_start=1, row_end=5))
    assert locator_key_from_label("table t01, rows r0002–r0004", doc=csv_doc) == "r0002-r0004"
    assert locator_key_from_label("table t01, row r0003", doc=csv_doc) == "r0003-r0003"
    assert locator_key_from_label("table t09, rows r0002–r0004", doc=csv_doc) is None
    assert locator_key_from_label("table t01, rows r0002–r0004") is None
    sheet_doc = with_table(PLAN, XlsxRowsLocator(sheet="Achats", row_start=1, row_end=9))
    label = "table t01, rows r0002–r0004"
    assert locator_key_from_label(label, doc=sheet_doc) == "sheet-achats-r0002-r0004"
    docx_doc = with_table(MINUTES, DocxTableLocator(table=2, row_start=1, row_end=3))
    assert locator_key_from_label(label, doc=docx_doc) == "tbl-02-r0002-r0004"


# ------------------------------------------------------------------------------ evidence


def test_evidence_text_at_metric_granularity(corpus: CorpusContext) -> None:
    evidence = corpus.evidence
    page = evidence.text(QUOTE, "p0002") or ""
    assert "44943,60 €" in page and "TVA 20 %" in page and "2,40 m" not in page
    rows = evidence.text(PLAN, "sheet-achats-r0001-r0003") or ""
    assert "BC-2026-008" in rows and "BC-2026-009" in rows and "T07" not in rows
    assert "BC-2026-009" in (evidence.text(MAIL, "msg-body") or "")
    assert "semaine 17" in (evidence.text(NOTE, "l0010-l0010") or "")
    assert "2,40 mètres" in (evidence.text(TALK, "cue-00-02-01") or "")
    assert "Baie de liaison" in (evidence.text(DECK, "slide-04") or "")
    assert "27/03/2026" in (evidence.text(MINUTES, "tbl-02-r0002-r0003") or "")
    assert evidence.text(PHOTO, "*") == ""  # OCR without OCR: the locator exists, no text
    assert evidence.text(QUOTE, "p0009") is None
    assert evidence.text("full/unknown.pdf", "p0001") is None


def test_restricted_fingerprint(corpus: CorpusContext) -> None:
    assert corpus.fingerprint == {"3324.26", "34518.74", "zm-61078"}


# ---------------------------------------------------------------------------- catalog io


def test_release_catalog_loading(tmp_path: Path, repo_root: Path) -> None:
    mock = repo_root / "samples" / "fixtures" / "mock-release"
    for location in (mock, mock / "releases"):
        catalog = ReleaseCatalog.load(location)
        assert catalog.release_id == "20260401T090000Z-8a41b109"
        assert catalog.audience == "public"
        assert {source.source_id for source in catalog.sources} == {
            "src-59cf9366e50c",
            "src-7630d0741377",
            "src-f0757603684a",
        }
        assert all(source.sha256 and len(source.sha256) == 64 for source in catalog.sources)
        assert any(source.title for source in catalog.sources)
    file = tmp_path / "catalog.json"
    file.write_text(
        json.dumps(
            {"release_id": "r", "sources": [{"source_id": "src-000000000001", "path": "a.pdf"}]}
        ),
        encoding="utf-8",
    )
    assert ReleaseCatalog.load(file).sources[0].sha256 is None
    with pytest.raises(FileNotFoundError):
        ReleaseCatalog.load(tmp_path / "missing")


def test_mock_release_sources_map_to_the_corpus(repo_root: Path) -> None:
    """The release fixture and the sample corpus agree on raw paths (no hash in the fixture)."""
    manifest = CorpusManifest.load(repo_root / "samples" / "corpus")
    catalog = ReleaseCatalog.load(repo_root / "samples" / "fixtures" / "mock-release")
    resolver = SourceResolver(manifest, catalog)
    assert resolver.path_for_id("src-f0757603684a") == (
        "full/chantiers/moreau/3-execution/site-meeting-minutes/"
        "2026-03-24_compte-rendu-de-chantier-n3.docx"
    )
    assert resolver.path_for_id("src-59cf9366e50c") == (
        "held-back/chantiers/moreau/3-execution/schedule/"
        "PLN-2026-003_indice-B_planning-et-suivi-des-achats.xlsx"
    )
    assert resolver.path_for_id("src-000000000000") is None


# -------------------------------------------------------------------------- extraction


def test_extraction_cache_extracts_once_and_reuses(tmp_path: Path, repo_root: Path) -> None:
    corpus_root = repo_root / "samples" / "corpus"
    manifest = CorpusManifest.load(corpus_root)
    # The real corpus path of the window maker's e-mail (slice F layout, ADR 0011).
    real_mail = "full/chantiers/moreau/3-execution/supplier-email/" + MAIL.rsplit("/", 1)[1]
    target = manifest.get(real_mail)
    assert target is not None
    cache = ExtractionCache(corpus_root, tmp_path / "cache")
    docs = asyncio.run(cache.load([target]))
    doc = docs[target.path]
    assert doc.source_id == source_id_for(target.path)
    assert any("BC-2026-009" in block.text for block in doc.blocks)
    cached = list((tmp_path / "cache" / "extract").rglob("*.json"))
    assert len(cached) == 1 and cache.version().startswith("local-")
    again = asyncio.run(ExtractionCache(corpus_root, tmp_path / "cache").load([target]))
    assert again[target.path] == doc
    cached[0].write_text("{}", encoding="utf-8")  # a damaged entry is extracted again
    assert asyncio.run(cache.load([target]))[target.path] == doc


def test_azure_extraction_needs_an_endpoint(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Foundry endpoint"):
        ExtractionCache(tmp_path, tmp_path, mode="azure")
