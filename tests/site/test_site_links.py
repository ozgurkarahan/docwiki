from __future__ import annotations

from pathlib import Path

import pytest
from site_testkit import BUNDLES, page, write_site

from docwiki.site import check_links, resolve_site_path
from docwiki.site.links import main as links_main


def test_resolve_site_path_follows_quartz_urls() -> None:
    files = {"index.html", "sources/a.html", "topics/index.html", "img/p.png"}
    assert resolve_site_path(files, "/") == "index.html"
    assert resolve_site_path(files, "/sources/a") == "sources/a.html"
    assert resolve_site_path(files, "/sources/a.html") == "sources/a.html"
    assert resolve_site_path(files, "/topics/") == "topics/index.html"
    assert resolve_site_path(files, "/topics") == "topics/index.html"
    assert resolve_site_path(files, "/img/p.png") == "img/p.png"
    assert resolve_site_path(files, "/sources/b") is None


def test_valid_site_passes(tmp_path: Path) -> None:
    site = write_site(
        tmp_path,
        {
            **BUNDLES,
            "index.html": page(
                '<a href="./sources/a">A</a><a href="topics/">T</a><a href=".">home</a>'
                '<a href="#top" id="top">top</a><a href="https://github.com/o/r">ext</a>'
                '<a href="mailto:x@example.org">mail</a><template><a href="#nope"></a></template>'
            ),
            "sources/a.html": page(
                '<h2 id="key-facts">Key facts</h2>'
                '<sup><a href="#user-content-fn-c1" id="user-content-fnref-c1">1</a></sup>'
                '<li id="user-content-fn-c1"><a href="../evidence/src-0/p0001">ev</a>'
                '<a href="#user-content-fnref-c1">back</a></li>'
                '<a href="../topics/#overview">overview</a><img srcset="../img/p.png 2x"/>',
                depth=1,
            ),
            "topics/index.html": page('<h2 id="overview">Overview</h2>', depth=1),
            "evidence/src-0/p0001.html": page(
                '<a href="./img/p0001.png"><img src="./img/p0001.png"/></a>'
                '<a href="original.pdf#page=3">original</a>'
                '<a href="../../sources/a#key-facts">s</a>',
                depth=2,
            ),
            "evidence/src-0/img/p0001.png": "png",
            "evidence/src-0/original.pdf": "pdf",
            "img/p.png": "png",
            "404.html": '<link href="/index.css" rel="stylesheet"/><a href="/">home</a>',
        },
    )
    report = check_links(site)
    assert report.ok, report.problems
    assert report.pages == 5
    assert report.anchors == 5
    assert report.links >= 20
    assert report.summary().endswith(": ok")


def test_problems_are_reported_with_lines(tmp_path: Path) -> None:
    site = write_site(
        tmp_path,
        {
            **BUNDLES,
            "index.html": page(
                '<a href="sources/missing">x</a>\n<a href="#nowhere">y</a>\n'
                '<a href="sources/a#nope">z</a><img src="img/none.png"/>'
            ),
            "sources/a.html": page("<h2 id='yes'>Yes</h2>", depth=1),
        },
    )
    report = check_links(site)
    assert [(p.line, p.reason, p.url) for p in report.problems] == [
        (2, "missing-target", "sources/missing"),
        (3, "missing-anchor", "#nowhere"),
        (4, "missing-target", "img/none.png"),
        (4, "missing-anchor", "sources/a#nope"),
    ]
    assert not report.ok
    assert check_links(site, check_anchors=False).problems == [
        report.problems[0],
        report.problems[2],
    ]


def test_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    good = write_site(tmp_path / "good", {**BUNDLES, "index.html": page('<a href=".">h</a>')})
    assert links_main([str(good)]) == 0
    assert "internal links" in capsys.readouterr().out
    bad = write_site(tmp_path / "bad", {**BUNDLES, "index.html": page('<a href="x">x</a>')})
    assert links_main([str(bad), "--json"]) == 1
    assert '"reason": "missing-target"' in capsys.readouterr().out
    with pytest.raises(FileNotFoundError):
        check_links(tmp_path / "missing")
