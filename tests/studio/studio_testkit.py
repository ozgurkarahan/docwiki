"""Studio test kit: folder storage seeded like a deployed environment, and a fake agent client.

Used by the Studio tests and by the local preview (``python tests/studio/studio_preview.py``),
which serves the Studio on seeded data with canned agent answers (no Azure needed).
"""

from __future__ import annotations

import asyncio
import inspect
import shutil
import sys
import uuid
from pathlib import Path
from typing import Any

MCP_TESTS = Path(__file__).resolve().parents[1] / "mcp"
if str(MCP_TESTS) not in sys.path:
    sys.path.insert(0, str(MCP_TESTS))

from mcp_testkit import FIXTURE_ROOT, RELEASE_ID, seed_work  # noqa: E402

from docwiki.agents_client.citations import parse_answer  # noqa: E402
from docwiki.agents_client.client import (  # noqa: E402
    AgentAnswer,
    AgentUsage,
    ApprovalDecision,
    ApprovalRequest,
    ToolCall,
)
from docwiki.contracts.storage import FolderStorage  # noqa: E402

__all__ = [
    "DONE_PATH",
    "NEW_PATH",
    "OWNER",
    "RAW_FILES",
    "RELEASE_ID",
    "RESEARCHER_TEXT",
    "WIKI_URL",
    "FakeAgentClient",
    "seed_storage",
]

WIKI_URL = "https://wiki.example.org"
OWNER = str(uuid.UUID(int=0xA11C))
"""Object ID of the signed-in owner in the tests (the allowed principal)."""
DONE_PATH = "procedures/SOP-GBX-010 rev B.docx"
NEW_PATH = "uploads/fresh-note.md"

RAW_FILES: dict[str, bytes] = {
    DONE_PATH: b"PK\x03\x04 docx",
    "procedures/broken-scan.pdf": b"%PDF-1.7 broken scan",
    "records/odd-export.csv": b"a;b\n1;2\n",
    "records/new-plan.xlsx": b"PK\x03\x04 xlsx",
    NEW_PATH: b"# Fresh note\n\nYaw brake pads were replaced on WTG-07.\n",
}
"""``raw/`` files: done (in the release), failed, quarantined, pending, and new (no state)."""

RESEARCHER_TEXT = (
    "Revision B of the gearbox oil change SOP is the current procedure [1]. Revision A is "
    "superseded and must not be used for new work [2].\n\n"
    "Sources:\n"
    "[1] Gearbox oil change SOP rev B — ¶ 4 (native-text) — "
    "evidence/src-4d9c65e05302/para-0004.md\n"
    "[2] Gearbox oil change SOP rev A — p. 1 (native-text) — evidence/src-f2750f41f3fa/p0001.md\n"
)


def seed_storage(root: Path) -> FolderStorage:
    """Mock release served, five source states, two run reports and the ``raw/`` files."""
    root.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        FIXTURE_ROOT / "releases",
        root / "releases",
        ignore=shutil.ignore_patterns("__pycache__"),
        dirs_exist_ok=True,
    )
    storage = FolderStorage(root, fsync=False)
    seed_work(storage)
    for path, data in RAW_FILES.items():
        storage.write_bytes(f"raw/{path}", data)
    return storage


class FakeAgentClient:
    """Canned answers: the Researcher cites two sources; the Librarian asks to approve one
    ``ingest_start`` call and reports what happened."""

    def __init__(self, *, delay_s: float = 0.0, fail: Exception | None = None) -> None:
        self.delay_s = delay_s
        self.fail = fail
        self.calls: list[tuple[str, str]] = []
        self.closed = False

    async def ask(
        self,
        question: str,
        *,
        agent: str = "researcher",
        approve: Any = None,
        conversation_id: str | None = None,
        version: str | None = None,
    ) -> AgentAnswer:
        self.calls.append((agent, question))
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        if self.fail is not None:
            raise self.fail
        if agent == "librarian":
            return await self._librarian(approve)
        return AgentAnswer(
            text=RESEARCHER_TEXT,
            sources=parse_answer(RESEARCHER_TEXT),
            tool_calls=[
                ToolCall(
                    name="search",
                    arguments={"query": question},
                    status="completed",
                    server_label="docwiki",
                ),
                ToolCall(
                    name="get_evidence",
                    arguments={"path": "evidence/src-4d9c65e05302/para-0004.md"},
                    status="completed",
                    server_label="docwiki",
                ),
            ],
            usage=AgentUsage(input_tokens=5200, output_tokens=410, total_tokens=5610, responses=1),
            agent="docwiki-researcher",
            version="3",
            latency_s=2.4,
        )

    async def _librarian(self, approve: Any) -> AgentAnswer:
        request = ApprovalRequest(
            id="mcpr_test_0001",
            agent="docwiki-librarian",
            server_label="docwiki",
            name="ingest_start",
            arguments={"prefix": "uploads/", "reason": "a new document was uploaded"},
        )
        approved = False
        if approve is not None:
            decision = approve(request)
            approved = bool(await decision if inspect.isawaitable(decision) else decision)
        calls = [ToolCall(name="run_status", status="completed", server_label="docwiki")]
        calls.append(
            ToolCall(
                name="ingest_start",
                arguments=request.arguments,
                status="completed" if approved else "denied",
                server_label="docwiki",
            )
        )
        text = (
            "I queued an ingest run for uploads/; the ingest job picks it up within a minute."
            if approved
            else "I did not start the ingest run: the request was denied."
        )
        return AgentAnswer(
            text=text,
            tool_calls=calls,
            approvals=[
                ApprovalDecision(
                    id=request.id,
                    name=request.name,
                    arguments=request.arguments,
                    approved=approved,
                )
            ],
            agent="docwiki-librarian",
            version="2",
            latency_s=1.1,
        )

    async def latest_version(self, agent: str) -> tuple[str, str | None]:
        if self.fail is not None:
            raise self.fail
        return "3", None

    async def aclose(self) -> None:
        self.closed = True
