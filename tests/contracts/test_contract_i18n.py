"""String tables of the generated wiki text (v1.7, ADR 0012)."""

from __future__ import annotations

import string

import pytest

from docwiki.contracts.i18n import (
    CORE_STRINGS,
    STRUCTURAL_KEYS,
    Strings,
    core_strings,
    heading_variants,
    language_name,
    untranslated_marker,
)
from docwiki.contracts.markdown import heading_anchor


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def test_every_core_table_has_the_same_keys_and_fields() -> None:
    english = CORE_STRINGS["en"]
    for lang, table in CORE_STRINGS.items():
        assert set(table) == set(english), lang
        for key, template in table.items():
            assert _fields(template) == _fields(english[key]), (lang, key)


def test_english_strings_are_the_wiki_text_before_v1_7() -> None:
    t = core_strings("en")
    assert t.heading("key_facts") == "Key facts"
    assert t.heading("superseded") == "Superseded information"
    assert t("render.superseded_banner", links="[B](b.md)") == (
        "> **Superseded** by [B](b.md). Use the current revision."
    )
    assert t.count("hub.counts", 1, date="2026-03-02") == "1 document, last received 2026-03-02."
    assert t.count("hub.counts", 0, date="2026-03-02") == "0 documents, last received 2026-03-02."


def test_french_plurals_and_typography() -> None:
    t = core_strings("fr")
    assert t.count("hub.counts", 0, date="2026-03-02").startswith("0 document,")
    assert t.count("hub.counts", 2, date="2026-03-02").startswith("2 documents,")
    assert t("topic.policy", notes="x") == "Politique de résolution : x"
    assert t.status("superseded") == "remplacé" and t.status("unknown") == "unknown"


def test_structural_headings_are_known_in_every_language() -> None:
    assert heading_variants("key_facts") == {"Key facts", "Faits clés"}
    assert heading_variants("heading.related") == {"Related", "Voir aussi"}
    assert all(key.startswith("heading.") for key in STRUCTURAL_KEYS)
    # anchors of French headings are derived like GitHub's (letters kept, accents included)
    assert heading_anchor(core_strings("fr").heading("open_contradictions")) == (
        "contradictions-ouvertes"
    )


def test_overrides_and_unknown_languages() -> None:
    t = Strings("fr", {"entity.no_dated": "Rien."})
    assert t("entity.no_dated") == "Rien." and t.heading("facts") == "Faits"
    assert Strings("fr-CA").heading("facts") == "Faits"
    assert Strings("de").heading("facts") == "Facts"  # English for a language without a table
    with pytest.raises(KeyError, match="no string"):
        t("no.such.key")


def test_untranslated_marker_and_language_names() -> None:
    assert untranslated_marker("en") == "> **Untranslated:**"
    assert untranslated_marker("fr") == "> **Non traduit :**"
    assert language_name("fr") == "French (fr)" and language_name("xx") == "xx"
