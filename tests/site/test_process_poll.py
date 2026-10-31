"""How often the pipeline page polls ``/api/process`` (scripts/process.inline.ts): its pure pacing
block is run with Node (skipped without it)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from functools import cache
from pathlib import Path

import pytest
from site_testkit import OVERLAY

SCRIPT = OVERLAY / "quartz" / "components" / "docwiki" / "scripts" / "process.inline.ts"
START = "// --- poll pacing (start)"
END = "// --- poll pacing (end)"
NAMES = ("pollDelay", "FAST_MS", "BUSY_SLOW_MS", "SLOW_MS", "UNCHANGED_BEFORE_BACKOFF")


def _pacing() -> str:
    source = SCRIPT.read_text(encoding="utf-8")
    block = source[source.index(START) : source.index(END)]
    assert "document" not in block and "window" not in block  # pure: no DOM
    return block


@cache
def _node() -> str | None:
    return shutil.which("node")


def run(tmp_path: Path, expression: str) -> object:
    node = _node()
    if node is None:
        pytest.skip("Node is not available")
    module = tmp_path / "pacing.ts"
    module.write_text(_pacing() + f"\nexport {{ {', '.join(NAMES)} }}\n", encoding="utf-8")
    program = (
        f"const m = await import({json.dumps(module.as_uri())});\n"
        f"console.log(JSON.stringify({expression}))"
    )
    stderr = ""
    for flags in ((), ("--experimental-strip-types",)):
        completed = subprocess.run(
            [node, *flags, "--no-warnings", "--input-type=module", "-e", program],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if completed.returncode == 0:
            return json.loads(completed.stdout)
        stderr = completed.stderr
        if "Unknown file extension" not in stderr and "bad option" not in stderr:
            break
    if "Unknown file extension" in stderr or "bad option" in stderr:
        pytest.skip("Node 22.6+ (type stripping) is not available")
    raise AssertionError(stderr)


def test_the_poll_backs_off_while_nothing_changes_and_is_slow_when_idle(tmp_path: Path) -> None:
    result = run(
        tmp_path,
        """{
          constants: [m.FAST_MS, m.BUSY_SLOW_MS, m.SLOW_MS, m.UNCHANGED_BEFORE_BACKOFF],
          busy: [0, 1, 2, 3, 4, 10].map((n) => m.pollDelay(true, false, n)),
          idle: [0, 3, 10].map((n) => m.pollDelay(false, false, n)),
          following: [0, 10].map((n) => [m.pollDelay(true, true, n), m.pollDelay(false, true, n)]),
        }""",
    )
    assert isinstance(result, dict)
    assert result["constants"] == [5_000, 15_000, 30_000, 3]
    # 5 s while the replies change, 15 s after three identical busy replies in a row
    assert result["busy"] == [5_000, 5_000, 5_000, 15_000, 15_000, 15_000]
    assert result["idle"] == [30_000, 30_000, 30_000]
    # the owner following an upload or a rebuild stays at 5 s
    assert result["following"] == [[5_000, 5_000], [5_000, 5_000]]


def test_the_poll_resets_on_change_and_pauses_on_a_hidden_tab() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    # a changed reply starts the count again (fast), an identical one adds to it
    assert "unchanged = reply === lastReply ? unchanged + 1 : 0" in source
    assert "schedule(pollDelay(busy(view), Date.now() < followUntil, unchanged))" in source
    # a hidden tab schedules nothing; showing it polls at once
    assert re.search(r"if \(alive && !document\.hidden\) timer = window\.setTimeout", source)
    assert re.search(
        r"if \(document\.hidden\) window\.clearTimeout\(timer\)\s*else void poll\(\)", source
    )
    assert 'document.addEventListener("visibilitychange", onVisibility)' in source
    assert 'document.removeEventListener("visibilitychange", onVisibility)' in source
