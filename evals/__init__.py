"""DocWiki evaluation: runner, deterministic metrics, baselines and scoreboard.

Implements ``docs/spec/evals.md``. Entry points are the scripts ``evals/run.py`` and
``evals/scoreboard.py``; see ``evals/README.md``. The golden set lives in ``evals/golden/``
(corpus lane); the private holdout never enters the repository.
"""

from __future__ import annotations

__all__ = ["METRICS_VERSION", "RESULT_FORMAT"]

METRICS_VERSION = "evals-metrics-v1"
"""Version of the deterministic metric definitions (recorded in every result file)."""

RESULT_FORMAT = "docwiki.evals.result/v1"
"""Format tag of ``evals/results/<date>-<system>-<split>.json``."""
