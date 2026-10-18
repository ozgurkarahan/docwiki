from __future__ import annotations

import json
from enum import StrEnum
from typing import Annotated, Any, Literal

import pytest
from pydantic import BaseModel, Field

from docwiki.llm import StrictSchemaError, to_strict_json_schema


class Severity(StrEnum):
    low = "low"
    high = "high"


class Citation(BaseModel):
    """A pointer to an extracted block."""

    block_id: str = Field(pattern=r"^b\d{4}$", description="Block id")
    quote: str | None = None


class KeyFact(BaseModel):
    text: str = Field(max_length=500)
    citations: list[Citation] = Field(min_length=1)
    numbers: list[str] = []
    severity: Severity = Severity.low
    kind: Literal["fact"] = "fact"
    confidence: float = Field(ge=0, le=1)
    primary: Citation = Field(description="The main citation")
    secondary: Citation | None = Field(default=None, description="Optional second citation")


class Cat(BaseModel):
    pet: Literal["cat"]
    lives: int


class Dog(BaseModel):
    pet: Literal["dog"]
    tricks: list[str]


class Node(BaseModel):
    name: str
    parent: Node | None = Field(default=None, description="Parent node")
    children: list[Node] = []


class Compiled(BaseModel):
    facts: list[KeyFact]
    animal: Annotated[Cat | Dog, Field(discriminator="pet")]
    tree: Node
    issued: str = Field(json_schema_extra={"format": "date"})


class KeywordNamedFields(BaseModel):
    title: str
    default: str | None = None
    format: Literal["pdf", "docx"] = "pdf"


def _walk(node: dict[str, Any]) -> list[dict[str, Any]]:
    """All schema nodes (not property-name mappings) reachable from ``node``."""
    found = [node]
    children: list[Any] = [*node.get("properties", {}).values(), *node.get("anyOf", [])]
    children.extend(node.get("$defs", {}).values())
    if isinstance(node.get("items"), dict):
        children.append(node["items"])
    for child in children:
        found.extend(_walk(child))
    return found


def test_every_object_is_closed_and_fully_required() -> None:
    schema = to_strict_json_schema(Compiled)
    objects = [node for node in _walk(schema) if node.get("type") == "object"]
    assert objects
    for node in objects:
        assert node["additionalProperties"] is False
        assert node["required"] == list(node["properties"])


def test_no_unsupported_or_annotation_keywords_remain() -> None:
    schema = to_strict_json_schema(Compiled)
    forbidden = {
        "title",
        "default",
        "pattern",
        "format",
        "maxLength",
        "minimum",
        "maximum",
        "minItems",
        "const",
        "oneOf",
        "allOf",
        "discriminator",
    }
    for node in _walk(schema):
        assert not set(node) & forbidden, set(node) & forbidden


def test_fields_named_like_keywords_are_preserved() -> None:
    schema = to_strict_json_schema(KeywordNamedFields)
    assert list(schema["properties"]) == ["title", "default", "format"]
    assert schema["required"] == ["title", "default", "format"]
    assert schema["properties"]["format"] == {"type": "string", "enum": ["pdf", "docx"]}


def test_nested_models_use_defs_and_refs() -> None:
    schema = to_strict_json_schema(Compiled)
    assert schema["properties"]["facts"] == {"type": "array", "items": {"$ref": "#/$defs/KeyFact"}}
    assert set(schema["$defs"]) >= {"KeyFact", "Citation", "Severity", "Cat", "Dog", "Node"}


def test_optional_becomes_any_of_null_and_stays_required() -> None:
    citation = to_strict_json_schema(Compiled)["$defs"]["Citation"]
    assert citation["properties"]["quote"] == {"anyOf": [{"type": "string"}, {"type": "null"}]}
    assert citation["required"] == ["block_id", "quote"]
    fact = to_strict_json_schema(Compiled)["$defs"]["KeyFact"]
    assert fact["properties"]["secondary"] == {
        "anyOf": [{"$ref": "#/$defs/Citation"}, {"type": "null"}],
        "description": "Optional second citation",
    }


def test_enums_literals_and_discriminated_unions() -> None:
    schema = to_strict_json_schema(Compiled)
    assert schema["$defs"]["Severity"] == {"type": "string", "enum": ["low", "high"]}
    fact = schema["$defs"]["KeyFact"]["properties"]
    assert fact["severity"] == {"$ref": "#/$defs/Severity"}
    assert fact["kind"] == {"type": "string", "enum": ["fact"]}
    assert schema["properties"]["animal"] == {
        "anyOf": [{"$ref": "#/$defs/Cat"}, {"$ref": "#/$defs/Dog"}]
    }
    assert schema["$defs"]["Cat"]["properties"]["pet"] == {"type": "string", "enum": ["cat"]}


def test_lists_keep_item_schemas() -> None:
    fact = to_strict_json_schema(Compiled)["$defs"]["KeyFact"]["properties"]
    assert fact["numbers"] == {"type": "array", "items": {"type": "string"}}
    assert fact["citations"]["items"] == {"$ref": "#/$defs/Citation"}


def test_ref_with_description_is_inlined_as_a_strict_object() -> None:
    primary = to_strict_json_schema(Compiled)["$defs"]["KeyFact"]["properties"]["primary"]
    assert "$ref" not in primary
    assert primary["type"] == "object"
    assert primary["additionalProperties"] is False
    assert primary["required"] == ["block_id", "quote"]
    assert primary["description"].startswith("The main citation")


def test_removed_constraints_are_restated_in_descriptions() -> None:
    schema = to_strict_json_schema(Compiled)
    fact = schema["$defs"]["KeyFact"]["properties"]
    assert fact["text"]["description"] == "(constraints: maxLength=500)"
    assert fact["confidence"]["description"] == "(constraints: minimum=0, maximum=1)"
    assert fact["citations"]["description"] == "(constraints: minItems=1)"
    block_id = schema["$defs"]["Citation"]["properties"]["block_id"]
    assert block_id["description"] == "Block id (constraints: pattern=^b\\d{4}$)"
    assert schema["properties"]["issued"]["description"] == "(constraints: format=date)"


def test_recursive_models_are_supported() -> None:
    schema = to_strict_json_schema(Node)
    assert schema["type"] == "object"
    assert schema["properties"]["children"] == {"type": "array", "items": {"$ref": "#/$defs/Node"}}
    assert schema["properties"]["parent"]["anyOf"][0] == {"$ref": "#/$defs/Node"}
    assert schema["$defs"]["Node"]["additionalProperties"] is False


def test_docstring_description_is_kept_and_titles_dropped() -> None:
    schema = to_strict_json_schema(Citation)
    assert schema["description"] == "A pointer to an extracted block."
    assert "title" not in schema


def test_result_is_a_fresh_copy_and_json_serialisable() -> None:
    first = to_strict_json_schema(Compiled)
    first["properties"].clear()
    second = to_strict_json_schema(Compiled)
    assert second["properties"]
    json.dumps(second, allow_nan=False)


class FreeForm(BaseModel):
    values: dict[str, int]


class Tupled(BaseModel):
    pair: tuple[int, str]


class Anything(BaseModel):
    payload: Any


class Opened(BaseModel):
    model_config = {"extra": "allow"}

    name: str


@pytest.mark.parametrize("model", [FreeForm, Tupled, Anything])
def test_unrepresentable_models_raise(model: type[BaseModel]) -> None:
    with pytest.raises(StrictSchemaError):
        to_strict_json_schema(model)


def test_extra_allow_is_closed_for_the_model_output() -> None:
    schema = to_strict_json_schema(Opened)
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["name"]


def test_non_model_is_rejected() -> None:
    with pytest.raises(TypeError):
        to_strict_json_schema(dict)  # type: ignore[arg-type]


class SpecCitation(BaseModel):
    block_id: str
    quote: str | None = None


class SpecKeyFact(BaseModel):
    text: str
    citations: list[SpecCitation]
    numbers: list[str]


class SpecSection(BaseModel):
    heading: str
    body: str
    table_refs: list[str]


class SpecEntityMention(BaseModel):
    entity_id: str
    block_ids: list[str]


class SpecUnknownEntity(BaseModel):
    label: str
    type_guess: str
    block_ids: list[str]


class SpecGlossaryCandidate(BaseModel):
    term: str
    definition: str
    block_ids: list[str]


class SpecInjectionFlag(BaseModel):
    block_id: str
    reason: str


class SpecCompiledSource(BaseModel):
    """Shape of CompiledSource in docs/spec/pipeline.md section 3."""

    title: str
    summary: str
    key_facts: list[SpecKeyFact]
    sections: list[SpecSection]
    entity_mentions: list[SpecEntityMention]
    unknown_entities: list[SpecUnknownEntity]
    glossary_candidates: list[SpecGlossaryCandidate]
    injection_flags: list[SpecInjectionFlag]


def _depth_and_properties(
    schema: dict[str, Any], node: dict[str, Any], depth: int
) -> tuple[int, int]:
    if "$ref" in node:
        node = schema["$defs"][node["$ref"].removeprefix("#/$defs/")]
    if node.get("type") == "array":
        return _depth_and_properties(schema, node["items"], depth)
    if node.get("type") != "object":
        return depth, 0
    deepest, count = depth, len(node["properties"])
    for child in node["properties"].values():
        child_depth, child_count = _depth_and_properties(schema, child, depth + 1)
        deepest, count = max(deepest, child_depth), count + child_count
    return deepest, count


def test_spec_compiled_source_fits_strict_mode_limits() -> None:
    schema = to_strict_json_schema(SpecCompiledSource)
    assert schema["required"] == list(SpecCompiledSource.model_fields)
    depth, properties = _depth_and_properties(schema, schema, 1)
    # Azure OpenAI structured outputs: at most 5 nesting levels and 100 object properties.
    assert depth <= 5
    assert properties <= 100
