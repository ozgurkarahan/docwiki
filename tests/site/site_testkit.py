"""Shared paths and fake-site helpers for the site tests."""

from __future__ import annotations

import json
import posixpath
import re
import shutil
from collections.abc import Sequence
from pathlib import Path

from docwiki.contracts.frontmatter import read_frontmatter

REPO_ROOT = Path(__file__).resolve().parents[2]
MOCK_RELEASE = REPO_ROOT / "samples" / "fixtures" / "mock-release"
MOCK_RELEASE_ID = "20260401T090000Z-8a41b109"
MOCK_RELEASE_DIR = MOCK_RELEASE / "releases" / MOCK_RELEASE_ID
MOCK_TITLE = "Chantier Moreau mock wiki"
PLAN_A, PLAN_B, MINUTES = "src-7630d0741377", "src-59cf9366e50c", "src-f0757603684a"
PLAN_A_PAGE = "sources/pln-2026-003-indice-a-planning-et-suivi-des-achats"
PLAN_B_PAGE = "sources/pln-2026-003-indice-b-planning-et-suivi-des-achats"
MINUTES_PAGE = "sources/2026-03-24-compte-rendu-de-chantier-n3"
OVERLAY = REPO_ROOT / "site"


def make_portable(dest: Path, release_dir: Path = MOCK_RELEASE_DIR) -> Path:
    """A synthetic portable wiki folder made from a release: wiki content at the root, evidence/
    inside it, machine files (manifest, pointer, search.db, tables/) under .docwiki/."""
    shutil.copytree(release_dir / "wiki", dest)
    shutil.copytree(release_dir / "evidence", dest / "evidence")
    machine = dest / ".docwiki"
    machine.mkdir()
    for name in ("manifest.json", "search.db"):
        shutil.copyfile(release_dir / name, machine / name)
    shutil.copytree(release_dir / "tables", machine / "tables")
    pointer = release_dir.parent / "current.json"
    shutil.copyfile(pointer, machine / "current.json")
    return dest


SCOPES = {PLAN_A: "moreau", PLAN_B: "moreau", MINUTES: "entreprise"}
"""The scoped copy of the mock release: the schedule belongs to the chantier, the minutes to the
default scope (v1.7, ADR 0011)."""
HUB_PAGE = "chantiers/moreau"


def make_scoped(dest: Path, release_dir: Path = MOCK_RELEASE_DIR) -> Path:
    """A copy of the mock release whose sources have a scope and a phase, with the hub page of
    ``moreau`` and the hubs index (no manifest: the site does not need one)."""
    from docwiki.contracts.catalog import Catalog, catalog_page_for
    from docwiki.contracts.pages import Page, parse_frontmatter

    shutil.copytree(release_dir, dest, ignore=shutil.ignore_patterns("manifest.json"))
    wiki = dest / "wiki"
    stamp = {"schema": 1, "release": MOCK_RELEASE_ID}
    common = {"summary": "Fictional sample.", "sensitivity": "public", "updated": "2026-04-01"}
    pages = [
        Page(
            path=f"{HUB_PAGE}.md",
            frontmatter=parse_frontmatter(
                {
                    **common,
                    "id": "hub:chantiers/moreau",
                    "type": "hub",
                    "title": "Chantier Moreau",
                    "scope_type": "chantier",
                    "scope": "moreau",
                    "sources": sorted([PLAN_A, PLAN_B]),
                    "docwiki": stamp,
                }
            ),
            body=f"# Chantier Moreau\n\nThe documents of the chantier.\n\n"
            f"- [Planning and purchase tracking, indice B](../{PLAN_B_PAGE}.md)\n",
        ),
        Page(
            path="chantiers/index.md",
            frontmatter=parse_frontmatter(
                {
                    **common,
                    "id": "index:hubs/chantiers",
                    "type": "index",
                    "title": "Chantiers",
                    "docwiki": stamp,
                }
            ),
            body="# Chantiers\n\n- [Chantier Moreau](moreau.md): 2 documents\n",
        ),
    ]
    for page in pages:
        (wiki / page.path).parent.mkdir(parents=True, exist_ok=True)
        (wiki / page.path).write_bytes(page.render().encode("utf-8"))
    for rel in (PLAN_A_PAGE, PLAN_B_PAGE, MINUTES_PAGE):
        file = wiki / f"{rel}.md"
        page = Page.parse(file.read_text(encoding="utf-8"), f"{rel}.md")
        scope = SCOPES[page.frontmatter.id]
        update = {"scope": scope, "phase": "3" if scope == "moreau" else None}
        page = page.model_copy(update={"frontmatter": page.frontmatter.model_copy(update=update)})
        file.write_bytes(page.render().encode("utf-8"))
    for path in (dest / "catalog.json", wiki / "catalog.json"):
        catalog = Catalog.from_json(path.read_bytes())
        entries = {entry.path: entry for entry in catalog.pages}
        for page in pages:
            entries[page.path] = catalog_page_for(page.frontmatter, page.path)
        for rel in (PLAN_A_PAGE, PLAN_B_PAGE):
            entries[f"{rel}.md"] = entries[f"{rel}.md"].model_copy(update={"scope": "moreau"})
        entries[f"{MINUTES_PAGE}.md"] = entries[f"{MINUTES_PAGE}.md"].model_copy(
            update={"scope": "entreprise"}
        )
        sources = [
            item.model_copy(update={"scope": SCOPES[item.source_id]}) for item in catalog.sources
        ]
        updated = catalog.model_copy(
            update={"pages": sorted(entries.values(), key=lambda e: e.path), "sources": sources}
        )
        path.write_bytes(updated.to_json().encode("utf-8"))
    return dest


FR_HOME_TITLE = "Wiki maquette du chantier Moreau"
FR_MINUTES_TITLE = "Compte rendu de chantier n°3"
"""Titles of the canonical (French) copy of the mock release; the English mirror keeps the mock's
English titles (``MOCK_TITLE``, "Site meeting minutes n°3")."""
_LINK_RE = re.compile(r"\]\(([^)\s]+)\)")


def _set_frontmatter(text: str, values: dict[str, str]) -> str:
    """Set top-level ``key: value`` lines of a page's frontmatter (added before its end)."""
    head, sep, body = text.partition("\n---\n")
    lines = head.split("\n")
    for key, value in values.items():
        found = [i for i, line in enumerate(lines) if line.startswith(f"{key}:")]
        if found:
            lines[found[0]] = f"{key}: {value}"
        else:
            lines.append(f"{key}: {value}")
    return "\n".join(lines) + sep + body


def _mirror_links(body: str, page: str, mirrored: set[str]) -> str:
    """Links of a page copied one folder down (``en/``): links to mirrored pages stay as they
    are; links to anything else (evidence, ``llms.txt``, filed answers) go one level further up
    to the canonical tree."""

    def fix(match: re.Match[str]) -> str:
        target = match.group(1)
        if "://" in target or target.startswith(("#", "mailto:")):
            return match.group(0)
        path = target.split("#", 1)[0]
        folder = posixpath.dirname(page)
        resolved = posixpath.normpath(posixpath.join(folder, path)) if path else page
        if resolved in mirrored:
            return match.group(0)
        return f"](../{target})"

    return _LINK_RE.sub(fix, body)


def make_bilingual(dest: Path, release_dir: Path = MOCK_RELEASE_DIR) -> Path:
    """A two-language copy of the mock release, shaped as the release contract of ADR 0012 says:
    canonical French pages at ``wiki/<path>`` (``lang: fr``), an English mirror at
    ``wiki/en/<path>`` (``lang: en``, ``translation_of: <id>``, same ids and slugs, links to the
    shared evidence one level further up), catalog pages unique by ``(id, lang)`` and
    ``wiki_languages: ["fr", "en"]`` in the manifest. Filed answers (``queries/``) stay canonical
    and keep ``lang: en`` (the schema-1 page model accepts only English there)."""
    shutil.copytree(release_dir, dest)
    wiki = dest / "wiki"
    manifest = json.loads((dest / "manifest.json").read_text(encoding="utf-8"))
    manifest["wiki_languages"] = ["fr", "en"]
    (dest / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    pages = sorted(
        path.relative_to(wiki).as_posix()
        for path in wiki.rglob("*.md")
        if not any(part.startswith(".") for part in path.relative_to(wiki).parts)
    )
    mirrored = {rel for rel in pages if not rel.startswith("queries/") and rel != "AGENTS.md"}
    french = {"index.md": FR_HOME_TITLE, f"{MINUTES_PAGE}.md": FR_MINUTES_TITLE}
    for rel in pages:
        file = wiki / rel
        text = file.read_text(encoding="utf-8")
        if rel in mirrored:
            meta, _ = read_frontmatter(text)
            english = _set_frontmatter(text, {"lang": "en", "translation_of": str(meta["id"])})
            head, sep, body = english.partition("\n---\n")
            target = wiki / "en" / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(head + sep + _mirror_links(body, rel, mirrored), encoding="utf-8")
        if not rel.startswith("queries/"):
            values = {"lang": "fr"}
            if rel in french:
                values["title"] = french[rel]
            file.write_text(_set_frontmatter(text, values), encoding="utf-8")
    for path in (dest / "catalog.json", wiki / "catalog.json"):
        catalog = json.loads(path.read_text(encoding="utf-8"))
        canonical, mirror = [], []
        for entry in catalog["pages"]:
            if not entry["path"].startswith("queries/"):
                if entry["path"] in mirrored:
                    mirror.append(
                        {
                            **entry,
                            "path": f"en/{entry['path']}",
                            "lang": "en",
                            "translation_of": entry["id"],
                        }
                    )
                entry = {**entry, "lang": "fr", "title": french.get(entry["path"], entry["title"])}
            canonical.append(entry)
        catalog["pages"] = canonical + mirror
        path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    return dest


def write_site(root: Path, files: dict[str, str]) -> Path:
    """Write a small fake built site (``relative path → text``)."""
    for rel, text in files.items():
        path = root.joinpath(*rel.split("/"))
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return root


def page(body: str, *, head: str = "", depth: int = 0) -> str:
    """A page shaped like Quartz output (bundles referenced relative to the page)."""
    up = "../" * depth if depth else "./"
    return (
        "<!DOCTYPE html>\n<html><head>"
        f'<link href="{up}index.css" rel="stylesheet"/>'
        f'<script src="{up}prescript.js" type="application/javascript"></script>'
        f'<script src="{up}static/docwiki/content-index.js"></script>'
        f"{head}</head><body>{body}"
        f'<script src="{up}postscript.js" type="module"></script></body></html>\n'
    )


BUNDLES = {
    "index.css": "body{color:#222}\n",
    "prescript.js": "\n",
    "postscript.js": "\n",
    "static/docwiki/content-index.js": "\n",
}


class FakeTools:
    """Stands in for git, npm and node: records commands and fakes their effects."""

    HEAD = "0" * 40

    def __init__(self) -> None:
        self.commands: list[tuple[str, ...]] = []

    def __call__(self, args: Sequence[str], *, cwd: Path) -> str:
        tool = Path(args[0]).name
        command = (tool, *args[1:])
        self.commands.append(command)
        if tool == "git" and "clone" in args:
            checkout = Path(args[-1])
            write_site(
                checkout,
                {
                    ".git/HEAD": "ref",
                    "package-lock.json": "{}",
                    "quartz.config.ts": "stock",
                    "quartz/static/giscus/dark.css": "x",
                    "content/.gitkeep": "",
                },
            )
        elif tool == "git" and "rev-parse" in args:
            return self.HEAD + "\n"
        elif tool == "npm":
            (cwd / "node_modules").mkdir(exist_ok=True)
        elif tool == "node":
            settings = json.loads((cwd / "docwiki-site.json").read_text(encoding="utf-8"))
            title = settings["pageTitle"]
            write_site(
                cwd / "public",
                {
                    "index.html": f'<title>{title}</title><a href="sources/a">a</a>'
                    '<script src="postscript.js" type="module"></script>',
                    "sources/a.html": '<a href="../">home</a>'
                    '<a href="../evidence/src-x/p0001">evidence</a>',
                    "evidence/src-x/p0001.html": '<a href="../../sources/a">source</a>',
                    "postscript.js": "",
                },
            )
        return ""
