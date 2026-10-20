import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import ModuleType

import pytest

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.gates import gate_results
from docwiki.contracts.layout import SKILL_PROJECTIONS
from docwiki.contracts.manifest import ReleaseInputs
from docwiki.contracts.pages import EvidencePage, Page
from docwiki.contracts.storage import FolderStorage, StorageError
from docwiki.release import (
    PointerConflictError,
    ReleaseIntegrityError,
    ReleaseReader,
    ReleaseWriter,
    RetentionOutcome,
    TableQueryError,
    apply_retention,
    list_release_ids,
    materialize_release,
    publish_release,
    read_current_pointer,
    rollback,
    swap_current_pointer,
    try_retention,
    validate_release,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"


def staged_copy_of_fixture(
    builder: ModuleType, staging: Path, *, created_at: datetime | None = None
):
    """Rebuild the mock release through ReleaseWriter (exercises every writer API)."""
    source = FIXTURE_ROOT / "releases" / builder.RELEASE_ID
    inputs = ReleaseInputs.from_json(
        json.dumps(
            {
                "sources": json.loads((source / "manifest.json").read_text(encoding="utf-8"))[
                    "inputs"
                ]["sources"]
            }
        )
    )
    writer = ReleaseWriter(
        staging,
        created_at=created_at or builder.CREATED_AT,
        audience=builder.AUDIENCE,
        versions=builder.VERSIONS,
        inputs=inputs,
        run_id=builder.RUN_ID,
    )
    wiki = source / "wiki"
    pages = []
    for file in sorted(wiki.rglob("*")):
        rel = file.relative_to(wiki).as_posix()
        if file.is_dir() or rel == "catalog.json":
            continue
        if rel.endswith(".md") and not any(rel.startswith(p + "/") for p in SKILL_PROJECTIONS):
            page = Page.parse(file.read_text(encoding="utf-8"), rel)
            if writer.release_id != builder.RELEASE_ID:
                page = page.model_copy(
                    update={
                        "frontmatter": page.frontmatter.model_copy(update={"docwiki": writer.stamp})
                    }
                )
            writer.write_page(page)
            pages.append(page)
        else:
            writer.write_wiki_file(rel, file.read_text(encoding="utf-8"))
    for file in sorted((source / "evidence").rglob("*")):
        rel = file.relative_to(source).as_posix()
        if file.suffix == ".md":
            writer.write_evidence(EvidencePage.parse(file.read_text(encoding="utf-8"), rel))
        elif file.is_file():
            writer.copy_file(rel, file)
    catalog = Catalog.from_json((source / "catalog.json").read_bytes())
    writer.write_catalog(catalog.model_copy(update={"release_id": writer.release_id}))
    writer.write_tables(builder.PLAN_B, builder.PLAN_TABLES, "public")
    titles = {
        p.frontmatter.id: (p.frontmatter.title, p.path)
        for p in pages
        if p.frontmatter.type == "source"
    }
    writer.write_search_db(pages, builder._blocks(titles), [("revision", "indice", "fr")])
    return writer, writer.finalize(
        gates=gate_results([], skipped=builder.SKIPPED_GATES), counts={"pages": len(pages)}
    )


def test_writer_rebuilds_the_fixture_and_it_validates(builder: ModuleType, tmp_path: Path) -> None:
    writer, staged = staged_copy_of_fixture(builder, tmp_path / "staging")
    assert staged.release_id == builder.RELEASE_ID == writer.release_id
    assert validate_release(staged.root) == []
    assert "manifest.json" not in staged.manifest.files
    assert (staged.root / "wiki" / "catalog.json").read_bytes() == (
        staged.root / "catalog.json"
    ).read_bytes()
    with pytest.raises(RuntimeError, match="finalized"):
        writer.write_text("wiki/x.md", "x")
    with pytest.raises(RuntimeError, match="finalized"):
        writer.finalize()


def test_writer_guards(builder: ModuleType, tmp_path: Path) -> None:
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "file").write_text("x", encoding="utf-8")
    with pytest.raises(FileExistsError):
        ReleaseWriter(
            occupied, created_at=builder.CREATED_AT, audience="public", versions=builder.VERSIONS
        )
    writer = ReleaseWriter(
        tmp_path / "s", created_at=builder.CREATED_AT, audience="public", versions=builder.VERSIONS
    )
    for bad in ("manifest.json", "../x", "wiki/../x", "other/x.md", "wiki/evidence/x.md", "/abs"):
        with pytest.raises(ValueError):
            writer.write_text(bad, "x")
    with pytest.raises(ValueError, match="CR"):
        writer.write_text("wiki/x.md", "a\r\nb")
    page = Page.parse(
        (FIXTURE_ROOT / "releases" / builder.RELEASE_ID / "wiki" / "index.md").read_text(
            encoding="utf-8"
        ),
        "index.md",
    )
    with pytest.raises(ValueError, match=r"docwiki\.release"):
        writer.write_page(page)
    with pytest.raises(ValueError):
        ReleaseWriter(
            tmp_path / "naive",
            created_at=datetime(2026, 1, 1),
            audience="public",
            versions=builder.VERSIONS,
        )


def test_publish_read_rollback_and_retention(builder: ModuleType, tmp_path: Path) -> None:
    storage = FolderStorage(tmp_path / "store", fsync=False)
    _, first = staged_copy_of_fixture(builder, tmp_path / "s1")
    pointer = publish_release(storage, first, now=builder.CREATED_AT)
    assert (
        pointer.release_id == first.release_id and pointer.manifest_sha256 == first.manifest_sha256
    )
    assert read_current_pointer(storage) is not None
    reader = ReleaseReader.open(storage.root / "releases")
    assert reader.release_id == first.release_id and reader.pointer == pointer
    assert validate_release(storage.root / "releases") == []
    with pytest.raises(FileExistsError):
        publish_release(storage, first)

    _, second = staged_copy_of_fixture(
        builder, tmp_path / "s2", created_at=builder.CREATED_AT + timedelta(days=1)
    )
    assert second.release_id != first.release_id
    publish_release(storage, second)
    assert ReleaseReader.open(storage.root / "releases").release_id == second.release_id
    assert validate_release(storage.root / "releases") == []

    back = rollback(storage, first.release_id)
    assert back.release_id == first.release_id
    assert ReleaseReader.open(storage.root / "releases").release_id == first.release_id

    current, etag = read_current_pointer(storage)  # type: ignore[misc]
    storage.write_bytes("releases/current.json", current.to_json().encode("utf-8") + b" ")
    with pytest.raises(PointerConflictError):
        swap_current_pointer(storage, current, expected_etag=etag)

    for day in range(12):
        stamp = datetime(2025, 1, 1, tzinfo=UTC) + timedelta(days=day)
        storage.write_bytes(
            f"releases/{stamp.strftime('%Y%m%dT%H%M%SZ')}-0000000{day % 10}/manifest.json", b"{}"
        )
    deleted = apply_retention(storage, keep=2)
    assert len(deleted) == 12
    assert list_release_ids(storage) == sorted([first.release_id, second.release_id])
    assert apply_retention(storage, keep=1) == []
    assert first.release_id in list_release_ids(storage)


class _FailingDeletes:
    """Storage whose deletes fail (a transient network error during retention)."""

    def __init__(self, inner: FolderStorage) -> None:
        self.inner = inner

    def delete(self, key: str, *, if_match: str | None = None) -> bool:
        raise StorageError(f"connection reset while deleting {key}")

    def __getattr__(self, name: str) -> object:
        return getattr(self.inner, name)


def test_retention_after_the_pointer_swap_is_best_effort(
    builder: ModuleType, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    storage = FolderStorage(tmp_path / "store", fsync=False)
    _, first = staged_copy_of_fixture(builder, tmp_path / "s1")
    publish_release(storage, first, now=builder.CREATED_AT)
    _, second = staged_copy_of_fixture(
        builder, tmp_path / "s2", created_at=builder.CREATED_AT + timedelta(days=1)
    )
    failing = _FailingDeletes(storage)
    pointer = publish_release(failing, second, keep=1)  # type: ignore[arg-type]
    assert pointer.release_id == second.release_id
    assert read_current_pointer(storage)[0].release_id == second.release_id  # type: ignore[index]
    assert list_release_ids(storage) == sorted([first.release_id, second.release_id])
    assert "release retention failed" in caplog.text
    outcome = try_retention(failing, keep=1)  # type: ignore[arg-type]
    assert outcome.deleted == [] and outcome.error and "StorageError" in outcome.error
    assert try_retention(storage, keep=1) == RetentionOutcome(deleted=[first.release_id])
    _, third = staged_copy_of_fixture(
        builder, tmp_path / "s3", created_at=builder.CREATED_AT + timedelta(days=2)
    )
    publish_release(storage, third, keep=None)
    assert list_release_ids(storage) == sorted([second.release_id, third.release_id])


def test_publish_refuses_failing_blocking_gates(builder: ModuleType, tmp_path: Path) -> None:
    from docwiki.contracts.gates import Violation

    _, staged = staged_copy_of_fixture(builder, tmp_path / "s")
    failing = gate_results([Violation(gate="G02", code="link-unresolved", message="x")])
    bad = staged.manifest.model_copy(update={"gates": failing})
    with pytest.raises(ValueError, match="G02"):
        publish_release(
            FolderStorage(tmp_path / "store", fsync=False),
            type(staged)(staged.root, bad, staged.manifest_sha256),
        )


def test_materialize_release_verifies_hashes(builder: ModuleType, tmp_path: Path) -> None:
    storage = FolderStorage(tmp_path / "store", fsync=False)
    _, staged = staged_copy_of_fixture(builder, tmp_path / "s")
    pointer = publish_release(storage, staged)
    local = materialize_release(
        storage,
        staged.release_id,
        tmp_path / "cache",
        expected_manifest_sha256=pointer.manifest_sha256,
    )
    assert validate_release(local) == []
    with pytest.raises(ReleaseIntegrityError):
        materialize_release(
            storage, staged.release_id, tmp_path / "cache2", expected_manifest_sha256="0" * 64
        )
    storage.write_bytes(f"releases/{staged.release_id}/wiki/index.md", b"tampered")
    with pytest.raises(ReleaseIntegrityError, match=r"wiki/index\.md"):
        materialize_release(storage, staged.release_id, tmp_path / "cache3")


def test_reader_api_on_the_fixture(builder: ModuleType) -> None:
    for location in (
        FIXTURE_ROOT,
        FIXTURE_ROOT / "releases",
        FIXTURE_ROOT / "releases" / builder.RELEASE_ID,
    ):
        assert ReleaseReader.open(location).release_id == builder.RELEASE_ID
    reader = ReleaseReader.open(FIXTURE_ROOT)
    assert reader.audience == "public"
    assert {page.type for page in reader.list_pages()} == {
        "index",
        "source",
        "entity",
        "topic",
        "query",
        "meta",
        "glossary",
        "log",
    }
    topic_ids = [page.id for page in reader.list_pages("topic")]
    assert topic_ids == ["topic:schedule-and-window-delivery"]
    by_id = reader.read_page("topic:schedule-and-window-delivery")
    assert by_id == reader.read_page("topics/schedule-and-window-delivery.md")
    assert by_id.frontmatter.contradictions == 1  # type: ignore[union-attr]
    section = reader.read_section("topic:schedule-and-window-delivery", "contradictions")
    assert section.startswith("## Contradictions\n") and "70 %" in section and "100 %" in section
    with pytest.raises(KeyError):
        reader.read_section("topic:schedule-and-window-delivery", "Nope")
    with pytest.raises(KeyError):
        reader.read_page("topic:missing")
    links = reader.links(builder.PLAN_A)
    assert {(e.to, e.kind) for e in links["outgoing"]} >= {
        ("organisation:vanarsdel-menuiseries", "mentions")
    }
    assert {(e.from_, e.kind) for e in links["backlinks"]} >= {
        (builder.PLAN_B, "supersedes"),
        ("topic:schedule-and-window-delivery", "topic-of"),
    }

    evidence = reader.resolve_evidence(builder.PLAN_B, "sheet-planning-r0006-r0009")
    assert evidence.frontmatter.provenance == "deterministic-table"
    assert "## Row 8" in evidence.body and evidence.original is None
    with pytest.raises(KeyError):
        reader.resolve_evidence(builder.PLAN_B, "sheet-planning-r0009-r0009")
    with pytest.raises(ValueError):
        reader.resolve_evidence(builder.PLAN_B, "../x")
    assert reader.list_evidence(builder.PLAN_A) == [f"evidence/{builder.PLAN_A}/p0001.md"]
    assert len(reader.list_evidence()) == 5

    skills = reader.list_skills()
    assert [skill.name for skill in skills] == [
        "cite-sources",
        "deep-research",
        "wiki-maintainer",
        "wiki-navigator",
    ]
    assert reader.read_skill("cite-sources").startswith("---\nname: cite-sources\n")
    with pytest.raises(KeyError):
        reader.read_skill("unknown")


@pytest.mark.parametrize("fallback", [False, True])
def test_reader_search_on_the_fixture(builder: ModuleType, fallback: bool) -> None:
    with ReleaseReader.open(FIXTURE_ROOT).open_search(force_fallback=fallback) as index:
        hits = index.search("window delivery postponed")
        assert hits[0].page_id in {builder.PLAN_B, "topic:schedule-and-window-delivery"}
        block = index.search("annoncé report", kinds=["source-block"])[0]
        assert (block.source_id, block.locator_key) == (builder.MINUTES, "para-0011")
        assert index.search("joinery")[0].page_id in {
            "work-package:lot-5-menuiseries-exterieures",
            "glossary",
        }


def test_tables_and_queries(builder: ModuleType) -> None:
    reader = ReleaseReader.open(FIXTURE_ROOT)
    index = reader.tables(builder.PLAN_B)
    assert [entry.id for entry in index.tables] == ["t01", "t02"]
    assert index.entry("t01").row_count == 23
    entry = index.entry("t02")
    assert [(c.name, c.header, c.type) for c in entry.columns] == [
        ("n_commande", "N° commande", "VARCHAR"),
        ("date", "Date", "VARCHAR"),
        ("fournisseur", "Fournisseur", "VARCHAR"),
        ("objet", "Objet", "VARCHAR"),
        ("commande_ht", "Commandé HT", "DOUBLE"),
        ("facture_ht", "Facturé HT", "DOUBLE"),
        ("statut", "Statut", "VARCHAR"),
    ]
    assert entry.row_ids[:3] == ["r0002", "r0003", "r0004"] and entry.locator.kind == "xlsx-rows"
    assert reader.table_file(builder.PLAN_B, "t01").is_file()
    result = reader.query_table(
        builder.PLAN_B,
        "SELECT row_id, n_commande, facture_ht FROM t02 "
        "WHERE n_commande LIKE 'BC-%' AND facture_ht > 900 ORDER BY row_id",
    )
    assert result.columns == ["row_id", "n_commande", "facture_ht"]
    assert result.rows == [
        ["r0003", "BC-2026-009", 996.0],
        ["r0004", "BC-2026-010", 4386.5],
        ["r0005", "BC-2026-012", 1484.8],
    ]
    assert not result.truncated
    assert reader.query_table(builder.PLAN_B, "SELECT * FROM t01", max_rows=2).truncated
    for bad in (
        "DELETE FROM t01",
        "SELECT 1; SELECT 2",
        "COPY t01 TO 'x.csv'",
        "SELECT * FROM read_csv('x.csv')",
        "SET lock_configuration = false",
        "not sql",
    ):
        with pytest.raises(TableQueryError):
            reader.query_table(builder.PLAN_B, bad)
    with pytest.raises(KeyError):
        reader.tables(builder.PLAN_A)
