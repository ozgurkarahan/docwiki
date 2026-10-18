from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from leakguard_core.cli import main
from leakguard_core.config import deny_rule_id
from leakguard_fixtures import (
    FAKE_AUTHOR_EMAIL,
    FAKE_EMAIL,
    FAKE_GITHUB_TOKEN,
    FAKE_GUID,
    FAKE_INTERNAL_URL,
    FAKE_MIRROR_URL,
    FAKE_TERM,
    FAKE_WIN_HOME,
    PUBLIC_REGISTRY_URL,
    commit_all,
    git,
    make_docx,
    make_image,
    make_pdf,
    make_pptx,
    make_sqlite,
    write,
)

TOOL = Path(__file__).resolve().parents[2] / "tools" / "leakguard" / "leakguard.py"
DENY_PATTERN = "zorblax[- ]?corp"


def scan(capsys: pytest.CaptureFixture[str], *args: str) -> tuple[int, str]:
    code = main(["scan", *args])
    captured = capsys.readouterr()
    return code, captured.out + captured.err


def scan_json(
    capsys: pytest.CaptureFixture[str], repo: Path, *args: str
) -> tuple[int, dict[str, Any]]:
    code = main(["scan", "--root", str(repo), "--format", "json", *args])
    return code, json.loads(capsys.readouterr().out)


def rules(report: dict[str, Any]) -> list[str]:
    return sorted(finding["rule"] for finding in report["findings"])


def leaky_document() -> str:
    return "\n".join(
        [
            "tenant " + FAKE_GUID,
            "contact " + FAKE_EMAIL,
            "notes in " + FAKE_WIN_HOME,
            "token " + FAKE_GITHUB_TOKEN,
            "wiki " + FAKE_INTERNAL_URL,
            "pip " + FAKE_MIRROR_URL,
            "The " + FAKE_TERM + " plant",
        ]
    )


def test_clean_repository_and_denylist_exit_codes(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "README.md", "# Demo\n\nNothing to see here.\n")
    commit_all(repo, "docs: readme")

    code, report = scan_json(capsys, repo)
    assert code == 0
    assert [(f["rule"], f["severity"]) for f in report["findings"]] == [
        ("denylist-missing", "warning")
    ]
    code, report = scan_json(capsys, repo, "--strict")
    assert code == 1
    assert report["findings"][0]["severity"] == "error"
    code, report = scan_json(capsys, repo, "--strict", "--denylist", str(denylist))
    assert (code, report["findings"]) == (0, [])


def test_empty_denylist_counts_as_missing(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "README.md", "hello\n")
    commit_all(repo, "init")
    empty = tmp_path / "empty-denylist.txt"
    empty.write_text("# only comments\n", encoding="utf-8")
    code, report = scan_json(capsys, repo, "--strict", "--denylist", str(empty))
    assert code == 1 and rules(report) == ["denylist-missing"]


def test_identifier_findings_fail_the_scan(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "docs/notes.md", leaky_document() + "\n")
    commit_all(repo, "docs: notes")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    assert code == 1
    found = rules(report)
    deny = deny_rule_id(DENY_PATTERN)
    assert found.count(deny) == 3  # the term itself, the e-mail domain and the internal URL
    assert set(found) - {deny} == {
        "email",
        "guid",
        "home-path",
        "internal-host",
        "package-mirror",
        "secret-github-token",
    }
    guid = next(f for f in report["findings"] if f["rule"] == "guid")
    assert guid["file"] == "docs/notes.md" and guid["line"] == 1
    assert guid["severity"] == "error" and guid["id"].startswith("LG-")
    assert guid["match"] == FAKE_GUID
    token = next(f for f in report["findings"] if f["rule"] == "secret-github-token")
    assert FAKE_GITHUB_TOKEN not in json.dumps(report)  # secrets are always masked
    assert token["match"].startswith(FAKE_GITHUB_TOKEN[:4])


def test_redaction_never_prints_matches_or_patterns(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    write(repo, "docs/notes.md", leaky_document() + "\n")
    commit_all(repo, "docs: notes")
    monkeypatch.setenv("CI", "true")

    code, output = scan(capsys, "--root", str(repo), "--denylist", str(denylist))
    assert code == 1
    assert f"rule={deny_rule_id(DENY_PATTERN)}  docs/notes.md:7\n" in output
    lowered = output.lower()
    for secret in (FAKE_TERM, FAKE_EMAIL, FAKE_GUID, "zorblax", DENY_PATTERN, FAKE_INTERNAL_URL):
        assert secret.lower() not in lowered

    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    deny = [f for f in report["findings"] if f["rule"].startswith("deny:")]
    assert deny and all(set(f) == {"rule", "severity", "file", "line", "source"} for f in deny)
    assert "zorblax" not in json.dumps(report).lower()

    code, output = scan(capsys, "--root", str(repo), "--denylist", str(denylist), "--no-redact")
    assert FAKE_TERM in output


def test_history_finds_removed_secrets_and_author_emails(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "config.md", "token " + FAKE_GITHUB_TOKEN + "\n")
    first = commit_all(repo, "add config", author_email=FAKE_AUTHOR_EMAIL)
    write(repo, "config.md", "token from the environment\n")
    commit_all(repo, "remove token")

    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    assert code == 0 and report["findings"] == []

    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--history")
    assert code == 1
    assert report["stats"]["history_commits"] == 2
    token = next(f for f in report["findings"] if f["rule"] == "secret-github-token")
    assert token["source"] == "history"
    assert token["file"] == f"config.md@{first[:12]}" and token["line"] == 1
    emails = [f for f in report["findings"] if f["rule"] == "email"]
    assert len(emails) == 1 and emails[0]["match"] == FAKE_AUTHOR_EMAIL
    assert emails[0]["file"].startswith("git-history@")
    deny = [f for f in report["findings"] if f["rule"].startswith("deny:")]
    assert deny and deny[0]["file"].startswith("git-history@")


def test_history_scans_old_binary_versions(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "samples/corpus/sop.docx", make_docx(["Oil change"], author="Jane Quillon"))
    commit_all(repo, "add sop")
    write(repo, "samples/corpus/sop.docx", make_docx(["Oil change"]))
    commit_all(repo, "fix metadata")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    assert code == 0, report["findings"]
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--history")
    assert code == 1
    found = {(f["rule"], f["source"]) for f in report["findings"]}
    assert ("metadata-office-author", "history") in found


def test_tool_session_trailers_are_not_reported(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "README.md", "hello\n")
    trailer = "Copilot-Session: " + FAKE_GUID
    commit_all(repo, "docs: readme\n\n" + trailer)
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--history")
    assert code == 0, report["findings"]
    write(repo, "README.md", "hello again\n")
    commit_all(repo, "docs: tenant " + FAKE_GUID + "\n\n" + trailer)
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--history")
    assert code == 1
    guid = next(f for f in report["findings"] if f["rule"] == "guid")
    assert guid["location"] == "commit message line 1"


def test_commits_from_limits_the_history_scan(
    repo: Path, denylist: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "a.md", "token " + FAKE_GITHUB_TOKEN + "\n")
    leaky = commit_all(repo, "leak")
    write(repo, "a.md", "clean\n")
    clean = commit_all(repo, "clean")
    listing = tmp_path / "commits.txt"
    listing.write_text(clean + "\n", encoding="utf-8")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--commits-from",
                             str(listing))
    assert code == 0 and report["stats"]["history_commits"] == 1
    listing.write_text(leaky + "\n", encoding="utf-8")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--commits-from",
                             str(listing))
    assert code == 1 and "secret-github-token" in rules(report)


def test_include_untracked(repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(repo, "README.md", "hello\n")
    commit_all(repo, "init")
    write(repo, "docs/draft.md", "mail " + FAKE_EMAIL + "\n")
    code, _ = scan_json(capsys, repo, "--denylist", str(denylist))
    assert code == 0
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--include-untracked")
    assert code == 1
    email = next(f for f in report["findings"] if f["rule"] == "email")
    assert email["source"] == "untracked" and email["file"] == "docs/draft.md"


def test_site_folder_names_are_warnings(
    repo: Path, denylist: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "README.md", "hello\n")
    commit_all(repo, "init")
    site = tmp_path / "public"
    site.mkdir()
    (site / "index.html").write_text(
        "<html><body><p>Welcome to the Zorblax Portal</p>"
        "<script>var ZorbWidget = 1;</script></body></html>",
        encoding="utf-8",
    )
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--site", str(site))
    assert code == 0
    findings = [(f["rule"], f["severity"], f["match"]) for f in report["findings"]]
    assert findings == [("closed-world", "warning", "Zorblax")]
    assert report["findings"][0]["file"].endswith("public/index.html")
    code, _ = scan_json(capsys, repo, "--denylist", str(denylist), "--site", str(site), "--strict")
    assert code == 1


def test_sample_content_closed_world_and_metadata(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "samples/fiction/allowlist.txt", "Contoso Renewables\nMira Jensen\n")
    write(
        repo,
        "samples/corpus/note.md",
        "# Gearbox Oil Change\n\nMira Jensen asked Zorblax Lubricants about the oil grade.\n",
    )
    write(repo, "samples/corpus/ok.docx", make_docx(["The oil is changed by Contoso Renewables."]))
    write(repo, "samples/corpus/sop.docx", make_docx(["Oil change"], author="Jane Quillon"))
    deck = make_pptx("Site Rules", "Contoso Renewables", last_modified_by=None)
    write(repo, "samples/corpus/deck.pptx", deck)
    write(repo, "samples/corpus/photo.jpg", make_image("JPEG", exif=True))
    pdf_info = {"Author": "jquillon", "Producer": "fpdf2"}
    write(repo, "samples/corpus/report.pdf", make_pdf(["Contoso Renewables lab report"], pdf_info))
    write(repo, "samples/generators/gen.py", 'TITLE = "Prepared for Quentin Marsh"\n')
    write(repo, "evals/golden/dev.jsonl", '{"question": "Who supplies Zorblax oil?"}\n')
    commit_all(repo, "samples")

    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    assert code == 1
    found = {(f["rule"], f["severity"], f["file"], f.get("match")) for f in report["findings"]}
    assert ("closed-world", "error", "samples/corpus/note.md", "Zorblax") in found
    assert ("closed-world", "error", "samples/generators/gen.py", "Quentin Marsh") in found
    assert ("closed-world", "warning", "evals/golden/dev.jsonl", "Zorblax") in found
    assert ("metadata-office-author", "error", "samples/corpus/sop.docx", "Jane Quillon") in found
    assert ("metadata-exif", "error", "samples/corpus/photo.jpg", None) in found
    assert ("metadata-pdf", "error", "samples/corpus/report.pdf", "jquillon") in found
    deck = {f["rule"] for f in report["findings"] if f["file"] == "samples/corpus/deck.pptx"}
    assert "metadata-office-author" in deck
    assert not [f for f in report["findings"] if f["file"] == "samples/corpus/ok.docx"]
    assert not [f for f in report["findings"] if f["file"] == "samples/fiction/allowlist.txt"]


def test_generated_release_identifiers_are_not_names(
    repo: Path, denylist: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    release_id = "20260215T090000Z-decd4b59"
    base = f"samples/fixtures/mock-release/releases/{release_id}"
    write(repo, "samples/fixtures/mock-release/releases/current.json",
          json.dumps({"release_id": release_id, "created_at": "2026-02-15T09:00:00Z"}))
    write(repo, f"{base}/catalog.json", json.dumps(
        {"pages": [{"id": "src-43c97f7dfcde", "summary": "Append-only change log of this wiki."},
                   {"summary": "Curated multi-source syntheses.",
                    "synonyms": ["Standardarbeitsanweisung"]}],
         "columns": [{"name": "asset", "type": "VARCHAR"}, {"name": "row", "type": "BIGINT"}]},
        indent=2))
    write(repo, f"{base}/wiki/sources/sop-gbx-010-rev-a.md", "\n".join([
        "---", "summary: Superseded revision A of the procedure SOP-GBX-010.",
        f"release: {release_id}", "locator: p0003, b0042", "---", "", "### Draining", "",
        "Drain the oil while it is still warm.", "Turbines are identified as WTG-NN.", "",
        "| Asset | Document | OEM |", "|---|---|---|", "| WTG-07 | SOP-GBX-010 | Litware |", "",
    ]))
    write(repo, "samples/fixtures/mock-release/build_fixture.py",
          '"""Usage: build_fixture.py --out DIR"""\nRELEASE = "' + release_id + '"\n')
    database = tmp_path / "search.db"
    make_sqlite(database, [("Index", "Sources: 3\nFiled research answers: 1")])
    write(repo, f"{base}/search.db", database.read_bytes())
    commit_all(repo, "mock release")

    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    names = [(f["match"], f["file"].rsplit("/", 1)[-1]) for f in report["findings"]]
    assert names == [("Litware", "sop-gbx-010-rev-a.md")]
    assert code == 1

    allowlist = tmp_path / "allowlist.txt"
    allowlist.write_text("Litware\nre:WTG-\\d{2}\nre:SOP-[A-Z]{3}-\\d{3}\n", encoding="utf-8")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--strict",
                             "--allowlist", str(allowlist))
    assert (code, report["findings"]) == (0, [])


def test_unicode_escaped_text_is_checked_decoded(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pattern = "z\u00f6rblax"
    deny = tmp_path / "deny-umlaut.txt"
    deny.write_text(pattern + "\n", encoding="utf-8")
    write(repo, "samples/corpus/glossary.json",
          '{"term": "Generatorb\\u00fcrsten", "vendor": "Z\\u00f6rblax"}\n')
    commit_all(repo, "glossary")
    code, report = scan_json(capsys, repo, "--denylist", str(deny))
    assert code == 1
    found = sorted((f["rule"], f.get("match")) for f in report["findings"])
    expected = [(deny_rule_id(pattern), "Z\u00f6rblax"), ("closed-world", "Z\u00f6rblax")]
    assert found == sorted(expected)


def test_policy_files_and_lock_file_mirrors(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mirror = "https:" + "//mirror.zorblax-corp.com/simple"
    write(repo, ".gitignore", "*.log\n")
    write(repo, "uv.lock", f'source = {{ registry = "{mirror}" }}\n')
    write(repo, ".env", "MODE=dev\n")
    write(repo, "requirements.txt", f"--index-url {mirror}\nrequests\n")
    write(repo, "constraints.txt", f"# from {PUBLIC_REGISTRY_URL}\n")
    write(repo, "debug.log", "noise\n")
    git(repo, "add", "-A")
    git(repo, "add", "-f", "debug.log")
    git(repo, "commit", "-q", "--no-verify", "-m", "policy")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    assert code == 1
    policy = sorted(f["file"] for f in report["findings"] if f["rule"] == "policy-file")
    assert policy == [".env", "debug.log", "uv.lock"]
    mirrors = sorted(f["file"] for f in report["findings"] if f["rule"] == "lockfile-mirror")
    assert mirrors == ["requirements.txt", "uv.lock"]


def test_ignore_file_suppresses_reviewed_findings(
    repo: Path, denylist: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "docs/a.md", "id " + FAKE_GUID + "\nThe " + FAKE_TERM + " plant\n")
    commit_all(repo, "docs")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist))
    ids = {f["rule"]: f["id"] for f in report["findings"]}
    ignore = tmp_path / "ignore.txt"
    deny_id = ids[deny_rule_id(DENY_PATTERN)]
    ignore.write_text(f"{ids['guid']}  # reviewed fixture\n{deny_id}  # attempt\n", "utf-8")
    code, report = scan_json(capsys, repo, "--denylist", str(denylist), "--ignore-file",
                             str(ignore))
    assert rules(report) == [deny_rule_id(DENY_PATTERN)]  # deny-list findings stay
    assert report["summary"]["suppressed"] == 1
    ignore.write_text(f"{ids['guid']}\n", encoding="utf-8")
    code, output = scan(capsys, "--root", str(repo), "--denylist", str(denylist),
                        "--ignore-file", str(ignore))
    assert code == 2 and "reason" in output


def test_configuration_errors_exit_2(
    repo: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    plain = tmp_path / "plain"
    plain.mkdir()
    assert scan(capsys, "--root", str(plain))[0] == 2

    inside = write(repo, "denylist.txt", "zorblax\n")
    code, output = scan(capsys, "--root", str(repo), "--denylist", str(inside))
    assert code == 2 and "outside the repository" in output

    broken = tmp_path / "broken-denylist.txt"
    broken.write_text("# private\nzorb([a-\n", encoding="utf-8")
    code, output = scan(capsys, "--root", str(repo), "--denylist", str(broken))
    assert code == 2 and "line 2" in output and "zorb" not in output

    code, _ = scan(capsys, "--root", str(repo), "--allowlist", str(tmp_path / "missing.txt"))
    assert code == 2
    code, _ = scan(capsys, "--root", str(repo), "--denylist", str(tmp_path / "missing.txt"))
    assert code == 2
    monkeypatch.setenv("DOCWIKI_DENYLIST", str(tmp_path / "missing.txt"))
    assert scan(capsys, "--root", str(repo))[0] == 2


def test_denylist_from_environment_and_ids_command(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    write(repo, "a.md", "The " + FAKE_TERM + " plant\n")
    commit_all(repo, "a")
    monkeypatch.setenv("DOCWIKI_DENYLIST", str(denylist))
    code, report = scan_json(capsys, repo)
    assert code == 1 and rules(report) == [deny_rule_id(DENY_PATTERN)]
    assert main(["denylist-ids"]) == 0
    output = capsys.readouterr().out
    assert output == f"{deny_rule_id(DENY_PATTERN)}  line 2\n"


def test_script_entry_point(repo: Path, denylist: Path) -> None:
    write(repo, "README.md", "hello\n")
    commit_all(repo, "init")
    command = [sys.executable, str(TOOL), "scan", "--root", str(repo), "--strict",
               "--denylist", str(denylist)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "-> PASS (exit 0)" in completed.stdout
