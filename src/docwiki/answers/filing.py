"""Turn a reviewed Researcher answer into a contract query page (ADR 0007).

Deterministic, no model call: the answer's numbered citations become footnotes to evidence
sidecars with the source title, the locator label and an honest badge (wiki-contract §5); the
numbers of every cited sentence are checked against the cited evidence; the text passes the
content-safety rules (wiki-contract §10); a "How this answer was produced" section records the
agent, the release, the tool calls and the review. Filed answers are English (D10); quotations
keep their language. An honest "Not found in the wiki." answer files without sources.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Literal, Protocol

from docwiki.agents_client.citations import Source, parse_answer, split_answer
from docwiki.contracts.catalog import Catalog, CatalogPage
from docwiki.contracts.enums import badge_for, max_sensitivity
from docwiki.contracts.ids import format_query_id, query_page_path, slugify_ascii
from docwiki.contracts.layout import EVIDENCE_MOUNT, ReleaseFiles, StorageKeys
from docwiki.contracts.locators import locator_label
from docwiki.contracts.markdown import relative_link
from docwiki.contracts.pages import (
    DocwikiStamp,
    EvidenceFrontmatter,
    EvidencePage,
    Page,
    QueryFrontmatter,
)
from docwiki.contracts.safety import find_violations, sanitize_markdown
from docwiki.contracts.storage import KeyNotFoundError, Storage
from docwiki.release.layout import ReleaseLayout
from docwiki.release.publish import read_current_pointer
from docwiki.stages.verify_citations import unsigned_values

__all__ = [
    "APPROVED_BY",
    "HOW_HEADING",
    "FiledAnswer",
    "FilingError",
    "FolderRelease",
    "ReleaseLookup",
    "StorageRelease",
    "build_query_page",
    "query_slug",
]

APPROVED_BY = "owner"
"""``approved_by`` of every filed answer: a role, never a person's name or address."""
HOW_HEADING = "How this answer was produced"

_NOT_FOUND_RE = re.compile(r"\bnot found in the wiki\b", re.IGNORECASE)
_SLUG_MAX = 60
_INLINE_RE = re.compile(r"\[\^?c?(\d{1,3})\](?![(:])")
_RENUMBER_RE = re.compile(r"[ \t]*\[\^?c?(\d{1,3})\](?![(:])")
_LABEL_RE = re.compile(r"\[\^c(\d+)\]")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(?P<text>.+?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")
_CODE_SPAN_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
_SENTENCE_END_RE = re.compile(r"[.!?]+(?:\[\^c\d+\])*(?=\s|$)")
_LAST_WORD_RE = re.compile(r"([^\W\d_]+(?:\.[^\W\d_]+)*)$")
_ABBREVIATIONS = frozenset(
    {
        "no", "nos", "nr", "p", "pp", "art", "fig", "vol", "ch", "cf", "vs", "eg", "ie",
        "approx", "incl", "ref", "réf", "env", "mr", "mrs", "ms", "dr", "st", "mme", "mlle",
        "me", "ste", "sté",
    }
)  # fmt: skip
"""Words whose period never ends a sentence ("amendment no. 1", "M. Ancelin", "e.g. a lot")."""
_NUMBER_TOKEN_RE = re.compile(r"\d+(?:[\u00a0\u202f\u2009'\u2019]\d{3})*(?:[.,]\d+)*")
_LINK_RE = re.compile(r"!?\[(?P<text>[^\]]*)\]\([^)]*\)")
_MAX_QUESTION = 300
_MAX_SUMMARY = 240
_MAX_STEP = 80
_STEP_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "search": ("query",),
    "read_page": ("path", "section"),
    "get_index": ("scope",),
    "get_links": ("path",),
    "glossary": ("term", "query"),
    "get_evidence": ("path",),
    "query_table": ("source_id", "table", "sql"),
    "get_skill": ("name",),
}


class FilingError(ValueError):
    """The answer cannot become a query page (the message says why)."""


class ReleaseLookup(Protocol):
    """The parts of a release that filing reads: its catalog and its evidence sidecars."""

    @property
    def release_id(self) -> str: ...

    @property
    def catalog(self) -> Catalog: ...

    def evidence(self, ns_path: str) -> EvidencePage | None:
        """The sidecar at a content-namespace path (``evidence/<source_id>/<key>.md``)."""
        ...


class FolderRelease:
    """A published release folder (``releases/<id>/``) or a portable wiki folder."""

    def __init__(self, path: str | Path) -> None:
        layout = ReleaseLayout.detect(path)
        if layout is None:
            raise FilingError(f"no release or portable wiki folder at {path}")
        self._layout = layout
        self._catalog = Catalog.from_json(layout.catalog_path.read_bytes())

    @property
    def release_id(self) -> str:
        return self._catalog.release_id

    @property
    def catalog(self) -> Catalog:
        return self._catalog

    def evidence(self, ns_path: str) -> EvidencePage | None:
        try:
            file = self._layout.content_file(ns_path)
        except ValueError:
            return None
        if not file.is_file():
            return None
        return EvidencePage.parse(file.read_text(encoding="utf-8"), ns_path)


class StorageRelease:
    """A release in storage (``releases/<id>/``); the current one by default."""

    def __init__(self, storage: Storage, release_id: str | None = None) -> None:
        if release_id is None:
            pointer = read_current_pointer(storage)
            if pointer is None:
                raise FilingError("no release has been published yet")
            release_id = pointer[0].release_id
        self._storage = storage
        self._prefix = f"{StorageKeys.RELEASES}/{release_id}/"
        try:
            data = storage.read_bytes(self._prefix + ReleaseFiles.CATALOG)
        except KeyNotFoundError as exc:
            raise FilingError(f"release {release_id} has no catalog") from exc
        self._catalog = Catalog.from_json(data)

    @property
    def release_id(self) -> str:
        return self._catalog.release_id

    @property
    def catalog(self) -> Catalog:
        return self._catalog

    def evidence(self, ns_path: str) -> EvidencePage | None:
        if not ns_path.startswith(f"{EVIDENCE_MOUNT}/") or ".." in ns_path.split("/"):
            return None
        try:
            data = self._storage.read_bytes(self._prefix + ns_path)
        except KeyNotFoundError:
            return None
        return EvidencePage.parse(data.decode("utf-8"), ns_path)


@dataclass(frozen=True)
class FiledAnswer:
    """A query page ready for the inbox, with what the owner should review."""

    page: Page
    warnings: tuple[str, ...] = ()
    not_found: bool = False
    numbers_checked: int = 0
    """Cited sentences whose numbers were checked against their evidence."""


@dataclass(frozen=True)
class _Citation:
    label: int
    ns_path: str
    page: CatalogPage
    evidence: EvidencePage
    badge: str

    def footnote(self, from_path: str) -> str:
        assert isinstance(self.evidence.frontmatter, EvidenceFrontmatter)
        label = locator_label(self.evidence.frontmatter.locator)
        href = relative_link(from_path, self.ns_path)
        return f"[^c{self.label}]: [{self.page.title} — {label}]({href}) · {self.badge}"


def build_query_page(
    answer: Any,
    *,
    question: str,
    release: ReleaseLookup,
    filed_on: date,
    answered_on: date | None = None,
    asked_by: Literal["human", "researcher"] = "human",
) -> FiledAnswer:
    """The contract query page of ``answer`` (an :class:`~docwiki.agents_client.AgentAnswer` or
    any object with ``text``, ``sources``, ``tool_calls``, ``agent``, ``version`` and
    ``latency_s``) to ``question``, answered from ``release``.

    Raises :class:`FilingError` when a citation does not resolve to an evidence sidecar of the
    release, when the answer cites nothing and is not an explicit abstention, or when the text
    still breaks the content-safety rules after sanitising.
    """
    question_text = " ".join(question.split())
    if not question_text:
        raise FilingError("the question is empty")
    if len(question_text) > _MAX_QUESTION:
        raise FilingError(f"the question is longer than {_MAX_QUESTION} characters")
    text = str(getattr(answer, "text", "") or "")
    body, _ = split_answer(text)
    listed: list[Source] = list(getattr(answer, "sources", None) or parse_answer(text))
    by_number = {source.n: source for source in listed}
    used = _numbers_in_order(body)
    not_found = not used and bool(_NOT_FOUND_RE.search(body))
    if not used and not not_found:
        raise FilingError(
            "the answer cites nothing: only cited answers or an explicit "
            "'Not found in the wiki.' can be filed"
        )
    warnings: list[str] = []
    citations, numbering = _resolve_citations(used, by_number, release)
    unused = sorted(set(by_number) - set(used))
    if unused:
        listed_only = ", ".join(f"[{n}]" for n in unused)
        warnings.append(f"sources listed but never cited in the text were left out: {listed_only}")

    renumbered = _replace_outside_code(
        body,
        _RENUMBER_RE,
        lambda match: (
            f"[^c{numbering[int(match.group(1))]}]"
            if int(match.group(1)) in numbering
            else match.group(0)
        ),
    )
    clean, findings = sanitize_markdown(_demote_headings(renumbered))
    for message in dict.fromkeys(finding.message for finding in findings):
        warnings.append(f"removed from the answer: {message}")
    clean = clean.strip()
    if not clean:
        raise FilingError("the answer has no text left after the safety rules")

    checked, missing = _check_numbers(clean, citations)
    warnings.extend(missing)

    slug = query_slug(question_text)
    query_id = format_query_id(filed_on, slug)
    path = query_page_path(query_id)
    question_md, title_findings = sanitize_markdown(question_text)
    if title_findings:
        warnings.append("removed from the question: unsafe Markdown")
    tiers = [citation.page.sensitivity for citation in citations]
    frontmatter = QueryFrontmatter(
        id=query_id,
        title=question_text,
        summary=_summary(clean, fallback=question_text),
        sensitivity=max_sensitivity(*tiers) if tiers else "public",
        updated=filed_on,
        tags=[],
        docwiki=DocwikiStamp(schema=1, release=release.release_id),
        question=question_text,
        asked_by=asked_by,
        sources=sorted({citation.page.id for citation in citations}),
        approved_by=APPROVED_BY,
    )
    lines = [f"# {question_md.strip()}", "", clean, "", f"## {HOW_HEADING}", ""]
    lines.append(
        _provenance(
            answer,
            release_id=release.release_id,
            answered_on=answered_on or filed_on,
            filed_on=filed_on,
            not_found=not_found,
            checked=checked,
            missing=len(missing),
        )
    )
    steps = _steps(getattr(answer, "tool_calls", None) or [])
    if steps:
        lines += ["", *(f"- {step}" for step in steps)]
    if citations:
        lines += ["", "## Sources", ""]
        lines += [citation.footnote(path) for citation in _unique_labels(citations)]
    page = Page(path=path, frontmatter=frontmatter, body="\n".join(lines) + "\n")
    page = Page.parse(page.render(), path)  # contract round trip
    violations = find_violations(page.body)
    if violations:
        raise FilingError(f"the page breaks the content-safety rules: {violations[0].message}")
    return FiledAnswer(page, tuple(warnings), not_found=not_found, numbers_checked=checked)


def query_slug(question: str) -> str:
    """Slug of a filed question: its ASCII kebab-case, at most 60 characters.

    A slug cut at 60 characters ends with 6 hex of the hash of the full slug, so two long
    questions that start alike never share a page, while the same question filed again keeps
    its page (and replaces it).
    """
    full = slugify_ascii(question, 10_000) or "answer"
    if len(full) <= _SLUG_MAX:
        return full
    digest = hashlib.sha256(full.encode("ascii")).hexdigest()[:6]
    return f"{full[: _SLUG_MAX - len(digest) - 1].rstrip('-')}-{digest}"


def _numbers_in_order(body: str) -> list[int]:
    numbers: list[int] = []
    for line in _text_lines(body):
        for match in _INLINE_RE.finditer(_CODE_SPAN_RE.sub("", line)):
            number = int(match.group(1))
            if number not in numbers:
                numbers.append(number)
    return numbers


def _text_lines(markdown: str) -> list[str]:
    """Lines outside fenced code blocks."""
    lines: list[str] = []
    fence: str | None = None
    for line in markdown.split("\n"):
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)[0]
            fence = None if fence == marker else (fence or marker)
            continue
        if fence is None:
            lines.append(line)
    return lines


def _resolve_citations(
    used: Sequence[int], by_number: dict[int, Source], release: ReleaseLookup
) -> tuple[list[_Citation], dict[int, int]]:
    sources = {page.id: page for page in release.catalog.pages if page.type == "source"}
    citations: list[_Citation] = []
    by_path: dict[str, int] = {}
    numbering: dict[int, int] = {}
    for number in used:
        source = by_number.get(number)
        if source is None:
            raise FilingError(f"citation [{number}] is not in the answer's source list")
        if not source.source_id or not source.locator_key:
            raise FilingError(
                f"source [{number}] does not name an evidence sidecar "
                f"(evidence/<source_id>/<locator>.md): {source.path or source.title!r}"
            )
        ns_path = f"{EVIDENCE_MOUNT}/{source.source_id}/{source.locator_key}.md"
        if ns_path in by_path:
            numbering[number] = by_path[ns_path]
            continue
        evidence = release.evidence(ns_path)
        if evidence is None or not isinstance(evidence.frontmatter, EvidenceFrontmatter):
            raise FilingError(
                f"source [{number}]: no evidence sidecar {ns_path} in release {release.release_id}"
            )
        page = sources.get(evidence.frontmatter.source_id)
        if page is None:
            raise FilingError(
                f"source [{number}]: {evidence.frontmatter.source_id} has no source page in "
                f"release {release.release_id}"
            )
        label = len(citations) + 1
        badge = badge_for(evidence.frontmatter.provenance, "unverified-paraphrase")
        citations.append(_Citation(label, ns_path, page, evidence, badge))
        by_path[ns_path] = label
        numbering[number] = label
    return citations, numbering


def _unique_labels(citations: Sequence[_Citation]) -> list[_Citation]:
    return sorted(citations, key=lambda citation: citation.label)


def _replace_outside_code(
    markdown: str, pattern: re.Pattern[str], replace: Callable[[re.Match[str]], str]
) -> str:
    out: list[str] = []
    fence: str | None = None
    for line in markdown.split("\n"):
        match = _FENCE_RE.match(line)
        if match:
            marker = match.group(1)[0]
            fence = None if fence == marker else (fence or marker)
            out.append(line)
            continue
        if fence is not None:
            out.append(line)
            continue
        pieces: list[str] = []
        last = 0
        for span in _CODE_SPAN_RE.finditer(line):
            pieces.append(pattern.sub(replace, line[last : span.start()]))
            pieces.append(span.group(0))
            last = span.end()
        pieces.append(pattern.sub(replace, line[last:]))
        out.append("".join(pieces))
    return "\n".join(out)


def _demote_headings(markdown: str) -> str:
    """Headings of the answer become bold lines: the page owns its sections."""
    return _replace_outside_code(
        markdown,
        re.compile(r"^\s{0,3}#{1,6}\s+(?P<text>.+?)\s*#*\s*$"),
        lambda match: f"**{match.group('text')}**",
    )


def _plain(markdown: str) -> str:
    text = _LABEL_RE.sub("", markdown)
    text = _LINK_RE.sub(lambda match: match.group("text"), text)
    text = re.sub(r"[*`]+", "", text)
    return re.sub(r"\s+([.,;:!?])", r"\1", " ".join(text.split()))


def _sentences(markdown: str) -> list[str]:
    sentences: list[str] = []
    for line in _text_lines(markdown):
        line = line.strip()
        if not line:
            continue
        start = 0
        for match in _SENTENCE_END_RE.finditer(line):
            if match.group(0) == "." and _ends_with_abbreviation(line[: match.start()]):
                continue
            sentences.append(line[start : match.end()].strip())
            start = match.end()
        rest = line[start:].strip()
        if rest:
            sentences.append(rest)
    return sentences


def _ends_with_abbreviation(text: str) -> bool:
    """``text`` (just before a period) ends with an abbreviation or an initial."""
    match = _LAST_WORD_RE.search(text)
    if match is None:
        return False
    word = match.group(1).replace(".", "").casefold()
    return len(word) == 1 or word in _ABBREVIATIONS


def _check_numbers(markdown: str, citations: Sequence[_Citation]) -> tuple[int, list[str]]:
    """``(cited sentences checked, warnings)``: every number of a cited sentence must appear in
    the evidence it cites (the same number parsing as citation verification)."""
    if not citations:
        return 0, []
    available = {
        citation.label: unsigned_values([citation.evidence.body]) for citation in citations
    }
    checked = 0
    warnings: list[str] = []
    for sentence in _sentences(markdown):
        labels = [int(label) for label in _LABEL_RE.findall(sentence)]
        if not labels:
            continue
        checked += 1
        evidence: set[str] = set()
        for label in labels:
            evidence |= available.get(label, set())
        plain = _LINK_RE.sub(lambda match: match.group("text"), _LABEL_RE.sub("", sentence))
        missing = [
            token
            for token in dict.fromkeys(_NUMBER_TOKEN_RE.findall(plain))
            if not unsigned_values([token]) & evidence
        ]
        if missing:
            quoted = _clip(_plain(sentence), 120)
            warnings.append(
                f"numbers not found in the cited evidence: {', '.join(missing)} (in “{quoted}”)"
            )
    return checked, warnings


def _summary(markdown: str, *, fallback: str) -> str:
    for sentence in _sentences(markdown):
        plain = _plain(sentence)
        if plain:
            return _clip(plain, _MAX_SUMMARY)
    return _clip(fallback, _MAX_SUMMARY)


def _clip(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _provenance(
    answer: Any,
    *,
    release_id: str,
    answered_on: date,
    filed_on: date,
    not_found: bool,
    checked: int,
    missing: int,
) -> str:
    agent = str(getattr(answer, "agent", "") or "the Researcher agent").strip()
    version = getattr(answer, "version", None)
    who = f"`{agent}`" + (f" version {version}" if version else "")
    parts = [
        f"Answered by the Researcher agent ({who}) on {answered_on.isoformat()} from release "
        f"`{release_id}`, then reviewed and filed by the {APPROVED_BY} on {filed_on.isoformat()}."
    ]
    if not_found:
        parts.append("No source of that release answers the question.")
    elif missing:
        parts.append(
            f"Numbers checked against the cited evidence: {checked - missing} of {checked} cited "
            "sentences match; the others state computed or rounded values."
        )
    else:
        parts.append(f"Numbers checked against the cited evidence: all {checked} cited sentences.")
    calls = getattr(answer, "tool_calls", None) or []
    latency = getattr(answer, "latency_s", None)
    if calls:
        timing = f" in {float(latency):.0f} s" if latency else ""
        parts.append(f"The agent made {len(calls)} tool calls{timing}:")
    return " ".join(parts)


def _steps(calls: Sequence[Any]) -> list[str]:
    steps: list[str] = []
    for call in calls:
        name = re.sub(r"[^a-z0-9_]", "", str(getattr(call, "name", "") or "").lower())
        if not name:
            continue
        detail = _argument_text(name, getattr(call, "arguments", None))
        status = str(getattr(call, "status", "") or "")
        suffix = "" if status in ("", "completed") else f" ({_clip(status, 20)})"
        steps.append(f"{name}" + (f" `{detail}`" if detail else "") + suffix)
    return steps


def _argument_text(name: str, arguments: Any) -> str:
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except ValueError:
            arguments = {"value": arguments}
    if not isinstance(arguments, dict):
        return ""
    keys = _STEP_ARGUMENTS.get(name) or tuple(arguments)
    values = [
        str(arguments[key])
        for key in keys
        if key in arguments and isinstance(arguments[key], str | int | float) and arguments[key]
    ]
    text = " ".join(" ".join(values).replace("`", "'").split())
    return _clip(text, _MAX_STEP)
