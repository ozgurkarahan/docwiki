"""``validate_release``: structural checks of a release, reused by the quality gates.

Violations carry the gate they belong to (pipeline §7). Gates that need pipeline state (G04
quote verification, G15 extraction, G10 and G16 without pack knowledge) are left to the ``verify``
stage.
Structural/integrity problems of machine files (manifest, catalog, pointer, tables index, search
database) are reported under G01 (schema validity).
"""

from __future__ import annotations

import json
import re
import sqlite3
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from pathlib import Path

from pydantic import ValidationError

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.catalog import Catalog, catalog_page_for, catalog_source_for
from docwiki.contracts.enums import BADGES, allowed_for_audience, max_sensitivity
from docwiki.contracts.frontmatter import FrontmatterError
from docwiki.contracts.gates import Violation
from docwiki.contracts.i18n import MIRRORED_PAGE_TYPES, heading_variants, untranslated_marker
from docwiki.contracts.ids import (
    RELEASE_ID_RE,
    SOURCE_ID_RE,
    check_wiki_path,
    entity_page_path,
    hub_page_path,
    index_page_path,
    query_page_path,
    topic_page_path,
    view_page_path,
)
from docwiki.contracts.layout import (
    CORE_SKILLS,
    EVIDENCE_MOUNT,
    REQUIRED_WIKI_FILES,
    SKILL_PROJECTIONS,
    ReleaseFiles,
    WikiFiles,
)
from docwiki.contracts.locators import locator_key, locator_label, parse_locator_key
from docwiki.contracts.manifest import CurrentPointer, ReleaseManifest
from docwiki.contracts.markdown import (
    extract_footnotes,
    extract_headings,
    extract_links,
    resolve_href,
    split_sections,
    strip_backlinks_block,
)
from docwiki.contracts.pages import (
    EntityFrontmatter,
    EvidenceFrontmatter,
    EvidenceIndexFrontmatter,
    EvidencePage,
    HubFrontmatter,
    Page,
    QueryFrontmatter,
    SkillFile,
    SourceFrontmatter,
    TopicFrontmatter,
    ViewFrontmatter,
)
from docwiki.contracts.safety import find_violations
from docwiki.release.layout import PORTABLE_META_DIR, ReleaseLayout
from docwiki.release.tables import SourceTablesIndex
from docwiki.search.index import READABLE_SCHEMAS

__all__ = ["CITATION_RE", "validate_page", "validate_release"]

CITATION_RE = re.compile(
    r"^\[(?P<title>.+) — (?P<label>[^\]]+)\]\((?P<href>[^)\s]+)\) · (?P<badge>.+)$"
)
_BADGES_BY_PROVENANCE = {
    "native-text": {"✓ quote verified", "paraphrase", "generated description"},
    "deterministic-table": {"table"},
    "ocr": {"OCR", "generated description"},
    "model-description": {"generated description"},
}
_TEXT_SUFFIXES = (".md", ".json", ".txt")
_SAFETY_GATE = "G05"
_ANY_LANGUAGE_TYPES = frozenset({"query", "meta"})
"""Canonical pages that need not be in the canonical language (v1.7)."""


@dataclass
class _State:
    root: Path
    violations: list[Violation] = field(default_factory=list)
    audience: str | None = None
    release_id: str | None = None
    pages: dict[str, Page] = field(default_factory=dict)
    evidence: dict[str, EvidencePage] = field(default_factory=dict)
    headings: dict[str, set[str]] = field(default_factory=dict)
    catalog: Catalog | None = None
    offsets: dict[str, int] = field(default_factory=dict)
    cache: dict[Path, bytes] = field(default_factory=dict)
    layout: ReleaseLayout | None = None
    languages: list[str] = field(default_factory=lambda: ["en"])
    """The wiki languages (v1.7, ADR 0012), canonical first: from the manifest, else the
    catalog, else English only."""

    def canonical_pages(self) -> dict[str, Page]:
        """The canonical wiki (mirror pages left out), by wiki path."""
        return {rel: page for rel, page in self.pages.items() if not page.is_mirror}

    def trees(self) -> list[dict[str, Page]]:
        """The canonical wiki, then each mirror tree: pages by wiki path."""
        groups = [self.canonical_pages()]
        for lang in self.languages[1:]:
            groups.append(
                {
                    rel: page
                    for rel, page in self.pages.items()
                    if page.is_mirror and page.frontmatter.lang == lang
                }
            )
        return groups

    @property
    def lay(self) -> ReleaseLayout:
        if self.layout is None:  # pragma: no cover - set before any check runs
            raise RuntimeError("layout not resolved")
        return self.layout

    def wiki_display(self, wiki_rel: str) -> str:
        return self.lay.wiki_display(wiki_rel)

    def ns_display(self, ns_path: str) -> str:
        return self.lay.ns_display(ns_path)

    def read(self, path: Path) -> bytes:
        """File bytes, read once per validation (file system access dominates on Windows)."""
        data = self.cache.get(path)
        if data is None:
            data = path.read_bytes()
            self.cache[path] = data
        return data

    def add(
        self,
        gate: str,
        code: str,
        message: str,
        path: str | None = None,
        line: int | None = None,
        *,
        warning: bool = False,
    ) -> None:
        self.violations.append(
            Violation(
                gate=gate,  # type: ignore[arg-type]
                code=code,
                severity="warning" if warning else "error",
                path=path,
                line=line,
                message=message,
            )
        )


def _summarize(exc: ValidationError) -> str:
    parts = []
    for error in exc.errors(include_url=False)[:3]:
        loc = ".".join(str(item) for item in error.get("loc", ()))
        parts.append(f"{loc}: {error.get('msg')}" if loc else str(error.get("msg")))
    return "; ".join(parts)


def _read_text(state: _State, file: Path, rel: str) -> str | None:
    data = state.read(file)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        state.add("G01", "encoding", "file is not valid UTF-8", rel)
        return None
    if text.startswith("\ufeff"):
        state.add("G01", "encoding", "byte order mark is not allowed", rel)
    if "\r" in text:
        state.add("G01", "encoding", "CR line endings are not allowed (LF only)", rel)
    return text


def _resolve_root(
    path: Path, state: _State
) -> tuple[ReleaseLayout, CurrentPointer | None, str | None]:
    """Layout to validate, the pointer that selected it (if any) and the pointer's display path."""
    layout = ReleaseLayout.detect(path)
    if layout is not None:
        pointer_file = layout.pointer_path
        if pointer_file is None:
            return layout, None, None
        display = f"{PORTABLE_META_DIR}/current.json"
        try:
            return layout, CurrentPointer.from_json(state.read(pointer_file)), display
        except ValidationError as exc:
            state.add("G01", "pointer-invalid", _summarize(exc), display)
            return layout, None, None
    for releases in (path, path / "releases"):
        pointer_file = releases / "current.json"
        if not pointer_file.is_file():
            continue
        try:
            pointer = CurrentPointer.from_json(pointer_file.read_bytes())
        except ValidationError as exc:
            state.add("G01", "pointer-invalid", _summarize(exc), "current.json")
            return ReleaseLayout("release", path), None, None
        return ReleaseLayout("release", releases / pointer.release_id), pointer, "current.json"
    return ReleaseLayout("release", path), None, None


def _check_manifest(
    state: _State, pointer: CurrentPointer | None, pointer_display: str | None, require: bool
) -> ReleaseManifest | None:
    layout = state.lay
    file = layout.manifest_path
    shown = layout.display(ReleaseFiles.MANIFEST)
    if not file.is_file():
        if require:
            state.add("G01", "manifest-missing", "manifest.json is missing", shown)
        return None
    data = state.read(file)
    try:
        manifest = ReleaseManifest.from_json(data)
    except ValidationError as exc:
        state.add("G01", "manifest-invalid", _summarize(exc), shown)
        return None
    if (
        not layout.portable
        and RELEASE_ID_RE.match(layout.root.name)
        and layout.root.name != manifest.release_id
    ):
        state.add(
            "G01",
            "release-id-mismatch",
            f"folder {layout.root.name} holds {manifest.release_id}",
            shown,
        )
    if pointer is not None:
        where = pointer_display or "current.json"
        if pointer.release_id != manifest.release_id:
            state.add(
                "G01",
                "pointer-release-mismatch",
                f"pointer names {pointer.release_id}, manifest holds {manifest.release_id}",
                where,
            )
        if pointer.manifest_sha256 != sha256_hex(data):
            state.add(
                "G01",
                "pointer-hash-mismatch",
                "manifest_sha256 does not match manifest.json",
                where,
            )
        if pointer.audience != manifest.audience:
            state.add(
                "G01",
                "pointer-audience-mismatch",
                "pointer audience differs from the manifest",
                where,
            )
    for rel, entry in manifest.files.items():
        target = layout.file_for(rel)
        if target is None:
            continue
        if not target.is_file():
            state.add(
                "G01", "file-missing", "listed in manifest.json but missing", layout.display(rel)
            )
            continue
        content = state.read(target)
        if sha256_hex(content) != entry.sha256 or len(content) != entry.size:
            state.add(
                "G01",
                "file-hash-mismatch",
                "content does not match manifest.json",
                layout.display(rel),
            )
    listed = set(manifest.files)
    for owned in layout.owned_files():
        rel = layout.release_rel_of(owned)
        if rel is None or rel in listed:
            continue
        if (
            layout.portable
            and rel == f"{ReleaseFiles.WIKI_DIR}/{ReleaseFiles.CATALOG}"
            and (ReleaseFiles.CATALOG in listed)
        ):
            continue
        state.add(
            "G01",
            "file-unlisted",
            "file is not listed in manifest.json",
            owned.relative_to(layout.root).as_posix(),
        )
    for gate in manifest.blocking_failures:
        state.add(
            gate.gate,
            "gate-failed",
            f"manifest records a failing blocking gate {gate.gate} ({gate.name})",
            shown,
        )
    return manifest


def _expected_page_path(page: Page) -> str | None:
    fm = page.frontmatter
    if fm.translation_of is not None:
        # a mirror page (v1.7, ADR 0012): the canonical path under <lang>/
        prefix = f"{fm.lang}/"
        if not page.path.startswith(prefix):
            return None
        canonical = Page(path=page.path[len(prefix) :], frontmatter=fm, body="")
        expected = _expected_canonical_path(canonical)
        return f"{prefix}{expected}" if expected else None
    return _expected_canonical_path(page)


def _expected_canonical_path(page: Page) -> str | None:
    fm = page.frontmatter
    if isinstance(fm, SourceFrontmatter):
        return (
            page.path
            if re.match(r"^sources/[a-z0-9]+(?:-[a-z0-9]+)*\.md$", page.path)
            and page.path != WikiFiles.SOURCES_INDEX
            else None
        )
    if isinstance(fm, EntityFrontmatter):
        return entity_page_path(fm.id)
    if isinstance(fm, TopicFrontmatter):
        return topic_page_path(fm.id)
    if isinstance(fm, HubFrontmatter):
        return hub_page_path(fm.id)
    if isinstance(fm, ViewFrontmatter):
        return view_page_path(fm.id)
    if isinstance(fm, QueryFrontmatter):
        return query_page_path(fm.id)
    if fm.type == "index":
        return index_page_path(fm.id.removeprefix("index:"))
    if fm.type == "glossary":
        return WikiFiles.GLOSSARY
    if fm.type == "log":
        return WikiFiles.LOG
    name = fm.id.removeprefix("meta:")
    return WikiFiles.AGENTS if name == "agents" else f"_meta/{name}.md"


def _is_skill_path(rel: str) -> bool:
    return any(rel.startswith(f"{projection}/") for projection in SKILL_PROJECTIONS)


def _load_wiki(state: _State) -> None:
    wiki = state.lay.wiki_root
    if not wiki.is_dir():
        state.add("G01", "wiki-missing", "wiki/ folder is missing", state.wiki_display(""))
        return
    for required in REQUIRED_WIKI_FILES:
        if not (wiki / required).is_file():
            state.add(
                "G01",
                "required-file-missing",
                f"required wiki file {required} is missing",
                state.wiki_display(required),
            )
    if not state.lay.portable and (wiki / EVIDENCE_MOUNT).exists():
        state.add(
            "G09", "reserved-path", "'evidence' is reserved at the wiki root", "wiki/evidence"
        )
    for rel, file in state.lay.wiki_files():
        problem = check_wiki_path(rel)
        if problem:
            state.add("G09", "path-invalid", problem, state.wiki_display(rel))
        if not rel.endswith(".md") or _is_skill_path(rel):
            continue
        text = _read_text(state, file, state.wiki_display(rel))
        if text is None:
            continue
        try:
            page = Page.parse(text, rel)
        except FrontmatterError as exc:
            state.add("G01", "frontmatter-invalid", str(exc), state.wiki_display(rel))
            continue
        except ValidationError as exc:
            gate = (
                "G12"
                if any(err.get("loc", ())[1:2] == ("tags",) for err in exc.errors())
                else "G01"
            )
            state.add(gate, "frontmatter-invalid", _summarize(exc), state.wiki_display(rel))
            continue
        state.pages[rel] = page
        state.offsets[rel] = text[: len(text) - len(page.body)].count("\n")
        _check_page_lang(state, page, rel)
        expected = _expected_page_path(page)
        if expected != rel:
            state.add(
                "G09",
                "page-path-mismatch",
                f"{page.frontmatter.id} should live at {expected}",
                state.wiki_display(rel),
            )
        if state.release_id and page.frontmatter.docwiki.release != state.release_id:
            state.add(
                "G01",
                "stamp-mismatch",
                f"docwiki.release must be {state.release_id}",
                state.wiki_display(rel),
            )
        if state.audience and not allowed_for_audience(
            page.frontmatter.sensitivity, state.audience
        ):
            state.add(
                "G07",
                "page-above-audience",
                f"{page.frontmatter.sensitivity} page in a {state.audience} build",
                state.wiki_display(rel),
            )
        state.headings[rel] = {heading.anchor for heading in extract_headings(page.body)}


def _check_page_lang(state: _State, page: Page, rel: str) -> None:
    """A canonical page is in the canonical language (a filed research answer keeps the language
    it was filed in, the agent files and run pages are English); a mirror page is in one of the
    mirror languages (v1.7, ADR 0012)."""
    fm = page.frontmatter
    shown = state.wiki_display(rel)
    if fm.translation_of is not None:
        if fm.lang not in state.languages[1:]:
            state.add(
                "G01",
                "page-lang",
                f"mirror page in {fm.lang!r}, not a mirror language of this wiki {state.languages}",
                shown,
            )
    elif fm.lang != state.languages[0] and fm.type not in _ANY_LANGUAGE_TYPES:
        state.add(
            "G01",
            "page-lang",
            f"canonical page in {fm.lang!r}; the wiki is written in {state.languages[0]!r}",
            shown,
        )


def _load_evidence(state: _State, source_ids: set[str] | None) -> None:
    base = state.lay.evidence_root
    if not base.is_dir():
        return
    for file in sorted(p for p in base.rglob("*") if p.is_file()):
        ns = f"{EVIDENCE_MOUNT}/{file.relative_to(base).as_posix()}"
        problem = check_wiki_path(ns)
        if problem:
            state.add("G09", "path-invalid", problem, ns)
        parts = ns.split("/")
        if len(parts) < 3 or not SOURCE_ID_RE.match(parts[1]):
            state.add("G09", "evidence-path-invalid", "evidence lives in evidence/<source_id>/", ns)
            continue
        if source_ids is not None and parts[1] not in source_ids:
            state.add("G07", "evidence-unknown-source", f"no source {parts[1]} in this release", ns)
        if not ns.endswith(".md"):
            continue
        text = _read_text(state, file, ns)
        if text is None:
            continue
        try:
            page = EvidencePage.parse(text, ns)
        except (FrontmatterError, ValidationError) as exc:
            message = _summarize(exc) if isinstance(exc, ValidationError) else str(exc)
            state.add("G01", "evidence-invalid", message, ns)
            continue
        fm = page.frontmatter
        if fm.source_id != parts[1]:
            state.add(
                "G01",
                "evidence-source-mismatch",
                "frontmatter source_id differs from its folder",
                ns,
            )
        if isinstance(fm, EvidenceIndexFrontmatter):
            if len(parts) != 3 or parts[2] != "index.md":
                state.add(
                    "G09",
                    "evidence-path-invalid",
                    "evidence index must be evidence/<source_id>/index.md",
                    ns,
                )
        elif len(parts) != 3 or parts[2] != f"{locator_key(fm.locator)}.md":
            state.add(
                "G09",
                "evidence-path-invalid",
                f"sidecar must be named {locator_key(fm.locator)}.md",
                ns,
            )
        if state.audience and not allowed_for_audience(fm.sensitivity, state.audience):
            state.add(
                "G07",
                "evidence-above-audience",
                f"{fm.sensitivity} evidence in a {state.audience} build",
                ns,
            )
        state.evidence[ns] = page
        state.offsets[ns] = text[: len(text) - len(page.body)].count("\n")
        state.headings[ns] = {heading.anchor for heading in extract_headings(page.body)}


def _content_file(state: _State, ns_path: str) -> Path:
    return state.lay.content_file(ns_path)


def _release_rel(state: _State, ns_path: str) -> str:
    """Reported path of a content-namespace path (``wiki/…`` in a release folder)."""
    return state.ns_display(ns_path)


def _check_links(state: _State, ns_path: str, body: str, inbound: dict[str, set[str]]) -> None:
    rel = _release_rel(state, ns_path)
    offset = state.offsets.get(ns_path, 0)
    for link in extract_links(body):
        line = link.line + offset
        resolved = resolve_href(ns_path, link.href)
        if resolved.external:
            continue  # reported by the safety check (G05)
        if resolved.error or resolved.path is None:
            state.add("G02", "link-invalid", f"{link.href!r}: {resolved.error}", rel, line)
            continue
        target = _content_file(state, resolved.path)
        if not target.is_file():
            state.add("G02", "link-unresolved", f"{link.href!r} does not resolve", rel, line)
            continue
        if resolved.anchor and resolved.path.endswith(".md"):
            anchors = state.headings.get(resolved.path)
            if anchors is None:
                text = state.read(target).decode("utf-8", errors="replace")
                anchors = {h.anchor for h in extract_headings(text)}
                state.headings[resolved.path] = anchors
            if resolved.anchor not in anchors:
                state.add(
                    "G02",
                    "anchor-unresolved",
                    f"{link.href!r}: no heading #{resolved.anchor}",
                    rel,
                    line,
                )
    for link in extract_links(strip_backlinks_block(body)):
        target_path = resolve_href(ns_path, link.href).path
        if target_path and target_path != ns_path and _content_file(state, target_path).is_file():
            inbound.setdefault(target_path, set()).add(ns_path)


def _check_footnotes(
    state: _State, ns_path: str, page: Page, source_titles: dict[str, str]
) -> None:
    rel = _release_rel(state, ns_path)
    offset = state.offsets.get(ns_path, 0)
    raw_refs, raw_defs = extract_footnotes(page.body)
    refs = [(label, line + offset) for label, line in raw_refs]
    defs = [replace(definition, line=definition.line + offset) for definition in raw_defs]
    defined: dict[str, int] = {}
    for definition in defs:
        if definition.label in defined:
            state.add(
                "G02",
                "footnote-duplicate",
                f"footnote [^{definition.label}] defined twice",
                rel,
                definition.line,
            )
        defined[definition.label] = definition.line
    order: list[str] = []
    for label, line in refs:
        if label not in defined:
            state.add(
                "G02", "footnote-undefined", f"footnote [^{label}] has no definition", rel, line
            )
        if label not in order:
            order.append(label)
    for label, line in defined.items():
        if label not in order:
            state.add(
                "G02", "footnote-unused", f"footnote [^{label}] is never referenced", rel, line
            )
    expected = [f"c{index}" for index in range(1, len(order) + 1)]
    if order != expected:
        state.add(
            "G03",
            "footnote-order",
            f"footnote labels must be c1..cN in order of first use, got {order}",
            rel,
        )
    for definition in defs:
        match = CITATION_RE.match(definition.content)
        if not match:
            state.add(
                "G03",
                "citation-format",
                "footnote must be '[<title> — <label>](<sidecar>) · <badge>'",
                rel,
                definition.line,
            )
            continue
        badge = match.group("badge")
        if badge not in BADGES:
            state.add(
                "G03", "citation-badge", f"unknown provenance badge {badge!r}", rel, definition.line
            )
        resolved = resolve_href(ns_path, match.group("href"))
        if (
            resolved.path is None
            or not resolved.path.startswith(f"{EVIDENCE_MOUNT}/")
            or resolved.anchor
        ):
            state.add(
                "G06",
                "citation-target",
                "citations must link to an evidence sidecar",
                rel,
                definition.line,
            )
            continue
        sidecar = state.evidence.get(resolved.path)
        if sidecar is None or not isinstance(sidecar.frontmatter, EvidenceFrontmatter):
            state.add(
                "G06",
                "sidecar-missing",
                f"no evidence sidecar {resolved.path}",
                rel,
                definition.line,
            )
            continue
        fm = sidecar.frontmatter
        if match.group("label") != locator_label(fm.locator):
            state.add(
                "G03",
                "citation-label",
                f"label must be {locator_label(fm.locator)!r}",
                rel,
                definition.line,
            )
        if badge in BADGES and badge not in _BADGES_BY_PROVENANCE[fm.provenance]:
            state.add(
                "G03",
                "citation-badge",
                f"badge {badge!r} is not honest for {fm.provenance} evidence",
                rel,
                definition.line,
            )
        title = source_titles.get(fm.source_id)
        if title is not None and match.group("title") != title:
            state.add(
                "G03",
                "citation-title",
                f"citation title must be the source title {title!r}",
                rel,
                definition.line,
            )


def _check_cited_lists(state: _State, ns_path: str, page: Page) -> None:
    fm = page.frontmatter
    wanted = (
        set(heading_variants("key_facts"))
        if isinstance(fm, SourceFrontmatter)
        else heading_variants("facts") | heading_variants("timeline")
        if isinstance(fm, EntityFrontmatter)
        else set()
    )
    if not wanted:
        return
    base = state.offsets.get(ns_path, 0)
    for section in split_sections(page.body):
        if section.heading not in wanted:
            continue
        first = section.line_start + 1 + base
        for number, line in enumerate(section.markdown.split("\n"), start=first):
            if re.match(r"^\s*(?:[-*+]|\d+[.)])\s+\S", line) and "[^" not in line:
                state.add(
                    "G03",
                    "fact-uncited",
                    f"item under '{section.heading}' has no citation",
                    _release_rel(state, ns_path),
                    number,
                )


def _check_catalog(state: _State, manifest: ReleaseManifest | None) -> None:
    root_file = state.lay.catalog_path
    wiki_file = state.lay.wiki_root / WikiFiles.CATALOG
    if not root_file.is_file():
        state.add("G01", "catalog-missing", "catalog.json is missing", ReleaseFiles.CATALOG)
        return
    data = state.read(root_file)
    if wiki_file != root_file and wiki_file.is_file() and state.read(wiki_file) != data:
        state.add(
            "G01",
            "catalog-copy-mismatch",
            "wiki/catalog.json must equal catalog.json",
            state.wiki_display(WikiFiles.CATALOG),
        )
    try:
        catalog = Catalog.from_json(data)
    except ValidationError as exc:
        state.add("G01", "catalog-invalid", _summarize(exc), ReleaseFiles.CATALOG)
        return
    state.catalog = catalog
    if catalog.wiki_languages != state.languages:
        state.add(
            "G01",
            "catalog-languages",
            f"catalog wiki_languages {catalog.wiki_languages} differ from {state.languages}",
            ReleaseFiles.CATALOG,
        )
    if state.release_id and catalog.release_id != state.release_id:
        state.add(
            "G01",
            "catalog-release",
            "catalog release_id differs from the manifest",
            ReleaseFiles.CATALOG,
        )
    if state.audience and catalog.audience != state.audience:
        state.add(
            "G01",
            "catalog-audience",
            "catalog audience differs from the manifest",
            ReleaseFiles.CATALOG,
        )
    by_path = catalog.page_by_path()
    for path, page in state.pages.items():
        entry = by_path.get(path)
        expected = catalog_page_for(page.frontmatter, path)
        if entry is None:
            state.add(
                "G01",
                "catalog-page-missing",
                f"{page.frontmatter.id} is not in catalog.json",
                state.wiki_display(path),
            )
        elif entry != expected:
            fields = [
                name
                for name in type(entry).model_fields
                if getattr(entry, name) != getattr(expected, name)
            ]
            state.add(
                "G01",
                "catalog-page-mismatch",
                f"catalog entry differs in {fields}",
                state.wiki_display(path),
            )
    for path in sorted(set(by_path) - set(state.pages)):
        state.add(
            "G01",
            "catalog-page-unknown",
            f"catalog lists {path} but the page is missing",
            ReleaseFiles.CATALOG,
        )
    for entry in catalog.pages:
        if state.audience and not allowed_for_audience(entry.sensitivity, state.audience):
            state.add(
                "G07",
                "catalog-above-audience",
                f"{entry.id} is {entry.sensitivity}",
                ReleaseFiles.CATALOG,
            )
    canonical = state.canonical_pages()
    expected_sources = {
        page.frontmatter.source_id: catalog_source_for(page.frontmatter)
        for page in canonical.values()
        if isinstance(page.frontmatter, SourceFrontmatter)
    }
    actual_sources = {source.source_id: source for source in catalog.sources}
    for source_id in sorted(set(expected_sources) | set(actual_sources)):
        if expected_sources.get(source_id) != actual_sources.get(source_id):
            state.add(
                "G01",
                "catalog-source-mismatch",
                f"catalog source {source_id} differs from its page",
                ReleaseFiles.CATALOG,
            )
    if manifest is not None and manifest.inputs.sources:
        for source_id, source in actual_sources.items():
            recorded = manifest.inputs.sources.get(source_id)
            if recorded is None:
                state.add(
                    "G07",
                    "source-not-in-inputs",
                    f"{source_id} is not an input of this build",
                    ReleaseFiles.CATALOG,
                )
            elif recorded != source.hash:
                state.add(
                    "G01",
                    "source-hash-mismatch",
                    f"{source_id} hash differs from manifest inputs",
                    ReleaseFiles.CATALOG,
                )
    edges = {(edge.from_, edge.to, edge.kind) for edge in catalog.edges}
    page_ids = {page.frontmatter.id: page for page in canonical.values()}
    tiers = {page_id: page.frontmatter.sensitivity for page_id, page in page_ids.items()}
    for page in state.pages.values():
        fm = page.frontmatter
        rel = state.wiki_display(page.path)
        if page.is_mirror:
            # edges are the canonical wiki's; a mirror page's sources are checked all the same
            _check_page_sources(state, page, tiers, rel)
            continue
        if isinstance(fm, SourceFrontmatter):
            for entity_id in fm.entities:
                if entity_id not in page_ids:
                    state.add("G02", "entity-page-missing", f"{entity_id} has no page", rel)
                elif (fm.id, entity_id, "mentions") not in edges:
                    state.add(
                        "G01",
                        "edge-missing",
                        f"missing edge {fm.id} mentions {entity_id}",
                        ReleaseFiles.CATALOG,
                    )
            for topic_id in fm.topics:
                if topic_id not in page_ids:
                    state.add("G02", "topic-page-missing", f"{topic_id} has no page", rel)
            for other in (*fm.supersedes, *fm.superseded_by):
                if other not in page_ids:
                    state.add(
                        "G02", "source-ref-missing", f"{other} has no page in this release", rel
                    )
            for older in fm.supersedes:
                if older in page_ids and (fm.id, older, "supersedes") not in edges:
                    state.add(
                        "G01",
                        "edge-missing",
                        f"missing edge {fm.id} supersedes {older}",
                        ReleaseFiles.CATALOG,
                    )
        _check_page_sources(state, page, tiers, rel)
        if isinstance(fm, TopicFrontmatter):
            for source_id in fm.sources:
                if source_id in page_ids and (fm.id, source_id, "topic-of") not in edges:
                    state.add(
                        "G01",
                        "edge-missing",
                        f"missing edge {fm.id} topic-of {source_id}",
                        ReleaseFiles.CATALOG,
                    )
    glossary_anchors = state.headings.get(WikiFiles.GLOSSARY, set())
    for entry in catalog.glossary:
        anchor = entry.page.split("#", 1)[1]
        if anchor not in glossary_anchors:
            state.add(
                "G02", "glossary-anchor", f"{entry.page} does not resolve", ReleaseFiles.CATALOG
            )


def _check_page_sources(state: _State, page: Page, tiers: Mapping[str, str], rel: str) -> None:
    """The ``sources`` of an entity, topic, hub, view or query page have a page in the release
    (G02) and the page tier is their highest tier (G07); ``tiers`` maps page ids to their
    sensitivity."""
    fm = page.frontmatter
    if not isinstance(
        fm,
        EntityFrontmatter | TopicFrontmatter | HubFrontmatter | ViewFrontmatter | QueryFrontmatter,
    ):
        return
    found: list[str] = []
    for source_id in fm.sources:
        tier = tiers.get(source_id)
        if tier is None:
            state.add("G02", "source-ref-missing", f"{source_id} has no page in this release", rel)
        else:
            found.append(tier)
    if found and fm.sensitivity != max_sensitivity(*found):
        state.add("G07", "page-tier", "page sensitivity must be the maximum of its sources", rel)


def _intro_targets(page: Page) -> set[str | None]:
    """Link targets before the first level-2 heading (title, banner and summary)."""
    intro: list[str] = []
    for section in split_sections(page.body):
        if section.level >= 2:
            break
        intro.append(section.markdown)
    return {resolve_href(page.path, link.href).path for link in extract_links("\n".join(intro))}


def _check_supersession(state: _State) -> None:
    for tree in state.trees():
        _check_supersession_tree(state, tree)


def _check_supersession_tree(state: _State, tree: Mapping[str, Page]) -> None:
    """G11 within one language tree (the canonical wiki or one mirror)."""
    sources: dict[str, tuple[Page, SourceFrontmatter]] = {
        page.frontmatter.id: (page, page.frontmatter)
        for page in tree.values()
        if isinstance(page.frontmatter, SourceFrontmatter)
    }
    for page, fm in sources.values():
        rel = state.wiki_display(page.path)
        for newer_id in fm.superseded_by:
            if newer_id not in sources:
                continue
            newer_page, newer_fm = sources[newer_id]
            if fm.id not in newer_fm.supersedes:
                state.add(
                    "G11",
                    "supersession-asymmetric",
                    f"{newer_id} must list {fm.id} in supersedes",
                    rel,
                )
            if fm.status == "superseded" and newer_page.path not in _intro_targets(page):
                state.add(
                    "G11",
                    "superseded-banner",
                    f"superseded page must link to {newer_page.path} before its sections",
                    rel,
                )
        for older_id in fm.supersedes:
            if older_id not in sources:
                continue
            _, older_fm = sources[older_id]
            if fm.id not in older_fm.superseded_by:
                state.add(
                    "G11",
                    "supersession-asymmetric",
                    f"{older_id} must list {fm.id} in superseded_by",
                    rel,
                )
            if older_fm.status != "superseded":
                state.add(
                    "G11", "superseded-status", f"{older_id} must have status superseded", rel
                )
    for page in tree.values():
        topic = page.frontmatter
        if not isinstance(topic, TopicFrontmatter):
            continue
        headings = {section.heading for section in split_sections(page.body)}
        if topic.superseded_claims and not headings & heading_variants("superseded"):
            state.add(
                "G11",
                "superseded-section",
                "topic with superseded claims needs '## Superseded information'",
                state.wiki_display(page.path),
            )
        if topic.contradictions and not headings & heading_variants("contradictions"):
            state.add(
                "G11",
                "contradictions-section",
                "topic with contradictions needs '## Contradictions'",
                state.wiki_display(page.path),
            )


def _check_skills(state: _State) -> None:
    wiki = state.lay.wiki_root
    projections: dict[str, dict[str, bytes]] = {}
    for projection in SKILL_PROJECTIONS:
        base = wiki / projection
        files = (
            {p.relative_to(base).as_posix(): state.read(p) for p in base.rglob("*") if p.is_file()}
            if base.is_dir()
            else {}
        )
        projections[projection] = files
    canonical = projections[SKILL_PROJECTIONS[0]]
    for projection in SKILL_PROJECTIONS[1:]:
        if projections[projection] != canonical:
            differing = sorted(set(projections[projection]) ^ set(canonical)) or sorted(
                name for name in canonical if projections[projection].get(name) != canonical[name]
            )
            state.add(
                "G14",
                "skills-projection-mismatch",
                f"{projection} differs from {SKILL_PROJECTIONS[0]}: {differing[:5]}",
                state.wiki_display(projection),
            )
    names = sorted({name.split("/", 1)[0] for name in canonical})
    for core in CORE_SKILLS:
        if core not in names:
            state.add(
                "G14",
                "core-skill-missing",
                f"core skill {core} is missing",
                state.wiki_display(SKILL_PROJECTIONS[0]),
            )
    for name in names:
        rel = state.wiki_display(f"{SKILL_PROJECTIONS[0]}/{name}/SKILL.md")
        content = canonical.get(f"{name}/SKILL.md")
        if content is None:
            state.add("G14", "skill-invalid", "skill folder without SKILL.md", rel)
            continue
        extras = sorted(
            path for path in canonical if path.startswith(f"{name}/") and path != f"{name}/SKILL.md"
        )
        if extras:
            state.add("G14", "skill-extra-file", f"unexpected files {extras}", rel)
        try:
            SkillFile.parse(content.decode("utf-8"), name)
        except (FrontmatterError, ValidationError, ValueError, UnicodeDecodeError) as exc:
            message = _summarize(exc) if isinstance(exc, ValidationError) else str(exc)
            state.add("G14", "skill-invalid", message, rel)


def _check_safety(state: _State, canaries: Sequence[str]) -> None:
    layout = state.lay
    plain = {WikiFiles.AGENTS, WikiFiles.LLMS}
    files: list[tuple[str, Path, bool]] = [
        (state.wiki_display(rel), path, not _is_skill_path(rel) and rel not in plain)
        for rel, path in layout.wiki_files()
    ]
    evidence = layout.evidence_root
    if evidence.is_dir():
        files += [
            (f"{EVIDENCE_MOUNT}/{p.relative_to(evidence).as_posix()}", p, False)
            for p in sorted(evidence.rglob("*"))
            if p.is_file()
        ]
    for shown, file, allow_markers in files:
        if not shown.endswith((".md", ".txt")):
            continue
        try:
            text = state.read(file).decode("utf-8")
        except UnicodeDecodeError:
            continue
        for finding in find_violations(text, allow_markers=allow_markers):
            state.add(
                _SAFETY_GATE,
                finding.kind,
                finding.message + (f": {finding.excerpt}" if finding.excerpt else ""),
                shown,
                finding.line,
            )
    if canaries:
        texts = [(shown, file) for shown, file, _ in files if shown.endswith(_TEXT_SUFFIXES)]
        if layout.catalog_path not in {file for _, file in texts}:
            texts.append((layout.display(ReleaseFiles.CATALOG), layout.catalog_path))
        site = layout.site_root
        if site is not None and site.is_dir():
            texts += [
                (p.relative_to(layout.root).as_posix(), p) for p in site.rglob("*") if p.is_file()
            ]
        for shown, file in texts:
            if not file.is_file():
                continue
            content = state.read(file).decode("utf-8", errors="ignore")
            for canary in canaries:
                if canary and canary in content:
                    state.add("G08", "canary-present", "injection canary found", shown)


def _check_llms(state: _State, inbound: dict[str, set[str]]) -> None:
    file = state.lay.wiki_root / WikiFiles.LLMS
    if not file.is_file():
        return
    text = state.read(file).decode("utf-8", errors="replace")
    lines = text.split("\n")
    if not lines or not lines[0].startswith("# "):
        state.add(
            "G01",
            "llms-format",
            "llms.txt must start with '# <title>'",
            state.wiki_display(WikiFiles.LLMS),
        )
    if "## Start here" not in lines:
        state.add(
            "G01",
            "llms-format",
            "llms.txt needs a '## Start here' section",
            state.wiki_display(WikiFiles.LLMS),
        )
    _check_links(state, WikiFiles.LLMS, text, inbound)


def _check_search_db(state: _State) -> None:
    path = state.lay.search_db_path
    shown = state.lay.display(ReleaseFiles.SEARCH_DB)
    if not path.is_file():
        state.add("G01", "search-missing", "search.db is missing", shown)
        return
    try:
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    except sqlite3.Error as exc:
        state.add("G01", "search-invalid", str(exc), shown)
        return
    try:
        tables = {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        missing = {"docs", "synonyms", "meta", "pages", "page_refs"} - tables
        if missing:
            state.add("G01", "search-schema", f"missing tables {sorted(missing)}", shown)
            return
        meta = dict(conn.execute("SELECT key, value FROM meta"))
        if meta.get("schema") not in READABLE_SCHEMAS:
            accepted = " or ".join(f"'{value}'" for value in sorted(READABLE_SCHEMAS))
            state.add("G01", "search-schema", f"meta.schema must be {accepted}", shown)
        if state.release_id and meta.get("release_id") != state.release_id:
            state.add(
                "G01",
                "search-release",
                "meta.release_id differs from the manifest",
                shown,
            )
        if state.audience and meta.get("audience") != state.audience:
            state.add(
                "G01",
                "search-audience",
                "meta.audience differs from the manifest",
                shown,
            )
        page_ids = {page.frontmatter.id for page in state.pages.values()}
        source_ids = {
            page.frontmatter.source_id
            for page in state.pages.values()
            if isinstance(page.frontmatter, SourceFrontmatter)
        }
        for rowid, page_id, source_id, sensitivity in conn.execute(
            "SELECT rowid, page_id, source_id, sensitivity FROM docs ORDER BY rowid"
        ):
            if page_id not in page_ids:
                state.add(
                    "G01",
                    "search-row-page",
                    f"row {rowid} references unknown page {page_id}",
                    shown,
                )
            if source_id is not None and source_id not in source_ids:
                state.add(
                    "G07",
                    "search-row-source",
                    f"row {rowid} references unknown source {source_id}",
                    shown,
                )
            if state.audience and (
                sensitivity is None or not allowed_for_audience(sensitivity, state.audience)
            ):
                state.add(
                    "G07",
                    "search-row-above-audience",
                    f"row {rowid} is {sensitivity}",
                    shown,
                )
    except sqlite3.Error as exc:
        state.add("G01", "search-invalid", str(exc), shown)
    finally:
        conn.close()


def _check_tables(state: _State, source_ids: set[str]) -> None:
    base = state.lay.tables_root
    if not base.is_dir():
        return
    for folder in sorted(p for p in base.iterdir()):
        rel = folder.relative_to(state.lay.root).as_posix()
        if not folder.is_dir() or not SOURCE_ID_RE.match(folder.name):
            state.add("G09", "tables-path-invalid", "tables live in tables/<source_id>/", rel)
            continue
        if folder.name not in source_ids:
            state.add(
                "G07", "tables-unknown-source", f"no source {folder.name} in this release", rel
            )
        index_file = folder / "index.json"
        if not index_file.is_file():
            state.add("G01", "tables-index-missing", "index.json is missing", rel)
            continue
        try:
            index = SourceTablesIndex.from_json(state.read(index_file))
        except ValidationError as exc:
            state.add("G01", "tables-index-invalid", _summarize(exc), f"{rel}/index.json")
            continue
        if index.source_id != folder.name:
            state.add(
                "G01",
                "tables-index-invalid",
                "source_id differs from its folder",
                f"{rel}/index.json",
            )
        if state.audience and not allowed_for_audience(index.sensitivity, state.audience):
            state.add(
                "G07",
                "tables-above-audience",
                f"{index.sensitivity} tables in a {state.audience} build",
                rel,
            )
        expected = {"index.json", *(entry.file for entry in index.tables)}
        present = {p.name for p in folder.iterdir() if p.is_file()}
        for name in sorted(expected - present):
            state.add("G01", "table-file-missing", f"{name} is missing", f"{rel}/{name}")
        for name in sorted(present - expected):
            state.add("G01", "table-file-unlisted", f"{name} is not in index.json", f"{rel}/{name}")
        for entry in index.tables:
            if entry.row_count != len(entry.row_ids) or len(set(entry.row_ids)) != len(
                entry.row_ids
            ):
                state.add(
                    "G01",
                    "tables-index-invalid",
                    f"{entry.id}: row_ids inconsistent",
                    f"{rel}/index.json",
                )


def _check_mirrors(state: _State) -> None:
    """G17 (v1.7, ADR 0012): every canonical page of a mirrored type has its mirror in each
    other wiki language (warning when it is missing or was kept untranslated); a mirror page
    always translates a canonical page of the same path (error)."""
    mirrors = state.languages[1:]
    if not mirrors:
        return
    canonical = state.canonical_pages()
    for rel, page in sorted(state.pages.items()):
        fm = page.frontmatter
        if not page.is_mirror:
            continue
        original = canonical.get(rel.removeprefix(f"{fm.lang}/"))
        if original is None or original.frontmatter.id != fm.translation_of:
            state.add(
                "G01",
                "mirror-orphan",
                f"{fm.translation_of} has no canonical page at the same path",
                state.wiki_display(rel),
            )
    for rel, page in sorted(canonical.items()):
        if page.frontmatter.type not in MIRRORED_PAGE_TYPES:
            continue
        for lang in mirrors:
            mirror = state.pages.get(f"{lang}/{rel}")
            shown = state.wiki_display(f"{lang}/{rel}")
            if mirror is None or mirror.frontmatter.translation_of != page.frontmatter.id:
                state.add(
                    "G17",
                    "mirror-missing",
                    f"{page.frontmatter.id} has no {lang} mirror",
                    shown,
                    warning=True,
                )
            elif mirror.body.lstrip().startswith(untranslated_marker(lang)) or (
                f"\n{untranslated_marker(lang)}" in mirror.body
            ):
                state.add(
                    "G17",
                    "mirror-untranslated",
                    f"{page.frontmatter.id}: the {lang} translation was rejected, the page is "
                    "shown untranslated",
                    shown,
                    warning=True,
                )


def _check_orphans(state: _State, inbound: dict[str, set[str]], threshold: float) -> None:
    candidates = [path for path in state.pages if path != WikiFiles.INDEX]
    if not candidates:
        return
    orphans = sorted(path for path in candidates if not inbound.get(path))
    ratio = len(orphans) / len(candidates)
    if ratio > threshold:
        state.add(
            "G13",
            "orphan-pages",
            f"{len(orphans)} of {len(candidates)} pages have no inbound link "
            f"({ratio:.0%} > {threshold:.0%}): {orphans[:5]}",
            state.wiki_display(""),
            warning=True,
        )


_QUOTED_RE = re.compile(r'"[^"\n]*"|“[^”\n]*”|«[^»\n]*»')
_BLOCKQUOTE_RE = re.compile(r"^\s*>")
_TITLE_LINE_RE = re.compile(r"^title\s*:")


def _rendering_pattern(rendering: str) -> re.Pattern[str] | None:
    """Whole-word, case-insensitive pattern of a banned rendering (plural ``s``/``es`` allowed).

    Words of a multi-word rendering may be separated by any whitespace; a hyphen is literal, so
    ``hand-over`` matches only when it is listed itself.
    """
    words = rendering.split()
    if not words:
        return None
    phrase = r"\s+".join(re.escape(word) for word in words)
    return re.compile(rf"(?<!\w){phrase}(?:e?s)?(?!\w)", re.IGNORECASE)


def _prose(line: str) -> str:
    """The part of a line in the wiki's own words: blockquotes and quoted text removed."""
    if _BLOCKQUOTE_RE.match(line):
        return ""
    return _QUOTED_RE.sub(" ", line)


def _check_locked_vocabulary(state: _State, locked_terms: Mapping[str, Sequence[str]]) -> None:
    """G16: no page title or body renders a locked trade term with a banned English equivalent.

    Text quoted from the documents (blockquotes, text between double quotes) is not checked. The
    quality report is not checked either: it lists the findings themselves.
    """
    patterns: list[tuple[str, str, re.Pattern[str]]] = []
    for term, renderings in locked_terms.items():
        for rendering in (renderings,) if isinstance(renderings, str) else renderings:
            pattern = _rendering_pattern(rendering)
            if pattern is not None:
                patterns.append((term, rendering.strip(), pattern))
    if not patterns:
        return
    files = dict(state.lay.wiki_files())
    for rel, page in sorted(state.pages.items()):
        if rel == WikiFiles.QUALITY:
            continue
        shown = state.wiki_display(rel)
        title_line: int | None = None
        file = files.get(rel)
        if file is not None:
            head = state.read(file).decode("utf-8", errors="ignore").split("\n")
            for number, raw in enumerate(head[: state.offsets.get(rel, 0)], start=1):
                if _TITLE_LINE_RE.match(raw):
                    title_line = number
                    break
        lines: list[tuple[int | None, str]] = [(title_line, _prose(page.frontmatter.title))]
        offset = state.offsets.get(rel, 0)
        lines += [
            (offset + number, _prose(raw))
            for number, raw in enumerate(page.body.split("\n"), start=1)
        ]
        for line, text in lines:
            if not text.strip():
                continue
            for term, rendering, pattern in patterns:
                if pattern.search(text):
                    state.add(
                        "G16",
                        "banned-rendering",
                        f'"{rendering}" is a banned rendering of the locked term "{term}"',
                        shown,
                        line,
                    )


def validate_release(
    path: str | Path,
    *,
    canaries: Iterable[str] = (),
    require_manifest: bool = True,
    audience: str | None = None,
    orphan_threshold: float = 0.05,
    glossary_seeded: bool | None = None,
    locked_terms: Mapping[str, Sequence[str]] | None = None,
) -> list[Violation]:
    """Validate a release folder, a portable wiki folder or a folder holding ``current.json``.

    Paths in violations are relative to the validated folder (``wiki/…`` in a release folder,
    plain wiki paths and ``.docwiki/…`` in a portable folder). ``require_manifest=False``
    validates a candidate release before ``finalize`` (then pass ``audience``). ``canaries``
    enables G08. ``glossary_seeded=True`` enables G10. ``locked_terms`` (``{locked term:
    [banned renderings]}``, from the domain pack) enables G16.
    """
    base = Path(path)
    state = _State(root=base)
    layout, pointer, pointer_display = _resolve_root(base, state)
    state.layout = layout
    state.root = layout.root
    if not layout.root.is_dir():
        state.add(
            "G01",
            "release-missing",
            f"release folder {layout.root.name} not found",
            str(layout.root.name),
        )
        return state.violations
    manifest = _check_manifest(state, pointer, pointer_display, require_manifest)
    raw_catalog: dict[str, object] = {}
    catalog_file = layout.catalog_path
    if catalog_file.is_file():
        try:
            raw_catalog = json.loads(state.read(catalog_file).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            raw_catalog = {}
    state.audience = (
        audience
        or (manifest.audience if manifest else None)
        or (
            raw_catalog.get("audience") if isinstance(raw_catalog.get("audience"), str) else None  # type: ignore[assignment]
        )
    )
    state.release_id = (manifest.release_id if manifest else None) or (
        raw_catalog.get("release_id") if isinstance(raw_catalog.get("release_id"), str) else None  # type: ignore[assignment]
    )
    languages = manifest.wiki_languages if manifest else raw_catalog.get("wiki_languages")
    if isinstance(languages, list) and languages and all(isinstance(x, str) for x in languages):
        state.languages = list(languages)
    _load_wiki(state)
    _check_catalog(state, manifest)
    source_ids = {
        page.frontmatter.source_id
        for page in state.pages.values()
        if isinstance(page.frontmatter, SourceFrontmatter)
    }
    _load_evidence(state, source_ids)
    source_titles = {
        page.frontmatter.source_id: page.frontmatter.title
        for page in state.canonical_pages().values()
        if isinstance(page.frontmatter, SourceFrontmatter)
    }
    inbound: dict[str, set[str]] = {}
    for rel, page in sorted(state.pages.items()):
        _check_links(state, rel, page.body, inbound)
        _check_footnotes(state, rel, page, source_titles)
        _check_cited_lists(state, rel, page)
    for ns, evidence_page in sorted(state.evidence.items()):
        _check_links(state, ns, evidence_page.body, inbound)
    _check_llms(state, inbound)
    _check_supersession(state)
    _check_skills(state)
    _check_safety(state, [canary for canary in canaries if canary])
    _check_search_db(state)
    _check_tables(state, source_ids)
    _check_orphans(state, inbound, orphan_threshold)
    _check_mirrors(state)
    if locked_terms:
        _check_locked_vocabulary(state, locked_terms)
    if glossary_seeded and state.catalog is not None and not state.catalog.glossary:
        state.add(
            "G10",
            "glossary-empty",
            "the domain pack has glossary seeds but the glossary is empty",
            state.wiki_display(WikiFiles.GLOSSARY),
        )
    for ns, evidence_page in state.evidence.items():
        fm = evidence_page.frontmatter
        if isinstance(fm, EvidenceFrontmatter):
            try:
                parse_locator_key(locator_key(fm.locator))
            except ValueError as exc:
                state.add("G09", "locator-key", str(exc), ns)
    return sorted(
        state.violations, key=lambda v: (v.path or "", v.line or 0, v.gate, v.code, v.message)
    )


def validate_page(
    page: Page,
    *,
    sources: Mapping[str, Page],
    evidence: Mapping[str, EvidencePage],
    canaries: Iterable[str] = (),
) -> list[Violation]:
    """The checks of :func:`validate_release` that one content page passes on its own, run on a
    page that is not written yet (the pipeline checks carried and filed research answers).

    ``sources`` are the source pages of the release by source id and ``evidence`` its sidecars
    by content path (``evidence/<source_id>/<locator_key>.md``). Covered: footnotes and
    citations (G02, G03, G06), cited-fact lists (G03), the cited sources and the page tier
    (G02, G07), safe content (G05) and canaries (G08). Links to other pages need the whole
    release: :func:`validate_release` checks them. Paths are reported as in a release folder.
    """
    layout = ReleaseLayout("release", Path("."))
    state = _State(root=layout.root, layout=layout)
    state.evidence.update(evidence)
    shown = state.wiki_display(page.path)
    text = page.render()
    try:
        page = Page.parse(text, page.path)  # what the release validator reads from the file
    except (FrontmatterError, ValidationError) as exc:
        message = _summarize(exc) if isinstance(exc, ValidationError) else str(exc)
        state.add("G01", "frontmatter-invalid", message, shown)
        return state.violations
    state.offsets[page.path] = text[: len(text) - len(page.body)].count("\n")
    titles = {
        source_id: source.frontmatter.title
        for source_id, source in sources.items()
        if isinstance(source.frontmatter, SourceFrontmatter)
    }
    tiers = {source_id: source.frontmatter.sensitivity for source_id, source in sources.items()}
    _check_footnotes(state, page.path, page, titles)
    _check_cited_lists(state, page.path, page)
    _check_page_sources(state, page, tiers, shown)
    for finding in find_violations(text):
        state.add(
            _SAFETY_GATE,
            finding.kind,
            finding.message + (f": {finding.excerpt}" if finding.excerpt else ""),
            shown,
            finding.line,
        )
    if any(canary and canary in text for canary in canaries):
        state.add("G08", "canary-present", "injection canary found", shown)
    return sorted(
        state.violations, key=lambda v: (v.path or "", v.line or 0, v.gate, v.code, v.message)
    )
