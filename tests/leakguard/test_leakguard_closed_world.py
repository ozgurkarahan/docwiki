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
    for term in ("Lamna Bâtiment", "Inès Roux", "Chantier Moreau", "BC"):
        allow.add_term(term)
    tech, common = base_lists
    return Vocabulary(allow=allow, tech=tech, common=common)


def terms(text: str, vocabulary: Vocabulary, *, sentence_start: bool = True) -> list[str]:
    return [candidate.term for candidate in find_candidates(text, sentence_start, vocabulary)]


def test_allowlisted_tech_and_common_words_are_accepted(vocabulary: Vocabulary) -> None:
    text = (
        "Lamna Bâtiment runs the Chantier Moreau. Inès Roux reviewed the Delivery Schedule "
        "with Microsoft Foundry on Azure and the OCR Evidence Log."
    )
    assert terms(text, vocabulary) == []


def test_unknown_names_are_reported(vocabulary: Vocabulary) -> None:
    text = "The blocks were supplied by Zorblax Supplies and checked by Quentin Marsh."
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
    vocabulary.learn("The dehumidifier in the extension dries the slab.")
    assert terms(heading, vocabulary, sentence_start=False) == []


def test_regex_entries_in_allowlists(base_lists: tuple[TermSet, TermSet]) -> None:
    allow = TermSet(name="allow")
    allow.regexes.append(re.compile(r"Zorb[a-z]+", re.IGNORECASE))
    tech, common = base_lists
    vocabulary = Vocabulary(allow=allow, tech=tech, common=common)
    assert terms("Supplied by Zorbington today.", vocabulary) == []


def test_plurals_possessives_and_french_elision(vocabulary: Vocabulary) -> None:
    assert terms("Read the Lamna's Inspections Reports today.", vocabulary) == []
    assert terms("Le technicien de l'Atelier Zorblax arrive.", vocabulary) == ["Zorblax"]


def test_long_runs_are_split_into_short_candidates(vocabulary: Vocabulary) -> None:
    found = terms("met Aaa Bbb Ccc Ddd Eee Fff", vocabulary)
    assert found == ["Aaa Bbb Ccc Ddd", "Eee Fff"]


@pytest.mark.parametrize(
    "text",
    [
        "release: 20260401T090000Z-7ce99a3f",
        '"release_id": "20260401T090000Z-7ce99a3f",',
        "created 2026-04-01T09:00:00Z by the job",
        "evidence for src-c6436ec50050 and SRC-165F1D3A109C",
        "see p0003, b0042 and sheet-planning-r0006-r0009",
        "check BC-2026-009 and BC-2026-012 today",
        "follow DEV-2026-014 indice B and DEV-2026-014.",
        "set FIXTURE_DIR and ReleaseFiles.WIKI_DIR first",
        "orders are identified as BC-NNN",
        "dates use YYYY-MM-DD and times HH:MM",
    ],
)
def test_identifier_fragments_and_placeholders_are_not_names(
    text: str, vocabulary: Vocabulary
) -> None:
    assert terms(text, vocabulary, sentence_start=False) == []


def test_names_next_to_identifiers_are_still_reported(vocabulary: Vocabulary) -> None:
    assert terms("BC-2026-009 was delivered by Zorblax on 2026-04-20.", vocabulary) == ["Zorblax"]
    text = "release 20260401T090000Z-7ce99a3f approved by Quentin Marsh"
    assert terms(text, vocabulary) == ["Quentin Marsh"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ('"summary": "Append-only change log of this wiki."', []),
        ('"summary": "Curated multi-source syntheses."', []),
        ('"message": "Non-empty when the domain pack has seeds"', []),
        ('["Deliver the windows", "Check the level"]', []),
        ("summary: Superseded revision A of the schedule.", []),
        ("Deliver the windows once the slab is dry.", []),
        ('"vendor": "Zorblax"', ["Zorblax"]),
        ("Supplier: Zorblax", ["Zorblax"]),
        ("| Zorblax | 12 |", ["Zorblax"]),
        ("Note (Zorblax supplied it) today", ["Zorblax"]),
        ("# Zorblax window", ["Zorblax"]),
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
