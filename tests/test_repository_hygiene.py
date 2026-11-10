"""Repository-wide checks that keep merged files clean."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".md", ".py", ".yaml", ".yml", ".toml", ".bicep", ".ts", ".tsx", ".scss", ".txt"}
SKIPPED_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".local", ".azure", "work"}
MARKERS = ("<<<<<<< ", ">>>>>>> ")


def test_no_merge_conflict_markers() -> None:
    offenders: list[str] = []
    for path in ROOT.rglob("*"):
        if path.suffix not in TEXT_SUFFIXES or not path.is_file():
            continue
        relative = path.relative_to(ROOT)
        if SKIPPED_DIRS.intersection(relative.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for number, line in enumerate(text.splitlines(), start=1):
            if line.startswith(MARKERS):
                offenders.append(f"{relative.as_posix()}:{number}")
    assert not offenders, "merge conflict markers: " + ", ".join(offenders)
