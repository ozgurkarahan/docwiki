"""Computed views end to end (v1.7, ADR 0011): two chantiers, two kinds of tables, every row
cited to the evidence of exactly that row, totals computed by code."""

from __future__ import annotations

import shutil
from pathlib import Path

from conftest import PACK
from engine_stubs import CANARY, stub_engine
from engine_stubs import classify_source as stub_classify

from docwiki.contracts.markdown import extract_footnotes, resolve_href
from docwiki.contracts.pages import EvidencePage, Page
from docwiki.domain.rules import scope_axes
from docwiki.evidence.builder import build_evidence
from docwiki.release.reader import ReleaseReader
from docwiki.release.validate import CITATION_RE, validate_release

TYPES = """
  - key: equipment-register
    title: Equipment register
    category: schedule-and-purchases
    authority: 4
    rules:
      - filename_regex: "(?i)^registre-materiel"
  - key: situation
    title: Situation de travaux
    category: contract-documents
    authority: 7
    rules:
      - filename_regex: "(?i)^situation"
"""

SCOPES = """
name: chantier
title: Chantier
plural: chantiers
default: {key: entreprise, title: Entreprise}
paths:
  - regex: '^chantiers/(?P<scope>[a-z0-9-]+)/'
"""

VIEWS = """
views:
  - slug: controles-en-retard
    title: Contrôles en retard
    description: Equipment whose next inspection is due before 1 June 2026.
    doc_types: [equipment-register]
    columns:
      equipement: ["Équipement", "Matériel"]
      prochain_controle: ["Prochain contrôle", "Date du prochain contrôle"]
    sql: >-
      SELECT equipement, prochain_controle, _source_id, _table_id, _row_id, _scope
      FROM rows WHERE parse_date(prochain_controle) < DATE '2026-06-01'
      ORDER BY parse_date(prochain_controle)
  - slug: situations-par-chantier
    title: Situations par chantier
    doc_types: [situation]
    columns:
      lot: [Lot]
      designation: ["Désignation", "Libellé"]
      montant_ht: ["Montant HT"]
    sql: >-
      SELECT lot, designation, montant_ht, _source_id, _table_id, _row_id, _scope
      FROM rows ORDER BY _scope, _source_id, _row_id
    per_scope: true
    totals: [montant_ht]
"""

CORPUS = {
    "chantiers/moreau/registre-materiel-moreau.csv": (
        "Équipement,Prochain contrôle,Responsable\n"
        "Échafaudage E1,15/03/2026,Inès Roux\n"
        "Bétonnière B2,2026-12-01,Inès Roux\n"
    ),
    "chantiers/ecole/registre-materiel-ecole.csv": (
        "Equipement,Date du prochain controle,Responsable\nNacelle N3,2026-02-10,Inès Roux\n"
    ),
    "chantiers/moreau/situation-01-moreau.csv": (
        'Lot,Désignation,Montant HT\n1,Installation de chantier,"1 350,00 €"\n'
        '2,Maçonnerie,"2390,00 €"\n'
    ),
    "chantiers/ecole/situation-01-ecole.csv": (
        'Lot,Libellé,Montant HT\n1,Installation,"1 000,50 €"\n'
    ),
    "notes/supplier-note.txt": (
        "Note from VanArsdel Menuiseries about the window delivery of the sliding window F1.\n"
    ),
}


async def classify_with_scope(doc, pack, llm):
    """The stub classification plus the scope from the raw path (as the real classifier)."""
    found = await stub_classify(doc, pack, llm)
    axes = scope_axes(pack, doc.source_path)
    return found.model_copy(update={"scope": axes.scope, "phase": axes.phase, "lot": axes.lot})


def _pack(tmp_path: Path, views: str | None) -> Path:
    target = tmp_path / "pack"
    shutil.copytree(PACK, target)
    taxonomy = target / "taxonomy.yaml"
    taxonomy.write_text(taxonomy.read_text(encoding="utf-8") + TYPES, encoding="utf-8")
    (target / "scopes.yaml").write_text(SCOPES, encoding="utf-8")
    if views is not None:
        (target / "views.yaml").write_text(views, encoding="utf-8")
    return target


def _corpus(tmp_path: Path) -> Path:
    root = tmp_path / "views-input"
    for rel, text in CORPUS.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    return root


def _harness(make_harness, tmp_path: Path, views: str | None = VIEWS):
    pack = _pack(tmp_path, views)
    engine = stub_engine(classify_source=classify_with_scope, build_evidence=build_evidence)
    return make_harness(pack=pack, domain=str(pack), input_dir=_corpus(tmp_path), engine=engine)


def _problems(root: Path) -> list[str]:
    return [
        f"{v.gate} {v.severity} {v.code} {v.path}:{v.line} {v.message}"
        for v in validate_release(root, canaries=[CANARY], glossary_seeded=True)
    ]


def _cited_rows(root: Path, page: Page) -> list[tuple[str, str, str]]:
    """(source title, sidecar key, row text) of every footnote of a page, from the sidecars."""
    out: list[tuple[str, str, str]] = []
    _, definitions = extract_footnotes(page.body)
    for definition in definitions:
        match = CITATION_RE.match(definition.content)
        assert match, definition.content
        target = resolve_href(page.path, match.group("href")).path
        assert target is not None and target.startswith("evidence/")
        sidecar = EvidencePage.parse((root / target).read_text(encoding="utf-8"), target)
        rows = [line for line in sidecar.body.split("\n") if line.startswith("| ")]
        out.append((match.group("title"), sidecar.frontmatter.locator_key, rows[-1]))
    return out


async def test_views_are_computed_by_code_and_cited_row_by_row(make_harness, tmp_path):
    harness = _harness(make_harness, tmp_path)
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    assert _problems(root) == []

    reader = ReleaseReader.open(harness.settings.work_dir)
    assert [page.id for page in reader.list_pages("view")] == [
        "view:controles-en-retard",
        "view:situations-par-chantier",
    ]
    overdue = reader.read_page("view:controles-en-retard")
    assert overdue.path == "views/controles-en-retard.md"
    assert overdue.frontmatter.rows == 2
    assert len(overdue.frontmatter.sources) == 2
    assert "computed by code, not by a language model" in overdue.body
    # the école's lift is the most overdue, then the Moreau scaffold; the mixer is not due
    rows = [line for line in overdue.body.split("\n") if line.startswith("| ")][2:]
    assert [line.split(" | ")[:3] for line in rows] == [
        ["| ecole", "Nacelle N3", "2026-02-10"],
        ["| moreau", "Échafaudage E1", "15/03/2026"],
    ]
    assert "Bétonnière" not in overdue.body
    cited = _cited_rows(root, overdue)
    assert [(title, key) for title, key, _ in cited] == [
        ("Registre materiel ecole", "r0002-r0002"),
        ("Registre materiel moreau", "r0002-r0002"),
    ]
    assert "Nacelle N3" in cited[0][2] and "Échafaudage E1" in cited[1][2]

    situations = reader.read_page("view:situations-par-chantier")
    assert situations.frontmatter.rows == 3
    cited = _cited_rows(root, situations)
    assert [(title, key) for title, key, _ in cited] == [
        ("Situation 01 ecole", "r0002-r0002"),
        ("Situation 01 moreau", "r0002-r0002"),
        ("Situation 01 moreau", "r0003-r0003"),
    ]
    assert "Maçonnerie" in cited[2][2]
    body = situations.body
    assert "## Totals" in body
    assert "| ecole | 1 | 1 000,50 € HT |" in body
    assert "| moreau | 2 | 3 740,00 € HT |" in body
    assert "| **All** | 3 | 4 740,50 € HT |" in body
    # the source pages the views read link to them (## Related)
    source = next(page for page in reader.list_pages("source") if page.title.startswith("Sit"))
    assert "- Computed view: [Situations par chantier](../views/situations-par-chantier.md)" in (
        reader.read_page(source.id).body
    )
    # the catalog records the view and its edges to the documents it cites
    catalog = {page.id: page for page in reader.catalog.pages}
    assert catalog["view:situations-par-chantier"].type == "view"
    assert {(edge.from_, edge.kind) for edge in reader.catalog.edges} >= {
        ("view:situations-par-chantier", "cites")
    }


async def test_a_view_that_fails_on_the_data_fails_the_run(make_harness, tmp_path):
    views = VIEWS.replace("SELECT lot,", "SELECT CAST(montant_ht AS INTEGER) AS n, lot,")
    harness = _harness(make_harness, tmp_path, views)
    outcome = await harness.run()
    assert outcome.status == "failed"
    assert not outcome.published
    assert any("situations-par-chantier" in error for error in outcome.errors), outcome.errors


async def test_without_views_yaml_there_are_no_view_pages(make_harness, tmp_path):
    harness = _harness(make_harness, tmp_path, views=None)
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    assert _problems(root) == []
    reader = ReleaseReader.open(harness.settings.work_dir)
    assert reader.list_pages("view") == []
    assert not (root / "wiki" / "views").exists()
