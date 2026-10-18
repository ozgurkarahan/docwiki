"""``docwiki export obsidian``: copy a release into an Obsidian vault with ``[[wikilinks]]``.

The canonical wiki uses relative Markdown links (wiki-contract §5); Obsidian prefers wikilinks.
The export copies ``wiki/`` (without the hidden skill projections) and ``evidence/`` into the
vault and rewrites every relative link to a Markdown page as ``[[path#Heading|text]]`` (paths
from the vault root, headings by their text). Code spans and fenced code are left untouched.
"""

from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from pathlib import Path

from docwiki.contracts.layout import EVIDENCE_MOUNT, ReleaseFiles
from docwiki.contracts.markdown import extract_headings, resolve_href

__all__ = ["ExportResult", "export_obsidian", "rewrite_wikilinks"]

_LINK_RE = re.compile(r"(?<!!)\[(?P<text>(?:[^\[\]\\]|\\.)*)\]\((?P<href>[^)\s]+)\)")
_CODE_RE = re.compile(r"(`+)(?:(?!\1).)+?\1")
_FENCE_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})")


@dataclass(frozen=True)
class ExportResult:
    vault: Path
    files: int
    links: int


def _unescape(text: str) -> str:
    return re.sub(r"\\(.)", r"\1", text)


def _alias(text: str) -> str:
    return _unescape(text).replace("|", "-").replace("]]", "] ]").replace("[[", "[ [")


def rewrite_wikilinks(
    markdown: str, page_path: str, headings: dict[str, dict[str, str]]
) -> tuple[str, int]:
    """Rewrite relative ``.md`` links of ``page_path`` as wikilinks; returns ``(text, count)``.

    ``headings`` maps content paths to ``{anchor: heading text}``.
    """
    count = 0
    out: list[str] = []
    fence: str | None = None
    for line in markdown.split("\n"):
        match = _FENCE_RE.match(line)
        if fence is not None:
            out.append(line)
            if match and match.group(1)[0] == fence[0]:
                fence = None
            continue
        if match:
            fence = match.group(1)
            out.append(line)
            continue
        pieces: list[str] = []
        position = 0
        for code in [*_CODE_RE.finditer(line), None]:
            end = code.start() if code is not None else len(line)
            segment = line[position:end]

            def replace(found: re.Match[str]) -> str:
                nonlocal count
                resolved = resolve_href(page_path, found.group("href"))
                if resolved.external or resolved.path is None or not resolved.path.endswith(".md"):
                    return found.group(0)
                target = resolved.path.removesuffix(".md")
                heading = ""
                if resolved.anchor:
                    title = headings.get(resolved.path, {}).get(resolved.anchor)
                    heading = f"#{title}" if title else ""
                count += 1
                return f"[[{target}{heading}|{_alias(found.group('text'))}]]"

            pieces.append(_LINK_RE.sub(replace, segment))
            if code is not None:
                pieces.append(code.group(0))
                position = code.end()
        out.append("".join(pieces))
    return "\n".join(out), count


def export_obsidian(release_root: Path, out_dir: Path) -> ExportResult:
    """Copy the release ``wiki/`` and ``evidence/`` into ``out_dir`` with wikilinks."""
    wiki = Path(release_root) / ReleaseFiles.WIKI_DIR
    evidence = Path(release_root) / ReleaseFiles.EVIDENCE_DIR
    if not wiki.is_dir():
        raise FileNotFoundError(f"no wiki/ folder in {release_root}")
    files: dict[str, Path] = {}
    for path in sorted(wiki.rglob("*")):
        rel = path.relative_to(wiki).as_posix()
        if path.is_file() and not rel.startswith("."):
            files[rel] = path
    if evidence.is_dir():
        for path in sorted(evidence.rglob("*")):
            if path.is_file():
                files[f"{EVIDENCE_MOUNT}/{path.relative_to(evidence).as_posix()}"] = path
    headings: dict[str, dict[str, str]] = {}
    for rel, path in files.items():
        if rel.endswith(".md"):
            text = path.read_text(encoding="utf-8")
            headings[rel] = {h.anchor: h.text for h in extract_headings(text)}
    vault = Path(out_dir)
    vault.mkdir(parents=True, exist_ok=True)
    links = 0
    for rel, path in files.items():
        target = vault.joinpath(*rel.split("/"))
        target.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith(".md"):
            text, count = rewrite_wikilinks(path.read_text(encoding="utf-8"), rel, headings)
            links += count
            target.write_text(text, encoding="utf-8", newline="\n")
        else:
            shutil.copyfile(path, target)
    return ExportResult(vault=vault, files=len(files), links=links)
