"""Rebuild the machine files of the hand-made mock release and validate it.

The Markdown (wiki pages, evidence sidecars, skills, llms.txt) is written by hand and committed.
This script regenerates everything derived from it: the page image of the PDF sidecar, the
Parquet tables of the workbook, ``catalog.json`` (release root and ``wiki/``), ``search.db``,
``manifest.json`` and ``current.json``; then it runs ``validate_release`` and fails on any
violation.

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
from docwiki.contracts.ids import source_id_for
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
RELEASE_ID = "20260401T090000Z-7ce99a3f"
CREATED_AT = datetime(2026, 4, 1, 9, 0, 0, tzinfo=UTC)
AUDIENCE = "public"
RUN_ID = "run-20260401-090000-0a1b2c3d"
VERSIONS = VersionInfo(
    docwiki="0.1.0",
    domain_pack="batiment-mock",
    domain_pack_hash="mock-pack-v1",
    prompts={"compile": "mock-1"},
    extractors={"local": "mock-1"},
)
# Schedule indice A (PDF, superseded), schedule indice B (XLSX, current) and the minutes (DOCX).
PLAN_A, PLAN_B, MINUTES = "src-c6436ec50050", "src-86eabe3d6d0d", "src-165f1d3a109c"
SKIPPED_GATES = ("G04", "G10", "G15")

GLOSSARY = [
    ("revision", {"en": ["revision letter"], "fr": ["indice"]}, "revision"),
    (
        "schedule",
        {
            "en": ["works schedule", "programme"],
            "fr": ["planning", "planning de travaux", "calendrier des travaux"],
        },
        "schedule",
    ),
    (
        "windows and external doors",
        {"en": ["exterior joinery", "joinery"], "fr": ["menuiseries extérieures", "menuiseries"]},
        "windows-and-external-doors",
    ),
]

LAMNA, VANARSDEL, ADATUM, ZAVA = (
    "Lamna Bâtiment",
    "VanArsdel Menuiseries",
    "Adatum Électricité",
    "Zava Matériaux",
)
DONE, TODO = "100 %", "0 %"


def _row(number: int, *cells: str) -> TableRow:
    return TableRow(row_id=f"r{number:04d}", cells=list(cells))


# The two sheets of the workbook of indice B as the local extractor reads them: one table per
# sheet, and spreadsheet row n has the row id r000n (the blank row 20 has none).
# fmt: off
PLANNING_COLUMNS = [
    "Tâche", "Désignation", "Lot", "Intervenant", "Début", "Fin", "Avancement", "Observations",
]
PLANNING_ROWS = [
    _row(2, "T01", "Installation de chantier", "1", LAMNA, "2026-02-23", "2026-02-23", DONE, ""),
    _row(3, "T02", "Terrassement", "2", LAMNA, "2026-02-24", "2026-02-27", DONE, ""),
    _row(4, "T03", "Fondations", "2", LAMNA, "2026-03-02", "2026-03-06", DONE, ""),
    _row(5, "T04", "Dallage", "3", LAMNA, "2026-03-09", "2026-03-12", DONE,
         "Dalle coulée le 12/03/2026"),
    _row(6, "T05", "Élévation des murs", "3", LAMNA, "2026-03-16", "2026-03-27", DONE, ""),
    _row(7, "T06", "Charpente, couverture et fenêtre de toit", "4 et avenant n°1", LAMNA,
         "2026-03-30", "2026-04-03", TODO, ""),
    _row(8, "T07", "Livraison des menuiseries", "5", VANARSDEL, "2026-04-20", "2026-04-20", TODO,
         "Livraison reportée (courriel de VanArsdel Menuiseries du 18/03/2026)"),
    _row(9, "T08", "Pose des menuiseries", "5", LAMNA, "2026-04-21", "2026-04-23", TODO, ""),
    _row(10, "T18", "Fermeture provisoire des baies (panneaux bois)", "5", LAMNA, "2026-04-07",
         "2026-04-07", TODO, "Décision de la réunion de chantier n°3"),
    _row(11, "T09", "Électricité 1er œuvre", "6", ADATUM, "2026-04-07", "2026-04-10", TODO, ""),
    _row(12, "T10", "Ouverture du mur existant (baie de liaison)", "3", LAMNA, "2026-04-27",
         "2026-04-29", TODO, "Après la pose des menuiseries"),
    _row(13, "T11", "Isolation et plâtrerie", "7", LAMNA, "2026-04-13", "2026-04-24", TODO, ""),
    _row(14, "T12", "Cuisine : dépose et plomberie", "8", LAMNA, "2026-04-07", "2026-04-10",
         TODO, "Avancée (réunion de chantier n°3)"),
    _row(15, "T13", "Électricité 2nd œuvre", "6 et 8", ADATUM, "2026-05-04", "2026-05-06",
         TODO, ""),
    _row(16, "T14", "Carrelage et faïence", "7 et 8", LAMNA, "2026-05-04", "2026-05-07",
         TODO, ""),
    _row(17, "T15", "Pose des meubles de cuisine", "8", LAMNA, "2026-05-11", "2026-05-12",
         TODO, ""),
    _row(18, "T16", "Finitions et nettoyage", "-", LAMNA, "2026-05-13", "2026-05-13", TODO, ""),
    _row(19, "T17", "Réception des travaux", "-", "Lamna Bâtiment et clients", "2026-05-15",
         "2026-05-15", TODO, ""),
    _row(21, "Document", "Planning et suivi des achats PLN-2026-003 indice B du 27/03/2026",
         "", "", "", "", "", ""),
    _row(22, "Établi par", "Inès Roux, conductrice de travaux, Lamna Bâtiment",
         "", "", "", "", "", ""),
    _row(23, "Avancement au", "2026-03-27", "", "", "", "", "", ""),
    _row(24, "Observations",
         "Cet indice annule et remplace le planning PLN-2026-003 indice A du 17/03/2026.",
         "", "", "", "", "", ""),
    _row(25, "Observations",
         "Motif : report de la livraison des menuiseries au 20/04/2026 (courriel de VanArsdel "
         "Menuiseries du 18/03/2026) et décisions de la réunion de chantier n°3 du 24/03/2026.",
         "", "", "", "", "", ""),
]
ACHATS_COLUMNS = [
    "N° commande", "Date", "Fournisseur", "Objet", "Commandé HT", "Facturé HT", "Statut",
]
ACHATS_ROWS = [
    _row(2, "BC-2026-008", "2026-02-12", ADATUM,
         "Sous-traitance électricité (extension et cuisine)", "2390", "0",
         "Intervention à partir du 07/04/2026"),
    _row(3, "BC-2026-009", "2026-02-16", VANARSDEL, "Menuiseries extérieures F1, F2 et F3",
         "3320", "996",
         "Acompte de 30 % facturé ; livraison reportée au 20/04/2026 (courriel du 18/03/2026)"),
    _row(4, "BC-2026-010", "2026-02-18", ZAVA,
         "Béton, aciers, hérisson et isolant (fondations et dallage)", "4386.5", "4386.5",
         "Livré et facturé (FA-2026-0174)"),
    _row(5, "BC-2026-012", "2026-03-02", ZAVA, "Blocs béton, mortier, aciers et linteau (murs)",
         "1484.8", "1484.8", "Livré le 13/03/2026, facture FA-2026-0217 en cours de vérification"),
    _row(6, "BC-2026-013", "2026-03-09", ZAVA, "Bois de charpente, tuiles et zinguerie",
         "2964", "0", "Livré le 27/03/2026"),
    _row(7, "BC-2026-016", "2026-03-11", ZAVA,
         "Fenêtre de toit 78 x 98 cm et raccord (avenant n°1)", "612", "0",
         "Livré le 27/03/2026"),
    _row(8, "Total commandé (HT)", "", "", "", "15157.3", "", ""),
    _row(9, "Achats facturés à date (HT)", "", "", "", "", "6867.3", ""),
]
# fmt: on
PLAN_TABLES = [
    Table(
        id="t01",
        locator=XlsxRowsLocator(sheet="Planning", row_start=1, row_end=25),
        provenance="deterministic-table",
        columns=PLANNING_COLUMNS,
        rows=PLANNING_ROWS,
        artifact="tables/t01.parquet",
    ),
    Table(
        id="t02",
        locator=XlsxRowsLocator(sheet="Achats", row_start=1, row_end=9),
        provenance="deterministic-table",
        columns=ACHATS_COLUMNS,
        rows=ACHATS_ROWS,
        artifact="tables/t02.parquet",
    ),
]

SHEET_6_9 = (
    "Row 6: Tâche: T05; Désignation: Élévation des murs; Lot: 3; Intervenant: Lamna Bâtiment; "
    "Début: 2026-03-16; Fin: 2026-03-27; Avancement: 100 %. "
    "Row 7: Tâche: T06; Désignation: Charpente, couverture et fenêtre de toit; Lot: 4 et "
    "avenant n°1; Intervenant: Lamna Bâtiment; Début: 2026-03-30; Fin: 2026-04-03; "
    "Avancement: 0 %. "
    "Row 8: Tâche: T07; Désignation: Livraison des menuiseries; Lot: 5; Intervenant: "
    "VanArsdel Menuiseries; Début: 2026-04-20; Fin: 2026-04-20; Avancement: 0 %; "
    "Observations: Livraison reportée (courriel de VanArsdel Menuiseries du 18/03/2026). "
    "Row 9: Tâche: T08; Désignation: Pose des menuiseries; Lot: 5; Intervenant: Lamna "
    "Bâtiment; Début: 2026-04-21; Fin: 2026-04-23; Avancement: 0 %."
)
SHEET_24_25 = (
    "Row 24: Observations: Cet indice annule et remplace le planning PLN-2026-003 indice A "
    "du 17/03/2026. "
    "Row 25: Observations: Motif : report de la livraison des menuiseries au 20/04/2026 "
    "(courriel de VanArsdel Menuiseries du 18/03/2026) et décisions de la réunion de "
    "chantier n°3 du 24/03/2026."
)


def _blocks(titles: dict[str, tuple[str, str]]) -> list[SearchBlock]:
    """Extracted blocks of the (fictional) originals, indexed as ``source-block`` rows."""
    raw = [
        (
            PLAN_A,
            "p0001",
            "p. 1",
            "Planning et suivi des achats PLN-2026-003 indice A du 17/03/2026",
        ),
        (
            PLAN_A,
            "p0001",
            "p. 1",
            "T05 Élévation des murs 3 Lamna Bâtiment 2026-03-16 2026-03-27 20 %",
        ),
        (
            PLAN_A,
            "p0001",
            "p. 1",
            "T07 Livraison des menuiseries 5 VanArsdel Menuiseries 2026-03-30 2026-03-30 0 % "
            "Commande BC-2026-009",
        ),
        (
            PLAN_A,
            "p0001",
            "p. 1",
            "T08 Pose des menuiseries 5 Lamna Bâtiment 2026-03-31 2026-04-02 0 %",
        ),
        (MINUTES, "para-0007", "¶ 7", "Élévation des murs : avancement 70 %."),
        (
            MINUTES,
            "para-0011",
            "¶ 11",
            "VanArsdel Menuiseries a annoncé par courriel du 18/03/2026 le report de la livraison "
            "des menuiseries (commande BC-2026-009) du 30/03/2026 au 20/04/2026. Pose prévue du "
            "21/04 au 23/04/2026.",
        ),
        (PLAN_B, "sheet-planning-r0006-r0009", 'sheet "Planning", rows 6–9', SHEET_6_9),
        (PLAN_B, "sheet-planning-r0024-r0025", 'sheet "Planning", rows 24–25', SHEET_24_25),
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
            status="superseded" if source_id == PLAN_A else "current",
            lang="fr",
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
    for page in sources:
        fm = page.frontmatter
        if source_id_for(fm.source_path) != fm.source_id:  # type: ignore[union-attr]
            raise SystemExit(f"{page.path}: source_id does not derive from source_path")
    inputs = ReleaseInputs(
        sources={page.frontmatter.source_id: page.frontmatter.source_hash for page in sources}  # type: ignore[union-attr]
    )
    expected = ReleaseManifest.compute_release_id(
        created_at=CREATED_AT, audience=AUDIENCE, run_id=RUN_ID, inputs=inputs, versions=VERSIONS
    )
    if expected != RELEASE_ID:
        raise SystemExit(f"release identity changed: expected folder {expected}, have {RELEASE_ID}")

    image = release / "evidence" / PLAN_A / "img" / "p0001.png"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(_png(48, 64, (4, 10, 44, 22)))
    write_source_tables(release, PLAN_B, PLAN_TABLES, "public")

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
        (p.frontmatter.title, alias.text, alias.lang)
        for p in pages
        if isinstance(p.frontmatter, EntityFrontmatter)
        for alias in p.frontmatter.aliases
    ]
    build_search_db(
        pages,
        _blocks(titles),
        list(dict.fromkeys(synonyms)),
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
            "tables": len(PLAN_TABLES),
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
