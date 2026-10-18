"""Text and metadata extraction for every file type the leak guard understands.

Every extractor returns an :class:`Extraction`: text chunks with locations, document metadata,
EXIF presence, notices (content that cannot be scanned) and problems (extraction failures).
"""

from __future__ import annotations

import codecs
import ctypes
import email
import email.policy
import io
import os
import re
import sqlite3
import tokenize
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import replace
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath

from .model import Chunk, Extraction, MetaField

MAX_DEPTH = 4
MAX_MEMBER_BYTES = 64 * 1024 * 1024
MAX_TABLE_ROWS = 200_000

OOXML_EXTS = frozenset(
    {
        ".docx", ".docm", ".dotx", ".dotm",
        ".xlsx", ".xlsm", ".xltx", ".xltm",
        ".pptx", ".pptm", ".potx", ".potm", ".ppsx", ".ppsm",
        ".vsdx", ".vsdm",
    }
)
IMAGE_EXTS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".tif", ".tiff", ".bmp", ".ico"}
)
SQLITE_EXTS = frozenset({".db", ".sqlite", ".sqlite3", ".db3"})
PARQUET_EXTS = frozenset({".parquet", ".pq"})
FONT_EXTS = frozenset({".woff", ".woff2", ".ttf", ".otf", ".eot"})
MARKUP_EXTS = frozenset({".html", ".htm", ".xhtml", ".svg", ".xml", ".rss", ".atom"})
CELL_EXTS = frozenset({".csv", ".tsv"})
MARKDOWN_EXTS = frozenset({".md", ".markdown", ".mdx"})
PYTHON_EXTS = frozenset({".py", ".pyi"})
# Source code and configuration: identifiers only, never the proper-noun check.
CODE_EXTS = frozenset(
    {
        ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".css", ".scss", ".map",
        ".sh", ".bash", ".ps1", ".psm1", ".bat", ".cmd", ".bicep", ".bicepparam",
        ".toml", ".ini", ".cfg", ".lock", ".j2", ".jinja", ".dockerfile",
    }
)
# Binary types worth extracting from git history blobs.
BINARY_EXTS = OOXML_EXTS | IMAGE_EXTS | SQLITE_EXTS | PARQUET_EXTS | FONT_EXTS | {".pdf", ".zip"}

_STRUCTURE_RE = re.compile(r"^\s*(?:[-*+]\s|>\s?|\d{1,3}[.)]\s|[A-Za-z][.)]\s)")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s")
_TERMINAL_RE = re.compile(r"[.!?]['\")\]»”]*\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_PRINTABLE_RE = re.compile(rb"[\x20-\x7e]{6,}")
_UTF16_RE = re.compile(rb"(?:[\x20-\x7e]\x00){6,}")
_XMP_RE = re.compile(rb"<x:xmpmeta.*?</x:xmpmeta>", re.DOTALL)
_PDF_URI_RE = re.compile(rb"/URI\s*\(((?:[^()\\]|\\.)*)\)")
_EXIF_MARKER = b"Exif\x00\x00"

# Office XML attributes whose values are human text (names, titles, alt text, link targets).
_TEXT_ATTRS = frozenset(
    {
        "name", "title", "descr", "author", "initials", "userId", "displayName", "providerId",
        "text", "alt", "tooltip", "Target", "location", "lastModifiedBy", "creator",
    }
)
_PERSON_ATTRS = frozenset({"author", "initials", "userId", "displayName", "lastModifiedBy"})
# Template boilerplate parts (themes, fonts, styles, masters...): identifiers only.
_BOILERPLATE_PART_RE = re.compile(
    r"(?:^|/)(?:fontTable|styles|stylesWithEffects|settings|webSettings|numbering|presProps"
    r"|viewProps|tableStyles|calcChain)\.xml$|(?:^|/)(?:theme|slideMasters|slideLayouts"
    r"|notesMasters|handoutMasters|printerSettings)/|\[Content_Types\]\.xml$",
    re.IGNORECASE,
)
_CORE_PROSE_FIELDS = frozenset(
    {"title", "subject", "creator", "keywords", "description", "lastModifiedBy", "category",
     "contentStatus"}
)
_APP_PROSE_FIELDS = frozenset({"Company", "Manager"})
# Elements whose text is a structural reference, not content: field instructions are handled
# separately and table style ids are built-in Office constants such as PowerPoint's
# "Medium Style 2 - Accent 1" (or random ids of custom styles).
_STRUCTURAL_ELEMENTS = frozenset({"instrText", "tableStyleId"})
_OFFICE_META_FIELDS = frozenset(
    {
        "title", "subject", "creator", "keywords", "description", "lastModifiedBy", "category",
        "contentStatus", "Company", "Manager", "Application", "Template", "HyperlinkBase",
    }
)
_EMAIL_PROSE_HEADERS = frozenset(
    {"from", "to", "cc", "bcc", "reply-to", "sender", "subject", "organization", "comments"}
)
_IMAGE_SKIP_INFO = frozenset(
    {
        "dpi", "gamma", "transparency", "duration", "loop", "background", "aspect",
        "progressive", "progression", "jfif", "jfif_version", "jfif_unit", "jfif_density",
        "interlace", "srgb", "chromaticity", "adobe", "adobe_transform", "icc_profile",
        "compression", "version", "palette", "disposal", "blend", "default_image", "mp",
        "photoshop", "exif", "mpinfo", "transparency_index",
    }
)


def suffix_of(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/").lower()).suffix


def decode_text(data: bytes) -> str | None:
    """Decode a text file; ``None`` when the content is binary."""
    if data.startswith(codecs.BOM_UTF8):
        return data[len(codecs.BOM_UTF8) :].decode("utf-8", errors="replace")
    if data.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return data.decode("utf-16", errors="replace")
    if b"\x00" in data[:8192]:
        return None
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("latin-1")
        controls = sum(1 for ch in text[:8192] if ord(ch) < 32 and ch not in "\r\n\t\f")
        return None if controls > len(text[:8192]) * 0.05 else text


def extract_bytes(
    data: bytes, name: str, *, path_on_disk: Path | None = None, depth: int = 0
) -> Extraction:
    """Extract text, metadata and EXIF information from ``data`` (file name ``name``)."""
    if depth > MAX_DEPTH:
        return Extraction(kind="binary", problems=["nested too deeply; not scanned"])
    if not data:
        return Extraction(kind="empty")
    ext = suffix_of(name)
    try:
        if data.startswith(b"%PDF-") or (ext == ".pdf" and b"%PDF-" in data[:1024]):
            return extract_pdf(data, depth)
        if data.startswith(b"PK\x03\x04") or data.startswith(b"PK\x05\x06"):
            return extract_zip(data, depth)
        if data.startswith(b"SQLite format 3\x00"):
            return extract_sqlite(data, path_on_disk)
        if data.startswith(b"PAR1") or ext in PARQUET_EXTS:
            return extract_parquet(path_on_disk)
        if _looks_like_image(data) or ext in IMAGE_EXTS:
            return extract_image(data, ext)
        if ext in FONT_EXTS:
            result = Extraction(kind="font", chunks=strings_chunks(data))
            return result
        if ext == ".eml":
            return extract_email(data, depth)
        text = decode_text(data)
        if text is None:
            result = Extraction(kind="binary", chunks=strings_chunks(data), unknown_binary=True)
            return result
        return extract_text(text, name)
    except Exception as exc:  # extraction must never crash the scan; the failure is reported
        if os.environ.get("LEAKGUARD_DEBUG") == "1":
            raise
        return Extraction(kind="error", problems=[f"extraction failed: {type(exc).__name__}"])


def _looks_like_image(data: bytes) -> bool:
    return (
        data.startswith(b"\x89PNG\r\n\x1a\n")
        or data.startswith(b"\xff\xd8\xff")
        or data.startswith((b"GIF87a", b"GIF89a"))
        or (data.startswith(b"RIFF") and data[8:12] == b"WEBP")
        or data.startswith((b"II*\x00", b"MM\x00*"))
    )


# --------------------------------------------------------------------------------------------
# Plain text


def extract_text(text: str, name: str) -> Extraction:
    ext = suffix_of(name)
    base = PurePosixPath(name.replace("\\", "/").lower()).name
    if ext in PYTHON_EXTS:
        chunks = python_chunks(text)
    elif ext in MARKUP_EXTS:
        chunks = line_chunks(text, closed_world=False)
        chunks.extend(markup_chunks(text))
    elif ext in CODE_EXTS or base in {"dockerfile", "makefile"}:
        chunks = line_chunks(text, closed_world=False)
    elif ext in CELL_EXTS:
        chunks = line_chunks(text, cells=True)
    else:
        chunks = line_chunks(text, markdown=ext in MARKDOWN_EXTS)
    return Extraction(kind="text", chunks=with_unescaped(chunks))


_ESCAPE_RE = re.compile(r"\\(?:u([0-9a-fA-F]{4})|U([0-9a-fA-F]{8})|([nrt\"/\\]))")
_SIMPLE_ESCAPES = {"n": "\n", "r": "\r", "t": "\t", '"': '"', "/": "/", "\\": "\\"}


def unescape_text(text: str) -> str:
    """Decode JSON/YAML/Python string escapes: ``\\uXXXX``, ``\\UXXXXXXXX``, ``\\n``, ``\\t``,
    ``\\"``... (surrogate code points are kept escaped)."""

    def decode(match: re.Match[str]) -> str:
        if match.group(3):
            return _SIMPLE_ESCAPES[match.group(3)]
        code = int(match.group(1) or match.group(2), 16)
        if 0xD800 <= code <= 0xDFFF or code > 0x10FFFF:
            return match.group(0)
        return chr(code)

    return _ESCAPE_RE.sub(decode, text)


def with_unescaped(chunks: list[Chunk]) -> list[Chunk]:
    """Add a decoded copy of every chunk written with string escapes ("J\\u00fcrgen", "a\\nB").

    The decoded copy feeds every rule (a deny-list term must match "Jürgen" either way); the
    escaped original keeps only the identifier rules, because escapes split words.
    """
    result: list[Chunk] = []
    for chunk in chunks:
        decoded = unescape_text(chunk.text) if "\\" in chunk.text else ""
        if decoded and decoded != chunk.text:
            result.append(replace(chunk, closed_world=False))
            result.append(replace(chunk, text=decoded, decoded=True))
        else:
            result.append(chunk)
    return result


def line_chunks(
    text: str,
    *,
    closed_world: bool = True,
    cells: bool = False,
    markdown: bool = True,
    first_line: int = 1,
    location_prefix: str = "",
) -> list[Chunk]:
    """One chunk per line, tracking whether each line starts a sentence."""
    chunks: list[Chunk] = []
    continuing = False
    in_fence = False
    for offset, line in enumerate(text.splitlines()):
        number = first_line + offset
        location = f"{location_prefix}line {number}"
        stripped = line.strip()
        prose = closed_world
        if markdown and _FENCE_RE.match(line):
            in_fence = not in_fence
            prose = False
        elif in_fence:
            prose = False
        table_or_heading = bool(_HEADING_RE.match(line)) or stripped.startswith("|")
        start = not cells and not table_or_heading and (
            bool(_STRUCTURE_RE.match(line)) or not continuing
        )
        chunks.append(Chunk(line, location, number, sentence_start=start, closed_world=prose))
        continuing = bool(stripped) and not _TERMINAL_RE.search(stripped) and not in_fence
        if table_or_heading:
            continuing = False
    return chunks


def python_chunks(text: str) -> list[Chunk]:
    """Raw lines for the identifier rules, string literals and comments for the noun check."""
    chunks = line_chunks(text, closed_world=False)
    literal_kinds = {tokenize.STRING, tokenize.COMMENT}
    fstring_middle = getattr(tokenize, "FSTRING_MIDDLE", None)
    if fstring_middle is not None:
        literal_kinds.add(fstring_middle)
    try:
        tokens = list(tokenize.generate_tokens(io.StringIO(text).readline))
    except (tokenize.TokenError, SyntaxError):
        tokens = []
        for number, line in enumerate(text.splitlines(), start=1):
            for match in re.finditer(r"#(.*)$|\"([^\"]*)\"|'([^']*)'", line):
                value = next(group for group in match.groups() if group is not None)
                chunks.append(
                    Chunk(value, f"line {number}", number, identifiers=False, kind="literal")
                )
        return chunks
    for token in tokens:
        if token.type not in literal_kinds:
            continue
        value = token.string
        if token.type == tokenize.COMMENT:
            value = value.lstrip("#")
        elif token.type == tokenize.STRING:
            value = _strip_string_quotes(value)
        start_line = token.start[0]
        for index, part in enumerate(value.splitlines() or [value]):
            if not part.strip():
                continue
            number = start_line + index
            chunks.append(
                Chunk(part, f"line {number}", number, identifiers=False, kind="literal")
            )
    return chunks


def _strip_string_quotes(token: str) -> str:
    match = re.match(r"^[A-Za-z]*(\"\"\"|'''|\"|')(.*)\1$", token, re.DOTALL)
    return match.group(2) if match else token


_BLOCK_TAGS = frozenset(
    {
        "p", "div", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "td", "th", "tr",
        "table", "br", "section", "article", "header", "footer", "title", "option", "dt", "dd",
        "blockquote", "pre", "figcaption", "caption", "nav", "aside", "main", "body", "html",
        "text", "tspan", "desc", "label", "button", "summary", "details", "hr", "form",
    }
)


class _MarkupText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[int, str, bool]] = []
        self._buffer: list[str] = []
        self._line = 1
        self._skip = 0

    def _flush(self) -> None:
        text = " ".join("".join(self._buffer).split())
        if text:
            self.blocks.append((self._line, text, True))
        self._buffer = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "code", "pre", "math"}:
            self._skip += 1
        if tag in _BLOCK_TAGS:
            self._flush()
            self._line = self.getpos()[0]
        for attr, value in attrs:
            if attr in {"alt", "title", "aria-label", "placeholder", "content", "label"} and value:
                self.blocks.append((self.getpos()[0], value, False))

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "code", "pre", "math"} and self._skip:
            self._skip -= 1
        if tag in _BLOCK_TAGS:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._skip:
            return
        if not self._buffer:
            self._line = self.getpos()[0]
        self._buffer.append(data)

    def close(self) -> None:
        super().close()
        self._flush()


def markup_chunks(text: str) -> list[Chunk]:
    """Visible text of HTML/SVG/XML for the proper-noun check (identifiers use raw lines)."""
    parser = _MarkupText()
    try:
        parser.feed(text)
        parser.close()
    except Exception:  # HTMLParser is lenient; never fail the scan on odd markup
        return []
    return [
        Chunk(value, f"line {line}", line, identifiers=False, sentence_start=start, kind="text")
        for line, value, start in parser.blocks
    ]


# --------------------------------------------------------------------------------------------
# E-mail (.eml)


def extract_email(data: bytes, depth: int) -> Extraction:
    message = email.message_from_bytes(data, policy=email.policy.default)
    result = Extraction(kind="email")
    for header, value in message.items():
        text = f"{header}: {value}"
        prose = header.lower() in _EMAIL_PROSE_HEADERS
        result.chunks.append(
            Chunk(text, f"header {header}", kind="metadata", field=header, closed_world=prose)
        )
    for index, part in enumerate(message.walk(), start=1):
        if part.is_multipart():
            continue
        filename = part.get_filename()
        payload = part.get_payload(decode=True)
        if not isinstance(payload, bytes):
            continue
        content_type = part.get_content_type()
        if filename:
            result.chunks.append(
                Chunk(filename, f"part {index} file name", kind="metadata", sentence_start=False)
            )
        if content_type.startswith("text/") and not filename:
            charset = part.get_content_charset() or "utf-8"
            try:
                body = payload.decode(charset, errors="replace")
            except LookupError:
                body = payload.decode("utf-8", errors="replace")
            prefix = f"part {index} "
            if content_type == "text/html":
                result.chunks.extend(line_chunks(body, closed_world=False, location_prefix=prefix))
                for chunk in markup_chunks(body):
                    result.chunks.append(
                        Chunk(
                            chunk.text,
                            prefix + chunk.location,
                            identifiers=False,
                            sentence_start=chunk.sentence_start,
                        )
                    )
            else:
                result.chunks.extend(line_chunks(body, location_prefix=prefix))
        else:
            nested = extract_bytes(payload, filename or f"part{index}", depth=depth + 1)
            result.merge(nested, f"attachment {filename or index}")
    return result


# --------------------------------------------------------------------------------------------
# ZIP containers and Office Open XML (DOCX, XLSX, PPTX...)


def _local(tag: str) -> str:
    return tag.rpartition("}")[2]


def _read_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes | None:
    with archive.open(info) as handle:
        data = handle.read(MAX_MEMBER_BYTES + 1)
    return None if len(data) > MAX_MEMBER_BYTES else data


def _parse_xml(data: bytes) -> ET.Element:
    if b"<!DOCTYPE" in data[:4096] or b"<!ENTITY" in data[:4096]:
        raise ValueError("XML with DTD or entity declarations is not parsed")
    return ET.fromstring(data)


def extract_zip(data: bytes, depth: int) -> Extraction:
    archive = zipfile.ZipFile(io.BytesIO(data))
    names = archive.namelist()
    ooxml = "[Content_Types].xml" in names
    result = Extraction(kind="office" if ooxml else "zip")
    members = {info.filename: info for info in archive.infolist() if not info.is_dir()}

    shared: list[str] = []
    if "xl/sharedStrings.xml" in members:
        raw = _read_member(archive, members["xl/sharedStrings.xml"])
        if raw is not None:
            shared = [
                _paragraph_text(si)[0] for si in _parse_xml(raw) if _local(si.tag) == "si"
            ]
    sheet_names = _sheet_names(archive, members) if ooxml else {}
    used_shared: set[int] = set()

    for member, info in members.items():
        if not ooxml:
            result.chunks.append(
                Chunk(member, f"{member} (entry name)", kind="path", sentence_start=False)
            )
        if member == "xl/sharedStrings.xml":
            continue
        raw = _read_member(archive, info)
        if raw is None:
            result.problems.append(f"{member}: entry too large; not scanned")
            continue
        lower = member.lower()
        try:
            if ooxml and lower.startswith("docprops/") and lower.endswith(".xml"):
                _office_properties(raw, member, result)
            elif ooxml and re.fullmatch(r"xl/worksheets/sheet\d+\.xml", lower):
                label = sheet_names.get(member, PurePosixPath(member).stem)
                _sheet_cells(raw, label, shared, used_shared, result)
            elif lower.endswith((".xml", ".rels", ".vml")) and (ooxml or raw.lstrip()[:1] == b"<"):
                result.chunks.extend(xml_chunks(raw, member))
            else:
                result.merge(extract_bytes(raw, member, depth=depth + 1), member)
        except (ET.ParseError, ValueError) as exc:
            # Legacy VML drawings are often not well-formed XML: fall back to tag-stripped text.
            if not lower.endswith(".vml"):
                result.problems.append(f"{member}: cannot parse XML ({type(exc).__name__})")
            stripped = re.sub(r"<[^>]*>", " ", raw.decode("utf-8", errors="replace"))
            result.chunks.extend(
                Chunk(line, f"{member} line {number}", closed_world=False)
                for number, line in enumerate(stripped.splitlines(), start=1)
                if line.strip()
            )
    for index, value in enumerate(shared):
        if index not in used_shared and value.strip():
            result.chunks.append(
                Chunk(value, f"xl/sharedStrings.xml string {index}", sentence_start=False)
            )
    return result


def _paragraph_text(element: ET.Element) -> tuple[str, list[str]]:
    """Visible text of a paragraph-like element and the field instructions inside it."""
    parts: list[str] = []
    instructions: list[str] = []
    for node in element.iter():
        local = _local(node.tag)
        if local in {"t", "delText"} and node.text:
            parts.append(node.text)
        elif local == "instrText" and node.text:
            instructions.append(node.text)
        elif local in {"tab", "br", "cr"}:
            parts.append(" ")
    return "".join(parts), instructions


def _attribute_chunk(
    element: str, attr: str, value: str, location: str, boilerplate: bool
) -> Chunk:
    # Shape, style, font and layout names are generated boilerplate ("Title 1", "Office Theme");
    # sheet names and person attributes are content.
    prose = (
        not boilerplate
        and attr not in {"Target", "providerId", "location"}
        and (attr != "name" or element == "sheet")
    )
    return Chunk(
        value,
        location,
        kind="metadata" if attr in _PERSON_ATTRS else "attribute",
        field=attr,
        sentence_start=False,
        closed_world=prose,
    )


def xml_chunks(raw: bytes, member: str) -> list[Chunk]:
    """Text of an Office XML part: paragraphs, other element text and human-text attributes."""
    root = _parse_xml(raw)
    chunks: list[Chunk] = []
    counter = 0
    boilerplate = bool(_BOILERPLATE_PART_RE.search(member))

    def visit(node: ET.Element, in_table: bool) -> None:
        nonlocal counter
        local = _local(node.tag)
        for attr, value in node.attrib.items():
            attr_local = _local(attr)
            if attr_local in _TEXT_ATTRS and value.strip():
                location = f"{member} @{attr_local}"
                chunks.append(_attribute_chunk(local, attr_local, value, location, boilerplate))
        if local in {"p", "si", "is", "comment"}:
            counter += 1
            text, instructions = _paragraph_text(node)
            if text.strip():
                chunks.append(
                    Chunk(
                        text,
                        f"{member} paragraph {counter}",
                        sentence_start=not in_table,
                        closed_world=not boilerplate,
                    )
                )
            for instruction in instructions:
                chunks.append(
                    Chunk(instruction, f"{member} field {counter}", closed_world=False)
                )
            for child in node.iter():
                if child is node:
                    continue
                child_local = _local(child.tag)
                for attr, value in child.attrib.items():
                    attr_local = _local(attr)
                    if attr_local in _TEXT_ATTRS and value.strip():
                        location = f"{member} paragraph {counter} @{attr_local}"
                        chunks.append(
                            _attribute_chunk(child_local, attr_local, value, location, boilerplate)
                        )
            return
        if node.text and node.text.strip() and local not in _STRUCTURAL_ELEMENTS:
            chunks.append(
                Chunk(
                    node.text,
                    f"{member} <{local}>",
                    sentence_start=False,
                    kind="element",
                    closed_world=not boilerplate,
                )
            )
        child_in_table = in_table or local == "tc"
        for child in node:
            visit(child, child_in_table)

    visit(root, False)
    return chunks


def _office_properties(raw: bytes, member: str, result: Extraction) -> None:
    root = _parse_xml(raw)
    lower = member.lower()
    if lower.endswith("custom.xml"):
        for prop in root:
            name = prop.attrib.get("name", "property")
            for value_node in prop.iter():
                if value_node is not prop and value_node.text and value_node.text.strip():
                    result.metadata.append(MetaField("office", name, value_node.text, member))
                    result.chunks.append(
                        Chunk(
                            f"{name}: {value_node.text}",
                            f"{member} {name}",
                            kind="metadata",
                            field=name,
                            sentence_start=False,
                        )
                    )
        return
    for node in root.iter():
        if node is root:
            continue
        local = _local(node.tag)
        text = (node.text or "").strip()
        if not text:
            continue
        if local in {"created", "modified", "lastPrinted", "TotalTime", "Pages", "Words"}:
            continue
        if local in _OFFICE_META_FIELDS:
            result.metadata.append(MetaField("office", local, text, f"{member} {local}"))
        # Core title/subject/author fields are content; app.xml lists fonts, themes and the
        # producing application (identifiers only), except Company and Manager.
        prose = local in (_APP_PROSE_FIELDS if lower.endswith("app.xml") else _CORE_PROSE_FIELDS)
        result.chunks.append(
            Chunk(
                text,
                f"{member} {local}",
                kind="metadata",
                field=local,
                sentence_start=False,
                closed_world=prose,
            )
        )


def _sheet_names(archive: zipfile.ZipFile, members: dict[str, zipfile.ZipInfo]) -> dict[str, str]:
    names: dict[str, str] = {}
    if "xl/workbook.xml" not in members or "xl/_rels/workbook.xml.rels" not in members:
        return names
    workbook = _read_member(archive, members["xl/workbook.xml"])
    rels = _read_member(archive, members["xl/_rels/workbook.xml.rels"])
    if workbook is None or rels is None:
        return names
    targets: dict[str, str] = {}
    for rel in _parse_xml(rels):
        target = rel.attrib.get("Target", "")
        target = target.lstrip("/") if target.startswith("/") else f"xl/{target}"
        targets[rel.attrib.get("Id", "")] = target
    for node in _parse_xml(workbook).iter():
        if _local(node.tag) == "sheet":
            rid = next((v for k, v in node.attrib.items() if _local(k) == "id"), "")
            if rid in targets:
                names[targets[rid]] = node.attrib.get("name", rid)
    return names


def _sheet_cells(
    raw: bytes, label: str, shared: list[str], used_shared: set[int], result: Extraction
) -> None:
    root = _parse_xml(raw)
    for cell in root.iter():
        if _local(cell.tag) != "c":
            continue
        ref = cell.attrib.get("r", "?")
        kind = cell.attrib.get("t", "n")
        location = f"{label}!{ref}"
        for child in cell:
            local = _local(child.tag)
            if local == "f" and child.text:
                result.chunks.append(
                    Chunk(child.text, f"{location} formula", closed_world=False, kind="formula")
                )
            elif local == "v" and child.text is not None:
                if kind == "s":
                    try:
                        index = int(child.text)
                    except ValueError:
                        continue
                    if 0 <= index < len(shared):
                        used_shared.add(index)
                        if shared[index].strip():
                            result.chunks.append(
                                Chunk(shared[index], location, sentence_start=False)
                            )
                elif kind in {"str", "inlineStr"} and child.text.strip():
                    result.chunks.append(Chunk(child.text, location, sentence_start=False))
            elif local == "is":
                text, _ = _paragraph_text(child)
                if text.strip():
                    result.chunks.append(Chunk(text, location, sentence_start=False))


# --------------------------------------------------------------------------------------------
# PDF


def extract_pdf(data: bytes, depth: int) -> Extraction:
    result = Extraction(kind="pdf")
    if _EXIF_MARKER in data:
        result.exif.append("embedded image (EXIF marker in the PDF data)")
    for match in _XMP_RE.finditer(data):
        try:
            result.chunks.extend(
                Chunk(c.text, "XMP metadata", kind="metadata", sentence_start=False,
                      closed_world=False)
                for c in xml_chunks(match.group(0), "XMP")
            )
        except (ET.ParseError, ValueError):
            result.chunks.extend(
                Chunk(text, "XMP metadata", kind="metadata", closed_world=False)
                for text in match.group(0).decode("utf-8", errors="replace").splitlines()
            )
    try:
        import pypdfium2 as pdfium
    except ImportError:
        result.problems.append("pypdfium2 is not installed; PDF text and metadata not scanned")
        return result

    try:
        document = pdfium.PdfDocument(data)
    except pdfium.PdfiumError as exc:
        result.problems.append(f"cannot open PDF ({exc})")
        return result
    try:
        for key, value in document.get_metadata_dict(skip_empty=True).items():
            if key in {"CreationDate", "ModDate"}:
                continue
            result.metadata.append(MetaField("pdf", key, value, f"info {key}"))
            result.chunks.append(
                Chunk(value, f"info {key}", kind="metadata", field=key, sentence_start=False)
            )
        empty_pages = 0
        uris: list[tuple[int, str]] = []
        for index in range(len(document)):
            page = document[index]
            try:
                textpage = page.get_textpage()
                try:
                    text = textpage.get_text_range()
                finally:
                    textpage.close()
                if not text.strip():
                    empty_pages += 1
                result.chunks.extend(
                    line_chunks(text, markdown=False, location_prefix=f"page {index + 1} ")
                )
                uris.extend((index + 1, uri) for uri in _page_uris(pdfium, document, page))
            finally:
                page.close()
        for page_no, uri in uris:
            result.chunks.append(
                Chunk(uri, f"page {page_no} link", kind="link", closed_world=False)
            )
        if not uris:
            for match in _PDF_URI_RE.finditer(data):
                uri = match.group(1).decode("latin-1")
                result.chunks.append(Chunk(uri, "link", kind="link", closed_world=False))
        if empty_pages:
            result.notices.append(
                f"{empty_pages} page(s) without a text layer (image only); OCR is not available"
            )
        for item in _toc_titles(document):
            result.chunks.append(Chunk(item, "bookmark", sentence_start=False))
        for index in range(document.count_attachments()):
            attachment = document.get_attachment(index)
            name = attachment.get_name()
            result.chunks.append(
                Chunk(name, f"attachment {index + 1} name", kind="metadata", sentence_start=False)
            )
            nested = extract_bytes(bytes(attachment.get_data()), name, depth=depth + 1)
            result.merge(nested, f"attachment {name}")
    finally:
        document.close()
    return result


def _page_uris(pdfium: object, document: object, page: object) -> list[str]:
    """URI link targets of a page, read through the PDFium C API."""
    raw = pdfium.raw  # type: ignore[attr-defined]
    uris: list[str] = []
    try:
        position = ctypes.c_int(0)
        link = raw.FPDF_LINK()
        while raw.FPDFLink_Enumerate(page.raw, ctypes.byref(position), ctypes.byref(link)):  # type: ignore[attr-defined]
            action = raw.FPDFLink_GetAction(link)
            if not action or raw.FPDFAction_GetType(action) != raw.PDFACTION_URI:
                continue
            size = raw.FPDFAction_GetURIPath(document.raw, action, None, 0)  # type: ignore[attr-defined]
            if size <= 0:
                continue
            buffer = ctypes.create_string_buffer(size)
            raw.FPDFAction_GetURIPath(document.raw, action, buffer, size)  # type: ignore[attr-defined]
            uris.append(buffer.value.decode("utf-8", errors="replace"))
    except (AttributeError, TypeError, ctypes.ArgumentError):
        return uris
    return uris


def _toc_titles(document: object) -> list[str]:
    titles: list[str] = []
    try:
        for bookmark in document.get_toc():  # type: ignore[attr-defined]
            title = bookmark.get_title()
            if title:
                titles.append(title)
    except Exception:  # an unreadable outline is not worth failing the scan
        return titles
    return titles


# --------------------------------------------------------------------------------------------
# Images


def extract_image(data: bytes, ext: str) -> Extraction:
    result = Extraction(kind="image")
    try:
        from PIL import Image
    except ImportError:
        result.problems.append("Pillow is not installed; image metadata not scanned")
        return result
    try:
        with Image.open(io.BytesIO(data)) as image:
            image_format = (image.format or "").upper()
            info = dict(image.info)
            exif = image.getexif()
            if image_format == "TIFF":
                if any(tag in exif for tag in (0x8769, 0x8825)) or info.get("exif"):
                    result.exif.append("EXIF/GPS directory")
                for tag in (0x010E, 0x010F, 0x0110, 0x0131, 0x013B, 0x013C, 0x8298):
                    value = exif.get(tag)
                    if isinstance(value, str) and value.strip():
                        result.chunks.append(
                            Chunk(value, f"TIFF tag {tag:#06x}", kind="metadata",
                                  sentence_start=False)
                        )
            elif len(exif) > 0 or info.get("exif"):
                result.exif.append("EXIF block")
            for key, value in info.items():
                key_text = str(key)
                if "exif" in key_text.lower() and key_text.lower() != "exif":
                    result.exif.append(f"EXIF text chunk '{key_text}'")
                    continue
                if key_text.lower() in _IMAGE_SKIP_INFO:
                    continue
                if isinstance(value, bytes):
                    text = value.decode("utf-8", errors="replace")
                elif isinstance(value, str):
                    text = value
                else:
                    continue
                if not text.strip():
                    continue
                result.metadata.append(MetaField("image", key_text, text, f"metadata {key_text}"))
                is_xml = text.lstrip().startswith("<")
                result.chunks.append(
                    Chunk(text, f"metadata {key_text}", kind="metadata", field=key_text,
                          sentence_start=False, closed_world=not is_xml)
                )
    except Exception as exc:  # Pillow raises many exception types for corrupt images
        result.problems.append(f"cannot read image ({type(exc).__name__})")
        return result
    result.notices.append("image pixels are not OCR-scanned")
    return result


# --------------------------------------------------------------------------------------------
# SQLite and Parquet


def extract_sqlite(data: bytes, path_on_disk: Path | None) -> Extraction:
    result = Extraction(kind="sqlite")
    connection = sqlite3.connect(":memory:")
    try:
        try:
            connection.deserialize(data)
            connection.execute("SELECT count(*) FROM sqlite_master").fetchone()
        except (AttributeError, sqlite3.DatabaseError):
            connection.close()
            if path_on_disk is None:
                result.problems.append("cannot open SQLite data")
                return result
            uri = path_on_disk.resolve().as_uri() + "?mode=ro&immutable=1"
            connection = sqlite3.connect(uri, uri=True)
        tables = connection.execute(
            "SELECT name, type, coalesce(sql, '') FROM sqlite_master ORDER BY rowid"
        ).fetchall()
        for name, kind, sql in tables:
            if sql:
                result.chunks.append(Chunk(sql, f"schema {kind} {name}", closed_world=False))
        for name, kind, sql in tables:
            if kind != "table" or sql.upper().startswith("CREATE VIRTUAL TABLE"):
                continue
            quoted = '"' + name.replace('"', '""') + '"'
            columns = [row[1] for row in connection.execute(f"PRAGMA table_info({quoted})")]
            cursor = connection.execute(f"SELECT * FROM {quoted} LIMIT {MAX_TABLE_ROWS}")
            for row_no, row in enumerate(cursor, start=1):
                for column, value in zip(columns, row, strict=False):
                    location = f"table {name} row {row_no} column {column}"
                    if isinstance(value, str) and value.strip():
                        result.chunks.append(Chunk(value, location, sentence_start=False))
                    elif isinstance(value, bytes) and value:
                        result.chunks.extend(
                            Chunk(c.text, location, closed_world=False)
                            for c in strings_chunks(value)
                        )
    except sqlite3.DatabaseError as exc:
        result.problems.append(f"cannot read SQLite database ({exc})")
    finally:
        connection.close()
    return result


def extract_parquet(path_on_disk: Path | None) -> Extraction:
    result = Extraction(kind="parquet")
    try:
        import duckdb
    except ImportError:
        result.notices.append("unscanned: duckdb is not installed, Parquet content not scanned")
        return result
    if path_on_disk is None:
        result.notices.append("unscanned: Parquet data outside the working tree is not scanned")
        return result
    connection = duckdb.connect(":memory:")
    try:
        target = str(path_on_disk)
        cursor = connection.execute("SELECT * FROM read_parquet(?)", [target])
        columns = [str(item[0]) for item in cursor.description or []]
        result.chunks.append(Chunk(" ".join(columns), "columns", sentence_start=False))
        row_no = 0
        while row_no < MAX_TABLE_ROWS:
            rows = cursor.fetchmany(5000)
            if not rows:
                break
            for row in rows:
                row_no += 1
                for column, value in zip(columns, row, strict=False):
                    if isinstance(value, str) and value.strip():
                        result.chunks.append(
                            Chunk(value, f"row {row_no} column {column}", sentence_start=False)
                        )
        for key, value in connection.execute(
            "SELECT key, value FROM parquet_kv_metadata(?)", [target]
        ).fetchall():
            text = f"{_as_text(key)}: {_as_text(value)}"
            result.chunks.append(Chunk(text, "key-value metadata", kind="metadata",
                                       closed_world=False))
        for (created_by,) in connection.execute(
            "SELECT created_by FROM parquet_file_metadata(?)", [target]
        ).fetchall():
            if created_by:
                result.chunks.append(Chunk(str(created_by), "created_by", kind="metadata",
                                           closed_world=False))
    except duckdb.Error as exc:
        result.problems.append(f"cannot read Parquet file ({type(exc).__name__})")
    finally:
        connection.close()
    return result


def _as_text(value: object) -> str:
    if isinstance(value, bytes | bytearray):
        return bytes(value).decode("utf-8", errors="replace")
    return str(value)


# --------------------------------------------------------------------------------------------
# Unknown binaries


def strings_chunks(data: bytes) -> list[Chunk]:
    """Printable ASCII and UTF-16LE runs (like ``strings``) for the identifier rules only."""
    chunks = [
        Chunk(match.group().decode("ascii"), f"offset {match.start()}", closed_world=False)
        for match in _PRINTABLE_RE.finditer(data)
    ]
    chunks.extend(
        Chunk(match.group().decode("utf-16-le"), f"offset {match.start()}", closed_world=False)
        for match in _UTF16_RE.finditer(data)
    )
    return chunks
