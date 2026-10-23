"""``docwiki file-answer``: a reviewed answer goes to the inbox and the next run publishes it."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from docwiki.agents_client import AgentAnswer
from docwiki.answers import INBOX_PREFIX
from docwiki.cli import app
from docwiki.contracts.storage import FolderStorage
from docwiki.release.publish import read_current_pointer

runner = CliRunner()


def invoke(*args: str):  # type: ignore[no-untyped-def]
    return runner.invoke(app, list(args), catch_exceptions=False)


def _current(work: Path) -> Path:
    pointer = read_current_pointer(FolderStorage(work))
    assert pointer is not None
    return work / "releases" / pointer[0].release_id


def test_file_a_saved_answer_then_publish_it(cli_env, tmp_path: Path) -> None:
    work, corpus = cli_env["work"], cli_env["input"]
    assert invoke("run", "--input", str(corpus)).exit_code == 0
    root = _current(work)
    sidecar = next(p for p in sorted((root / "evidence").rglob("*.md")) if p.name != "index.md")
    cited = sidecar.relative_to(root).as_posix()
    saved = tmp_path / "answer.json"
    saved.write_text(
        AgentAnswer(
            text=f"The schedule sets the date [1].\n\nSources:\n[1] Doc — part — {cited}\n",
            agent="docwiki-researcher",
        ).model_dump_json(),
        encoding="utf-8",
    )
    storage = FolderStorage(work)

    dry = invoke("file-answer", "Which delivery date?", "--from-json", str(saved), "--dry-run")
    assert dry.exit_code == 0, dry.output
    assert "page: queries/" in dry.output and "## How this answer was produced" in dry.output
    assert storage.list(INBOX_PREFIX) == []

    refused = runner.invoke(app, ["file-answer", "Which delivery date?", "--from-json", str(saved)])
    assert refused.exit_code == 1 and "--yes" in refused.output

    filed = invoke("file-answer", "Which delivery date?", "--from-json", str(saved), "--yes")
    assert filed.exit_code == 0, filed.output
    assert f"filed: {INBOX_PREFIX}" in filed.output and "docwiki run" in filed.output
    assert len(storage.list(INBOX_PREFIX)) == 1

    published = invoke("run", "--input", str(corpus))
    assert published.exit_code == 0 and "(published)" in published.output, published.output
    assert list((_current(work) / "wiki" / "queries").glob("*-which-delivery-date.md"))
    assert storage.list(INBOX_PREFIX) == []


def test_answers_that_cannot_be_filed_fail_with_a_message(cli_env, tmp_path: Path) -> None:
    assert invoke("run", "--input", str(cli_env["input"])).exit_code == 0
    missing = runner.invoke(
        app, ["file-answer", "Q?", "--from-json", str(tmp_path / "missing.json"), "--yes"]
    )
    assert missing.exit_code == 1 and "cannot read the answer" in missing.output
    uncited = tmp_path / "uncited.json"
    uncited.write_text(AgentAnswer(text="Something.", agent="a").model_dump_json(), "utf-8")
    result = runner.invoke(app, ["file-answer", "Q?", "--from-json", str(uncited), "--yes"])
    assert result.exit_code == 1 and "cannot file this answer" in result.output


MOCK = Path(__file__).resolve().parents[2] / "samples" / "fixtures" / "mock-release"
MOCK_DIR = MOCK / "releases" / "20260401T090000Z-8a41b109"


def test_a_dry_run_on_a_release_folder_or_storage_root_writes_nothing(
    cli_env, tmp_path: Path
) -> None:
    sidecar = "evidence/src-f0757603684a/para-0011.md"
    saved = tmp_path / "answer.json"
    saved.write_text(
        AgentAnswer(
            text=f"They arrive on 2026-04-20 [1].\n\nSources:\n[1] Minutes — ¶ 11 — {sidecar}\n",
            agent="docwiki-researcher",
        ).model_dump_json(),
        encoding="utf-8",
    )
    for folder in (MOCK_DIR, MOCK):  # a release folder, then a storage root (current.json)
        result = invoke(
            "file-answer",
            "When do the windows arrive?",
            "--from-json",
            str(saved),
            "--release",
            str(folder),
            "--dry-run",
        )
        assert result.exit_code == 0, result.output
        assert "page: queries/" in result.output
        assert "(from release 20260401T090000Z-8a41b109)" in result.output
    assert not cli_env["work"].exists()  # no storage was opened
