"""Source mapping (hash, source id, path, title), locators, evidence text and extraction cache."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
from evals.corpus import CorpusContext, CorpusManifest, ExtractionCache, ReleaseCatalog
from evals.locators import compact_keys, is_key, keys_match, locator_key_from_label
from evals.records import Citation
from evals_testkit import (
    CHECKLIST,
    DECK,
    LOG,
    MAIL,
    MANUAL,
    NOTE,
    QS_MANUAL,
    RATES,
    SOP,
    STOCK,
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
    assert MANUAL in full and RATES not in full
    assert all(path.startswith("full/") for path in full)
    assert RATES in {entry.path for entry in manifest.select("full", "restricted")}
    assert [entry.path for entry in manifest.select("quickstart")] == [MANUAL, MAIL, CHECKLIST]
    assert not any(entry.held_back for entry in manifest.select("all", "restricted"))
    with pytest.raises(ValueError, match="unknown corpus scope"):
        manifest.select("everything")


def test_manifest_canonical_copies_and_hashes(corpus: CorpusContext) -> None:
    manifest = corpus.manifest
    assert manifest.canonical(QS_MANUAL) == MANUAL
    assert manifest.canonical(MANUAL) == MANUAL
    assert manifest.by_sha256("sha256:" + file_sha(MANUAL)) == MANUAL
    assert manifest.by_sha256(file_sha(MANUAL).upper()) == MANUAL
    assert manifest.sensitivity(RATES) == "restricted"
    assert QS_MANUAL not in {entry.path for entry in manifest.documents()}


def test_real_manifest_loads(repo_root: Path) -> None:
    manifest = CorpusManifest.load(repo_root / "samples" / "corpus")
    assert len(manifest.sha256) == 64
    assert len(manifest.select("quickstart")) == 12
    assert all(entry.copy_of is None for entry in manifest.select("quickstart"))
    restricted = [entry for entry in manifest.documents() if entry.sensitivity == "restricted"]
    assert restricted and not set(restricted) & set(manifest.select("full", "public"))


# ------------------------------------------------------------------------------ resolver


def _resolve(
    corpus: CorpusContext, citation: Citation
) -> tuple[str | None, str | None, str | None]:
    resolved = corpus.resolver.resolve(citation, unit="1")
    return resolved.path, resolved.locator_key, resolved.via


@pytest.mark.parametrize(
    "raw_path",
    [
        MANUAL,
        QS_MANUAL,
        MANUAL.removeprefix("full/"),
        "LWS-MM-GBX-32_RevD_manual.pdf",
        "samples/corpus/" + MANUAL,
    ],
)
def test_source_ids_derived_from_deployment_paths(corpus: CorpusContext, raw_path: str) -> None:
    """A release built from full/, from its content or from the repository maps back to full/."""
    citation = Citation(source_id=source_id_for(raw_path), locator_key="p0003")
    assert _resolve(corpus, citation) == (MANUAL, "p0003", "source_id")


def test_hash_mapping_through_the_release_catalog() -> None:
    corpus = mini_corpus(renamed_catalog())
    path, key, via = _resolve(corpus, Citation(source_id="src-0123456789ab", locator_key="p0004"))
    assert (path, key, via) == (MANUAL, "p0004", "source_id")
    # the stock list has no hash in that catalog and an unknown raw path: unresolved
    assert _resolve(corpus, Citation(source_id="src-ba9876543210", locator_key="p0001"))[0] is None
    # catalog source titles also identify sources
    title = Citation(title="Gearbox manual (LT-32, Rev. D)", label="p. 3")
    assert _resolve(corpus, title) == (MANUAL, "p0003", "title")


def test_sha256_wins_and_quickstart_copies_are_canonical(corpus: CorpusContext) -> None:
    citation = Citation(sha256="sha256:" + file_sha(QS_MANUAL), locator_key="p0003")
    assert _resolve(corpus, citation) == (MANUAL, "p0003", "sha256")
    assert _resolve(corpus, cite(QS_MANUAL, "p0001"))[0] == MANUAL


@pytest.mark.parametrize(
    ("raw_path", "expected"),
    [
        (STOCK, STOCK),
        ("records/spare-parts-stock-2026-07-21.xlsx", STOCK),
        ("raw/full/records/spare-parts-stock-2026-07-21.xlsx", STOCK),
        ("full\\records\\spare-parts-stock-2026-07-21.xlsx", STOCK),
        ("./" + STOCK, STOCK),
        ("unknown/file.pdf", None),
        ("", None),
    ],
)
def test_path_mapping(corpus: CorpusContext, raw_path: str, expected: str | None) -> None:
    assert corpus.resolver.path_for(raw_path) == expected


def test_manifest_titles_identify_sources(corpus: CorpusContext) -> None:
    citation = Citation(
        title="RE: Applicability of SB-LWS-2025-07 to Quellmoor Ridge",
        label="message body, lines 10–12",
    )
    assert _resolve(corpus, citation) == (MAIL, "msg-body-l0010-l0012", "title")


def test_unresolvable_citation(corpus: CorpusContext) -> None:
    resolved = corpus.resolver.resolve(Citation(label="p. 3"), unit="[4]")
    assert not resolved.resolved and resolved.unit == "[4]" and resolved.via is None


def test_restricted_sources_carry_their_sensitivity(corpus: CorpusContext) -> None:
    resolved = corpus.resolver.resolve(cite(RATES, "sheet-rates-2026-r0002-r0002"), unit="1")
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
        ("sheet-stock-r0002-r0002", "sheet-stock-r0001-r0024", True),
        ("sheet-stock-r0002-r0002", "sheet-movements-r0002-r0002", False),
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
    assert compact_keys(["sheet-stock-r0001-r0001", "sheet-stock-r0002-r0002"]) == [
        "sheet-stock-r0001-r0002"
    ]
    assert compact_keys(["sheet-stock-r0002-r0002", "sheet-movements-r0003-r0003"]) == [
        "sheet-stock-r0002-r0002",
        "sheet-movements-r0003-r0003",
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
        ('sheet "Stock", rows 12–20', "sheet-stock-r0012-r0020"),
        ('sheet "Plan 2026", row 4', "sheet-plan-2026-r0004-r0004"),
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

    csv_doc = with_table(LOG, CsvRowsLocator(row_start=1, row_end=5))
    assert locator_key_from_label("table t01, rows r0002–r0004", doc=csv_doc) == "r0002-r0004"
    assert locator_key_from_label("table t01, row r0003", doc=csv_doc) == "r0003-r0003"
    assert locator_key_from_label("table t09, rows r0002–r0004", doc=csv_doc) is None
    assert locator_key_from_label("table t01, rows r0002–r0004") is None
    sheet_doc = with_table(STOCK, XlsxRowsLocator(sheet="Stock", row_start=1, row_end=24))
    label = "table t01, rows r0002–r0004"
    assert locator_key_from_label(label, doc=sheet_doc) == "sheet-stock-r0002-r0004"
    docx_doc = with_table(SOP, DocxTableLocator(table=2, row_start=1, row_end=3))
    assert locator_key_from_label(label, doc=docx_doc) == "tbl-02-r0002-r0004"


# ------------------------------------------------------------------------------ evidence


def test_evidence_text_at_metric_granularity(corpus: CorpusContext) -> None:
    evidence = corpus.evidence
    page = evidence.text(MANUAL, "p0003") or ""
    assert "410 L" in page and "PWG 320" in page and "4.5 mm/s" not in page
    rows = evidence.text(STOCK, "sheet-stock-r0001-r0003") or ""
    assert "FGT-P-22328" in rows and "LWS-P-30418" in rows and "FGT-P-11872" not in rows
    assert "CCV" in (evidence.text(MAIL, "msg-body") or "")
    assert "KW 40" in (evidence.text(NOTE, "l0010-l0010") or "")
    assert "300 metres" in (evidence.text(TALK, "cue-00-02-01") or "")
    assert "high-speed" in (evidence.text(DECK, "slide-04") or "")
    assert "280 Nm" in (evidence.text(SOP, "tbl-02-r0002-r0003") or "")
    assert evidence.text(CHECKLIST, "*") == ""  # OCR without OCR: the locator exists, no text
    assert evidence.text(MANUAL, "p0009") is None
    assert evidence.text("full/unknown.pdf", "p0001") is None


def test_restricted_fingerprint(corpus: CorpusContext) -> None:
    assert corpus.fingerprint == {"18400", "42000", "ts-600c-02"}


# ---------------------------------------------------------------------------- catalog io


def test_release_catalog_loading(tmp_path: Path, repo_root: Path) -> None:
    mock = repo_root / "samples" / "fixtures" / "mock-release"
    for location in (mock, mock / "releases"):
        catalog = ReleaseCatalog.load(location)
        assert catalog.release_id == "20260215T090000Z-decd4b59"
        assert catalog.audience == "public"
        assert {source.source_id for source in catalog.sources} == {
            "src-43c97f7dfcde",
            "src-4d9c65e05302",
            "src-f2750f41f3fa",
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


# -------------------------------------------------------------------------- extraction


def test_extraction_cache_extracts_once_and_reuses(tmp_path: Path, repo_root: Path) -> None:
    corpus_root = repo_root / "samples" / "corpus"
    manifest = CorpusManifest.load(corpus_root)
    target = manifest.get("full/field/2026-08-03_lieferantenhinweis-fabrikam.txt")
    assert target is not None
    cache = ExtractionCache(corpus_root, tmp_path / "cache")
    docs = asyncio.run(cache.load([target]))
    doc = docs[target.path]
    assert doc.source_id == source_id_for(target.path)
    assert any("PO-76994" in block.text for block in doc.blocks)
    cached = list((tmp_path / "cache" / "extract").rglob("*.json"))
    assert len(cached) == 1 and cache.version().startswith("local-")
    again = asyncio.run(ExtractionCache(corpus_root, tmp_path / "cache").load([target]))
    assert again[target.path] == doc
    cached[0].write_text("{}", encoding="utf-8")  # a damaged entry is extracted again
    assert asyncio.run(cache.load([target]))[target.path] == doc


def test_azure_extraction_needs_an_endpoint(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Foundry endpoint"):
        ExtractionCache(tmp_path, tmp_path, mode="azure")
