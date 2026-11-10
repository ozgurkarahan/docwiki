"""Registry of the systems under test: the built-in systems and any ``evals/systems_*.py`` module.

A module named ``evals/systems_<something>.py`` registers its systems when imported::

    from evals.registry import register_system

    def _build(options, corpus):
        return MySystem(...)

    register_system("my-system", _build, indexes_documents=True)

:func:`load_plugins` imports every such module once, so adding a system never edits the runner.
``indexes_documents`` marks systems that index the corpus documents of ``--scope`` (the runner
checks the selection is not empty and records the scope); agent systems answer over a release.
"""

from __future__ import annotations

import importlib
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from evals.corpus import CorpusContext
    from evals.systems import EvalSystem

__all__ = [
    "SystemFactory",
    "SystemSpec",
    "get_system",
    "load_plugins",
    "register_system",
    "system_names",
]

SystemFactory = Callable[[Any, "CorpusContext"], "EvalSystem"]
"""``factory(options, corpus)``: ``options`` is the runner's ``RunOptions``."""

PLUGIN_PREFIX = "systems_"


@dataclass(frozen=True)
class SystemSpec:
    name: str
    factory: SystemFactory
    indexes_documents: bool = False


_REGISTRY: dict[str, SystemSpec] = {}
_LOADED = False


def register_system(name: str, factory: SystemFactory, *, indexes_documents: bool = False) -> None:
    """Register a system; registering another factory under a taken name is an error."""
    existing = _REGISTRY.get(name)
    if existing is not None and existing.factory is not factory:
        raise ValueError(f"system {name!r} is already registered")
    _REGISTRY[name] = SystemSpec(name, factory, indexes_documents)


def load_plugins() -> None:
    """Import the ``evals/systems_*.py`` modules (once)."""
    global _LOADED
    if _LOADED:
        return
    _LOADED = True
    folder = Path(__file__).resolve().parent
    for module in sorted(pkgutil.iter_modules([str(folder)]), key=lambda m: m.name):
        if module.name.startswith(PLUGIN_PREFIX):
            importlib.import_module(f"evals.{module.name}")


def system_names() -> tuple[str, ...]:
    load_plugins()
    return tuple(_REGISTRY)


def get_system(name: str) -> SystemSpec:
    load_plugins()
    try:
        return _REGISTRY[name]
    except KeyError:
        raise ValueError(f"unknown system {name!r}; use one of {', '.join(_REGISTRY)}") from None
