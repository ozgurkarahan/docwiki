"""EML via the ``email`` package: headers, body lines and attachment list (local adapter).

Body locators count the 1-based lines of the decoded ``text/plain`` body (or of the text
converted from the HTML body when there is no plain-text alternative).
"""

from __future__ import annotations

import email
import html
from email import policy
from email.message import EmailMessage
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser

from docwiki.contracts.locators import EmlPartLocator
from docwiki.extract._draft import Draft
from docwiki.extract._text import (
    lang_from_tag,
    normalize_lines,
    one_line,
    paragraph_ranges,
    safe_label,
    words,
)

__all__ = ["extract_eml", "html_to_text"]

HEADER_NAMES = ("From", "To", "Cc", "Date", "Subject")

_BLOCK_TAGS = words(
    "address article aside blockquote br dd div dl dt figcaption figure footer form h1 h2 h3 h4 "
    "h5 h6 header hr li main nav ol p pre section table tbody td tfoot th thead tr ul"
)
_SKIP_TAGS = words("script style head title template noscript svg math object iframe")


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP_TAGS:
            self._skip += 1
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip:
            self.parts.append(data)


def html_to_text(markup: str) -> str:
    """Visible text of an HTML body: tags dropped, scripts/styles removed, blocks on new lines."""
    parser = _TextExtractor()
    try:
        parser.feed(markup)
        parser.close()
    except (AssertionError, ValueError):  # pragma: no cover - HTMLParser is lenient
        return html.unescape(markup)
    lines = [" ".join(line.split()) for line in "".join(parser.parts).split("\n")]
    collapsed: list[str] = []
    for line in lines:
        if line or (collapsed and collapsed[-1]):
            collapsed.append(line)
    return "\n".join(collapsed).strip("\n")


def _body_text(message: EmailMessage, draft: Draft) -> str:
    part = message.get_body(preferencelist=("plain", "html"))
    if part is None:
        return ""
    try:
        content = part.get_content()
    except (LookupError, ValueError) as exc:
        draft.warn("eml-body", f"body could not be decoded: {type(exc).__name__}")
        payload = part.get_payload(decode=True) or b""
        content = payload.decode("utf-8", errors="replace") if isinstance(payload, bytes) else ""
    if not isinstance(content, str):
        return ""
    if part.get_content_type() == "text/html":
        draft.warn("eml-html-body", "no text/plain alternative; lines come from the HTML body")
        return html_to_text(content)
    return content


def extract_eml(data: bytes, draft: Draft) -> None:
    message = email.message_from_bytes(data, policy=policy.default)
    if not isinstance(message, EmailMessage):  # pragma: no cover - policy.default guarantees it
        raise ValueError("not an e-mail message")

    header_lines: list[str] = []
    for name in HEADER_NAMES:
        try:
            value = message.get(name)
        except (ValueError, IndexError):
            value = None
        if value is not None and one_line(str(value)):
            header_lines.append(f"{name}: {one_line(str(value))}")
    if header_lines:
        draft.block(
            "email-header", "\n".join(header_lines), EmlPartLocator(part="headers"), "native-text"
        )
    subject = one_line(str(message.get("Subject") or ""))
    draft.title_hint = subject or None
    try:
        sent = parsedate_to_datetime(str(message.get("Date") or ""))
        draft.authored = sent.date()
    except (TypeError, ValueError, IndexError):
        draft.authored = None
    draft.lang = lang_from_tag(str(message.get("Content-Language") or ""))

    lines = normalize_lines(_body_text(message, draft))
    for start, end in paragraph_ranges(lines):
        text = "\n".join(lines[start - 1 : end]).strip()
        locator = EmlPartLocator(part="body", line_start=start, line_end=end)
        draft.block("email-body", text, locator, "native-text")

    for index, attachment in enumerate(message.iter_attachments(), 1):
        name = safe_label(attachment.get_filename(), fallback=f"attachment {index}", max_len=80)
        payload = attachment.get_payload(decode=True)
        size = len(payload) if isinstance(payload, bytes) else 0
        text = f"Attachment: {name} ({attachment.get_content_type()}, {size} bytes)"
        draft.block("paragraph", text, EmlPartLocator(part=f"attachment:{name}"), "native-text")
