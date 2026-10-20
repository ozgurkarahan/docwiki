from pathlib import Path

import pytest

from docwiki.domain import (
    explicit_references,
    glossary_synonym_rows,
    load_pack,
    match_doc_type,
    order_revisions,
    parse_doc_number,
    parse_revision,
    revision_rank,
    route_topics,
    score_topic,
    sensitivity_floor,
    sensitivity_for,
    supersession_pairs,
)
from docwiki.domain.models import SensitivityFile, SensitivityRule
from docwiki.domain.rules import compare_revisions, glob_to_regex

PACK = load_pack(Path(__file__).parent / "fixtures" / "mini-pack")


def test_match_doc_type_by_filename_text_and_order() -> None:
    match = match_doc_type(PACK, "devis/DEV-2026-014 indice B.pdf", "")
    assert match is not None and (
        match.doc_type,
        match.category,
        match.authority,
        match.rule_id,
    ) == (
        "devis",
        "quotes",
        7,
        "devis#0",
    )
    match = match_doc_type(PACK, "divers/note.pdf", "Ce devis de travaux couvre ...")
    assert match is not None and match.rule_id == "devis#1"
    late = "x" * 300 + "devis de travaux"
    assert match_doc_type(PACK, "divers/note.pdf", late) is None
    invoice = match_doc_type(PACK, "achats/Facture 12.pdf", "Émise par Zava Matériaux")
    assert invoice is not None and invoice.doc_type == "facture"
    assert match_doc_type(PACK, "achats/Facture 12.pdf", "Émise par un autre fournisseur") is None
    assert match_doc_type(PACK, "dev-x/etude 2026.xlsx", "").doc_type == "etude-de-prix"  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("glob", "path", "matches"),
    [
        ("public/**", "public/a/b.pdf", True),
        ("public/**", "internal/public/b.pdf", False),
        ("**/restricted/**", "restricted/etude.xlsx", True),
        ("**/restricted/**", "a/b/Restricted/etude.xlsx", True),
        ("*.pdf", "a/b.pdf", False),
        ("**/*.pdf", "a/b.pdf", True),
        ("a/?.pdf", "a/1.pdf", True),
        ("a/?.pdf", "a/12.pdf", False),
        ("a/[x].pdf", "a/[x].pdf", True),
    ],
)
def test_glob_semantics(glob: str, path: str, matches: bool) -> None:
    assert bool(glob_to_regex(glob).match(path)) is matches


def test_sensitivity_rules_take_the_highest_tier() -> None:
    assert sensitivity_for(PACK, "devis/devis.pdf", "devis") == "internal"
    assert sensitivity_for(PACK, "public/plaquette.pdf", None) == "public"
    assert sensitivity_for(PACK, "public/restricted/etude.xlsx", None) == "restricted"
    assert sensitivity_for(PACK, "chiffrage/etude.xlsx", "etude-de-prix") == "restricted"


def test_sensitivity_floor_is_the_lowest_tier_over_every_doc_type() -> None:
    lowered = PACK.model_copy(
        update={
            "sensitivity": SensitivityFile(
                default="internal",
                rules=[
                    SensitivityRule(tier="public", doc_type="devis"),
                    SensitivityRule(tier="restricted", path_glob="**/restricted/**"),
                ],
            )
        }
    )
    devis = "devis/DEV-2026-014 indice B.pdf"
    assert sensitivity_for(lowered, devis, None) == "internal", "the unclassified tier"
    assert sensitivity_floor(lowered, devis) == "public", "classified as a quote it is public"
    assert sensitivity_floor(lowered, "restricted/devis-marges.pdf") == "restricted"
    assert sensitivity_floor(PACK, "chiffrage/etude.xlsx") == "internal"
    assert sensitivity_floor(PACK, "public/plaquette.pdf") == "public"
    assert sensitivity_floor(PACK, "public/restricted/etude.xlsx") == "restricted"


def test_supersession_parsing_and_ordering() -> None:
    assert parse_doc_number(PACK, "devis/DEV-2026-014 indice B.pdf") == "DEV-2026-014"
    assert parse_doc_number(PACK, "notes.pdf", "Réf. DEV-2026-021 applicable") == "DEV-2026-021"
    assert parse_doc_number(PACK, "notes.pdf") is None
    assert parse_revision(PACK, "DEV-2026-014 indice B.pdf") == "B"
    assert parse_revision(PACK, "x.pdf", "Indice C — 2026") == "C"
    assert parse_revision(PACK, "indicateur.pdf") is None
    assert revision_rank(PACK, "b") == 1
    assert compare_revisions(PACK, "A", "C") == -1 and compare_revisions(PACK, "B", "b") == 0
    with pytest.raises(ValueError, match="revision_order"):
        revision_rank(PACK, "Z")
    text = (
        "Ce devis annule et remplace DEV-2026-014 et annule et remplace dev-2026-009 aussi. "
        "Annule et remplace le devis DEV-2026-014."
    )
    assert explicit_references(PACK, text) == ["DEV-2026-014", "dev-2026-009"]
    sources = [
        ("src-00000000000c", "DEV-2026-014", "C"),
        ("src-00000000000a", "DEV-2026-014", "A"),
        ("src-00000000000b", "DEV-2026-014", "B"),
        ("src-0000000000ff", "DEV-2026-021", "A"),
        ("src-0000000000ee", None, "A"),
    ]
    assert order_revisions(PACK, sources) == {
        "DEV-2026-014": ["src-00000000000a", "src-00000000000b", "src-00000000000c"],
        "DEV-2026-021": ["src-0000000000ff"],
    }
    assert supersession_pairs(PACK, sources) == [
        ("src-00000000000b", "src-00000000000a"),
        ("src-00000000000c", "src-00000000000b"),
    ]


def test_numeric_revision_order() -> None:
    numeric = PACK.model_copy(
        update={"supersession": PACK.supersession.model_copy(update={"revision_order": "numeric"})}  # type: ignore[union-attr]
    )
    assert revision_rank(numeric, "12") == 12
    with pytest.raises(ValueError, match="not numeric"):
        revision_rank(numeric, "B")


def test_topic_scoring_weights_boundaries_and_aliases() -> None:
    topic = PACK.topic("window-delivery")
    score = score_topic(
        topic,
        "Window delivery date change",
        [("Bay window", "Check the roof window below. Bay windowsill paint.")],
    )
    assert score.by_field == {"title": 6.0, "heading": 2.0, "body": 1.0}
    assert score.score == 9.0
    assert set(score.matched_terms) == {
        "window delivery",
        "delivery date",
        "bay window",
        "roof window",
    }
    french = score_topic(
        topic, "Report", [("Courriel", "Report de la LIVRAISON DES MENUISERIES à la semaine 17.")]
    )
    assert french.score == 1.0
    accented = score_topic(topic, "Fenetre de toit FT1", [])
    assert accented.score == 3.0
    assert score_topic(topic, "Windowsill deliveries", [("", "redelivery dates")]).score == 0.0


def test_route_topics_uses_per_topic_min_score() -> None:
    routed = route_topics(PACK, "Window delivery date", [("Deposit paid", "Retention released.")])
    assert [score.slug for score in routed] == ["window-delivery", "payments"]
    assert route_topics(PACK, "Unrelated", [("Body", "retention")]) == []


def test_glossary_synonym_rows() -> None:
    rows = glossary_synonym_rows(PACK)
    assert ("TTC", "including VAT", "en") in rows
    assert ("TTC", "toutes taxes comprises", "fr") in rows
    assert ("Baie F1", "baie coulissante F1", "fr") in rows
    assert all(row[0] != "HT" for row in rows)
    assert ("Baie F1", "bay window F1", "en") not in glossary_synonym_rows(
        PACK, include_entity_aliases=False
    )
