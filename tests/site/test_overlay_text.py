"""The overlay's pure TypeScript helpers, run with Node (skipped when Node cannot strip types)."""

from __future__ import annotations

import json
import shutil
import subprocess
from functools import cache

import pytest
from site_testkit import OVERLAY

from docwiki.contracts.markdown import BACKLINKS_END, BACKLINKS_START, strip_backlinks_block

TEXT_MODULE = OVERLAY / "quartz" / "plugins" / "transformers" / "docwiki-text.ts"

BACKLINK_CASES = [
    "no block at all\n",
    f"# T\n\nBody.\n\n{BACKLINKS_START}\n## Referenced by\n\n- [A](a.md)\n\n{BACKLINKS_END}\n\n"
    "## Sources\n\n[^c1]: x\n",
    f"a\n{BACKLINKS_START}\nfirst\n{BACKLINKS_END}\nb\n{BACKLINKS_START}\nsecond\n{BACKLINKS_END}\n",
    f"unterminated {BACKLINKS_START}\nstays\n",
    f"crlf{BACKLINKS_START}\r\nx\r\n{BACKLINKS_END}\r\n",
]


@cache
def _node() -> tuple[str, ...] | None:
    """Node command able to import the ``.ts`` module (type stripping), or ``None``."""
    node = shutil.which("node")
    if node is None:
        return None
    probe = f"await import({json.dumps(TEXT_MODULE.as_uri())})"
    for flags in ((), ("--experimental-strip-types",)):
        command = (node, *flags, "--no-warnings", "--input-type=module")
        completed = subprocess.run(
            [*command, "-e", probe], capture_output=True, text=True, check=False
        )
        if completed.returncode == 0:
            return command
    return None


def run_helpers(script: str) -> object:
    command = _node()
    if command is None:
        pytest.skip("Node 22.6+ (type stripping) is not available")
    program = f"const m = await import({json.dumps(TEXT_MODULE.as_uri())});\n{script}"
    completed = subprocess.run(
        [*command, "-e", program],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_strip_backlinks_block_matches_the_python_contract() -> None:
    cases = json.dumps(BACKLINK_CASES)
    result = run_helpers(
        f"console.log(JSON.stringify({cases}.map((text) => m.stripBacklinksBlock(text))))"
    )
    assert result == [strip_backlinks_block(case) for case in BACKLINK_CASES]


def test_footnote_and_sidecar_badges() -> None:
    result = run_helpers(
        """console.log(JSON.stringify([
          m.splitTrailingBadge(" · ✓ quote verified"),
          m.splitTrailingBadge(" · table "),
          m.splitTrailingBadge(" · generated description"),
          m.splitTrailingBadge(" · OCR"),
          m.splitTrailingBadge(" · paraphrase"),
          m.splitTrailingBadge(" · a table of contents"),
          m.splitTrailingBadge("plain text"),
          m.splitProvenanceBadge(" · Provenance: ✓ quote verified (native text)"),
          m.splitProvenanceBadge("Provenance: unknown"),
        ].map((split) => split ? [split.before, split.badge.kind, split.after] : null)))"""
    )
    assert result == [
        [" · ", "verified", ""],
        [" · ", "table", " "],
        [" · ", "generated", ""],
        [" · ", "ocr", ""],
        [" · ", "paraphrase", ""],
        None,
        None,
        [" · Provenance: ", "verified", " (native text)"],
        None,
    ]


def test_notices_document_links_and_dates() -> None:
    result = run_helpers(
        """console.log(JSON.stringify({
          notices: [
            "FICTIONAL - NOT FOR OPERATIONAL USE.",
            "Superseded by Gearbox oil change SOP rev B.",
            "Warning: this answer cites a withdrawn source.",
            "Fictional characters appear here.",
          ].map(m.noticeKind),
          documents: ["../evidence/src-1/original.pdf#page=3", "original.XLSX", "../a", "x.png"]
            .map(m.isDocumentHref),
          days: ["2026-02-15", "2026-2-15", 20260215, null].map(m.isIsoDay),
          provenance: Object.keys(m.PROVENANCE_BADGES).sort(),
        }))"""
    )
    assert result == {
        "notices": ["fictional", "superseded", "warning", None],
        "documents": [True, True, False, False],
        "days": [True, False, False, False],
        "provenance": ["deterministic-table", "model-description", "native-text", "ocr"],
    }
