#!/usr/bin/env python3
"""azd ``preprovision`` hook: run the DocWiki preflight before any resource is created.

Set ``DOCWIKI_SKIP_PREFLIGHT=true`` to bypass it (not recommended) and
``DOCWIKI_PREFLIGHT_SKIP=quota,roles`` to skip individual checks.
"""

from __future__ import annotations

import os
import sys

if sys.version_info < (3, 12):  # noqa: UP036 - must run (and explain) on older interpreters
    major, minor = sys.version_info[:2]
    sys.stderr.write(f"[docwiki] ERROR: Python 3.12+ is required (found {major}.{minor}).\n")
    raise SystemExit(1)

from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(SCRIPTS / "hooks"))

import preflight  # noqa: E402
from azdlib import is_true, warn  # noqa: E402


def main() -> int:
    if is_true(os.environ.get("DOCWIKI_SKIP_PREFLIGHT")):
        warn("DOCWIKI_SKIP_PREFLIGHT is set: preflight checks skipped")
        return 0
    return preflight.main([])


if __name__ == "__main__":
    raise SystemExit(main())
