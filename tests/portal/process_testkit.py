"""Folder storage seeded like a deployed environment, for the process view and the uploads."""

from __future__ import annotations

import json
import shutil
import sys
import uuid
from pathlib import Path

MCP_TESTS = Path(__file__).resolve().parents[1] / "mcp"
if str(MCP_TESTS) not in sys.path:
    sys.path.insert(0, str(MCP_TESTS))

from mcp_testkit import (  # noqa: E402
    BROKEN_PATH,
    DONE_PATH,
    FIXTURE_ROOT,
    GONE_PATH,
    ODD_PATH,
    RELEASE_ID,
    seed_work,
)
from mcp_testkit import NEW_PATH as PENDING_PATH  # noqa: E402

from docwiki.contracts.storage import FolderStorage  # noqa: E402

__all__ = [
    "BROKEN_PATH",
    "DONE_PATH",
    "GONE_PATH",
    "NEW_PATH",
    "ODD_PATH",
    "OWNER",
    "PENDING_PATH",
    "RAW_FILES",
    "RELEASE_ID",
    "seed_storage",
]

OWNER = str(uuid.UUID(int=0xA11C))
"""Object ID of the signed-in owner in the tests."""
NEW_PATH = "uploads/fresh-note.md"

RAW_FILES: dict[str, bytes] = {
    DONE_PATH: b"PK\x03\x04 docx",
    BROKEN_PATH: b"%PDF-1.7 broken scan",
    ODD_PATH: b"a;b\n1;2\n",
    PENDING_PATH: b"PK\x03\x04 xlsx",
    NEW_PATH: b"# Fresh note\n",
}
"""``raw/`` files: done, failed, quarantined, pending, and new (no state). The deleted one has a
state only."""


def seed_storage(root: Path, *, sensitivity: str = "internal") -> FolderStorage:
    """Mock public release served, five source states, two run reports and the ``raw/`` files.

    The seeded states are ``internal``, above the public release: ``sensitivity`` rewrites
    the sensitivity of all of them (use ``public`` to see them as a visitor)."""
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        FIXTURE_ROOT / "releases",
        root / "releases",
        ignore=shutil.ignore_patterns("__pycache__"),
        dirs_exist_ok=True,
    )
    storage = FolderStorage(root, fsync=False)
    seed_work(storage)
    for key in storage.list("work/state/sources/"):
        state = json.loads(storage.read_bytes(key))
        state["sensitivity"] = sensitivity
        storage.write_bytes(key, json.dumps(state).encode("utf-8"))
    for path, data in RAW_FILES.items():
        storage.write_bytes(f"raw/{path}", data)
    return storage
