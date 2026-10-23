"""The ``translate`` stage (v1.7, ADR 0012): plans, the preservation check, the cache key, the
model call with its retry, and the mirror page under ``en/``."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from assemble_helpers import source_page

from docwiki.contracts.i18n import untranslated_marker
from docwiki.contracts.markdown import BACKLINKS_END, BACKLINKS_START
from docwiki.domain import load_pack
from docwiki.domain.models import DomainPack
from docwiki.llm import FakeLlmClient, LlmRequest
from docwiki.stages.links import replace_frontmatter
from docwiki.stages.translate import (
    SCHEMA_NAME,
    PagePlan,
    Segment,
    TranslationResult,
    Vocabulary,
    anchor_map,
    assemble_mirror,
    check_translation,
    plan_page,
    relocate_page,
    repair_terms,
    translate_plan,
    translation_digest,
    unrelocate_text,
)

BATIMENT = Path(__file__).resolve().parents[2] / "domains" / "batiment"
RAW = "chantiers/moreau/1-marche/devis/DEV-2026-014 indice A.txt"
NB = " "
NNB = " "
BODY = f"""# Devis DEV-2026-014 indice A

> FICTIONAL SAMPLE - banner of the pack.

Devis de la menuiserie pour le chantier [Moreau](../entities/chantier/moreau.md).

## Faits clés

- Le montant du lot 5 est de 2{NNB}390,00{NB}€{NB}HT, à la réception le 2026-03-16.[^c1]
- La conductrice de travaux valide le bon BC-2026-009.[^c2]

## Contenu

### Délais

La pose commence en avril, après l'OS n°3 ; voir `t01`.[^c1]

| Ligne | Désignation |
| --- | --- |
| 1 | Fenêtre |

> « Livraison sous 3 semaines »

## Figures

Aucune figure n'a été extraite de ce document.

## Voir aussi

- Thème: [Planning](../topics/moreau/planning.md)

{BACKLINKS_START}
## Pages qui renvoient ici

- [Chantier Moreau](../entities/chantier/moreau.md)
{BACKLINKS_END}

## Sources

[^c1]: [Devis — line 2](../evidence/src-000000000001/l0002-l0002.md) · ✓ quote verified
[^c2]: [Devis — line 3](../evidence/src-000000000001/l0003-l0003.md) · ✓ quote verified
"""


@pytest.fixture(scope="module")
def batiment() -> DomainPack:
    return load_pack(BATIMENT)


def french_page() -> Any:
    page = source_page(RAW, "Devis DEV-2026-014 indice A", BODY, slug="dev-2026-014-indice-a")
    return replace_frontmatter(page, lang="fr", summary="Devis de la menuiserie, lot 5.")


def sent(request: LlmRequest) -> list[dict[str, Any]]:
    """The segments a request sent to the model."""
    payload = request.text.split("BEGIN SEGMENTS ", 1)[1].split("\n", 1)[1]
    payload = payload.rsplit("\nEND SEGMENTS ", 1)[0]
    segments: list[dict[str, Any]] = json.loads(payload)["segments"]
    return segments


def echo(prefix: str = "EN: ", change: Any = None, reshape: Any = None) -> Any:
    calls: list[LlmRequest] = []

    def handler(request: LlmRequest) -> dict[str, Any]:
        calls.append(request)
        out = []
        for segment in sent(request):
            text = prefix + segment["text"]
            if change is not None:
                text = change(len(calls), segment, text)
            out.append({"id": segment["id"], "text": text})
        if reshape is not None:
            out = reshape(len(calls), out)
        return {"segments": out}

    handler.calls = calls  # type: ignore[attr-defined]
    return handler


# -- plans -------------------------------------------------------------------------------------


def test_the_plan_keeps_structure_out_of_the_model(batiment: DomainPack) -> None:
    plan = plan_page(french_page(), batiment, "en")
    texts = [segment.text for segment in plan.segments]
    lines = [line for line in plan.lines if isinstance(line, str)]
    # the title, the banner, tables, document quotes, footnotes and the backlinks stay verbatim
    assert "# Devis DEV-2026-014 indice A" in lines
    assert "| 1 | Fenêtre |" in lines and "> « Livraison sous 3 semaines »" in lines
    assert any(line.startswith("[^c1]: [Devis — line 2]") for line in lines)
    assert "- [Chantier Moreau](../entities/chantier/moreau.md)" in lines
    # generated headings and sentences are mapped by code, never translated by the model
    assert "## Key facts" in lines and "## Related" in lines and "## Referenced by" in lines
    assert "No figures were extracted from this document." in lines
    assert "- Topic: [Planning](../topics/moreau/planning.md)" in lines
    assert not any("Faits clés" in text or "Aucune figure" in text for text in texts)
    # links, citations and code spans are masked; the summary is a segment
    # (and locked terms: "lot" becomes a placeholder, named in the segment's terms)
    first = next(segment for segment in plan.segments if "Le montant du" in segment.text)
    # (amounts, written by code with no-break spaces, are masked as well)
    amount = "2\u202f390,00\u00a0€\u00a0HT"
    assert "réception" not in first.text and "€" not in first.text
    assert first.tokens == ("[^c1]", amount, "réception", "lot")
    assert first.terms == (None, None, "réception", "lot")
    assert any(segment.text == "Délais" for segment in plan.segments)
    assert plan.segments[-1].id == "summary"
    pose = next(segment for segment in plan.segments if "pose" in segment.text)
    assert pose.tokens == ("`t01`", "[^c1]", "OS")


def test_the_cache_key_follows_what_the_model_reads(batiment: DomainPack) -> None:
    vocabulary = Vocabulary.of(batiment)
    page = french_page()
    key = translation_digest(plan_page(page, batiment, "en"), vocabulary)
    # a link target or a footnote definition is restored by code: same translation
    moved = page.model_copy(update={"body": page.body.replace("planning.md", "planning-2.md")})
    assert translation_digest(plan_page(moved, batiment, "en"), vocabulary) == key
    # the prose, the target language and the locked vocabulary are part of the key
    edited = page.model_copy(update={"body": page.body.replace("en avril", "en mai")})
    assert translation_digest(plan_page(edited, batiment, "en"), vocabulary) != key
    assert translation_digest(plan_page(page, batiment, "de"), vocabulary) != key
    other_terms = Vocabulary.of(batiment.model_copy(update={"terms": type(batiment.terms)()}))
    assert translation_digest(plan_page(page, batiment, "en"), other_terms) != key


# -- the preservation check --------------------------------------------------------------------

SOURCE = (
    f"La conductrice de travaux valide le bon BC-2026-009 du 2026-03-16 : 2{NNB}390,00{NB}€{NB}HT "
    "pour le lot 5 et la réception.⟦1⟧ Voir ⟦2⟧."
)
GOOD = (
    f"The conductrice de travaux (works manager) approves order BC-2026-009 of 2026-03-16: "
    f"2{NNB}390,00{NB}€{NB}HT for lot 5 and the réception.⟦1⟧ See ⟦2⟧."
)


@pytest.mark.parametrize(
    ("translated", "problem"),
    [
        (GOOD.replace("⟦1⟧", ""), "placeholders"),
        (GOOD.replace("⟦2⟧", "⟦3⟧"), "placeholders"),
        (GOOD + " [x](https://example.invalid)", "links, footnotes or code were added"),
        (GOOD + " [^c9]", "links, footnotes or code were added"),
        (GOOD.replace("lot 5", "lot 6"), "numbers changed"),
        (GOOD.replace("2026-03-16", "16 March 2026"), "dates changed"),
        (GOOD.replace("BC-2026-009", "BC-2026-010"), "document numbers changed"),
        (GOOD.replace(f"2{NNB}390,00{NB}€{NB}HT", "EUR 2,390.00 excl. VAT"), "amounts changed"),
        (GOOD.replace("the réception", "the acceptance"), "locked terms changed: réception"),
        (GOOD.replace("the réception", "the handover"), "banned rendering"),
        (
            GOOD.replace("conductrice de travaux (works manager)", "site manager"),
            "locked terms changed",
        ),
        (GOOD + " <b>x</b>", "HTML"),
        ("", "empty"),
    ],
)
def test_every_change_is_rejected(batiment: DomainPack, translated: str, problem: str) -> None:
    problems = check_translation(SOURCE, translated, Vocabulary.of(batiment))
    assert any(problem in item for item in problems), problems


def test_a_faithful_translation_passes(batiment: DomainPack) -> None:
    assert check_translation(SOURCE, GOOD, Vocabulary.of(batiment)) == []


# -- the model call ----------------------------------------------------------------------------


async def test_translation_and_mirror_page(batiment: DomainPack) -> None:
    handler = echo()
    llm = FakeLlmClient({SCHEMA_NAME: handler})
    page = french_page()
    plan = plan_page(page, batiment, "en")
    result = await translate_plan(llm, plan, batiment)
    assert result.status == "translated" and result.calls == 1 == len(handler.calls)
    request = handler.calls[0]
    assert request.tier == "fast" and request.prompt_version == "translate-v3"
    assert "from French (fr) into English (en)" in request.text
    # locked terms are placeholders now: the request names them per segment and lists the bans
    assert '"terms"' in request.text and "Never write:" in request.text
    assert "'handover'" in request.text
    mirror = assemble_mirror(plan, result, batiment)
    fm = mirror.frontmatter
    assert fm.lang == "en" and fm.translation_of == fm.id == page.frontmatter.id
    assert fm.title == page.frontmatter.title and fm.summary.startswith("EN: Devis")
    # "lot" is a locked term: kept, and glossed by code on its first use on the page
    assert "- EN: Le montant du lot 5 [" in mirror.body  # after its reference
    assert "[^c1]" in mirror.body
    assert "### EN: Délais" in mirror.body
    # a JSON round trip of the cached result rebuilds the same page
    again = assemble_mirror(plan, TranslationResult.from_json(result.to_json()), batiment)
    assert again == mirror


async def test_a_rejected_translation_is_retried_once_then_kept_untranslated(
    batiment: DomainPack,
) -> None:
    handler = echo(change=lambda call, segment, text: text.replace("5", "6"))
    llm = FakeLlmClient({SCHEMA_NAME: handler})
    plan = plan_page(french_page(), batiment, "en")
    result = await translate_plan(llm, plan, batiment)
    assert result.status == "untranslated" and len(handler.calls) == 2
    assert "numbers changed" in " ".join(result.problems)
    assert "# Your previous translation was rejected" in handler.calls[1].text
    mirror = assemble_mirror(plan, result, batiment)
    assert untranslated_marker("en") in mirror.body
    assert "Le montant du lot 5" in mirror.body and "## Key facts" in mirror.body
    assert mirror.frontmatter.summary == "Devis de la menuiserie, lot 5."


async def test_the_retry_can_fix_the_translation(batiment: DomainPack) -> None:
    handler = echo(change=lambda call, segment, text: text.replace("5", "6") if call == 1 else text)
    plan = plan_page(french_page(), batiment, "en")
    result = await translate_plan(FakeLlmClient({SCHEMA_NAME: handler}), plan, batiment)
    assert result.status == "translated" and len(handler.calls) == 2


# -- a locked term written as its word; partial retries ----------------------------------------


def write_term(word: str, term: str = "lot") -> Any:
    """A model that writes ``word`` where the placeholder of the locked ``term`` was."""

    def change(call: int, segment: dict[str, Any], text: str) -> str:
        for placeholder, original in (segment.get("terms") or {}).items():
            if original.lower() == term:
                text = text.replace(placeholder, word)
        return text

    return change


def lot_segment(batiment: DomainPack) -> Segment:
    plan = plan_page(french_page(), batiment, "en")
    return next(segment for segment in plan.segments if "Le montant du" in segment.text)


@pytest.mark.parametrize("word", ["lot", "Lot", "LOT"])
def test_a_locked_term_written_as_its_word_is_put_back(batiment: DomainPack, word: str) -> None:
    vocabulary = Vocabulary.of(batiment)
    segment = lot_segment(batiment)
    assert segment.terms[3] == "lot"
    english = segment.text.replace("Le montant du ⟦4⟧", f"The amount of {word}")
    assert check_translation(segment.text, english, vocabulary)  # rejected as written
    repaired = repair_terms(segment, english, vocabulary)
    assert repaired == segment.text.replace("Le montant du", "The amount of")
    assert check_translation(segment.text, repaired, vocabulary) == []


@pytest.mark.parametrize(
    ("before", "after"),
    [
        ("du ⟦4⟧", "of the work package"),  # the lot placeholder replaced by another word
        ("la ⟦3⟧", "the lot"),  # the réception placeholder replaced by another term's word
        ("du ⟦4⟧ 5", "du ⟦4⟧ 5, a lot of work,"),  # an English "a lot": no placeholder missing
        ("du ⟦4⟧ 5", "of lot 5 (lot"),  # the word once more than the placeholder it stands for
    ],
)
def test_a_placeholder_replaced_by_anything_else_is_still_rejected(
    batiment: DomainPack, before: str, after: str
) -> None:
    vocabulary = Vocabulary.of(batiment)
    segment = lot_segment(batiment)
    assert before in segment.text
    english = segment.text.replace(before, after)
    problems = check_translation(
        segment.text, repair_terms(segment, english, vocabulary), vocabulary
    )
    assert any("locked terms changed" in item or "placeholders" in item for item in problems)


async def test_a_page_whose_lots_are_written_as_words_is_translated(batiment: DomainPack) -> None:
    handler = echo(change=write_term("Lot"))
    plan = plan_page(french_page(), batiment, "en")
    result = await translate_plan(FakeLlmClient({SCHEMA_NAME: handler}), plan, batiment)
    assert result.status == "translated" and len(handler.calls) == 1, result.problems
    mirror = assemble_mirror(plan, result, batiment)
    gloss = next(term.gloss for term in batiment.terms.terms if term.term == "lot")
    # the placeholder is back: the canonical word, glossed by code once
    assert f"Le montant du lot 5 [{gloss}]" in mirror.body
    assert mirror.frontmatter.summary == "EN: Devis de la menuiserie, lot 5."


async def test_only_the_rejected_segments_are_sent_again(batiment: DomainPack) -> None:
    def change(call: int, segment: dict[str, Any], text: str) -> str:
        return text.replace("5", "6") if call == 1 and segment["id"] != "summary" else text

    handler = echo(change=change)
    plan = plan_page(french_page(), batiment, "en")
    result = await translate_plan(FakeLlmClient({SCHEMA_NAME: handler}), plan, batiment)
    assert result.status == "translated" and len(handler.calls) == 2
    first = lot_segment(batiment)
    assert len(sent(handler.calls[0])) == len(plan.segments)
    assert [segment["id"] for segment in sent(handler.calls[1])] == [first.id]
    retry = handler.calls[1].text.split("# Your previous translation was rejected", 1)[1]
    assert f"- {first.id}: numbers changed" in retry
    # the segments accepted the first time are kept as they were
    assert result.texts["summary"] == "EN: " + plan.segments[-1].text
    assert result.texts[first.id] == "EN: " + first.text


async def test_a_merged_batch_is_retried_one_segment_per_call(batiment: DomainPack) -> None:
    def merge(call: int, out: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if call > 1:
            return out
        merged = {"id": out[0]["id"], "text": out[0]["text"] + " " + out[1]["text"]}
        return [merged, *out[2:]]

    handler = echo(reshape=merge)
    plan = plan_page(french_page(), batiment, "en")
    result = await translate_plan(FakeLlmClient({SCHEMA_NAME: handler}), plan, batiment)
    assert result.status == "translated", result.problems
    assert len(handler.calls) == 1 + len(plan.segments)
    assert all(len(sent(request)) == 1 for request in handler.calls[1:])
    assert "segments were merged" in handler.calls[1].text
    assert result.texts == {segment.id: "EN: " + segment.text for segment in plan.segments}


async def test_a_segment_rejected_twice_keeps_the_whole_page_untranslated(
    batiment: DomainPack,
) -> None:
    def change(call: int, segment: dict[str, Any], text: str) -> str:
        return text.replace("5", "6") if segment["id"] == "summary" else text

    handler = echo(change=change)
    plan = plan_page(french_page(), batiment, "en")
    result = await translate_plan(FakeLlmClient({SCHEMA_NAME: handler}), plan, batiment)
    assert result.status == "untranslated" and len(handler.calls) == 2
    assert [segment["id"] for segment in sent(handler.calls[1])] == ["summary"]
    assert result.problems and all(item.startswith("summary: ") for item in result.problems)
    assert result.texts == {segment.id: segment.text for segment in plan.segments}


# -- relocation --------------------------------------------------------------------------------


async def test_relocated_links_point_to_the_mirror_or_to_canonical_evidence(
    batiment: DomainPack,
) -> None:
    page = french_page()
    plan = plan_page(page, batiment, "en")
    mirror = assemble_mirror(
        plan, await translate_plan(FakeLlmClient({SCHEMA_NAME: echo()}), plan, batiment), batiment
    )
    anchors = {page.path: anchor_map(page, mirror)}
    assert anchors[page.path]["faits-clés"] == "key-facts"
    mirrored = {page.path, "entities/chantier/moreau.md"}
    moved = relocate_page(mirror, "en", mirrored, anchors)
    assert moved.path == f"en/{page.path}"
    assert "](../entities/chantier/moreau.md)" in moved.body  # a mirrored page
    assert "](../../topics/moreau/planning.md)" in moved.body  # not mirrored: canonical
    assert "](../../evidence/src-000000000001/l0002-l0002.md)" in moved.body
    # the previous mirror log is read back in the canonical layout
    text = "- [A](sources/a.md) and [Q](../queries/q.md)"
    assert unrelocate_text(text, "en", "log.md") == "- [A](sources/a.md) and [Q](queries/q.md)"


def test_segments_are_ordered_and_hashable() -> None:
    plan = PagePlan(page=french_page(), source_lang="fr", target_lang="en")
    plan.segments.append(Segment("s1", "Bonjour"))
    assert re.fullmatch(r"[0-9a-f]{64}", plan.content_hash)


def test_locked_terms_are_masked_for_the_model_and_glossed_once_by_code() -> None:
    from docwiki.domain import load_pack as _load
    from docwiki.stages.translate import Vocabulary, _mask_terms, _unmask

    pack = _load(Path(__file__).resolve().parents[2] / "domains" / "batiment")
    forms = Vocabulary.of(pack).forms
    text = "La réception est prévue ; la réception [^c1] fixe la retenue de garantie."
    masked, tokens, terms = _mask_terms(text, forms)
    # the model sees no locked term, only placeholders (the footnote marker is one too)
    assert "réception" not in masked and "retenue" not in masked
    assert sorted(t for t in terms if t) == ["retenue de garantie", "réception", "réception"]
    english = masked.replace("La ", "The ").replace("est prévue", "is planned")
    glosses = {term.term: term.gloss for term in pack.terms.terms}
    glossed: set[str] = set()
    out = _unmask(english, tokens, terms, glosses, glossed)
    gloss = glosses["réception"]
    assert out.count(f"réception [{gloss}]") == 1  # first occurrence on the page only
    assert out.count("réception") == 2 and "[^c1]" in out
    # a second segment of the same page gets no gloss again
    again = _unmask(masked, tokens, terms, glosses, glossed)
    assert "[" + gloss not in again


# -- gloss placement and the case of locked terms ------------------------------------------------


def test_a_gloss_follows_the_whole_reference() -> None:
    from docwiki.stages.translate import _unmask

    glosses = {"OS": "works order", "lot": "work package", "DPGF": "priced breakdown"}
    tokens = ("OS", "lot", "DPGF")
    text = "The ⟦1⟧ n°3 moves ⟦2⟧ 5.2, then ⟦3⟧ DEV-2026-031 indice B of 13/03/2026."
    out = _unmask(text, tokens, tokens, glosses, set())
    assert out == (
        "The OS n°3 [works order] moves lot 5.2 [work package], then "
        "DPGF DEV-2026-031 indice B [priced breakdown] of 13/03/2026."
    )
    # no reference: the gloss follows the term itself
    assert _unmask("The ⟦1⟧ is late.", ("lot",), ("lot",), glosses, set()) == (
        "The lot [work package] is late."
    )


def test_a_locked_common_noun_takes_the_case_of_its_place() -> None:
    from docwiki.stages.translate import _unmask

    tokens = ("lot", "Lot", "OS")
    terms = ("lot", "lot", "OS")
    text = "⟦1⟧ 5 is late. The ⟦2⟧ 6 and the ⟦3⟧ are not."
    assert _unmask(text, tokens, terms, recase=True) == (
        "Lot 5 is late. The lot 6 and the OS are not."
    )
    # the canonical text of an untranslated page is never recased
    assert _unmask(text, tokens, terms) == "lot 5 is late. The Lot 6 and the OS are not."


def test_plurals_of_one_word_terms_are_locked_too(batiment: DomainPack) -> None:
    from docwiki.stages.translate import _mask_terms

    forms = Vocabulary.of(batiment).forms
    masked, tokens, terms = _mask_terms("Les lots 02 et 03 et les situations n°1 à n°3.", forms)
    assert "lots" not in masked and "situations" not in masked
    assert dict(zip(tokens, terms, strict=True)) == {"lots": "lot", "situations": "situation"}
    # acronyms are matched as written only
    assert _mask_terms("Les OSs.", forms)[1] == ()


async def test_glosses_never_go_in_a_heading_and_follow_terms_in_link_labels(
    batiment: DomainPack,
) -> None:
    page = french_page()
    body = page.body.replace("### Délais", "### Délais et OS").replace(
        "La pose commence",
        "Voir la [DPGF DEV-2026-031](../sources/dpgf.md) indice B du 13/03/2026. La pose commence",
    )
    page = page.model_copy(update={"body": body})
    plan = plan_page(page, batiment, "en")
    result = await translate_plan(FakeLlmClient({SCHEMA_NAME: echo()}), plan, batiment)
    mirror = assemble_mirror(plan, result, batiment)
    glosses = {term.term: term.gloss for term in batiment.terms.terms}
    assert "### EN: Délais et OS\n" in mirror.body  # no gloss in the heading
    # the gloss of a term inside a link label goes after the link and its reference
    assert (
        f"[DPGF DEV-2026-031](../sources/dpgf.md) indice B [{glosses['DPGF']}] du 13/03/2026"
        in mirror.body
    )
    # the first use in the text gets the gloss the heading did not
    assert f"l'OS n°3 [{glosses['OS']}]" in mirror.body
    assert mirror.body.count(f"[{glosses['OS']}]") == 1
