"""JSON Schema export compatible with OpenAI / Azure OpenAI *strict* structured outputs.

Strict mode requires: an object root, every property listed in ``required``,
``additionalProperties: false`` on every object, optional values expressed as
``anyOf: [..., {"type": "null"}]`` and only a small keyword subset. Validation keywords that
strict mode does not support (patterns, lengths, bounds, formats) are removed here; the
Pydantic model still enforces them when the response is parsed.
"""

from __future__ import annotations

import copy
from typing import Any

from pydantic import BaseModel

__all__ = ["check_strict_schema", "strict_json_schema", "strict_response_format"]

_ALLOWED_KEYS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "anyOf",
        "enum",
        "const",
        "description",
    }
)


def _resolve_refs(node: Any, defs: dict[str, Any], stack: tuple[str, ...] = ()) -> Any:
    if isinstance(node, dict):
        if "$ref" in node:
            name = node["$ref"].rsplit("/", 1)[-1]
            if name in stack:
                raise ValueError(f"recursive schema {name!r} is not supported in strict mode")
            merged = {**copy.deepcopy(defs[name]), **{k: v for k, v in node.items() if k != "$ref"}}
            return _resolve_refs(merged, defs, (*stack, name))
        return {key: _resolve_refs(value, defs, stack) for key, value in node.items()}
    if isinstance(node, list):
        return [_resolve_refs(item, defs, stack) for item in node]
    return node


def _is_nullable(node: dict[str, Any]) -> bool:
    return node.get("type") == "null" or any(
        isinstance(option, dict) and option.get("type") == "null"
        for option in node.get("anyOf", [])
    )


def _strictify(node: Any) -> Any:
    if isinstance(node, list):
        return [_strictify(item) for item in node]
    if not isinstance(node, dict):
        return node
    if "oneOf" in node and "anyOf" not in node:
        node = {
            **{k: v for k, v in node.items() if k not in ("oneOf", "discriminator")},
            "anyOf": node["oneOf"],
        }
    if "allOf" in node and len(node["allOf"]) == 1:
        node = {**{k: v for k, v in node.items() if k != "allOf"}, **node["allOf"][0]}
    out: dict[str, Any] = {}
    for key, value in node.items():
        if key not in _ALLOWED_KEYS:
            continue
        if key == "properties":
            out[key] = {name: _strictify(prop) for name, prop in value.items()}
        elif key in ("items",):
            out[key] = _strictify(value)
        elif key == "anyOf":
            out[key] = [_strictify(option) for option in value]
        elif key == "additionalProperties":
            if isinstance(value, dict) and value:
                raise ValueError("free-form maps are not allowed in strict structured outputs")
            out[key] = False
        else:
            out[key] = value
    if out.get("type") == "object" or "properties" in out:
        properties = out.get("properties", {})
        out["type"] = "object"
        out["properties"] = properties
        out["required"] = list(properties)
        out["additionalProperties"] = False
    return out


def strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Self-contained strict schema for ``model`` (``$ref`` inlined, all properties required)."""
    raw = model.model_json_schema(by_alias=True, mode="validation")
    defs = raw.pop("$defs", {})
    inlined = _resolve_refs(raw, defs)
    schema = _strictify(inlined)
    if schema.get("type") != "object":
        raise ValueError("strict structured outputs need an object at the root")
    check_strict_schema(schema)
    return schema


def strict_response_format(model: type[BaseModel], name: str | None = None) -> dict[str, Any]:
    """``text.format`` payload for the Responses API (``{"type": "json_schema", ...}``)."""
    return {
        "type": "json_schema",
        "name": name or model.__name__,
        "schema": strict_json_schema(model),
        "strict": True,
    }


def check_strict_schema(schema: dict[str, Any], path: str = "$") -> None:
    """Raise ``ValueError`` when ``schema`` breaks a strict-mode rule (used by tests and lanes)."""
    if not isinstance(schema, dict):
        raise ValueError(f"{path}: schema node must be an object")
    unknown = set(schema) - _ALLOWED_KEYS
    if unknown:
        raise ValueError(f"{path}: unsupported keywords {sorted(unknown)}")
    if "anyOf" in schema:
        for index, option in enumerate(schema["anyOf"]):
            check_strict_schema(option, f"{path}.anyOf[{index}]")
    if schema.get("type") == "object":
        properties = schema.get("properties")
        if not isinstance(properties, dict):
            raise ValueError(f"{path}: objects need properties")
        if schema.get("additionalProperties") is not False:
            raise ValueError(f"{path}: additionalProperties must be false")
        if schema.get("required") != list(properties):
            raise ValueError(f"{path}: every property must be required")
        for name, prop in properties.items():
            check_strict_schema(prop, f"{path}.{name}")
    if schema.get("type") == "array":
        if "items" not in schema:
            raise ValueError(f"{path}: arrays need items")
        check_strict_schema(schema["items"], f"{path}[]")


def is_nullable(node: dict[str, Any]) -> bool:
    """True when a strict schema node accepts ``null``."""
    return _is_nullable(node)
