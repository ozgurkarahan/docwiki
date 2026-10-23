"""The document contract of the sample corpus (spec domain-and-corpus.md section 3.4).

Supersession, citation verification, containment and the evaluation rely on these properties
of the generated files: upload-safe ASCII paths, document numbers and indices only in the quote,
DPGF and planning file names, amounts that parse as one number, the canary in a paragraph of its
own, restricted-only values, and no architect on the chantier Moreau.
"""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path, PurePosixPath
from typing import Any

from docwiki.portal.process import check_upload_path
from docwiki.stages.verify_citations import number_values, parse_number_spec

SEGMENT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,99}$")
REVISED_KINDS = {"devis": "DEV-", "dpgf": "DEV-", "planning": "PLN-"}
PLANTED_AMOUNT = re.compile(r"(?<![\d,.])(\d+,\d{2}) ?€")
GROUPED_AMOUNT = re.compile(r"(?<![\d,.])\d{1,3}(?:[ \u00a0\u202f.'’]\d{3})+,\d{2}(?!\d)")
CANCELS = re.compile(r"annule et remplace (?:le |la )?(?:\w+ )?((?:DEV|PLN)-\d{4}-\d{3})")


def _flat(text: str) -> str:
    return " ".join(text.split())


def _fold(text: str) -> str:
    """Case-, accent- and apostrophe-insensitive form ("Maître d'œuvre" -> "maitre d'oeuvre")."""
    text = text.replace("œ", "oe").replace("Œ", "OE").replace("’", "'")
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).casefold()


def _full_text(entry: dict[str, Any], extracted) -> str:
    content = extracted(entry["path"])
    return "\n".join([content.text(), *content.metadata.values()])


def _single_value(raw: str) -> str:
    """The one canonical value of an amount as the citation verifier parses it."""
    spec = parse_number_spec(raw)
    assert spec is not None and len(spec.values) == 1, raw
    assert len(spec.values[0]) == 1, f"{raw} is ambiguous: {sorted(spec.values[0])}"
    return next(iter(spec.values[0]))


# ------------------------------------------------------------------------------ rule 1: paths


def test_paths_pass_the_portal_upload_check(documents: list[dict[str, Any]]) -> None:
    for entry in documents:
        path = entry["path"]
        assert path.isascii(), path
        for segment in path.split("/"):
            assert SEGMENT.fullmatch(segment), (path, segment)
        relative = path.split("/", 1)[1]
        assert check_upload_path(path) == path
        assert check_upload_path(relative) == relative


def test_only_quotes_and_plannings_carry_numbers_and_indices(
    documents: list[dict[str, Any]], bible: dict[str, Any]
) -> None:
    schemes = {scheme["prefix"]: scheme["regex"] for scheme in bible["document_number_schemes"]}
    revisions: dict[str, list[tuple[str, str]]] = {}
    for entry in documents:
        name = PurePosixPath(entry["path"]).name
        prefix = REVISED_KINDS.get(entry["kind"])
        if prefix:
            number, revision = entry["doc_number"], entry["revision"]
            assert re.fullmatch(schemes[prefix], number), number
            assert name.startswith(f"{number}_indice-{revision}_"), name
            revisions.setdefault(number, []).append((revision, entry["path"].split("/")[0]))
        else:
            assert not name.upper().startswith(("DEV-", "PLN-")), name
            assert "indice" not in name.lower() and entry["revision"] is None, name
    facts = bible["facts"]
    assert {number: sorted(found) for number, found in revisions.items()} == {
        facts["devis"]["number"]: [("A", "full"), ("B", "full")],
        facts["planning"]["number"]: [("A", "full"), ("B", "held-back")],
        facts["ecole"]["dpgf"]["number"]: [("A", "full"), ("B", "full")],
        facts["ecole"]["planning"]["number"]: [("A", "full")],
    }


def test_no_text_starts_with_a_quote_or_planning_number(
    documents: list[dict[str, Any]], extracted
) -> None:
    for entry in documents:
        head = extracted(entry["path"]).text().lstrip()
        assert not head.upper().startswith(("DEV-", "PLN-")), entry["path"]


# ------------------------------------------------------------------- rule 2: revision groups


def test_only_later_indices_cancel_and_replace_their_own_number(
    documents: list[dict[str, Any]], extracted
) -> None:
    replacing = []
    for entry in documents:
        text = _flat(extracted(entry["path"]).text())
        found = CANCELS.findall(text)
        if entry["revision"] not in (None, "A"):
            assert found == [entry["doc_number"]], entry["path"]
            replacing.append(entry["id"])
        else:
            assert "annule et remplace" not in text.lower(), entry["path"]
    assert sorted(replacing) == ["devis-b", "eco-dpgf-b", "planning-b"]


def test_the_amendment_amends_and_never_replaces(
    documents: list[dict[str, Any]], extracted, bible: dict[str, Any]
) -> None:
    avenant = next(entry for entry in documents if entry["id"] == "avenant")
    text = _flat(_full_text(avenant, extracted)).lower()
    assert "remplace" not in text
    assert _flat(bible["facts"]["avenant"]["object"]).lower() in text


# ----------------------------------------------------------------------- rule 4: amounts


def _derived_amounts(node: Any, inside: bool = False) -> set[str]:
    """Amounts of every ``derived_not_printed`` section of the bible facts, printed form."""
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            found |= _derived_amounts(value, inside or key == "derived_not_printed")
    elif isinstance(node, list):
        for value in node:
            found |= _derived_amounts(value, inside)
    elif inside and isinstance(node, float):
        found.add(f"{node:.2f}".replace(".", ","))
    return found


def _planted_amounts(planted: str) -> list[tuple[str, str, list[str]]]:
    """(fact id, amount, source paths) for every euro amount of the planted-facts table."""
    paths = dict(re.findall(r"^\| (\d+) \| `([^`]+)` \|", planted, flags=re.MULTILINE))
    facts: list[tuple[str, str, list[str]]] = []
    for line in planted.splitlines():
        if not re.match(r"^\| P\d{2} \|", line):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split(" | ")]
        assert len(cells) == 4, line
        fact, statement, source, _ = cells
        numbers = re.findall(r"#(\d+)", source)
        # Sources named without a number ("devis A and B") are searched in the whole corpus.
        sources = [paths[number] for number in numbers] if numbers else sorted(paths.values())
        for amount in PLANTED_AMOUNT.findall(statement):
            facts.append((fact, amount, sources))
    return facts


def test_each_planted_amount_parses_as_one_value_in_its_source(
    repo_root: Path, bible: dict[str, Any], extracted
) -> None:
    planted = (repo_root / "samples/fiction/PLANTED.md").read_text(encoding="utf-8")
    derived = _derived_amounts(bible["facts"])
    amounts = _planted_amounts(planted)
    assert len(amounts) >= 40
    checked = 0
    for fact, amount, sources in amounts:
        value = _single_value(f"{amount} €")
        if amount in derived:
            continue
        assert sources, f"{fact}: {amount} has no source document"
        holders = [path for path in sources if value in number_values(extracted(path).text())]
        assert holders, f"{fact}: {amount} € is not one number in {sources}"
        checked += 1
    assert checked >= 40


def test_amounts_are_printed_without_thousands_separators(
    documents: list[dict[str, Any]], extracted
) -> None:
    for entry in documents:
        text = extracted(entry["path"]).text()
        assert not GROUPED_AMOUNT.findall(text), entry["path"]
        for match in re.finditer("€", text):
            before = text[max(0, match.start() - 24) : match.start()]
            assert re.search(r"(?:^|[^\d.,])\d+,\d{2} $", before), (entry["path"], before)


# ------------------------------------------------------------------------ rule 5: canary


def _paragraphs(entry_path: str, extracted) -> list[str]:
    lines = [text for key, text in extracted(entry_path).units if key.startswith("msg-body")]
    paragraphs: list[str] = []
    current: list[str] = []
    for line in [*lines, ""]:
        if line.strip():
            current.append(line)
        elif current:
            paragraphs.append(_flat(" ".join(current)))
            current = []
    return paragraphs


def test_the_canary_stands_in_a_paragraph_of_its_own(
    bible: dict[str, Any], extracted
) -> None:
    injection = bible["injection"]
    facts = bible["facts"]["mail_fournisseur"]
    paragraphs = _paragraphs(injection["document"], extracted)
    sentence = _flat(injection["sentence"])
    new_date = "/".join(reversed(facts["new_delivery"].split("-")))
    delay = [p for p in paragraphs if new_date in p]
    assert delay == [_flat(facts["delay_paragraph"])]
    for token in (injection["canary"], *injection["forbidden_in_outputs"], sentence[:40]):
        assert token not in delay[0]
    carriers = [p for p in paragraphs if injection["canary"] in p]
    assert carriers == [sentence]
    assert paragraphs.index(delay[0]) < paragraphs.index(_flat(facts["second_paragraph"]))
    assert paragraphs.index(_flat(facts["second_paragraph"])) < paragraphs.index(sentence)


# ------------------------------------------------------------- rule 6: restricted values


def _restricted_values(bible: dict[str, Any]) -> dict[str, dict[str, Any]]:
    facts = bible["facts"]
    return {
        "etude-prix": facts["etude_de_prix"]["restricted_only_values"],
        "ent-marges": facts["entreprise"]["tableau_marges"]["restricted_only_values"],
    }


def test_restricted_only_values_appear_only_in_the_restricted_document(
    documents: list[dict[str, Any]], bible: dict[str, Any], extracted
) -> None:
    by_id = _restricted_values(bible)
    restricted = [entry for entry in documents if entry["sensitivity"] == "restricted"]
    others = [entry for entry in documents if entry["sensitivity"] != "restricted"]
    assert sorted(entry["id"] for entry in restricted) == sorted(by_id)
    other_values: set[str] = set()
    for entry in others:
        other_values |= number_values(_full_text(entry, extracted))
    public = _flat(" ".join(_full_text(entry, extracted) for entry in others))
    for entry in restricted:
        values = by_id[entry["id"]]
        restricted_text = extracted(entry["path"]).text()
        restricted_values = number_values(restricted_text)
        assert len(values["long"]) >= 2
        for raw in values["long"]:
            assert sum(ch.isdigit() for ch in raw.split(",")[0]) >= 4, raw
            value = _single_value(raw)
            assert value in restricted_values, raw
            assert value not in other_values, raw
        for raw in values["short"]:
            assert raw in _flat(restricted_text), raw
            assert raw not in public, raw


# ------------------------------------------------------------------- abstain: no architect


def test_no_document_of_the_chantier_moreau_mentions_an_architect(
    documents: list[dict[str, Any]], bible: dict[str, Any], extracted
) -> None:
    """The abstain fact is scoped to one chantier: the résidence Les Nacrines has an architect
    as maître d'œuvre, so the question must be answered per chantier."""
    absent = bible["facts"]["absent_from_corpus"]
    terms = [_fold(term) for term in absent["terms"]]
    assert {"architecte", "architect", "maitre d'oeuvre"} <= set(terms)
    scope = f"/chantiers/{absent['chantier']}/"
    moreau = [entry for entry in documents if scope in entry["path"]]
    assert len(moreau) == 14
    for entry in moreau:
        text = _fold(_full_text(entry, extracted))
        for term in terms:
            assert term not in text, (entry["path"], term)
    elsewhere = _fold(" ".join(_full_text(entry, extracted) for entry in documents
                               if "/chantiers/nacrines/" in entry["path"]))
    assert "architecte" in elsewhere and "maitre d'oeuvre" in elsewhere
