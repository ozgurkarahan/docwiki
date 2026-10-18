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
    match = match_doc_type(PACK, "procedures/SOP-GBX-010 rev B.docx", "")
    assert match is not None and (
        match.doc_type,
        match.category,
        match.authority,
        match.rule_id,
    ) == (
        "sop",
        "procedures",
        7,
        "sop#0",
    )
    match = match_doc_type(PACK, "misc/note.docx", "This Standard Operating Procedure covers ...")
    assert match is not None and match.rule_id == "sop#1"
    late = "x" * 300 + "standard operating procedure"
    assert match_doc_type(PACK, "misc/note.docx", late) is None
    bulletin = match_doc_type(
        PACK, "oem/Service Bulletin 12.pdf", "Issued by Litware for all sites"
    )
    assert bulletin is not None and bulletin.doc_type == "service-bulletin"
    assert match_doc_type(PACK, "oem/Service Bulletin 12.pdf", "Issued by another vendor") is None
    assert match_doc_type(PACK, "folder.sop-x/plan 2026.xlsx", "").doc_type == "maintenance-plan"  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("glob", "path", "matches"),
    [
        ("public/**", "public/a/b.pdf", True),
        ("public/**", "internal/public/b.pdf", False),
        ("**/contracts/**", "contracts/rate.xlsx", True),
        ("**/contracts/**", "a/b/Contracts/rate.xlsx", True),
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
    assert sensitivity_for(PACK, "procedures/sop.docx", "sop") == "internal"
    assert sensitivity_for(PACK, "public/brochure.pdf", None) == "public"
    assert sensitivity_for(PACK, "public/contracts/rate-card.xlsx", None) == "restricted"
    assert sensitivity_for(PACK, "records/plan.xlsx", "maintenance-plan") == "restricted"


def test_sensitivity_floor_is_the_lowest_tier_over_every_doc_type() -> None:
    lowered = PACK.model_copy(
        update={
            "sensitivity": SensitivityFile(
                default="internal",
                rules=[
                    SensitivityRule(tier="public", doc_type="sop"),
                    SensitivityRule(tier="restricted", path_glob="**/contracts/**"),
                ],
            )
        }
    )
    sop = "procedures/SOP-GBX-010 rev B.docx"
    assert sensitivity_for(lowered, sop, None) == "internal", "the unclassified tier"
    assert sensitivity_floor(lowered, sop) == "public", "classified as a SOP it is public"
    assert sensitivity_floor(lowered, "contracts/sop-rates.docx") == "restricted"
    assert sensitivity_floor(PACK, "records/plan.xlsx") == "internal"
    assert sensitivity_floor(PACK, "public/brochure.pdf") == "public"
    assert sensitivity_floor(PACK, "public/contracts/rate-card.xlsx") == "restricted"


def test_supersession_parsing_and_ordering() -> None:
    assert parse_doc_number(PACK, "procedures/SOP-GBX-010 rev B.docx") == "SOP-GBX-010"
    assert parse_doc_number(PACK, "notes.docx", "Ref SOP-LTO-002 applies") == "SOP-LTO-002"
    assert parse_doc_number(PACK, "notes.docx") is None
    assert parse_revision(PACK, "SOP-GBX-010 rev B.docx") == "B"
    assert parse_revision(PACK, "x.docx", "Revision C — 2026") == "C"
    assert parse_revision(PACK, "previous.docx") is None
    assert revision_rank(PACK, "b") == 1
    assert compare_revisions(PACK, "A", "C") == -1 and compare_revisions(PACK, "B", "b") == 0
    with pytest.raises(ValueError, match="revision_order"):
        revision_rank(PACK, "Z")
    text = (
        "This procedure supersedes SOP-GBX-010 and supersedes sop-gbx-009 too. "
        "Supersedes SOP-GBX-010."
    )
    assert explicit_references(PACK, text) == ["SOP-GBX-010", "sop-gbx-009"]
    sources = [
        ("src-00000000000c", "SOP-GBX-010", "C"),
        ("src-00000000000a", "SOP-GBX-010", "A"),
        ("src-00000000000b", "SOP-GBX-010", "B"),
        ("src-0000000000ff", "SOP-LTO-002", "A"),
        ("src-0000000000ee", None, "A"),
    ]
    assert order_revisions(PACK, sources) == {
        "SOP-GBX-010": ["src-00000000000a", "src-00000000000b", "src-00000000000c"],
        "SOP-LTO-002": ["src-0000000000ff"],
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
    topic = PACK.topic("gearbox-oil")
    score = score_topic(
        topic,
        "Gearbox oil change SOP",
        [("Oil grade", "Use the viscosity grade below. Boil water.")],
    )
    assert score.by_field == {"title": 6.0, "heading": 2.0, "body": 1.0}
    assert score.score == 9.0
    assert set(score.matched_terms) == {"gearbox oil", "oil change", "oil grade", "viscosity grade"}
    french = score_topic(
        topic, "Vidange", [("Procédure", "Remplacer l'HUILE DE BOITE DE VITESSES chaque année.")]
    )
    assert french.score == 1.0
    german = score_topic(topic, "Getriebeol Wechsel", [])
    assert german.score == 3.0
    assert score_topic(topic, "Spoil grades", [("", "boiling oils")]).score == 0.0


def test_route_topics_uses_per_topic_min_score() -> None:
    routed = route_topics(
        PACK, "Gearbox oil change", [("Cold weather start", "Low temperature limits.")]
    )
    assert [score.slug for score in routed] == ["gearbox-oil", "cold-weather"]
    assert route_topics(PACK, "Unrelated", [("Body", "cold weather")]) == []


def test_glossary_synonym_rows() -> None:
    rows = glossary_synonym_rows(PACK)
    assert ("LOTO", "lockout/tagout", "en") in rows
    assert ("LOTO", "consignation", "fr") in rows
    assert ("WTG-07", "éolienne 7", "fr") in rows
    assert all(row[0] != "SCADA" for row in rows)
    assert ("WTG-07", "turbine 7", "en") not in glossary_synonym_rows(
        PACK, include_entity_aliases=False
    )
