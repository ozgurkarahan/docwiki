"""Closed-world check: capitalised names in sample content must come from the fictional world.

Candidates are capitalised word sequences (and camel-case / brand-like tokens) that do not merely
start a sentence. A candidate is reported unless every word is known: in the fiction allowlist
(``samples/fiction/allowlist.txt``), the technology allowlist, the curated common-word list, or
the vocabulary learned from words that the scanned sample content itself uses in lower case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .config import TermSet
from .words import (
    WORD_RE,
    is_capitalised,
    is_roman_numeral,
    keys,
    strip_elision,
    strip_possessive,
    word_stems,
)

# Lower-case words that may sit inside a name ("Bank of X", "Jean de Y", "Power & Light").
CONNECTORS = frozenset(
    {"of", "the", "and", "de", "du", "des", "la", "le", "von", "van", "der", "den", "di", "da",
     "del", "y", "zu", "et", "und"}
)
# A period after these does not end a sentence and the name continues ("Mr. X", "J. X").
HONORIFICS = frozenset(
    {"mr", "mrs", "ms", "mx", "dr", "prof", "mme", "mlle", "m", "hr", "fr", "sr", "jr", "st",
     "mt", "sir", "dame", "herr", "frau"}
)
# A period after these does not end a sentence.
ABBREVIATIONS = HONORIFICS | frozenset(
    {"no", "nr", "fig", "figs", "vol", "ref", "refs", "approx", "dept", "inc", "ltd", "co",
     "corp", "rev", "p", "pp", "ch", "sec", "art", "al", "max", "min", "tel", "ext", "ca",
     "env", "nb", "ed", "eds", "vgl", "bzw", "usw", "ggf", "inkl", "cie"}
)

_VTT_VOICE_RE = re.compile(r"<v(?:\.[\w.-]+)?\s+([^>]+)>")
_ABBREV_DOTS_RE = re.compile(r"\b(?:e\.g|i\.e|z\.b|d\.h|u\.a|c\.-à-d|p\.ex)\.", re.IGNORECASE)
_CLEAN_RES = (
    re.compile(r"`[^`\n]*`"),
    re.compile(r"\]\([^)\s]*\)"),
    re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE),
    re.compile(r"\bwww\.\S+", re.IGNORECASE),
    re.compile(r"[\w.%+-]+@[\w-]+(?:\.[\w-]+)+"),
    re.compile(r"(?:\b[A-Za-z]:)?(?:[\\/][\w.~-]+){2,}[\\/]?"),
    re.compile(r"\b(?:[\w-]+\.)+[A-Za-z]{2,6}\b"),
    re.compile(r"</?[A-Za-z][^<>]*>"),
    re.compile(r"&(?:[A-Za-z]+|#\d+);"),
    re.compile(r"\[\^[^\]]*\]"),
    re.compile(r"\{\{[^}]*\}\}|\{[^{}\s]*\}"),
)
_RUN_SPLIT_WORDS = 4
# Alphanumeric compounds (letters, digits, "_" joined by "-", ".", ":", "/", "+", "#").
_COMPOUND_RE = re.compile(r"\w(?:[\w.:/+#-]*\w)?")
# Format placeholders such as NN, XX, YYYY (as in "WTG-NN" or "YYYY-MM-DD").
_PLACEHOLDER_RE = re.compile(r"([A-Z])\1+")
# Humps of a camel-case token: "PDFContext" -> PDF, Context; "iZorb" -> i, Zorb.
_CAMEL_HUMP_RE = re.compile(r"[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+|[A-Z]+")
# Characters in the gap before a word that open a new phrase: a value after a colon, a table
# cell, a new line, a double-quoted string (JSON). Parentheses and single quotes do not: names
# often appear there in the middle of a sentence.
_PHRASE_OPENERS = frozenset("\":|“„«\n\t")
_HEADING_START_RE = re.compile(r"^\s*#{1,6}\s")


def clean_text(text: str) -> str:
    """Remove code spans, URLs, e-mail addresses, paths, domains and markup from prose."""
    text = _VTT_VOICE_RE.sub(r" \1: ", text)
    for pattern in _CLEAN_RES:
        text = pattern.sub(" ", text)
    return _ABBREV_DOTS_RE.sub(lambda match: match.group().replace(".", ""), text)


@dataclass(frozen=True, slots=True)
class Candidate:
    """An unknown capitalised term (``term``) inside a capitalised run (``context``)."""

    term: str
    context: str


@dataclass(slots=True)
class Vocabulary:
    allow: TermSet
    tech: TermSet
    common: TermSet
    learned: set[str] = field(default_factory=set)

    def _known_key(self, key: str) -> bool:
        return (
            key in self.allow.words
            or key in self.tech.words
            or key in self.common.words
            or key in self.learned
        )

    def knows(self, word: str) -> bool:
        word = strip_possessive(word)
        if len(word) <= 1 or _PLACEHOLDER_RE.fullmatch(word):
            return True
        if word.isupper() and is_roman_numeral(word):
            return True
        word_keys = keys(word)
        if any(self._known_key(key) for key in word_keys):
            return True
        # Inflected forms of known words: plurals, "-ed", "-ing", "-er", "-ly"...
        for stem in word_stems(word_keys[0]) + word_stems(word_keys[1]):
            if stem in self.common.words or stem in self.tech.words or stem in self.learned:
                return True
        parts = [part for part in re.split(r"['’-]", word) if part]
        if len(parts) > 1 and all(self.knows(part) for part in parts):
            return True
        # Camel-case compounds of known words are code identifiers ("ReleaseReader",
        # "PDFContext"); brand-like tokens with an unknown or one-letter hump stay names.
        humps = _CAMEL_HUMP_RE.findall(word)
        if (
            len(humps) > 1
            and all(len(hump) >= 2 for hump in humps)
            and all(self.knows(hump) for hump in humps)
        ):
            return True
        return self.regex_known(word)

    def regex_known(self, text: str) -> bool:
        return any(terms.regex_match(text) for terms in (self.allow, self.tech, self.common))

    def learn(self, text: str) -> None:
        """Words written in lower case in prose are common words of the corpus."""
        for match in WORD_RE.finditer(clean_text(text)):
            word = strip_elision(match.group())
            if len(word) >= 2 and word.islower():
                for part in {word, *re.split(r"['’-]", word)}:
                    if len(part) >= 2:
                        part_keys = keys(part)
                        self.learned.update(part_keys)
                        self.learned.update(word_stems(part_keys[0]))


def identifier_spans(text: str) -> list[tuple[int, int]]:
    """Spans of alphanumeric identifiers: compounds containing a digit or an underscore.

    Examples: release ids (``20260215T090000Z-decd4b59``), ISO timestamps, source ids
    (``src-43c97f7dfcde``), locators (``p0003``, ``b0042``), asset tags (``WTG-07``), document
    numbers (``SOP-GBX-010``), code identifiers (``FIXTURE_DIR``). Words inside them are not names.
    """
    return [
        match.span()
        for match in _COMPOUND_RE.finditer(text)
        if "_" in match.group() or any(ch.isdigit() for ch in match.group())
    ]


def _gap_kind(gap: str, previous: str | None) -> str:
    """``join`` (same run), ``cell`` (run break) or ``sentence`` (run break + sentence start)."""
    if not gap or (gap.isspace() and "\n" not in gap):
        return "join"
    stripped = gap.strip()
    if stripped == "&":
        return "join"
    if any(ch in ".!?…" for ch in stripped):
        if stripped == "." and previous:
            lower = previous.lower()
            if (len(previous) == 1 and previous.isupper()) or lower in HONORIFICS:
                return "join"
            if lower in ABBREVIATIONS:
                return "cell"
        return "sentence"
    return "cell"


def find_candidates(text: str, sentence_start: bool, vocabulary: Vocabulary) -> list[Candidate]:
    """Unknown capitalised terms of ``text``.

    A single capitalised word is not a candidate when it starts a sentence, or when it opens a
    phrase (start of the text, a quoted value, a cell, a line, or after a colon) and is followed
    by lower-case prose ("Drain the oil", ``"summary": "Curated syntheses"``). A capitalised word
    standing alone in such a position ("Supplier: Zorblax") is still checked.
    """
    clean = clean_text(text)
    fragments = identifier_spans(clean)
    fragment_index = 0
    results: list[Candidate] = []
    run: list[tuple[str, bool]] = []
    run_start = run_end = 0
    run_at_sentence_start = run_at_phrase_start = False
    connectors = 0
    at_start = sentence_start
    # A chunk opens a phrase (cell, value, line) unless it is a Markdown heading.
    phrase_open = not _HEADING_START_RE.match(text)
    previous_end = 0
    previous: str | None = None

    def flush(followed_by_prose: bool = False) -> None:
        nonlocal run, connectors
        if run:
            excused = len(run) == 1 and (
                run_at_sentence_start or (run_at_phrase_start and followed_by_prose)
            )
            if not excused:
                results.extend(_evaluate(run, clean[run_start:run_end], vocabulary))
        run = []
        connectors = 0

    for match in WORD_RE.finditer(clean):
        word = match.group()
        gap = clean[previous_end : match.start()]
        kind = _gap_kind(gap, previous)
        if kind != "join":
            flush()
            if kind == "sentence":
                at_start = True
        if any(ch in _PHRASE_OPENERS for ch in gap):
            phrase_open = True
        first_word, phrase_word = at_start, phrase_open
        at_start = phrase_open = False
        previous_end = match.end()
        previous = word
        while fragment_index < len(fragments) and fragments[fragment_index][1] <= match.start():
            fragment_index += 1
        if (
            fragment_index < len(fragments)
            and fragments[fragment_index][0] <= match.start()
            and match.end() <= fragments[fragment_index][1]
        ):
            flush()  # part of an identifier such as WTG-07 or 20260215T090000Z-decd4b59
            continue
        core = strip_elision(word)
        if core and is_capitalised(core):
            if not run:
                run_at_sentence_start = first_word
                run_at_phrase_start = phrase_word
                run_start = match.end() - len(core)
            run.append((core, connectors > 0))
            run_end = match.end()
            connectors = 0
        elif run and word.lower() in CONNECTORS and connectors < 2:
            connectors += 1
        else:
            flush(followed_by_prose=kind == "join" and word.islower())
    flush()
    return results


def _evaluate(run: list[tuple[str, bool]], context: str, vocabulary: Vocabulary) -> list[Candidate]:
    """Unknown words of a capitalised run, grouped into adjacent spans of at most 4 words."""
    if vocabulary.regex_known(context):
        return []
    candidates: list[Candidate] = []
    span: list[str] = []

    def close_span() -> None:
        nonlocal span
        while span:
            candidates.append(Candidate(" ".join(span[:_RUN_SPLIT_WORDS]), context))
            span = span[_RUN_SPLIT_WORDS:]

    for word, after_connector in run:
        if vocabulary.knows(word):
            close_span()
            continue
        if after_connector:
            close_span()
        span.append(word)
    close_span()
    return candidates
