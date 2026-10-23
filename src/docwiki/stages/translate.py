"""Stage ``translate`` — the mirror of the wiki in its other languages (v1.7, ADR 0012).

A domain pack that declares ``wiki_languages: [fr, en]`` compiles its wiki in French (the
canonical language, ``wiki/<path>``) and gets an English mirror under ``wiki/en/<same path>``:

* source, entity and topic pages are translated by the ``fast`` model, **prose only**. The page
  body is cut into segments: headings the code generated and sentences it wrote without fields
  are mapped through the string tables (no model); titles, tables, footnote definitions, code,
  blockquotes (the documents' own words), the backlinks list and the pack banner are kept
  verbatim; every other line is a segment. Inside a segment, links, footnote markers and code
  spans are masked as placeholders (``⟦1⟧``) that the model must copy; they are restored from
  the canonical page, so link targets and citations never pass through the model;
* in the frontmatter only ``summary`` and the ``subject`` of each ``contradiction_pairs`` item
  are translated; the title, names, aliases, ids, numbers and every other field are copied;
* a deterministic check (:func:`check_translation`) compares each segment with its translation:
  placeholders, numbers, dates, document numbers, amounts and locked terms must be identical
  and no banned rendering of a locked term may appear. A locked term the model wrote as its
  own word where its placeholder was is put back as the placeholder first
  (:func:`repair_terms`). The rejected segments only are asked again once, with their problems
  listed (one segment per call when the model merged or dropped segments of a batch); when one
  fails again the page is kept untranslated, with the
  :func:`~docwiki.contracts.i18n.untranslated_marker` line and a run warning (gate G17 warns);
* the result is cached in the artifact store under
  ``cache_key("translate", [content hash, target language, locked-terms digest],
  STAGE_VERSION, PROMPT_VERSION, model)``: the content hash covers only what the model reads
  (the masked segments and the source language), so a rebuild without a change costs nothing.

The pages the code builds (views, hubs, indexes, glossary, log) are not translated: the
pipeline rebuilds them in the mirror language from the mirror pages, then
:func:`relocate_page` moves every mirror page under ``<lang>/`` and rewrites its links (to the
mirror page when there is one, else to the canonical page or evidence).
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from docwiki.contracts._base import canonical_json, sha256_hex
from docwiki.contracts.fences import FenceTracker
from docwiki.contracts.i18n import CORE_STRINGS, Strings, language_name
from docwiki.contracts.markdown import (
    BACKLINKS_END,
    BACKLINKS_START,
    FOOTNOTE_DEF_RE,
    extract_headings,
    relative_link,
    resolve_href,
)
from docwiki.contracts.pages import Page, TopicFrontmatter
from docwiki.contracts.safety import detect_injection
from docwiki.domain.models import DomainPack
from docwiki.llm.client import LlmClient
from docwiki.llm.errors import LlmError
from docwiki.stages.classify import data_nonce
from docwiki.stages.llm_failures import describe_failure, is_systemic
from docwiki.stages.prompts import load_prompt

__all__ = [
    "MAX_BATCH_CHARS",
    "PROMPT_VERSION",
    "SCHEMA_NAME",
    "STAGE_VERSION",
    "TRANSLATED_TYPES",
    "PagePlan",
    "Segment",
    "TranslatedSegment",
    "TranslationOutput",
    "TranslationResult",
    "Vocabulary",
    "anchor_map",
    "assemble_mirror",
    "check_translation",
    "language_name",
    "plan_page",
    "relocate_page",
    "repair_terms",
    "rewrite_links",
    "translate_plan",
    "translation_digest",
    "unrelocate_text",
]

STAGE_VERSION = "4"
PROMPT_VERSION = load_prompt("translate").version
SCHEMA_NAME = "translate_page"
TRANSLATED_TYPES = frozenset({"source", "entity", "topic"})
"""Page types translated by the model; the other mirrored types are rebuilt by code."""
MAX_BATCH_CHARS = 24_000
"""Segment characters per model call (a long source page takes several calls)."""
MAX_OUTPUT_TOKENS = 16_000

_HEADING_RE = re.compile(r"^(?P<marks>#{1,6})[ \t]+(?P<text>.*?)[ \t]*#*[ \t]*$")
_LIST_RE = re.compile(r"^(?P<prefix>\s*(?:[-*+]|\d+[.)])\s+)(?P<text>\S.*)$")
_TABLE_RE = re.compile(r"^\s*\|")
_QUOTE_RE = re.compile(r"^\s*>")
_COMMENT_RE = re.compile(r"^\s*<!--.*?-->\s*$", re.DOTALL)
_PROTECTED_RE = re.compile(
    r"(?P<code>(`+)(?:(?!\2).)+?\2)"
    r"|(?P<link>!?\[(?:[^\[\]\\]|\\.|\[(?:[^\[\]\\]|\\.)*\])*\](?:\([^)\n]*\)|\[[^\]\n]*\]))"
    r"|(?P<footnote>\[\^[^\]\s]+\])"
)
_PLACEHOLDER_RE = re.compile(r"⟦(\d+)⟧")
_NUMBER_RE = re.compile(r"\d+(?:[.,  ]\d+)*")
_DATE_RE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}/\d{1,2}/\d{2,4}\b")
_DOC_NUMBER_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")
_AMOUNT_RE = re.compile(r"\d+(?:[.,  ]\d+)*[   ]?€(?:[   ](?:HT|TTC))?")
_HREF_RE = re.compile(r"(?<!\\)\]\((?P<href>[^)\s]+)\)")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*:")


# -- planning --------------------------------------------------------------------------------


@dataclass(frozen=True)
class Segment:
    """One piece of prose the model translates: ``text`` with its protected tokens masked."""

    id: str
    text: str
    tokens: tuple[str, ...] = ()
    """The masked originals, in placeholder order (``⟦1⟧`` is ``tokens[0]``)."""
    terms: tuple[str | None, ...] = ()
    """For each token, the locked term it is (``None`` for a link, a marker or code)."""


@dataclass
class PagePlan:
    """A canonical page cut into verbatim lines, mapped lines and segments."""

    page: Page
    source_lang: str
    target_lang: str
    lines: list[str | Segment] = field(default_factory=list)
    segments: list[Segment] = field(default_factory=list)
    """Every segment: body lines, ``summary`` and ``subject.<n>`` of the frontmatter."""
    prefixes: dict[str, str] = field(default_factory=dict)
    """Segment id → the Markdown kept before the translated text (list marker, ``> ``, ``## ``)."""

    @property
    def content_hash(self) -> str:
        """Hash of what the model reads (the cache key's content input)."""
        payload = {
            "from": self.source_lang,
            "to": self.target_lang,
            "segments": [[segment.id, segment.text] for segment in self.segments],
        }
        return sha256_hex(canonical_json(payload))


def _mask(text: str) -> tuple[str, tuple[str, ...]]:
    masked, tokens, _ = _mask_terms(text, ())
    return masked, tokens


def _mask_terms(
    text: str, forms: Sequence[tuple[str, re.Pattern[str]]]
) -> tuple[str, tuple[str, ...], tuple[str | None, ...]]:
    """``text`` with links, markers and code masked, then every locked term (``forms``, longest
    first): the model never sees a locked term, so it can neither translate nor drop it."""
    tokens: list[str] = []
    terms: list[str | None] = []

    def replacer(term: str | None) -> Callable[[re.Match[str]], str]:
        def replace(match: re.Match[str]) -> str:
            tokens.append(match.group(0))
            terms.append(term)
            return f"⟦{len(tokens)}⟧"

        return replace

    masked = _PROTECTED_RE.sub(replacer(None), text)
    # amounts are written by code ("2 390,00 € HT", with no-break spaces): the model only moves them
    masked = _AMOUNT_RE.sub(replacer(None), masked)
    for term, pattern in forms:
        masked = pattern.sub(replacer(term), masked)
    return masked, tuple(tokens), tuple(terms)


_REFERENCE_RE = re.compile(
    r"(?:[  ]+(?:n°[  ]?)?(?=[\w/-]*\d)[A-Za-z0-9](?:[\w/-]|[.,](?=\w))*)?"
    r"(?:[  ]+indices?[  ]+[A-Z0-9]\b)?"
)
"""The reference that may follow a locked term (``lot 5``, ``OS n°3``, ``DPGF DEV-2026-031
indice B``): its gloss goes after the reference, never between the term and its reference."""
_LINK_LABEL_RE = re.compile(r"\[(?P<label>.*)\](?:\(|\[)", re.DOTALL)
_SENTENCE_END = ".!?"
_CLOSING = "\"'»”)"


def _link_label(token: str) -> str:
    """The label of a link token (``[DPGF DEV-2026-031](…)`` → ``DPGF DEV-2026-031``); empty
    for an image, a footnote marker, code or an amount."""
    match = _LINK_LABEL_RE.match(token)
    return match.group("label") if match is not None else ""


def _recased(original: str, term: str, sentence_start: bool) -> str:
    """A locked common noun as the translated sentence places it: capitalised at the start of
    a sentence, lower case inside one (an acronym or a name-like term is kept as written)."""
    if not term[:1].islower() or not original[:1].isalpha():
        return original
    if sentence_start:
        return original[:1].upper() + original[1:]
    if original[1:] == original[1:].lower():
        return original[:1].lower() + original[1:]
    return original


def _unmask(
    text: str,
    tokens: Sequence[str],
    terms: Sequence[str | None] = (),
    glosses: Mapping[str, str] | None = None,
    glossed: set[str] | None = None,
    forms: Sequence[tuple[str, re.Pattern[str]]] = (),
    recase: bool = False,
) -> str:
    """``text`` with its placeholders restored.

    With ``glosses``, the first occurrence of each locked term on the page (``glossed``
    collects them) is followed by its gloss in brackets, after the reference that follows the
    term (``lot 5 [gloss]``); a locked term in the label of a link (found with ``forms``) is
    glossed after the link. With ``recase``, a locked common noun takes the case of its place
    in the translated sentence.
    """
    out: list[str] = []
    position = 0
    for match in _PLACEHOLDER_RE.finditer(text):
        out.append(text[position : match.start()])
        position = match.end()
        index = int(match.group(1)) - 1
        original = tokens[index]
        term = terms[index] if index < len(terms) else None
        if term is not None and recase:
            before = "".join(out).rstrip().rstrip(_CLOSING)
            start = not before or before[-1] in _SENTENCE_END
            original = _recased(original, term, start)
        out.append(original)
        if glosses is None or glossed is None:
            continue
        if term is not None:
            named = [term]
        else:
            named = [name for _, _, name in _locked_spans(_link_label(original), forms)]
        owed: list[str] = []
        for name in named:
            if name in glossed:
                continue
            glossed.add(name)
            if glosses.get(name):
                owed.append(glosses[name])
        if owed:
            reference = _REFERENCE_RE.match(text, position)
            if reference is not None:
                out.append(reference.group(0))
                position = reference.end()
            out += [f" [{gloss}]" for gloss in owed]
    out.append(text[position:])
    return "".join(out)


def _fixed_strings(source: Strings, target: Strings) -> tuple[dict[str, str], dict[str, str]]:
    """``(headings, sentences)``: source text → target text of the generated headings and of
    the generated sentences without fields (``Aucun fait daté.``)."""
    headings: dict[str, str] = {}
    sentences: dict[str, str] = {}
    for key in CORE_STRINGS["en"]:
        source_text, target_text = source.table[key], target.table[key]
        if key.startswith("heading."):
            headings.setdefault(source_text, target_text)
        elif "{" not in source_text and source_text.endswith(".") and " " in source_text:
            sentences.setdefault(source_text, target_text)
    return headings, sentences


_LINK_LABEL_KEYS = (
    "links.topic.one",
    "links.topic.other",
    "links.view.one",
    "links.view.other",
    "links.supersedes",
    "links.superseded_by",
)
_LINK_LIST_RE = re.compile(r"^(?P<label>[^⟦\n]+?):[ \u00a0]?(?P<links>⟦\d+⟧(?:, ⟦\d+⟧)*)$")
"""A ``## Related`` item: a label (a string of the table, or an entity type title of the pack)
and only links; it is mapped by code, never sent to the model."""


def _superseded_prefix(strings: Strings) -> str:
    return strings("render.superseded_banner").split("{links}", 1)[0]


def plan_page(page: Page, pack: DomainPack, target_lang: str) -> PagePlan:
    """Cut a canonical content page into verbatim lines and segments to translate."""
    source = pack.strings(page.frontmatter.lang)
    target = pack.strings(target_lang)
    headings, sentences = _fixed_strings(source, target)
    labels = {source(key): target(key) for key in _LINK_LABEL_KEYS}
    superseded = _superseded_prefix(source).strip()
    plan = PagePlan(page=page, source_lang=page.frontmatter.lang, target_lang=target_lang)
    fences = FenceTracker()
    in_backlinks = False
    counter = 0

    forms = Vocabulary.of(pack).forms

    def add(text: str, prefix: str = "") -> Segment:
        nonlocal counter
        counter += 1
        masked, tokens, terms = _mask_terms(text, forms)
        segment = Segment(id=f"s{counter}", text=masked, tokens=tokens, terms=terms)
        plan.segments.append(segment)
        plan.prefixes[segment.id] = prefix
        return segment

    for line in page.body.split("\n"):
        if fences.feed(line):
            plan.lines.append(line)
            continue
        stripped = line.strip()
        if stripped == BACKLINKS_START:
            in_backlinks = True
        if stripped == BACKLINKS_END:
            in_backlinks = False
        heading = _HEADING_RE.match(line)
        verbatim = (
            not stripped
            or _COMMENT_RE.match(line)
            or _TABLE_RE.match(line)
            or FOOTNOTE_DEF_RE.match(stripped)
        )
        if verbatim:
            plan.lines.append(line)
        elif heading is not None:
            marks, text = heading.group("marks"), heading.group("text")
            if len(marks) == 1:
                plan.lines.append(line)  # the title: never translated
            elif text in headings:
                plan.lines.append(f"{marks} {headings[text]}")
            elif in_backlinks:
                plan.lines.append(line)
            else:
                plan.lines.append(add(text, f"{marks} "))
        elif stripped in sentences:
            plan.lines.append(line.replace(stripped, sentences[stripped]))
        elif in_backlinks:
            plan.lines.append(line)
        elif _QUOTE_RE.match(line):
            if superseded and stripped.startswith(superseded):
                # the generated superseded banner is translated; the pack banner and the
                # documents' own words (blockquotes) are not
                plan.lines.append(add(stripped[1:].strip(), "> "))
            else:
                plan.lines.append(line)
        else:
            item = _LIST_RE.match(line)
            masked = _mask(item.group("text"))[0] if item is not None else ""
            related = _LINK_LIST_RE.match(masked) if item is not None else None
            if item is not None and related is not None:
                label = related.group("label").strip()
                if label in labels:
                    start = item.start("text") + len(related.group("label"))
                    plan.lines.append(f"{item.group('prefix')}{labels[label]}{line[start:]}")
                else:
                    plan.lines.append(line)  # an entity type title of the pack: kept
            elif item is not None:
                plan.lines.append(add(item.group("text"), item.group("prefix")))
            else:
                indent = line[: len(line) - len(line.lstrip())]
                plan.lines.append(add(stripped, indent))
    fm = page.frontmatter
    if fm.summary.strip():
        masked, tokens, terms = _mask_terms(fm.summary, forms)
        plan.segments.append(Segment(id="summary", text=masked, tokens=tokens, terms=terms))
    if isinstance(fm, TopicFrontmatter):
        for index, pair in enumerate(fm.contradiction_pairs, start=1):
            masked, tokens, terms = _mask_terms(pair.subject, forms)
            plan.segments.append(
                Segment(id=f"subject.{index}", text=masked, tokens=tokens, terms=terms)
            )
    return plan


# -- the preservation check -----------------------------------------------------------------


def _locked_spans(
    text: str, forms: Sequence[tuple[str, re.Pattern[str]]]
) -> list[tuple[int, int, str]]:
    """``(start, end, term)`` of each locked term written in ``text`` (any of its forms, longest
    first, no overlap), in text order."""
    taken: list[tuple[int, int, str]] = []
    for term, pattern in forms:
        for match in pattern.finditer(text):
            start, end = match.span()
            if any(start < other_end and other_start < end for other_start, other_end, _ in taken):
                continue
            taken.append((start, end, term))
    return sorted(taken)


def _locked_counts(text: str, forms: Sequence[tuple[str, re.Pattern[str]]]) -> Counter[str]:
    """Occurrences of each locked term (any of its forms, longest first, no overlap)."""
    return Counter(term for _, _, term in _locked_spans(text, forms))


def _whole_word(text: str) -> re.Pattern[str]:
    """``text`` as whole words, any case; a one-word common noun (``lot``, ``situation``) also
    matches its plural in ``s`` (``lots``, ``situations``), whichever forms the pack lists."""
    words = text.split()
    phrase = r"\s+".join(re.escape(word) for word in words)
    plural = (
        len(words) == 1
        and text != text.upper()
        and text[-1].isalpha()
        and text[-1].lower() not in "sx"
    )
    return re.compile(rf"(?<!\w){phrase}{'s?' if plural else ''}(?!\w)", re.IGNORECASE)


@dataclass(frozen=True)
class Vocabulary:
    """The locked terms of a pack (each with its written forms) and their banned renderings."""

    forms: tuple[tuple[str, re.Pattern[str]], ...] = ()
    banned: tuple[tuple[str, str, re.Pattern[str]], ...] = ()

    @classmethod
    def of(cls, pack: DomainPack) -> Vocabulary:
        forms: list[tuple[str, str]] = []
        banned: list[tuple[str, str, re.Pattern[str]]] = []
        for term in pack.terms.terms:
            for form in {term.term, *term.forms}:
                if form.strip():
                    forms.append((term.term, form))
            for rendering in term.banned:
                if rendering.strip():
                    pattern = re.compile(
                        r"(?<!\w)"
                        + r"\s+".join(re.escape(word) for word in rendering.split())
                        + r"(?:e?s)?(?!\w)",
                        re.IGNORECASE,
                    )
                    banned.append((term.term, rendering, pattern))
        forms.sort(key=lambda item: (-len(item[1]), item[1]))
        return cls(
            forms=tuple((term, _whole_word(form)) for term, form in forms),
            banned=tuple(banned),
        )

    def digest(self) -> str:
        payload = [[term, pattern.pattern] for term, pattern in self.forms]
        payload += [[term, rendering] for term, rendering, _ in self.banned]
        return sha256_hex(canonical_json(payload))


def check_translation(source: str, translated: str, vocabulary: Vocabulary) -> list[str]:
    """What a translation of one segment changed (``[]`` when it may be used).

    Placeholders, numbers, dates, document numbers, amounts and locked terms must be identical
    (as multisets) and no banned rendering of a locked term may appear more often than in the
    source; the translation may not add links, footnotes or code of its own.
    """
    problems: list[str] = []
    if not translated.strip() and source.strip():
        return ["the translation is empty"]
    if Counter(_PLACEHOLDER_RE.findall(source)) != Counter(_PLACEHOLDER_RE.findall(translated)):
        problems.append("placeholders (links, citations, code) changed")
    if _PROTECTED_RE.search(_PLACEHOLDER_RE.sub("", translated)) or "`" in translated:
        problems.append("links, footnotes or code were added")
    for name, pattern in (
        ("dates", _DATE_RE),
        ("document numbers", _DOC_NUMBER_RE),
        ("amounts", _AMOUNT_RE),
        ("numbers", _NUMBER_RE),
    ):
        before = Counter(pattern.findall(_PLACEHOLDER_RE.sub(" ", source)))
        after = Counter(pattern.findall(_PLACEHOLDER_RE.sub(" ", translated)))
        if before != after:
            missing = sorted((before - after).elements())
            extra = sorted((after - before).elements())
            problems.append(f"{name} changed (missing {missing}, added {extra})")
    if vocabulary.forms:
        before_terms = _locked_counts(source, vocabulary.forms)
        after_terms = _locked_counts(translated, vocabulary.forms)
        if before_terms != after_terms:
            changed = sorted(set(before_terms) ^ set(after_terms)) or sorted(
                term for term in before_terms if before_terms[term] != after_terms[term]
            )
            problems.append(
                f"locked terms changed: {', '.join(changed)} (keep each term placeholder exactly "
                "once and never write these words yourself)"
            )
    for term, rendering, pattern in vocabulary.banned:
        if len(pattern.findall(translated)) > len(pattern.findall(source)):
            problems.append(
                f'"{rendering}" is a banned rendering of the locked term "{term}": rephrase '
                f'without the words "{rendering}" (for example "person in charge")'
            )
    for marker in ("<", ">", "://"):
        if translated.count(marker) > source.count(marker):
            problems.append(f"{marker!r} was added (HTML or a link)")
    if detect_injection(translated) and not detect_injection(source):
        problems.append("the translation addresses an AI system")
    return problems


def repair_terms(segment: Segment, translated: str, vocabulary: Vocabulary) -> str:
    """``translated`` with each locked term the model wrote as its own word (any written form
    of that term, case-insensitive, whole words) where the term's placeholder is missing put
    back as that placeholder, in order.

    A locked term is never translated, so writing its word instead of its placeholder changes
    nothing on the page; the repair only lets :func:`check_translation` see the placeholder.
    A missing placeholder replaced by anything else (another word, another term) is left
    missing and still rejected, and a term's word with no missing placeholder of that term
    (an English "a lot of") is left as written and still rejected.
    """
    missing: dict[str, list[int]] = {}
    present = Counter(_PLACEHOLDER_RE.findall(translated))
    for index, term in enumerate(segment.terms, start=1):
        if term is not None and not present[str(index)]:
            missing.setdefault(term, []).append(index)
    if not missing:
        return translated
    parts: list[str] = []
    position = 0
    for start, end, term in _locked_spans(translated, vocabulary.forms):
        queue = missing.get(term)
        if not queue:
            continue
        parts += [translated[position:start], f"⟦{queue.pop(0)}⟧"]
        position = end
    return "".join(parts) + translated[position:]


# -- the model call --------------------------------------------------------------------------


class TranslatedSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(description="The id of the input segment.")
    text: str = Field(description="The translation of that segment, placeholders kept.")


class TranslationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    segments: list[TranslatedSegment] = Field(
        description="One item per input segment, same ids, same order."
    )


@dataclass
class TranslationResult:
    """The translations of one plan (``untranslated`` when they were rejected twice)."""

    texts: dict[str, str]
    status: str = "translated"
    problems: list[str] = field(default_factory=list)
    calls: int = 0

    def to_json(self) -> bytes:
        data = {"status": self.status, "texts": self.texts, "problems": self.problems}
        return json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")

    @classmethod
    def from_json(cls, data: bytes) -> TranslationResult:
        raw = json.loads(data)
        return cls(
            texts=dict(raw.get("texts") or {}),
            status=str(raw.get("status") or "translated"),
            problems=list(raw.get("problems") or []),
        )


def translation_digest(plan: PagePlan, vocabulary: Vocabulary) -> list[str]:
    """Inputs of the translate cache key: content hash, target language, vocabulary."""
    return [
        f"content:{plan.content_hash}",
        f"lang:{plan.target_lang}",
        f"terms:{vocabulary.digest()}",
    ]


def _batches(segments: Sequence[Segment]) -> list[list[Segment]]:
    batches: list[list[Segment]] = [[]]
    size = 0
    for segment in segments:
        if batches[-1] and size + len(segment.text) > MAX_BATCH_CHARS:
            batches.append([])
            size = 0
        batches[-1].append(segment)
        size += len(segment.text)
    return [batch for batch in batches if batch]


def _segment_payload(segment: Segment) -> dict[str, Any]:
    """One segment as the model reads it; ``terms`` names the trade terms behind placeholders
    (the model keeps the placeholder and builds the sentence around the word it stands for)."""
    payload: dict[str, Any] = {"id": segment.id, "text": segment.text}
    terms = {
        f"⟦{index}⟧": segment.tokens[index - 1]
        for index, term in enumerate(segment.terms, start=1)
        if term is not None
    }
    if terms:
        payload["terms"] = terms
    return payload


def _request(
    plan: PagePlan, batch: Sequence[Segment], pack: DomainPack, problems: Sequence[str]
) -> str:
    payload = json.dumps(
        {"segments": [_segment_payload(segment) for segment in batch]},
        ensure_ascii=False,
        indent=0,
    )
    nonce = data_nonce(payload)
    lines = [
        "# Task",
        f"Translate every segment from {language_name(plan.source_lang)} into "
        f"{language_name(plan.target_lang)}.",
        "",
        "# Page",
        f"- type: {plan.page.frontmatter.type}",
        f"- title (never translated): {plan.page.frontmatter.title}",
    ]
    banned = sorted({item for term in pack.terms.terms for item in term.banned})
    if banned:
        lines += [
            "",
            "# Banned renderings (reviewed domain pack)",
            "The trade terms are placeholders like the links: keep them. Never write: "
            + ", ".join(repr(item) for item in banned)
            + ".",
        ]
    if problems:
        lines += [
            "",
            "# Your previous translation was rejected",
            "Fix these problems; everything else in the rules still applies:",
            *(f"- {problem}" for problem in problems),
        ]
    lines += ["", "# Segments", f"BEGIN SEGMENTS {nonce}", payload, f"END SEGMENTS {nonce}"]
    return "\n".join(lines)


async def _translate_batch(
    llm: LlmClient,
    plan: PagePlan,
    batch: Sequence[Segment],
    pack: DomainPack,
    problems: Sequence[str],
) -> tuple[dict[str, str], list[str]]:
    """Translations of one batch and the problems found in them."""
    try:
        result = await llm.structured(
            tier="fast",
            system=load_prompt("translate").text,
            user=_request(plan, batch, pack, problems),
            output=TranslationOutput,
            schema_name=SCHEMA_NAME,
            prompt_version=PROMPT_VERSION,
            max_output_tokens=MAX_OUTPUT_TOKENS,
            metadata={
                "stage": "translate",
                "page_id": plan.page.frontmatter.id,
                "lang": plan.target_lang,
            },
        )
    except LlmError as exc:
        if is_systemic(exc):
            raise
        return {}, [f"the model call failed: {describe_failure(exc)}"]
    output: TranslationOutput = result.output
    texts = {item.id: item.text for item in output.segments}
    found: list[str] = []
    wanted = [segment.id for segment in batch]
    if [item.id for item in output.segments] != wanted:
        found.append("segments were merged, dropped, added or reordered")
    return texts, found


async def translate_plan(
    llm: LlmClient, plan: PagePlan, pack: DomainPack, vocabulary: Vocabulary | None = None
) -> TranslationResult:
    """Translate every segment of ``plan``; retry the rejected segments once, then keep the
    page untranslated.

    The first attempt sends the segments in batches. A segment whose translation passes
    :func:`check_translation` (after :func:`repair_terms`) is kept; only the rejected ones are
    sent again, with their own problems listed. When a whole batch failed (the model call
    failed, or it merged, dropped, added or reordered segments) none of its translations is
    trusted and its segments are retried one per call. The page is ``translated`` only when
    every segment passed.
    """
    vocabulary = vocabulary or Vocabulary.of(pack)
    result = TranslationResult(texts={})
    if not plan.segments:
        return result
    accepted: dict[str, str] = {}
    pending = list(plan.segments)
    problems: dict[str, list[str]] = {}
    alone: set[str] = set()  # segments of a batch that failed as a whole: one per call
    for _attempt in range(2):
        batches = _batches([s for s in pending if s.id not in alone])
        batches += [[segment] for segment in pending if segment.id in alone]
        failed: dict[str, list[str]] = {}
        alone = set()
        for batch in batches:
            previous = [f"{s.id}: {item}" for s in batch for item in problems.get(s.id, ())]
            got, found = await _translate_batch(llm, plan, batch, pack, previous[:30])
            result.calls += 1
            if found:  # the batch failed as a whole
                failed.update({segment.id: list(found) for segment in batch})
                alone.update(segment.id for segment in batch)
                continue
            for segment in batch:
                translated = repair_terms(segment, got[segment.id], vocabulary)
                rejected = check_translation(segment.text, translated, vocabulary)
                if rejected:
                    failed[segment.id] = rejected
                else:
                    accepted[segment.id] = translated
        if not failed:
            result.texts = {segment.id: accepted[segment.id] for segment in plan.segments}
            result.status = "translated"
            return result
        pending = [segment for segment in plan.segments if segment.id in failed]
        problems = failed
    result.texts = {segment.id: segment.text for segment in plan.segments}
    result.status = "untranslated"
    result.problems = [
        f"{segment.id}: {item}" for segment in pending for item in problems[segment.id]
    ]
    return result


# -- the mirror page --------------------------------------------------------------------------


def assemble_mirror(plan: PagePlan, result: TranslationResult, pack: DomainPack) -> Page:
    """The mirror page of ``plan`` at the canonical path (:func:`relocate_page` moves it)."""
    texts = result.texts
    by_id = {segment.id: segment for segment in plan.segments}
    glosses = (
        {term.term: term.gloss for term in pack.terms.terms if term.gloss}
        if plan.target_lang == "en" and result.status == "translated"
        else None
    )
    glossed: set[str] = set()
    forms = Vocabulary.of(pack).forms if glosses is not None else ()
    recase = result.status == "translated"
    lines: list[str] = []
    for line in plan.lines:
        if isinstance(line, Segment):
            text = texts.get(line.id, line.text)
            prefix = plan.prefixes.get(line.id, "")
            # never a gloss in a heading: the first use in the text below gets it
            in_heading = prefix.lstrip().startswith("#")
            restored = _unmask(
                text,
                line.tokens,
                line.terms,
                None if in_heading else glosses,
                glossed,
                forms,
                recase,
            )
            lines.append(prefix + restored)
        else:
            lines.append(line)
    if result.status != "translated":
        marker = pack.strings(plan.target_lang)("mirror.untranslated", lang=plan.source_lang)
        position = next((index + 1 for index, line in enumerate(lines) if line.startswith("# ")), 0)
        lines[position:position] = ["", marker]
    fm = plan.page.frontmatter
    data: dict[str, Any] = fm.model_dump(by_alias=True)
    data.update(lang=plan.target_lang, translation_of=fm.id)

    def text_of(segment_id: str, fallback: str) -> str:
        segment = by_id.get(segment_id)
        if segment is None:
            return fallback
        text = _unmask(
            texts.get(segment_id, segment.text), segment.tokens, segment.terms, recase=recase
        )
        return " ".join(text.split()) or fallback

    data["summary"] = text_of("summary", fm.summary)
    if isinstance(fm, TopicFrontmatter):
        data["contradiction_pairs"] = [
            {"sources": list(pair.sources), "subject": text_of(f"subject.{n}", pair.subject)}
            for n, pair in enumerate(fm.contradiction_pairs, start=1)
        ]
    frontmatter = type(fm).model_validate(data)
    return Page(path=plan.page.path, frontmatter=frontmatter, body="\n".join(lines))


def anchor_map(canonical: Page, mirror: Page) -> dict[str, str]:
    """Canonical anchor → mirror anchor of the same heading (when both pages have the same
    headings in the same order, which a plan guarantees)."""
    before = extract_headings(canonical.body)
    after = extract_headings(mirror.body)
    if len(before) != len(after):
        return {}
    return {
        old.anchor: new.anchor
        for old, new in zip(before, after, strict=True)
        if old.anchor and new.anchor
    }


def relocate_page(
    page: Page,
    lang: str,
    mirrored: Iterable[str],
    anchors: Mapping[str, Mapping[str, str]] | None = None,
) -> Page:
    """``page`` (a mirror page still at its canonical path) moved under ``<lang>/``.

    Every link is rewritten: to the mirror of its target when ``mirrored`` (canonical paths)
    has one, else to the canonical page, sidecar or original. With ``anchors`` (canonical path
    → canonical anchor → mirror anchor; for translated pages, whose links carry canonical
    anchors) the anchor follows the translated heading.
    """
    mirrored_paths = set(mirrored)
    new_path = f"{lang}/{page.path}"

    def target_for(target: str, anchor: str | None) -> tuple[str, str | None]:
        if anchors is not None and anchor:
            anchor = anchors.get(target, {}).get(anchor, anchor)
        return (f"{lang}/{target}" if target in mirrored_paths else target), anchor

    body = rewrite_links(page.body, page.path, new_path, target_for)
    fm = page.frontmatter
    if fm.translation_of is None or fm.lang != lang:
        fm = type(fm).model_validate(
            {**fm.model_dump(by_alias=True), "lang": lang, "translation_of": fm.id}
        )
    return Page(path=new_path, frontmatter=fm, body=body)


def rewrite_links(
    text: str,
    old_path: str,
    new_path: str,
    target_for: Callable[[str, str | None], tuple[str, str | None]],
) -> str:
    """``text`` written at ``old_path`` with its relative links rewritten for ``new_path``:
    ``target_for(target, anchor)`` gives the new target (content-namespace path) and anchor of
    each link. Links in code, external links and same-page anchors are left alone."""

    def rewrite(match: re.Match[str]) -> str:
        href = match.group("href")
        if _SCHEME_RE.match(href) or href.startswith("#"):
            return match.group(0)
        resolved = resolve_href(old_path, href)
        if resolved.error or resolved.external or resolved.path is None:
            return match.group(0)
        target, anchor = target_for(resolved.path, resolved.anchor)
        return f"]({relative_link(new_path, target)}{'#' + anchor if anchor else ''})"

    lines: list[str] = []
    fences = FenceTracker()
    for line in text.split("\n"):
        lines.append(line if fences.feed(line) else _HREF_RE.sub(rewrite, line))
    return "\n".join(lines)


def unrelocate_text(text: str, lang: str, path: str) -> str:
    """A mirror file's text (``<lang>/<path>``, e.g. the previous mirror ``log.md``) with its
    links rewritten as if it were written at ``path`` in the canonical layout, so that the
    builders can carry it over; :func:`relocate_page` moves it back."""
    prefix = f"{lang}/"

    def target_for(target: str, anchor: str | None) -> tuple[str, str | None]:
        return target.removeprefix(prefix), anchor

    return rewrite_links(text, f"{prefix}{path}", path, target_for)
