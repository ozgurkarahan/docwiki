"""WebVTT transcripts: one ``cue`` block per cue, locators ``HH:MM:SS`` (milliseconds truncated)."""

from __future__ import annotations

import html
import re

from docwiki.contracts.locators import VttCueLocator
from docwiki.extract._draft import Draft
from docwiki.extract._text import clean_text, decode_text, normalize_lines

__all__ = ["extract_vtt", "parse_timestamp"]

_TIMESTAMP = r"(?:\d+:)?\d{1,2}:\d{2}[.,]\d{1,3}"
_TIMING_RE = re.compile(rf"^\s*({_TIMESTAMP})\s+-->\s+({_TIMESTAMP})(?:\s|$)")
_VOICE_RE = re.compile(r"<v(?:\.[^\s>]*)?\s+([^>]*)>")
_TAG_RE = re.compile(r"</?[^>]*>")


def parse_timestamp(value: str) -> int:
    """Seconds (milliseconds truncated) of ``[HH:]MM:SS.mmm``."""
    clock = value.replace(",", ".").split(".", 1)[0]
    parts = [int(part) for part in clock.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0)
    hours, minutes, seconds = parts
    return hours * 3600 + minutes * 60 + seconds


def _hms(total: int) -> str:
    return f"{total // 3600:02d}:{total % 3600 // 60:02d}:{total % 60:02d}"


def _cue_text(lines: list[str]) -> str:
    text = "\n".join(lines)
    text = _VOICE_RE.sub(lambda match: f"{match[1].strip()}: " if match[1].strip() else "", text)
    text = _TAG_RE.sub("", text)
    return clean_text(html.unescape(text))


def extract_vtt(data: bytes, draft: Draft) -> None:
    text, encoding = decode_text(data)
    if encoding == "cp1252":
        draft.warn("encoding", "the file is not valid UTF-8; decoded as Windows-1252")
    lines = normalize_lines(text)
    if not lines or not lines[0].lstrip().startswith("WEBVTT"):
        draft.warn("vtt-header", "the file does not start with WEBVTT; parsed leniently")
    chunks: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if line.strip():
            current.append(line)
        elif current:
            chunks.append(current)
            current = []
    if current:
        chunks.append(current)

    for chunk in chunks:
        timing_index = next(
            (index for index, line in enumerate(chunk[:2]) if _TIMING_RE.match(line)), None
        )
        if timing_index is None:
            continue  # header, NOTE, STYLE and REGION blocks
        match = _TIMING_RE.match(chunk[timing_index])
        assert match is not None
        start = parse_timestamp(match[1])
        end = parse_timestamp(match[2])
        if end < start:
            draft.warn("vtt-cue", f"cue at {_hms(start)} ends before it starts; end set to start")
            end = start
        cue_text = _cue_text(chunk[timing_index + 1 :])
        if not cue_text:
            continue
        locator = VttCueLocator(cue_start=_hms(start), cue_end=_hms(end))
        draft.block("cue", cue_text, locator, "native-text")
