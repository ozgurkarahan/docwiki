"""Command line of the evaluation runner (implementation: ``evals/runner.py``).

    uv run python evals/run.py --system docwiki-researcher|baseline-rag|baseline-long-context \
        --questions evals/golden/dev.jsonl [--split-name dev] [--limit N] \
        [--corpus samples/corpus] [--out evals/results] [--private-out DIR] [--catalog PATH] \
        [--judge]

See ``evals/README.md``.
"""

from __future__ import annotations

import sys
from pathlib import Path

if __package__ in (None, ""):  # run as a script: make the repository root importable
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.runner import main

if __name__ == "__main__":
    raise SystemExit(main())
