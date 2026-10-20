"""Word tokenisation and normalisation shared by the allowlists and the closed-world check."""

from __future__ import annotations

import re
import unicodedata

# A word: letters with optional internal apostrophes or hyphens ("O'Neil", "Sous-Traitance").
WORD_RE = re.compile(r"[^\W\d_]+(?:['’\-][^\W\d_]+)*")

_POSSESSIVE_RE = re.compile(r"['’]s$", re.IGNORECASE)
_ELISION_RE = re.compile(r"^(?:[cdjlmnst]|qu|jusqu|lorsqu|puisqu)['’](?=[^\W\d_])", re.IGNORECASE)


def strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def norm(word: str) -> str:
    """Case- and form-insensitive key of a word."""
    return unicodedata.normalize("NFKC", word).replace("’", "'").casefold()


def keys(word: str) -> tuple[str, str]:
    """Lookup keys of a word: normalised, and normalised without accents."""
    key = norm(word)
    return key, strip_accents(key)


def strip_possessive(word: str) -> str:
    return _POSSESSIVE_RE.sub("", word)


def strip_elision(word: str) -> str:
    """Remove a French elided article or pronoun ("l'", "d'", "qu'") from the front of a word."""
    return _ELISION_RE.sub("", word)


_INFLECTIONS = ("ings", "ing", "ed", "ly", "ments", "ment", "ness")


def word_stems(key: str) -> list[str]:
    """Candidate base forms of an (already normalised) English word.

    Plurals ("slabs", "bodies"), past tenses and participles ("filed", "drained", "stopped",
    "applied"), gerunds ("draining", "curating") and adverbs. Agent nouns ("-er") are left out on
    purpose: too many surnames would become common words. Bases have at least three letters.
    """
    stems: list[str] = []
    if len(key) > 4 and key.endswith("ies"):
        stems.append(key[:-3] + "y")
    if len(key) > 3 and key.endswith("es"):
        stems.append(key[:-2])
    if len(key) > 2 and key.endswith("s") and not key.endswith("ss"):
        stems.append(key[:-1])
    for suffix in _INFLECTIONS:
        if not key.endswith(suffix) or len(key) - len(suffix) < 3:
            continue
        base = key[: -len(suffix)]
        stems.extend((base, base + "e"))
        if base[-1] == base[-2]:
            stems.append(base[:-1])
        if base.endswith("i"):
            stems.append(base[:-1] + "y")
    return stems


def is_capitalised(word: str) -> bool:
    """Starts with an upper-case letter, or is camel-case such as ``iPhone``."""
    if not word:
        return False
    if word[0].isupper():
        return True
    return any(ch.isupper() for ch in word[1:])


def is_roman_numeral(word: str) -> bool:
    return bool(
        re.fullmatch(r"M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})", word)
    ) and bool(word)
