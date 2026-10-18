from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from leakguard_core.cli import main
from leakguard_core.config import (
    DEFAULT_SITE_VENDOR,
    DomainPolicy,
    deny_rule_id,
    glob_to_regex,
    load_site_vendor,
)
from leakguard_core.model import ConfigError
from leakguard_core.rules import identifier_hits
from leakguard_fixtures import FAKE_TERM, commit_all, write

VENDOR_EMAIL = "lib.author" + "@" + "zorblaxlib.com"
OTHER_EMAIL = "someone.else" + "@" + "zorblaxlib.com"
W3C_SVG = "http:" + "//www.w3.org/2000/svg"


def sha_prefix(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def test_glob_patterns() -> None:
    glob = glob_to_regex("**/postscript.js")
    assert glob.fullmatch("postscript.js") and glob.fullmatch("static/js/postscript.js")
    assert not glob.fullmatch("postscript.js.map") and not glob.fullmatch("mypostscript.js")
    assert glob_to_regex("static/*.js").fullmatch("static/app.js")
    assert not glob_to_regex("static/*.js").fullmatch("static/deep/app.js")


def test_load_site_vendor_entries_and_errors(tmp_path: Path) -> None:
    path = tmp_path / "vendor.txt"
    path.write_text(
        "file **/postscript.js\n"
        f"allow email sha256:{sha_prefix(VENDOR_EMAIL)}  # licence header\n"
        "allow package-mirror re:https?://www\\.w3\\.org/.*  # XML namespaces\n",
        encoding="utf-8",
    )
    policy = load_site_vendor(path)
    assert policy.is_vendor("postscript.js") and not policy.is_vendor("index.html")
    assert policy.allows("email", VENDOR_EMAIL)
    assert not policy.allows("email", OTHER_EMAIL)
    assert policy.allows("package-mirror", W3C_SVG)
    assert not policy.allows("guid", VENDOR_EMAIL)
    for bad in (
        "allow email sha256:abc  # too short\n",
        "allow email re:x\n",
        "allow deny:1234abcd re:.*  # never\n",
        "exempt everything\n",
    ):
        path.write_text(bad, encoding="utf-8")
        with pytest.raises(ConfigError):
            load_site_vendor(path)
    assert load_site_vendor(tmp_path / "missing.txt").globs == []
    with pytest.raises(ConfigError):
        load_site_vendor(tmp_path / "missing.txt", required=True)


def test_repository_site_vendor_list_is_valid() -> None:
    policy = load_site_vendor(DEFAULT_SITE_VENDOR, required=True)
    assert policy.is_vendor("postscript.js") and policy.is_vendor("prescript.js")
    assert not policy.is_vendor("index.html") and not policy.is_vendor("static/contentIndex.json")


def test_mirror_context_is_limited_to_the_text_before_the_url() -> None:
    domains = DomainPolicy()
    minified = 'var registry={};' + "x" * 200 + 'createElementNS("' + W3C_SVG + '")'
    assert identifier_hits(minified, allowed_guids=set(), domains=domains) == []
    config = "registry=" + "https:" + "//npm.zorblax-corp.com/"
    rules = [hit.rule for hit in identifier_hits(config, allowed_guids=set(), domains=domains)]
    assert rules == ["package-mirror"]


def scan_site(
    capsys: pytest.CaptureFixture[str], repo: Path, site: Path, *extra: str
) -> tuple[int, dict[str, Any]]:
    code = main(["scan", "--root", str(repo), "--format", "json", "--site", str(site), *extra])
    return code, json.loads(capsys.readouterr().out)


def test_vendor_bundles_get_narrow_exemptions_only(
    repo: Path, denylist: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    write(repo, "README.md", "hello\n")
    commit_all(repo, "init")
    site = tmp_path / "public"
    site.mkdir()
    licence = f"/** filesize @copyright 2024 Lib Author <{VENDOR_EMAIL}> @license BSD-3-Clause */"
    bundle = "\n".join(
        [
            licence,
            'var registry={};' + "a" * 300 + 'document.createElementNS("' + W3C_SVG + '","svg");',
            f'var maintainer="{OTHER_EMAIL}";',
            f'var vendorName="{FAKE_TERM}";',
        ]
    )
    (site / "postscript.js").write_text(bundle, encoding="utf-8")
    (site / "prescript.js").write_text("console.log('ok');\n", encoding="utf-8")
    (site / "index.html").write_text(
        f"<html><body><p>Questions: {VENDOR_EMAIL}</p></body></html>", encoding="utf-8"
    )
    vendor = tmp_path / "site-vendor.txt"
    vendor.write_text(
        "file **/postscript.js\nfile **/prescript.js\n"
        f"allow email sha256:{sha_prefix(VENDOR_EMAIL)}  # licence header of a bundled library\n",
        encoding="utf-8",
    )

    code, report = scan_site(
        capsys, repo, site, "--denylist", str(denylist), "--site-vendor", str(vendor)
    )
    assert code == 1
    found = sorted(
        (f["rule"], f["file"].rsplit("/", 1)[-1], f.get("match")) for f in report["findings"]
    )
    assert found == sorted(
        [
            (deny_rule_id("zorblax[- ]?corp"), "postscript.js", FAKE_TERM),
            ("email", "postscript.js", OTHER_EMAIL),
            ("email", "index.html", VENDOR_EMAIL),
        ]
    )
    assert report["stats"]["site_vendor_exempted"] == 1

    empty = tmp_path / "empty-vendor.txt"
    empty.write_text("# nothing reviewed\n", encoding="utf-8")
    code, report = scan_site(
        capsys, repo, site, "--denylist", str(denylist), "--site-vendor", str(empty)
    )
    emails = [f["file"].rsplit("/", 1)[-1] for f in report["findings"] if f["rule"] == "email"]
    assert sorted(emails) == ["index.html", "postscript.js", "postscript.js"]
    assert main(["scan", "--root", str(repo), "--site-vendor", str(tmp_path / "nope.txt")]) == 2


def test_json_escapes_are_decoded_once(
    repo: Path, denylist: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    escaped_path = "C:" + "\\\\" + "Users" + "\\\\" + "zorblax" + "\\\\" + "x"
    write(repo, "samples/corpus/index.json", json.dumps(
        {"text": "intro\nFICTIONAL - NOT FOR OPERATIONAL USE\nZorblax"}) + "\n"
        + '{"path": "' + escaped_path + '"}\n')
    commit_all(repo, "index")
    code = main(["scan", "--root", str(repo), "--format", "json", "--denylist", str(denylist)])
    report = json.loads(capsys.readouterr().out)
    assert code == 1
    found = sorted((f["rule"], f["line"], f.get("match")) for f in report["findings"])
    assert [item[:2] for item in found] == [("closed-world", 1), ("home-path", 2)]
    assert found[0][2] == "Zorblax"
