"""Data model shared by the leak guard modules."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, replace
from typing import Literal

Severity = Literal["error", "warning"]

GENERATOR_AUTHOR = "DocWiki sample generator"


class ConfigError(Exception):
    """A configuration problem. The command line exits with code 2."""


def sha_hex(text: str, length: int) -> str:
    return hashlib.sha256(text.encode("utf-8", "surrogatepass")).hexdigest()[:length]


def finding_id(rule: str, path: str, key: str) -> str:
    """Stable fingerprint of a finding: rule + logical path + matched text (or location)."""
    return "LG-" + sha_hex(f"{rule}\x00{path}\x00{key}", 10)


@dataclass(frozen=True, slots=True)
class Chunk:
    """A unit of extracted text with its location inside a file.

    ``identifiers`` selects the deny-list and identifier rules, ``closed_world`` the proper-noun
    check. ``sentence_start`` tells the proper-noun check whether the first word of the chunk
    starts a sentence (capitalised only because of its position).
    """

    text: str
    location: str
    line: int | None = None
    kind: str = "content"
    field: str | None = None
    sentence_start: bool = True
    identifiers: bool = True
    closed_world: bool = True
    decoded: bool = False


@dataclass(frozen=True, slots=True)
class MetaField:
    """A document metadata value (Office core/app properties, PDF info dictionary...)."""

    fmt: str
    name: str
    value: str
    location: str


@dataclass(slots=True)
class Extraction:
    """Everything extracted from one file (or one embedded part)."""

    kind: str
    chunks: list[Chunk] = field(default_factory=list)
    metadata: list[MetaField] = field(default_factory=list)
    exif: list[str] = field(default_factory=list)
    notices: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    unknown_binary: bool = False

    def merge(self, other: Extraction, prefix: str) -> None:
        """Merge the extraction of an embedded part under a location prefix."""

        def loc(location: str) -> str:
            return f"{prefix} > {location}" if location else prefix

        for chunk in other.chunks:
            self.chunks.append(replace(chunk, location=loc(chunk.location), line=None))
        for meta in other.metadata:
            self.metadata.append(MetaField(meta.fmt, meta.name, meta.value, loc(meta.location)))
        self.exif.extend(loc(item) for item in other.exif)
        self.notices.extend(f"{prefix}: {item}" for item in other.notices)
        self.problems.extend(f"{prefix}: {item}" for item in other.problems)
        if other.unknown_binary:
            self.notices.append(f"{prefix}: embedded binary scanned for printable strings only")


@dataclass(frozen=True, slots=True)
class Notice:
    """Informational message (for example a file type that cannot be fully extracted)."""

    file: str
    kind: str
    message: str


@dataclass(slots=True)
class Finding:
    """One leak-guard finding.

    ``message`` never contains matched text. ``match`` and ``detail`` may contain it and are
    omitted from the output in redact mode. ``sensitive`` findings (deny-list) never expose the
    matched text or the pattern in redact mode.
    """

    rule: str
    severity: Severity
    path: str
    location: str
    message: str
    id: str
    line: int | None = None
    match: str | None = None
    detail: str | None = None
    source: str = "worktree"
    commit: str | None = None
    count: int = 1
    sensitive: bool = False
    key: str = field(default="", repr=False)

    @property
    def file(self) -> str:
        if self.commit:
            return f"{self.path}@{self.commit[:12]}"
        return self.path

    def sort_key(self) -> tuple[int, str, int, str]:
        return (0 if self.severity == "error" else 1, self.file, self.line or 0, self.rule)
