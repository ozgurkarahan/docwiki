from docwiki.contracts.export_schemas import SCHEMA_DIR, render_schemas, stale_files
from docwiki.contracts.strict_schema import check_strict_schema


def test_committed_json_schemas_are_up_to_date() -> None:
    stale = stale_files()
    assert stale == [], (
        f"JSON Schemas are stale: {stale}. Run: uv run python -m docwiki.contracts.export_schemas"
    )


def test_exported_schemas_cover_the_contracts() -> None:
    names = set(render_schemas())
    for expected in (
        "page-frontmatter.schema.json",
        "catalog.schema.json",
        "extracted-doc.schema.json",
        "compiled-source.strict.schema.json",
        "queue-message.schema.json",
        "release-manifest.schema.json",
        "current-pointer.schema.json",
        "proposal.schema.json",
        "tables-index.schema.json",
        "domain-taxonomy.schema.json",
    ):
        assert expected in names
    assert SCHEMA_DIR.is_dir()


def test_strict_schema_file_is_strict() -> None:
    import json

    schema = json.loads(render_schemas()["compiled-source.strict.schema.json"])
    schema.pop("$schema")
    assert schema.pop("title")
    check_strict_schema(schema)
