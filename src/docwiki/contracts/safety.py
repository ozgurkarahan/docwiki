"""Markdown safety (wiki-contract §10): sanitisation, injection heuristics and gate checks.

* :func:`sanitize_markdown` rewrites untrusted Markdown into the safe subset (no raw HTML, no
  comments except the backlinks markers, no ``javascript:``/``data:`` URLs, no external links or
  images; bare URLs are defanged into code spans).
* :func:`find_violations` reports what a renderer would expose (used by gates G05/G08).
* :func:`detect_injection` / :func:`neutralize_injections` flag text addressed to AI systems.

The guarantee tested in the suite: ``find_violations(sanitize_markdown(x)[0]) == []`` for any ``x``.
"""

from __future__ import annotations

import html
import re
import unicodedata
from collections.abc import Callable, Iterable
from typing import Literal
from urllib.parse import unquote

from docwiki.contracts._base import ContractModel
from docwiki.contracts.fences import FenceTracker
from docwiki.contracts.markdown import (
    BACKLINKS_END,
    BACKLINKS_START,
    FOOTNOTE_DEF_RE,
    markdown_parser,
)

__all__ = [
    "Finding",
    "FindingKind",
    "detect_injection",
    "find_violations",
    "neutralize_injections",
    "sanitize_markdown",
]

FindingKind = Literal[
    "control-char",
    "raw-html",
    "html-comment",
    "marker",
    "unsafe-url",
    "external-link",
    "external-image",
    "absolute-link",
    "bare-url",
    "injection",
]


class Finding(ContractModel):
    """One safety finding. ``line`` is 1-based when known."""

    kind: FindingKind
    message: str
    line: int | None = None
    excerpt: str = ""
    rule: str | None = None


MARKERS = (BACKLINKS_START, BACKLINKS_END)
UNSAFE_SCHEMES = frozenset({"javascript", "vbscript", "data", "file", "blob", "about"})

_INVISIBLE_RE = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\u2066-\u2069\ufeff]")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_PLACEHOLDER_RE = re.compile("\ue000(\\d+)\ue001")
_CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)([^\n]+?)(?<!`)\1(?!`)")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_DANGEROUS_BLOCK_RE = re.compile(
    r"<(script|style|iframe|object|embed|noscript|textarea|template|svg|math|xmp|title)\b[^>]*>"
    r".*?</\1\s*>",
    re.DOTALL | re.IGNORECASE,
)
_TAG_RE = re.compile(r"</?[A-Za-z][A-Za-z0-9\-]*(?:\s[^<>]*?)?/?>", re.DOTALL)
_SPECIAL_RE = re.compile(r"<!\[CDATA\[.*?\]\]>|<![A-Za-z][^>]*>|<\?.*?\?>", re.DOTALL)
_AUTOLINK_RE = re.compile(
    r"<(?:[A-Za-z][A-Za-z0-9+.\-]{1,31}:[^\s<>]*|[A-Za-z0-9.!#$%&'*+/=?^_`{|}~\-]+@[A-Za-z0-9]"
    r"(?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9\-]{0,61}[A-Za-z0-9])?)*)>"
)
_LEFTOVER_LT_RE = re.compile(r"(?<!\\)<(?=[A-Za-z!?/])")
_INLINE_LINK_RE = re.compile(
    r"(?P<bang>!?)\[(?P<text>(?:[^\[\]\\\n]|\\.|\[(?:[^\[\]\\\n]|\\.)*\])*)\]"
    r"\(\s*(?P<dest><[^<>\n]*>|(?:[^\s()\\]|\\.|\((?:[^\s()\\]|\\.)*\))*)"
    r"(?:\s+(?:\"[^\"\n]*\"|'[^'\n]*'|\([^()\n]*\)))?\s*\)"
)
_REF_DEF_RE = re.compile(
    r"^ {0,3}\[(?!\^)(?:[^\]\\\n]|\\.)+\]:[ \t]*(?P<dest><[^<>\n]*>|\S+).*$", re.MULTILINE
)
_SCHEME_RE = re.compile(r"^\s*([A-Za-z][A-Za-z0-9+.\-]*):")
_BARE_URL_RE = re.compile(
    r"(?<![\w/@`])(?:(?:https?|ftp)://[^\s<>`\[\]()]+|www\.[A-Za-z0-9\-]+\.[^\s<>`\[\]()]+)"
)
_EMAIL_RE = re.compile(r"(?<![\w.+\-/`])[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+")
_TRAILING_PUNCT_RE = re.compile(r"[.,:;!?'\"*_~]+$")


def _excerpt(text: str, limit: int = 80) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def _classify_url(url: str, allowed_hosts: Iterable[str]) -> tuple[str, str | None]:
    """Return (``internal``|``anchor``|``external``|``unsafe``|``absolute``, scheme).

    Entities and percent-escapes are decoded and whitespace removed before the scheme is read,
    because browsers ignore tabs/newlines inside URLs (``java\\tscript:``).
    """
    value = url.strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1]
    probe = re.sub(r"[\s\x00-\x1f]", "", unquote(html.unescape(value)))
    if not probe:
        return "internal", None
    if probe.startswith("#"):
        return "anchor", None
    if probe.startswith("//") or probe.startswith("\\\\"):
        return "external", ""
    match = _SCHEME_RE.match(probe)
    if match:
        scheme = match.group(1).lower()
        if scheme in UNSAFE_SCHEMES:
            return "unsafe", scheme
        host = re.sub(r"^[a-z0-9+.\-]+://", "", probe, flags=re.IGNORECASE).split("/", 1)[0]
        if scheme in ("http", "https") and host.lower() in {h.lower() for h in allowed_hosts}:
            return "internal", scheme
        return "external", scheme
    if probe.startswith("/") or probe.startswith("\\"):
        return "absolute", None
    return "internal", None


def _strip_invisible(text: str, findings: list[Finding]) -> str:
    cleaned = _CONTROL_RE.sub("", _INVISIBLE_RE.sub("", text))
    if cleaned != text:
        findings.append(
            Finding(kind="control-char", message="removed control or invisible characters")
        )
    return cleaned


def _protect_fenced_blocks(text: str, protect: Callable[[str], str]) -> str:
    """Replace each fenced code block (CommonMark rules, fence lines included) by ``protect``.

    Uses the same tracker as citation verification and rendering, so a line that only looks like
    a fence (for example three backticks followed by an info string holding a backtick) is text,
    and the HTML around it is sanitised.
    """
    lines = text.split("\n")
    out: list[str] = []
    block: list[str] = []
    tracker = FenceTracker()
    for line in lines:
        if tracker.feed(line):
            block.append(line)
            if not tracker.inside:
                out.append(protect("\n".join(block)))
                block = []
            continue
        out.append(line)
    if block:
        out.append(protect("\n".join(block)))
    return "\n".join(out)


def sanitize_markdown(
    markdown: str,
    *,
    allow_markers: bool = True,
    allowed_hosts: Iterable[str] = (),
) -> tuple[str, list[Finding]]:
    """Return ``(clean_markdown, findings)``.

    Removes HTML tags (keeping their text), dangerous elements with their content, comments
    (except the two backlinks markers when ``allow_markers``), unsafe-scheme and external links
    (keeping link text), external images (keeping alt text) and external reference definitions.
    Bare URLs, e-mail addresses and autolinks to external targets become inline code (not
    clickable). Code spans and fenced code blocks are left untouched.
    """
    hosts = tuple(allowed_hosts)
    findings: list[Finding] = []
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\ue000", "").replace("\ue001", "")
    text = _strip_invisible(text, findings)

    protected: list[str] = []

    def protect(value: str) -> str:
        protected.append(value)
        return f"\ue000{len(protected) - 1}\ue001"

    text = _protect_fenced_blocks(text, protect)
    text = _CODE_SPAN_RE.sub(lambda m: protect(m.group(0)), text)

    def on_comment(match: re.Match[str]) -> str:
        source = match.string
        alone = (match.start() == 0 or source[match.start() - 1] == "\n") and (
            match.end() == len(source) or source[match.end()] == "\n"
        )
        if allow_markers and match.group(0) in MARKERS and alone:
            return protect(match.group(0))
        kind = "marker" if match.group(0) in MARKERS else "html-comment"
        findings.append(
            Finding(kind=kind, message="removed HTML comment", excerpt=_excerpt(match.group(0)))
        )
        return ""

    def on_tag(match: re.Match[str]) -> str:
        findings.append(
            Finding(kind="raw-html", message="removed raw HTML", excerpt=_excerpt(match.group(0)))
        )
        return ""

    for _ in range(10):
        before = text
        text = _COMMENT_RE.sub(on_comment, text)
        if "<!--" in text:
            findings.append(Finding(kind="html-comment", message="removed unterminated comment"))
            text = text.replace("<!--", "")
        text = _DANGEROUS_BLOCK_RE.sub(on_tag, text)
        text = _SPECIAL_RE.sub(on_tag, text)
        text = _TAG_RE.sub(on_tag, text)
        if text == before:
            break

    def on_autolink(match: re.Match[str]) -> str:
        target = match.group(0)[1:-1]
        kind, scheme = _classify_url(target, hosts)
        if kind == "unsafe":
            findings.append(
                Finding(
                    kind="unsafe-url",
                    message=f"removed {scheme}: autolink",
                    excerpt=_excerpt(target),
                )
            )
            return ""
        if kind == "internal" and scheme:
            return protect(match.group(0))
        findings.append(
            Finding(kind="external-link", message="defanged autolink", excerpt=_excerpt(target))
        )
        return protect(_code(target))

    text = _AUTOLINK_RE.sub(on_autolink, text)

    def on_link(match: re.Match[str]) -> str:
        image = bool(match.group("bang"))
        label = _INLINE_LINK_RE.sub(on_link, match.group("text"))
        dest = match.group("dest")
        kind, scheme = _classify_url(dest, hosts)
        if kind in ("internal", "anchor"):
            tail = match.group(0)[match.end("text") - match.start(0) :]
            return f"{match.group('bang')}[{label}" + protect(tail)
        if kind == "unsafe":
            findings.append(
                Finding(kind="unsafe-url", message=f"removed {scheme}: URL", excerpt=_excerpt(dest))
            )
        elif kind == "absolute":
            findings.append(
                Finding(
                    kind="absolute-link",
                    message="removed absolute-path link",
                    excerpt=_excerpt(dest),
                )
            )
        else:
            findings.append(
                Finding(
                    kind="external-image" if image else "external-link",
                    message="removed external " + ("image" if image else "link"),
                    excerpt=_excerpt(dest),
                )
            )
        return label

    text = _INLINE_LINK_RE.sub(on_link, text)

    def on_ref_def(match: re.Match[str]) -> str:
        kind, _scheme = _classify_url(match.group("dest"), hosts)
        if kind in ("internal", "anchor"):
            return match.group(0)
        findings.append(
            Finding(
                kind="unsafe-url" if kind == "unsafe" else "external-link",
                message="removed link reference definition",
                excerpt=_excerpt(match.group("dest")),
            )
        )
        return ""

    text = _REF_DEF_RE.sub(on_ref_def, text)

    def on_bare(match: re.Match[str]) -> str:
        url = match.group(0)
        trailing = _TRAILING_PUNCT_RE.search(url)
        tail = trailing.group(0) if trailing else ""
        core = url[: len(url) - len(tail)] if tail else url
        if not core:
            return url
        findings.append(
            Finding(kind="bare-url", message="defanged bare URL or e-mail", excerpt=_excerpt(core))
        )
        return protect(_code(core)) + tail

    text = _BARE_URL_RE.sub(on_bare, text)
    text = _EMAIL_RE.sub(on_bare, text)
    text = _LEFTOVER_LT_RE.sub(r"\\<", text)

    for _ in range(len(protected) + 1):
        restored = _PLACEHOLDER_RE.sub(lambda m: protected[int(m.group(1))], text)
        if restored == text:
            break
        text = restored
    return text, findings


def _code(value: str) -> str:
    fence = "``" if "`" in value else "`"
    pad = " " if value.startswith("`") or value.endswith("`") else ""
    return f"{fence}{pad}{value}{pad}{fence}"


def find_violations(
    markdown: str,
    *,
    allow_markers: bool = True,
    allowed_hosts: Iterable[str] = (),
) -> list[Finding]:
    """Report unsafe constructs as a renderer would see them (no modification)."""
    hosts = tuple(allowed_hosts)
    findings: list[Finding] = []
    for number, line in enumerate(markdown.split("\n"), 1):
        if _CONTROL_RE.search(line) or _INVISIBLE_RE.search(line) or "\r" in line:
            findings.append(
                Finding(
                    kind="control-char", message="control, CR or invisible character", line=number
                )
            )
    prepared_lines = []
    for line in markdown.split("\n"):
        match = FOOTNOTE_DEF_RE.match(line)
        prepared_lines.append(match.group("content") if match else line)
    prepared = "\n".join(prepared_lines)
    tokens = markdown_parser().parse(prepared)
    for token in tokens:
        line = (token.map[0] + 1) if token.map else None
        if token.type == "html_block":
            _check_html(token.content, line, allow_markers, findings, block=True)
        elif token.type == "inline":
            inside_link = 0
            current = line
            for child in token.children or []:
                if child.type in ("softbreak", "hardbreak"):
                    current = current + 1 if current is not None else None
                elif child.type == "html_inline":
                    _check_html(child.content, current, allow_markers, findings, block=False)
                elif child.type == "link_open":
                    inside_link += 1
                    href = str(child.attrGet("href") or "")
                    _check_url(href, False, current, hosts, findings)
                elif child.type == "link_close":
                    inside_link = max(0, inside_link - 1)
                elif child.type == "image":
                    src = str(child.attrGet("src") or "")
                    _check_url(src, True, current, hosts, findings)
                elif child.type == "text" and not inside_link:
                    for match in list(_BARE_URL_RE.finditer(child.content)) + list(
                        _EMAIL_RE.finditer(child.content)
                    ):
                        findings.append(
                            Finding(
                                kind="bare-url",
                                message="bare URL or e-mail would be auto-linked",
                                line=current,
                                excerpt=_excerpt(match.group(0)),
                            )
                        )
    return findings


def _check_html(
    content: str, line: int | None, allow_markers: bool, findings: list[Finding], *, block: bool
) -> None:
    stripped = content.strip()
    if stripped in MARKERS:
        if not allow_markers or not block:
            message = (
                "backlinks marker not allowed here"
                if not allow_markers
                else "backlinks markers must stand alone on their own line"
            )
            findings.append(Finding(kind="marker", message=message, line=line))
        return
    if stripped.startswith("<!--"):
        findings.append(
            Finding(
                kind="html-comment", message="HTML comment", line=line, excerpt=_excerpt(stripped)
            )
        )
    else:
        findings.append(
            Finding(kind="raw-html", message="raw HTML", line=line, excerpt=_excerpt(stripped))
        )


def _check_url(
    url: str, image: bool, line: int | None, hosts: tuple[str, ...], findings: list[Finding]
) -> None:
    kind, scheme = _classify_url(url, hosts)
    if kind == "unsafe":
        findings.append(
            Finding(kind="unsafe-url", message=f"{scheme}: URL", line=line, excerpt=_excerpt(url))
        )
    elif kind == "absolute":
        findings.append(
            Finding(
                kind="absolute-link", message="absolute-path link", line=line, excerpt=_excerpt(url)
            )
        )
    elif kind == "external":
        findings.append(
            Finding(
                kind="external-image" if image else "external-link",
                message="external " + ("image" if image else "link"),
                line=line,
                excerpt=_excerpt(url),
            )
        )


def _alt(*options: str) -> str:
    return "(?:" + "|".join(options) + ")"


_GAP = r"[^.!?\n]{0,40}?"
_AI = _alt("ai", "llms?", "language models?", "chatbots?", "ai assistants?", "ai agents?")
_INJECTION_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "ignore-instructions",
        r"\b"
        + _alt("ignore", "disregard", "forget", "override", "bypass")
        + r"\b"
        + _GAP
        + r"\b"
        + _alt(
            "previous",
            "prior",
            "above",
            "earlier",
            "preceding",
            "all",
            "any",
            "your",
            "the",
            "these",
            "those",
        )
        + r"\b"
        + _GAP
        + r"\b"
        + _alt(
            "instructions?", "prompts?", "directives?", "guidelines", "guardrails", "system message"
        )
        + r"\b",
    ),
    (
        "address-ai",
        r"\b"
        + _alt(
            r"as an? "
            + _alt(
                "ai", "artificial intelligence", "language model", "llm", "chatbot", "ai assistant"
            )
            + r"\b",
            _alt("dear", "attention", "note to", "hey", "hello")
            + r"[ ,:]+"
            + _alt(
                "ai",
                "llms?",
                "chatbots?",
                "assistants?",
                "copilots?",
                "agents?",
                "gpt",
                "language models?",
            )
            + r"\b",
            _alt("to", "for") + " " + _alt("any", "all", "every", "the") + " " + _AI + r"\b",
            r"you are (?:now )?(?:an?|the) " + _AI + r"\b",
            r"if you are an? " + _AI + r"\b",
        ),
    ),
    (
        "prompt-reference",
        r"\b"
        + _alt(
            "system prompt",
            "system message",
            "developer message",
            "hidden instructions?",
            "new instructions?",
            "updated instructions?",
            "jailbreak",
        )
        + r"\b",
    ),
    (
        "tool-syntax",
        _alt(
            r"<\|im_(?:start|end)\|>",
            r"<\|(?:system|assistant|user)\|>",
            r"\[/?inst\]",
            r"</?tool_call>",
            r"\"tool_calls\"",
            r"\bfunction_call\b",
            r"<function=",
            r"\{\s*\"name\"\s*:\s*\"[a-z_]+\"\s*,\s*\"arguments\"",
            r"(?:^|\n)\s*(?:system|assistant|developer)\s*:",
        ),
    ),
    (
        "exfiltration",
        _alt(
            r"\b"
            + _alt("send", "post", "upload", "exfiltrate", "forward", "transmit", "leak")
            + r"\b[^.!?\n]{0,60}?"
            + _alt(r"https?://", r"www\.", r"\b[a-z0-9._%+\-]+@[a-z0-9\-]+\."),
            r"\b"
            + _alt("reveal", "print", "output", "disclose", "repeat")
            + r"\b[^.!?\n]{0,30}?\b"
            + _alt(
                "system prompt",
                "your instructions",
                "api keys?",
                "secrets?",
                "passwords?",
                "access tokens?",
            )
            + r"\b",
        ),
    ),
    (
        "secrecy",
        r"\bdo not "
        + _alt("tell", "inform", "mention", "reveal", "show")
        + r"\b[^.!?\n]{0,20}?\b"
        + r"(?:the )?"
        + _alt("user", "human", "operator", "reader")
        + r"s?\b",
    ),
    (
        "command",
        r"\b"
        + _alt("run", "execute")
        + r"\b[^.!?\n]{0,20}?\b(?:the )?"
        + _alt("following", "this")
        + " "
        + _alt("command", "code", "script", "shell command", "tool")
        + r"\b",
    ),
    (
        "ignore-instructions-fr",
        r"\b"
        + _alt("ignore[sz]?", "ignorer", "oublie[sz]?", "oublier")
        + r"\b"
        + _GAP
        + r"\b"
        + _alt("instructions?", "consignes?")
        + r"\b[^.!?\n]{0,30}?\b"
        + _alt("precedentes?", "anterieures?", "ci-dessus")
        + r"\b",
    ),
    (
        "address-ai-fr",
        r"\ben tant qu ?"
        + _alt("ia", "assistant", "intelligence artificielle", "modele de langage")
        + r"\b",
    ),
    (
        "ignore-instructions-de",
        r"\b"
        + _alt("ignoriere", "ignorieren sie", "vergiss", "vergessen sie")
        + r"\b"
        + _GAP
        + r"\b"
        + _alt("anweisungen", "instruktionen", "vorgaben")
        + r"\b",
    ),
    ("address-ai-de", r"\bals " + _alt("ki", "ki-assistent", "sprachmodell") + r"\b"),
)
_INJECTION_RULES: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (name, re.compile(pattern)) for name, pattern in _INJECTION_PATTERNS
)


def _normalise_for_detection(text: str) -> str:
    text = _INVISIBLE_RE.sub("", text)
    decomposed = unicodedata.normalize("NFKD", unicodedata.normalize("NFKC", text))
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = stripped.replace("’", "'").replace("‘", "'").replace("'", " ")
    return re.sub(r"[ \t]+", " ", stripped.casefold())


def detect_injection(text: str) -> list[Finding]:
    """Heuristic detection of text addressed to AI systems (EN/FR/DE), one finding per match."""
    findings: list[Finding] = []
    seen: set[tuple[str, int]] = set()
    lines = text.split("\n")
    paragraph_start = 0
    paragraphs: list[tuple[int, str]] = []
    buffer: list[str] = []
    for index, line in enumerate(lines):
        if line.strip():
            if not buffer:
                paragraph_start = index
            buffer.append(line)
        elif buffer:
            paragraphs.append((paragraph_start, "\n".join(buffer)))
            buffer = []
    if buffer:
        paragraphs.append((paragraph_start, "\n".join(buffer)))
    for start, paragraph in paragraphs:
        normalised = _normalise_for_detection(paragraph)
        # A sentence hard-wrapped over several lines (e-mails, PDF text) is matched again with its
        # line breaks read as spaces; both strings have the same length, so offsets map to lines.
        joined = normalised.replace("\n", " ")
        variants = (normalised, joined) if joined != normalised else (normalised,)
        for name, pattern in _INJECTION_RULES:
            for match in (match for variant in variants for match in pattern.finditer(variant)):
                offset_line = start + normalised.count("\n", 0, match.start()) + 1
                if (name, offset_line) in seen:
                    continue
                seen.add((name, offset_line))
                findings.append(
                    Finding(
                        kind="injection",
                        rule=name,
                        message=f"text addressed to an AI system ({name})",
                        line=offset_line,
                        excerpt=_excerpt(match.group(0).strip()),
                    )
                )
    return findings


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def neutralize_injections(markdown: str) -> tuple[str, list[Finding]]:
    """Drop sentences that :func:`detect_injection` flags (code blocks untouched)."""
    findings: list[Finding] = []
    out: list[str] = []
    tracker = FenceTracker()
    for number, line in enumerate(markdown.split("\n"), 1):
        if tracker.feed(line):
            out.append(line)
            continue
        prefix_match = re.match(r"^(\s*(?:[-*+]|\d+[.)]|>)\s+)", line)
        prefix = prefix_match.group(1) if prefix_match else ""
        content = line[len(prefix) :]
        kept: list[str] = []
        dropped = False
        for sentence in _SENTENCE_SPLIT_RE.split(content):
            hits = detect_injection(sentence)
            if hits:
                dropped = True
                for hit in hits:
                    findings.append(hit.model_copy(update={"line": number}))
            else:
                kept.append(sentence)
        if dropped and not "".join(kept).strip():
            continue
        out.append(prefix + " ".join(kept) if dropped else line)
    return "\n".join(out), findings
