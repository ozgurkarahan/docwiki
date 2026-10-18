"""Shared helpers: fixed timestamps, seeded randomness, text sanitising and file output."""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

STAMP = "FICTIONAL - NOT FOR OPERATIONAL USE"
GENERATOR_AUTHOR = "DocWiki sample generator"
BASE_SEED = 20260917

_LATIN1_REPLACEMENTS = {
    "\u2013": "-",
    "\u2014": "-",
    "\u2212": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2026": "...",
    "\u2192": "->",
    "\u2264": "<=",
    "\u2265": ">=",
    "\u2022": "-",
    "\u00a0": " ",
    "\u202f": " ",
    "\u2009": " ",
}


@dataclass(frozen=True)
class DocMeta:
    """Neutral metadata written into every generated file."""

    title: str
    subject: str
    organisation: str
    created: datetime
    modified: datetime
    lang: str = "en"
    keywords: str = ""


def parse_day(value: str) -> date:
    return date.fromisoformat(value)


def stamp_time(day: str, hour: int = 8, minute: int = 30) -> datetime:
    """A fixed, timezone-aware (UTC) timestamp on a timeline day."""
    d = parse_day(day)
    return datetime(d.year, d.month, d.day, hour, minute, 0, tzinfo=UTC)


def rng(name: str) -> random.Random:
    """A deterministic random generator per named stream (independent of the Python hash seed)."""
    return random.Random(BASE_SEED ^ zlib.crc32(name.encode("utf-8")))


def latin1(text: str) -> str:
    """Map typographic characters to the latin-1 range so PDF core fonts can render them."""
    for src, dst in _LATIN1_REPLACEMENTS.items():
        text = text.replace(src, dst)
    text.encode("latin-1")
    return text


def write_bytes(out_root: Path, rel_path: str, data: bytes) -> Path:
    target = out_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def write_text(out_root: Path, rel_path: str, text: str, *, bom: bool = False) -> Path:
    """Write UTF-8 text with line feed endings (as the repository normalises text files)."""
    if "\r" in text:
        raise ValueError(f"{rel_path}: text must use LF line endings")
    data = text.encode("utf-8")
    if bom:
        data = b"\xef\xbb\xbf" + data
    return write_bytes(out_root, rel_path, data)


def meta_for(doc: dict[str, object], organisation: str, *, subject: str = STAMP) -> DocMeta:
    """Build the document metadata from a bible document entry."""
    day = str(doc["date"])
    return DocMeta(
        title=str(doc["title"]),
        subject=subject,
        organisation=organisation,
        created=stamp_time(day, 8, 30),
        modified=stamp_time(day, 16, 45),
        lang=str(doc.get("lang") or "en"),
        keywords=" ".join(
            str(v) for v in (doc.get("doc_number"), doc.get("kind"), "fictional sample") if v
        ),
    )
