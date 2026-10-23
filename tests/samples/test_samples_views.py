"""The computed views of the batiment pack on the real sample corpus (v1.7, ADR 0011).

Every view of ``domains/batiment/views.yaml`` runs on the tables the local extraction adapters
read from the generated files of ``samples/corpus/full``, through the engine's own
``view_sources`` and ``build_view_pages``, and must give the planted answers of
``samples/fiction/PLANTED.md`` (P31, P42, P43, P48): the rows, the cited row of each, and the
totals summed by code. No model and no network.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.locators import locator_key
from docwiki.contracts.manifest import ReleaseInputs, ReleaseManifest
from docwiki.contracts.pages import DocwikiStamp, ExtractionSummary, Page, SourceFrontmatter
from docwiki.contracts.runs import VersionInfo
from docwiki.domain import DomainPack, load_pack
from docwiki.domain.rules import scope_axes
from docwiki.engine_types import ExtractSettings
from docwiki.extract import extract_source
from docwiki.stages.amounts import NBSP, format_number
from docwiki.stages.views import ViewBuild, ViewResult, build_view_pages, view_sources

REPO = Path(__file__).resolve().parents[2]
FULL = REPO / "samples" / "corpus" / "full"
BILLING = "entreprise/billing-register/2026-04-10_suivi-de-facturation-clients.xlsx"
ATTESTATIONS = (
    "entreprise/compliance-register/2026-04-10_registre-des-attestations-sous-traitants.xlsx"
)
CREWS = "entreprise/crew-schedule/2026-04-03_planning-des-equipes-s15-s17.xlsx"
EQUIPMENT = "entreprise/equipment-register/2026-04-10_registre-du-materiel.xlsx"
SITUATION = "chantiers/nacrines/3-execution/situation/2026-03-31_situation-n4.xlsx"
# Documents with tables of other types: the views must ignore them.
OTHERS = (
    "entreprise/price-list/2026-01-08_tarif-2026-zava-materiaux.xlsx",
    "chantiers/moreau/3-execution/schedule/PLN-2026-003_indice-A_planning-et-suivi-des-achats.xlsx",
    "chantiers/nacrines/4-reception/liste-des-reserves/2026-04-14_liste-des-reserves-etat-de-levee.xlsx",
    "chantiers/moreau/3-execution/supplier-invoice/2026-03-16_facture-FA-2026-0217_zava-materiaux.pdf",
)
CREATED = datetime(2026, 4, 10, 9, 0, tzinfo=UTC)
VERSIONS = VersionInfo(docwiki="0.1.0", domain_pack="batiment", domain_pack_hash="h")
STAMP = DocwikiStamp(
    release=ReleaseManifest.compute_release_id(
        created_at=CREATED,
        audience="public",
        run_id=None,
        inputs=ReleaseInputs(),
        versions=VERSIONS,
    )
)


def _sid(rel: str) -> str:
    return source_id_for(rel)


async def _extract(rels: list[str]) -> dict[str, ExtractedDoc]:
    docs: dict[str, ExtractedDoc] = {}
    for rel in rels:
        result = await extract_source(FULL / rel, rel_path=rel, settings=ExtractSettings())
        docs[result.doc.source_id] = result.doc
    return docs


def _source_page(pack: DomainPack, rel: str) -> Page:
    axes = scope_axes(pack, rel)
    assert axes.doc_type is not None, rel
    doc_type = pack.doc_type(axes.doc_type)
    source_id = _sid(rel)
    slug = Path(rel).stem.lower()
    fm = SourceFrontmatter(
        id=source_id,
        title=Path(rel).stem,
        summary=f"Summary of {Path(rel).stem}.",
        sensitivity="public",
        updated=date(2026, 4, 10),
        docwiki=STAMP,
        source_id=source_id,
        source_path=rel,
        source_hash="sha256:" + "0" * 64,
        media_type="application/octet-stream",
        doc_type=doc_type.key,
        category=doc_type.category,
        status="current",
        original_lang="fr",
        authority=doc_type.authority,
        extraction=ExtractionSummary(adapter="local", version="1"),
        scope=axes.scope,
        phase=axes.phase,
    )
    return Page(path=f"sources/{slug}.md", frontmatter=fm, body=f"# {fm.title}\n")


@pytest.fixture(scope="module")
def build() -> ViewBuild:
    return build_corpus_views()


def build_corpus_views() -> ViewBuild:
    """The view pages of the batiment pack over the extracted corpus documents."""
    pack = load_pack(REPO / "domains" / "batiment")
    assert pack.views is not None
    rels = [BILLING, ATTESTATIONS, CREWS, EQUIPMENT, SITUATION, *OTHERS]
    docs = asyncio.run(_extract(rels))
    pages = {_sid(rel): _source_page(pack, rel) for rel in rels}
    scopes = {_sid(rel): scope_axes(pack, rel).scope for rel in rels}
    sources = view_sources(pages, docs, scopes)
    return build_view_pages(pack, sources, stamp=STAMP)


def _result(build: ViewBuild, slug: str) -> ViewResult:
    return next(result for result in build.results if result.view.slug == slug)


def _rows(result: ViewResult) -> list[dict[str, object]]:
    return [dict(zip(result.columns, row.values, strict=True)) for row in result.rows]


def _cited(result: ViewResult) -> list[tuple[str | None, str, str]]:
    return [(row.scope, row.source_id, locator_key(row.locator)) for row in result.rows]


def test_the_pack_declares_four_views(build: ViewBuild) -> None:
    assert [result.view.slug for result in build.results] == [
        "position-financiere",
        "vgp-en-retard",
        "attestations-de-vigilance-expirees",
        "doubles-affectations",
    ]
    assert [page.path for page in build.pages] == [
        "views/position-financiere.md",
        "views/vgp-en-retard.md",
        "views/attestations-de-vigilance-expirees.md",
        "views/doubles-affectations.md",
    ]
    for page in build.pages:
        assert "computed by code, not by a language model" in page.body
        assert "FICTIONAL SAMPLE" in page.body


def test_financial_position_of_every_chantier(build: ViewBuild) -> None:
    """P43: contract + avenants/OS, billed, retained and left to bill, per chantier."""
    result = _result(build, "position-financiere")
    assert result.sources == [_sid(BILLING)]
    marches = "sheet-marches-r{0:04d}-r{0:04d}"
    factures = "sheet-factures-r{0:04d}-r{0:04d}"
    billing = _sid(BILLING)
    assert _cited(result) == [
        ("ecole-montferrine", billing, marches.format(4)),
        ("moreau", billing, marches.format(2)),
        ("moreau", billing, factures.format(4)),
        ("nacrines", billing, marches.format(3)),
        ("nacrines", billing, factures.format(2)),
        ("nacrines", billing, factures.format(3)),
        ("nacrines", billing, factures.format(5)),
        ("nacrines", billing, factures.format(6)),
    ]
    totals = {
        total.scope: (total.rows, {name: str(value) for name, value in total.values.items()})
        for total in result.totals
    }
    assert {scope: rows for scope, (rows, _) in totals.items()} == {
        "ecole-montferrine": 1,
        "moreau": 2,
        "nacrines": 5,
        None: 8,
    }

    def money(scope: str | None) -> dict[str, Decimal]:
        return {name: Decimal(value) for name, value in totals[scope][1].items()}

    assert money("moreau") == {
        "marche_ht": Decimal("39783"),
        "marche_ttc": Decimal("47271.60"),
        "facture_ttc": Decimal("13483.08"),
        "retenue_ttc": Decimal("0"),
        "reste_a_facturer_ttc": Decimal("33788.52"),
    }
    assert money("nacrines") == {
        "marche_ht": Decimal("184490"),
        "marche_ttc": Decimal("202939"),
        "facture_ttc": Decimal("192401"),
        "retenue_ttc": Decimal("9620.05"),
        "reste_a_facturer_ttc": Decimal("10538"),
    }
    assert money("ecole-montferrine") == {
        "marche_ht": Decimal("87440"),
        "marche_ttc": Decimal("104928"),
        "facture_ttc": Decimal("0"),
        "retenue_ttc": Decimal("0"),
        "reste_a_facturer_ttc": Decimal("104928"),
    }
    assert result.totals[-1].skipped == {}
    page = build.pages[0].body

    def cells(*amounts: str) -> str:
        return " | ".join(
            format_number(Decimal(amount), unit=f"€{NBSP}{'HT' if n == 0 else 'TTC'}")
            for n, amount in enumerate(amounts)
        )

    assert f"| moreau | 2 | {cells('39783.00', '47271.60', '13483.08', '0.00', '33788.52')} |" in (
        page
    )
    assert (
        f"| nacrines | 5 | {cells('184490.00', '202939.00', '192401.00', '9620.05', '10538.00')} |"
        in page
    )
    # the planted figures, as people read them
    readable = page.replace(chr(0x202F), " ")  # narrow no-break spaces group thousands
    assert "47 271,60" in readable and "10 538,00" in readable


def test_overdue_vgp_at_the_register_date(build: ViewBuild) -> None:
    """P48: the nacelle MAT-04, due 2026-03-22, 19 days overdue on 10/04/2026."""
    result = _result(build, "vgp-en-retard")
    rows = _rows(result)
    assert [(row["code"], row["prochaine_echeance"], row["jours_de_retard"]) for row in rows] == [
        ("MAT-04", "2026-03-22", 19)
    ]
    assert rows[0]["derniere_verification"] == "2025-09-22"
    assert "Nacelle" in str(rows[0]["designation"])
    assert "Nacrines" in str(rows[0]["affectation"])
    assert _cited(result) == [
        ("entreprise", _sid(EQUIPMENT), "sheet-materiel-r0005-r0005"),
    ]


def test_attestation_de_vigilance_expired_at_the_situation(build: ViewBuild) -> None:
    """P29, P31: Adatum's attestation of 2025-09-15 expired on 2026-03-15, before its situation
    of 2026-03-31; renewed by the attestation of 2026-04-08."""
    result = _result(build, "attestations-de-vigilance-expirees")
    assert result.sources == sorted([_sid(ATTESTATIONS), _sid(SITUATION)])
    rows = _rows(result)
    assert [
        (
            row["piece"],
            row["date_piece"],
            row["valable_jusqu_au"],
            row["situation_du"],
            row["renouvelee_le"],
            row["jours_apres_expiration"],
        )
        for row in rows
    ] == [
        (
            "Attestation de vigilance",
            date(2025, 9, 15),
            date(2026, 3, 15),
            date(2026, 3, 31),
            date(2026, 4, 8),
            16,
        ),
        (
            "Situation de sous-traitance n°2",
            date(2026, 3, 31),
            date(2026, 3, 15),
            date(2026, 3, 31),
            date(2026, 4, 8),
            16,
        ),
    ]
    assert {str(row["sous_traitant"]) for row in rows} == {"Adatum Électricité"}
    assert _cited(result) == [
        ("entreprise", _sid(ATTESTATIONS), "sheet-attestations-r0003-r0003"),
        ("nacrines", _sid(SITUATION), "sheet-sous-traitance-r0002-r0002"),
    ]


def test_crew_double_booking_in_week_16(build: ViewBuild) -> None:
    """P42: Mathis Ancelin at Moreau all week 16 and at Les Nacrines on 16-17 April."""
    result = _result(build, "doubles-affectations")
    rows = _rows(result)
    assert [
        (row["salarie"], row["autre_chantier"], row["conflit_du"], row["conflit_au"])
        for row in rows
    ] == [
        ("Mathis Ancelin", "nacrines", date(2026, 4, 16), date(2026, 4, 17)),
        ("Mathis Ancelin", "moreau", date(2026, 4, 16), date(2026, 4, 17)),
    ]
    assert _cited(result) == [
        ("moreau", _sid(CREWS), "sheet-equipes-r0007-r0007"),
        ("nacrines", _sid(CREWS), "sheet-equipes-r0008-r0008"),
    ]


def test_every_cited_row_goes_to_the_evidence_stage(build: ViewBuild) -> None:
    cited = {(item.source_id, item.key) for item in build.cited}
    expected = {
        (row.source_id, locator_key(row.locator)) for result in build.results for row in result.rows
    }
    assert cited == expected
    assert len(expected) == 13
