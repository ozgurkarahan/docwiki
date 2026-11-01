"""``answer_context`` coverage and gaps (``DOCWIKI_ANSWER_CONTEXT_COVERAGE``, off by default).

A scoped copy of the mock release is staged with three chantiers: ``moreau`` (the two schedule
revisions), ``nacrines`` (the site minutes) and ``ecole-montferrine`` (a hub and no document),
each with its hub and its registry entity page (title and aliases), plus the hub of the default
scope ``entreprise`` (no entity page: never named).
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from mcp_testkit import MINUTES, NOW, PLAN_A, PLAN_B, copy_fixture, stage_release

from docwiki.contracts.settings import SETTINGS_DEFAULTS, SettingsKeys
from docwiki.contracts.storage import FolderStorage
from docwiki.mcp.bounds import dumps
from docwiki.mcp.config import McpConfig
from docwiki.mcp.source import FolderReleaseSource
from docwiki.mcp.tools_read import (
    COVERAGE_MAX_CHARS,
    GAP_COUNT_CAP,
    MAX_GAP_CHECKS,
    ReadTools,
)
from docwiki.release import publish_release

Json = Callable[[str], dict[str, Any]]
SCOPES = {PLAN_A: "moreau", PLAN_B: "moreau", MINUTES: "nacrines"}
ON = McpConfig(answer_context_coverage=True)


def _common(title: str) -> dict[str, Any]:
    return {
        "title": title,
        "summary": "Fictional sample.",
        "sensitivity": "public",
        "updated": date(2026, 4, 1),
    }


def _hub(scope: str, title: str, sources: list[str], body: str) -> tuple[str, dict[str, Any], str]:
    return (
        f"chantiers/{scope}.md",
        {
            **_common(title),
            "id": f"hub:chantiers/{scope}",
            "type": "hub",
            "scope_type": "chantier",
            "scope": scope,
            "sources": sorted(sources),
        },
        f"# {title}\n\n{body}\n",
    )


def _entity(key: str, title: str, aliases: list[tuple[str, str]]) -> tuple[str, dict, str]:
    return (
        f"entities/chantier/{key}.md",
        {
            **_common(title),
            "id": f"chantier:{key}",
            "type": "entity",
            "entity_type": "chantier",
            "key": key,
            "aliases": [{"text": text, "lang": lang} for text, lang in aliases],
        },
        f"# {title}\n\nA chantier of the company.\n",
    )


EXTRA_PAGES = [
    _hub("moreau", "Chantier Moreau", [PLAN_A, PLAN_B], "Its schedule and purchase tracking."),
    _hub("nacrines", "Chantier résidence Les Nacrines", [MINUTES], "Its site minutes."),
    _hub("ecole-montferrine", "Chantier Montferrine", [], "No documents yet."),
    _hub("entreprise", "Entreprise", [], "Company-wide documents."),
    _entity("moreau", "Chantier Moreau", [("chantier Moreau", "fr"), ("Moreau site", "en")]),
    _entity(
        "nacrines",
        "Chantier résidence Les Nacrines",
        [("résidence Les Nacrines", "fr"), ("Les Nacrines", "fr")],
    ),
    _entity(
        "ecole-montferrine",
        "Chantier école de Montferrine",
        [
            ("école élémentaire du Bourg", "fr"),
            ("école du Bourg", "fr"),
            ("école de Montferrine", "fr"),
        ],
    ),
    (
        "chantiers/index.md",
        {**_common("Chantiers"), "id": "index:hubs/chantiers", "type": "index"},
        "# Chantiers\n\n- [Chantier Moreau](moreau.md)\n- [Les Nacrines](nacrines.md)\n",
    ),
]

QUESTIONS = [
    "When will the menuiseries be delivered?",
    "Livraison des menuiseries du chantier Moreau",
    "Compare the delivery of the menuiseries at Les Nacrines and on the Moreau site",
    "Qui livre l'école du Bourg ?",
    "Quel chantier de l'entreprise a un site ?",
]

# sha256 of the flag-off answer_context output for QUESTIONS on the staged release, recorded
# before coverage existed (regenerate only when answer_context changes on purpose).
OFF_SNAPSHOT = {
    QUESTIONS[0]: "9e63809bf5cbd286b4a22ceea4fe8804fa4b8d15729ded9f12667082e8e75375",
    QUESTIONS[1]: "3a793fa4bb20d1a50637b0956f01d338d9b46ddf4040e638bb989e75fee9a2ad",
    QUESTIONS[2]: "ed86cb61ea097876a7e57043502b73e76f50777150cc5c9f322639630b02a391",
    QUESTIONS[3]: "c35f3bd7afc2ad7244711f3235e522243eba31b9f463c4716ec6b8c58eaa3e7d",
    QUESTIONS[4]: "fb93fc2ae68b6795b2089f087aa81af6bf9bfeee176d9e07959f7bfcc4c67d1b",
}


@pytest.fixture
def root(tmp_path: Path) -> Path:
    target = copy_fixture(tmp_path / "mock")
    staged = stage_release(
        tmp_path / "staged", created_at=NOW, scopes=SCOPES, extra_pages=EXTRA_PAGES
    )
    publish_release(FolderStorage(target, fsync=False), staged)
    return target


@pytest.fixture
def off(root: Path) -> ReadTools:
    return ReadTools(FolderReleaseSource(root), McpConfig())


@pytest.fixture
def on(root: Path) -> ReadTools:
    return ReadTools(FolderReleaseSource(root), ON)


def _named(tools: ReadTools, question: str) -> dict[str, str]:
    return tools._named_scopes(tools.snapshot(), question)


# --- flag ----------------------------------------------------------------------------------


def test_flag_is_off_by_default_and_read_from_the_environment() -> None:
    key = SettingsKeys.ANSWER_CONTEXT_COVERAGE
    assert SETTINGS_DEFAULTS[key] == "off"
    assert McpConfig().answer_context_coverage is False
    assert McpConfig.from_env({}).answer_context_coverage is False
    assert McpConfig.from_env({key: "off"}).answer_context_coverage is False
    assert McpConfig.from_env({key: "on"}).answer_context_coverage is True
    assert McpConfig.from_env({key: " ON "}).answer_context_coverage is True


@pytest.mark.parametrize("value", ["1", "true", "yes", "enabled", "of"])
def test_invalid_flag_value_is_an_error(value: str) -> None:
    key = SettingsKeys.ANSWER_CONTEXT_COVERAGE
    with pytest.raises(ValueError, match=f"{key} must be 'on' or 'off', got '{value}'"):
        McpConfig.from_env({key: value})


# --- flag off: unchanged output --------------------------------------------------------------


@pytest.mark.parametrize("question", QUESTIONS)
def test_flag_off_output_matches_the_snapshot(off: ReadTools, question: str) -> None:
    out = off.answer_context(question)
    assert hashlib.sha256(out.encode("utf-8")).hexdigest() == OFF_SNAPSHOT[question]
    assert '"coverage"' not in out and '"gaps"' not in out


@pytest.mark.parametrize("question", QUESTIONS)
@pytest.mark.parametrize("limit", [1, 5, 10])
def test_hits_are_byte_identical_with_the_flag_on(
    off: ReadTools, on: ReadTools, as_json: Json, question: str, limit: int
) -> None:
    before = off.answer_context(question, limit=limit)
    after = on.answer_context(question, limit=limit)
    assert after.startswith(before[:-1] + ',"coverage":[')
    assert dumps(as_json(after)["hits"]) == dumps(as_json(before)["hits"])
    assert len(after) - len(before) <= COVERAGE_MAX_CHARS


def test_flag_on_changes_nothing_with_within_a_later_window_or_no_scopes(
    off: ReadTools, on: ReadTools, as_json: Json
) -> None:
    question = QUESTIONS[2]
    assert on.answer_context(question, within="moreau") == off.answer_context(
        question, within="moreau"
    )
    assert on.answer_context(question, limit=1, offset=1) == off.answer_context(
        question, limit=1, offset=1
    )
    from mcp_testkit import FIXTURE_ROOT

    plain_off = ReadTools(FolderReleaseSource(FIXTURE_ROOT), McpConfig())
    plain_on = ReadTools(FolderReleaseSource(FIXTURE_ROOT), ON)
    for text in QUESTIONS:
        assert plain_on.answer_context(text) == plain_off.answer_context(text)


# --- detection ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("Livraison des menuiseries du chantier Moreau", {"moreau": "chantier Moreau"}),
        ("What is late on the Moreau site?", {"moreau": "Moreau site"}),
        ("moreau", {"moreau": "moreau"}),
        ("MOREAU: planning", {"moreau": "MOREAU"}),
        ("Résidence les nacrines", {"nacrines": "Résidence les nacrines"}),
        ("les NACRINES", {"nacrines": "les NACRINES"}),
        ("Réception de l'ECOLE DE MONTFERRINE", {"ecole-montferrine": "ECOLE DE MONTFERRINE"}),
        ("Quand l'école du Bourg ouvre-t-elle ?", {"ecole-montferrine": "école du Bourg"}),
        ("ecole-montferrine", {"ecole-montferrine": "ecole-montferrine"}),
        ("Montferrine", {"ecole-montferrine": "Montferrine"}),
        (
            "Compare Les Nacrines, the Moreau site and Montferrine",
            {
                "nacrines": "Les Nacrines",
                "moreau": "Moreau site",
                "ecole-montferrine": "Montferrine",
            },
        ),
    ],
)
def test_named_chantiers_are_detected(on: ReadTools, question: str, expected: dict) -> None:
    named = _named(on, question)
    assert named == expected
    assert list(named) == list(expected), "order of first mention"


@pytest.mark.parametrize(
    "question",
    [
        "Quel chantier de l'entreprise a une école ?",
        "Which site of the company is late?",
        "Les menuiseries de la résidence",
        "Moreaux and Nacrine are not chantier names",
        "Le bourg, l'élémentaire et l'école",
        "Chantier",
        "",
    ],
)
def test_common_words_name_no_chantier(on: ReadTools, question: str) -> None:
    assert _named(on, question) == {}


def test_a_release_without_scopes_names_nothing(as_json: Json) -> None:
    from mcp_testkit import FIXTURE_ROOT

    plain = ReadTools(FolderReleaseSource(FIXTURE_ROOT), ON)
    assert _named(plain, "chantier Moreau") == {}


# --- coverage and gaps ----------------------------------------------------------------------


def test_coverage_counts_hits_per_chantier(on: ReadTools, as_json: Json) -> None:
    result = as_json(on.answer_context(QUESTIONS[2], limit=10))
    by_scope = {item["scope"]: item for item in result["coverage"]}
    hits = result["hits"]
    for scope, item in by_scope.items():
        ranks = [hit["rank"] for hit in hits if hit.get("scope") == scope]
        assert item["hits"] == len(ranks)
        assert item["best_rank"] == (min(ranks) if ranks else None)
        assert item["candidates"] >= item["hits"]
        assert item["hub"] == f"chantiers/{scope}.md"
    assert by_scope["moreau"]["named_as"] == "Moreau site"
    assert by_scope["nacrines"]["named_as"] == "Les Nacrines"
    assert "named_as" not in by_scope.get("entreprise", {})
    ranks = [item["best_rank"] for item in result["coverage"]]
    assert ranks == sorted(ranks, key=lambda rank: (rank is None, rank or 0))
    # the first Moreau candidate ranks 11th: a gap even with ten hits
    assert by_scope["moreau"]["hits"] == 0 and by_scope["moreau"]["candidates"] > 0
    assert [gap["scope"] for gap in result["gaps"]] == ["moreau"]


def test_a_named_chantier_cut_from_the_hits_is_a_gap_with_matches(
    on: ReadTools, as_json: Json
) -> None:
    result = as_json(on.answer_context(QUESTIONS[2], limit=1))
    (top,) = result["hits"]
    named = {"moreau", "nacrines"}
    missing = named - {top.get("scope")}
    assert missing, "one hit cannot cover two chantiers"
    gaps = {gap["scope"]: gap for gap in result["gaps"]}
    assert set(gaps) == missing
    for scope, gap in gaps.items():
        assert gap["in_scope_matches"] > 0
        assert f"answer_context(within='{scope}')" in gap["hint"]
        scoped = as_json(on.answer_context(QUESTIONS[2], within=scope, limit=10))
        assert scoped["hits"], "the gap's matches are really there"
        assert all(hit["scope"] == scope for hit in scoped["hits"])


def test_a_gap_without_matches_never_says_absent(on: ReadTools, as_json: Json) -> None:
    result = as_json(on.answer_context(QUESTIONS[3]))
    (gap,) = result["gaps"]
    assert gap["scope"] == "ecole-montferrine" and gap["named_as"] == "école du Bourg"
    assert gap["in_scope_matches"] == 0
    assert "absent" not in gap["hint"] and "within='ecole-montferrine'" in gap["hint"]
    scoped = as_json(on.answer_context(QUESTIONS[3], within="ecole-montferrine"))
    assert scoped["hits"] == [], "zero means zero in-scope matches for these words"
    (item,) = [c for c in result["coverage"] if c["scope"] == "ecole-montferrine"]
    assert (item["hits"], item["best_rank"], item["candidates"]) == (0, None, 0)
    assert item["hub"] == "chantiers/ecole-montferrine.md"


def test_gap_counts_agree_with_scoped_calls(on: ReadTools, as_json: Json) -> None:
    question = "Menuiseries: Moreau site, Les Nacrines, école du Bourg"
    result = as_json(on.answer_context(question, limit=1))
    assert result["gaps"]
    for gap in result["gaps"]:
        scoped = as_json(on.answer_context(question, within=gap["scope"], limit=10))
        assert (gap["in_scope_matches"] > 0) == bool(scoped["hits"])
        assert gap["in_scope_matches"] <= GAP_COUNT_CAP


def test_only_the_first_named_gaps_are_checked(
    on: ReadTools, as_json: Json, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str | None] = []
    original = ReadTools._context_candidates

    def counted(self: ReadTools, snap: Any, question: str, scope: Any, *rest: Any) -> Any:
        calls.append(scope)
        return original(self, snap, question, scope, *rest)

    monkeypatch.setattr("docwiki.mcp.tools_read.MAX_GAP_CHECKS", 1)
    monkeypatch.setattr(ReadTools, "_context_candidates", counted)
    question = "Montferrine et Les Nacrines"
    result = as_json(on.answer_context(question, limit=1))
    gaps = [gap for gap in result["gaps"]]
    assert MAX_GAP_CHECKS == 4
    unchecked = [gap for gap in gaps if gap["in_scope_matches"] is None]
    assert len(gaps) - len(unchecked) <= 1
    assert all("answer_context(within=" in gap["hint"] for gap in unchecked)
    assert len([scope for scope in calls if scope]) == len(gaps) - len(unchecked)


def test_coverage_stays_within_its_reserved_budget(
    root: Path, as_json: Json, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("docwiki.mcp.tools_read.COVERAGE_MAX_CHARS", 260)
    tools = ReadTools(FolderReleaseSource(root), ON)
    plain = ReadTools(FolderReleaseSource(root), McpConfig())
    question = "Menuiseries: Moreau site, Les Nacrines, école du Bourg"
    before, after = plain.answer_context(question), tools.answer_context(question)
    assert len(after) - len(before) <= 260
    result = as_json(after)
    assert result["coverage_truncated"] is True
    assert dumps(result["hits"]) == dumps(as_json(before)["hits"])


def test_coverage_is_json_after_the_unchanged_keys(on: ReadTools, off: ReadTools) -> None:
    after = json.loads(on.answer_context(QUESTIONS[1]))
    before = json.loads(off.answer_context(QUESTIONS[1]))
    assert list(after)[: len(before)] == list(before)
    assert list(after)[len(before) :] == ["coverage", "gaps"]
