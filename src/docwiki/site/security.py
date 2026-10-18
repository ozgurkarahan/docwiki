"""Security scan of a built site (site.md §6).

Reports ``<script>`` tags other than the Quartz bundles, ``<iframe>``/``<object>``/``<embed>``,
inline event handlers, ``javascript:``/``data:`` URLs, external ``src``/``href`` hosts outside an
allowlist (the repository host and the site's own host) and injection canaries.

Command line: ``uv run python -m docwiki.site.scan <site-dir>`` (:mod:`docwiki.site.scan`).
"""

from __future__ import annotations

import html
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from docwiki.site.html import URL_ATTRIBUTES, HtmlTag, iter_site_files, parse_html, srcset_urls

__all__ = [
    "QUARTZ_SCRIPTS",
    "REPO_URL",
    "SiteFinding",
    "default_allowed_hosts",
    "scan_site",
]

REPO_URL = "https://github.com/ozgurkarahan/docwiki"
"""Public repository of DocWiki (linked from the site footer and landing section)."""

QUARTZ_SCRIPTS = frozenset({"prescript.js", "postscript.js", "static/docwiki/content-index.js"})
"""Same-origin scripts emitted by Quartz and the DocWiki overlay (site-relative paths)."""

_QUARTZ_INLINE = re.compile(
    r'^const fetchData = fetch\("[^"<>]*static/contentIndex\.json"\)'
    r"\.then\(data => data\.json\(\)\)$"
)
_DATA_SCRIPT_TYPES = frozenset({"application/json", "application/ld+json"})
_UNSAFE_SCHEMES = frozenset({"javascript", "data", "vbscript", "file", "blob", "filesystem"})
_WEB_SCHEMES = frozenset({"http", "https"})
_FRAME_TAGS = frozenset({"iframe", "frame", "frameset"})
_EMBED_TAGS = frozenset({"object", "embed", "applet"})
_TEXT_SUFFIXES = frozenset(
    {".html", ".htm", ".js", ".mjs", ".css", ".json", ".xml", ".txt", ".md", ".svg", ".map"}
)
_URL_NOISE = re.compile(r"[\x00-\x20\x7f]")
_SCHEME = re.compile(r"^([a-z][a-z0-9+.\-]*):", re.IGNORECASE)
_CSS_URL = re.compile(r"""url\(\s*(['"]?)(.*?)\1\s*\)|@import\s+(['"])(.*?)\3""", re.IGNORECASE)
_REFRESH_URL = re.compile(r"url\s*=\s*(['\"]?)(.+?)\1\s*$", re.IGNORECASE)
_ORIGIN = "https://site.invalid"


@dataclass(frozen=True, order=True)
class SiteFinding:
    path: str
    line: int
    rule: str
    """``script``, ``iframe``, ``object-embed``, ``inline-handler``, ``unsafe-url``,
    ``external-host``, ``external-scheme`` or ``canary``."""
    message: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


def _host_of(url: str) -> str | None:
    parsed = urlsplit(url if "://" in url or url.startswith("//") else f"//{url}")
    return parsed.hostname


def default_allowed_hosts(base_url: str | None = None, repo_url: str = REPO_URL) -> set[str]:
    """The repository host and the site's own host."""
    hosts = {_host_of(repo_url)}
    if base_url:
        hosts.add(_host_of(base_url))
    return {host for host in hosts if host}


def _host_allowed(host: str, allowed: frozenset[str]) -> bool:
    host = host.lower().rstrip(".")
    return any(
        host == entry or (entry.startswith(".") and host.endswith(entry)) for entry in allowed
    )


class _Scanner:
    def __init__(self, allowed_hosts: Iterable[str]) -> None:
        self.allowed = frozenset(host.lower().strip() for host in allowed_hosts if host.strip())
        self.findings: list[SiteFinding] = []

    def add(self, path: str, line: int, rule: str, message: str) -> None:
        self.findings.append(SiteFinding(path, line, rule, message))

    def check_url(self, path: str, line: int, value: str, where: str) -> None:
        url = _URL_NOISE.sub("", value)
        if not url:
            return
        scheme_match = _SCHEME.match(url)
        if scheme_match:
            scheme = scheme_match.group(1).lower()
            if scheme in _UNSAFE_SCHEMES:
                self.add(path, line, "unsafe-url", f"{scheme}: URL in {where}")
                return
            if scheme not in _WEB_SCHEMES:
                self.add(path, line, "external-scheme", f"{scheme}: URL in {where}")
                return
        elif not url.startswith("//"):
            return
        host = urlsplit(url if scheme_match else f"https:{url}").hostname
        if not host:
            self.add(path, line, "external-host", f"URL without a host in {where}: {value!r}")
        elif not _host_allowed(host, self.allowed):
            self.add(path, line, "external-host", f"{host} in {where}")

    def check_css(self, path: str, line: int, css: str, where: str) -> None:
        for match in _CSS_URL.finditer(css):
            url = match.group(2) if match.group(2) is not None else match.group(4)
            if not url:
                continue
            scheme = _SCHEME.match(_URL_NOISE.sub("", url))
            if scheme and scheme.group(1).lower() == "data":
                continue  # inline images and fonts in stylesheets cannot run code
            self.check_url(path, line, url, where)

    def check_script(self, path: str, tag: HtmlTag) -> None:
        script_type = (tag.get("type") or "").strip().lower()
        src = tag.get("src")
        if src is not None:
            target = urlsplit(urljoin(f"{_ORIGIN}/{path}", _URL_NOISE.sub("", src)))
            local = target.scheme == "https" and target.netloc == "site.invalid"
            if not (local and target.path.lstrip("/") in QUARTZ_SCRIPTS):
                self.add(path, tag.line, "script", f"script source is not a Quartz bundle: {src}")
            return
        if script_type in _DATA_SCRIPT_TYPES:
            return
        if not _QUARTZ_INLINE.match(tag.text.strip()):
            snippet = " ".join(tag.text.split())[:60]
            self.add(path, tag.line, "script", f"inline script: {snippet!r}")

    def scan_html(self, path: str, text: str) -> None:
        for tag in parse_html(text):
            if tag.name == "script":
                self.check_script(path, tag)
            elif tag.name in _FRAME_TAGS:
                self.add(path, tag.line, "iframe", f"<{tag.name}> element")
            elif tag.name in _EMBED_TAGS:
                self.add(path, tag.line, "object-embed", f"<{tag.name}> element")
            elif tag.name == "style":
                self.check_css(path, tag.line, tag.text, "<style>")
            if tag.name == "meta" and (tag.get("http-equiv") or "").lower() == "refresh":
                refresh = _REFRESH_URL.search(tag.get("content") or "")
                if refresh:
                    self.check_url(path, tag.line, refresh.group(2), "meta refresh")
            for name, value in tag.attrs:
                if name.startswith("on") and len(name) > 2:
                    self.add(path, tag.line, "inline-handler", f"{name} on <{tag.name}>")
                if value is None:
                    continue
                if name == "style":
                    self.check_css(path, tag.line, value, f"style of <{tag.name}>")
                elif name in URL_ATTRIBUTES:
                    urls = srcset_urls(value) if name == "srcset" else [value]
                    for url in urls:
                        self.check_url(path, tag.line, url, f"{name} of <{tag.name}>")

    def scan_canaries(self, path: str, text: str, canaries: Sequence[str]) -> None:
        decoded = html.unescape(text) if path.endswith((".html", ".htm", ".xml", ".svg")) else text
        for canary in canaries:
            for haystack in (text, decoded):
                position = haystack.find(canary)
                if position >= 0:
                    line = haystack.count("\n", 0, position) + 1
                    self.add(path, line, "canary", "injection canary found")
                    break


def scan_site(
    out_dir: str | Path,
    allowed_hosts: Iterable[str],
    *,
    canaries: Iterable[str] = (),
) -> list[SiteFinding]:
    """Scan every file of a built site; an empty list means the site is clean."""
    root = Path(out_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"site folder not found: {root}")
    scanner = _Scanner(allowed_hosts)
    canary_list = [canary for canary in canaries if canary]
    for rel, file in iter_site_files(root):
        suffix = file.suffix.lower()
        if suffix not in _TEXT_SUFFIXES:
            continue
        text = file.read_text(encoding="utf-8", errors="replace")
        if suffix in (".html", ".htm"):
            scanner.scan_html(rel, text)
        elif suffix == ".css":
            scanner.check_css(rel, 1, text, "stylesheet")
        if canary_list:
            scanner.scan_canaries(rel, text, canary_list)
    return sorted(set(scanner.findings))
