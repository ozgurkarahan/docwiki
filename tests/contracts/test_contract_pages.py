from datetime import date

import pytest
from pydantic import ValidationError

from docwiki.contracts.frontmatter import (
    FrontmatterError,
    read_frontmatter,
    render_frontmatter,
    split_frontmatter,
    write_frontmatter,
)
from docwiki.contracts.pages import (
    EntityFrontmatter,
    EvidencePage,
    Page,
    SkillFile,
    SourceFrontmatter,
    parse_frontmatter,
)

RELEASE = "20260131T080509Z-01234567"
SOURCE_ID = "src-0123456789ab"


def source_fm(**overrides: object) -> dict[str, object]:
    data: dict[str, object] = {
        "id": SOURCE_ID,
        "type": "source",
        "title": "Gearbox manual",
        "summary": "Litware gearbox maintenance manual excerpt.",
        "lang": "en",
        "sensitivity": "public",
        "updated": date(2026, 1, 31),
        "tags": ["gearbox", "oil"],
        "docwiki": {"schema": 1, "release": RELEASE},
        "source_id": SOURCE_ID,
        "source_path": "oem/gearbox-manual.pdf",
        "source_hash": "sha256:" + "a" * 64,
        "media_type": "application/pdf",
        "doc_type": "oem-manual",
        "category": "oem-documentation",
        "status": "current",
        "original_lang": "en",
        "pages": 12,
        "entities": ["asset:wtg-07"],
        "topics": ["topic:gearbox-oil"],
        "authority": 8,
        "extraction": {
            "adapter": "local",
            "version": "1.0.0",
            "provenance_mix": {"native-text": 40},
        },
    }
    data.update(overrides)
    return data


def test_frontmatter_round_trip_keeps_order_types_and_lf() -> None:
    data = {
        "id": "x",
        "zeta": "1.0",
        "alpha": date(2026, 1, 2),
        "flag": True,
        "none": None,
        "list": [],
        "uni": "Ölwechsel",
    }
    text = write_frontmatter(data, "\n\n# Body\r\nline\n\n\n")
    assert text.startswith("---\nid: x\nzeta: '1.0'\nalpha: 2026-01-02\n")
    assert "uni: Ölwechsel" in text and "\r" not in text
    assert text.endswith("---\n\n# Body\nline\n")
    parsed, body = read_frontmatter(text)
    assert parsed == data and list(parsed) == list(data)
    assert body == "# Body\nline\n"


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("---\nid: x\n", "unterminated"),
        ("---\nid: x\nid: y\n---\n", "duplicate key"),
        ("---\n- a\n- b\n---\n", "expected a mapping"),
        ("---\r\nid: x\r\n---\r\n", "CR characters"),
        ("\ufeff---\nid: x\n---\n", "byte order mark"),
        ("---\nid: [unclosed\n---\n", "invalid YAML"),
        ("# no frontmatter\n", "missing frontmatter"),
    ],
)
def test_malformed_frontmatter(text: str, message: str) -> None:
    with pytest.raises(FrontmatterError, match=message):
        read_frontmatter(text)


def test_split_without_block_returns_text() -> None:
    assert split_frontmatter("# Title\n") == (None, "# Title\n")
    assert render_frontmatter({}) == "---\n{}\n---\n"


def test_page_render_parse_round_trip() -> None:
    page = Page(
        path="sources/gearbox-manual.md",
        frontmatter=parse_frontmatter(source_fm()),
        body="# Gearbox manual\n",
    )
    text = page.render()
    assert text.index("id:") < text.index("type:") < text.index("source_id:")
    assert Page.parse(text, page.path) == page


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"tags": ["oil", "gearbox"]}, "sorted"),
        ({"tags": ["Oil"]}, "pattern"),
        ({"status": "superseded"}, "superseded_by"),
        ({"superseded_by": ["src-aaaaaaaaaaaa"]}, "current sources"),
        ({"id": "src-ffffffffffff"}, "equal source_id"),
        ({"authority": 11}, "less than or equal"),
        ({"pages": "12"}, "valid integer"),
        ({"entities": ["wtg-07"]}, "invalid entity id"),
        ({"updated": "2026-1-31"}, "YYYY-MM-DD"),
        ({"summary": "two\nlines"}, "single line"),
        ({"unknown": 1}, "Extra inputs"),
        ({"lang": "fr"}, "'en'"),
        ({"docwiki": {"schema": 1, "release": "latest"}}, "pattern"),
        ({"source_path": "/abs/x.pdf"}, "relative POSIX"),
    ],
)
def test_source_frontmatter_rejects_invalid_values(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(ValidationError, match=message):
        parse_frontmatter(source_fm(**overrides))


def test_frontmatter_accepts_iso_date_strings_from_json() -> None:
    parsed = parse_frontmatter(source_fm(updated="2026-01-31"))
    assert isinstance(parsed, SourceFrontmatter) and parsed.updated == date(2026, 1, 31)


def test_discriminated_union_dispatches_and_checks_ids() -> None:
    common = {
        "title": "WTG-07",
        "summary": "Turbine 7.",
        "sensitivity": "internal",
        "updated": date(2026, 1, 31),
        "docwiki": {"schema": 1, "release": RELEASE},
    }
    entity = parse_frontmatter(
        {**common, "id": "asset:wtg-07", "type": "entity", "entity_type": "asset", "key": "wtg-07"}
    )
    assert isinstance(entity, EntityFrontmatter)
    with pytest.raises(ValidationError, match="entity_type"):
        parse_frontmatter(
            {
                **common,
                "id": "asset:wtg-08",
                "type": "entity",
                "entity_type": "asset",
                "key": "wtg-07",
            }
        )
    with pytest.raises(ValidationError):
        parse_frontmatter({**common, "id": "x", "type": "wiki"})
    assert (
        parse_frontmatter({**common, "id": "index:entities/asset", "type": "index"}).type == "index"
    )
    assert (
        parse_frontmatter(
            {**common, "id": "meta:runs/run-20260131-080509-0a1b2c3d", "type": "meta"}
        ).type
        == "meta"
    )
    with pytest.raises(ValidationError):
        parse_frontmatter({**common, "id": "index:everything", "type": "index"})
    with pytest.raises(ValidationError):
        parse_frontmatter({**common, "id": "glossary-2", "type": "glossary"})
    topic = {
        **common,
        "id": "topic:gearbox-oil",
        "type": "topic",
        "topic_slug": "gearbox-oil",
        "confidence": "high",
    }
    assert parse_frontmatter(topic).type == "topic"
    query = {
        **common,
        "id": "query:2026-01-31-oil-grade",
        "type": "query",
        "question": "Which oil grade?",
        "asked_by": "researcher",
        "approved_by": "maintenance lead",
        "sources": ["src-0123456789ab"],
    }
    assert parse_frontmatter(query).type == "query"


def test_evidence_page_checks_id_against_locator() -> None:
    text = (
        "---\nid: evidence:src-0123456789ab:p0003\ntype: evidence\ntitle: Gearbox manual — p. 3\n"
        "source_id: src-0123456789ab\nlocator:\n  kind: pdf-page\n  page: 3\n"
        "provenance: native-text\n"
        "sensitivity: public\n---\n\n# p. 3\n"
    )
    page = EvidencePage.parse(text, "evidence/src-0123456789ab/p0003.md")
    assert page.frontmatter.type == "evidence"
    with pytest.raises(ValidationError, match="evidence id"):
        EvidencePage.parse(text.replace("page: 3", "page: 4"), "evidence/src-0123456789ab/p0003.md")


def test_skill_file_limits() -> None:
    text = (
        "---\nname: wiki-navigator\ndescription: Find information in the wiki.\n---\n\n# Navigate\n"
    )
    assert SkillFile.parse(text, "wiki-navigator").frontmatter.name == "wiki-navigator"
    with pytest.raises(ValueError, match="must match its folder"):
        SkillFile.parse(text, "cite-sources")
    with pytest.raises(ValueError, match="5000 words"):
        SkillFile.parse(text + "word " * 5001, "wiki-navigator")
    with pytest.raises(ValidationError):
        SkillFile.parse(text.replace("Find information in the wiki.", "x" * 1025), "wiki-navigator")
