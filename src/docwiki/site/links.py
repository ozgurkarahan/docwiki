"""``python -m docwiki.site.links <site-dir>``: check internal links and anchors of a built site.

Exit code 0 when every internal ``href``/``src`` target and ``#anchor`` resolves, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from pathlib import Path

from docwiki.site.linkcheck import check_links


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m docwiki.site.links",
        description="Check that every internal link and anchor of a built site resolves.",
    )
    parser.add_argument("site_dir", type=Path)
    parser.add_argument("--no-anchors", action="store_true", help="skip #fragment checks")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)
    report = check_links(args.site_dir, check_anchors=not args.no_anchors)
    if args.json:
        payload = {
            "pages": report.pages,
            "links": report.links,
            "anchors": report.anchors,
            "problems": [asdict(problem) for problem in report.problems],
        }
        print(json.dumps(payload, indent=2))
    else:
        for problem in report.problems:
            print(problem)
        print(report.summary())
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
