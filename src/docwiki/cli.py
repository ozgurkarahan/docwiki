"""DocWiki command-line interface (pipeline §8).

Settings come from ``DOCWIKI_*`` environment variables and an optional local ``.env`` file
(never committed; existing environment variables win). Command options override both.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib
import json
import sys
from pathlib import Path
from typing import Annotated, Any

import typer

from docwiki import __version__

app = typer.Typer(add_completion=False, help="DocWiki: compile documents into an agent-ready wiki.")
release_app = typer.Typer(add_completion=False, help="Manage published releases.")
export_app = typer.Typer(add_completion=False, help="Export a release to other tools.")
app.add_typer(release_app, name="release")
app.add_typer(export_app, name="export")

EXIT_FAILED = 1
EXIT_UNAVAILABLE = 2
EXIT_BUSY = 3


@app.callback()
def main(
    env_file: Annotated[
        Path,
        typer.Option("--env-file", help="Local settings file (KEY=VALUE, never committed)."),
    ] = Path(".env"),
) -> None:
    """DocWiki command group."""
    from docwiki.orchestration.settings import load_dotenv

    _never_fail_on_output_encoding()
    load_dotenv(env_file)


def _never_fail_on_output_encoding() -> None:
    """Answers contain characters such as ``−``, ``°`` or ``✓``: a stream that cannot encode them
    (a Windows pipe in the ANSI code page) prints a replacement character instead of crashing."""
    for stream in (sys.stdout, sys.stderr):
        encoding = (getattr(stream, "encoding", None) or "").lower().replace("-", "")
        if encoding != "utf8" and hasattr(stream, "reconfigure"):
            with contextlib.suppress(ValueError, OSError):
                stream.reconfigure(errors="replace")


@app.command()
def version() -> None:
    """Print the DocWiki version."""
    typer.echo(__version__)


def _fail(message: str, code: int = EXIT_FAILED) -> typer.Exit:
    typer.echo(f"error: {message}", err=True)
    return typer.Exit(code)


def _settings(**overrides: Any) -> Any:
    from docwiki.orchestration.settings import EngineSettings, SettingsError

    try:
        return EngineSettings.from_env(**overrides)
    except SettingsError as exc:
        raise _fail(str(exc)) from exc


def _print_outcome(outcome: Any) -> None:
    report = outcome.report
    counts = report.counts
    typer.echo(f"run {outcome.run_id}: {outcome.status}")
    typer.echo(
        f"  sources: {counts.sources_total} total, {counts.new} new, {counts.changed} changed, "
        f"{counts.deleted} deleted, {counts.unchanged} unchanged, {counts.quarantined} quarantined"
    )
    if outcome.release_id:
        state = "published" if outcome.published else "not published"
        typer.echo(f"  release: {outcome.release_id} ({state})")
    if outcome.staged_root:
        typer.echo(f"  staged release kept for inspection: {outcome.staged_root}")
    for gate in outcome.gates:
        if gate.status in ("fail", "warn"):
            typer.echo(
                f"  gate {gate.gate} {gate.name}: {gate.status} ({gate.violations} findings)"
            )
    calls = sum(item.calls for item in report.cost.llm)
    typer.echo(f"  model calls: {calls}; estimated cost: {report.cost.total_cost} USD")
    for error in outcome.errors[:10]:
        typer.echo(f"  error: {error}")


def _worker(kind: str, requested_by: str, settings: Any, *, request: Any = None) -> int:
    from docwiki.orchestration.telemetry import configure_exporter, console_logs, flush_exporter

    console_logs()
    exporting = configure_exporter()
    try:
        return _work(kind, requested_by, settings, request=request)
    finally:
        if exporting:
            flush_exporter()


def _work(kind: str, requested_by: str, settings: Any, *, request: Any = None) -> int:
    from docwiki.orchestration.context import open_queue, open_run_context, open_storage
    from docwiki.orchestration.runner import run_worker

    storage = open_storage(settings)
    queue = None if request is not None else open_queue(settings, storage)
    result = asyncio.run(
        run_worker(
            lambda lease_ok: open_run_context(settings, lease_ok=lease_ok, storage=storage),
            storage=storage,
            settings=settings,
            queue=queue,
            kind=kind,  # type: ignore[arg-type]
            requested_by=requested_by,  # type: ignore[arg-type]
            base_request=request,
            max_cycles=1 if request is not None else None,
        )
    )
    if result.status == "lease-held":
        typer.echo("another execution holds the run lease; nothing to do here")
        return 0 if request is None else EXIT_BUSY
    for outcome in result.outcomes:
        _print_outcome(outcome)
    for error in result.errors:
        typer.echo(f"error: {error}", err=True)
    if queue is not None:
        typer.echo(
            f"messages: {result.deleted} acknowledged, {result.kept} kept for retry, "
            f"{result.poisoned + result.invalid} moved to the poison queue"
        )
    if result.status == "completed":
        return 0
    # A queue worker whose run failed deterministically acknowledged its messages: exiting 0
    # keeps Container Apps from retrying the replica, which would fail the same way.
    return 0 if request is None and not result.retry else EXIT_FAILED


@app.command()
def run(
    input_dir: Annotated[
        str | None,
        typer.Option("--input", help="Input folder (local mode) or raw container (azure mode)."),
    ] = None,
    work_dir: Annotated[Path | None, typer.Option("--work-dir", help="Work folder.")] = None,
    mode: Annotated[str | None, typer.Option("--mode", help="local or azure.")] = None,
    audience: Annotated[
        str | None, typer.Option("--audience", help="public, internal or restricted.")
    ] = None,
    domain: Annotated[
        str | None, typer.Option("--domain", help="Domain pack name or folder.")
    ] = None,
    site: Annotated[
        bool | None,
        typer.Option(
            "--site/--no-site",
            help="Build the Quartz site into the release (default: DOCWIKI_SITE_BUILD, "
            "on in azure mode).",
        ),
    ] = None,
    limit: Annotated[int | None, typer.Option("--limit", help="Only the first N sources.")] = None,
    only: Annotated[
        list[str] | None, typer.Option("--only", help="Only these source ids (repeatable).")
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Build a new release even if nothing changed.")
    ] = False,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Build and verify without publishing.")
    ] = False,
) -> None:
    """Compile the input documents and publish a release (direct call, no queue)."""
    from docwiki.orchestration.pipeline import RunRequest

    settings = _settings(mode=mode, work_dir=work_dir, audience=audience, domain=domain)
    if input_dir is not None:
        if settings.mode == "azure":
            settings = settings.with_overrides(raw_container=input_dir)
        else:
            folder = Path(input_dir)
            if not folder.is_dir():
                raise _fail(f"input folder not found: {input_dir}")
            settings = settings.with_overrides(input_dir=folder)
    settings = settings.with_overrides(debounce_s=0.0)
    request = RunRequest(
        kind="rebuild" if force else "ingest",
        requested_by="cli",
        only=tuple(only or ()),
        limit=limit,
        site=site,
        force=force,
        publish=not dry_run,
    )
    raise typer.Exit(_worker(request.kind, "cli", settings, request=request))


@app.command()
def worker() -> None:
    """Queue worker (ACA Job entrypoint): lease, drain the queue, run, acknowledge, exit."""
    raise typer.Exit(_worker("ingest", "event", _settings()))


@app.command()
def reconcile() -> None:
    """Scheduled safety net: the worker algorithm with kind=reconcile."""
    raise typer.Exit(_worker("reconcile", "schedule", _settings()))


@app.command()
def status(
    run_id: Annotated[str | None, typer.Option("--run", help="Show one run report.")] = None,
    work_dir: Annotated[Path | None, typer.Option("--work-dir", help="Work folder.")] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print JSON.")] = False,
) -> None:
    """Show the current release and the latest run reports."""
    from docwiki.contracts.layout import StorageKeys, run_report_key
    from docwiki.contracts.runs import RunReport
    from docwiki.contracts.storage import KeyNotFoundError
    from docwiki.orchestration.context import open_storage
    from docwiki.release.publish import read_current_pointer

    settings = _settings(work_dir=work_dir)
    storage = open_storage(settings)
    if run_id:
        try:
            report = RunReport.from_json(storage.read_bytes(run_report_key(run_id)))
        except (KeyNotFoundError, ValueError) as exc:
            raise _fail(f"no run report for {run_id}") from exc
        typer.echo(report.to_json())
        return
    pointer = read_current_pointer(storage)
    keys = sorted(
        key for key in storage.list(StorageKeys.RUNS_DIR + "/") if key.endswith("/report.json")
    )
    reports = [RunReport.from_json(storage.read_bytes(key)) for key in keys[-10:]]
    if as_json:
        payload = {
            "current": pointer[0].to_json_dict() if pointer else None,
            "runs": [
                {
                    "run_id": item.run_id,
                    "status": item.status,
                    "kind": item.kind,
                    "release_id": item.release_id,
                    "started_at": item.started_at.isoformat(),
                }
                for item in reports
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
        return
    if pointer:
        typer.echo(f"current release: {pointer[0].release_id} ({pointer[0].audience})")
    else:
        typer.echo("no release published yet")
    for item in reversed(reports):
        typer.echo(
            f"{item.run_id}  {item.status:<9} {item.kind:<9} "
            f"release={item.release_id or '-'} errors={len(item.errors)}"
        )


def _release_root(release: str, settings: Any) -> Path:
    """Local folder of a release: a path, ``current`` or a release id (downloaded if remote)."""
    from docwiki.contracts.layout import StorageKeys
    from docwiki.orchestration.context import open_storage, scratch_dir
    from docwiki.release.publish import materialize_release, read_current_pointer
    from docwiki.storage.routed import local_path_for

    candidate = Path(release)
    if release != "current" and candidate.is_dir():
        return candidate
    storage = open_storage(settings)
    release_id = release
    if release == "current":
        pointer = read_current_pointer(storage)
        if pointer is None:
            raise _fail("no release has been published yet")
        release_id = pointer[0].release_id
    manifest_key = f"{StorageKeys.RELEASES}/{release_id}/manifest.json"
    local = local_path_for(storage, manifest_key)
    if local is not None:
        if not local.is_file():
            raise _fail(f"release {release_id} not found")
        return local.parent
    return materialize_release(storage, release_id, scratch_dir(settings) / "releases")


@app.command()
def lint(
    release: Annotated[
        str, typer.Option("--release", help="current, a release id or a release folder.")
    ] = "current",
    work_dir: Annotated[Path | None, typer.Option("--work-dir", help="Work folder.")] = None,
) -> None:
    """Validate a release against the wiki contract and the quality gates."""
    from docwiki.orchestration.settings import SettingsError, resolve_pack_path
    from docwiki.release.validate import validate_release
    from docwiki.stages.verify import load_canaries

    settings = _settings(work_dir=work_dir)
    root = _release_root(release, settings)
    canaries = list(settings.canaries)
    if settings.domain:
        with contextlib.suppress(SettingsError):
            canaries += load_canaries(resolve_pack_path(settings.domain), env={})
    violations = validate_release(root, canaries=canaries)
    for violation in violations:
        where = f"{violation.path}:{violation.line}" if violation.line else violation.path or "-"
        typer.echo(
            f"{violation.gate} {violation.severity} {violation.code} {where}: {violation.message}"
        )
    errors = sum(1 for violation in violations if violation.severity == "error")
    typer.echo(f"{root.name}: {errors} errors, {len(violations) - errors} warnings")
    raise typer.Exit(EXIT_FAILED if errors else 0)


@app.command()
def site(
    release: Annotated[
        str, typer.Option("--release", help="current, a release id or a release folder.")
    ] = "current",
    out: Annotated[
        Path | None,
        typer.Option("--out", help="Output folder (default: <work dir>/.scratch/site/<release>)."),
    ] = None,
    work_dir: Annotated[Path | None, typer.Option("--work-dir", help="Work folder.")] = None,
) -> None:
    """Build the Quartz site of a release into a folder (needs the site lane, Node and git)."""
    from docwiki.orchestration.context import scratch_dir
    from docwiki.stages.sitehook import build_site_for_release

    settings = _settings(work_dir=work_dir)
    root = _release_root(release, settings)
    target = out or scratch_dir(settings) / "site" / root.name
    result = build_site_for_release(root, out_dir=target, base_url=settings.site_base_url)
    typer.echo(f"site: {result.status}: {result.message}")
    if result.status == "built":
        typer.echo(f"site folder: {result.path or target}")
    if result.status == "skipped":
        raise typer.Exit(EXIT_UNAVAILABLE)
    raise typer.Exit(0 if result.status == "built" else EXIT_FAILED)


def _delegate(module: str, attribute: str) -> Any:
    try:
        return getattr(importlib.import_module(module), attribute)
    except (ImportError, AttributeError) as exc:
        raise _fail(
            f"{module}.{attribute} is not installed in this build", EXIT_UNAVAILABLE
        ) from exc


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def serve(
    ctx: typer.Context,
    stdio: Annotated[bool, typer.Option("--stdio", help="Serve MCP over stdio.")] = False,
    http: Annotated[
        str | None, typer.Option("--http", help="Serve MCP over HTTP, e.g. :8080.")
    ] = None,
    release: Annotated[
        str | None, typer.Option("--release", help="Release folder or releases root.")
    ] = None,
) -> None:
    """Run the DocWiki MCP server (delegates to docwiki.mcp.server.main)."""
    main_fn = _delegate("docwiki.mcp.server", "main")
    argv: list[str] = []
    if stdio:
        argv.append("--stdio")
    if http:
        argv += ["--http", http]
    if release:
        argv += ["--release", release]
    argv += list(ctx.args)
    raise typer.Exit(int(main_fn(argv) or 0))


@app.command()
def ask(
    question: Annotated[str, typer.Argument(help="The question to ask.")],
    agent: Annotated[
        str, typer.Option("--agent", help="researcher, librarian or an agent name.")
    ] = "researcher",
    conversation: Annotated[
        str | None, typer.Option("--conversation", help="Continue this conversation id.")
    ] = None,
    version: Annotated[
        str | None, typer.Option("--version", help="Pin an agent version (default: latest).")
    ] = None,
    approve: Annotated[
        str | None,
        typer.Option(
            "--approve",
            help="Approval of MCP calls: prompt or deny (default: prompt in a terminal, "
            "deny otherwise).",
        ),
    ] = None,
    as_json: Annotated[bool, typer.Option("--json", help="Print the full answer as JSON.")] = False,
) -> None:
    """Ask a deployed Foundry agent (docwiki.agents_client): answer, sources and a receipt."""
    if approve not in (None, "prompt", "deny"):
        raise _fail("--approve must be prompt or deny")
    ask_fn = _delegate("docwiki.agents_client", "ask")
    format_answer = _delegate("docwiki.agents_client", "format_answer")
    prompt_approval = _delegate("docwiki.agents_client", "prompt_approval")
    client_error = _delegate("docwiki.agents_client", "AgentsClientError")
    interactive = approve == "prompt" or (approve is None and sys.stdin.isatty())
    try:
        answer = asyncio.run(
            ask_fn(
                question,
                agent=agent,
                conversation_id=conversation,
                approve=prompt_approval if interactive else None,
                version=version,
            )
        )
    except client_error as exc:
        raise _fail(str(exc)) from exc
    typer.echo(answer.model_dump_json(indent=2) if as_json else format_answer(answer))


@export_app.command("obsidian")
def export_obsidian_command(
    out: Annotated[Path, typer.Option("--out", help="Vault folder to write.")],
    release: Annotated[
        str, typer.Option("--release", help="current, a release id or a release folder.")
    ] = "current",
    work_dir: Annotated[Path | None, typer.Option("--work-dir", help="Work folder.")] = None,
) -> None:
    """Copy a release into an Obsidian vault with [[wikilinks]]."""
    from docwiki.orchestration.export import export_obsidian

    settings = _settings(work_dir=work_dir)
    root = _release_root(release, settings)
    result = export_obsidian(root, out)
    typer.echo(f"exported {result.files} files ({result.links} links rewritten) to {result.vault}")


@release_app.command("list")
def release_list(
    work_dir: Annotated[Path | None, typer.Option("--work-dir", help="Work folder.")] = None,
) -> None:
    """List the releases in storage (newest last)."""
    from docwiki.orchestration.context import open_storage
    from docwiki.release.publish import list_release_ids, read_current_pointer

    storage = open_storage(_settings(work_dir=work_dir))
    pointer = read_current_pointer(storage)
    current = pointer[0].release_id if pointer else None
    for release_id in list_release_ids(storage):
        typer.echo(f"{release_id}{'  (current)' if release_id == current else ''}")


@release_app.command("rollback")
def release_rollback(
    release_id: Annotated[str, typer.Argument(help="Release id to make current again.")],
    work_dir: Annotated[Path | None, typer.Option("--work-dir", help="Work folder.")] = None,
) -> None:
    """Point releases/current.json at an earlier release (If-Match guarded)."""
    from docwiki.contracts.storage import KeyNotFoundError
    from docwiki.orchestration.context import open_storage
    from docwiki.release.publish import PointerConflictError, rollback

    storage = open_storage(_settings(work_dir=work_dir))
    try:
        pointer = rollback(storage, release_id)
    except KeyNotFoundError as exc:
        raise _fail(f"release {release_id} not found") from exc
    except PointerConflictError as exc:
        raise _fail(str(exc)) from exc
    typer.echo(f"current release: {pointer.release_id}")


if __name__ == "__main__":
    app()
