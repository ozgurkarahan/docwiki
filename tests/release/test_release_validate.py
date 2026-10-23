import json
import shutil
import zlib
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import pytest

from docwiki.contracts.manifest import ReleaseManifest
from docwiki.release import validate_release

FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"

RELEASE = "20260401T090000Z-8a41b109"
PLAN_A, PLAN_B, MINUTES = "src-7630d0741377", "src-59cf9366e50c", "src-f0757603684a"
TOPIC = "topics/planning.md"
PLAN_A_PAGE = "sources/pln-2026-003-indice-a-planning-et-suivi-des-achats.md"
PLAN_B_PAGE = "sources/pln-2026-003-indice-b-planning-et-suivi-des-achats.md"
LOT_3 = "entities/work-package/lot-3-gros-oeuvre.md"
QUERY_LINK = "(queries/2026-03-31-window-delivery-date.md)"
QUERY_TITLE = "[When are the windows of the extension delivered?]"


def png_pixels(path: Path) -> tuple[bytes, bytes]:
    """IHDR and decompressed IDAT of a PNG (compressed bytes depend on the zlib build)."""
    data = path.read_bytes()
    position, header, idat = 8, b"", b""
    while position < len(data):
        length = int.from_bytes(data[position : position + 4], "big")
        tag = data[position + 4 : position + 8]
        body = data[position + 8 : position + 8 + length]
        if tag == b"IHDR":
            header = body
        elif tag == b"IDAT":
            idat += body
        position += 12 + length
    return header, zlib.decompress(idat)


def test_committed_fixture_is_valid() -> None:
    assert validate_release(FIXTURE_ROOT, canaries=["DOCWIKI-CANARY-TEST-TOKEN"]) == []
    assert validate_release(FIXTURE_ROOT / "releases" / RELEASE) == []


def test_fixture_rebuild_is_reproducible(builder: ModuleType, tmp_path: Path) -> None:
    out = builder.copy_sources(tmp_path / "rebuilt")
    assert not (out / "releases" / RELEASE / "manifest.json").exists()
    assert builder.build(out) == []
    rebuilt = out / "releases" / RELEASE
    committed = FIXTURE_ROOT / "releases" / RELEASE
    for rel in ("catalog.json", "wiki/catalog.json", f"tables/{PLAN_B}/index.json"):
        assert (rebuilt / rel).read_bytes() == (committed / rel).read_bytes(), rel
    image = f"evidence/{PLAN_A}/img/p0001.png"
    assert png_pixels(rebuilt / image) == png_pixels(committed / image)
    rebuilt_files = ReleaseManifest.from_json((rebuilt / "manifest.json").read_bytes()).files
    committed_files = ReleaseManifest.from_json((committed / "manifest.json").read_bytes()).files
    assert set(rebuilt_files) == set(committed_files)
    for rel, entry in committed_files.items():
        if rel.endswith(".md") or rel.endswith(".txt"):
            assert rebuilt_files[rel] == entry, rel


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, (path, old)
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


Mutation = Callable[[Path], None]


def wiki(root: Path, rel: str) -> Path:
    return root / "releases" / RELEASE / "wiki" / rel


def release_file(root: Path, rel: str) -> Path:
    return root / "releases" / RELEASE / rel


MUTATIONS: dict[str, tuple[Mutation, str, str]] = {
    "broken link": (
        lambda r: edit(
            wiki(r, TOPIC),
            "(../entities/work-package/lot-3-gros-oeuvre.md)",
            "(../entities/work-package/lot-13-gros-oeuvre.md)",
        ),
        "G02",
        "link-unresolved",
    ),
    "broken anchor": (
        lambda r: edit(
            wiki(r, "index.md"),
            "(topics/planning.md)",
            "(topics/planning.md#nope)",
        ),
        "G02",
        "anchor-unresolved",
    ),
    "escaping link": (
        lambda r: edit(wiki(r, "index.md"), "(glossary.md)", "(../../glossary.md)"),
        "G02",
        "link-invalid",
    ),
    "undefined footnote": (
        lambda r: edit(wiki(r, LOT_3), "task T05, the walls.[^c1]", "task T05, the walls.[^c9]"),
        "G02",
        "footnote-undefined",
    ),
    "footnote order": (
        lambda r: edit(
            wiki(r, TOPIC), '"Pose des menuiseries").[^c1]', '"Pose des menuiseries").[^c3]'
        ),
        "G03",
        "footnote-order",
    ),
    "citation label": (
        lambda r: edit(wiki(r, PLAN_A_PAGE), "indice A — p. 1](", "indice A — p. 2]("),
        "G03",
        "citation-label",
    ),
    "dishonest badge": (
        lambda r: edit(wiki(r, PLAN_A_PAGE), "p0001.md) · ✓ quote verified", "p0001.md) · table"),
        "G03",
        "citation-badge",
    ),
    "citation title": (
        lambda r: edit(
            wiki(r, PLAN_A_PAGE),
            "[^c1]: [Planning and purchase tracking, indice A",
            "[^c1]: [Old schedule",
        ),
        "G03",
        "citation-title",
    ),
    "uncited key fact": (
        lambda r: edit(
            wiki(r, PLAN_B_PAGE),
            "indice A of 2026-03-17.[^c1]\n- The reason",
            "indice A of 2026-03-17.\n- The reason",
        ),
        "G03",
        "fact-uncited",
    ),
    "missing sidecar": (
        lambda r: release_file(r, f"evidence/{MINUTES}/para-0011.md").unlink(),
        "G06",
        "sidecar-missing",
    ),
    "external link": (
        lambda r: edit(
            wiki(r, "glossary.md"),
            "A new issue of the same numbered document",
            "See https://example.org/revision. A new issue of the same numbered document",
        ),
        "G05",
        "bare-url",
    ),
    "raw html": (
        lambda r: edit(
            wiki(r, "glossary.md"),
            "A new issue of the same numbered document",
            "<b>A new issue</b> of the same numbered document",
        ),
        "G05",
        "raw-html",
    ),
    "canary": (
        lambda r: edit(wiki(r, "AGENTS.md"), "## Safety", "## Safety\n\nDOCWIKI-CANARY-TEST-TOKEN"),
        "G08",
        "canary-present",
    ),
    "audience": (
        lambda r: edit(wiki(r, LOT_3), "sensitivity: public", "sensitivity: restricted"),
        "G07",
        "page-above-audience",
    ),
    "page tier": (
        lambda r: edit(wiki(r, PLAN_B_PAGE), "sensitivity: public", "sensitivity: internal"),
        "G07",
        "page-tier",
    ),
    "tags": (
        lambda r: edit(
            wiki(r, TOPIC), "tags:\n- schedule\n- windows", "tags:\n- windows\n- schedule"
        ),
        "G12",
        "frontmatter-invalid",
    ),
    "frontmatter": (
        lambda r: edit(wiki(r, TOPIC), "confidence: medium", "confidence: certain"),
        "G01",
        "frontmatter-invalid",
    ),
    "stamp": (
        lambda r: edit(
            wiki(r, "log.md"), f"release: {RELEASE}", "release: 20260101T000000Z-00000000"
        ),
        "G01",
        "stamp-mismatch",
    ),
    "path": (
        lambda r: wiki(r, TOPIC).rename(wiki(r, "topics/Schedule-and-window-delivery.md")),
        "G09",
        "path-invalid",
    ),
    "supersession": (
        lambda r: edit(wiki(r, PLAN_B_PAGE), f"supersedes:\n- {PLAN_A}", "supersedes: []"),
        "G11",
        "supersession-asymmetric",
    ),
    "superseded banner": (
        lambda r: edit(
            wiki(r, PLAN_A_PAGE),
            "> **Superseded** by [Planning and purchase tracking, indice B]"
            "(pln-2026-003-indice-b-planning-et-suivi-des-achats.md). Use the current revision.\n",
            "",
        ),
        "G11",
        "superseded-banner",
    ),
    "skills projection": (
        lambda r: edit(
            wiki(r, ".claude/skills/deep-research/SKILL.md"), "12 tool calls", "20 tool calls"
        ),
        "G14",
        "skills-projection-mismatch",
    ),
    "core skill": (
        lambda r: [
            shutil.rmtree(wiki(r, f"{p}/skills/wiki-maintainer"))
            for p in (".agents", ".claude", ".github")
        ],
        "G14",
        "core-skill-missing",
    ),
    "manifest hash": (
        lambda r: edit(wiki(r, "llms.txt"), "## Topics", "## Topics\n"),
        "G01",
        "file-hash-mismatch",
    ),
    "unlisted file": (
        lambda r: release_file(r, "wiki/topics/extra.txt").write_text("x\n", encoding="utf-8"),
        "G01",
        "file-unlisted",
    ),
    "catalog copy": (
        lambda r: edit(
            release_file(r, "wiki/catalog.json"), '"audience": "public"', '"audience": "public" '
        ),
        "G01",
        "catalog-copy-mismatch",
    ),
    "catalog page": (
        lambda r: edit(
            release_file(r, "catalog.json"), '"title": "Lot 3 - Gros œuvre"', '"title": "Lot three"'
        ),
        "G01",
        "catalog-page-mismatch",
    ),
    "pointer": (
        lambda r: (r / "releases" / "current.json").write_text(
            json.dumps(
                {
                    **json.loads((r / "releases" / "current.json").read_text(encoding="utf-8")),
                    "manifest_sha256": "0" * 64,
                }
            ),
            encoding="utf-8",
        ),
        "G01",
        "pointer-hash-mismatch",
    ),
    "unknown tables": (
        lambda r: shutil.copytree(
            release_file(r, f"tables/{PLAN_B}"), release_file(r, "tables/src-000000000000")
        ),
        "G07",
        "tables-unknown-source",
    ),
    "orphans": (
        lambda r: [
            edit(wiki(r, "index.md"), f"- 2026-04-01 query: {QUERY_TITLE}{QUERY_LINK}\n", ""),
            edit(wiki(r, "log.md"), f"- {QUERY_TITLE}{QUERY_LINK}\n", ""),
        ],
        "G13",
        "orphan-pages",
    ),
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_validator_detects_mutation(fixture_copy: Path, name: str) -> None:
    mutate, gate, code = MUTATIONS[name]
    mutate(fixture_copy)
    violations = validate_release(fixture_copy, canaries=["DOCWIKI-CANARY-TEST-TOKEN"])
    found = {(v.gate, v.code) for v in violations}
    assert (gate, code) in found, [(v.gate, v.code, v.path, v.line, v.message) for v in violations]


def test_violation_lines_are_file_relative(fixture_copy: Path) -> None:
    target = wiki(fixture_copy, TOPIC)
    edit(
        target,
        "(../entities/work-package/lot-3-gros-oeuvre.md)",
        "(../entities/work-package/lot-13-gros-oeuvre.md)",
    )
    expected = next(
        n
        for n, line in enumerate(target.read_text(encoding="utf-8").split("\n"), 1)
        if "lot-13" in line
    )
    violation = next(v for v in validate_release(fixture_copy) if v.code == "link-unresolved")
    assert violation.line == expected and violation.path == f"wiki/{TOPIC}"
    assert (
        next(v for v in validate_release(fixture_copy) if v.code == "file-hash-mismatch").gate
        == "G01"
    )


def test_candidate_release_validation_without_manifest(fixture_copy: Path) -> None:
    release = fixture_copy / "releases" / RELEASE
    (release / "manifest.json").unlink()
    (fixture_copy / "releases" / "current.json").unlink()
    assert validate_release(release, require_manifest=False, audience="public") == []
    codes = {v.code for v in validate_release(release)}
    assert codes == {"manifest-missing"}
    restricted = validate_release(
        release, require_manifest=False, audience="public", glossary_seeded=True
    )
    assert restricted == []
    catalog = json.loads((release / "catalog.json").read_text(encoding="utf-8"))
    catalog["glossary"] = []
    text = json.dumps(catalog, ensure_ascii=False, indent=2) + "\n"
    (release / "catalog.json").write_text(text, encoding="utf-8")
    (release / "wiki" / "catalog.json").write_text(text, encoding="utf-8")
    assert ("G10", "glossary-empty") in {
        (v.gate, v.code)
        for v in validate_release(release, require_manifest=False, glossary_seeded=True)
    }


def test_missing_release_folder(tmp_path: Path) -> None:
    (tmp_path / "releases").mkdir()
    pointer = (FIXTURE_ROOT / "releases" / "current.json").read_text(encoding="utf-8")
    (tmp_path / "releases" / "current.json").write_text(pointer, encoding="utf-8")
    assert [v.code for v in validate_release(tmp_path)] == ["release-missing"]
