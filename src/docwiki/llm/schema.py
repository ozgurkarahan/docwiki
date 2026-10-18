"""Convert pydantic models into JSON schemas accepted by strict structured outputs.

Azure OpenAI / Foundry structured outputs accept a subset of JSON Schema: every object lists all
of its properties as ``required`` and sets ``additionalProperties: false``; optional values are
expressed as ``anyOf`` with ``{"type": "null"}``; validation keywords such as ``maxLength``,
``pattern``, ``format``, ``minimum`` or ``minItems`` are not supported. This module rewrites the
pydantic schema accordingly:

* annotations (``title``, ``default``, ``examples``...) are removed;
* unsupported validation keywords are removed and restated in the ``description`` (the pydantic
  model still enforces them when the output is validated, which triggers the repair retry);
* ``const`` becomes a one-value ``enum``, ``oneOf`` becomes ``anyOf``, single ``allOf`` is merged;
* ``$ref`` with sibling keywords is inlined (recursion keeps the bare ``$ref``);
* anything that cannot be expressed (free-form dicts, ``Any``, tuples, ``not``/``if``...) raises
  :class:`StrictSchemaError` instead of silently changing the meaning of the schema.
"""

from __future__ import annotations

import copy
import functools
import json
from typing import Any

from pydantic import BaseModel

_ANNOTATION_KEYS = frozenset(
    {
        "title",
        "default",
        "examples",
        "$comment",
        "$schema",
        "$id",
        "deprecated",
        "readOnly",
        "writeOnly",
        "discriminator",
        "contentEncoding",
        "contentMediaType",
    }
)
_HINT_KEYS = (
    "format",
    "pattern",
    "minLength",
    "maxLength",
    "minimum",
    "exclusiveMinimum",
    "maximum",
    "exclusiveMaximum",
    "multipleOf",
    "minItems",
    "maxItems",
    "uniqueItems",
    "minProperties",
    "maxProperties",
)
_UNSUPPORTED_KEYS = frozenset(
    {
        "not",
        "if",
        "then",
        "else",
        "dependentRequired",
        "dependentSchemas",
        "patternProperties",
        "unevaluatedProperties",
        "unevaluatedItems",
        "propertyNames",
        "contains",
        "minContains",
        "maxContains",
        "prefixItems",
        "additionalItems",
        "contentSchema",
        "$dynamicRef",
        "$dynamicAnchor",
        "$anchor",
    }
)
_ALLOWED_KEYS = frozenset(
    {
        "type",
        "description",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "enum",
        "anyOf",
        "$ref",
    }
)


class StrictSchemaError(ValueError):
    """The model cannot be expressed as a strict structured-output schema."""


def to_strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    """Return a strict structured-output JSON schema for ``model`` (a fresh copy every call)."""
    if not (isinstance(model, type) and issubclass(model, BaseModel)):
        raise TypeError(f"Expected a pydantic BaseModel subclass, got {model!r}")
    return copy.deepcopy(_cached_strict_schema(model))


@functools.lru_cache(maxsize=512)
def _cached_strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    raw = model.model_json_schema(mode="validation")
    return _StrictConverter(raw, model.__name__).convert()


class _StrictConverter:
    def __init__(self, root: dict[str, Any], model_name: str) -> None:
        self._root = root
        self._defs: dict[str, Any] = dict(root.get("$defs", {}))
        self._model_name = model_name
        self._expanding: list[str] = []

    def convert(self) -> dict[str, Any]:
        root = {key: value for key, value in self._root.items() if key != "$defs"}
        if "$ref" in root:
            # Recursive root models are emitted as {"$ref": "#/$defs/Model", "$defs": {...}}.
            ref = root.pop("$ref")
            root = {**self._resolve(ref, "#"), **root}
        converted = self._node(root, "#")
        if converted.get("type") != "object" or "properties" not in converted:
            raise self._error("#", "the root schema must be an object (use a BaseModel)")
        if self._defs:
            converted["$defs"] = {
                name: self._node(definition, f"#/$defs/{name}")
                for name, definition in self._defs.items()
            }
        return converted

    def _error(self, path: str, message: str) -> StrictSchemaError:
        return StrictSchemaError(f"{self._model_name} {path}: {message}")

    def _node(self, schema: Any, path: str) -> dict[str, Any]:
        if not isinstance(schema, dict):
            raise self._error(path, f"expected a schema object, got {schema!r}")
        node = {key: value for key, value in schema.items() if key not in _ANNOTATION_KEYS}

        hints = [f"{key}={_format_hint(node.pop(key))}" for key in _HINT_KEYS if key in node]

        unsupported = sorted(key for key in node if key in _UNSUPPORTED_KEYS)
        if unsupported:
            raise self._error(
                path,
                f"unsupported keyword(s) {', '.join(unsupported)} "
                "(tuples, free-form mappings and conditional schemas cannot be strict)",
            )

        if "const" in node:
            value = node.pop("const")
            if "enum" in node and node["enum"] != [value]:
                raise self._error(path, "both const and enum are set")
            node["enum"] = [value]

        if "oneOf" in node:
            if "anyOf" in node:
                raise self._error(path, "both oneOf and anyOf are set")
            node["anyOf"] = node.pop("oneOf")

        if "allOf" in node:
            members = node.pop("allOf")
            if not isinstance(members, list) or len(members) != 1:
                raise self._error(path, "allOf with several schemas is not supported")
            merged = {**members[0], **node}
            return _with_hints(self._node(merged, path), hints)

        if "$ref" in node:
            return _with_hints(self._ref(node, path), hints)

        if "anyOf" in node:
            members = node["anyOf"]
            if not isinstance(members, list) or not members:
                raise self._error(path, "anyOf must be a non-empty list")
            node["anyOf"] = [
                self._node(member, f"{path}/anyOf/{index}") for index, member in enumerate(members)
            ]

        types = node.get("type")
        type_list = types if isinstance(types, list) else [types]
        if "object" in type_list or "properties" in node:
            self._object(node, path)
        if "array" in type_list:
            items = node.get("items")
            if not isinstance(items, dict):
                raise self._error(path, "arrays need an item schema (tuples are not supported)")
            node["items"] = self._node(items, f"{path}/items")
        elif "items" in node:
            raise self._error(path, "items is only allowed on arrays")

        if not any(key in node for key in ("type", "enum", "anyOf")):
            raise self._error(path, "the schema accepts any value (typing.Any is not supported)")
        unknown = sorted(set(node) - _ALLOWED_KEYS)
        if unknown:
            raise self._error(path, f"unknown keyword(s) {', '.join(unknown)}")
        return _with_hints(node, hints)

    def _object(self, node: dict[str, Any], path: str) -> None:
        properties = node.get("properties", {})
        if not isinstance(properties, dict):
            raise self._error(path, "properties must be an object")
        extra = node.get("additionalProperties", False)
        if extra is not False and (isinstance(extra, dict) or not properties):
            raise self._error(
                path,
                "free-form objects (dict fields, additionalProperties) are not supported; "
                "use a list of key/value models instead",
            )
        node["type"] = "object"
        node["properties"] = {
            name: self._node(value, f"{path}/properties/{name}")
            for name, value in properties.items()
        }
        node["required"] = list(properties)
        node["additionalProperties"] = False

    def _ref(self, node: dict[str, Any], path: str) -> dict[str, Any]:
        ref = node["$ref"]
        siblings = {key: value for key, value in node.items() if key != "$ref"}
        if not siblings or ref in self._expanding:
            return {"$ref": ref}
        target = self._resolve(ref, path)
        self._expanding.append(ref)
        try:
            return self._node({**target, **siblings}, path)
        finally:
            self._expanding.pop()

    def _resolve(self, ref: Any, path: str) -> dict[str, Any]:
        if ref == "#":
            return {key: value for key, value in self._root.items() if key != "$defs"}
        prefix = "#/$defs/"
        if not isinstance(ref, str) or not ref.startswith(prefix):
            raise self._error(path, f"unsupported $ref {ref!r}")
        name = ref[len(prefix) :]
        if name not in self._defs:
            raise self._error(path, f"unresolved $ref {ref!r}")
        return self._defs[name]


def _format_hint(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False)


def _with_hints(node: dict[str, Any], hints: list[str]) -> dict[str, Any]:
    if not hints:
        return node
    if set(node) == {"$ref"}:
        return node
    note = f"(constraints: {', '.join(hints)})"
    description = node.get("description")
    node["description"] = f"{description} {note}" if description else note
    return node
