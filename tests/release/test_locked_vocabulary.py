"""Gate G16 (locked vocabulary): no page renders a locked trade term with a banned rendering."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from docwiki.contracts.gates import GATES, Violation
from docwiki.release.validate import validate_release
from docwiki.stages.verify import verify_release

MOCK = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"
MOCK_ID = "20260401T090000Z-7ce99a3f"
TOPIC = "topics/schedule-and-window-delivery.md"
TERMS = {
    "conducteur de travaux": ["site manager", "works manager"],
    "réception": ["handover"],
}


@pytest.fixture
def release(tmp_path: Path) -> Path:
    target = tmp_path / "release"
    shutil.copytree(MOCK / "releases" / MOCK_ID, target)
    return target


def _append(release: Path, *lines: str, page: str = TOPIC) -> tuple[Path, int]:
    """Append ``lines`` to a page; returns the file and the 1-based line of the first one."""
    file = release / "wiki" / page
    text = file.read_text(encoding="utf-8")
    first = text.count("\n") + 1
    file.write_text(text + "\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    return file, first


def _g16(release: Path, terms: dict[str, list[str]] | None = TERMS) -> list[Violation]:
    violations = validate_release(release, require_manifest=False, locked_terms=terms)
    return [violation for violation in violations if violation.gate == "G16"]


def test_g16_is_a_blocking_gate():
    spec = GATES["G16"]
    assert spec.blocking and spec.name == "locked-vocabulary"


def test_a_clean_release_passes(release: Path):
    assert _g16(release) == []
    result = verify_release(release, audience="public", locked_terms=TERMS)
    gates = {gate.gate: gate for gate in result.gates}
    assert gates["G16"].status == "pass"
    assert "G16" not in result.skipped


def test_a_banned_rendering_in_the_body_fails_the_gate(release: Path):
    _, line = _append(release, "The site manager signed the minutes.")
    [violation] = _g16(release)
    assert violation.code == "banned-rendering" and violation.severity == "error"
    assert violation.path == f"wiki/{TOPIC}" and violation.line == line
    assert violation.message == (
        '"site manager" is a banned rendering of the locked term "conducteur de travaux"'
    )
    result = verify_release(release, audience="public", locked_terms=TERMS)
    assert "G16" in {gate.gate for gate in result.blocking}
    assert not result.passed


def test_a_banned_rendering_in_the_title_fails_the_gate(release: Path):
    file = release / "wiki" / TOPIC
    text = file.read_text(encoding="utf-8")
    file.write_text(
        text.replace("title: Schedule and window delivery", "title: Schedule and handover", 1),
        encoding="utf-8",
        newline="\n",
    )
    [violation] = _g16(release)
    assert violation.line == 4
    assert violation.message == '"handover" is a banned rendering of the locked term "réception"'


def test_matching_ignores_case_whitespace_and_plurals(release: Path):
    _, line = _append(
        release, "Handover of the extension.", "Two Site\tManagers attended.", "HANDOVERS."
    )
    found = [(v.line, v.message.split('"')[1]) for v in _g16(release)]
    assert found == [(line, "handover"), (line + 1, "site manager"), (line + 2, "handover")]


def test_matching_respects_word_boundaries(release: Path):
    _append(
        release,
        "The handoverage and prehandover checks are not words of the pack.",
        "The on-site managerial review is not a site-manager either.",
        "A hand-over is only banned when it is listed.",
    )
    assert _g16(release) == []
    assert [v.line for v in _g16(release, {"réception": ["hand-over"]})] != []


def test_quoted_document_text_is_not_checked(release: Path):
    _, line = _append(
        release,
        "> The site manager confirms the date.",
        '   > quoted "handover" in a nested blockquote',
        'The minutes say "the site manager confirms" and “handover planned” and « handover ».',
        'The works manager was quoted as "on time".',
    )
    [violation] = _g16(release)
    assert violation.line == line + 3
    assert violation.message.startswith('"works manager"')


def test_the_gate_is_skipped_without_locked_terms(release: Path):
    _append(release, "The site manager signed the minutes.")
    assert _g16(release, None) == [] and _g16(release, {}) == []
    result = verify_release(release, audience="public")
    gates = {gate.gate: gate for gate in result.gates}
    assert gates["G16"].status == "skipped" and "G16" in result.skipped
    empty = verify_release(release, audience="public", locked_terms={})
    assert {gate.gate: gate for gate in empty.gates}["G16"].status == "skipped"


def test_a_single_string_rendering_is_one_rendering_not_characters(release: Path):
    _append(release, "A short note on the handover.")
    [violation] = _g16(release, {"réception": "handover"})  # type: ignore[dict-item]
    assert violation.message.startswith('"handover"')
