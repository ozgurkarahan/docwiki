"""Frontmatter read/write: a YAML block at the top of every page, stable key order, LF only."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import yaml

__all__ = [
    "FrontmatterError",
    "load_yaml_mapping",
    "read_frontmatter",
    "render_frontmatter",
    "split_frontmatter",
    "write_frontmatter",
]


class FrontmatterError(ValueError):
    """Malformed frontmatter block or YAML."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe loader that rejects duplicate mapping keys."""


def _construct_mapping(
    loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False
) -> dict:
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError:
            raise yaml.constructor.ConstructorError(
                None, None, f"unhashable key {key!r}", key_node.start_mark
            ) from None
        if key in mapping:
            raise yaml.constructor.ConstructorError(
                None, None, f"duplicate key {key!r}", key_node.start_mark
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


class _Dumper(yaml.SafeDumper):
    def ignore_aliases(self, data: Any) -> bool:
        return True


def _represent_str(dumper: yaml.SafeDumper, value: str) -> yaml.ScalarNode:
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_Dumper.add_representer(str, _represent_str)


def load_yaml_mapping(text: str, *, where: str = "YAML") -> dict[str, Any]:
    """Parse YAML text that must be a mapping (empty text → ``{}``); duplicate keys are errors."""
    try:
        data = yaml.load(text, Loader=_UniqueKeyLoader)
    except yaml.YAMLError as exc:
        raise FrontmatterError(f"{where}: invalid YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise FrontmatterError(f"{where}: expected a mapping, got {type(data).__name__}")
    for key in data:
        if not isinstance(key, str):
            raise FrontmatterError(f"{where}: keys must be strings, got {key!r}")
    return data


def split_frontmatter(text: str) -> tuple[str | None, str]:
    """Split ``---`` delimited YAML from the body. Returns ``(None, text)`` without a block.

    The opening line must be exactly ``---`` at the very start of the file and the block must be
    closed by a line that is exactly ``---``. Blank lines after the block are not part of the
    body.
    """
    if text.startswith("\ufeff"):
        raise FrontmatterError("byte order mark is not allowed")
    if "\r" in text:
        raise FrontmatterError("CR characters are not allowed (LF line endings only)")
    if not (text.startswith("---\n") or text == "---"):
        return None, text
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if lines[index] == "---":
            yaml_text = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return yaml_text, body.lstrip("\n")
    raise FrontmatterError("unterminated frontmatter block (missing closing '---')")


def read_frontmatter(text: str, *, where: str = "frontmatter") -> tuple[dict[str, Any], str]:
    """Return ``(data, body)``; raises :class:`FrontmatterError` when the block is missing."""
    yaml_text, body = split_frontmatter(text)
    if yaml_text is None:
        raise FrontmatterError(f"{where}: missing frontmatter block")
    return load_yaml_mapping(yaml_text, where=where), body


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    if isinstance(value, str):
        return str(value)
    if value is None or isinstance(value, bool | int | float | date | datetime):
        return value
    raise TypeError(f"cannot write {type(value).__name__} to frontmatter")


def render_frontmatter(data: Mapping[str, Any]) -> str:
    """``---`` + YAML (insertion order kept, Unicode as-is, no line wrapping) + ``---``."""
    text = yaml.dump(
        _plain(data),
        Dumper=_Dumper,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=4096,
    )
    return f"---\n{text}---\n"


def write_frontmatter(data: Mapping[str, Any], body: str) -> str:
    """Full page text: frontmatter block, one blank line, body (LF, single trailing newline)."""
    clean = body.replace("\r\n", "\n").replace("\r", "\n").lstrip("\n").rstrip("\n")
    return f"{render_frontmatter(data)}\n{clean}\n"
