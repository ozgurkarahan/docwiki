"""History is judged against every version of the word lists it contains (closed-world rule)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from leakguard_core import gitsource
from leakguard_core.cli import main
from leakguard_core.config import load_termset, merge_termsets, parse_termset
from leakguard_core.model import ConfigError
from leakguard_core.words import keys
from leakguard_fixtures import commit_all, make_docx, write

ALLOWLIST = "samples/fiction/allowlist.txt"
COMMON_WORDS = "tools/leakguard/common_words.txt"
TECH_ALLOWLIST = "tools/leakguard/tech_allowlist.txt"
NOTE = "samples/corpus/note.md"
OTHER_NOTE = "samples/corpus/other.md"


def scan_json(
    capsys: pytest.CaptureFixture[str], repo: Path, *args: str
) -> tuple[int, dict[str, Any]]:
    code = main(["scan", "--root", str(repo), "--format", "json", *args])
    return code, json.loads(capsys.readouterr().out)


def closed_world(report: dict[str, Any]) -> list[tuple[str, str, str]]:
    """``(source, path, term)`` of every closed-world finding."""
    return sorted(
        (finding["source"], finding["path"], finding["match"])
        for finding in report["findings"]
        if finding["rule"] == "closed-world"
    )


def history_arguments(repo: Path, how: str, tmp_path: Path) -> list[str]:
    """``--history`` (every ref) or ``--commits-from`` (what the CI workflow does)."""
    if how == "history":
        return ["--history"]
    commits = tmp_path / "commits.txt"
    commits.write_text("\n".join(gitsource.reachable_commits(repo, None)) + "\n", encoding="utf-8")
    return ["--commits-from", str(commits)]


# A name of a retired world, the list that accepted it in its time, and that list's content.
RETIRED = [
    pytest.param(ALLOWLIST, "Zorblax\n", "Zorblax", id="allowlist"),
    pytest.param(COMMON_WORDS, "# words\nzorbword\n", "Zorbword", id="common-words"),
    pytest.param(TECH_ALLOWLIST, "Zorbtech\n", "Zorbtech", id="tech-allowlist"),
]


@pytest.mark.parametrize("how", ["history", "commits-from"])
@pytest.mark.parametrize(("word_list", "content", "name"), RETIRED)
def test_history_accepts_what_any_version_of_the_word_lists_allowed(
    repo: Path,
    denylist: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    word_list: str,
    content: str,
    name: str,
    how: str,
) -> None:
    write(repo, word_list, content)
    write(repo, NOTE, f"The delivery was confirmed by {name}.\n")
    write(repo, OTHER_NOTE, "The delivery was confirmed by Quentin Marsh.\n")
    commit_all(repo, "samples: the first world")
    write(repo, word_list, "# the first world is retired\n")
    (repo / NOTE).unlink()
    (repo / OTHER_NOTE).unlink()
    commit_all(repo, "samples: the second world")

    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--strict")
    assert (code, report["findings"]) == (0, [])
    arguments = history_arguments(repo, how, tmp_path)
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--strict", *arguments)
    # the retired name is accepted; a name that no version of any list allowed is still reported
    assert closed_world(report) == [("history", OTHER_NOTE, "Quentin Marsh")]
    assert code == 1


def test_history_accepts_the_names_of_binary_files_that_are_gone(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, ALLOWLIST, "Zorblax\n")
    write(repo, "samples/corpus/ok.docx", make_docx(["The windows are delivered by Zorblax."]))
    commit_all(repo, "samples: the first world")
    write(repo, ALLOWLIST, "Lamna Bâtiment\n")
    (repo / "samples/corpus/ok.docx").unlink()
    commit_all(repo, "samples: the second world")

    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--history", "--strict")
    assert (code, report["findings"]) == (0, [])
    assert report["stats"]["history_blobs"] == 1
    assert report["stats"]["history_word_list_versions"] == 2


def test_the_working_tree_is_judged_against_the_current_lists(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, ALLOWLIST, "Zorblax\n")
    write(repo, NOTE, "The delivery was confirmed by Zorblax.\n")
    commit_all(repo, "samples: the first world")
    write(repo, ALLOWLIST, "Lamna Bâtiment\n")
    commit_all(repo, "samples: the second world, a file still uses the retired name")

    for arguments in ([], ["--history"]):
        code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--strict", *arguments)
        assert closed_world(report) == [("worktree", NOTE, "Zorblax")]
        assert code == 1


def test_the_site_folders_are_judged_against_the_current_lists(
    repo: Path, denylist: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, ALLOWLIST, "Zorblax\n")
    commit_all(repo, "samples: the first world")
    write(repo, ALLOWLIST, "Lamna Bâtiment\n")
    commit_all(repo, "samples: the second world")
    site = tmp_path / "public"
    site.mkdir()
    (site / "index.html").write_text(
        "<html><body><p>Welcome to the Zorblax Portal</p></body></html>", encoding="utf-8"
    )
    code, report = scan_json(
        capsys, repo, "--denylist", str(denylist), "--history", "--site", str(site)
    )
    assert [(f["source"], f["severity"], f["match"]) for f in report["findings"]] == [
        ("site", "warning", "Zorblax")
    ]
    assert code == 0


def test_a_broken_version_of_a_word_list_is_skipped_with_a_notice(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, ALLOWLIST, "Zorblax\nre:(\n")
    write(repo, NOTE, "The delivery was confirmed by Zorblax.\n")
    commit_all(repo, "samples: a list with a broken pattern")
    write(repo, ALLOWLIST, "Lamna Bâtiment\n")
    (repo / NOTE).unlink()
    commit_all(repo, "samples: the second world")

    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--history", "--strict")
    assert closed_world(report) == [("history", NOTE, "Zorblax")]
    assert code == 1
    notices = [notice for notice in report["notices"] if notice["kind"] == "config"]
    assert [notice["file"] for notice in notices] == [ALLOWLIST]
    assert "invalid regular expression" in notices[0]["message"]
    assert report["stats"]["history_word_list_versions"] == 1


def test_no_history_means_no_history_vocabulary(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, ALLOWLIST, "Lamna Bâtiment\n")
    commit_all(repo, "samples")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--strict")
    assert code == 0
    assert "history_word_list_versions" not in report["stats"]


def test_parse_termset_reads_the_same_syntax_as_load_termset(tmp_path: Path) -> None:
    text = "# comment\nZorblax Industries  # trailing comment\nre:ZB-\\d+\n\n"
    path = tmp_path / "list.txt"
    path.write_text(text, encoding="utf-8")
    loaded = load_termset(path, "list", required=True)
    parsed = parse_termset(text, "list", str(path))
    assert parsed.words == loaded.words and parsed.entries == loaded.entries == 2
    assert [r.pattern for r in parsed.regexes] == [r.pattern for r in loaded.regexes] == ["ZB-\\d+"]
    with pytest.raises(ConfigError, match=r"abc1234:list\.txt line 2: invalid regular expression"):
        parse_termset("Zorblax\nre:(\n", "list", "abc1234:list.txt")


def test_merge_termsets_is_a_union() -> None:
    one = parse_termset("Zorblax\nre:ZB-\\d+\n", "one", "one")
    two = parse_termset("Quillon\nre:ZB-\\d+\nre:QU-\\d+\n", "two", "two")
    merged = merge_termsets("merged", [one, two])
    assert merged.words == one.words | two.words
    assert [regex.pattern for regex in merged.regexes] == ["ZB-\\d+", "QU-\\d+"]
    assert merged.knows(keys("Quillon")) and merged.regex_match("qu-12")
    assert merged.entries == one.entries + two.entries
    assert one.words < merged.words and "quillon" not in one.words  # the inputs are untouched


def test_file_versions_lists_every_distinct_version_of_a_path(repo: Path) -> None:
    write(repo, "other.txt", "x\n")
    commit_all(repo, "the list does not exist yet")
    write(repo, ALLOWLIST, "one\n")
    second = commit_all(repo, "first version")
    write(repo, "other.txt", "y\n")
    commit_all(repo, "unrelated change")
    write(repo, ALLOWLIST, "two\n")
    commit_all(repo, "second version")
    write(repo, ALLOWLIST, "one\n")
    commit_all(repo, "back to the first version")

    every = gitsource.reachable_commits(repo, None)
    assert len(every) == 5
    versions = gitsource.file_versions(repo, every, [ALLOWLIST, "missing.txt"])
    assert sorted(versions[ALLOWLIST]) == [b"one\n", b"two\n"]
    assert versions["missing.txt"] == []
    # versions are read from the listed commits only; HEAD and the ancestors count as reachable
    assert gitsource.file_versions(repo, [second], [ALLOWLIST]) == {ALLOWLIST: [b"one\n"]}
    assert set(gitsource.reachable_commits(repo, [second])) == set(every)
    assert gitsource.file_versions(repo, [], [ALLOWLIST]) == {ALLOWLIST: []}
