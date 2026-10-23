import json
import shutil
from datetime import UTC
from pathlib import Path
from types import ModuleType
from urllib.parse import unquote

import pytest

from docwiki.contracts.manifest import CurrentPointer
from docwiki.contracts.markdown import extract_footnotes, extract_links
from docwiki.release import (
    PORTABLE_META_DIR,
    ReleaseIntegrityError,
    ReleaseLayout,
    ReleaseReader,
    export_portable,
    is_portable,
    portable_owned_entries,
    query_tables,
    read_tables_index,
    validate_release,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"
RELEASE = "20260401T090000Z-8a41b109"
PLAN_A, PLAN_B, MINUTES = "src-7630d0741377", "src-59cf9366e50c", "src-f0757603684a"
TOPIC = "topics/planning.md"
CANARY = "DOCWIKI-CANARY-TEST-TOKEN"


@pytest.fixture
def portable(tmp_path: Path) -> Path:
    return export_portable(FIXTURE_ROOT, tmp_path / "wiki")


def snapshot(folder: Path) -> dict[str, bytes]:
    return {
        path.relative_to(folder).as_posix(): path.read_bytes()
        for path in sorted(folder.rglob("*"))
        if path.is_file()
    }


def test_export_layout_and_validation(portable: Path) -> None:
    assert is_portable(portable)
    top = sorted(path.name for path in portable.iterdir())
    assert top == [
        ".agents",
        ".claude",
        ".docwiki",
        ".github",
        "AGENTS.md",
        "_meta",
        "catalog.json",
        "entities",
        "evidence",
        "glossary.md",
        "index.md",
        "llms.txt",
        "log.md",
        "queries",
        "sources",
        "topics",
    ]
    meta = sorted(p.relative_to(portable).as_posix() for p in (portable / ".docwiki").rglob("*"))
    assert meta == [
        ".docwiki/current.json",
        ".docwiki/manifest.json",
        ".docwiki/search.db",
        ".docwiki/tables",
        f".docwiki/tables/{PLAN_B}",
        f".docwiki/tables/{PLAN_B}/index.json",
        f".docwiki/tables/{PLAN_B}/t01.parquet",
        f".docwiki/tables/{PLAN_B}/t02.parquet",
    ]
    release = FIXTURE_ROOT / "releases" / RELEASE
    assert (portable / ".docwiki/manifest.json").read_bytes() == (
        release / "manifest.json"
    ).read_bytes()
    assert (portable / ".docwiki/current.json").read_bytes() == (
        FIXTURE_ROOT / "releases" / "current.json"
    ).read_bytes()
    assert (portable / "catalog.json").read_bytes() == (release / "catalog.json").read_bytes()
    assert not (portable / "wiki").exists() and not (portable / "site").exists()
    assert validate_release(portable, canaries=[CANARY]) == []


def test_reader_on_the_portable_folder(portable: Path) -> None:
    reader = ReleaseReader.open(portable, verify=True)
    assert reader.portable and reader.layout.kind == "portable" and reader.root == portable
    assert reader.release_id == RELEASE and reader.pointer is not None
    assert reader.pointer.manifest_sha256 == reader.manifest_sha256
    assert reader.verify_files() == []
    assert reader.wiki_root == portable and reader.evidence_root == portable / "evidence"
    assert reader.tables_root == portable / PORTABLE_META_DIR / "tables"
    assert reader.search_db_path == portable / PORTABLE_META_DIR / "search.db"
    assert reader.file_for("wiki/index.md") == portable / "index.md"
    assert reader.file_for("site/index.html") is None

    page = reader.read_page("topic:planning")
    assert page.frontmatter.contradictions == 1  # type: ignore[union-attr]
    old_plan = reader.read_page("sources/pln-2026-003-indice-a-planning-et-suivi-des-achats.md")
    assert old_plan.frontmatter.status == "superseded"  # type: ignore[union-attr]
    contradictions = reader.read_section("topic:planning", "Contradictions")
    assert "70 %" in contradictions
    assert {edge.kind for edge in reader.links(PLAN_A)["backlinks"]} >= {"supersedes", "topic-of"}
    evidence = reader.resolve_evidence(MINUTES, "para-0011")
    assert evidence.path == f"evidence/{MINUTES}/para-0011.md" and "20/04/2026" in evidence.body
    assert reader.content_file(evidence.path) == portable / "evidence" / MINUTES / "para-0011.md"
    assert reader.list_evidence(PLAN_A) == [f"evidence/{PLAN_A}/p0001.md"]
    assert len(reader.list_evidence()) == 5

    assert reader.sources_with_tables() == [PLAN_B]
    assert reader.table_file(PLAN_B, "t01") == (
        portable / ".docwiki" / "tables" / PLAN_B / "t01.parquet"
    )
    result = reader.query_table(
        PLAN_B, "SELECT row_id, tache FROM t01 WHERE lot = '5' AND intervenant LIKE 'VanArsdel%'"
    )
    assert result.rows == [["r0008", "T07"]]
    assert read_tables_index(portable, PLAN_B).entry("t01").row_count == 23
    assert query_tables(portable, PLAN_B, "SELECT count(*) FROM t01").rows == [[23]]

    for fallback in (False, True):
        with reader.open_search(force_fallback=fallback) as index:
            hits = index.search("annoncé report", kinds=["source-block"])
            assert (hits[0].source_id, hits[0].locator_key) == (MINUTES, "para-0011")
    assert [skill.name for skill in reader.list_skills()] == [
        "cite-sources",
        "deep-research",
        "wiki-maintainer",
        "wiki-navigator",
    ]
    assert reader.read_skill("wiki-navigator").startswith("---\nname: wiki-navigator\n")


def test_every_link_is_a_plain_relative_file_path(portable: Path) -> None:
    """GitHub, Obsidian and agents resolve links against the file system, without mapping."""
    footnotes = 0
    for file in sorted(portable.rglob("*.md")):
        rel = file.relative_to(portable).as_posix()
        if rel.startswith("."):
            continue
        text = file.read_text(encoding="utf-8")
        _, definitions = extract_footnotes(text)
        for definition in definitions:
            for link in extract_links(definition.content):
                target = (file.parent / unquote(link.href.split("#", 1)[0])).resolve()
                assert target.is_file(), (rel, link.href)
                assert target.is_relative_to(portable.resolve())
                assert target.relative_to(portable.resolve()).as_posix().startswith("evidence/")
                footnotes += 1
        for link in extract_links(text):
            path = unquote(link.href.split("#", 1)[0])
            if path:
                target = (file.parent / path).resolve()
                assert target.is_file() and target.is_relative_to(portable.resolve()), (
                    rel,
                    link.href,
                )
    assert footnotes >= 14


def test_export_is_deterministic_and_idempotent(portable: Path, tmp_path: Path) -> None:
    clean = snapshot(portable)
    again = snapshot(export_portable(FIXTURE_ROOT, tmp_path / "second"))
    assert again == clean

    (portable / "stale.md").write_text("old\n", encoding="utf-8")
    (portable / "sources" / "removed.md").write_text("old\n", encoding="utf-8")
    (portable / ".docwiki" / "old.json").write_text("{}\n", encoding="utf-8")
    old_skill = portable / ".agents" / "skills" / "old-skill"
    old_skill.mkdir()
    (old_skill / "SKILL.md").write_text("old\n", encoding="utf-8")
    kept = {
        ".git/HEAD": "ref: refs/heads/main\n",
        ".obsidian/app.json": "{}\n",
        ".github/workflows/ci.yml": "name: ci\n",
        ".gitignore": "*.tmp\n",
    }
    for rel, text in kept.items():
        (portable / rel).parent.mkdir(parents=True, exist_ok=True)
        (portable / rel).write_bytes(text.encode("utf-8"))
    assert portable / "stale.md" in portable_owned_entries(portable)
    assert portable / ".git" not in portable_owned_entries(portable)

    export_portable(FIXTURE_ROOT, portable)
    after = snapshot(portable)
    for rel, text in kept.items():
        assert after.pop(rel) == text.encode("utf-8")
    assert after == clean


def test_export_from_release_folder_staging_and_portable_inputs(
    portable: Path, tmp_path: Path, builder: ModuleType
) -> None:
    from_release = export_portable(FIXTURE_ROOT / "releases" / RELEASE, tmp_path / "from-release")
    assert snapshot(from_release) == snapshot(portable)
    from_portable = export_portable(portable, tmp_path / "from-portable")
    assert snapshot(from_portable) == snapshot(portable)

    lone = tmp_path / "lone" / RELEASE
    shutil.copytree(FIXTURE_ROOT / "releases" / RELEASE, lone)
    derived = export_portable(lone, tmp_path / "derived")
    pointer = CurrentPointer.from_json((derived / ".docwiki" / "current.json").read_bytes())
    reader = ReleaseReader.open(derived)
    assert pointer.release_id == RELEASE and pointer.manifest_sha256 == reader.manifest_sha256
    assert pointer.created_at == builder.CREATED_AT.astimezone(UTC)
    assert validate_release(derived) == []


def test_export_refuses_unsafe_targets(tmp_path: Path) -> None:
    release = FIXTURE_ROOT / "releases" / RELEASE
    for target in (release, release / "wiki" / "copy", FIXTURE_ROOT / "releases", FIXTURE_ROOT):
        with pytest.raises(ValueError, match="must not"):
            export_portable(FIXTURE_ROOT, target)
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "notes.txt").write_text("keep me\n", encoding="utf-8")
    with pytest.raises(FileExistsError):
        export_portable(FIXTURE_ROOT, busy)
    assert (busy / "notes.txt").is_file()
    export_portable(FIXTURE_ROOT, busy, force=True)
    assert not (busy / "notes.txt").exists() and is_portable(busy)
    with pytest.raises(NotADirectoryError):
        export_portable(FIXTURE_ROOT, busy / "index.md")


def test_export_refuses_tampered_releases(tmp_path: Path, fixture_copy: Path) -> None:
    page = fixture_copy / "releases" / RELEASE / "wiki" / "index.md"
    page.write_text(page.read_text(encoding="utf-8") + "\nedited\n", encoding="utf-8")
    with pytest.raises(ReleaseIntegrityError, match=r"wiki/index\.md"):
        export_portable(fixture_copy, tmp_path / "out")
    pointer = fixture_copy / "releases" / "current.json"
    data = json.loads(pointer.read_text(encoding="utf-8"))
    pointer.write_text(json.dumps({**data, "manifest_sha256": "0" * 64}), encoding="utf-8")
    with pytest.raises(ReleaseIntegrityError, match=r"current\.json"):
        export_portable(fixture_copy, tmp_path / "out2")


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def test_validator_reports_portable_paths(portable: Path) -> None:
    edit(
        portable / TOPIC,
        "(../entities/work-package/lot-3-gros-oeuvre.md)",
        "(../entities/work-package/lot-13-gros-oeuvre.md)",
    )
    (portable / "notes.md").write_text("# Notes\n", encoding="utf-8")
    (portable / ".docwiki" / "search.db").unlink()
    (portable / ".git").mkdir()
    (portable / ".git" / "HEAD").write_text("ref\n", encoding="utf-8")
    found = {(v.gate, v.code, v.path) for v in validate_release(portable)}
    assert ("G02", "link-unresolved", TOPIC) in found
    assert ("G01", "file-hash-mismatch", TOPIC) in found
    assert ("G01", "file-unlisted", "notes.md") in found
    assert ("G01", "frontmatter-invalid", "notes.md") in found
    assert ("G01", "file-missing", ".docwiki/search.db") in found
    assert ("G01", "search-missing", ".docwiki/search.db") in found
    assert not any(path and path.startswith((".git", "wiki/")) for _, _, path in found)
    with pytest.raises(ReleaseIntegrityError):
        ReleaseReader.open(portable, verify=True)


def test_validator_checks_the_pointer_copy(portable: Path) -> None:
    pointer = portable / ".docwiki" / "current.json"
    data = json.loads(pointer.read_text(encoding="utf-8"))
    pointer.write_text(
        json.dumps({**data, "release_id": "20260101T000000Z-00000000", "audience": "internal"}),
        encoding="utf-8",
    )
    found = {(v.code, v.path) for v in validate_release(portable)}
    assert ("pointer-release-mismatch", ".docwiki/current.json") in found
    assert ("pointer-audience-mismatch", ".docwiki/current.json") in found
    pointer.unlink()
    assert validate_release(portable) == []
    assert ReleaseReader.open(portable).pointer is None


def test_layout_path_mapping(tmp_path: Path) -> None:
    release = ReleaseLayout("release", tmp_path / "r")
    folder = ReleaseLayout("portable", tmp_path / "p")
    for rel, expected in (
        ("wiki/sources/a.md", "sources/a.md"),
        ("wiki/.agents/skills/x/SKILL.md", ".agents/skills/x/SKILL.md"),
        ("wiki/catalog.json", "catalog.json"),
        ("catalog.json", "catalog.json"),
        ("evidence/src-0123456789ab/p0001.md", "evidence/src-0123456789ab/p0001.md"),
        ("search.db", ".docwiki/search.db"),
        ("tables/src-0123456789ab/t01.parquet", ".docwiki/tables/src-0123456789ab/t01.parquet"),
        ("manifest.json", ".docwiki/manifest.json"),
    ):
        assert folder.physical(rel) == expected
        assert release.physical(rel) == rel
    assert folder.physical("site/index.html") is None and folder.file_for("site/x") is None
    assert folder.content_file("evidence/src-0123456789ab/p0001.md") == (
        tmp_path / "p" / "evidence" / "src-0123456789ab" / "p0001.md"
    )
    assert release.content_file("sources/a.md") == tmp_path / "r" / "wiki" / "sources" / "a.md"
    assert folder.wiki_display("") == "." and release.wiki_display("") == "wiki"
    assert folder.release_rel_of(tmp_path / "p" / "sources" / "a.md") == "wiki/sources/a.md"
    assert folder.release_rel_of(tmp_path / "p" / ".docwiki" / "search.db") == "search.db"
    assert folder.release_rel_of(tmp_path / "p" / ".docwiki" / "manifest.json") is None
    assert folder.release_rel_of(tmp_path / "p" / ".git" / "HEAD") is None
    assert folder.release_rel_of(tmp_path / "p" / ".github" / "workflows" / "ci.yml") is None
    assert folder.release_rel_of(tmp_path / "p" / ".github" / "skills" / "x" / "SKILL.md") == (
        "wiki/.github/skills/x/SKILL.md"
    )
    with pytest.raises(ValueError):
        folder.content_file("../x.md")
    assert ReleaseLayout.detect(tmp_path) is None
