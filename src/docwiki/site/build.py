"""Build the Quartz site of a release (site.md §1–3).

The pinned Quartz tag (``site/QUARTZ_VERSION``) is cloned into ``.cache/quartz/<tag>`` (reused when
present), installed with ``npm ci`` from Quartz's own lock file, reset to the tag, overlaid with
``site/`` (configuration, layout, components, styles, static files) and fed with the content
namespace as ``content/``: a release's ``wiki/`` with its ``evidence/`` mounted at ``evidence/``,
or a portable wiki folder as is (``evidence/`` already inside, ``.docwiki/`` machine files left
out). It is then built with the Quartz CLI (``npx quartz build`` ≡
``node quartz/bootstrap-cli.mjs build``), copied to ``out_dir`` and checked: internal links and
anchors (:mod:`docwiki.site.links`) and the security scan (:mod:`docwiki.site.scan`). The filed
research answers (``queries/``) are published as ``static/docwiki/answers.json`` for the "Ask this
wiki" drawer (:mod:`docwiki.site.answers`). No symlinks are used, so it runs unprivileged on
Windows.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Literal, Protocol

from docwiki.contracts.catalog import Catalog
from docwiki.contracts.frontmatter import read_frontmatter
from docwiki.contracts.gates import GateResult
from docwiki.contracts.ids import parse_release_id
from docwiki.contracts.layout import EVIDENCE_MOUNT, ReleaseFiles, WikiFiles
from docwiki.contracts.manifest import ReleaseManifest
from docwiki.contracts.settings import SettingsKeys
from docwiki.release.reader import ReleaseNotFoundError, ReleaseReader
from docwiki.site.answers import build_answers, write_answers
from docwiki.site.errors import SiteBuildError
from docwiki.site.linkcheck import check_links
from docwiki.site.process_page import STAGES, write_documents_page, write_process_page
from docwiki.site.security import REPO_URL, default_allowed_hosts, scan_site

__all__ = [
    "DEFAULT_BANNER",
    "PORTABLE_DIR",
    "QUARTZ_REPOSITORY",
    "SETTINGS_FILE",
    "CommandRunner",
    "ReleaseView",
    "SiteBuildError",
    "apply_overlay",
    "assemble_content",
    "build_site",
    "default_cache_dir",
    "default_overlay_dir",
    "detect_fictional",
    "ensure_quartz",
    "is_portable_wiki",
    "looks_like_site",
    "normalize_base_url",
    "open_release",
    "read_quartz_version",
    "site_settings",
    "subprocess_runner",
]

QUARTZ_REPOSITORY = "https://github.com/jackyzha0/quartz.git"
SETTINGS_FILE = "docwiki-site.json"
"""Generated in the Quartz checkout; read by ``quartz/components/docwiki/settings.ts``."""
DEFAULT_BANNER = (
    "Every organisation, person, site and document in this wiki is invented. "
    "Not for operational use."
)
OVERLAY_FILES = ("quartz.config.ts", "quartz.layout.ts")
OVERLAY_DIRS = ("quartz",)
UNUSED_QUARTZ_FILES = (
    "quartz/static/giscus",
    "quartz/static/og-image.png",
    "quartz/static/icon.png",
)
"""Quartz static assets the DocWiki layout never references (giscus themes load from a CDN)."""
INSTALL_STAMP = ".docwiki-install"
PORTABLE_DIR = ".docwiki"
"""Machine files of a portable wiki folder (``manifest.json``, ``current.json``, ``search.db``,
``tables/``); never part of the site content."""
_PORTABLE_MARKERS = ("manifest.json", "current.json")
_TAG_RE = re.compile(r"^v\d+\.\d+\.\d+$")
_HOST_PATH_RE = re.compile(
    r"^[a-z0-9]([a-z0-9.\-]*[a-z0-9])?(:\d{1,5})?(/[A-Za-z0-9._~\-/]*)?$"
)
_FICTIONAL_RE = re.compile(r"^>\s*(\*\*)?FICTIONAL\b", re.MULTILINE)


class CommandRunner(Protocol):
    def __call__(self, args: Sequence[str], *, cwd: Path) -> str:
        """Run a command, return its standard output; raise :class:`SiteBuildError` on failure."""
        ...


def _tail(text: str, lines: int = 40) -> str:
    return "\n".join(text.strip().splitlines()[-lines:])


def subprocess_runner(args: Sequence[str], *, cwd: Path) -> str:
    try:
        completed = subprocess.run(
            list(args),
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise SiteBuildError(f"cannot run {args[0]}: {exc}") from exc
    if completed.returncode != 0:
        output = _tail(f"{completed.stdout}\n{completed.stderr}")
        raise SiteBuildError(
            f"{Path(args[0]).name} {' '.join(args[1:3])} failed "
            f"(exit {completed.returncode}):\n{output}"
        )
    return completed.stdout


def _tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise SiteBuildError(f"{name} is required to build the site (Node 22+ with npm, and git)")
    return found


def _repo_root() -> Path | None:
    for parent in Path(__file__).resolve().parents:
        if (parent / "site" / "QUARTZ_VERSION").is_file():
            return parent
    return None


def default_overlay_dir() -> Path:
    """``site/`` of the source checkout this package runs from."""
    root = _repo_root()
    if root is None:
        raise SiteBuildError("site overlay not found; pass overlay_dir (the repository's site/)")
    return root / "site"


def default_cache_dir() -> Path:
    """``.cache/quartz`` of the source checkout (git-ignored), else of the working directory."""
    return (_repo_root() or Path.cwd()) / ".cache" / "quartz"


def read_quartz_version(overlay_dir: Path) -> str:
    tag = (overlay_dir / "QUARTZ_VERSION").read_text(encoding="utf-8").strip()
    if not _TAG_RE.match(tag):
        raise SiteBuildError(f"invalid Quartz tag in QUARTZ_VERSION: {tag!r}")
    return tag


def normalize_base_url(value: str | None) -> str | None:
    """Quartz ``baseUrl``: host and optional path, without scheme or trailing slash."""
    if value is None or not value.strip():
        return None
    base = re.sub(r"^[a-z][a-z0-9+.\-]*://", "", value.strip(), flags=re.IGNORECASE).rstrip("/")
    host, sep, path = base.partition("/")
    base = host.lower() + sep + path
    if not _HOST_PATH_RE.match(base):
        raise SiteBuildError(f"invalid base URL: {value!r}")
    return base


def detect_fictional(index_markdown: str) -> bool:
    """True when the wiki home carries the fictional-sample notice (``> FICTIONAL …``)."""
    try:
        _, body = read_frontmatter(index_markdown)
    except Exception:
        body = index_markdown
    return bool(_FICTIONAL_RE.search(body))


def _rmtree(path: Path) -> None:
    def make_writable(func: Callable[..., Any], target: str, _exc: BaseException) -> None:
        os.chmod(target, stat.S_IWRITE)
        func(target)

    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.exists():
        shutil.rmtree(path, onexc=make_writable)


Layout = Literal["release", "portable"]


@dataclass(frozen=True)
class _Location:
    root: Path
    wiki_dir: Path
    evidence_dir: Path
    layout: Layout
    catalogs: tuple[Path, ...]


@dataclass(frozen=True)
class ReleaseView:
    """What the site needs from a release: its wiki, its evidence and its catalog.

    ``layout`` is ``release`` (``releases/<id>/`` with ``wiki/`` and ``evidence/``, published or
    staged before ``manifest.json`` exists, as in the pipeline's ``site`` stage) or ``portable``
    (wiki content at the folder root, ``evidence/`` inside it, machine files under ``.docwiki/``).
    """

    root: Path
    catalog: Catalog
    wiki_dir: Path
    evidence_dir: Path
    layout: Layout = "release"

    @property
    def release_id(self) -> str:
        return self.catalog.release_id

    @property
    def release_date(self) -> str:
        return parse_release_id(self.catalog.release_id)[0].date().isoformat()

    @property
    def audience(self) -> str:
        return self.catalog.audience

    @property
    def manifest_path(self) -> Path:
        """Where the release manifest lives (absent while the pipeline stages the release)."""
        if self.layout == "portable":
            return self.root / PORTABLE_DIR / ReleaseFiles.MANIFEST
        return self.root / ReleaseFiles.MANIFEST

    def manifest(self) -> ReleaseManifest | None:
        path = self.manifest_path
        return ReleaseManifest.from_json(path.read_bytes()) if path.is_file() else None


def is_portable_wiki(path: str | Path) -> bool:
    """A portable wiki folder: ``.docwiki/manifest.json`` (or ``.docwiki/current.json``)."""
    machine = Path(path) / PORTABLE_DIR
    return any((machine / marker).is_file() for marker in _PORTABLE_MARKERS)


def _locate(path: str | Path) -> _Location:
    root = Path(path)
    if is_portable_wiki(root):
        catalogs = (root / WikiFiles.CATALOG, root / PORTABLE_DIR / ReleaseFiles.CATALOG)
        return _Location(root, root, root / EVIDENCE_MOUNT, "portable", catalogs)
    if not (root / ReleaseFiles.WIKI_DIR / WikiFiles.INDEX).is_file():
        try:
            root = ReleaseReader.open(root).root
        except ReleaseNotFoundError as exc:
            raise SiteBuildError(f"no release or portable wiki found at {path}") from exc
    wiki = root / ReleaseFiles.WIKI_DIR
    catalogs = (root / ReleaseFiles.CATALOG, wiki / WikiFiles.CATALOG)
    return _Location(root, wiki, root / ReleaseFiles.EVIDENCE_DIR, "release", catalogs)


def open_release(path: str | Path) -> ReleaseView:
    """A portable wiki folder, a release folder (staged or published), a ``releases/`` folder with
    ``current.json``, or a folder that contains ``releases/current.json``."""
    found = _locate(path)
    for candidate in found.catalogs:
        if candidate.is_file():
            catalog = Catalog.from_json(candidate.read_bytes())
            return ReleaseView(
                found.root, catalog, found.wiki_dir, found.evidence_dir, found.layout
            )
    raise SiteBuildError(f"no catalog.json in {found.layout} {found.root}")


def _quality_summary(gates: Sequence[GateResult]) -> dict[str, int] | None:
    """Gate counts for the home page's provenance line (``None`` without gate results)."""
    if not gates:
        return None
    statuses = Counter(gate.status for gate in gates)
    return {
        "gates": len(gates),
        "passed": statuses["pass"],
        "warned": statuses["warn"],
        "failed": statuses["fail"],
        "skipped": statuses["skipped"],
        "blockingFailed": sum(1 for gate in gates if gate.blocks_publish),
    }


def _content_slug(release: ReleaseView, wiki_path: str) -> str | None:
    """Content slug of a wiki page (``_meta/quality``) when the release has it."""
    if not (release.wiki_dir / wiki_path).is_file():
        return None
    return wiki_path.removesuffix(".md")


def site_settings(
    release: ReleaseView,
    *,
    base_url: str | None,
    page_title: str | None,
    banner: str | None,
    repo_url: str,
    quartz_version: str,
    gates: Sequence[GateResult] | None = None,
    run_id: str | None = None,
    answers: int | None = None,
) -> dict[str, Any]:
    """The ``docwiki-site.json`` payload read by the overlay.

    Gate results and the run id come from the release manifest; the pipeline's site stage builds
    the staged release before its manifest exists and passes them explicitly. ``answers`` is the
    number of filed research answers (counted from ``queries/`` when ``None``); the "Ask this
    wiki" drawer is left out of the pages when it is 0.
    """
    index_text = (release.wiki_dir / WikiFiles.INDEX).read_text(encoding="utf-8")
    if page_title is None:
        frontmatter, _ = read_frontmatter(index_text)
        page_title = str(frontmatter.get("title") or "DocWiki")
    if banner is None:
        banner = DEFAULT_BANNER if detect_fictional(index_text) else ""
    if gates is None or run_id is None:
        manifest = release.manifest()
        if manifest is not None:
            gates = manifest.gates if gates is None else gates
            run_id = manifest.run_id if run_id is None else run_id
    statuses = Counter(source.status for source in release.catalog.sources)
    titles = {page.id: page.title for page in release.catalog.pages if page.type == "source"}
    revisions = {source.source_id: source.revision for source in release.catalog.sources}
    sources: dict[str, dict[str, str | None]] = {}
    for page in release.catalog.pages:
        if page.type != "source":
            continue
        originals = sorted(
            path.name
            for path in (release.evidence_dir / page.id).glob("original.*")
            if path.is_file()
        )
        meta = _source_meta(release, page.path)
        source_path = _text(meta.get("source_path"))
        later = [sid for sid in meta.get("superseded_by") or [] if sid in titles]
        document = release.evidence_dir / page.id / "index.md"
        has_document = document.is_file()
        dated = _document_date(document) if has_document else None
        sources[page.id] = {
            "page": page.path.removesuffix(".md"),
            "title": page.title,
            "original": f"{EVIDENCE_MOUNT}/{page.id}/{originals[0]}" if originals else None,
            "status": page.status,
            # The documents register (ADR 0010, slice B).
            "document": f"{EVIDENCE_MOUNT}/{page.id}/index" if has_document else None,
            "docType": _text(meta.get("doc_type")),
            "docNumber": _text(meta.get("doc_number")),
            "revision": _text(meta.get("revision")),
            "date": dated or _path_date(source_path),
            "format": PurePosixPath(source_path).suffix.lstrip(".").lower() or None
            if source_path
            else None,
            "supersededBy": titles[later[0]] if later else None,
            "supersededByRevision": revisions.get(later[0]) if later else None,
        }
    return {
        "schema": 1,
        "pageTitle": page_title,
        "baseUrl": base_url,
        "repoUrl": repo_url,
        "banner": banner or None,
        "releaseId": release.release_id,
        "releaseDate": release.release_date,
        "audience": release.audience,
        "quartzVersion": quartz_version,
        "documents": {
            "current": statuses["current"],
            "superseded": statuses["superseded"],
        },
        # The story home's third card (ADR 0010): the wiki pages that cite at least one source.
        "citedPages": sum(1 for page in release.catalog.pages if page.sources),
        "runId": run_id,
        "runPage": _content_slug(release, f"{WikiFiles.RUNS_DIR}/{run_id}.md") if run_id else None,
        "qualityPage": _content_slug(release, WikiFiles.QUALITY),
        "quality": _quality_summary(gates or []),
        "sources": dict(sorted(sources.items())),
        "answers": len(build_answers(release)["answers"]) if answers is None else answers,
        "steps": [{"name": name, "text": text} for name, text in STAGES],
    }


_PATH_DATE_RE = re.compile(r"(?<!\d)(20\d{2}-[01]\d-[0-3]\d)(?!\d)")


def _text(value: Any) -> str | None:
    return value.strip() or None if isinstance(value, str) else None


def _path_date(source_path: str | None) -> str | None:
    """The document's date when its file name carries one (``2026-03-24_compte-rendu…``)."""
    found = _PATH_DATE_RE.search(source_path or "")
    return found.group(1) if found else None


def _document_date(index: Path) -> str | None:
    """``document_date`` of a document page (the evidence index), when the extraction found one."""
    try:
        meta, _ = read_frontmatter(index.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = meta.get("document_date") if isinstance(meta, dict) else None
    return str(value) if value else None


def _source_meta(release: ReleaseView, page_path: str) -> dict[str, Any]:
    """Frontmatter of a source page (empty when unreadable: the register just shows less)."""
    try:
        meta, _ = read_frontmatter((release.wiki_dir / page_path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return meta if isinstance(meta, dict) else {}


def _skip_hidden(_folder: str, names: list[str]) -> list[str]:
    """Hidden entries (``.docwiki/`` machine files, ``.agents``/``.claude``/``.github`` skill
    projections): Quartz never publishes them, so they are not copied either."""
    return [name for name in names if name.startswith(".")]


def assemble_content(release: ReleaseView | str | Path, content_dir: Path) -> int:
    """Quartz ``content/`` = the content namespace (CONTRACT.md §4): a release's ``wiki/`` with
    ``evidence/`` mounted at ``evidence/``, or a portable wiki folder as is.

    Returns the number of files copied. ``content_dir`` is replaced.
    """
    found = (
        _Location(release.root, release.wiki_dir, release.evidence_dir, release.layout, ())
        if isinstance(release, ReleaseView)
        else _locate(release)
    )
    if not (found.wiki_dir / WikiFiles.INDEX).is_file():
        raise SiteBuildError(f"no index.md in the wiki of {found.root}")
    if found.layout == "release" and (found.wiki_dir / EVIDENCE_MOUNT).exists():
        raise SiteBuildError("wiki/evidence is reserved for the evidence mount (CONTRACT.md §4)")
    _rmtree(content_dir)
    shutil.copytree(found.wiki_dir, content_dir, ignore=_skip_hidden)
    if found.layout == "release" and found.evidence_dir.is_dir():
        shutil.copytree(found.evidence_dir, content_dir / EVIDENCE_MOUNT, ignore=_skip_hidden)
    return sum(1 for path in content_dir.rglob("*") if path.is_file())


def apply_overlay(overlay_dir: Path, quartz_dir: Path) -> list[str]:
    """Copy the DocWiki overlay over a Quartz checkout and drop the static assets it does not use;
    returns the overlay paths written."""
    for unused in UNUSED_QUARTZ_FILES:
        _rmtree(quartz_dir / unused)
    written: list[str] = []
    for name in OVERLAY_FILES:
        source = overlay_dir / name
        if not source.is_file():
            raise SiteBuildError(f"overlay file missing: {source}")
        shutil.copyfile(source, quartz_dir / name)
        written.append(name)
    for folder in OVERLAY_DIRS:
        for source in sorted((overlay_dir / folder).rglob("*")):
            if not source.is_file():
                continue
            rel = source.relative_to(overlay_dir).as_posix()
            target = quartz_dir / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            written.append(rel)
    return written


def _git_output(runner: CommandRunner, checkout: Path, *args: str) -> str:
    return runner([_tool("git"), "-C", str(checkout), *args], cwd=checkout).strip()


def _valid_checkout(checkout: Path, tag: str, runner: CommandRunner) -> bool:
    if not (checkout / ".git").exists() or not (checkout / "package-lock.json").is_file():
        return False
    try:
        head = _git_output(runner, checkout, "rev-parse", "HEAD")
        tagged = _git_output(runner, checkout, "rev-parse", f"refs/tags/{tag}^{{commit}}")
    except SiteBuildError:
        return False
    return bool(head) and head == tagged


def ensure_quartz(
    tag: str,
    cache_dir: Path,
    *,
    runner: CommandRunner = subprocess_runner,
    log: Callable[[str], None] = lambda _message: None,
) -> Path:
    """A clean checkout of Quartz ``tag`` with its dependencies installed (idempotent)."""
    cache_dir = Path(cache_dir).resolve()
    checkout = cache_dir / tag
    git = _tool("git")
    if _valid_checkout(checkout, tag, runner):
        log(f"reusing Quartz {tag} in {checkout}")
        runner([git, "-C", str(checkout), "reset", "--hard", "--quiet"], cwd=checkout)
        runner(
            [git, "-C", str(checkout), "clean", "-fdxq", "-e", "node_modules"], cwd=checkout
        )
    else:
        _rmtree(checkout)
        cache_dir.mkdir(parents=True, exist_ok=True)
        log(f"cloning Quartz {tag} into {checkout}")
        runner(
            [git, "-c", "advice.detachedHead=false", "clone", "--quiet", "--depth", "1",
             "--branch", tag, QUARTZ_REPOSITORY, str(checkout)],
            cwd=cache_dir,
        )
    lock_hash = hashlib.sha256((checkout / "package-lock.json").read_bytes()).hexdigest()
    stamp = checkout / "node_modules" / INSTALL_STAMP
    if not stamp.is_file() or stamp.read_text(encoding="utf-8").strip() != lock_hash:
        log("installing Quartz dependencies (npm ci)")
        runner(
            [_tool("npm"), "ci", "--ignore-scripts", "--no-audit", "--no-fund",
             "--loglevel=error"],
            cwd=checkout,
        )
        stamp.write_text(lock_hash + "\n", encoding="utf-8")
    return checkout


def looks_like_site(path: Path) -> bool:
    """A previous Quartz build (safe to replace)."""
    return (path / "index.html").is_file() and (path / "postscript.js").is_file()


@dataclass(frozen=True)
class _Checks:
    links: int
    anchors: int


def _verify(out_dir: Path, base_url: str | None, repo_url: str) -> _Checks:
    report = check_links(out_dir)
    findings = scan_site(out_dir, default_allowed_hosts(base_url, repo_url))
    problems = [str(problem) for problem in report.problems] + [str(f) for f in findings]
    if problems:
        shown = "\n".join(problems[:30])
        more = f"\n… and {len(problems) - 30} more" if len(problems) > 30 else ""
        raise SiteBuildError(f"the built site failed its checks ({out_dir}):\n{shown}{more}")
    return _Checks(report.links, report.anchors)


def _check_replaceable(out_dir: Path) -> None:
    if out_dir.exists() and any(out_dir.iterdir()) and not looks_like_site(out_dir):
        raise SiteBuildError(f"refusing to replace {out_dir}: not empty and not a Quartz build")


def _publish(build_dir: Path, out_dir: Path) -> None:
    _check_replaceable(out_dir)
    staging = out_dir.with_name(f".{out_dir.name}.tmp-{os.getpid()}")
    _rmtree(staging)
    out_dir.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(build_dir, staging)
        _rmtree(out_dir)
        staging.replace(out_dir)
    finally:
        _rmtree(staging)


def build_site(
    release_root: str | Path,
    out_dir: str | Path,
    *,
    base_url: str | None = None,
    page_title: str | None = None,
    banner: str | None = None,
    gates: Sequence[GateResult] | None = None,
    run_id: str | None = None,
    repo_url: str = REPO_URL,
    overlay_dir: Path | None = None,
    cache_dir: Path | None = None,
    check: bool = True,
    runner: CommandRunner = subprocess_runner,
    env: Mapping[str, str] | None = None,
    log: Callable[[str], None] = lambda _message: None,
) -> Path:
    """Build the human site of a release into ``out_dir`` and return it.

    ``release_root`` is a portable wiki folder (``.docwiki/manifest.json``), a release folder
    (staged or published), a ``releases/`` folder with ``current.json``, or a folder that
    contains one. ``base_url`` defaults to
    ``DOCWIKI_SITE_BASE_URL``; the page title defaults to the title of ``wiki/index.md`` (the
    domain pack's ``wiki_title``); the banner (``None``: automatic) shows a fictional-sample
    notice when the home page carries one, and ``""`` disables it. ``gates`` and ``run_id``
    default to the release manifest (the pipeline passes them for a staged release). The filed
    research answers (``queries/``) are published as ``static/docwiki/answers.json`` for the
    "Ask this wiki" drawer. With ``check`` the built site must pass the link checker and the
    security scan, otherwise :class:`SiteBuildError` is raised (the output is kept for review).
    """
    environment = os.environ if env is None else env
    release = open_release(release_root)
    overlay = overlay_dir or default_overlay_dir()
    tag = read_quartz_version(overlay)
    base = normalize_base_url(
        base_url if base_url is not None else environment.get(SettingsKeys.SITE_BASE_URL)
    )
    target = Path(out_dir).resolve()
    root = release.root.resolve()
    if target == root or root.is_relative_to(target):
        raise SiteBuildError("out_dir must not contain the release")
    if (
        release.layout == "portable"
        and target.is_relative_to(root)
        and not target.is_relative_to(root / PORTABLE_DIR)
    ):
        raise SiteBuildError(
            "out_dir must be outside a portable wiki folder (or under its .docwiki/): "
            "the folder itself is the site content"
        )
    _check_replaceable(target)
    answers = build_answers(release)  # before Quartz, so that a bad query page fails fast

    checkout = ensure_quartz(tag, cache_dir or default_cache_dir(), runner=runner, log=log)
    apply_overlay(overlay, checkout)
    write_answers(answers, checkout)
    files = assemble_content(release, checkout / "content")
    write_process_page(checkout / "content")
    write_documents_page(checkout / "content")
    settings = site_settings(
        release,
        base_url=base,
        page_title=page_title,
        banner=banner,
        repo_url=repo_url,
        quartz_version=tag,
        gates=gates,
        run_id=run_id,
        answers=len(answers["answers"]),
    )
    (checkout / SETTINGS_FILE).write_text(
        json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    log(
        f"building {files} content files of {release.layout} {release.release_id} "
        f"with Quartz {tag}"
    )
    runner(
        [_tool("node"), "quartz/bootstrap-cli.mjs", "build", "-d", "content", "-o", "public"],
        cwd=checkout,
    )
    _publish(checkout / "public", target)
    log(f"site written to {target}")
    if check:
        checks = _verify(target, base, repo_url)
        log(f"checks passed: {checks.links} internal links, {checks.anchors} anchors, scan clean")
    return target
