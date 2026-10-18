"""``python -m docwiki.site <release> --out DIR``: build, check and scan the site of a release."""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from pathlib import Path

from docwiki.site.build import SiteBuildError, build_site, looks_like_site
from docwiki.site.security import REPO_URL


def _size(path: Path) -> int:
    return sum(file.stat().st_size for file in path.rglob("*") if file.is_file())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m docwiki.site",
        description="Build the Quartz site of a DocWiki release (pinned Quartz + site/ overlay).",
    )
    parser.add_argument("release", type=Path, help="release folder, releases/ or its parent")
    parser.add_argument("--out", type=Path, required=True, help="output folder (replaced)")
    parser.add_argument("--base-url", help="public host, e.g. docs.example.org (default: env)")
    parser.add_argument("--title", help="site title (default: title of wiki/index.md)")
    parser.add_argument("--banner", help="banner text; empty string disables it")
    parser.add_argument("--repo-url", default=REPO_URL)
    parser.add_argument("--cache-dir", type=Path, help="Quartz checkout cache (.cache/quartz)")
    parser.add_argument("--overlay-dir", type=Path, help="DocWiki overlay (the repo's site/)")
    parser.add_argument("--no-check", action="store_true", help="skip link check and scan")
    args = parser.parse_args(argv)

    started = time.monotonic()
    try:
        out = build_site(
            args.release,
            args.out,
            base_url=args.base_url,
            page_title=args.title,
            banner=args.banner,
            repo_url=args.repo_url,
            overlay_dir=args.overlay_dir,
            cache_dir=args.cache_dir,
            check=not args.no_check,
            log=lambda message: print(message, flush=True),
        )
    except SiteBuildError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if looks_like_site(out):
        files = sum(1 for file in out.rglob("*") if file.is_file())
        print(
            f"done in {time.monotonic() - started:.1f} s: {files} files, "
            f"{_size(out) / 1024:.0f} KiB in {out}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
