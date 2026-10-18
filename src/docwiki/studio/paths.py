"""Safe document paths for uploads into ``raw/`` and links from the Studio into the wiki site."""

from __future__ import annotations

import re
import unicodedata
from urllib.parse import quote

from docwiki.extract.formats import SUPPORTED_EXTENSIONS, detect_format

__all__ = ["MAX_DEPTH", "MAX_PATH_CHARS", "PathError", "check_upload_path", "wiki_link"]

MAX_PATH_CHARS = 200
MAX_DEPTH = 4
_SEGMENT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,99}$")
_WIKI_PATH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_./-]{0,254}$")


class PathError(ValueError):
    """A document path the Studio refuses."""


def check_upload_path(path: str) -> str:
    """The normalised ``raw/``-relative path of an upload, or :class:`PathError`.

    Accepts at most four segments of letters, digits, spaces and ``._()+-`` (no leading dot, so
    no hidden files the pipeline would skip) and only the file types the pipeline extracts.
    """
    value = unicodedata.normalize("NFC", path or "").strip()
    if not value or len(value) > MAX_PATH_CHARS:
        raise PathError(f"the path must have 1 to {MAX_PATH_CHARS} characters")
    if value.startswith("/") or "\\" in value or "//" in value:
        raise PathError("the path must be relative and use '/' between folders")
    parts = value.split("/")
    if len(parts) > MAX_DEPTH:
        raise PathError(f"the path may have at most {MAX_DEPTH} segments")
    for part in parts:
        if part in (".", "..") or part != part.strip() or part.endswith("."):
            raise PathError(f"invalid path segment {part!r}")
        if not _SEGMENT_RE.match(part):
            raise PathError(
                f"invalid path segment {part!r}: use letters, digits, spaces and ._()+- only"
            )
    if detect_format(value) is None:
        raise PathError("unsupported file type; supported: " + ", ".join(SUPPORTED_EXTENSIONS))
    return value


def wiki_link(wiki_url: str | None, path: str | None) -> str | None:
    """URL of a release-relative page (``evidence/src-…/p0001.md``) on the wiki site.

    Quartz serves ``x/y.md`` at ``x/y`` (``x/index.md`` at ``x/``). Anything that is not a plain
    relative Markdown path gives ``None``: model output never becomes a link by itself.
    """
    if not wiki_url or not path:
        return None
    value = path.strip().split("#", 1)[0]
    if not _WIKI_PATH_RE.match(value) or not value.endswith(".md"):
        return None
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return None
    page = value[: -len(".md")]
    if page == "index":
        page = ""
    elif page.endswith("/index"):
        page = page[: -len("index")]
    return f"{wiki_url.rstrip('/')}/{quote(page, safe='/-_.')}"
