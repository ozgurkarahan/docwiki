"""Stage 12 — ``site``: build the Quartz site of a release through the site lane.

Calls ``docwiki.site.build_site(release_root, release_root / "site", page_title=…, banner=…,
base_url=…)`` on the staged release, before it is finalized, so the site is part of the
published release. The stage is recorded as ``skipped`` with a warning — and the release is
still published — when the site lane is not installed or Node/git are not available; any other
failure (build error, broken link, security scan finding) is ``failed`` and blocks the publish.
"""

from __future__ import annotations

import importlib
import shutil
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from docwiki.contracts.layout import ReleaseFiles

__all__ = [
    "REQUIRED_TOOLS",
    "STAGE_VERSION",
    "SiteResult",
    "build_site_for_release",
    "site_builder",
    "site_unavailable",
]

STAGE_VERSION = "2"
REQUIRED_TOOLS = ("node", "git")
MAX_MESSAGE_LINES = 12
_TOOLING_MESSAGE = "is required to build the site"

SiteBuilder = Callable[..., object]


@dataclass(frozen=True)
class SiteResult:
    status: Literal["built", "skipped", "failed"]
    message: str
    path: Path | None = None


def site_builder() -> SiteBuilder | None:
    """``docwiki.site.build_site`` when importable, else ``None``."""
    try:
        module = importlib.import_module("docwiki.site")
    except ImportError:
        return None
    builder = getattr(module, "build_site", None)
    return builder if callable(builder) else None


def _is_site_lane(builder: SiteBuilder) -> bool:
    return str(getattr(builder, "__module__", "")).startswith("docwiki.site")


def site_unavailable(builder: SiteBuilder | None = None) -> str | None:
    """Why the site cannot be built here, or ``None`` when it can."""
    build = builder or site_builder()
    if build is None:
        return "the site lane (docwiki.site) is not installed"
    if _is_site_lane(build):
        missing = [tool for tool in REQUIRED_TOOLS if shutil.which(tool) is None]
        if missing:
            return f"{' and '.join(missing)} not found (the site needs Node 22+ with npm, and git)"
    return None


def _clip(message: str) -> str:
    lines = message.strip().splitlines()
    shown = "\n".join(lines[:MAX_MESSAGE_LINES])
    if len(lines) > MAX_MESSAGE_LINES:
        shown += f"\n… and {len(lines) - MAX_MESSAGE_LINES} more lines"
    return shown


def build_site_for_release(
    release_root: Path,
    *,
    out_dir: Path | None = None,
    base_url: str | None = None,
    page_title: str | None = None,
    banner: str | None = None,
    builder: SiteBuilder | None = None,
) -> SiteResult:
    """Build the site into ``out_dir`` (default ``<release>/site``)."""
    build = builder or site_builder()
    reason = site_unavailable(build)
    if build is None or reason is not None:
        return SiteResult("skipped", f"site not built: {reason}")
    target = out_dir or Path(release_root) / ReleaseFiles.SITE_DIR
    try:
        path = build(
            Path(release_root),
            target,
            page_title=page_title,
            banner=banner,
            base_url=base_url,
        )
    except Exception as exc:  # the site lane runs Node/Quartz; any failure is reported
        message = _clip(str(exc))
        if _TOOLING_MESSAGE in message:
            return SiteResult("skipped", f"site not built: {message}")
        return SiteResult("failed", f"site build failed: {type(exc).__name__}: {message}")
    built = Path(path) if isinstance(path, (str, Path)) else target
    return SiteResult("built", f"site built in {built.name}", built)
