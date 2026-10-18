"""``python -m docwiki.site.scan <site-dir>``: security scan of a built site (site.md §6).

Exit code 0 when clean, 1 when there are findings (or link problems with ``--links``).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from docwiki.site.linkcheck import LinkReport, check_links
from docwiki.site.security import REPO_URL, default_allowed_hosts, scan_site


def _links_payload(report: LinkReport) -> dict[str, object]:
    return {
        "pages": report.pages,
        "links": report.links,
        "anchors": report.anchors,
        "problems": [asdict(problem) for problem in report.problems],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m docwiki.site.scan",
        description="Security scan of a built DocWiki site (site.md §6).",
    )
    parser.add_argument("site_dir", type=Path)
    parser.add_argument("--base-url", help="site host, allowed in links (e.g. docs.example.org)")
    parser.add_argument("--repo-url", default=REPO_URL, help="repository URL (host allowed)")
    parser.add_argument("--allow-host", action="append", default=[], help="extra allowed host")
    parser.add_argument("--canary", action="append", default=[], help="injection canary string")
    parser.add_argument("--canary-file", type=Path, help="file with one canary per line")
    parser.add_argument("--links", action="store_true", help="also run the link checker")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    canaries = list(args.canary)
    if args.canary_file:
        lines = args.canary_file.read_text(encoding="utf-8").splitlines()
        canaries.extend(line.strip() for line in lines if line.strip())
    allowed = default_allowed_hosts(args.base_url, args.repo_url) | set(args.allow_host)
    findings = scan_site(args.site_dir, allowed, canaries=canaries)
    report = check_links(args.site_dir) if args.links else None

    if args.json:
        payload: dict[str, object] = {
            "allowed_hosts": sorted(allowed),
            "findings": [asdict(finding) for finding in findings],
        }
        if report is not None:
            payload["links"] = _links_payload(report)
        print(json.dumps(payload, indent=2))
    else:
        for finding in findings:
            print(finding)
        print(f"scan: {len(findings)} finding(s); allowed hosts: {', '.join(sorted(allowed))}")
        if report is not None:
            for problem in report.problems:
                print(problem)
            print(report.summary())
    failed = bool(findings) or (report is not None and not report.ok)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
