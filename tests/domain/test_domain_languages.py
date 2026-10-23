"""Wiki languages and generated-string overrides of a domain pack (v1.7, ADR 0012)."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from docwiki.domain import PackValidationError, load_pack

FIXTURE = Path(__file__).parent / "fixtures" / "mini-pack"
BATIMENT = Path(__file__).resolve().parents[2] / "domains" / "batiment"


@pytest.fixture
def pack_dir(tmp_path: Path) -> Path:
    target = tmp_path / "pack"
    shutil.copytree(FIXTURE, target)
    return target


def declare(pack_dir: Path, line: str) -> None:
    info = pack_dir / "pack.yaml"
    info.write_text(info.read_text(encoding="utf-8") + line + "\n", encoding="utf-8")


def test_a_pack_without_wiki_languages_stays_english_only(pack_dir: Path) -> None:
    pack = load_pack(pack_dir)
    assert pack.wiki_languages == ["en"]
    assert pack.canonical_lang == "en" and pack.mirror_langs == []
    assert pack.strings().lang == "en" and pack.strings().heading("key_facts") == "Key facts"


def test_the_batiment_wiki_is_french_with_an_english_mirror() -> None:
    pack = load_pack(BATIMENT)
    assert pack.wiki_languages == ["fr", "en"]
    assert pack.canonical_lang == "fr" and pack.mirror_langs == ["en"]
    assert pack.strings().heading("key_facts") == "Faits clés"
    assert pack.strings("en").heading("key_facts") == "Key facts"


@pytest.mark.parametrize(
    ("line", "message"),
    [
        ("wiki_languages: []", "at least 1"),
        ("wiki_languages: [fr, fr]", "duplicate language"),
        ("wiki_languages: [French]", "pattern"),
    ],
)
def test_wiki_languages_are_validated(pack_dir: Path, line: str, message: str) -> None:
    declare(pack_dir, line)
    with pytest.raises(PackValidationError, match=message):
        load_pack(pack_dir)


def test_pack_string_overrides(pack_dir: Path) -> None:
    declare(pack_dir, "wiki_languages: [fr, en]")
    folder = pack_dir / "i18n"
    folder.mkdir()
    (folder / "fr.yaml").write_text(
        'entity.no_dated: "Pas encore de fait daté."\n', encoding="utf-8"
    )
    pack = load_pack(pack_dir)
    assert pack.strings()("entity.no_dated") == "Pas encore de fait daté."
    assert pack.strings("en")("entity.no_dated") == "No dated facts."
    before = pack.content_hash()
    (folder / "fr.yaml").write_text('entity.no_dated: "Aucun."\n', encoding="utf-8")
    assert load_pack(pack_dir).content_hash() != before


@pytest.mark.parametrize(
    ("name", "text", "message"),
    [
        ("fr.yaml", 'heading.key_facts: "Points clés"\n', "structural headings"),
        ("fr.yaml", 'no.such.key: "x"\n', "unknown string key"),
        ("fr.yaml", "entity.no_dated: 3\n", "expected a string"),
        ("de.yaml", 'entity.no_dated: "Keine."\n', "not one of the wiki_languages"),
        ("fr.txt", "x", "expected <lang>.yaml files only"),
    ],
)
def test_bad_overrides_are_rejected(pack_dir: Path, name: str, text: str, message: str) -> None:
    declare(pack_dir, "wiki_languages: [fr, en]")
    folder = pack_dir / "i18n"
    folder.mkdir()
    (folder / name).write_text(text, encoding="utf-8")
    with pytest.raises(PackValidationError, match=message):
        load_pack(pack_dir)
