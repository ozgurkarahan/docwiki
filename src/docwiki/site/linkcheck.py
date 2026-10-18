"""Link checker for a built site: every internal ``href``/``src`` target and anchor must exist.

Quartz serves pages without their ``.html`` extension and folders through ``index.html``, so a URL
path ``sources/a`` resolves to ``sources/a``, ``sources/a.html`` or ``sources/a/index.html``.
External URLs are out of scope here (see :mod:`docwiki.site.scan`).

Command line: ``uv run python -m docwiki.site.links <site-dir>`` (:mod:`docwiki.site.links`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

from docwiki.site.html import HtmlTag, iter_site_files, parse_html, srcset_urls

__all__ = ["LinkProblem", "LinkReport", "check_links", "resolve_site_path"]

LINK_ATTRIBUTES = frozenset({"href", "src", "srcset", "poster"})
_ORIGIN = "https://site.invalid"


@dataclass(frozen=True, order=True)
class LinkProblem:
    page: str
    line: int
    url: str
    reason: str
    """``missing-target`` or ``missing-anchor``."""

    def __str__(self) -> str:
        return f"{self.page}:{self.line}: {self.reason}: {self.url}"


@dataclass
class LinkReport:
    pages: int = 0
    links: int = 0
    """Internal links and resources checked (same-page anchors included)."""
    anchors: int = 0
    """Links whose ``#fragment`` was checked against the target's ids."""
    problems: list[LinkProblem] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.problems

    def summary(self) -> str:
        status = "ok" if self.ok else f"{len(self.problems)} problem(s)"
        return (
            f"links: {self.pages} pages, {self.links} internal links, "
            f"{self.anchors} anchors checked: {status}"
        )


def resolve_site_path(files: set[str] | frozenset[str], url_path: str) -> str | None:
    """Site file served for a URL path, or ``None``."""
    path = url_path.lstrip("/")
    if not path or path.endswith("/"):
        candidates = [f"{path}index.html"]
    else:
        candidates = [path, f"{path}.html", f"{path}/index.html"]
    return next((candidate for candidate in candidates if candidate in files), None)


def _ids(tags: list[HtmlTag]) -> set[str]:
    found: set[str] = set()
    for tag in tags:
        if tag.in_template:
            continue
        for name, value in tag.attrs:
            if value and (name == "id" or (name == "name" and tag.name == "a")):
                found.add(value)
    return found


def check_links(site_dir: str | Path, *, check_anchors: bool = True) -> LinkReport:
    """Check every internal link and resource reference of every HTML page of ``site_dir``."""
    root = Path(site_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"site folder not found: {root}")
    files = {rel for rel, _ in iter_site_files(root)}
    pages = {
        rel: parse_html((root / rel).read_text(encoding="utf-8", errors="replace"))
        for rel in sorted(files)
        if rel.endswith(".html")
    }
    ids = {rel: _ids(tags) for rel, tags in pages.items()}
    report = LinkReport(pages=len(pages))
    for rel, tags in pages.items():
        base = f"{_ORIGIN}/{rel}"
        for tag in tags:
            if tag.in_template:
                continue
            for name, value in tag.attrs:
                if name not in LINK_ATTRIBUTES or not value or not value.strip():
                    continue
                urls = srcset_urls(value) if name == "srcset" else [value.strip()]
                for url in urls:
                    _check(
                        url,
                        base=base,
                        page=rel,
                        line=tag.line,
                        files=files,
                        ids=ids,
                        check_anchors=check_anchors,
                        report=report,
                    )
    report.problems.sort()
    return report


def _check(
    url: str,
    *,
    base: str,
    page: str,
    line: int,
    files: set[str],
    ids: dict[str, set[str]],
    check_anchors: bool,
    report: LinkReport,
) -> None:
    if url.startswith("//") or urlsplit(url).scheme:
        return
    absolute = urlsplit(urljoin(base, url))
    report.links += 1
    if url.startswith("#"):
        target: str | None = page
    else:
        target = resolve_site_path(files, unquote(absolute.path))
        if target is None:
            report.problems.append(LinkProblem(page, line, url, "missing-target"))
            return
    fragment = unquote(absolute.fragment)
    if check_anchors and fragment and target.endswith(".html"):
        report.anchors += 1
        if fragment not in ids.get(target, set()):
            report.problems.append(LinkProblem(page, line, url, "missing-anchor"))
