from __future__ import annotations

import re

import pytest
from leakguard_core.closedworld import Vocabulary, find_candidates
from leakguard_core.config import (
    DEFAULT_COMMON_WORDS,
    DEFAULT_TECH_ALLOWLIST,
    TermSet,
    load_termset,
)


@pytest.fixture(scope="module")
def base_lists() -> tuple[TermSet, TermSet]:
    tech = load_termset(DEFAULT_TECH_ALLOWLIST, "tech", required=True)
    common = load_termset(DEFAULT_COMMON_WORDS, "common", required=True)
    return tech, common


@pytest.fixture
def vocabulary(base_lists: tuple[TermSet, TermSet]) -> Vocabulary:
    allow = TermSet(name="allow")
    for term in ("Contoso Renewables", "Mira Jensen", "Northwind Ridge"):
        allow.add_term(term)
    tech, common = base_lists
    return Vocabulary(allow=allow, tech=tech, common=common)


def terms(text: str, vocabulary: Vocabulary, *, sentence_start: bool = True) -> list[str]:
    return [candidate.term for candidate in find_candidates(text, sentence_start, vocabulary)]


def test_allowlisted_tech_and_common_words_are_accepted(vocabulary: Vocabulary) -> None:
    text = (
        "Contoso Renewables operates Northwind Ridge. Mira Jensen reviewed the Gearbox "
        "Maintenance Procedure with Microsoft Foundry on Azure and the SCADA Alarm Log."
    )
    assert terms(text, vocabulary) == []


def test_unknown_names_are_reported(vocabulary: Vocabulary) -> None:
    text = "The oil was supplied by Zorblax Lubricants and checked by Quentin Marsh."
    assert terms(text, vocabulary) == ["Zorblax", "Quentin Marsh"]


def test_single_word_at_sentence_start_is_excused(vocabulary: Vocabulary) -> None:
    assert terms("Zorblax said nothing.", vocabulary) == []
    assert terms("Yesterday Zorblax said nothing.", vocabulary) == ["Zorblax"]
    # A capitalised run that starts a sentence is still checked.
    assert terms("Zorblax Industries said nothing.", vocabulary) == ["Zorblax"]


def test_cells_and_headings_are_not_excused(vocabulary: Vocabulary) -> None:
    assert terms("Zorblax", vocabulary, sentence_start=False) == ["Zorblax"]


def test_label_value_pairs_are_checked(vocabulary: Vocabulary) -> None:
    assert terms("Supplier: Zorblax", vocabulary) == ["Zorblax"]


def test_camel_case_brand_tokens_are_reported(vocabulary: Vocabulary) -> None:
    assert terms("the team uses ZorbView and iZorb daily", vocabulary) == ["ZorbView", "iZorb"]


def test_camel_case_code_identifiers_of_known_words(vocabulary: Vocabulary) -> None:
    text = "the ReleaseReader and FolderStorage classes load PDFContext data"
    assert terms(text, vocabulary) == []
    assert terms("the iReader app", vocabulary) == ["iReader"]


def test_honorifics_and_initials_join_the_name(vocabulary: Vocabulary) -> None:
    found = find_candidates("Approved by Mr. Quillon and J. R. Vantor.", True, vocabulary)
    assert [c.term for c in found] == ["Quillon", "Vantor"]
    assert found[0].context.startswith("Mr. Quillon")


def test_connectors_keep_names_together(vocabulary: Vocabulary) -> None:
    found = find_candidates("He joined the Bank of Zorblax last year.", True, vocabulary)
    assert [(c.term, c.context) for c in found] == [("Zorblax", "Bank of Zorblax")]


def test_urls_code_and_emails_are_ignored(vocabulary: Vocabulary) -> None:
    text = "See `ZorbClient` at https:" + "//zorblax.example/Docs or ops@zorblax.example now."
    assert terms(text, vocabulary) == []


def test_learned_vocabulary_accepts_title_case_corpus_words(vocabulary: Vocabulary) -> None:
    heading = "Dehumidifier Overhaul"
    assert terms(heading, vocabulary, sentence_start=False) == ["Dehumidifier"]
    vocabulary.learn("The dehumidifier in the nacelle is serviced with the yaw drive.")
    assert terms(heading, vocabulary, sentence_start=False) == []


def test_regex_entries_in_allowlists(base_lists: tuple[TermSet, TermSet]) -> None:
    allow = TermSet(name="allow")
    allow.regexes.append(re.compile(r"Zorb[a-z]+", re.IGNORECASE))
    tech, common = base_lists
    vocabulary = Vocabulary(allow=allow, tech=tech, common=common)
    assert terms("Supplied by Zorbington today.", vocabulary) == []


def test_plurals_possessives_and_french_elision(vocabulary: Vocabulary) -> None:
    assert terms("Read the Contoso's Inspections Reports today.", vocabulary) == []
    assert terms("Le technicien de l'Atelier Zorblax arrive.", vocabulary) == ["Zorblax"]


def test_long_runs_are_split_into_short_candidates(vocabulary: Vocabulary) -> None:
    found = terms("met Aaa Bbb Ccc Ddd Eee Fff", vocabulary)
    assert found == ["Aaa Bbb Ccc Ddd", "Eee Fff"]


@pytest.mark.parametrize(
    "text",
    [
        "release: 20260215T090000Z-decd4b59",
        '"release_id": "20260215T090000Z-decd4b59",',
        "created 2026-02-15T09:00:00Z by the job",
        "evidence for src-43c97f7dfcde and SRC-4D9C65E05302",
        "see p0003, b0042 and sheet-plan-r0002-r0004",
        "inspect WTG-07 and WTG-12 today",
        "follow SOP-GBX-010 rev B and SOP-GBX-010.",
        "set FIXTURE_DIR and ReleaseFiles.WIKI_DIR first",
        "turbines are identified as WTG-NN",
        "dates use YYYY-MM-DD and times HH:MM",
    ],
)
def test_identifier_fragments_and_placeholders_are_not_names(
    text: str, vocabulary: Vocabulary
) -> None:
    assert terms(text, vocabulary, sentence_start=False) == []


def test_names_next_to_identifiers_are_still_reported(vocabulary: Vocabulary) -> None:
    assert terms("WTG-07 was serviced by Zorblax on 2026-02-15.", vocabulary) == ["Zorblax"]
    text = "release 20260215T090000Z-decd4b59 approved by Quentin Marsh"
    assert terms(text, vocabulary) == ["Quentin Marsh"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('"summary": "Append-only change log of this wiki."', []),
        ('"summary": "Curated multi-source syntheses."', []),
        ('"message": "Non-empty when the domain pack has seeds"', []),
        ('["Drain the oil", "Check the level"]', []),
        ("summary: Superseded revision A of the procedure.", []),
        ("Drain the oil while it is still warm.", []),
        ('"vendor": "Zorblax"', ["Zorblax"]),
        ("Supplier: Zorblax", ["Zorblax"]),
        ("| Zorblax | 12 |", ["Zorblax"]),
        ("Note (Zorblax supplied it) today", ["Zorblax"]),
        ("# Zorblax gearbox", ["Zorblax"]),
    ],
)
def test_phrase_starts_followed_by_prose_are_not_names(
    text: str, expected: list[str], vocabulary: Vocabulary
) -> None:
    assert terms(text, vocabulary, sentence_start=False) == expected


def test_inflected_forms_of_known_words(vocabulary: Vocabulary) -> None:
    heading = "### Dehumidifying"
    assert terms(heading, vocabulary, sentence_start=False) == ["Dehumidifying"]
    vocabulary.learn("The cabinet was dehumidified overnight before the inspection started.")
    assert terms(heading, vocabulary, sentence_start=False) == []
    assert terms("### Filed", vocabulary, sentence_start=False) == []
    # Agent nouns are not stemmed: many surnames would become common words.
    assert terms("### Walker", vocabulary, sentence_start=False) == ["Walker"]
