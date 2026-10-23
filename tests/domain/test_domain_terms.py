"""The locked trade vocabulary of a domain pack (v1.7, ADR 0012): terms.yaml."""

from __future__ import annotations

from pathlib import Path

from docwiki.domain.loader import load_pack
from docwiki.domain.models import locked_terms_note

PACK = Path(__file__).resolve().parents[2] / "domains" / "batiment"


def test_the_batiment_pack_locks_its_trade_terms() -> None:
    pack = load_pack(PACK)
    terms = {term.term: term for term in pack.terms.terms}
    assert {"réception", "conducteur de travaux", "retenue de garantie", "avenant", "lot"} <= set(
        terms
    )
    assert "handover" in terms["réception"].banned
    assert "site manager" in terms["conducteur de travaux"].banned


def test_the_glossary_and_hints_never_use_a_banned_rendering() -> None:
    pack = load_pack(PACK)
    banned = [word.lower() for term in pack.terms.terms for word in term.banned]
    texts = [
        *(f"{term.term} {term.definition} {term.synonyms}" for term in pack.glossary.terms),
        pack.hints or "",
        *(f"{topic.title} {topic.description} {topic.keywords}" for topic in pack.topics.topics),
    ]
    for text in texts:
        for word in banned:
            assert word not in text.lower(), f"{word!r} in {text[:80]!r}"


def test_the_note_lists_the_terms_their_gloss_and_the_banned_renderings() -> None:
    note = locked_terms_note(load_pack(PACK))
    assert note.startswith("Locked trade terms")
    assert "- réception (also réception des travaux, PV de réception): formal acceptance" in note
    assert "never write 'site manager'" in note


def test_a_pack_without_terms_has_no_note(tmp_path: Path) -> None:
    import shutil

    shutil.copytree(PACK, tmp_path / "pack")
    (tmp_path / "pack" / "terms.yaml").unlink()
    pack = load_pack(tmp_path / "pack")
    assert pack.terms.terms == [] and locked_terms_note(pack) == ""
