"""Shared helpers: fixed timestamps, seeded randomness, French number formats and file output."""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

STAMP = "FICTIONAL - NOT FOR OPERATIONAL USE"
GENERATOR_AUTHOR = "DocWiki sample generator"
BASE_SEED = 20260917



@dataclass(frozen=True)
class DocMeta:
    """Neutral metadata written into every generated file."""

    title: str
    subject: str
    organisation: str
    created: datetime
    modified: datetime
    lang: str = "fr"
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


# ------------------------------------------------------------------------------------------
# French print formats (bible world.print_formats)


def dec(value: float | int | str | Decimal) -> Decimal:
    """Exact decimal of a bible number (YAML floats go through their shortest repr)."""
    return value if isinstance(value, Decimal) else Decimal(str(value))


def number(value: float | int | str | Decimal, decimals: int = 2) -> str:
    """Comma decimal separator and NO thousands separator: ``12500,00``.

    Citation verification joins digit groups only across non-breaking spaces, so a printed
    thousands separator would split one amount into two numbers.
    """
    exact = dec(value)
    quantum = Decimal(1).scaleb(-decimals)
    if exact.quantize(quantum) != exact:
        raise ValueError(f"{value!r} has more than {decimals} decimals")
    return f"{exact:.{decimals}f}".replace(".", ",")


def eur(value: float | int | str | Decimal) -> str:
    """An amount in euros: ``12500,00 €``."""
    return f"{number(value)} €"


def quantity(value: float | int) -> str:
    """Counts stay integers (``2``); measured quantities keep two decimals (``16,80``)."""
    return str(value) if isinstance(value, int) else number(value)


def percent(value: float | int | str | Decimal) -> str:
    """``30 %`` (a space before the percent sign)."""
    exact = dec(value)
    text = f"{exact.normalize():f}".replace(".", ",")
    return f"{text} %"


def fr_date(iso: str) -> str:
    """``2026-03-17`` -> ``17/03/2026``."""
    return parse_day(iso).strftime("%d/%m/%Y")


# ------------------------------------------------------------------------------------------
# Output


def write_bytes(out_root: Path, rel_path: str, data: bytes) -> Path:
    target = out_root / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


def write_text(out_root: Path, rel_path: str, text: str) -> Path:
    """Write UTF-8 text with line feed endings (as the repository normalises text files)."""
    if "\r" in text:
        raise ValueError(f"{rel_path}: text must use LF line endings")
    return write_bytes(out_root, rel_path, text.encode("utf-8"))


def meta_for(doc: dict[str, object], organisation: str, *, subject: str = STAMP) -> DocMeta:
    """Build the document metadata from a bible document entry."""
    day = str(doc["date"])
    return DocMeta(
        title=str(doc["title"]),
        subject=subject,
        organisation=organisation,
        created=stamp_time(day, 8, 30),
        modified=stamp_time(day, 16, 45),
        lang=str(doc.get("lang") or "fr"),
        keywords=" ".join(
            str(v) for v in (doc.get("doc_number"), doc.get("kind"), "fictional sample") if v
        ),
    )
