"""Parse the Researcher's citation format (docs/spec/mcp-and-agents.md §2, rule 4).

Every factual sentence ends with ``[n]``; the answer ends with a numbered source list::

    Sources:
    [1] <source title> — <locator label> (<provenance>) — <sidecar path>

:func:`parse_answer` returns that list. It tolerates the usual model drift (other dashes or ``|``
as separators, Markdown bullets, emphasis, links and backticks, the wiki footnote style
``[Title — label](../evidence/...) · badge``, badges instead of provenance types, ``../``
prefixes, a numbered Markdown list under the ``Sources:`` heading) and never mistakes body text
for a source line: outside the source block a line is only accepted when it carries a sidecar
path, a known provenance or a locator label.
"""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict

from docwiki.contracts.enums import PROVENANCES
from docwiki.contracts.locators import is_locator_key

__all__ = [
    "Source",
    "inline_citations",
    "normalize_path",
    "normalize_provenance",
    "parse_answer",
    "parse_source_line",
    "split_answer",
]


class Source(BaseModel):
    """One entry of an answer's source list."""

    model_config = ConfigDict(frozen=True)

    n: int
    title: str
    locator_label: str = ""
    provenance: str = ""
    path: str = ""
    source_id: str | None = None
    locator_key: str | None = None


_DASH = r"(?:—|–|--|-|\|)"
_SEP_RE = re.compile(rf"\s+{_DASH}\s+")
_TRAILING_SEP_RE = re.compile(rf"(?:\s+{_DASH}|\s+·)\s*$")
_ITEM_RE = re.compile(
    r"^\s{0,3}(?:[-*+]\s+|\d{1,3}[.)]\s+)?(?:\*\*|__)?\[\^?c?(?P<n>\d{1,3})\](?:\*\*|__)?"
    r"[:.]?\s+(?P<rest>\S.*?)\s*$"
)
_NUMBERED_RE = re.compile(r"^\s{0,3}(?P<n>\d{1,3})[.)]\s+(?P<rest>\S.*?)\s*$")
_HEADING_RE = re.compile(
    r"^\s{0,3}(?:#{1,6}\s*)?(?:\*\*|__)?\s*"
    r"(?:sources?|references?|références|quellen|fuentes|fonti|bronnen)"
    r"\s*(?:\*\*|__)?\s*:?\s*(?:\*\*|__)?\s*$",
    re.IGNORECASE,
)
_PATH_TOKEN = r"(?:https?://[^\s/]+/)?(?:\.{1,2}/)*[A-Za-z0-9_][\w./\-]*\.md(?:#[\w\-]*)?"
_PATH_RE = re.compile(_PATH_TOKEN)
_TRAILING_PATH_RE = re.compile(
    rf"(?:^|\s+{_DASH}\s+|\s+·\s+|\s+)[<(\"']*(?P<path>{_PATH_TOKEN})[>)\"']*[.;,]?$"
)
_LINK_RE = re.compile(r"\[(?P<label>[^\]]*)\]\(\s*<?(?P<target>[^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
_BADGE_RE = re.compile(r"\s+·\s+(?P<badge>[^·]+?)\s*$")
_PROVENANCE_RE = re.compile(r"\(\s*(?P<value>[^()]*?)\s*\)\s*$")
_EVIDENCE_PATH_RE = re.compile(
    r"^evidence/(?P<sid>src-[0-9a-f]{12})/(?P<key>[a-z0-9][a-z0-9-]*)\.md$"
)
_LOCATOR_HINT_RE = re.compile(
    r"^(?:pp?\.\s*\d|¶\s*\d|table\s+\d|rows?\s+\d|sheet\s|slide\s+\d|message\s|attachment\s"
    r"|lines?\s+\d|region\s+\d|\d{1,2}:\d{2})",
    re.IGNORECASE,
)
_INLINE_RE = re.compile(r"\[\^?c?(\d{1,3})\](?![(:])")

_PROVENANCE_ALIASES: dict[str, str] = {
    "native-text": "native-text",
    "native text": "native-text",
    "quote verified": "native-text",
    "verified": "native-text",
    "paraphrase": "native-text",
    "deterministic-table": "deterministic-table",
    "deterministic table": "deterministic-table",
    "table": "deterministic-table",
    "ocr": "ocr",
    "model-description": "model-description",
    "model description": "model-description",
    "generated description": "model-description",
}


def normalize_provenance(value: str) -> str:
    """Map a provenance type or footnote badge to its provenance type; unknown values stay as is."""
    key = re.sub(r"\s+", " ", value.replace("✓", " ").replace("_", "-")).strip().casefold()
    return _PROVENANCE_ALIASES.get(key, value.strip())


def normalize_path(path: str) -> str:
    """Sidecar path relative to the release root (``../evidence/x.md`` -> ``evidence/x.md``)."""
    value = path.strip().strip("<>`'\"()").split("#", 1)[0].replace("\\", "/")
    value = re.sub(r"^https?://[^/]+/", "", value)
    index = value.find("evidence/")
    if index > 0 and value[index - 1] == "/":
        value = value[index:]
    while value.startswith(("./", "../")):
        value = value[value.index("/") + 1 :]
    return value.lstrip("/")


def _looks_like_path(value: str) -> bool:
    return _PATH_RE.fullmatch(value.strip()) is not None


def _strip_emphasis(value: str) -> str:
    return value.strip().strip("*_").strip()


def _strip_trailing_separators(value: str) -> str:
    previous = None
    while previous != value:
        previous, value = value, _TRAILING_SEP_RE.sub("", value).strip()
    return value


def _source(n: int, rest: str) -> Source:
    text = rest.strip()
    link_paths: list[str] = []

    def unlink(match: re.Match[str]) -> str:
        label, target = match["label"], match["target"]
        if _looks_like_path(target):
            link_paths.append(target)
            return "" if _looks_like_path(label) else label
        return label

    text = _strip_emphasis(_LINK_RE.sub(unlink, text).replace("`", ""))
    path = ""
    trailing = _TRAILING_PATH_RE.search(text)
    if trailing:
        path, text = trailing["path"], text[: trailing.start()]
    elif link_paths:
        path = link_paths[-1]
    provenance = ""
    badge = _BADGE_RE.search(text)
    if badge:
        provenance, text = badge["badge"], text[: badge.start()]
    text = _strip_trailing_separators(text)
    if not provenance:
        group = _PROVENANCE_RE.search(text)
        if group:
            value = group["value"]
            known = normalize_provenance(value) in PROVENANCES
            if known or _SEP_RE.search(text[: group.start()]):
                provenance, text = value, text[: group.start()]
    text = _strip_trailing_separators(text)
    separators = list(_SEP_RE.finditer(text))
    if separators:
        title, locator = text[: separators[-1].start()], text[separators[-1].end() :]
    else:
        title, locator = text, ""
    path = normalize_path(path) if path else ""
    evidence = _EVIDENCE_PATH_RE.match(path)
    key = evidence["key"] if evidence and is_locator_key(evidence["key"]) else None
    return Source(
        n=n,
        title=_strip_emphasis(title),
        locator_label=_strip_emphasis(locator),
        provenance=normalize_provenance(provenance) if provenance else "",
        path=path,
        source_id=evidence["sid"] if evidence else None,
        locator_key=key,
    )


def _is_structured(source: Source) -> bool:
    return bool(
        source.path
        or source.provenance in PROVENANCES
        or (source.title and _LOCATOR_HINT_RE.match(source.locator_label))
    )


def parse_source_line(line: str, *, in_sources_block: bool = False) -> Source | None:
    """Parse one source-list line, or return ``None``.

    Outside the source block (``in_sources_block=False``) the line must carry a sidecar path, a
    known provenance or a locator label, so that body sentences starting with ``[n]`` are ignored.
    """
    match = _ITEM_RE.match(line)
    if match is None and in_sources_block:
        match = _NUMBERED_RE.match(line)
    if match is None:
        return None
    source = _source(int(match["n"]), match["rest"])
    if not source.title and not source.path:
        return None
    if in_sources_block or _is_structured(source):
        return source
    return None


def _lines(text: str) -> list[str]:
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _sources_start(lines: list[str]) -> int:
    """Index of the first line of the source block (``len(lines)`` when there is none)."""
    heading = None
    for index, line in enumerate(lines):
        if _HEADING_RE.match(line):
            heading = index
    if heading is not None:
        return heading + 1
    start = len(lines)
    for index in range(len(lines) - 1, -1, -1):
        if not lines[index].strip():
            continue
        if not _ITEM_RE.match(lines[index]):
            break
        start = index
    return start


def parse_answer(text: str) -> list[Source]:
    """The numbered source list of an answer, sorted by number (first occurrence of a number wins).

    An abstention ("Not found in the wiki.") has no source list and returns ``[]``.
    """
    lines = _lines(text)
    start = _sources_start(lines)
    sources: dict[int, Source] = {}
    for index, line in enumerate(lines):
        source = parse_source_line(line, in_sources_block=index >= start)
        if source is not None and source.n not in sources:
            sources[source.n] = source
    return [sources[n] for n in sorted(sources)]


def split_answer(text: str) -> tuple[str, str]:
    """``(body, source block)``; the source block includes its heading when there is one."""
    lines = _lines(text)
    start = _sources_start(lines)
    if start < len(lines) and start > 0 and _HEADING_RE.match(lines[start - 1]):
        start -= 1
    return "\n".join(lines[:start]).strip(), "\n".join(lines[start:]).strip()


def inline_citations(text: str) -> list[int]:
    """Citation numbers used in the body of an answer, in order of first use."""
    body, _ = split_answer(text)
    numbers: list[int] = []
    for match in _INLINE_RE.finditer(body):
        number = int(match[1])
        if number not in numbers:
            numbers.append(number)
    return numbers
