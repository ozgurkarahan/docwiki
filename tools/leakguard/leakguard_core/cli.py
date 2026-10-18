"""Command line: ``leakguard.py scan`` and ``leakguard.py denylist-ids``.

Exit codes: 0 clean, 1 findings (errors; warnings only with ``--strict``), 2 configuration error.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from pathlib import Path

from . import __version__
from .config import load_denylist
from .model import ConfigError
from .report import render_json, render_text
from .scanner import Scanner, ScanOptions

EXIT_CONFIG = 2


def _ci_default() -> bool:
    return os.environ.get("CI", "").strip().lower() in {"1", "true", "yes"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="leakguard",
        description="DocWiki publication-safety scanner (secrets, identifiers, real names).",
    )
    parser.add_argument("--version", action="version", version=f"leakguard {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)

    scan = commands.add_parser("scan", help="scan the repository (and optional site folders)")
    scan.add_argument("--root", type=Path, default=Path("."), help="repository to scan")
    scan.add_argument("--history", action="store_true", help="also scan every commit (git log)")
    scan.add_argument(
        "--commits-from",
        metavar="FILE",
        help="scan only the commits listed in FILE (one SHA per line, '-' for stdin)",
    )
    scan.add_argument(
        "--include-untracked",
        action="store_true",
        help="also scan untracked files that are not ignored",
    )
    scan.add_argument(
        "--site",
        action="append",
        type=Path,
        default=[],
        metavar="DIR",
        help="built site or generated wiki folder to scan (repeatable)",
    )
    scan.add_argument(
        "--denylist", type=Path, help="private deny-list file (default: $DOCWIKI_DENYLIST)"
    )
    scan.add_argument(
        "--allowlist",
        type=Path,
        help="fiction allowlist (default: samples/fiction/allowlist.txt in the repository)",
    )
    scan.add_argument(
        "--ignore-file",
        type=Path,
        help="reviewed false positives (default: tools/leakguard/ignore.txt)",
    )
    scan.add_argument(
        "--site-vendor",
        type=Path,
        help="reviewed exemptions for vendor bundles of --site folders "
        "(default: tools/leakguard/site_vendor.txt)",
    )
    scan.add_argument("--strict", action="store_true", help="warnings also fail the scan")
    scan.add_argument("--format", choices=("text", "json"), default="text")
    scan.add_argument(
        "--redact",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="never print matched text (default: on when CI=true)",
    )

    ids = commands.add_parser(
        "denylist-ids", help="print the rule id (deny:<hash>) of every deny-list line"
    )
    ids.add_argument(
        "--denylist", type=Path, help="private deny-list file (default: $DOCWIKI_DENYLIST)"
    )
    return parser


def _read_commits(source: str) -> list[str]:
    if source == "-":
        text = sys.stdin.read()
    else:
        try:
            text = Path(source).read_text(encoding="utf-8")
        except OSError as exc:
            raise ConfigError(f"cannot read --commits-from file: {exc.strerror}") from None
    commits = [line.strip() for line in text.splitlines() if line.strip()]
    for commit in commits:
        if not all(ch in "0123456789abcdefABCDEF" for ch in commit) or len(commit) < 7:
            raise ConfigError("--commits-from must list commit SHAs (hexadecimal), one per line")
    return commits


def _scan(args: argparse.Namespace) -> int:
    redact = _ci_default() if args.redact is None else bool(args.redact)
    commits = _read_commits(args.commits_from) if args.commits_from else None
    options = ScanOptions(
        root=args.root,
        history=args.history,
        commits=commits,
        include_untracked=args.include_untracked,
        sites=list(args.site),
        denylist=args.denylist,
        allowlist=args.allowlist,
        ignore_file=args.ignore_file,
        site_vendor=args.site_vendor,
        strict=args.strict,
        redact=redact,
    )
    report = Scanner(options).run()
    output = render_json(report) if args.format == "json" else render_text(report)
    sys.stdout.write(output)
    sys.stdout.flush()
    return report.exit_code


def _denylist_ids(args: argparse.Namespace) -> int:
    path = args.denylist
    if path is None and os.environ.get("DOCWIKI_DENYLIST"):
        path = Path(os.environ["DOCWIKI_DENYLIST"])
    if path is None:
        raise ConfigError("no deny-list configured (set DOCWIKI_DENYLIST or --denylist)")
    for pattern in load_denylist(path.expanduser()):
        sys.stdout.write(f"{pattern.rule}  line {pattern.line_no}\n")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(errors="backslashreplace")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "scan":
            return _scan(args)
        return _denylist_ids(args)
    except ConfigError as exc:
        sys.stderr.write(f"leakguard: configuration error: {exc}\n")
        return EXIT_CONFIG
