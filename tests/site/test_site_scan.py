from __future__ import annotations

from pathlib import Path

import pytest
from site_testkit import BUNDLES, page, write_site

from docwiki.site import default_allowed_hosts, scan_site
from docwiki.site.scan import main as scan_main

ALLOWED = {"github.com", "docs.example.org"}


def rules(site: Path, **kwargs: object) -> list[tuple[str, str]]:
    return [(f.rule, f.path) for f in scan_site(site, ALLOWED, **kwargs)]  # type: ignore[arg-type]


def test_clean_quartz_like_site_has_no_findings(tmp_path: Path) -> None:
    site = write_site(
        tmp_path,
        {
            **BUNDLES,
            "index.html": page(
                '<a href="sources/a">A</a> <a href="https://github.com/org/repo">repo</a>'
                '<img src="static/x.png" alt="x"/> <a href="https://docs.example.org/x">self</a>'
                '<script type="application/json">{"a": 1}</script>'
                "<svg xmlns=\"http://www.w3.org/2000/svg\"><path d='M0'/></svg>"
            ),
            "sources/a.html": page('<p style="max-width:0.8em">ok</p>', depth=1),
            "static/x.png": "png",
            "style.css": "a{background:url(data:image/png;base64,AAAA)} b{background:url(x.png)}",
        },
    )
    assert scan_site(site, ALLOWED) == []


def test_stock_quartz_inline_content_index_loader_is_allowed(tmp_path: Path) -> None:
    loader = 'const fetchData = fetch("../static/contentIndex.json").then(data => data.json())'
    site = write_site(tmp_path, {"a/b.html": f"<script>{loader}</script>"})
    assert scan_site(site, ALLOWED) == []


@pytest.mark.parametrize(
    ("html", "rule"),
    [
        ("<script>alert(1)</script>", "script"),
        ('<script src="evil.js"></script>', "script"),
        ('<script src="https://cdn.example.net/x.js"></script>', "script"),
        ('<iframe src="sources/a.html"></iframe>', "iframe"),
        ('<object data="x.swf"></object>', "object-embed"),
        ('<embed src="x.swf"/>', "object-embed"),
        ('<img src="x.png" onerror="alert(1)"/>', "inline-handler"),
        ('<a href="javascript:alert(1)">x</a>', "unsafe-url"),
        ('<a href="&#106;ava&#x73;cript:alert(1)">x</a>', "unsafe-url"),
        ('<a href=" java\tscript:alert(1)">x</a>', "unsafe-url"),
        ('<img src="data:image/svg+xml;base64,AAAA"/>', "unsafe-url"),
        ('<a href="vbscript:x">x</a>', "unsafe-url"),
        ('<img src="https://tracker.example.net/p.gif"/>', "external-host"),
        ('<link rel="preconnect" href="https://fonts.example.net"/>', "external-host"),
        ('<a href="//cdn.example.net/x">x</a>', "external-host"),
        ('<img srcset="a.png 1x, https://cdn.example.net/b.png 2x"/>', "external-host"),
        ('<form action="https://collect.example.net/f"></form>', "external-host"),
        ('<a href="mailto:someone@example.org">mail</a>', "external-scheme"),
        (
            '<meta http-equiv="refresh" content="0; url=https://evil.example.net/"/>',
            "external-host",
        ),
        ('<div style="background:url(https://cdn.example.net/x.png)"></div>', "external-host"),
        ("<style>@import 'https://cdn.example.net/x.css';</style>", "external-host"),
    ],
)
def test_each_rule_is_reported(tmp_path: Path, html: str, rule: str) -> None:
    site = write_site(tmp_path, {**BUNDLES, "index.html": page(html)})
    assert (rule, "index.html") in rules(site)


def test_external_hosts_in_stylesheets_are_reported(tmp_path: Path) -> None:
    site = write_site(
        tmp_path,
        {"static/giscus/dark.css": "@import url('https://assets.example.net/x.css');"},
    )
    assert rules(site) == [("external-host", "static/giscus/dark.css")]


def test_subdomain_allowlist_entries(tmp_path: Path) -> None:
    site = write_site(tmp_path, {"index.html": '<img src="https://img.docs.example.net/a.png">'})
    assert scan_site(site, {".example.net"}) == []
    assert [f.rule for f in scan_site(site, {"example.net"})] == ["external-host"]


def test_canaries_are_found_in_any_text_file(tmp_path: Path) -> None:
    canary = "DOCWIKI-CANARY-0000"
    site = write_site(
        tmp_path,
        {
            **BUNDLES,
            "index.html": page("<p>clean</p>"),
            "sources/a.html": page("<p>line</p>\n<p>DOCWIKI-CANARY&#45;0000</p>", depth=1),
            "static/contentIndex.json": '{"x": "' + canary + '"}',
            "image.png": canary,
        },
    )
    findings = [f for f in scan_site(site, ALLOWED, canaries=[canary]) if f.rule == "canary"]
    assert [(f.path, f.line) for f in findings] == [
        ("sources/a.html", 3),
        ("static/contentIndex.json", 1),
    ]


def test_default_allowed_hosts() -> None:
    assert default_allowed_hosts("https://docs.example.org/", "https://github.com/o/r") == {
        "docs.example.org",
        "github.com",
    }
    assert default_allowed_hosts(None) == {"github.com"}


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    clean = write_site(tmp_path / "clean", {**BUNDLES, "index.html": page("<p>ok</p>")})
    assert scan_main([str(clean), "--links"]) == 0
    assert "scan: 0 finding(s)" in capsys.readouterr().out
    dirty = write_site(tmp_path / "dirty", {**BUNDLES, "index.html": page("<iframe></iframe>")})
    assert scan_main([str(dirty), "--json"]) == 1
    assert '"rule": "iframe"' in capsys.readouterr().out
    canary = write_site(tmp_path / "canary", {"index.html": "<p>XYZ-CANARY</p>"})
    canaries = tmp_path / "canaries.txt"
    canaries.write_text("XYZ-CANARY\n\n", encoding="utf-8")
    assert scan_main([str(canary), "--canary-file", str(canaries)]) == 1


def test_missing_site_folder_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        scan_site(tmp_path / "missing", ALLOWED)
