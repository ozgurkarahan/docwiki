"""The shipped domain pack ``batiment`` on the real sample corpus (domain-and-corpus.md §1-§3).

The pack must classify, tier, scope and group the generated files of ``samples/corpus`` as the
document contract (§3.4), the planted scenarios (§3.2) and the scopes of ADR 0011 expect. Every
check runs the engine's own code on the real files: the local extraction adapters, the classify
stage (with a model client that fails on any call), discovery, the topic resolution rule, the
portal's upload check and the agent-kit renderer. No model and no network.
"""

from __future__ import annotations

import asyncio
import re
import shutil
from datetime import UTC, date, datetime, timedelta
from pathlib import Path, PurePosixPath
from typing import Any

import jinja2
import jinja2.meta
import pytest

from docwiki.contracts.enums import allowed_for_audience
from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.ids import source_id_for
from docwiki.contracts.pages import SkillFile
from docwiki.contracts.safety import find_violations
from docwiki.contracts.storage import FolderStorage
from docwiki.domain import (
    DomainPack,
    explicit_references,
    glossary_synonym_rows,
    load_pack,
    parse_doc_number,
    parse_revision,
    sensitivity_floor,
    sensitivity_for,
)
from docwiki.domain.rules import match_doc_type, normalize_for_matching, scope_axes
from docwiki.engine_types import Classification, ExtractSettings
from docwiki.extract import extract_source
from docwiki.llm import FakeLlmClient
from docwiki.orchestration.pipeline import _EXPLICIT_REFERENCE_CHARS
from docwiki.portal.process import check_upload_path
from docwiki.stages.agentkit import Safe, render_template
from docwiki.stages.classify import classify_source
from docwiki.stages.compile import detect_mentions
from docwiki.stages.discover import SupersessionRecord, discover, resolve_supersession
from docwiki.stages.models import SourceInfo
from docwiki.stages.topics import ScopeContext, is_change, resolution_statement
from docwiki.stages.verify import load_canaries
from docwiki.storage.routed import DirectorySource, RoutedStorage

PACK = "batiment"
NOW = datetime(2026, 3, 28, 9, 0, tzinfo=UTC)
SKILL_VARIABLES = {"wiki_title", "paths", "topics", "entity_types"}
EXPECTED_TYPES = {
    # chantier Moreau
    "devis-a": "quote",
    "devis-b": "quote",
    "contrat": "works-contract",
    "avenant": "contract-amendment",
    "planning-a": "schedule",
    "planning-b": "schedule",
    "facture": "supplier-invoice",
    "bl-scan": "delivery-note",
    "cr3": "site-meeting-minutes",
    "mail-client": "client-email",
    "mail-fournisseur": "supplier-email",
    "photo-dalle": "site-photo",
    "photo-palettes": "site-photo",
    "etude-prix": "price-study",
    # chantier résidence Les Nacrines
    "nac-marche": "works-contract",
    "nac-sous-traitance": "subcontract",
    "nac-dc4": "dc4",
    "nac-os1": "ordre-de-service",
    "nac-facture": "supplier-invoice",
    "nac-situation4": "situation",
    "nac-cr12": "site-meeting-minutes",
    "nac-pv": "pv-de-reception",
    "nac-reserves": "liste-des-reserves",
    "nac-mail-vanarsdel": "supplier-email",
    # chantier école de Montferrine
    "eco-ccap": "ccap",
    "eco-dpgf-a": "dpgf",
    "eco-dpgf-b": "dpgf",
    "eco-ae": "acte-d-engagement",
    "eco-bc-vanarsdel": "purchase-order",
    "eco-planning": "schedule",
    "eco-cr-prep": "site-meeting-minutes",
    "eco-mail-mairie": "client-email",
    "eco-ppsps": "ppsps",
    # entreprise
    "ent-cgv": "general-terms",
    "ent-organigramme": "organisation-chart",
    "ent-contrat-cadre": "framework-agreement",
    "ent-tarif": "price-list",
    "ent-planning-equipes": "crew-schedule",
    "ent-registre-materiel": "equipment-register",
    "ent-registre-attestations": "compliance-register",
    "ent-suivi-facturation": "billing-register",
    "ent-marges": "margin-dashboard",
}
REVISED = ("devis-a", "devis-b", "planning-a", "planning-b", "eco-dpgf-a", "eco-dpgf-b",
           "eco-planning")
REPLACING = {"devis-b": ["DEV-2026-014"], "planning-b": ["PLN-2026-003"],
             "eco-dpgf-b": ["DEV-2026-031"]}
RESTRICTED = ["ent-marges", "etude-prix"]
ORG_TYPES = {"electrical-subcontractor": "sous-traitant", "plumbing-subcontractor": "sous-traitant",
             "architect": "maitre-d-oeuvre"}
# French terms of the documents' headings, sheet names and table columns that the pack relies
# on (topic aliases, hints), with the glossary term that must carry them as a synonym.
HEADING_TERMS = {
    "devis": "quote",
    "facture": "invoice",
    "contrat de travaux": "works contract",
    "avenant": "contract amendment",
    "compte rendu de chantier": "site meeting minutes",
    "planning": "schedule",
    "achats": "purchase tracking",
    "avancement": "progress",
    "menuiseries extérieures": "windows and external doors",
    "échéancier de paiement": "payment schedule",
    "retenue de garantie": "retention",
    "sous-traitance": "subcontracting",
    "autorisation d'urbanisme": "planning permission",
    "travaux supplémentaires": "additional works",
    "délais": "time for completion",
    "lot": "work package",
    "échéance": "due date",
    "commande": "purchase order",
    "HT": "excluding VAT",
    "TTC": "including VAT",
}
# The delivery note is an image-only scan: its printed boxes are read by OCR only (bible facts).
SCAN_HEADING_TERMS = {"réserves à la livraison": "delivery reserves"}
SEARCH_SYNONYMS = (
    "devis",
    "avenant",
    "facture",
    "bon de livraison",
    "retenue de garantie",
    "acompte",
    "menuiseries",
    "palette",
)


def _relative(path: str) -> str:
    """Path relative to the folder given to a build (``samples/corpus/full`` or ``held-back``)."""
    return path.split("/", 1)[1]


def _words(text: str) -> set[str]:
    return set(re.findall(r"[^\W\d_]+", normalize_for_matching(text)))


def _has_term(text: str, term: str) -> bool:
    pattern = r"(?<!\w)" + re.escape(normalize_for_matching(term)) + r"(?!\w)"
    return re.search(pattern, normalize_for_matching(text)) is not None


@pytest.fixture(scope="module")
def pack_dir(repo_root: Path) -> Path:
    return repo_root / "domains" / PACK


@pytest.fixture(scope="module")
def pack(pack_dir: Path) -> DomainPack:
    return load_pack(pack_dir)


@pytest.fixture(scope="module")
def by_id(documents: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {entry["id"]: entry for entry in documents}


@pytest.fixture(scope="module")
def docs(documents: list[dict[str, Any]], corpus_root: Path) -> dict[str, ExtractedDoc]:
    """The engine's local extraction of every corpus file (no OCR, no figure descriptions)."""
    settings = ExtractSettings(mode="local", describe_figures=False)

    async def extract_all() -> dict[str, ExtractedDoc]:
        extracted = {}
        for entry in documents:
            result = await extract_source(
                corpus_root / entry["path"], rel_path=entry["path"], settings=settings
            )
            extracted[entry["id"]] = result.doc
        return extracted

    return asyncio.run(extract_all())


@pytest.fixture(scope="module")
def llm() -> FakeLlmClient:
    return FakeLlmClient()  # no handler: any model call fails


@pytest.fixture(scope="module")
def classifications(
    docs: dict[str, ExtractedDoc], pack: DomainPack, llm: FakeLlmClient
) -> dict[str, Classification]:
    async def classify_all() -> dict[str, Classification]:
        return {doc_id: await classify_source(doc, pack, llm) for doc_id, doc in docs.items()}

    return asyncio.run(classify_all())


# ------------------------------------------------------------------------------ the pack


def test_batiment_is_the_fictional_sample_pack(pack: DomainPack, bible: dict[str, Any]) -> None:
    info = pack.info
    assert info.name == PACK == bible["world"]["pack"]
    assert info.fictional and info.default_audience == "public"
    assert info.languages == ["fr", "en"]
    assert info.banner and info.banner.startswith("FICTIONAL SAMPLE")
    builder = next(org for org in bible["organisations"] if org["role"] == "builder")
    client = next(org for org in bible["organisations"] if org["role"] == "client")
    towns = [place["name"] for place in bible["places"] if place["type"] == "town"]
    assert info.wiki_title == builder["name"]
    for name in (builder["name"], client["short"], *towns):
        assert name in info.banner, name
    # A block made only of banner words is a notice for readers, never an injection: the stamp
    # printed on every document must be one.
    assert _words(bible["world"]["stamp"]) <= _words(info.banner)
    # Six topics per chantier (ADR 0011) and three company topics.
    assert len(pack.topics.topics) == 9
    assert sum(topic.per_scope for topic in pack.topics.topics) == 6
    for topic in pack.topics.topics:
        assert topic.keywords and topic.aliases, topic.slug
        assert {alias.lang for alias in topic.aliases} == {"fr"}, topic.slug
    assert len(pack.entities.types) == 12
    assert pack.scopes is not None
    assert pack.scopes.name in {entity_type.key for entity_type in pack.entities.types}
    assert len(pack.skill_templates) == 3


def test_the_registry_covers_the_bible(pack: DomainPack, bible: dict[str, Any]) -> None:
    org_type = {org["key"]: ORG_TYPES.get(org["role"], "organisation")
                for org in bible["organisations"]}
    expected = {f"{org_type[key]}:{key}" for key in org_type}
    expected |= {f"person:{person['key']}" for person in bible["people"]}
    expected |= {f"chantier:{chantier['code']}" for chantier in bible["chantiers"]}
    expected |= {f"materiel:{item['code'].lower()}" for item in bible["equipment"]}
    nacrines = bible["facts"]["nacrines"]
    expected |= {f"reserve:nacrines-{row['id'].lower()}" for row in nacrines["reserves"]["rows"]}
    expected |= {f"situation:nacrines-n{row['n']}" for row in nacrines["situations"]}
    expected.add("situation:adatum-nacrines-n2")
    expected |= {f"work-package:{lot['key']}" for lot in bible["work_packages"]}
    expected |= {
        f"material:{product['code'].lower()}"
        for product in bible["products"]
        if product.get("code")
    }
    expected |= {
        f"commercial-document:{number.lower()}"
        for scheme in bible["document_number_schemes"]
        for number in scheme["examples"]
    }
    # The documents always name the windows F2 and F3 together: one entity.
    together = {"fenetre-f2", "fenetre-f3"}
    expected |= {
        f"building-element:{asset['key']}"
        for asset in bible["other_assets"]
        if asset["key"] not in together
    }
    expected.add("building-element:fenetres-f2-f3")
    assert expected <= set(pack.entity_ids), sorted(expected - set(pack.entity_ids))
    for org in bible["organisations"]:
        assert pack.entity(f"{org_type[org['key']]}:{org['key']}").label == org["name"]
    people = {person["key"]: person["name"] for person in bible["people"]}
    for chantier in bible["chantiers"]:
        attributes = pack.entity(f"chantier:{chantier['code']}").attributes
        assert attributes["code"] == chantier["code"]
        assert attributes["phase"] == chantier["phase"]
        assert attributes["contract_type"] == chantier["contract_type"]
        assert attributes["conducteur"] == people[chantier["conducteur"]]
    for person in bible["people"]:
        assert pack.entity(f"person:{person['key']}").label == person["name"]
    for product in bible["products"]:
        if product.get("code"):
            assert product["code"] in pack.entity(f"material:{product['code'].lower()}").label


# ------------------------------------------------------------------- classification and tiers


def test_every_document_is_classified_by_its_path_and_its_file_name_agrees(
    documents: list[dict[str, Any]],
    docs: dict[str, ExtractedDoc],
    classifications: dict[str, Classification],
    pack: DomainPack,
    llm: FakeLlmClient,
) -> None:
    """The doc type folder of the path decides (ADR 0011); the file name rules give the same type,
    so a document uploaded outside the layout is still classified without a model."""
    assert {entry["id"] for entry in documents} == set(EXPECTED_TYPES)
    for entry in documents:
        expected = pack.doc_type(EXPECTED_TYPES[entry["id"]])
        result = classifications[entry["id"]]
        assert (result.method, result.rule_id) == ("path", None), entry["path"]
        name = PurePosixPath(entry["path"]).name
        match = match_doc_type(pack, name, docs[entry["id"]].text())
        assert match is not None and match.doc_type == expected.key, entry["path"]
        assert (result.doc_type, result.category, result.authority) == (
            expected.key,
            expected.category,
            expected.authority,
        )
        if docs[entry["id"]].text().strip():
            assert result.lang == entry["lang"] == "fr", entry["path"]
    assert llm.requests == []


def test_tiers_follow_the_manifest_and_a_public_build_drops_only_the_price_study(
    documents: list[dict[str, Any]], classifications: dict[str, Classification], pack: DomainPack
) -> None:
    dropped = []
    for entry in documents:
        doc_type = classifications[entry["id"]].doc_type
        for raw_path in (entry["path"], _relative(entry["path"])):
            tier = sensitivity_for(pack, raw_path, doc_type)
            assert tier == entry["sensitivity"], f"{raw_path}: {tier}"
            # The floor decides before classification whether a build may skip the file.
            assert sensitivity_floor(pack, raw_path) == entry["sensitivity"], raw_path
        if not allowed_for_audience(entry["sensitivity"], "public"):
            dropped.append(entry["id"])
    assert sorted(dropped) == RESTRICTED


def test_resolution_rule_on_the_planted_contradictions(
    by_id: dict[str, dict[str, Any]],
    docs: dict[str, ExtractedDoc],
    classifications: dict[str, Classification],
    pack: DomainPack,
) -> None:
    def info(doc_id: str, *, dated: bool = True) -> SourceInfo:
        result = classifications[doc_id]
        authored = docs[doc_id].metadata.authored
        if dated:
            assert authored == date.fromisoformat(by_id[doc_id]["date"]), doc_id
        return SourceInfo(
            source_id=doc_id,
            title=doc_id,
            path=f"sources/{doc_id}.md",
            status="current",
            sensitivity=by_id[doc_id]["sensitivity"],
            authority=result.authority,
            doc_type=result.doc_type,
            doc_number=result.doc_number,
            revision=result.revision,
            date=authored if dated else None,
            supersedes=(),
            superseded_by=(),
        )

    rule = "Resolution rule (authority, then recency): "
    # Window delivery: the schedule and the supplier's e-mail share an authority, the later wins.
    assert resolution_statement(pack, info("planning-a"), info("mail-fournisseur")) == (
        rule + "mail-fournisseur prevails (dated 2026-03-18 vs 2026-03-17)."
    )
    assert resolution_statement(pack, info("planning-a"), info("cr3")) == (
        rule + "cr3 prevails (authority 7 vs 4)."
    )
    # Pallets: the delivery note wins on authority, also without dates (no PDF date in Azure).
    assert resolution_statement(
        pack, info("facture", dated=False), info("bl-scan", dated=False)
    ) == (rule + "bl-scan prevails (authority 6 vs 5).")
    assert resolution_statement(pack, info("contrat"), info("avenant")) == (
        rule + "avenant prevails (authority 10 vs 9)."
    )
    assert info("contrat").authority > info("devis-b").authority
    # v1.7: an avenant or an OS of the same chantier changes its contract (not a contradiction)
    assert is_change(pack, info("contrat"), info("avenant"))
    assert is_change(pack, info("nac-marche"), info("nac-os1"))
    assert not is_change(pack, info("nac-os1"), info("nac-marche"))
    # a contract that wins against another document is to review when its chantier has an OS
    context = {
        sid: ScopeContext("Les Nacrines", ((info("nac-os1"), "[OS n°1](nac-os1.md)"),))
        for sid in ("nac-marche", "nac-cr12")
    }
    assert resolution_statement(pack, info("nac-cr12"), info("nac-marche"), context) == (
        rule + "to review; the rule would favour nac-marche (authority 9 vs 7), but the terms of "
        "nac-marche may have been changed by the amending documents of Les Nacrines: "
        "[OS n°1](nac-os1.md); check them before relying on either statement."
    )
    # the client's written constraint against our own schedule is arbitrated with the client
    arbitrated = resolution_statement(pack, info("eco-planning"), info("eco-mail-mairie"))
    assert arbitrated.startswith(
        rule + "to arbitrate; the rule does not decide between eco-planning and eco-mail-mairie. "
    )
    assert "arbitrate the point with the client" in arbitrated and "prevails" not in arbitrated
    # ... and so is the client's constraint against our own PPSPS (authority 5 vs 3)
    safety = resolution_statement(pack, info("eco-ppsps"), info("eco-mail-mairie"))
    assert safety.startswith(
        rule + "to arbitrate; the rule does not decide between eco-ppsps and eco-mail-mairie. "
    )
    assert "arbitrate the point with the client" in safety and "prevails" not in safety
    # documents the client signs are never paired with its e-mails: the rule decides
    pairs = {frozenset(pair.types) for pair in pack.resolution.arbitrate}
    for signed in ("works-contract", "contract-amendment", "ordre-de-service", "acte-d-engagement"):
        assert frozenset({"client-email", signed}) not in pairs
    notes = {int(number) for number in re.findall(r"\b(?:10|[1-9])\b", pack.resolution.notes)}
    assert notes == {doc_type.authority for doc_type in pack.taxonomy.doc_types}


# ------------------------------------------------------------------------------ supersession


def test_scope_phase_and_type_come_from_the_path(
    documents: list[dict[str, Any]], classifications: dict[str, Classification], pack: DomainPack
) -> None:
    assert pack.scopes is not None
    phases = {phase.key for phase in pack.scopes.phases}
    for entry in documents:
        parts = entry["path"].split("/")
        result = classifications[entry["id"]]
        for raw_path in (entry["path"], _relative(entry["path"])):
            axes = scope_axes(pack, raw_path)
            assert axes.doc_type == EXPECTED_TYPES[entry["id"]], raw_path
            if parts[1] == "chantiers":
                assert (axes.scope, axes.phase) == (parts[2], parts[3][0]), raw_path
                assert axes.phase in phases
                assert pack.entity(f"chantier:{axes.scope}")
            else:
                assert (axes.scope, axes.phase) == (pack.scopes.default.key, None), raw_path
        assert (result.scope, result.phase) == (axes.scope, axes.phase), entry["path"]


def test_discovery_groups_only_the_quotes_dpgf_and_schedules(
    tmp_path: Path, documents: list[dict[str, Any]], corpus_root: Path, pack: DomainPack
) -> None:
    raw = tmp_path / "raw"
    shutil.copytree(corpus_root / "full", raw)
    storage = RoutedStorage(
        FolderStorage(tmp_path / "work", fsync=False), {"raw": DirectorySource(raw)}
    )
    sid = {entry["id"]: source_id_for(_relative(entry["path"])) for entry in documents}
    initial = [entry for entry in documents if not entry["held_back"]]

    plan = discover(storage, pack, now=NOW)
    assert sorted(plan.new) == sorted(sid[entry["id"]] for entry in initial)
    assert sorted(plan.supersedes) == sorted(
        [(sid["devis-b"], sid["devis-a"]), (sid["eco-dpgf-b"], sid["eco-dpgf-a"])]
    )
    # Revision groups are keyed by (chantier, number): ADR 0011.
    assert plan.revision_groups == {
        "moreau/DEV-2026-014": [sid["devis-a"], sid["devis-b"]],
        "moreau/PLN-2026-003": [sid["planning-a"]],
        "ecole-montferrine/DEV-2026-031": [sid["eco-dpgf-a"], sid["eco-dpgf-b"]],
        "ecole-montferrine/PLN-2026-007": [sid["eco-planning"]],
    }
    for entry in initial:
        group = plan.items[sid[entry["id"]]].state.revision_group
        assert group == (entry["doc_number"] if entry["id"] in REVISED else None), entry["path"]

    # The held-back schedule revision is uploaded by the owner on the portal under its own name.
    held_back = next(entry for entry in documents if entry["held_back"])
    upload = check_upload_path(_relative(held_back["path"]))
    target = raw.joinpath(*upload.split("/"))
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(corpus_root / held_back["path"], target)
    later = discover(storage, pack, now=NOW + timedelta(minutes=5))
    assert later.new == [sid["planning-b"]]
    assert sorted(later.supersedes) == sorted(
        [(sid["devis-b"], sid["devis-a"]), (sid["planning-b"], sid["planning-a"]),
         (sid["eco-dpgf-b"], sid["eco-dpgf-a"])]
    )
    assert later.revision_groups["moreau/PLN-2026-003"] == [sid["planning-a"], sid["planning-b"]]


def test_supersession_after_classification(
    documents: list[dict[str, Any]],
    docs: dict[str, ExtractedDoc],
    classifications: dict[str, Classification],
    pack: DomainPack,
) -> None:
    """The records the pipeline builds once sources are classified (document numbers and
    revisions from the classification, explicit references from the head of the text)."""
    records = []
    for entry in documents:
        result = classifications[entry["id"]]
        name = PurePosixPath(entry["path"]).name
        text = docs[entry["id"]].text()[:_EXPLICIT_REFERENCE_CHARS]
        record = SupersessionRecord(
            entry["id"],
            result.doc_number or parse_doc_number(pack, name, text),
            result.revision or parse_revision(pack, name, text),
            tuple(explicit_references(pack, text)),
        )
        if entry["id"] in REVISED:
            assert (record.doc_number, record.revision) == (entry["doc_number"], entry["revision"])
        else:
            # The contracts, the amendment, the acte d'engagement, the purchase order, the
            # e-mails, the invoices, the delivery note, the minutes, the photos and the price
            # study cite numbers but form no revision group.
            assert (record.doc_number, record.revision) == (None, None), entry["path"]
        assert list(record.references) == REPLACING.get(entry["id"], []), entry["path"]
        records.append(record)
    initial = [record for record in records if not record.source_id.startswith("planning-b")]
    assert sorted(resolve_supersession(pack, initial)[1]) == [
        ("devis-b", "devis-a"),
        ("eco-dpgf-b", "eco-dpgf-a"),
    ]
    assert sorted(resolve_supersession(pack, records)[1]) == [
        ("devis-b", "devis-a"),
        ("eco-dpgf-b", "eco-dpgf-a"),
        ("planning-b", "planning-a"),
    ]


def test_owner_uploads_keep_the_names_the_pack_relies_on(
    documents: list[dict[str, Any]], pack: DomainPack
) -> None:
    for entry in documents:
        for path in (entry["path"], _relative(entry["path"])):
            assert check_upload_path(path) == path
        name = PurePosixPath(check_upload_path(_relative(entry["path"]))).name
        if entry["id"] in REVISED:
            assert parse_doc_number(pack, name) == entry["doc_number"]
            assert parse_revision(pack, name) == entry["revision"]
        else:
            assert parse_doc_number(pack, name) is None and parse_revision(pack, name) is None


# ------------------------------------------------------------- canary, glossary and registry


def test_the_canary_of_the_bible_is_the_pack_canary(pack_dir: Path, bible: dict[str, Any]) -> None:
    injection = bible["injection"]
    assert load_canaries(pack_dir, env={}) == (injection["canary"],)
    for file in pack_dir.rglob("*"):
        if file.is_file() and file.name != "canaries.txt":
            text = file.read_text(encoding="utf-8")
            for token in (injection["canary"], *injection["forbidden_in_outputs"]):
                assert token not in text, (file.name, token)


def test_the_glossary_covers_the_french_terms_of_the_headings(
    documents: list[dict[str, Any]],
    docs: dict[str, ExtractedDoc],
    pack: DomainPack,
    bible: dict[str, Any],
) -> None:
    headings: list[str] = []
    for entry in documents:
        if entry["sensitivity"] != "public":
            continue
        doc = docs[entry["id"]]
        headings += [block.text for block in doc.blocks if block.kind == "heading"]
        headings += [column for table in doc.tables for column in table.columns]
    scan_boxes = bible["facts"]["zava_delivery"]["printed_boxes"]
    glossary = {term.term.casefold(): term for term in pack.glossary.terms}
    for terms, source in ((HEADING_TERMS, headings), (SCAN_HEADING_TERMS, scan_boxes)):
        for french, english in terms.items():
            assert any(_has_term(heading, french) for heading in source), french
            synonyms = glossary[english.casefold()].synonyms.get("fr", [])
            assert normalize_for_matching(french) in map(normalize_for_matching, synonyms), (
                french,
                english,
            )
    search = {
        normalize_for_matching(synonym)
        for _, synonym, lang in glossary_synonym_rows(pack, include_entity_aliases=False)
        if lang == "fr"
    }
    assert {normalize_for_matching(term) for term in SEARCH_SYNONYMS} <= search


def test_every_registry_entry_is_named_in_a_public_document(
    documents: list[dict[str, Any]], docs: dict[str, ExtractedDoc], pack: DomainPack
) -> None:
    named: set[str] = set()
    for entry in documents:
        if entry["sensitivity"] == "public" and not entry["held_back"]:
            named |= set(detect_mentions(pack, docs[entry["id"]]))
    assert set(pack.entity_ids) <= named, sorted(set(pack.entity_ids) - named)


# ------------------------------------------------------------------------------ skills


def test_skill_templates_render_with_catalog_values(pack: DomainPack) -> None:
    paths = {
        key: Safe(value)
        for key, value in {
            "index": "index.md",
            "glossary": "glossary.md",
            "log": "log.md",
            "sources_index": "sources/index.md",
            "entities_index": "entities/index.md",
            "topics_index": "topics/index.md",
        }.items()
    }
    full = {
        "wiki_title": pack.info.wiki_title,
        "paths": paths,
        "topics": [
            {"slug": Safe(t.slug), "title": t.title, "path": Safe(f"topics/{t.slug}.md")}
            for t in pack.topics.topics
        ],
        "entity_types": [
            {"key": Safe(t.key), "title": t.title, "path": Safe(f"entities/{t.key}/index.md")}
            for t in pack.entities.types
        ],
    }
    empty = dict(full, topics=[], entity_types=[])
    environment = jinja2.Environment(autoescape=False)
    for name, source in pack.skill_templates.items():
        assert jinja2.meta.find_undeclared_variables(environment.parse(source)) <= SKILL_VARIABLES
        for context in (full, empty):
            text = render_template(source, context, name=name)
            skill = SkillFile.parse(text, name)
            assert skill.frontmatter.name == name and len(skill.frontmatter.description) <= 1024
            assert pack.info.wiki_title in skill.frontmatter.description
            assert find_violations(text, allow_markers=False) == []
            assert "`index.md`" in text and "{{" not in text and "{%" not in text
            # Loop items stay on their own lines (the renderer trims block tags).
            assert not re.findall(r"\S {2,}- \[|\S {2,}- \(no |\)\d+\. ", text), name
