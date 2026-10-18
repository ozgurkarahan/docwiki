"""Domain packs load with the contracts loader and classify the sample corpus correctly."""

from __future__ import annotations

import re
from pathlib import Path, PurePosixPath
from typing import Any

import jinja2
import jinja2.meta
import pytest
import yaml

from docwiki.domain.loader import load_pack
from docwiki.domain.models import DomainPack
from docwiki.domain.rules import (
    explicit_references,
    match_doc_type,
    parse_doc_number,
    parse_revision,
    sensitivity_for,
    supersession_pairs,
)

PACKS = ("wind-om", "it-runbooks")
KEBAB = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_VARIABLES = {"wiki_title", "paths", "topics", "entity_types"}
INPUT_ROOTS = ("full/", "held-back/", "it-runbooks/")
EXPECTED_TYPES = {
    "manual-gbx": "maintenance-manual",
    "sb-oil": "service-bulletin",
    "sb-pitch-b": "service-bulletin",
    "sop-gbx-b": "sop",
    "wi-gen-fr": "work-instruction",
    "inc-near-miss": "near-miss-report",
    "inc-8d": "incident-report",
    "moc-oil": "moc-record",
    "lift-plan-scan": "lift-plan",
    "deck-spl": "single-point-lesson",
    "deck-onboarding": "training-deck",
    "mail-oem": "email",
    "photo-checklist": "checklist",
    "supplier-de": "supplier-note",
    "rate-card": "rate-card",
    "it-postmortem": "postmortem",
    "it-handbook": "handbook",
}


@pytest.fixture(scope="module")
def packs(repo_root: Path) -> dict[str, DomainPack]:
    return {name: load_pack(repo_root / "domains" / name) for name in PACKS}


def _pack_documents(pack: str, documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [entry for entry in documents if entry["domain"] == pack]


def _input_relative(path: str) -> str:
    """Path relative to the folder given to a build (samples/corpus/full, ...)."""
    for root in INPUT_ROOTS:
        if path.startswith(root):
            return path.removeprefix(root)
    raise AssertionError(path)


def test_packs_are_fictional_with_banner(packs: dict[str, DomainPack]) -> None:
    for name, pack in packs.items():
        assert pack.info.name == name
        assert pack.info.fictional and pack.info.banner
    assert packs["wind-om"].info.languages == ["en", "fr", "de"]
    assert 8 <= len(packs["wind-om"].topics.topics) <= 10
    assert len(packs["wind-om"].skill_templates) == 3


@pytest.mark.parametrize("pack_name", PACKS)
def test_every_sample_is_classified_and_tiered(
    pack_name: str, packs: dict[str, DomainPack], documents: list[dict[str, Any]], extracted
) -> None:
    pack = packs[pack_name]
    for entry in _pack_documents(pack_name, documents):
        name = PurePosixPath(entry["path"]).name
        match = match_doc_type(pack, name, extracted(entry["path"]).text())
        assert match is not None, name
        if entry["id"] in EXPECTED_TYPES:
            assert match.doc_type == EXPECTED_TYPES[entry["id"]], name
        for raw_path in (entry["path"], _input_relative(entry["path"])):
            tier = sensitivity_for(pack, raw_path, match.doc_type)
            assert tier == entry["sensitivity"], f"{raw_path}: {tier}"


def test_supersession_on_the_sample(
    packs: dict[str, DomainPack], documents: list[dict[str, Any]], extracted
) -> None:
    pack = packs["wind-om"]
    sources = []
    for entry in _pack_documents("wind-om", documents):
        name = PurePosixPath(entry["path"]).name
        head = extracted(entry["path"]).text()[:2000]
        number = parse_doc_number(pack, name, head)
        if number is None:
            continue
        assert number == entry["doc_number"], name
        revision = parse_revision(pack, name, head)
        assert revision == entry["revision"], name
        sources.append((entry["id"], number, revision))
    with_held_back = supersession_pairs(pack, sources)
    assert sorted(with_held_back) == [("sb-pitch-b", "sb-pitch-a"), ("sop-gbx-b", "sop-gbx-a")]
    initial = [source for source in sources if source[0] != "sb-pitch-b"]
    assert supersession_pairs(pack, initial) == [("sop-gbx-b", "sop-gbx-a")]
    by_id = {entry["id"]: entry for entry in documents}

    def references(doc_id: str) -> list[str]:
        return explicit_references(pack, extracted(by_id[doc_id]["path"]).text())

    assert references("sop-gbx-b") == ["SOP-GBX-010"]
    assert references("sb-pitch-b") == ["SB-LWS-2025-11"]
    assert references("sb-oil") == [] and references("manual-gbx") == []


def test_wind_registry_covers_the_bible(
    packs: dict[str, DomainPack], bible: dict[str, Any]
) -> None:
    ids = set(packs["wind-om"].entity_ids)
    expected = {f"asset:{t['id'].lower()}" for t in bible["turbines"]}
    expected |= {f"part:{p['part_number'].lower()}" for p in bible["parts"]}
    expected |= {f"alarm-code:{a['code'].lower()}" for a in bible["alarm_codes"]}
    expected |= {f"status-code:{s['code'].lower()}" for s in bible["status_codes"]}
    expected |= {f"component:{c['key']}" for c in bible["components"]}
    expected |= {
        f"organisation:{o['key']}" for o in bible["organisations"] if o["key"] != "relecloud"
    }
    expected |= {f"procedure:{key}" for key in ("sop-gbx-010", "sop-loto-001", "sop-wah-003",
                                               "wi-gen-014", "spl-012")}
    assert expected <= ids, sorted(expected - ids)
    for term in packs["wind-om"].glossary.terms:
        assert term.synonyms.get("fr") and term.synonyms.get("de"), term.term


@pytest.mark.parametrize("pack_name", PACKS)
def test_skill_templates_render_with_catalog_values(
    pack_name: str, packs: dict[str, DomainPack]
) -> None:
    pack = packs[pack_name]
    assert 1 <= len(pack.skill_templates) <= 3
    env = jinja2.Environment(undefined=jinja2.StrictUndefined, autoescape=False,
                             keep_trailing_newline=True)
    paths = {"index": "index.md", "glossary": "glossary.md", "log": "log.md",
             "sources_index": "sources/index.md", "entities_index": "entities/index.md",
             "topics_index": "topics/index.md"}
    full = {
        "wiki_title": pack.info.wiki_title,
        "paths": paths,
        "topics": [{"slug": t.slug, "title": t.title, "path": f"topics/{t.slug}.md"}
                   for t in pack.topics.topics],
        "entity_types": [{"key": t.key, "title": t.title, "path": f"entities/{t.key}/index.md"}
                         for t in pack.entities.types],
    }
    empty = dict(full, topics=[], entity_types=[])
    for name, source in pack.skill_templates.items():
        assert jinja2.meta.find_undeclared_variables(env.parse(source)) <= SKILL_VARIABLES
        for context in (full, empty):
            rendered = env.from_string(source).render(**context)
            _, front, body = rendered.split("---\n", 2)
            frontmatter = yaml.safe_load(front)
            assert set(frontmatter) == {"name", "description"}
            assert frontmatter["name"] == name and KEBAB.match(name) and len(name) <= 64
            assert len(frontmatter["description"]) <= 1024
            assert len(body.split()) <= 5000
            assert "{{" not in rendered and "{%" not in rendered
