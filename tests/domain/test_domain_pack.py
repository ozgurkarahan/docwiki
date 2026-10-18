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
    assert pack.name == "mini-wind"
    assert pack.info.fictional and pack.info.languages == ["en", "fr", "de"]
    assert [t.key for t in pack.taxonomy.doc_types] == [
        "sop",
        "service-bulletin",
        "maintenance-plan",
    ]
    assert pack.entity_ids[0] == "asset:wtg-07"
    assert pack.entity("organisation:litware").label == "Litware"
    assert pack.topic("gearbox-oil").aliases[1].text == "Getriebeöl"
    assert pack.supersession is not None and pack.supersession.revision_order == [
        "A",
        "B",
        "C",
        "D",
    ]
    assert pack.resolution.order == ["authority", "recency"]
    assert pack.hints and "WTG-NN" in pack.hints
    assert list(pack.skill_templates) == ["troubleshoot-alarm"]
    assert pack.content_hash() == load_pack(FIXTURE).content_hash()


def test_content_hash_changes_with_content(pack_dir: Path) -> None:
    before = load_pack(pack_dir).content_hash()
    edit(pack_dir / "glossary.yaml", "Supervisory control", "Supervisory control (edited)")
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
            '"(?i)^sop[-_ ]"',
            '"(?i)^sop[-_ "',
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
        ("entities.yaml", "  - type: procedure\n", "  - type: tool\n", "uses unknown type 'tool'"),
        (
            "entities.yaml",
            "  - key: asset\n",
            "  - key: topic\n",
            "entity type 'topic' is reserved",
        ),
        ("entities.yaml", "key: wtg-07", "key: WTG-07", "entities.yaml: registry[0].key"),
        (
            "entities.yaml",
            "{text: turbine 7, lang: en}",
            "{text: turbine 7, lang: es}",
            "entities.yaml: registry[0].aliases[0].lang",
        ),
        (
            "topics.yaml",
            "    keywords: [cold weather, low temperature]\n",
            "",
            "needs keywords or aliases",
        ),
        (
            "glossary.yaml",
            "see_also: [procedure:sop-gbx-010]",
            "see_also: [procedure:sop-gbx-999]",
            "glossary.yaml: terms[0].see_also[0]",
        ),
        ("glossary.yaml", "  - term: SCADA", "  - term: loto", "duplicate glossary term 'loto'"),
        (
            "sensitivity.yaml",
            "doc_type: maintenance-plan",
            "doc_type: rate-card",
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
            "glossary.yaml",
            "  - term: SCADA",
            "  - term: SCADA\n    term: X",
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
    skill = pack_dir / "skills" / "troubleshoot-alarm" / "SKILL.md.j2"
    edit(skill, "{{ max_steps }}", "{% if %}")
    assert any("skills/troubleshoot-alarm/SKILL.md.j2" in e for e in errors_of(pack_dir))
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
  - type: asset
    key: wtg-07
    label: WTG-07 (north row)
    aliases:
      - {text: turbine 7, lang: en}
      - {text: Anlage 7, lang: de}
    attributes: {row: north}
  - type: asset
    key: wtg-08
    label: WTG-08
glossary:
  - term: loto
    definition: Lockout/tagout (overlay definition).
    synonyms: {fr: [consignation, condamnation]}
  - term: MOC
    definition: Management of change.
topics:
  - slug: gearbox-oil
    title: Gearbox oil and lubrication
    keywords: [lubrication, oil grade]
    min_score: 4
  - slug: blade-inspection
    title: Blade inspection
    keywords: [blade inspection]
""",
        encoding="utf-8",
    )
    merged = load_pack(FIXTURE, overlay=overlay_file)
    assert merged.overlay_applied and not pack.overlay_applied
    wtg07 = merged.entity("asset:wtg-07")
    assert wtg07.label == "WTG-07 (north row)"
    assert [(a.text, a.lang) for a in wtg07.aliases] == [
        ("turbine 7", "en"),
        ("éolienne 7", "fr"),
        ("Anlage 7", "de"),
    ]
    assert wtg07.attributes == {"rated_kw": 3000, "row": "north"}
    assert merged.entity_ids[-1] == "asset:wtg-08"
    loto = merged.glossary.terms[0]
    assert loto.definition.endswith("(overlay definition).")
    assert loto.synonyms["fr"] == ["consignation", "condamnation"] and loto.synonyms["en"] == [
        "lockout/tagout"
    ]
    assert merged.glossary.terms[-1].term == "MOC"
    topic = merged.topic("gearbox-oil")
    assert topic.title == "Gearbox oil and lubrication" and topic.min_score == 4
    assert topic.keywords == [
        "gearbox oil",
        "oil grade",
        "viscosity grade",
        "oil change",
        "lubrication",
    ]
    assert topic.description == pack.topic("gearbox-oil").description
    assert merged.topic_ids[-1] == "topic:blade-inspection"
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
    bad.write_text("entities: [{type: asset, key: X, label: x}]\n", encoding="utf-8")
    with pytest.raises(PackValidationError, match=r"overlay.yaml: entities\[0\].key"):
        load_overlay(bad)
    assert load_overlay(tmp_path / "missing.yaml") == Overlay()
    with pytest.raises(PackValidationError, match=r"overlay\.yaml"):
        apply_overlay(
            pack,
            Overlay.model_validate(
                {"glossary": [{"term": "X", "definition": "x", "see_also": ["asset:wtg-99"]}]}
            ),
        )


def test_accepted_proposals_flow_into_overlay() -> None:
    overlay = Overlay()
    entity = new_proposal(
        "entity", EntityProposalPayload(type="asset", key="wtg-09", label="WTG-09"), created_at=NOW
    )
    with pytest.raises(ValueError, match="accepted"):
        add_proposal(overlay, entity)
    accepted = entity.model_copy(update={"status": "accepted", "decided_by": "operator"})
    overlay = add_proposal(overlay, accepted)
    glossary = new_proposal(
        "glossary",
        GlossaryProposalPayload(term="SPL", definition="Single-point lesson."),
        created_at=NOW,
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    overlay = add_proposal(overlay, glossary)
    topic = new_proposal(
        "topic",
        TopicProposalPayload(slug="curtailment", title="Curtailment", keywords=["curtailment"]),
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
    assert "asset:wtg-09" in merged.entity_ids and "topic:curtailment" in merged.topic_ids
    reloaded = Overlay.model_validate(__import__("yaml").safe_load(dump_overlay(overlay)))
    assert reloaded == overlay


def test_add_proposal_reports_payloads_that_cannot_become_entries() -> None:
    topic = new_proposal(
        "topic", TopicProposalPayload(slug="noise", title="Noise"), created_at=NOW
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    with pytest.raises(PackValidationError, match=r"overlay\.yaml.*keywords or aliases"):
        add_proposal(Overlay(), topic)
    glossary = new_proposal(
        "glossary",
        GlossaryProposalPayload(term="Yaw", definition="Rotation.", synonyms={"x y": ["?"]}),
        created_at=NOW,
    ).model_copy(update={"status": "accepted", "decided_by": "operator"})
    with pytest.raises(PackValidationError, match=r"overlay\.yaml: synonyms"):
        add_proposal(Overlay(), glossary)


def test_filter_overlay_leaves_out_invalid_entries_one_at_a_time() -> None:
    pack = load_pack(FIXTURE)
    overlay = Overlay.model_validate(
        {
            "entities": [
                {"type": "unknown", "key": "pump-station", "label": "Pump station"},
                {"type": "asset", "key": "wtg-09", "label": "WTG-09"},
            ],
            "glossary": [
                {"term": "SPL", "definition": "Single-point lesson.", "synonyms": {"it": ["x"]}},
                {"term": "LOTO-2", "definition": "Second lockout/tagout procedure."},
            ],
            "topics": [{"slug": "curtailment", "title": "Curtailment", "keywords": ["curtail"]}],
        }
    )
    with pytest.raises(PackValidationError):
        apply_overlay(pack, overlay)
    kept, problems = filter_overlay(pack, overlay)
    assert [entry.id for entry in kept.entities] == ["asset:wtg-09"]
    assert [term.term for term in kept.glossary] == ["LOTO-2"]
    assert [topic.slug for topic in kept.topics] == ["curtailment"]
    assert len(problems) == 2
    assert problems[0] == (
        "overlay.yaml entities[0] unknown:pump-station: unknown entity type 'unknown'"
    )
    assert problems[1].startswith("overlay.yaml glossary[0] 'SPL': ") and "'it'" in problems[1]
    merged = apply_overlay(pack, kept)
    assert "asset:wtg-09" in merged.entity_ids and "topic:curtailment" in merged.topic_ids
    assert filter_overlay(pack, kept) == (kept, [])
