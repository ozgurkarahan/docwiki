import pytest

from docwiki.contracts.markdown import (
    BACKLINKS_END,
    BACKLINKS_START,
    Slugger,
    extract_footnotes,
    extract_headings,
    extract_links,
    heading_anchor,
    markdown_to_text,
    relative_link,
    resolve_href,
    split_sections,
)


@pytest.mark.parametrize(
    ("text", "anchor"),
    [
        ("Page 12", "page-12"),
        ("Key facts", "key-facts"),
        ("Superseded information", "superseded-information"),
        ("Gearbox oil: grade & viscosity", "gearbox-oil-grade--viscosity"),
        ("C++ (v2.0)", "c-v20"),
        ("Already-dashed_and_underscored", "already-dashed_and_underscored"),
        ("  Trimmed  ", "trimmed"),
        ("Rows 12–20", "rows-1220"),
        ("Über Öl", "über-öl"),
        ("Why? Because!", "why-because"),
    ],
)
def test_heading_anchor_matches_github_slugger(text: str, anchor: str) -> None:
    assert heading_anchor(text) == anchor


def test_slugger_deduplicates_like_github() -> None:
    slugger = Slugger()
    assert [slugger.slug(text) for text in ("Notes", "Notes", "Notes-1", "Notes")] == [
        "notes",
        "notes-1",
        "notes-1-1",
        "notes-2",
    ]


def test_extract_headings_uses_rendered_text() -> None:
    markdown = "# Title\n\n## The `oil` [grade](x.md) *now*\n\nSetext\n------\n\n## Title\n"
    headings = extract_headings(markdown)
    assert [(h.level, h.text, h.anchor, h.line) for h in headings] == [
        (1, "Title", "title", 1),
        (2, "The oil grade now", "the-oil-grade-now", 3),
        (2, "Setext", "setext", 5),
        (2, "Title", "title-1", 8),
    ]


def test_extract_links_sees_inline_reference_autolink_image_and_footnotes() -> None:
    markdown = (
        "See [a](../a.md#x) and ![img](img/p.png) and <https://example.org/x>.\n"
        "Ref [b][r].\n\n[r]: other.md\n\n"
        "Fact.[^c1]\n\n"
        "[^c1]: [Manual — p. 3](../evidence/src-0123456789ab/p0003.md) · ✓ quote verified\n"
        "`[not](a link)`\n"
    )
    links = extract_links(markdown)
    hrefs = [(link.href, link.image, link.autolink) for link in links]
    assert ("../a.md#x", False, False) in hrefs
    assert ("img/p.png", True, False) in hrefs
    assert ("https://example.org/x", False, True) in hrefs
    assert ("other.md", False, False) in hrefs
    assert ("../evidence/src-0123456789ab/p0003.md", False, False) in hrefs
    assert all(link.href != "a link" for link in links)
    footnote = next(link for link in links if "evidence" in link.href)
    assert footnote.line == 8


def test_extract_footnotes_ignores_code() -> None:
    markdown = "A[^c1] b[^c2] a again[^c1]\n\n```\n[^c9]\n```\n\n[^c1]: one\n[^c2]: two\n"
    refs, defs = extract_footnotes(markdown)
    assert [label for label, _ in refs] == ["c1", "c2", "c1"]
    assert [(d.label, d.content, d.line) for d in defs] == [("c1", "one", 7), ("c2", "two", 8)]


@pytest.mark.parametrize(
    ("source", "target", "link"),
    [
        ("sources/a.md", "sources/b.md", "b.md"),
        ("sources/a.md", "entities/asset/wtg-07.md", "../entities/asset/wtg-07.md"),
        (
            "sources/a.md",
            "evidence/src-0123456789ab/p0003.md",
            "../evidence/src-0123456789ab/p0003.md",
        ),
        (
            "entities/asset/wtg-07.md",
            "evidence/src-0123456789ab/p0003.md",
            "../../evidence/src-0123456789ab/p0003.md",
        ),
        ("index.md", "topics/gearbox-oil.md#overview", "topics/gearbox-oil.md#overview"),
        ("evidence/src-0123456789ab/p0003.md", "sources/a.md", "../../sources/a.md"),
        ("sources/a.md", "sources/a.md", "a.md"),
    ],
)
def test_relative_link(source: str, target: str, link: str) -> None:
    assert relative_link(source, target) == link
    resolved = resolve_href(source, link)
    assert resolved.path == target.split("#")[0]


@pytest.mark.parametrize(
    "bad", [("/x.md", "a.md"), ("a.md", "../b.md"), ("a\\b.md", "c.md"), ("a.md", "")]
)
def test_relative_link_rejects_bad_paths(bad: tuple[str, str]) -> None:
    with pytest.raises(ValueError):
        relative_link(*bad)


def test_resolve_href_cases() -> None:
    assert resolve_href("sources/a.md", "#key-facts").path == "sources/a.md"
    assert resolve_href("sources/a.md", "#key-facts").anchor == "key-facts"
    assert resolve_href("sources/a.md", "../../x.md").error == "link escapes the content root"
    assert resolve_href("sources/a.md", "/x.md").error == "absolute path link"
    external = resolve_href("sources/a.md", "HTTPS://example.org")
    assert external.external and external.scheme == "https"
    assert resolve_href("sources/a.md", "//example.org/x").external
    assert resolve_href("sources/a.md", "b%20c.md").path == "sources/b c.md"
    assert resolve_href("sources/a.md", "../evidence/x/original.pdf#page=3").anchor == "page=3"
    assert resolve_href("sources/a.md", "b.md?x=1").error


def test_split_sections_and_plain_text() -> None:
    body = (
        "# Title\n\n> Banner with [link](b.md)\n\nSummary text.[^c1]\n\n"
        "## Key facts\n\n- Fact one.[^c1]\n\n"
        f"{BACKLINKS_START}\n## Referenced by\n\n- [X](x.md)\n{BACKLINKS_END}\n\n## Sources\n\n"
        "[^c1]: [T — p. 1](../evidence/src-0123456789ab/p0001.md) · ✓ quote verified\n"
    )
    sections = split_sections(body)
    assert [(s.level, s.heading, s.anchor) for s in sections] == [
        (1, "Title", "title"),
        (2, "Key facts", "key-facts"),
        (2, "Referenced by", "referenced-by"),
        (2, "Sources", "sources"),
    ]
    text = markdown_to_text(body)
    assert "Banner with link" in text and "Summary text." in text and "Fact one." in text
    assert "[^c1]" not in text and "Referenced by" not in text and "evidence" not in text
    assert markdown_to_text("a <b>bold</b> <!-- c -->") == "a bold"
