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
    "BROKEN_PATH",
    "DONE_PATH",
    "GONE_PATH",
    "NEW_PATH",
    "NOT_FOUND_TEXT",
    "ODD_PATH",
    "OWNER",
    "PENDING_PATH",
    "RAW_FILES",
    "RELEASE_ID",
    "RESEARCHER_TEXT",
    "WIKI_URL",
    "WINDOWS_TEXT",
    "FakeAgentClient",
    "seed_storage",
]

WIKI_URL = "https://wiki.example.org"
OWNER = str(uuid.UUID(int=0xA11C))
"""Object ID of the signed-in owner in the tests (the allowed principal)."""
NEW_PATH = "uploads/fresh-note.md"

RAW_FILES: dict[str, bytes] = {
    DONE_PATH: b"PK\x03\x04 docx",
    BROKEN_PATH: b"%PDF-1.7 broken scan",
    ODD_PATH: b"a;b\n1;2\n",
    PENDING_PATH: b"PK\x03\x04 xlsx",
    NEW_PATH: b"# Fresh note\n\nThe bay window F1 was installed on 2026-04-21.\n",
}
"""``raw/`` files: done (in the release), failed, quarantined, pending, and new (no state)."""

RESEARCHER_TEXT = (
    "The windows of the extension are delivered on 2026-04-20, as the site meeting minutes "
    "record [1]. Indice A of the schedule showed 2026-03-30; it is superseded and must not be "
    "used for new work [2].\n\n"
    "Sources:\n"
    "[1] Site meeting minutes n°3 — ¶ 11 (native-text) — "
    "evidence/src-165f1d3a109c/para-0011.md\n"
    "[2] Planning and purchase tracking, indice A — p. 1 (native-text) — "
    "evidence/src-c6436ec50050/p0001.md\n"
)

WINDOWS_TEXT = (
    "The windows of the extension are delivered on 2026-04-20: the site meeting minutes record "
    "the postponement announced by VanArsdel Menuiseries from 2026-03-30 [1]. The revised "
    "schedule plans their installation from 2026-04-21 to 2026-04-23 [2]. The windows arrive "
    "69 days after the contract was signed [1].\n\n"
    "Sources:\n"
    "[1] Site meeting minutes n°3 — ¶ 11 (native-text) — "
    "evidence/src-165f1d3a109c/para-0011.md\n"
    '[2] Planning and purchase tracking, indice B — sheet "Planning", rows 6–9 '
    "(deterministic-table) — evidence/src-86eabe3d6d0d/sheet-planning-r0006-r0009.md\n"
)
"""Cites two sidecars of the seeded release; its last sentence states a computed delay (from the
signature of the contract) that the cited minutes do not contain, so filing it shows a number
warning."""

NOT_FOUND_TEXT = (
    "Not found in the wiki. I searched for the energy-performance (DPE) rating of the house and "
    "read the contract page; no source of this release gives one."
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
    """Canned answers: the Researcher cites two sources (``researcher_text``); the Librarian asks
    to approve one ``ingest_start`` call and reports what happened."""

    def __init__(
        self,
        *,
        delay_s: float = 0.0,
        fail: Exception | None = None,
        researcher_text: str = RESEARCHER_TEXT,
    ) -> None:
        self.delay_s = delay_s
        self.fail = fail
        self.researcher_text = researcher_text
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
            text=self.researcher_text,
            sources=parse_answer(self.researcher_text),
            tool_calls=[
                ToolCall(
                    name="search",
                    arguments={"query": question},
                    status="completed",
                    server_label="docwiki",
                ),
                ToolCall(
                    name="get_evidence",
                    arguments={"path": "evidence/src-165f1d3a109c/para-0011.md"},
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
