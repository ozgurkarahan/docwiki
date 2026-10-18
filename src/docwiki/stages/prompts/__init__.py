"""Versioned prompt files of the compile lane (pipeline.md §2).

Each ``<name>.md`` file in this folder starts with a frontmatter block ``{name, version}``; the
text after it is the prompt. ``version`` (``<name>-v<N>``) enters every request hash and stage
cache key, so bump it whenever the text changes (``tests/stages_compile`` pins the text hash of
every version). Prompts never contain document text: documents travel in the user message,
inside delimited data sections.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path

from docwiki.contracts.frontmatter import read_frontmatter

__all__ = ["PROMPTS_DIR", "Prompt", "combine_prompts", "load_prompt", "prompt_names"]

PROMPTS_DIR = Path(__file__).parent
_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


@dataclass(frozen=True)
class Prompt:
    """One prompt file: ``name``, ``version`` (``<name>-v<N>``) and the prompt ``text``."""

    name: str
    version: str
    text: str


def prompt_names() -> list[str]:
    """Names of every prompt file in this folder (sorted)."""
    return sorted(path.stem for path in PROMPTS_DIR.glob("*.md"))


@cache
def load_prompt(name: str) -> Prompt:
    """Load and validate ``<name>.md`` (cached)."""
    if not _NAME_RE.match(name):
        raise ValueError(f"invalid prompt name: {name!r}")
    path = PROMPTS_DIR / f"{name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"prompt file not found: {path.name}")
    raw = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    data, body = read_frontmatter(raw, where=path.name)
    if data.get("name") != name:
        raise ValueError(f"{path.name}: frontmatter name must be {name!r}")
    version = data.get("version")
    if not isinstance(version, str) or not re.fullmatch(rf"{re.escape(name)}-v\d+", version):
        raise ValueError(f"{path.name}: version must look like '{name}-v<N>'")
    if set(data) != {"name", "version"}:
        raise ValueError(f"{path.name}: frontmatter keys must be exactly name and version")
    text = body.strip()
    if not text:
        raise ValueError(f"{path.name}: empty prompt")
    return Prompt(name=name, version=version, text=text + "\n")


def combine_prompts(*names: str) -> tuple[str, str]:
    """``(system text, prompt version)`` of several prompts used together, in order.

    The texts are joined with a blank line; the version is the ``+``-joined list of versions
    (for example ``compile-v1+compile-map-v1``), so bumping any part changes the request hash.
    """
    if not names:
        raise ValueError("at least one prompt name is required")
    prompts = [load_prompt(name) for name in names]
    text = "\n".join(prompt.text for prompt in prompts)
    return text, "+".join(prompt.version for prompt in prompts)
