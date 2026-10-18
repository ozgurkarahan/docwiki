"""Registry of the cross-lane engine functions (docs/spec/engine-interfaces.md).

The orchestrator never imports the extract and compile lanes directly: it asks the registry for
an :class:`Engine`, a bundle of the seven functions with the exact frozen signatures. The real
modules are used automatically when they are importable; tests (and partial checkouts) install
stub implementations with :func:`use_engine` / :func:`set_engine`.

Versions used in cache keys come from the implementing modules: ``STAGE_VERSION`` (or
``VERSION`` / ``__version__``) when defined, otherwise a hash of the module source so that any
code change invalidates the dependent artifacts. Lane *packages* (``docwiki.extract``,
``docwiki.evidence``) add their public ``*_VERSION`` strings and ``extractor_versions()``
(adapter and parser library versions): they are hashed into the stage version and reported in
``VersionInfo.extractors``. Prompt versions are collected from ``docwiki.stages.prompts``
(``PROMPT_VERSION`` / ``PROMPT_VERSIONS`` of each module, a content hash for prompt files) and
from the stage modules themselves.
"""

from __future__ import annotations

import contextlib
import importlib
import importlib.resources
import inspect
import json
import logging
import pkgutil
from collections.abc import Awaitable, Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.enums import Sensitivity
from docwiki.contracts.extracted import ExtractedDoc
from docwiki.contracts.pages import DocwikiStamp, Page
from docwiki.contracts.state import SourceState
from docwiki.domain.models import DomainPack
from docwiki.engine_types import (
    CitedLocator,
    Classification,
    CompiledResult,
    ExtractResult,
    ExtractSettings,
    TopicSkip,
)
from docwiki.llm.client import LlmClient
from docwiki.release.writer import ReleaseWriter

__all__ = [
    "ENGINE_FUNCTIONS",
    "LLM_STAGES",
    "Engine",
    "EngineUnavailableError",
    "active_engine",
    "collect_prompt_versions",
    "load_engine",
    "missing_engine_functions",
    "module_version",
    "package_versions",
    "set_engine",
    "use_engine",
]

logger = logging.getLogger("docwiki.engine")


class ExtractSourceFn(Protocol):
    def __call__(
        self,
        raw_file: Path,
        *,
        rel_path: str,
        settings: ExtractSettings,
        llm: LlmClient | None = None,
    ) -> Awaitable[ExtractResult]: ...


class BuildEvidenceFn(Protocol):
    def __call__(
        self,
        *,
        doc: ExtractedDoc,
        raw_file: Path,
        cited: Sequence[CitedLocator],
        source_title: str,
        source_page_path: str,
        sensitivity: Sensitivity,
        publish_original: bool,
        writer: ReleaseWriter,
        page_images: Mapping[int, bytes] | None = None,
    ) -> list[str]: ...


class ClassifySourceFn(Protocol):
    def __call__(
        self, doc: ExtractedDoc, pack: DomainPack, llm: LlmClient
    ) -> Awaitable[Classification]: ...


class CompileSourceFn(Protocol):
    def __call__(
        self,
        doc: ExtractedDoc,
        classification: Classification,
        pack: DomainPack,
        llm: LlmClient,
        *,
        hints: str | None = None,
    ) -> Awaitable[CompiledResult]: ...


class RenderSourcePageFn(Protocol):
    def __call__(
        self,
        result: CompiledResult,
        doc: ExtractedDoc,
        classification: Classification,
        state: SourceState,
        *,
        slug: str,
        stamp: DocwikiStamp,
        pack: DomainPack,
        supersedes: Sequence[str] = (),
        superseded_by: Sequence[str] = (),
    ) -> tuple[Page, list[CitedLocator]]: ...


class BuildEntityPagesFn(Protocol):
    def __call__(
        self,
        results: Sequence[CompiledResult],
        source_pages: Mapping[str, Page],
        pack: DomainPack,
        llm: LlmClient,
        *,
        stamp: DocwikiStamp,
    ) -> Awaitable[tuple[list[Page], list[CitedLocator]]]: ...


class BuildTopicPagesFn(Protocol):
    def __call__(
        self,
        results: Sequence[CompiledResult],
        source_pages: Mapping[str, Page],
        states: Mapping[str, SourceState],
        classifications: Mapping[str, Classification],
        pack: DomainPack,
        llm: LlmClient,
        *,
        audience: Sensitivity,
        stamp: DocwikiStamp,
    ) -> Awaitable[tuple[list[Page], list[CitedLocator], list[TopicSkip]]]: ...


ENGINE_FUNCTIONS: dict[str, tuple[str, str, str]] = {
    "extract_source": ("docwiki.extract", "extract_source", "extract"),
    "build_evidence": ("docwiki.evidence", "build_evidence", "evidence"),
    "classify_source": ("docwiki.stages.classify", "classify_source", "classify"),
    "compile_source": ("docwiki.stages.compile", "compile_source", "compile"),
    "render_source_page": ("docwiki.stages.render", "render_source_page", "render"),
    "build_entity_pages": ("docwiki.stages.entities", "build_entity_pages", "entities"),
    "build_topic_pages": ("docwiki.stages.topics", "build_topic_pages", "topics"),
}
"""Function name → (module, attribute, stage) of the frozen cross-lane interface."""

LLM_STAGES = ("extract", "classify", "compile", "entities", "topics")
_PROMPT_STEMS: dict[str, tuple[str, ...]] = {
    "extract": ("figure", "describ", "extract"),
    "classify": ("classif",),
    "compile": ("compil",),
    "entities": ("entit",),
    "topics": ("topic",),
}
PROMPTS_PACKAGE = "docwiki.stages.prompts"


class EngineUnavailableError(RuntimeError):
    """Some engine functions cannot be imported (their lane is not merged yet)."""

    def __init__(self, missing: Sequence[str]) -> None:
        self.missing = list(missing)
        super().__init__(
            "engine functions not available: "
            + ", ".join(self.missing)
            + " (merge the extract and compile lanes or install stubs with use_engine())"
        )


def module_version(module: ModuleType | None, fallback: str = "unknown") -> str:
    """``STAGE_VERSION``/``VERSION``/``__version__`` of a module, else a hash of its source."""
    if module is None:
        return fallback
    for name in ("STAGE_VERSION", "VERSION", "__version__"):
        value = getattr(module, name, None)
        if isinstance(value, str | int) and str(value):
            return str(value)
    try:
        source = inspect.getsourcefile(module)
    except TypeError:
        source = None
    if source and Path(source).is_file():
        return "src-" + sha256_hex(Path(source).read_bytes())[:12]
    return fallback


def _function_version(func: Callable[..., Any]) -> str:
    explicit = getattr(func, "__docwiki_version__", None)
    if isinstance(explicit, str) and explicit:
        return explicit
    return module_version(inspect.getmodule(func))


def package_versions(package_name: str) -> dict[str, str]:
    """Version details a lane *package* exposes: its public ``*_VERSION`` strings and the
    result of an ``extractor_versions()`` helper (adapter and parser library versions).

    Plain modules (the compile-lane stages) return ``{}``: their ``STAGE_VERSION`` and prompt
    versions are used instead.
    """
    try:
        package = importlib.import_module(package_name)
    except ImportError:
        return {}
    if not hasattr(package, "__path__"):
        return {}
    found: dict[str, str] = {}
    for name in sorted(getattr(package, "__all__", None) or dir(package)):
        value = getattr(package, name, None)
        if name.endswith("_VERSION") and isinstance(value, str) and value:
            found[name.lower()] = value
    helper = getattr(package, "extractor_versions", None)
    if callable(helper):
        try:
            found.update({str(key): str(value) for key, value in dict(helper()).items()})
        except Exception:  # an optional helper must never stop the engine
            logger.warning("%s.extractor_versions() failed", package_name, exc_info=True)
    return found


def collect_prompt_versions(extra_modules: Sequence[ModuleType] = ()) -> dict[str, str]:
    """Prompt name → version from ``docwiki.stages.prompts`` and the given stage modules."""
    versions: dict[str, str] = {}
    try:
        package = importlib.import_module(PROMPTS_PACKAGE)
    except ImportError:
        package = None
    if package is not None:
        for info in pkgutil.iter_modules(getattr(package, "__path__", [])):
            try:
                module = importlib.import_module(f"{PROMPTS_PACKAGE}.{info.name}")
            except ImportError:
                continue
            _add_module_prompts(versions, info.name, module)
        try:
            files = importlib.resources.files(PROMPTS_PACKAGE)
            for entry in sorted(files.iterdir(), key=lambda item: item.name):
                if entry.is_file() and not entry.name.endswith((".py", ".pyc")):
                    stem = entry.name.rsplit(".", 1)[0]
                    versions.setdefault(stem, "sha-" + sha256_hex(entry.read_bytes())[:12])
        except (
            ModuleNotFoundError,
            FileNotFoundError,
            NotADirectoryError,
            TypeError,
            ValueError,
            AttributeError,
        ):
            pass
    for module in extra_modules:
        _add_module_prompts(versions, module.__name__.rsplit(".", 1)[-1], module)
    return dict(sorted(versions.items()))


def _add_module_prompts(versions: dict[str, str], name: str, module: ModuleType) -> None:
    single = getattr(module, "PROMPT_VERSION", None)
    if isinstance(single, str) and single:
        versions.setdefault(name, single)
    many = getattr(module, "PROMPT_VERSIONS", None)
    if isinstance(many, Mapping):
        for key, value in many.items():
            if isinstance(key, str) and isinstance(value, str):
                versions.setdefault(key, value)


@dataclass(frozen=True)
class Engine:
    """The seven cross-lane functions plus the versions that go into cache keys."""

    extract_source: ExtractSourceFn
    build_evidence: BuildEvidenceFn
    classify_source: ClassifySourceFn
    compile_source: CompileSourceFn
    render_source_page: RenderSourcePageFn
    build_entity_pages: BuildEntityPagesFn
    build_topic_pages: BuildTopicPagesFn
    stage_versions: Mapping[str, str] = field(default_factory=dict)
    prompt_versions: Mapping[str, str] = field(default_factory=dict)
    origins: Mapping[str, str] = field(default_factory=dict)
    version_details: Mapping[str, str] = field(default_factory=dict)

    def version(self, stage: str) -> str:
        return self.stage_versions.get(stage, "unknown")

    def prompts_for(self, stage: str) -> str | None:
        """Combined prompt versions used by ``stage`` (all prompts when none match by name)."""
        if stage not in LLM_STAGES or not self.prompt_versions:
            return None
        stems = _PROMPT_STEMS.get(stage, (stage,))
        matching = {
            name: version
            for name, version in self.prompt_versions.items()
            if any(stem in name.lower() for stem in stems)
        }
        chosen = matching or dict(self.prompt_versions)
        return ";".join(f"{name}={version}" for name, version in sorted(chosen.items()))

    @property
    def extractor_versions(self) -> dict[str, str]:
        return {
            "extract": self.version("extract"),
            "evidence": self.version("evidence"),
        }


def _import_function(module_name: str, attribute: str) -> Callable[..., Any] | None:
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return None
    func = getattr(module, attribute, None)
    return func if callable(func) else None


def missing_engine_functions() -> list[str]:
    """Names of the real engine functions that cannot be imported."""
    return [
        name
        for name, (module_name, attribute, _) in ENGINE_FUNCTIONS.items()
        if _import_function(module_name, attribute) is None
    ]


def load_engine(
    overrides: Mapping[str, Callable[..., Any]] | None = None,
    *,
    versions: Mapping[str, str] | None = None,
    prompts: Mapping[str, str] | None = None,
) -> Engine:
    """Build an :class:`Engine` from the real modules, replacing any function in ``overrides``.

    Raises :class:`EngineUnavailableError` listing the functions that are neither importable
    nor overridden.
    """
    functions: dict[str, Callable[..., Any]] = {}
    origins: dict[str, str] = {}
    missing: list[str] = []
    for name, (module_name, attribute, _) in ENGINE_FUNCTIONS.items():
        func = (overrides or {}).get(name) or _import_function(module_name, attribute)
        if func is None:
            missing.append(name)
            continue
        functions[name] = func
        origins[name] = f"{getattr(func, '__module__', '?')}:{getattr(func, '__name__', name)}"
    if missing:
        raise EngineUnavailableError(missing)
    stage_versions: dict[str, str] = {}
    details: dict[str, str] = {}
    for name, (package_name, _, stage) in ENGINE_FUNCTIONS.items():
        func = functions[name]
        version = _function_version(func)
        if str(getattr(func, "__module__", "")).startswith(package_name + "."):
            extra = package_versions(package_name)
            if extra:
                version = f"{version}+{sha256_hex(json.dumps(extra, sort_keys=True).encode())[:12]}"
                details.update({f"{stage}.{key}": value for key, value in extra.items()})
        stage_versions[stage] = version
    stage_versions.update(versions or {})
    modules = [
        module
        for module in (inspect.getmodule(func) for func in functions.values())
        if module is not None
    ]
    prompt_versions = collect_prompt_versions(modules)
    prompt_versions.update(prompts or {})
    return Engine(
        extract_source=functions["extract_source"],  # type: ignore[arg-type]
        build_evidence=functions["build_evidence"],  # type: ignore[arg-type]
        classify_source=functions["classify_source"],  # type: ignore[arg-type]
        compile_source=functions["compile_source"],  # type: ignore[arg-type]
        render_source_page=functions["render_source_page"],  # type: ignore[arg-type]
        build_entity_pages=functions["build_entity_pages"],  # type: ignore[arg-type]
        build_topic_pages=functions["build_topic_pages"],  # type: ignore[arg-type]
        stage_versions=dict(sorted(stage_versions.items())),
        prompt_versions=dict(sorted(prompt_versions.items())),
        origins=origins,
        version_details=dict(sorted(details.items())),
    )


_ACTIVE: Engine | None = None


def set_engine(engine: Engine | None) -> None:
    """Install ``engine`` for the whole process (``None`` returns to auto-detection)."""
    global _ACTIVE
    _ACTIVE = engine


@contextlib.contextmanager
def use_engine(engine: Engine) -> Iterator[Engine]:
    """Temporarily install ``engine`` (tests, notebooks)."""
    previous = _ACTIVE
    set_engine(engine)
    try:
        yield engine
    finally:
        set_engine(previous)


def active_engine() -> Engine:
    """The installed engine, else the real modules (``EngineUnavailableError`` if missing)."""
    return _ACTIVE if _ACTIVE is not None else load_engine()
