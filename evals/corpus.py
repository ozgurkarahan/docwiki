"""The corpus as the evaluator sees it (docs/spec/evals.md §2).

* :class:`CorpusManifest` - ``samples/corpus/MANIFEST.json``: paths, SHA-256, sensitivity,
  quickstart flags and quickstart copies (``copy_of``);
* :class:`ReleaseCatalog` - the ``sources`` of a release ``catalog.json`` (id, raw path, hash);
* :class:`SourceResolver` - maps a cited source (SHA-256, ``source_id``, raw path or title) to its
  canonical corpus path, so that citations of a deployment whose raw paths differ from the corpus
  layout still match the golden ``required_citations``;
* :class:`ExtractionCache` - ExtractedDocs of the corpus (``docwiki.extract``, local mode by
  default) cached under ``.cache/evals/``;
* :class:`EvidenceStore` - the extracted text behind a locator, for citation precision;
* :func:`restricted_fingerprint` - values that only restricted sources contain.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from pydantic import ValidationError

from docwiki.contracts import ExtractedDoc, allowed_for_audience, locator_key, source_id_for
from evals.locators import is_key, keys_match, locator_key_from_label
from evals.records import Citation
from evals.textnorm import normalize_text, value_tokens

__all__ = [
    "SCOPES",
    "CatalogSourceRef",
    "CorpusContext",
    "CorpusFile",
    "CorpusManifest",
    "EvidenceStore",
    "ExtractionCache",
    "ReleaseCatalog",
    "ResolvedCitation",
    "SourceResolver",
    "load_corpus",
    "restricted_fingerprint",
]

SCOPES = ("full", "quickstart", "all")
ExtractMode = Literal["local", "azure"]


# ---------------------------------------------------------------------------- manifest


@dataclass(frozen=True)
class CorpusFile:
    """One MANIFEST entry. ``canonical`` is the original of a quickstart copy."""

    path: str
    sha256: str
    format: str = ""
    media_type: str = ""
    sensitivity: str = "public"
    quickstart: bool = False
    copy_of: str | None = None
    held_back: bool = False
    domain: str | None = None
    title: str | None = None

    @property
    def canonical(self) -> str:
        return self.copy_of or self.path

    @classmethod
    def from_entry(cls, entry: Mapping[str, Any]) -> CorpusFile:
        return cls(
            path=str(entry["path"]),
            sha256=str(entry["sha256"]).lower(),
            format=str(entry.get("format") or ""),
            media_type=str(entry.get("media_type") or ""),
            sensitivity=str(entry.get("sensitivity") or "public"),
            quickstart=bool(entry.get("quickstart")),
            copy_of=entry.get("copy_of") or None,
            held_back=bool(entry.get("held_back")),
            domain=entry.get("domain"),
            title=entry.get("title"),
        )


def _hex(digest: str) -> str:
    return digest.strip().lower().removeprefix("sha256:")


class CorpusManifest:
    """``samples/corpus/MANIFEST.json``: every file with its hash, sensitivity and flags."""

    def __init__(
        self, files: Iterable[CorpusFile], *, sha256: str = "", quickstart: Sequence[str] = ()
    ) -> None:
        self.files: dict[str, CorpusFile] = {entry.path: entry for entry in files}
        self.sha256 = sha256
        self.quickstart_paths: tuple[str, ...] = tuple(quickstart) or tuple(
            entry.path
            for entry in self.files.values()
            if entry.quickstart and entry.copy_of is None
        )
        self._by_sha: dict[str, str] = {}
        for entry in self.files.values():
            self._by_sha.setdefault(entry.sha256, entry.canonical)

    @classmethod
    def load(cls, corpus_root: Path) -> CorpusManifest:
        raw = (Path(corpus_root) / "MANIFEST.json").read_bytes()
        return cls.from_dict(
            json.loads(raw.decode("utf-8")), sha256=hashlib.sha256(raw).hexdigest()
        )

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, sha256: str = "") -> CorpusManifest:
        return cls(
            (CorpusFile.from_entry(entry) for entry in data.get("files") or []),
            sha256=sha256,
            quickstart=tuple(data.get("quickstart") or ()),
        )

    def get(self, path: str) -> CorpusFile | None:
        return self.files.get(path)

    def canonical(self, path: str) -> str | None:
        entry = self.files.get(path)
        return entry.canonical if entry else None

    def by_sha256(self, digest: str) -> str | None:
        """Canonical path of the file with this raw SHA-256 (``sha256:`` prefix accepted)."""
        return self._by_sha.get(_hex(digest))

    def sensitivity(self, path: str) -> str | None:
        entry = self.files.get(path)
        return entry.sensitivity if entry else None

    def documents(self) -> list[CorpusFile]:
        """Every distinct document (quickstart copies excluded)."""
        return [entry for entry in self.files.values() if entry.copy_of is None]

    def select(self, scope: str = "full", audience: str = "public") -> list[CorpusFile]:
        """Documents of a build: ``full`` (``full/``), ``quickstart`` (the MANIFEST list) or
        ``all`` (everything except held-back files), restricted to what ``audience`` may see."""
        if scope == "quickstart":
            paths = [self.canonical(path) or path for path in self.quickstart_paths]
        elif scope == "full":
            paths = [entry.path for entry in self.documents() if entry.path.startswith("full/")]
        elif scope == "all":
            paths = [entry.path for entry in self.documents() if not entry.held_back]
        else:
            raise ValueError(f"unknown corpus scope {scope!r}; use one of {', '.join(SCOPES)}")
        selected = (self.files[path] for path in dict.fromkeys(paths) if path in self.files)
        return [entry for entry in selected if allowed_for_audience(entry.sensitivity, audience)]


# ----------------------------------------------------------------------------- catalog


@dataclass(frozen=True)
class CatalogSourceRef:
    source_id: str
    path: str
    sha256: str | None = None
    title: str | None = None


@dataclass(frozen=True)
class ReleaseCatalog:
    """What the evaluator needs from a release ``catalog.json``: its sources."""

    release_id: str | None = None
    audience: str | None = None
    sources: tuple[CatalogSourceRef, ...] = ()

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> ReleaseCatalog:
        titles: dict[str, str] = {}
        for page in data.get("pages") or []:
            if page.get("type") != "source" or not page.get("title"):
                continue
            for source_id in page.get("sources") or [page.get("id")]:
                if source_id:
                    titles.setdefault(str(source_id), str(page["title"]))
        sources = tuple(
            CatalogSourceRef(
                source_id=str(source["source_id"]),
                path=str(source.get("path") or ""),
                sha256=_hex(str(source["hash"])) if source.get("hash") else None,
                title=titles.get(str(source["source_id"])),
            )
            for source in data.get("sources") or []
            if source.get("source_id")
        )
        return cls(
            release_id=data.get("release_id"), audience=data.get("audience"), sources=sources
        )

    @classmethod
    def load(cls, path: Path) -> ReleaseCatalog:
        """Read ``catalog.json``, a release folder, a ``releases/`` folder with ``current.json``
        or a folder containing ``releases/current.json``."""
        return cls.from_dict(json.loads(_catalog_file(Path(path)).read_text(encoding="utf-8")))


def _catalog_file(path: Path) -> Path:
    if path.is_file():
        return path
    for root in (path, path / "releases"):
        if (root / "catalog.json").is_file():
            return root / "catalog.json"
        pointer = root / "current.json"
        if pointer.is_file():
            release_id = json.loads(pointer.read_text(encoding="utf-8"))["release_id"]
            candidate = root / release_id / "catalog.json"
            if candidate.is_file():
                return candidate
    raise FileNotFoundError(f"no catalog.json found under {path.name or path}")


# ------------------------------------------------------------------------------ resolver


@dataclass(frozen=True)
class ResolvedCitation:
    """A citation mapped to the corpus: canonical path and locator key (``None`` if unknown)."""

    unit: str
    path: str | None
    locator_key: str | None
    via: str | None = None
    sensitivity: str | None = None

    @property
    def resolved(self) -> bool:
        return self.path is not None and self.locator_key is not None

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit": self.unit,
            "path": self.path,
            "locator_key": self.locator_key,
            "via": self.via,
            "sensitivity": self.sensitivity,
        }


_EXTRA_PREFIXES = ("samples/corpus/",)
_STRIP_PREFIXES = ("samples/corpus/", "raw/")


def _clean_path(path: str) -> str:
    value = unicodedata.normalize("NFC", path.strip().replace("\\", "/"))
    while value.startswith(("./", "/")):
        value = value[1:] if value.startswith("/") else value[2:]
    for prefix in _STRIP_PREFIXES:
        if value.startswith(prefix):
            value = value[len(prefix) :]
    return value


class SourceResolver:
    """Map cited sources to canonical corpus paths.

    Order: SHA-256 (MANIFEST hashes) → ``source_id`` (release catalog first, then ids derived
    from every MANIFEST path and its suffixes, which covers deployments whose raw container holds
    ``full/…`` or the files of ``full/`` directly) → raw path (exact, then a unique suffix match)
    → source title (catalog source pages, MANIFEST titles). The locator is the cited key, or the
    key parsed from the locator label.
    """

    def __init__(
        self,
        manifest: CorpusManifest,
        catalog: ReleaseCatalog | None = None,
        docs: Mapping[str, ExtractedDoc] | None = None,
    ) -> None:
        self.manifest = manifest
        self.catalog = catalog
        self._docs = docs or {}
        self._by_id = self._source_ids()
        self._by_title = self._titles()

    def _source_ids(self) -> dict[str, str]:
        derived: dict[str, set[str]] = {}
        for entry in self.manifest.files.values():
            segments = entry.path.split("/")
            suffixes = ["/".join(segments[index:]) for index in range(len(segments))]
            suffixes += [prefix + entry.path for prefix in _EXTRA_PREFIXES]
            for suffix in suffixes:
                derived.setdefault(source_id_for(suffix), set()).add(entry.canonical)
        mapping = {sid: next(iter(paths)) for sid, paths in derived.items() if len(paths) == 1}
        for source in self.catalog.sources if self.catalog else ():
            path = (self.manifest.by_sha256(source.sha256) if source.sha256 else None) or (
                self.path_for(source.path) if source.path else None
            )
            if path is not None:
                mapping[source.source_id] = path
        return mapping

    def _titles(self) -> dict[str, str]:
        candidates: dict[str, set[str]] = {}
        for entry in self.manifest.documents():
            if entry.title:
                candidates.setdefault(normalize_text(entry.title), set()).add(entry.canonical)
        for source in self.catalog.sources if self.catalog else ():
            path = self._by_id.get(source.source_id)
            if source.title and path:
                candidates.setdefault(normalize_text(source.title), set()).add(path)
        return {title: next(iter(paths)) for title, paths in candidates.items() if len(paths) == 1}

    def path_for(self, raw_path: str) -> str | None:
        """Canonical corpus path of a raw path (exact, else a unique suffix match)."""
        value = _clean_path(raw_path)
        if not value:
            return None
        exact = self.manifest.canonical(value)
        if exact is not None:
            return exact
        matches = {
            entry.canonical
            for path, entry in self.manifest.files.items()
            if path.endswith("/" + value)
        }
        return next(iter(matches)) if len(matches) == 1 else None

    def path_for_id(self, source_id: str) -> str | None:
        return self._by_id.get(source_id)

    def resolve(self, citation: Citation, *, unit: str) -> ResolvedCitation:
        path: str | None = None
        via: str | None = None
        attempts = (
            ("sha256", citation.sha256, self.manifest.by_sha256),
            ("source_id", citation.source_id, self._by_id.get),
            ("path", citation.source_path, self.path_for),
            ("title", citation.title, lambda title: self._by_title.get(normalize_text(title))),
        )
        for name, value, lookup in attempts:
            if value:
                path = lookup(value)
                if path is not None:
                    via = name
                    break
        key = citation.locator_key if is_key(citation.locator_key) else None
        if key is None and citation.label and path is not None:
            key = locator_key_from_label(citation.label, doc=self._docs.get(path))
        return ResolvedCitation(
            unit=unit,
            path=path,
            locator_key=key,
            via=via,
            sensitivity=self.manifest.sensitivity(path) if path else None,
        )


# -------------------------------------------------------------------------- extraction


class ExtractionCache:
    """ExtractedDocs of corpus files, extracted once with ``docwiki.extract.extract_source`` and
    cached as JSON under ``<cache_dir>/extract/<mode>-<adapter version>/``.

    ``local`` mode runs the deterministic local adapters (no OCR: scans and photos have empty
    text); ``azure`` mode uses Content Understanding for PDFs and images (``cu_endpoint`` is the
    Foundry endpoint). Figure descriptions are not generated.
    """

    def __init__(
        self,
        corpus_root: Path,
        cache_dir: Path | None,
        *,
        mode: ExtractMode = "local",
        cu_endpoint: str | None = None,
        concurrency: int = 4,
    ) -> None:
        if mode == "azure" and not cu_endpoint:
            raise ValueError("azure extraction needs the Foundry endpoint (cu_endpoint)")
        self.corpus_root = Path(corpus_root)
        self.cache_dir = Path(cache_dir) if cache_dir is not None else None
        self.mode = mode
        self.cu_endpoint = cu_endpoint
        self.concurrency = max(1, concurrency)

    def _settings(self) -> Any:
        from docwiki.engine_types import ExtractSettings

        return ExtractSettings(
            mode=self.mode,
            cu_endpoint=self.cu_endpoint,
            describe_figures=False,
            page_render_dpi=72,
        )

    def version(self) -> str:
        from docwiki.extract import ADAPTER_VERSION, CU_ADAPTER_VERSION

        return f"{self.mode}-{CU_ADAPTER_VERSION if self.mode == 'azure' else ADAPTER_VERSION}"

    async def load(self, files: Iterable[CorpusFile]) -> dict[str, ExtractedDoc]:
        """ExtractedDoc per canonical path (copies are extracted once, as their original)."""
        paths = list(dict.fromkeys(entry.canonical for entry in files))
        semaphore = asyncio.Semaphore(self.concurrency)

        async def one(path: str) -> tuple[str, ExtractedDoc]:
            async with semaphore:
                return path, await self._extract(path)

        return dict(await asyncio.gather(*(one(path) for path in paths)))

    async def _extract(self, rel_path: str) -> ExtractedDoc:
        from docwiki.extract import extract_source

        raw_file = self.corpus_root / rel_path
        data = await asyncio.to_thread(raw_file.read_bytes)
        cache_file = self._cache_file(rel_path, data)
        if cache_file is not None and cache_file.is_file():
            try:
                return ExtractedDoc.from_json(cache_file.read_bytes())
            except ValidationError:
                pass  # stale or damaged cache entry: extract again
        result = await extract_source(raw_file, rel_path=rel_path, settings=self._settings())
        if cache_file is not None:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            temporary = cache_file.with_suffix(f".{os.getpid()}.tmp")
            temporary.write_text(result.doc.to_json(), encoding="utf-8", newline="\n")
            temporary.replace(cache_file)
        return result.doc

    def _cache_file(self, rel_path: str, data: bytes) -> Path | None:
        if self.cache_dir is None:
            return None
        content = hashlib.sha256(data).hexdigest()[:32]
        where = hashlib.sha256(rel_path.encode("utf-8")).hexdigest()[:8]
        return self.cache_dir / "extract" / self.version() / f"{content}-{where}.json"


# ---------------------------------------------------------------------------- evidence


class EvidenceStore:
    """Extracted text behind a locator: the blocks (and figure captions) whose locator overlaps
    the cited one at metric granularity (a page, rows of a sheet, lines of a message...)."""

    def __init__(self, docs: Mapping[str, ExtractedDoc]) -> None:
        self._docs = dict(docs)
        self._entries: dict[str, list[tuple[str, str]]] = {}

    def __contains__(self, path: object) -> bool:
        return path in self._docs

    def doc(self, path: str) -> ExtractedDoc | None:
        return self._docs.get(path)

    def entries(self, path: str) -> list[tuple[str, str]] | None:
        """``(locator key, text)`` of every block and figure of a document."""
        if path not in self._docs:
            return None
        cached = self._entries.get(path)
        if cached is None:
            doc = self._docs[path]
            cached = [(block.locator_key, block.text) for block in doc.blocks]
            for figure in doc.figures:
                text = " ".join(part for part in (figure.caption, figure.description) if part)
                cached.append((locator_key(figure.locator), text))
            self._entries[path] = cached
        return cached

    def text(self, path: str, key: str) -> str | None:
        """Text behind ``key`` in ``path``; ``None`` when the document or the locator is unknown.

        OCR content extracted in local mode is empty: such a locator exists but has no text.
        """
        entries = self.entries(path)
        if entries is None:
            return None
        matched = [text for block_key, text in entries if keys_match(key, block_key)]
        if not matched:
            return None
        return "\n".join(text for text in matched if text)


def restricted_fingerprint(
    manifest: CorpusManifest, docs: Mapping[str, ExtractedDoc]
) -> frozenset[str]:
    """Distinctive values (numbers of four digits or more, codes) that occur in restricted
    sources and in no other source of the corpus: their presence in an answer reveals restricted
    content even without a citation."""
    restricted: set[str] = set()
    other: set[str] = set()
    for path, doc in docs.items():
        values = value_tokens(normalize_text(doc.text()))
        (restricted if manifest.sensitivity(path) == "restricted" else other).update(values)
    return frozenset(restricted - other)


# ------------------------------------------------------------------------------ context


@dataclass
class CorpusContext:
    """Everything the metrics need about the corpus, built once per run."""

    manifest: CorpusManifest
    docs: dict[str, ExtractedDoc]
    catalog: ReleaseCatalog | None = None
    evidence: EvidenceStore = field(init=False)
    resolver: SourceResolver = field(init=False)
    fingerprint: frozenset[str] = field(init=False)

    def __post_init__(self) -> None:
        self.evidence = EvidenceStore(self.docs)
        self.resolver = SourceResolver(self.manifest, self.catalog, self.docs)
        self.fingerprint = restricted_fingerprint(self.manifest, self.docs)


async def load_corpus(
    corpus_root: Path,
    *,
    cache_dir: Path | None,
    mode: ExtractMode = "local",
    cu_endpoint: str | None = None,
    catalog: ReleaseCatalog | None = None,
) -> CorpusContext:
    """MANIFEST plus the extracted text of every document of the corpus."""
    manifest = CorpusManifest.load(corpus_root)
    cache = ExtractionCache(corpus_root, cache_dir, mode=mode, cu_endpoint=cu_endpoint)
    docs = await cache.load(manifest.documents())
    return CorpusContext(manifest=manifest, docs=docs, catalog=catalog)
