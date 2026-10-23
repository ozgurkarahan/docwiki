"""Scopes and the three classification axes (v1.7, ADR 0011): read from the raw path only."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from docwiki.contracts.ids import (
    format_hub_id,
    format_topic_id,
    hub_page_path,
    index_page_path,
    parse_topic_id,
    topic_page_path,
)
from docwiki.domain.loader import PackValidationError, load_pack
from docwiki.domain.models import RegistryEntry
from docwiki.domain.rules import (
    ScopeAxes,
    document_scope,
    entity_in_scope,
    entity_scope,
    scope_axes,
)
from docwiki.stages.discover import SupersessionRecord, resolve_supersession

MINI = Path(__file__).resolve().parent / "fixtures" / "mini-pack"

SCOPES = """
name: chantier
title: Chantier
plural: chantiers
default: {key: entreprise, title: Entreprise}
paths:
  - regex: '^chantiers/(?P<scope>[a-z0-9-]+)/(?P<phase>[0-5])[^/]*/(?P<type>[a-z0-9-]+)/'
  - regex: '^chantiers/(?P<scope>[a-z0-9-]+)/'
  - regex: '^entreprise/(?P<type>[a-z0-9-]+)/'
phases:
  - {key: "1", title: marché}
  - {key: "3", title: exécution}
lot_regex: '(?i)lot[-_ ]?(?P<lot>\\d{1,2})'
"""


@pytest.fixture
def pack_dir(tmp_path: Path) -> Path:
    target = tmp_path / "pack"
    shutil.copytree(MINI, target)
    (target / "scopes.yaml").write_text(SCOPES, encoding="utf-8")
    return target


def test_scope_and_axes_come_from_the_path(pack_dir: Path) -> None:
    pack = load_pack(pack_dir)
    assert pack.scopes is not None and pack.scopes.phase_title("3") == "exécution"
    assert scope_axes(pack, "chantiers/residence/3-execution/devis/DEV-2026-020 lot 4.pdf") == (
        ScopeAxes(scope="residence", phase="3", doc_type="devis", lot="4")
    )
    # a type the pack does not know is not taken from the path
    assert scope_axes(pack, "chantiers/ecole/1-marche/inconnu/x.pdf").doc_type is None
    assert scope_axes(pack, "chantiers/ecole/notes.txt") == ScopeAxes(scope="ecole")
    assert scope_axes(pack, "entreprise/facture/FA-1.pdf") == ScopeAxes(
        scope="entreprise", doc_type="facture"
    )
    assert scope_axes(pack, "anything/else.pdf").scope == "entreprise"


def test_without_scopes_nothing_changes() -> None:
    assert scope_axes(load_pack(MINI), "chantiers/residence/x.pdf") == ScopeAxes()


def test_a_path_regex_may_only_name_known_groups(pack_dir: Path) -> None:
    (pack_dir / "scopes.yaml").write_text(
        SCOPES.replace("(?P<phase>", "(?P<stage>"), encoding="utf-8"
    )
    with pytest.raises(PackValidationError, match="unknown named groups"):
        load_pack(pack_dir)


def test_the_hubs_folder_may_not_take_a_reserved_wiki_folder(pack_dir: Path) -> None:
    (pack_dir / "scopes.yaml").write_text(
        SCOPES.replace("plural: chantiers", "plural: topics"), encoding="utf-8"
    )
    with pytest.raises(PackValidationError, match="reserved wiki folder"):
        load_pack(pack_dir)


def test_revisions_supersede_within_their_scope_only(pack_dir: Path) -> None:
    pack = load_pack(pack_dir)
    records = [
        SupersessionRecord("src-a", "DEV-2026-001", "A", scope="ecole"),
        SupersessionRecord("src-b", "DEV-2026-001", "B", scope="ecole"),
        SupersessionRecord("src-c", "DEV-2026-001", "B", scope="residence"),
        SupersessionRecord("src-d", "DEV-2026-002", "A", ("DEV-2026-001",), scope="residence"),
    ]
    groups, pairs = resolve_supersession(pack, records)
    assert groups["ecole/DEV-2026-001"] == ["src-a", "src-b"]
    assert groups["residence/DEV-2026-001"] == ["src-c"]
    # B of the école replaces its A; the résidence's documents never touch the école's
    assert ("src-b", "src-a") in pairs
    assert ("src-c", "src-a") not in pairs
    # an explicit "annule et remplace" reaches the same number in the same scope only
    assert ("src-d", "src-c") in pairs and ("src-d", "src-a") not in pairs


def test_hub_and_scoped_topic_ids() -> None:
    assert hub_page_path(format_hub_id("chantiers", "moreau")) == "chantiers/moreau.md"
    assert index_page_path("hubs/chantiers") == "chantiers/index.md"
    scoped = format_topic_id("marche-et-avenants", "moreau")
    assert scoped == "topic:moreau/marche-et-avenants"
    assert parse_topic_id(scoped) == "moreau/marche-et-avenants"
    assert topic_page_path(scoped) == "topics/moreau/marche-et-avenants.md"
    assert topic_page_path(format_topic_id("procedures")) == "topics/procedures.md"
    with pytest.raises(ValueError):
        parse_topic_id("topic:a/b/c")


def test_an_entity_with_the_scope_attribute_belongs_to_that_scope(pack_dir: Path) -> None:
    pack = load_pack(pack_dir)
    lot = RegistryEntry(
        type="work-package", key="lot-5", label="Lot 5", attributes={"lot": 5, "chantier": "ecole"}
    )
    shared = RegistryEntry(type="organisation", key="atelier", label="Atelier")
    plural = RegistryEntry(
        type="organisation", key="sous-traitant", label="S", attributes={"chantiers": "ecole"}
    )
    named = RegistryEntry(
        type="building-element", key="baie", label="Baie", attributes={"chantier": "Ecole "}
    )
    assert entity_scope(pack, lot) == "ecole" and entity_scope(pack, named) == "ecole"
    assert entity_scope(pack, shared) is None and entity_scope(pack, plural) is None
    assert entity_in_scope(pack, lot, "ecole")
    # another scope, the default scope and a page without scope do not mention it
    for scope in ("residence", "entreprise", None):
        assert not entity_in_scope(pack, lot, scope)
        assert entity_in_scope(pack, shared, scope) and entity_in_scope(pack, plural, scope)
    # the document's scope: the recorded one, else the one of its raw path
    assert document_scope(pack, None, "chantiers/ecole/notes.txt") == "ecole"
    assert document_scope(pack, "residence", "chantiers/ecole/notes.txt") == "residence"
    assert document_scope(pack, None, "anything/else.pdf") == "entreprise"


def test_without_scopes_every_entity_is_company_wide() -> None:
    pack = load_pack(MINI)
    lot = RegistryEntry(type="work-package", key="lot-5", label="L", attributes={"chantier": "x"})
    assert entity_scope(pack, lot) is None
    assert entity_in_scope(pack, lot, None) and entity_in_scope(pack, lot, "y")
    assert document_scope(pack, None, "chantiers/x/notes.txt") is None
