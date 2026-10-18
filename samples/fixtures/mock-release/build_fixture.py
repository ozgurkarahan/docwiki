"""Rebuild the machine files of the hand-made mock release and validate it.

The Markdown (wiki pages, evidence sidecars, skills, llms.txt) is written by hand and committed.
This script regenerates everything derived from it: the page image of the PDF sidecar, the
Parquet table, ``catalog.json`` (release root and ``wiki/``), ``search.db``, ``manifest.json``
and ``current.json``; then it runs ``validate_release`` and fails on any violation.

    uv run python samples/fixtures/mock-release/build_fixture.py            # rebuild in place
    uv run python samples/fixtures/mock-release/build_fixture.py --out DIR  # rebuild a copy

All content is fictional (CC BY 4.0).
"""

from __future__ import annotations

import argparse
import shutil
import struct
import sys
import zlib
from datetime import UTC, datetime
from pathlib import Path

from docwiki.contracts.catalog import (
    Catalog,
    CatalogEdge,
    CatalogGlossaryEntry,
    catalog_page_for,
    catalog_source_for,
)
from docwiki.contracts.extracted import Table, TableRow
from docwiki.contracts.gates import gate_results
from docwiki.contracts.layout import SKILL_PROJECTIONS, ReleaseFiles
from docwiki.contracts.locators import XlsxRowsLocator
from docwiki.contracts.manifest import CurrentPointer, ReleaseInputs, ReleaseManifest
from docwiki.contracts.markdown import (
    extract_footnotes,
    extract_links,
    resolve_href,
    split_sections,
)
from docwiki.contracts.pages import (
    EntityFrontmatter,
    Page,
    QueryFrontmatter,
    SourceFrontmatter,
    TopicFrontmatter,
)
from docwiki.contracts.runs import VersionInfo
from docwiki.release.tables import write_source_tables
from docwiki.release.validate import validate_release
from docwiki.release.writer import hash_release_files
from docwiki.search.index import SearchBlock, build_search_db

HERE = Path(__file__).resolve().parent
RELEASE_ID = "20260215T090000Z-decd4b59"
CREATED_AT = datetime(2026, 2, 15, 9, 0, 0, tzinfo=UTC)
AUDIENCE = "public"
RUN_ID = "run-20260215-090000-0a1b2c3d"
VERSIONS = VersionInfo(
    docwiki="0.1.0",
    domain_pack="wind-om-mock",
    domain_pack_hash="mock-pack-v1",
    prompts={"compile": "mock-1"},
    extractors={"local": "mock-1"},
)
SOP_A, SOP_B, PLAN = "src-f2750f41f3fa", "src-4d9c65e05302", "src-43c97f7dfcde"
SKIPPED_GATES = ("G04", "G10", "G15")

GLOSSARY = [
    ("ISO VG", {"de": ["ISO-Viskositätsklasse"], "fr": ["grade de viscosité ISO"]}, "iso-vg"),
    ("SOP", {"de": ["Standardarbeitsanweisung"], "fr": ["procédure opératoire standard"]}, "sop"),
    (
        "WTG",
        {"de": ["Windenergieanlage"], "en": ["wind turbine generator"], "fr": ["éolienne"]},
        "wtg",
    ),
]

PLAN_TABLE = Table(
    id="t01",
    locator=XlsxRowsLocator(sheet="Plan", row_start=1, row_end=4),
    provenance="deterministic-table",
    columns=["Asset", "Task", "Oil grade", "Due", "Hours"],
    rows=[
        TableRow(
            row_id="r0002", cells=["WTG-07", "Gearbox oil change", "ISO VG 320", "2026-03", "6"]
        ),
        TableRow(row_id="r0003", cells=["WTG-07", "Vibration check", "", "2026-04", "2"]),
        TableRow(
            row_id="r0004", cells=["WTG-12", "Gearbox oil change", "ISO VG 220", "2026-05", "6"]
        ),
    ],
    artifact="tables/t01.parquet",
)


def _blocks(titles: dict[str, tuple[str, str]]) -> list[SearchBlock]:
    """Extracted blocks of the (fictional) originals, indexed as ``source-block`` rows."""
    raw = [
        (SOP_A, "p0001", "p. 1", "Use ISO VG 320 gearbox oil for all turbines."),
        (SOP_A, "p0001", "p. 1", "Drain the oil while it is still warm."),
        (
            SOP_B,
            "para-0004",
            "¶ 4",
            "At cold sites, where the ambient temperature can fall below -20 °C, use ISO VG 220 "
            "gearbox "
            "oil. WTG-07 is the first turbine to switch to ISO VG 220. This revision supersedes "
            "SOP-GBX-010 rev A for Litware gearboxes.",
        ),
        (
            PLAN,
            "sheet-plan-r0002-r0004",
            'sheet "Plan", rows 2–4',
            "Row 2: WTG-07, Gearbox oil change, ISO VG 320, due 2026-03, 6 hours. "
            "Row 3: WTG-07, Vibration check, due 2026-04, 2 hours. "
            "Row 4: WTG-12, Gearbox oil change, ISO VG 220, due 2026-05, 6 hours.",
        ),
    ]
    return [
        SearchBlock(
            source_id=source_id,
            page_id=source_id,
            path=titles[source_id][1],
            title=titles[source_id][0],
            locator_key=key,
            section=label,
            text=text,
            sensitivity="public",
            status="superseded" if source_id == SOP_A else "current",
            lang="en",
        )
        for source_id, key, label, text in raw
    ]


def _png(width: int, height: int, highlight: tuple[int, int, int, int]) -> bytes:
    """A tiny deterministic page image: grey text lines, cited lines highlighted in yellow."""
    x0, y0, x1, y1 = highlight
    rows = []
    for y in range(height):
        row = bytearray()
        for x in range(width):
            pixel = (255, 255, 255)
            if 6 <= x < width - 6 and y % 8 in (4, 5) and y > 6:
                pixel = (150, 150, 150)
            if x0 <= x < x1 and y0 <= y < y1:
                pixel = (255, 230, 90) if pixel == (255, 255, 255) else (120, 110, 40)
            row.extend(pixel)
        rows.append(b"\x00" + bytes(row))

    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


def _load_pages(wiki: Path) -> list[Page]:
    pages = []
    for file in sorted(wiki.rglob("*.md")):
        rel = file.relative_to(wiki).as_posix()
        if any(rel.startswith(projection + "/") for projection in SKILL_PROJECTIONS):
            continue
        pages.append(Page.parse(file.read_text(encoding="utf-8"), rel))
    return pages


def _edges(pages: list[Page]) -> list[CatalogEdge]:
    by_path = {page.path: page.frontmatter.id for page in pages}
    ids = {page.frontmatter.id for page in pages}
    edges: set[tuple[str, str, str]] = set()
    for page in pages:
        fm = page.frontmatter
        if isinstance(fm, SourceFrontmatter):
            edges |= {(fm.id, entity, "mentions") for entity in fm.entities if entity in ids}
            edges |= {(fm.id, older, "supersedes") for older in fm.supersedes if older in ids}
        if isinstance(fm, TopicFrontmatter):
            edges |= {(fm.id, source, "topic-of") for source in fm.sources if source in ids}
        if isinstance(fm, EntityFrontmatter | TopicFrontmatter | QueryFrontmatter):
            _, definitions = extract_footnotes(page.body)
            for definition in definitions:
                for link in extract_links(definition.content):
                    target = resolve_href(page.path, link.href).path or ""
                    parts = target.split("/")
                    if len(parts) == 3 and parts[0] == "evidence" and parts[1] in ids:
                        edges.add((fm.id, parts[1], "cites"))
    for page in pages:
        for section in split_sections(page.body):
            if section.heading != "Related":
                continue
            for link in extract_links(section.markdown):
                target = by_path.get(resolve_href(page.path, link.href).path or "")
                pair_known = any(e[0] == page.frontmatter.id and e[1] == target for e in edges)
                if target and target != page.frontmatter.id and not pair_known:
                    edges.add((page.frontmatter.id, target, "related"))
    return [
        CatalogEdge.model_validate({"from": a, "to": b, "kind": k}) for a, b, k in sorted(edges)
    ]


def _clean(release: Path, root: Path) -> None:
    for generated in (
        release / ReleaseFiles.CATALOG,
        release / ReleaseFiles.WIKI_DIR / ReleaseFiles.CATALOG,
        release / ReleaseFiles.SEARCH_DB,
        release / ReleaseFiles.MANIFEST,
        root / "releases" / "current.json",
    ):
        generated.unlink(missing_ok=True)
    shutil.rmtree(release / ReleaseFiles.TABLES_DIR, ignore_errors=True)
    for image in (release / "evidence").glob("*/img"):
        shutil.rmtree(image)


def build(root: Path = HERE) -> list[str]:
    """Regenerate the machine files under ``root``; returns validation problems (none expected)."""
    release = root / "releases" / RELEASE_ID
    wiki = release / ReleaseFiles.WIKI_DIR
    _clean(release, root)
    pages = _load_pages(wiki)
    sources = [page for page in pages if isinstance(page.frontmatter, SourceFrontmatter)]
    inputs = ReleaseInputs(
        sources={page.frontmatter.source_id: page.frontmatter.source_hash for page in sources}  # type: ignore[union-attr]
    )
    expected = ReleaseManifest.compute_release_id(
        created_at=CREATED_AT, audience=AUDIENCE, run_id=RUN_ID, inputs=inputs, versions=VERSIONS
    )
    if expected != RELEASE_ID:
        raise SystemExit(f"release identity changed: expected folder {expected}, have {RELEASE_ID}")

    image = release / "evidence" / SOP_A / "img" / "p0001.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(_png(48, 64, (4, 10, 44, 22)))
    write_source_tables(release, PLAN, [PLAN_TABLE], "public")

    catalog = Catalog(
        release_id=RELEASE_ID,
        audience=AUDIENCE,
        generated_at=CREATED_AT,
        pages=sorted(
            (catalog_page_for(p.frontmatter, p.path) for p in pages), key=lambda e: e.path
        ),
        edges=_edges(pages),
        sources=sorted(
            (catalog_source_for(p.frontmatter) for p in sources), key=lambda s: s.source_id
        ),  # type: ignore[arg-type]
        glossary=[
            CatalogGlossaryEntry(term=term, synonyms=synonyms, page=f"glossary.md#{anchor}")
            for term, synonyms, anchor in GLOSSARY
        ],
    )
    text = catalog.to_json()
    for target in (release / ReleaseFiles.CATALOG, wiki / ReleaseFiles.CATALOG):
        target.write_text(text, encoding="utf-8", newline="\n")

    titles = {p.frontmatter.id: (p.frontmatter.title, p.path) for p in sources}
    synonyms = [
        (term, synonym, lang)
        for term, by_lang, _ in GLOSSARY
        for lang, values in by_lang.items()
        for synonym in values
    ] + [
        ("WTG-07", "turbine 7", "en"),
        ("WTG-07", "éolienne 7", "fr"),
        ("WTG-12", "turbine 12", "en"),
    ]
    build_search_db(
        pages,
        _blocks(titles),
        synonyms,
        release / ReleaseFiles.SEARCH_DB,
        release_id=RELEASE_ID,
        audience=AUDIENCE,
    )

    staged = validate_release(release, require_manifest=False, audience=AUDIENCE)
    if staged:
        return [f"{v.gate} {v.code} {v.path}:{v.line} {v.message}" for v in staged]

    manifest = ReleaseManifest(
        release_id=RELEASE_ID,
        created_at=CREATED_AT,
        audience=AUDIENCE,
        run_id=RUN_ID,
        inputs=inputs,
        versions=VERSIONS,
        counts={
            "entities": sum(isinstance(p.frontmatter, EntityFrontmatter) for p in pages),
            "evidence": len(list((release / "evidence").glob("*/*.md"))) - len(sources),
            "pages": len(pages),
            "queries": sum(isinstance(p.frontmatter, QueryFrontmatter) for p in pages),
            "sources": len(sources),
            "tables": 1,
            "topics": sum(isinstance(p.frontmatter, TopicFrontmatter) for p in pages),
        },
        gates=gate_results([], skipped=SKIPPED_GATES),
        files=hash_release_files(release),
    )
    manifest_text = manifest.to_json()
    (release / ReleaseFiles.MANIFEST).write_text(manifest_text, encoding="utf-8", newline="\n")
    pointer = CurrentPointer(
        release_id=RELEASE_ID,
        created_at=CREATED_AT,
        audience=AUDIENCE,
        manifest_sha256=__import__("hashlib").sha256(manifest_text.encode("utf-8")).hexdigest(),
    )
    (root / "releases" / "current.json").write_text(
        pointer.to_json(), encoding="utf-8", newline="\n"
    )
    return [f"{v.gate} {v.code} {v.path}:{v.line} {v.message}" for v in validate_release(root)]


def copy_sources(destination: Path) -> Path:
    """Copy the hand-written files (no generated ones) to ``destination`` for a clean rebuild."""
    if destination.exists():
        shutil.rmtree(destination)
    release = HERE / "releases" / RELEASE_ID
    target = destination / "releases" / RELEASE_ID
    shutil.copytree(release / ReleaseFiles.WIKI_DIR, target / ReleaseFiles.WIKI_DIR)
    (target / ReleaseFiles.WIKI_DIR / ReleaseFiles.CATALOG).unlink(missing_ok=True)
    for sidecar in (release / "evidence").glob("*/*.md"):
        out = target / sidecar.relative_to(release)
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(sidecar, out)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--out", type=Path, help="rebuild a copy in this folder instead of in place"
    )
    args = parser.parse_args(argv)
    root = copy_sources(args.out) if args.out else HERE
    problems = build(root)
    for problem in problems:
        print(problem)
    print(
        f"mock release {RELEASE_ID}: {'INVALID' if problems else 'valid'} "
        f"({len(problems)} violations)"
    )
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
