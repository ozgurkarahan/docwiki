"""``docwiki`` CLI: run, status, lint, release, export, worker, serve and ask."""

from __future__ import annotations

import json
import shutil
import sys
import types
from pathlib import Path

import pytest
from typer.testing import CliRunner

from docwiki.cli import app
from docwiki.contracts.queue import QueueMessage
from docwiki.contracts.storage import FolderStorage
from docwiki.release.publish import list_release_ids, read_current_pointer
from docwiki.storage.queue import StorageQueue

runner = CliRunner()


def invoke(*args: str) -> object:
    return runner.invoke(app, list(args), catch_exceptions=False)


def test_run_status_lint_and_release_management(cli_env):
    work, corpus = cli_env["work"], cli_env["input"]
    result = invoke("run", "--input", str(corpus))
    assert result.exit_code == 0, result.output
    assert ": succeeded" in result.output and "(published)" in result.output
    storage = FolderStorage(work)
    first = read_current_pointer(storage)[0].release_id

    result = invoke("status")
    assert result.exit_code == 0
    assert f"current release: {first} (internal)" in result.output
    assert "succeeded" in result.output

    result = invoke("lint")
    assert result.exit_code == 0, result.output
    assert "0 errors" in result.output

    result = invoke("run", "--input", str(corpus))
    assert result.exit_code == 0 and ": no-op" in result.output

    result = invoke("run", "--input", str(corpus), "--force")
    assert result.exit_code == 0, result.output
    second = read_current_pointer(storage)[0].release_id
    assert second != first

    result = invoke("release", "list")
    assert f"{second}  (current)" in result.output and first in result.output
    result = invoke("release", "rollback", first)
    assert result.exit_code == 0 and first in result.output
    assert read_current_pointer(storage)[0].release_id == first
    result = runner.invoke(app, ["release", "rollback", "20990101T000000Z-00000000"])
    assert result.exit_code == 1


def test_dry_run_does_not_publish(cli_env):
    result = invoke("run", "--input", str(cli_env["input"]), "--dry-run")
    assert result.exit_code == 0, result.output
    assert "(not published)" in result.output
    assert read_current_pointer(FolderStorage(cli_env["work"])) is None


def test_export_obsidian_rewrites_links(cli_env):
    assert invoke("run", "--input", str(cli_env["input"])).exit_code == 0
    vault = cli_env["root"] / "vault"
    result = invoke("export", "obsidian", "--out", str(vault))
    assert result.exit_code == 0, result.output
    index = (vault / "index.md").read_text(encoding="utf-8")
    assert "[[topics/index|topics]]" in index
    assert "[[sources/index#Procedures|Procedures]]" in index
    page = next((vault / "sources").glob("sop-gbx-010-rev-a.md"))
    text = page.read_text(encoding="utf-8")
    assert "[[evidence/" in text and "](../evidence/" not in text
    assert (vault / "evidence").is_dir()
    assert not (vault / ".agents").exists()


def test_worker_drains_the_local_queue(cli_env):
    work = cli_env["work"]
    shutil.copytree(cli_env["input"], work / "raw")
    storage = FolderStorage(work)
    queue = StorageQueue(storage)
    queue.send(
        QueueMessage(
            kind="ingest",
            requested_by="librarian",
            idempotency_key="cli:worker",
            created_at="2026-02-01T00:00:00Z",
        ).to_body()
    )
    result = invoke("worker")
    assert result.exit_code == 0, result.output
    assert "1 acknowledged" in result.output
    assert queue.pending_count() == 0
    assert read_current_pointer(storage) is not None
    result = invoke("reconcile")
    assert result.exit_code == 0 and ": no-op" in result.output


def test_worker_consumes_messages_of_the_mcp_folder_queue(cli_env):
    from docwiki.mcp.ingest_queue import FolderQueue

    work = cli_env["work"]
    shutil.copytree(cli_env["input"], work / "raw")
    storage = FolderStorage(work)
    receipt = FolderQueue(storage).send(
        QueueMessage(
            kind="ingest",
            requested_by="librarian",
            idempotency_key="mcp:ingest_start:1",
            created_at="2026-02-01T00:00:00Z",
            hints={"reason": "new documents"},
        )
    )
    assert receipt.location.startswith("work/queue/") and not receipt.duplicate
    queue = StorageQueue(storage)
    assert queue.visible_count() == 1
    result = invoke("worker")
    assert result.exit_code == 0, result.output
    assert "1 acknowledged" in result.output
    assert queue.pending_count() == 0 and not storage.exists(receipt.location)
    assert read_current_pointer(storage) is not None


def test_busy_lease_and_invalid_settings(cli_env, monkeypatch):
    storage = FolderStorage(cli_env["work"])
    lease = storage.acquire_lease("work/state/lease", 60)
    result = invoke("run", "--input", str(cli_env["input"]))
    assert result.exit_code == 3 and "another execution holds the run lease" in result.output
    assert invoke("worker").exit_code == 0
    storage.release_lease(lease)
    monkeypatch.setenv("DOCWIKI_AUDIENCE", "everyone")
    result = runner.invoke(app, ["run", "--input", str(cli_env["input"])])
    assert result.exit_code == 1
    result = runner.invoke(app, ["run", "--input", str(cli_env["root"] / "missing")])
    assert result.exit_code == 1


def test_env_file_is_loaded_without_overriding_the_environment(cli_env, monkeypatch):
    import os

    env_file = cli_env["root"] / "local.env"
    env_file.write_text(
        "# local settings\nDOCWIKI_AUDIENCE=public\nexport DOCWIKI_SITE_BASE_URL='https://docs.example.org'\n"
        "DOCWIKI_WORK_DIR=ignored\n",
        encoding="utf-8",
        newline="\n",
    )
    # register both variables with monkeypatch so that its teardown removes them again
    monkeypatch.setenv("DOCWIKI_SITE_BASE_URL", "placeholder")
    monkeypatch.delenv("DOCWIKI_SITE_BASE_URL")
    monkeypatch.delenv("DOCWIKI_AUDIENCE")
    result = invoke("--env-file", str(env_file), "version")
    assert result.exit_code == 0
    assert os.environ["DOCWIKI_AUDIENCE"] == "public"
    assert os.environ["DOCWIKI_SITE_BASE_URL"] == "https://docs.example.org"
    assert os.environ["DOCWIKI_WORK_DIR"] == str(cli_env["work"])


def test_serve_and_ask_delegate_or_report_unavailable(cli_env, monkeypatch):
    monkeypatch.setitem(sys.modules, "docwiki.mcp.server", None)
    result = runner.invoke(app, ["serve", "--stdio"])
    assert result.exit_code == 2
    calls: list[list[str]] = []
    server = types.ModuleType("docwiki.mcp.server")
    server.main = lambda argv=None: calls.append(list(argv or [])) or 0  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "docwiki.mcp.server", server)
    result = runner.invoke(app, ["serve", "--stdio", "--release", "samples/wiki", "--verbose"])
    assert result.exit_code == 0, result.output
    assert calls == [["--stdio", "--release", "samples/wiki", "--verbose"]]

    monkeypatch.setitem(sys.modules, "docwiki.agents_client", None)
    assert runner.invoke(app, ["ask", "Which oil?"]).exit_code == 2
    client = types.ModuleType("docwiki.agents_client")
    asked: list[dict[str, object]] = []

    class AgentsClientError(Exception):
        pass

    class Answer:
        def __init__(self, text: str) -> None:
            self.text = text

        def model_dump_json(self, indent: int | None = None) -> str:
            return json.dumps({"text": self.text}, indent=indent)

    async def ask(question: str, **options: object) -> Answer:
        asked.append({"question": question, **options})
        if question == "boom":
            raise AgentsClientError("agent unavailable")
        return Answer(f"{options['agent']}: {question}\n\n[1] Rev B — ¶ 3")

    async def prompt_approval(request: object) -> bool:
        return True

    client.ask = ask  # type: ignore[attr-defined]
    client.format_answer = lambda answer: answer.text + "\n\n[receipt]"  # type: ignore[attr-defined]
    client.prompt_approval = prompt_approval  # type: ignore[attr-defined]
    client.AgentsClientError = AgentsClientError  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "docwiki.agents_client", client)
    result = runner.invoke(
        app, ["ask", "Which oil?", "--agent", "librarian", "--conversation", "conv-1"]
    )
    assert result.exit_code == 0, result.output
    assert "librarian: Which oil?" in result.output and "[1] Rev B" in result.output
    assert "[receipt]" in result.output
    assert asked[-1] == {
        "question": "Which oil?",
        "agent": "librarian",
        "conversation_id": "conv-1",
        "approve": None,
        "version": None,
    }
    result = runner.invoke(app, ["ask", "Which oil?", "--approve", "prompt", "--json"])
    assert result.exit_code == 0 and json.loads(result.output)["text"].startswith("researcher")
    assert asked[-1]["approve"] is prompt_approval
    failed = runner.invoke(app, ["ask", "boom"])
    assert failed.exit_code == 1 and "agent unavailable" in failed.output
    assert runner.invoke(app, ["ask", "x", "--approve", "always"]).exit_code == 1


def test_site_without_the_site_lane_exits_unavailable(cli_env, monkeypatch):
    assert invoke("run", "--input", str(cli_env["input"])).exit_code == 0
    monkeypatch.setitem(sys.modules, "docwiki.site", None)
    result = runner.invoke(app, ["site"])
    assert result.exit_code == 2 and "skipped" in result.output


@pytest.mark.parametrize("command", [["status"], ["release", "list"]])
def test_commands_work_on_an_empty_installation(cli_env, command):
    result = runner.invoke(app, command)
    assert result.exit_code == 0
    assert list_release_ids(FolderStorage(Path(cli_env["work"]))) == []
