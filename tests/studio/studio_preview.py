"""Local preview of DocWiki Studio on seeded data with canned agent answers (no Azure needed).

    uv run python tests/studio/studio_preview.py [--port 8091] [--delay 3]

Serves http://127.0.0.1:8091/ with the sign-in checks off (loopback only). The seeded storage
lives in a temporary folder: uploads land there, nothing leaves the machine.
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import uvicorn
from studio_testkit import WIKI_URL, FakeAgentClient, seed_storage

from docwiki.studio.app import create_app
from docwiki.studio.config import StudioConfig
from docwiki.studio.jobs import AgentJobs
from docwiki.studio.service import StudioService


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--port", type=int, default=8091)
    parser.add_argument("--delay", type=float, default=3.0, help="seconds per canned answer")
    args = parser.parse_args()
    root = Path(tempfile.mkdtemp(prefix="docwiki-studio-preview-"))
    storage = seed_storage(root)
    config = StudioConfig(wiki_url=WIKI_URL, require_sign_in=False)
    service = StudioService(storage, config, queue_depth=lambda: 1)
    client = FakeAgentClient(delay_s=args.delay)
    jobs = AgentJobs(lambda: client, daily_questions=100, approval_timeout_s=600.0)
    print(f"seeded storage: {root}")
    uvicorn.run(
        create_app(service, jobs, config), host="127.0.0.1", port=args.port, server_header=False
    )


if __name__ == "__main__":
    main()
