#!/usr/bin/env python3
"""Operator helpers of the evaluation stack (agents/README.md, "Evaluation variants").

    uv run python scripts/eval_stack.py encode                  # azd DOCWIKI_EVAL_MCP_VARIANTS
    uv run python scripts/eval_stack.py identities              # client IDs for the allowlist
    uv run python scripts/eval_stack.py grant --dry-run         # Wiki.Read for the variant agents
    uv run python scripts/eval_stack.py grant

The implementation lives in ``docwiki.agents_client.evalstack`` so that it is tested with the
package.
"""

from __future__ import annotations

import sys
from pathlib import Path

from docwiki.agents_client.evalstack import main

if __name__ == "__main__":
    sys.exit(main(agents_dir=Path(__file__).resolve().parents[1] / "agents"))
