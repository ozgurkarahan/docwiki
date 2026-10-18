"""DocWiki leak guard command line.

Usage: ``uv run python tools/leakguard/leakguard.py scan --root . [--history] [--strict]``.
See tools/leakguard/README.md for the rules and configuration files.
"""

from __future__ import annotations

import sys
from pathlib import Path


def _main() -> int:
    tool_dir = str(Path(__file__).resolve().parent)
    if tool_dir not in sys.path:
        sys.path.insert(0, tool_dir)
    from leakguard_core.cli import main

    return main()


if __name__ == "__main__":
    raise SystemExit(_main())
