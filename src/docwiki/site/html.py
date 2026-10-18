"""Minimal HTML inspection shared by the link checker and the security scanner (stdlib only)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

__all__ = ["URL_ATTRIBUTES", "HtmlTag", "iter_site_files", "parse_html", "srcset_urls"]

URL_ATTRIBUTES: frozenset[str] = frozenset(
    {
        "href",
        "src",
        "srcset",
        "action",
        "formaction",
        "poster",
        "data",
        "xlink:href",
        "background",
        "cite",
        "longdesc",
        "ping",
        "manifest",
        "codebase",
    }
)
"""Attributes whose value is (or contains) a URL the browser may fetch or navigate to."""


@dataclass
class HtmlTag:
    name: str
    attrs: list[tuple[str, str | None]]
    line: int
    text: str = ""
    """Raw content of ``<script>`` and ``<style>`` elements."""
    in_template: bool = False

    def get(self, name: str) -> str | None:
        for key, value in self.attrs:
            if key == name:
                return value
        return None


class _Collector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tags: list[HtmlTag] = []
        self._raw_text: HtmlTag | None = None
        self._templates = 0

    def _record(self, tag: str, attrs: list[tuple[str, str | None]]) -> HtmlTag:
        item = HtmlTag(tag, attrs, self.getpos()[0], in_template=self._templates > 0)
        self.tags.append(item)
        return item

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        item = self._record(tag, attrs)
        if tag in ("script", "style"):
            self._raw_text = item
        elif tag == "template":
            self._templates += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._record(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style"):
            self._raw_text = None
        elif tag == "template" and self._templates:
            self._templates -= 1

    def handle_data(self, data: str) -> None:
        if self._raw_text is not None:
            self._raw_text.text += data


def parse_html(text: str) -> list[HtmlTag]:
    """Every start tag in document order, with attribute values entity-decoded."""
    collector = _Collector()
    collector.feed(text)
    collector.close()
    return collector.tags


def srcset_urls(value: str) -> list[str]:
    """URLs of a ``srcset`` value (``a.png 1x, b.png 2x``)."""
    urls: list[str] = []
    for candidate in value.split(","):
        parts = candidate.strip().split()
        if parts:
            urls.append(parts[0])
    return urls


def iter_site_files(site_dir: Path) -> Iterator[tuple[str, Path]]:
    """``(relative POSIX path, file)`` for every file of a built site, sorted."""
    for path in sorted(p for p in site_dir.rglob("*") if p.is_file()):
        yield path.relative_to(site_dir).as_posix(), path
