import shutil
from datetime import UTC, datetime
from pathlib import Path

import pytest

from docwiki.contracts.proposals import (
    EntityProposalPayload,
    GlossaryProposalPayload,
    InjectionProposalPayload,
    TopicProposalPayload,
    new_proposal,
)
from docwiki.domain import (
    Overlay,
    PackValidationError,
    add_proposal,
    apply_overlay,
    dump_overlay,
    filter_overlay,
    load_overlay,
    load_pack,
)
from docwiki.domain.overlay import OVERLAY_FILE

FIXTURE = Path(__file__).parent / "fixtures" / "mini-pack"
NOW = datetime(2026, 1, 31, 8, 0, tzinfo=UTC)


@pytest.fixture
def pack_dir(tmp_path: Path) -> Path:
    target = tmp_path / "pack"
    shutil.copytree(FIXTURE, target)
    return target


def edit(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text, old
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def errors_of(path: Path) -> list[str]:
    with pytest.raises(PackValidationError) as info:
        load_pack(path)
    return [str(error) for error in info.value.errors]


def test_fixture_pack_loads() -> None:
    pack = load_pack(FIXTURE)
    assert pack.name == "mini-batiment"
    assert pack.info.fictional and pack.info.languages == ["en", "fr"]
    assert [t.key for t in pack.taxonomy.doc_types] == [
        "devis",
        "facture",
        "etude-de-prix",
    ]
    assert pack.entity_ids[0] == "building-element:baie-f1"
    assert pack.entity("organisation:zava-materiaux").label == "Zava Matériaux"
    assert pack.topic("window-delivery").aliases[1].text == "fenêtre de toit"
    assert pack.supersession is not None and pack.supersession.revision_order == [
        "A",
        "B",
        "C",
        "D",
    ]
    assert pack.resolution.order == ["authority", "recency"]
    assert pack.hints and "FT1" in pack.hints
    assert list(pack.skill_templates) == ["check-delivery"]
    assert pack.content_hash() == load_pack(FIXTURE).content_hash()


def test_content_hash_changes_with_content(pack_dir: Path) -> None:
    before = load_pack(pack_dir).content_hash()
    edit(pack_dir / "glossary.yaml", "Amount excluding VAT", "Amount excluding VAT (edited)")
    assert load_pack(pack_dir).content_hash() != before


@pytest.mark.parametrize(
    ("file", "old", "new", "expected"),
    [
        (
            "pack.yaml",
            "fictional: true",
            "fictional: true\nunknown_key: 1",
            "pack.yaml: unknown_key: Extra inputs",
        ),
        (
            "pack.yaml",
            "default_audience: internal",
            "default_audience: secret",
            "pack.yaml: default_audience",
        ),
        (
            "taxonomy.yaml",
            '"(?i)^dev[-_ ]"',
            '"(?i)^dev[-_ "',
            "taxonomy.yaml: doc_types[0].rules[0].filename_regex: invalid regex",
        ),
        ("taxonomy.yaml", "category: records", "category: archives", "unknown category 'archives'"),
        ("taxonomy.yaml", "authority: 9", "authority: 11", "taxonomy.yaml: doc_types[1].authority"),
        (
            "taxonomy.yaml",
            "authority: 7",
            "authority: '7'",
            "taxonomy.yaml: doc_types[0].authority: Input should be a valid integer",
        ),
        (
            "entities.yaml",
            "  - type: commercial-document\n",
            "  - type: tool\n",
            "uses unknown type 'tool'",
        ),
        (
            "entities.yaml",
            "  - key: building-element\n",
            "  - key: topic\n",
            "entity type 'topic' is reserved",
        ),
        ("entities.yaml", "key: baie-f1", "key: Baie-F1", "entities.yaml: registry[0].key"),
        (
            "entities.yaml",
            "{text: bay window F1, lang: en}",
            "{text: bay window F1, lang: es}",
            "entities.yaml: registry[0].aliases[0].lang",
        ),
        (
            "topics.yaml",
            "    keywords: [retention, deposit]\n",
            "",
            "needs keywords or aliases",
        ),
        (
            "glossary.yaml",
            "see_also: [commercial-document:dev-2026-014]",
            "see_also: [commercial-document:dev-2026-999]",
            "glossary.yaml: terms[0].see_also[0]",
        ),
        ("glossary.yaml", "  - term: HT", "  - term: ttc", "duplicate glossary term 'ttc'"),
        (
            "sensitivity.yaml",
            "doc_type: etude-de-prix",
            "doc_type: price-list",
            "sensitivity.yaml: rules[2].doc_type",
        ),
        (
            "sensitivity.yaml",
            "default: internal",
            "default: restricted",
            "sensitivity.yaml: default",
        ),
        (
            "supersession.yaml",
            "revision_order: [A, B, C, D]",
            "revision_order: [A, B, A]",
            "duplicate revision 'A'",
        ),
        (
            "resolution.yaml",
            "order: [authority, recency]",
            "order: [authority, votes]",
            "resolution.yaml: order[1]",
        ),
        (
            "resolution.yaml",
            "order: [authority, recency]",
            "order: [authority, recency]\namendments:\n  - {amending: [avenant], amended: [devis]}",
            "resolution.yaml: amendments[0].amending[0]: unknown doc type 'avenant'",
        ),
        (
            "resolution.yaml",
            "order: [authority, recency]",
            "order: [authority, recency]\namendments:\n  - {amending: [devis], amended: [devis]}",
            "doc types both amending and amended: devis",
        ),
        (
            "resolution.yaml",
            "order: [authority, recency]",
            "order: [authority, recency]\narbitrate:\n  - {types: [devis, mail], reason: Ask.}",
            "resolution.yaml: arbitrate[0].types[1]: unknown doc type 'mail'",
        ),
        (
            "resolution.yaml",
            "order: [authority, recency]",
            "order: [authority, recency]\narbitrate:\n  - {types: [devis], reason: Ask.}",
            "resolution.yaml: arbitrate[0].types",
        ),
        (
            "resolution.yaml",
            "order: [authority, recency]",
            "order: [authority, recency]\narbitrate:\n  - {types: [devis, facture], reason: A.}"
            "\n  - {types: [facture, devis], reason: B.}",
            "duplicate arbitrate pair",
        ),
        (
            "glossary.yaml",
            "  - term: HT",
            "  - term: HT\n    term: X",
            "glossary.yaml: invalid YAML",
        ),
    ],
)
def test_validation_errors_name_file_and_key(
    pack_dir: Path, file: str, old: str, new: str, expected: str
) -> None:
    edit(pack_dir / file, old, new)
    errors = errors_of(pack_dir)
    assert any(expected in error for error in errors), errors


def test_resolution_amendments_and_pairs_to_arbitrate(pack_dir: Path) -> None:
    assert load_pack(pack_dir).resolution.amendments == []
    edit(
        pack_dir / "resolution.yaml",
        "order: [authority, recency]",
        "order: [authority, recency]\n"
        "amendments:\n  - {amending: [facture], amended: [devis]}\n"
        "arbitrate:\n  - {types: [devis, etude-de-prix], reason: Ask the client.}",
    )
    resolution = load_pack(pack_dir).resolution
    assert resolution.amendment("facture", "devis") and not resolution.amendment("devis", "facture")
    assert resolution.amending_types("devis") == {"facture"} and not resolution.amending_types("x")
    pair = resolution.arbitration("etude-de-prix", "devis")
    assert pair is not None and pair.reason == "Ask the client."
    assert resolution.arbitration("devis", "facture") is None


def test_structural_errors(pack_dir: Path) -> None:
    (pack_dir / "topics.yaml").unlink()
    (pack_dir / "glosary.yaml").write_text("terms: []\n", encoding="utf-8")
    (pack_dir / "templates").mkdir()
    errors = errors_of(pack_dir)
    assert "topics.yaml: required file is missing" in errors
    assert "glosary.yaml: unknown file in domain pack" in errors
    assert "templates: unknown folder in domain pack" in errors


def test_optional_files_and_skill_checks(pack_dir: Path) -> None:
    (pack_dir / "supersession.yaml").unlink()
    (pack_dir / "resolution.yaml").unlink()
    (pack_dir / "hints.md").unlink()
    pack = load_pack(pack_dir)
    assert pack.supersession is None and pack.hints is None
    assert pack.resolution.order == ["authority", "recency"]
    skill = pack_dir / "skills" / "check-delivery" / "SKILL.md.j2"
    edit(skill, "{{ max_steps }}", "{% if %}")
    assert any("skills/check-delivery/SKILL.md.j2" in e for e in errors_of(pack_dir))
    edit(skill, "{% if %}", "{{ max_steps }}")
    core = pack_dir / "skills" / "wiki-navigator"
    core.mkdir()
    (core / "SKILL.md.j2").write_text("---\nname: wiki-navigator\n---\n", encoding="utf-8")
    assert any("clashes with a core skill" in e for e in errors_of(pack_dir))


def test_load_pack_missing_folder(tmp_path: Path) -> None:
    with pytest.raises(PackValidationError, match="not found"):
        load_pack(tmp_path / "nope")


def test_overlay_merge_semantics(tmp_path: Path) -> None:
    pack = load_pack(FIXTURE)
    overlay_file = tmp_path / OVERLAY_FILE
    overlay_file.write_text(
        """schema: 1
entities:
  - type: building-element
    key: baie-f1
    label: Baie F1 (south wall)
    aliases:
      - {text: bay window F1, lang: en}
      - {text: sliding door F1, lang: en}
    attributes: {wall: south}
  - type: building-element
    key: baie-f4
    label: Baie F4
glossary:
  - term: ttc
    definition: Amount including VAT (overlay definition).
    synonyms: {fr: [toutes taxes comprises, TVA comprise]}
  - term: BL
    definition: Delivery note (bon de livraison).
topics:
  - slug: window-delivery
    title: Window delivery and installation
    keywords: [installation, delivery date]
    min_score: 4
  - slug: slab-pouring
    title: Slab pouring
    keywords: [slab pouring]
""",
        encoding="utf-8",
    )
    merged = load_pack(FIXTURE, overlay=overlay_file)
    assert merged.overlay_applied and not pack.overlay_applied
    baie = merged.entity("building-element:baie-f1")
    assert baie.label == "Baie F1 (south wall)"
    assert [(a.text, a.lang) for a in baie.aliases] == [
        ("bay window F1", "en"),
        ("baie coulissante F1", "fr"),
        ("sliding door F1", "en"),
    ]
    assert baie.attributes == {"width_cm": 300, "wall": "south"}
    assert merged.entity_ids[-1] == "building-element:baie-f4"
    ttc = merged.glossary.terms[0]
    assert ttc.definition.endswith("(overlay definition).")
    assert ttc.synonyms["fr"] == ["toutes taxes comprises", "TVA comprise"] and ttc.synonyms[
        "en"
    ] == ["including VAT"]
    assert merged.glossary.terms[-1].term == "BL"
    topic = merged.topic("window-delivery")
    assert topic.title == "Window delivery and installation" and topic.min_score == 4
    assert topic.keywords == [
        "window delivery",
        "delivery date",
        "bay window",
        "roof window",
        "installation",
    ]
    assert topic.description == pack.topic("window-delivery").description
    assert merged.topic_ids[-1] == "topic:slab-pouring"
    assert merged.content_hash() != pack.content_hash()


def test_overlay_errors_name_overlay_file(tmp_path: Path) -> None:
    pack = load_pack(FIXTURE)
    with pytest.raises(
        PackValidationError, match=r"overlay.yaml: entities\[0\].type: unknown entity type 'tool'"
    ):
        apply_overlay(
            pack, Overlay.model_validate({"entities": [{"type": "tool", "key": "x", "label": "X"}]})
        )
    bad = tmp_path / OVERLAY_FILE
    bad.write_text("entities: [{type: building-element, key: X, label: x}]\n", encoding="utf-8")
    with pytest.raises(PackValidationError, match=r"overlay.yaml: entities\[0\].key"):
        load_overlay(bad)
    assert load_overlay(tmp_path / "missing.yaml") == Overlay()
    with pytest.raises(PackValidationError, match=r"overlay\.yaml"):
        apply_overlay(
            pack,
            Overlay.model_validate(
                {
                    "glossary": [
                        {"term": "X", "definition": "x", "see_also": ["building-element:baie-f9"]}
                    ]
                }
            ),
        )


def test_accepted_proposals_flow_into_overlay() -> None:
    overlay = Overlay()
    entity = new_proposal(
        "entity",
        EntityProposalPayload(type="building-element", key="baie-f5", label="Baie F5"),
        created_at=NOW,
    )
    with pytest.raises(ValueError, match="accepted"):
        add_proposal(overlay, entity)
    accepted = entity.model_copy(update={"status": "accepted", "decided_by": "operator"})
    overlay = add_proposal(overlay, accepted)
    glossary = new_proposal(
        "glossary",
        GlossaryProposalPayload(term="BC", definition="Purchase order (bon de commande)."),
        created_at=NOW,
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    overlay = add_proposal(overlay, glossary)
    topic = new_proposal(
        "topic",
        TopicProposalPayload(slug="slab-pouring", title="Slab pouring", keywords=["slab pouring"]),
        created_at=NOW,
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    overlay = add_proposal(overlay, topic)
    injection = new_proposal(
        "injection",
        InjectionProposalPayload(source_id="src-0123456789ab", block_id="b0001", reason="canary"),
        created_at=NOW,
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    with pytest.raises(ValueError, match="do not change the overlay"):
        add_proposal(overlay, injection)
    merged = apply_overlay(load_pack(FIXTURE), overlay)
    assert "building-element:baie-f5" in merged.entity_ids
    assert "topic:slab-pouring" in merged.topic_ids
    reloaded = Overlay.model_validate(__import__("yaml").safe_load(dump_overlay(overlay)))
    assert reloaded == overlay


def test_add_proposal_reports_payloads_that_cannot_become_entries() -> None:
    topic = new_proposal(
        "topic",
        TopicProposalPayload(slug="roof-insulation", title="Roof insulation"),
        created_at=NOW,
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    with pytest.raises(PackValidationError, match=r"overlay\.yaml.*keywords or aliases"):
        add_proposal(Overlay(), topic)
    glossary = new_proposal(
        "glossary",
        GlossaryProposalPayload(term="Linteau", definition="Lintel.", synonyms={"x y": ["?"]}),
        created_at=NOW,
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    with pytest.raises(PackValidationError, match=r"overlay\.yaml: synonyms"):
        add_proposal(Overlay(), glossary)


def test_filter_overlay_leaves_out_invalid_entries_one_at_a_time() -> None:
    pack = load_pack(FIXTURE)
    overlay = Overlay.model_validate(
        {
            "entities": [
                {"type": "unknown", "key": "site-hut", "label": "Site hut"},
                {"type": "building-element", "key": "baie-f5", "label": "Baie F5"},
            ],
            "glossary": [
                {"term": "BC", "definition": "Purchase order.", "synonyms": {"it": ["x"]}},
                {"term": "BL", "definition": "Delivery note (bon de livraison)."},
            ],
            "topics": [{"slug": "slab-pouring", "title": "Slab pouring", "keywords": ["slab"]}],
        }
    )
    with pytest.raises(PackValidationError):
        apply_overlay(pack, overlay)
    kept, problems = filter_overlay(pack, overlay)
    assert [entry.id for entry in kept.entities] == ["building-element:baie-f5"]
    assert [term.term for term in kept.glossary] == ["BL"]
    assert [topic.slug for topic in kept.topics] == ["slab-pouring"]
    assert len(problems) == 2
    assert problems[0] == (
        "overlay.yaml entities[0] unknown:site-hut: unknown entity type 'unknown'"
    )
    assert problems[1].startswith("overlay.yaml glossary[0] 'BC': ") and "'it'" in problems[1]
    merged = apply_overlay(pack, kept)
    assert "building-element:baie-f5" in merged.entity_ids
    assert "topic:slab-pouring" in merged.topic_ids
    assert filter_overlay(pack, kept) == (kept, [])
