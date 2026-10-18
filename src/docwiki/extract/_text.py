"""Text helpers shared by the extract adapters: normalisation, safe labels, language guess."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter

from docwiki.contracts.safety import detect_injection

__all__ = [
    "BULLET_RE",
    "clean_text",
    "decode_text",
    "guess_lang",
    "lang_from_tag",
    "normalize_lines",
    "one_line",
    "paragraph_ranges",
    "safe_label",
    "words",
]

# C0 controls except TAB/LF/CR, DEL and non-characters.
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ufffe\uffff]")
# Zero-width and bidirectional controls: invisible, and a classic vehicle for smuggled text.
_INVISIBLE_RE = re.compile(r"[\u200b\u2060\ufeff\u202a-\u202e\u2066-\u2069]")
_SPACES_RE = re.compile(r"[ \t\u00a0\u2000-\u200a\u202f\u205f\u3000]+")
BULLET_RE = re.compile(
    r"^(?:[\u2022\u25e6\u25aa\u25cf\u2023\u2043\u2219\u00b7*\-\u2013]\s+|\(?\d{1,3}[.)]\s+)"
)
_LABEL_DROP_RE = re.compile(r"[<>`\[\]\\|/{}]")


def _base_clean(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _CONTROL_RE.sub("", text)
    text = _INVISIBLE_RE.sub("", text)
    return unicodedata.normalize("NFC", text).replace("\u00a0", " ")


def normalize_lines(text: str) -> list[str]:
    """Physical lines of ``text`` (LF/CRLF/CR), cleaned, right-stripped, none dropped."""
    return [line.rstrip() for line in _base_clean(text).split("\n")]


def clean_text(text: str) -> str:
    """NFC text with LF line breaks, no control/invisible characters, no outer blank lines."""
    return "\n".join(normalize_lines(text)).strip("\n").strip()


def one_line(text: str) -> str:
    """``clean_text`` collapsed to a single line with single spaces."""
    return _SPACES_RE.sub(" ", clean_text(text).replace("\n", " ")).strip()


def safe_label(text: str | None, *, fallback: str, max_len: int = 100) -> str:
    """A short, inert label for identifiers taken from documents (sheet, attachment, shape names).

    These strings end up in locators, footnote labels and YAML frontmatter, so characters with a
    Markdown/HTML meaning are removed rather than escaped, and a name addressed to AI systems
    (``detect_injection``) is replaced by ``fallback``.
    """
    value = one_line(text or "")
    value = re.sub(r"<[^<>]*>", "", value)
    value = _LABEL_DROP_RE.sub("", value)
    value = re.sub(r"\s+", " ", value).strip(" .")
    if len(value) > max_len:
        value = value[:max_len].rstrip()
    if not value or detect_injection(value):
        return fallback
    return value


def paragraph_ranges(lines: list[str]) -> list[tuple[int, int]]:
    """1-based inclusive ranges of consecutive non-empty lines."""
    ranges: list[tuple[int, int]] = []
    start: int | None = None
    for number, line in enumerate(lines, 1):
        if line.strip():
            if start is None:
                start = number
        elif start is not None:
            ranges.append((start, number - 1))
            start = None
    if start is not None:
        ranges.append((start, len(lines)))
    return ranges


def decode_text(data: bytes) -> tuple[str, str]:
    """Decode text bytes: BOM-aware UTF-8/UTF-16, then UTF-8, then cp1252 as a last resort."""
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8", errors="replace"), "utf-8-sig"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16", errors="replace"), "utf-16"
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace"), "cp1252"


def words(text: str) -> frozenset[str]:
    """Whitespace-separated word set (compact literal for word lists)."""
    return frozenset(text.split())


_STOPWORDS: dict[str, frozenset[str]] = {
    "en": words(
        "the and of to is in for with on this that are be it as at by from or an not all must "
        "when was were will shall should which has have"
    ),
    "fr": words(
        "le la les et des du un une est pour dans avec sur pas que qui au aux ce cette sont par "
        "ou doit lors être ont été sera selon"
    ),
    "de": words(
        "der die das und ist nicht mit für auf ein eine den dem des zu von im sich wird bei oder "
        "sind werden auch muss nach"
    ),
    "es": words("el los las y del que en es por para con una se no al como su está son debe"),
    "it": words("il lo gli e di che per con una non sono della del nel alla deve"),
    "nl": words("het een en van is op niet met voor dat zijn te bij wordt naar ook moet"),
    "pt": words("os as e do da que em para com uma não são pela pelo deve"),
}
_WORD_RE = re.compile(r"[^\W\d_]+")


def guess_lang(text: str, *, default: str = "en") -> str:
    """Cheap stop-word language guess (en, fr, de, es, it, nl, pt); ``default`` when unsure."""
    words = _WORD_RE.findall(text[:40_000].lower())
    if not words:
        return default
    counts = Counter(words)
    scores = {
        lang: sum(counts[word] for word in stopwords) for lang, stopwords in _STOPWORDS.items()
    }
    ranked = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    best, best_score = ranked[0]
    runner_up = ranked[1][1]
    if best_score < 3 or best_score < runner_up * 1.25:
        return default
    return best


def lang_from_tag(tag: str | None) -> str | None:
    """Primary language subtag of a BCP-47 tag (``fr-FR`` → ``fr``), or None."""
    if not tag:
        return None
    primary = tag.strip().replace("_", "-").split("-", 1)[0].lower()
    return primary if re.fullmatch(r"[a-z]{2,3}", primary) else None
