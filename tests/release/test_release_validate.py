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

RELEASE = "20260215T090000Z-decd4b59"
SOP_A, SOP_B, PLAN = "src-f2750f41f3fa", "src-4d9c65e05302", "src-43c97f7dfcde"


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
    for rel in ("catalog.json", "wiki/catalog.json", f"tables/{PLAN}/index.json"):
        assert (rebuilt / rel).read_bytes() == (committed / rel).read_bytes(), rel
    image = f"evidence/{SOP_A}/img/p0001.png"
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
            wiki(r, "topics/gearbox-oil.md"),
            "(../entities/asset/wtg-12.md)",
            "(../entities/asset/wtg-13.md)",
        ),
        "G02",
        "link-unresolved",
    ),
    "broken anchor": (
        lambda r: edit(
            wiki(r, "index.md"), "(topics/gearbox-oil.md)", "(topics/gearbox-oil.md#nope)"
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
        lambda r: edit(wiki(r, "entities/asset/wtg-12.md"), "2026-05.[^c1]", "2026-05.[^c2]"),
        "G02",
        "footnote-undefined",
    ),
    "footnote order": (
        lambda r: edit(
            wiki(r, "topics/gearbox-oil.md"), "below -20 °C.[^c1]", "below -20 °C.[^c3]"
        ),
        "G03",
        "footnote-order",
    ),
    "citation label": (
        lambda r: edit(wiki(r, "sources/sop-gbx-010-rev-a.md"), "rev A — p. 1](", "rev A — p. 2]("),
        "G03",
        "citation-label",
    ),
    "dishonest badge": (
        lambda r: edit(
            wiki(r, "sources/sop-gbx-010-rev-a.md"),
            "p0001.md) · ✓ quote verified",
            "p0001.md) · table",
        ),
        "G03",
        "citation-badge",
    ),
    "citation title": (
        lambda r: edit(
            wiki(r, "sources/sop-gbx-010-rev-a.md"),
            "[^c1]: [Gearbox oil change SOP rev A",
            "[^c1]: [Old SOP",
        ),
        "G03",
        "citation-title",
    ),
    "uncited key fact": (
        lambda r: edit(
            wiki(r, "sources/maintenance-plan-2026.md"),
            "(6 hours).[^c1]\n- WTG-12",
            "(6 hours).\n- WTG-12",
        ),
        "G03",
        "fact-uncited",
    ),
    "missing sidecar": (
        lambda r: release_file(r, f"evidence/{SOP_B}/para-0004.md").unlink(),
        "G06",
        "sidecar-missing",
    ),
    "external link": (
        lambda r: edit(
            wiki(r, "glossary.md"), "Standard operating procedure.", "See https://example.org/sop."
        ),
        "G05",
        "bare-url",
    ),
    "raw html": (
        lambda r: edit(
            wiki(r, "glossary.md"), "Standard operating procedure.", "<b>Standard</b> procedure."
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
        lambda r: edit(
            wiki(r, "entities/asset/wtg-12.md"), "sensitivity: public", "sensitivity: restricted"
        ),
        "G07",
        "page-above-audience",
    ),
    "page tier": (
        lambda r: edit(
            wiki(r, "sources/maintenance-plan-2026.md"),
            "sensitivity: public",
            "sensitivity: internal",
        ),
        "G07",
        "page-tier",
    ),
    "tags": (
        lambda r: edit(
            wiki(r, "topics/gearbox-oil.md"), "tags:\n- gearbox\n- oil", "tags:\n- oil\n- gearbox"
        ),
        "G12",
        "frontmatter-invalid",
    ),
    "frontmatter": (
        lambda r: edit(
            wiki(r, "topics/gearbox-oil.md"), "confidence: medium", "confidence: certain"
        ),
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
        lambda r: wiki(r, "topics/gearbox-oil.md").rename(wiki(r, "topics/Gearbox-oil.md")),
        "G09",
        "path-invalid",
    ),
    "supersession": (
        lambda r: edit(
            wiki(r, "sources/sop-gbx-010-rev-b.md"), f"supersedes:\n- {SOP_A}", "supersedes: []"
        ),
        "G11",
        "supersession-asymmetric",
    ),
    "superseded banner": (
        lambda r: edit(
            wiki(r, "sources/sop-gbx-010-rev-a.md"),
            "> **Superseded** by [Gearbox oil change SOP rev B](sop-gbx-010-rev-b.md). "
            "Use the current revision.\n",
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
            release_file(r, "catalog.json"), '"title": "WTG-12"', '"title": "WTG twelve"'
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
            release_file(r, f"tables/{PLAN}"), release_file(r, "tables/src-000000000000")
        ),
        "G07",
        "tables-unknown-source",
    ),
    "orphans": (
        lambda r: [
            edit(
                wiki(r, "entities/asset/index.md"),
                "- [WTG-12](wtg-12.md): gearbox oil change planned for 2026-05\n",
                "",
            ),
            edit(
                wiki(r, "llms.txt"),
                "- [WTG-12](entities/asset/wtg-12.md): gearbox oil change planned for 2026-05\n",
                "",
            ),
            edit(
                wiki(r, "sources/maintenance-plan-2026.md"),
                ", [WTG-12](../entities/asset/wtg-12.md)",
                "",
            ),
            edit(wiki(r, "topics/gearbox-oil.md"), ", [WTG-12](../entities/asset/wtg-12.md)", ""),
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
    target = wiki(fixture_copy, "topics/gearbox-oil.md")
    edit(target, "(../entities/asset/wtg-12.md)", "(../entities/asset/wtg-13.md)")
    expected = next(
        n
        for n, line in enumerate(target.read_text(encoding="utf-8").split("\n"), 1)
        if "wtg-13" in line
    )
    violation = next(v for v in validate_release(fixture_copy) if v.code == "link-unresolved")
    assert violation.line == expected and violation.path == "wiki/topics/gearbox-oil.md"
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
