"""Evaluation runner (docs/spec/evals.md §3); the command line is ``evals/run.py``.

    uv run python evals/run.py --system baseline-rag --questions evals/golden/dev.jsonl
    uv run python evals/run.py --system docwiki-researcher --questions evals/golden/dev.jsonl \
        --catalog <release folder or catalog.json> --limit 5
    uv run python evals/run.py --system docwiki-researcher --questions <private holdout.jsonl> \
        --split-name holdout --private-out <folder outside the repository>

Writes ``<out>/<UTC date>-<system>-<split>.json`` (``-limit<N>`` appended for partial runs). For
the ``dev`` split the file holds every per-question record (answer, citations, tool calls,
metrics, tokens, cost, latency) next to the aggregates; for any other split it holds aggregates
only, and the per-question details go to ``--private-out`` (outside the repository).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import re
import statistics
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from docwiki import __version__ as docwiki_version
from docwiki.contracts.enums import SENSITIVITIES
from evals import METRICS_VERSION, RESULT_FORMAT
from evals.corpus import (
    SCOPES,
    CorpusContext,
    CorpusManifest,
    ExtractionCache,
    ReleaseCatalog,
    load_corpus,
)
from evals.judge import (
    Judge,
    JudgeUnavailable,
    aggregate_judge,
    judge_tool_calls,
    tool_definitions,
)
from evals.metrics import (
    BINARY_METRICS,
    METRICS,
    aggregate,
    recall_of,
    resolve_citations,
    score_answer,
)
from evals.questions import GoldenQuestion, QuestionSet, QuestionSetError, load_questions
from evals.records import Answer, Citation
from evals.scoreboard import format_metric
from evals.systems import (
    SYSTEMS,
    BaselineLongContextSystem,
    BaselineRagSystem,
    EvalSystem,
    ResearcherSystem,
    SystemNotConfigured,
    SystemSkipped,
)

__all__ = [
    "PUBLIC_SPLIT",
    "RunOptions",
    "build_system",
    "check_private_dir",
    "main",
    "public_view",
    "result_name",
    "run_evaluation",
    "scrub",
    "write_results",
]

REPO_ROOT = Path(__file__).resolve().parents[1]
PUBLIC_SPLIT = "dev"
"""The only split whose per-question records may be written to the repository."""
PRIVATE_FOLDERS = ("evals/holdout", "private", ".local")
"""Git-ignored folders of the repository where private outputs may be written."""
BASELINES = ("baseline-rag", "baseline-long-context")
"""Systems that index the documents of ``--scope`` (the Researcher answers over its release)."""
MAX_CONTEXT_CHARS = 30_000
_SPLIT_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}$")


@dataclass
class RunOptions:
    system: str
    questions: Path
    split: str = PUBLIC_SPLIT
    limit: int | None = None
    corpus: Path = REPO_ROOT / "samples" / "corpus"
    out: Path = REPO_ROOT / "evals" / "results"
    private_out: Path | None = None
    catalog: Path | None = None
    release_id: str | None = None
    cache_dir: Path | None = REPO_ROOT / ".cache" / "evals"
    extract_mode: str = "local"
    audience: str = "public"
    scope: str = "full"
    top_k: int = 8
    chunk_tokens: int = 800
    budget_tokens: int = 120_000
    concurrency: int = 1
    judge: bool = False
    env: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))

    @property
    def public(self) -> bool:
        return self.split == PUBLIC_SPLIT


# ------------------------------------------------------------------------------- privacy


def _inside(path: Path, root: Path) -> str | None:
    """``path`` relative to ``root`` (POSIX), or ``None`` when it is outside."""
    resolved, base = path.resolve(), root.resolve()
    if resolved == base or base in resolved.parents:
        return resolved.relative_to(base).as_posix()
    return None


def check_private_dir(path: Path, repo_root: Path = REPO_ROOT) -> None:
    """Private details may only go outside the repository or to a git-ignored private folder."""
    relative = _inside(path, repo_root)
    if relative is None:
        return
    if any(relative == folder or relative.startswith(folder + "/") for folder in PRIVATE_FOLDERS):
        return
    raise ValueError(
        "--private-out must be outside the repository or in one of its git-ignored private "
        f"folders ({', '.join(folder + '/' for folder in PRIVATE_FOLDERS)})"
    )


def _check_recording(options: RunOptions) -> None:
    """Recording LLM fixtures of a private split inside the repository would publish it."""
    if options.public or (options.env.get("DOCWIKI_LLM_MODE") or "").strip().lower() != "record":
        return
    fixtures = (options.env.get("DOCWIKI_LLM_FIXTURES") or "").strip()
    if not fixtures or _inside(Path(fixtures), REPO_ROOT) is not None:
        raise ValueError(
            "DOCWIKI_LLM_MODE=record with a non-dev split would write private questions into "
            "LLM fixtures: point DOCWIKI_LLM_FIXTURES outside the repository"
        )


def _check_split_labels(options: RunOptions, questions: QuestionSet) -> None:
    """A file whose questions are labelled with another split is never published as ``dev``."""
    if not options.public:
        return
    labels = sorted({question.split for question in questions.questions} - {PUBLIC_SPLIT})
    if labels:
        raise ValueError(
            f"the questions are labelled split={', '.join(labels)}: pass --split-name "
            f"{labels[0]} (per-question details of non-dev splits are never written to --out)"
        )


def _check_documents(options: RunOptions) -> None:
    """The baselines index the documents of the selected scope: none at all is an error, reported
    before any extraction or model call."""
    if options.system in BASELINES:
        CorpusManifest.load(options.corpus).select(options.scope, options.audience)


def _display_path(path: Path) -> str:
    """Repository-relative path, or only the file name (never a machine path)."""
    relative = _inside(path, REPO_ROOT)
    return relative if relative is not None else path.name


def result_name(system: str, split: str, day: str, *, limit: int | None, complete: bool) -> str:
    suffix = f"-limit{limit}" if limit and not complete else ""
    return f"{day}-{system}-{split}{suffix}.json"


def public_view(result: Mapping[str, Any]) -> dict[str, Any]:
    """What may be written to the repository: everything for ``dev``, aggregates otherwise."""
    if result.get("split") == PUBLIC_SPLIT:
        return dict(result)
    view = {
        key: value
        for key, value in result.items()
        if key not in ("questions", "failures", "errors")
    }
    view["privacy"] = (
        "aggregates only: per-question records of non-dev splits are written to --private-out"
    )
    return view


def write_results(
    result: Mapping[str, Any], *, out: Path, name: str, private_out: Path | None
) -> tuple[Path, Path | None]:
    """Write the public file (and the private details for non-dev splits)."""
    out.mkdir(parents=True, exist_ok=True)
    public_path = out / name
    public_path.write_text(_dumps(public_view(result)), encoding="utf-8", newline="\n")
    private_path: Path | None = None
    if private_out is not None and result.get("split") != PUBLIC_SPLIT:
        check_private_dir(private_out)
        private_out.mkdir(parents=True, exist_ok=True)
        private_path = private_out / name
        private_path.write_text(_dumps(dict(result)), encoding="utf-8", newline="\n")
    return public_path, private_path


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


_URL = re.compile(r"https?://[^\s'\"<>)]+")
_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?<![\w.])[A-Za-z]:[\\/][^\s'\"<>]*"), "<path>"),
    (re.compile(r"(?<![\w.])/(?:home|Users|tmp|var|private|mnt|opt)/[^\s'\"<>]*"), "<path>"),
    (
        re.compile(
            r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b"
        ),
        "<id>",
    ),
)


def _url(match: re.Match[str]) -> str:
    value = match[0]
    trailing = value[len(value.rstrip(".,:;")) :]
    return "<url>" + trailing


def scrub(text: str | None, *, limit: int = 300) -> str | None:
    """An error message fit for a committed file: no URL (endpoints), absolute path or GUID."""
    if text is None:
        return None
    text = _URL.sub(_url, text)
    for pattern, replacement in _SCRUB_PATTERNS:
        text = pattern.sub(replacement, text)
    return text[:limit]


# ------------------------------------------------------------------------------ systems


def build_system(options: RunOptions, corpus: CorpusContext) -> EvalSystem:
    """The system under test. The baselines index the documents of ``options.scope`` that the
    audience may see; an empty selection raises ``ValueError``."""
    if options.system == "docwiki-researcher":
        return ResearcherSystem(env=options.env)
    if options.system == "baseline-rag":
        return BaselineRagSystem(
            docs=corpus.docs,
            files=corpus.manifest.select(options.scope, options.audience),
            top_k=options.top_k,
            chunk_tokens=options.chunk_tokens,
        )
    if options.system == "baseline-long-context":
        return BaselineLongContextSystem(
            docs=corpus.docs,
            files=corpus.manifest.select(options.scope, options.audience),
            budget_tokens=options.budget_tokens,
        )
    raise ValueError(f"unknown system {options.system!r}; use one of {', '.join(SYSTEMS)}")


# ------------------------------------------------------------------------------- scoring


@dataclass
class _Outcome:
    question: GoldenQuestion
    answer: Answer
    latency_s: float
    error: str | None


async def _answer_all(
    system: EvalSystem, questions: Sequence[GoldenQuestion], concurrency: int
) -> list[_Outcome]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def one(question: GoldenQuestion) -> _Outcome:
        async with semaphore:
            started = time.perf_counter()
            try:
                answer, error = await system.answer(question), None
            except SystemNotConfigured:
                raise
            except Exception as exc:  # recorded per question; the run goes on
                answer, error = Answer(), scrub(f"{type(exc).__name__}: {exc}")
            return _Outcome(question, answer, round(time.perf_counter() - started, 3), error)

    return list(await asyncio.gather(*(one(question) for question in questions)))


def _retrieved_citations(answer: Answer) -> list[Citation]:
    return [
        Citation(source_path=item["path"], locator_key=key, unit=item.get("id"))
        for item in answer.info.get("retrieved") or []
        for key in item.get("keys") or []
    ]


def _context(answer: Answer, corpus: CorpusContext) -> str:
    """Evidence text of the cited locators (the context of the groundedness judge)."""
    parts: list[str] = []
    seen: set[tuple[str, str]] = set()
    for cited in resolve_citations(answer.citations, corpus):
        if not cited.resolved or cited.path is None or cited.locator_key is None:
            continue
        if (cited.path, cited.locator_key) in seen:
            continue
        seen.add((cited.path, cited.locator_key))
        text = corpus.evidence.text(cited.path, cited.locator_key)
        if text:
            parts.append(f"[{cited.path} — {cited.locator_key}]\n{text}")
    return "\n\n".join(parts)[:MAX_CONTEXT_CHARS]


async def _judge(judge: Judge, outcome: _Outcome, corpus: CorpusContext) -> dict[str, Any]:
    calls = [call.model_dump() for call in outcome.answer.tool_calls]
    return await judge.evaluate(
        query=outcome.question.question,
        response=outcome.answer.body or outcome.answer.text,
        ground_truth=outcome.question.expected_answer,
        context=_context(outcome.answer, corpus),
        tool_calls=judge_tool_calls(calls),
        definitions=tool_definitions([call["name"] for call in calls]),
    )


def _record(
    outcome: _Outcome, corpus: CorpusContext, judged: dict[str, Any] | None
) -> dict[str, Any]:
    question, answer = outcome.question, outcome.answer
    resolved = resolve_citations(answer.citations, corpus)
    score = score_answer(question, answer, corpus, resolved=resolved, error=outcome.error)
    metrics = dict(score.metrics)
    if "retrieved" in answer.info:
        metrics["retrieval_recall"] = recall_of(question, _retrieved_citations(answer), corpus)
    usage = answer.usage
    return {
        "id": question.id,
        "category": question.category,
        "lang": question.lang,
        "abstain": question.abstain,
        "question": question.question,
        "answer": {
            "text": answer.text,
            "abstained": answer.abstained,
            "citations": [citation.model_dump(exclude_none=True) for citation in answer.citations],
        },
        "tool_calls": [
            {**call.model_dump(exclude_none=True), "error": scrub(call.error)}
            if call.error
            else call.model_dump(exclude_none=True)
            for call in answer.tool_calls
        ],
        "metrics": metrics,
        "details": score.details,
        "tokens": {
            "input": usage.input_tokens,
            "output": usage.output_tokens,
            "cached_input": usage.cached_input_tokens,
            "reasoning": usage.reasoning_tokens,
            "total": usage.total_tokens,
            "calls": usage.calls,
        },
        "cost_usd": answer.cost_usd,
        "latency_s": outcome.latency_s,
        "error": outcome.error,
        "judge": judged,
        "info": answer.info,
    }


def _percentile(values: Sequence[float], share: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(share * len(ordered)) - 1)
    return round(ordered[index], 3)


def _latency(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    values = [float(record["latency_s"]) for record in records]
    if not values:
        return {"mean_s": None, "p50_s": None, "p95_s": None, "max_s": None, "total_s": 0.0}
    return {
        "mean_s": round(statistics.fmean(values), 3),
        "p50_s": round(statistics.median(values), 3),
        "p95_s": _percentile(values, 0.95),
        "max_s": round(max(values), 3),
        "total_s": round(sum(values), 3),
    }


def _cost(
    records: Sequence[Mapping[str, Any]],
    receipt: Mapping[str, Any] | None,
    system_versions: Mapping[str, Any],
) -> dict[str, Any]:
    costs = [float(record["cost_usd"]) for record in records if record["cost_usd"] is not None]
    if receipt is not None:
        verified = bool(receipt.get("prices_verified"))
    else:
        verified = bool((system_versions.get("price_table") or {}).get("verified"))
    total = round(sum(costs), 6) if costs else None
    return {
        "currency": "USD",
        "input_tokens": sum(int(record["tokens"]["input"]) for record in records),
        "cached_input_tokens": sum(int(record["tokens"]["cached_input"]) for record in records),
        "output_tokens": sum(int(record["tokens"]["output"]) for record in records),
        "reasoning_tokens": sum(int(record["tokens"]["reasoning"]) for record in records),
        "estimated_cost_usd": total,
        "per_question_usd": round(total / len(costs), 6) if total is not None else None,
        "priced_questions": len(costs),
        "prices_verified": verified,
        "receipt_totals": (receipt or {}).get("totals"),
    }


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip() if done.returncode == 0 else None


def _seal(questions_path: Path, questions: QuestionSet) -> dict[str, Any] | None:
    """Seal check of the public golden set (never reads files next to a private set)."""
    if _inside(questions_path, REPO_ROOT) is None:
        return None
    seal_file = questions_path.parent / "SEAL"
    if not seal_file.is_file():
        return None
    values = dict(
        line.rsplit("=", 1)
        for line in seal_file.read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    expected = values.get(f"{questions_path.name} sha256")
    return {"sealed": values.get("sealed"), "matches": expected == questions.sha256}


def _extractors() -> dict[str, str] | None:
    try:
        from docwiki.extract import extractor_versions
    except ImportError:
        return None
    return extractor_versions()


async def run_evaluation(
    options: RunOptions,
    *,
    questions: QuestionSet,
    corpus: CorpusContext,
    system: EvalSystem | None = None,
    judge: Judge | None = None,
    judge_notice: str | None = None,
    now: datetime | None = None,
    extraction: str | None = None,
) -> dict[str, Any]:
    """Run one system over the questions and build the full result document."""
    started_at = (now or datetime.now(UTC)).astimezone(UTC).replace(microsecond=0)
    clock = time.perf_counter()
    system = system or build_system(options, corpus)
    skipped: dict[str, Any] | None = None
    records: list[dict[str, Any]] = []
    receipt: dict[str, Any] | None = None
    try:
        try:
            await system.setup()
        except SystemSkipped as exc:
            skipped = {"reason": exc.reason, **exc.details}
        if skipped is None:
            outcomes = await _answer_all(system, questions.questions, options.concurrency)
            for outcome in outcomes:
                judged = await _judge(judge, outcome, corpus) if judge else None
                records.append(_record(outcome, corpus, judged))
            receipt = system.receipt()
        system_versions = await system.versions()
        system_config = system.config()
    finally:
        await system.aclose()

    duration = round(time.perf_counter() - clock, 3)
    finished_at = datetime.fromtimestamp(started_at.timestamp() + duration, UTC).replace(
        microsecond=0
    )
    aggregates = aggregate(records) if records else {"overall": None, "by_category": {}}
    judged_items = [record["judge"] for record in records if record.get("judge")]
    catalog = corpus.catalog
    result: dict[str, Any] = {
        "format": RESULT_FORMAT,
        "system": system.name,
        "split": options.split,
        "status": "skipped" if skipped else "ok",
        "skipped": skipped,
        "run": {
            "started_at": started_at.isoformat().replace("+00:00", "Z"),
            "finished_at": finished_at.isoformat().replace("+00:00", "Z"),
            "date": started_at.date().isoformat(),
            "duration_s": duration,
            "questions": 0 if skipped else len(questions.questions),
            "questions_total": questions.total,
            "complete": questions.complete,
            "limit": options.limit,
            "concurrency": options.concurrency,
        },
        "questions_file": {
            "file": _display_path(options.questions),
            "sha256": questions.sha256,
            "questions": questions.total,
            "seal": _seal(options.questions, questions) if options.public else None,
        },
        "config": {
            "system": system_config,
            "audience": options.audience,
            "scope": options.scope if system.name in BASELINES else None,
            "extract_mode": options.extract_mode,
            "catalog": catalog is not None,
            "judge": options.judge,
        },
        "versions": {
            "docwiki": docwiki_version,
            "git_sha": _git("rev-parse", "HEAD"),
            "git_dirty": None
            if (status := _git("status", "--porcelain")) is None
            else bool(status),
            "metrics": METRICS_VERSION,
            "release_id": options.release_id or (catalog.release_id if catalog else None),
            "release_audience": catalog.audience if catalog else None,
            "corpus_manifest_sha256": corpus.manifest.sha256,
            "extraction": extraction,
            "extractors": _extractors(),
            "system": system_versions,
            "judge": judge.versions if judge else None,
        },
        "aggregates": {
            "overall": aggregates.get("overall"),
            "by_category": aggregates.get("by_category"),
        },
        "failures": aggregates.get("failures", {}),
        "errors": aggregates.get("errors", []),
        "cost": _cost(records, receipt, system_versions),
        "latency": _latency(records),
        "judge": {
            "enabled": options.judge,
            "notice": judge_notice,
            "notices": judge.notices if judge else [],
            "summary": aggregate_judge(judged_items) if judged_items else None,
        },
        "questions": records,
    }
    return result


# ---------------------------------------------------------------------------------- cli


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="evals/run.py",
        description="Run a DocWiki evaluation (docs/spec/evals.md).",
    )
    parser.add_argument("--system", required=True, choices=SYSTEMS)
    parser.add_argument("--questions", required=True, type=Path, help="golden set (JSONL)")
    parser.add_argument(
        "--split-name",
        "--split",
        dest="split",
        default=PUBLIC_SPLIT,
        help="split name; anything but 'dev' writes aggregates only to --out",
    )
    parser.add_argument("--limit", type=int, help="evaluate the first N questions only")
    parser.add_argument("--corpus", type=Path, default=REPO_ROOT / "samples" / "corpus")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "evals" / "results")
    parser.add_argument(
        "--private-out",
        type=Path,
        help="folder for per-question details of non-dev splits (outside the repository)",
    )
    parser.add_argument(
        "--catalog",
        type=Path,
        help="catalog.json or release folder of the evaluated release (source id mapping)",
    )
    parser.add_argument("--release-id", help="release id to record when no catalog is given")
    parser.add_argument("--cache-dir", type=Path, default=REPO_ROOT / ".cache" / "evals")
    parser.add_argument("--extract-mode", choices=("local", "azure"), default="local")
    parser.add_argument("--audience", choices=SENSITIVITIES, default="public")
    parser.add_argument(
        "--scope", choices=SCOPES, default="full", help="document scope of the baselines"
    )
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--chunk-tokens", type=int, default=800)
    parser.add_argument("--budget-tokens", type=int, default=120_000)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--judge", action="store_true", help="also run azure-ai-evaluation")
    return parser


def _summary_lines(result: Mapping[str, Any]) -> list[str]:
    run = result["run"]
    head = (
        f"{result['system']} · {result['split']} · {run['questions']}/{run['questions_total']} "
        "questions"
    )
    if result["status"] == "skipped":
        return [f"{head} · skipped: {json.dumps(result['skipped'])}"]
    overall = result["aggregates"]["overall"] or {}
    lines = [f"{head} · {overall.get('errors', 0)} error(s)"]
    for key, title in METRICS:
        lines.append(
            f"  {title:<22} {format_metric(overall.get(key), binary=key in BINARY_METRICS)}"
        )
    cost, latency = result["cost"], result["latency"]
    if cost["estimated_cost_usd"] is not None:
        verified = "" if cost["prices_verified"] else " (unverified prices)"
        lines.append(f"  Cost                   ${cost['estimated_cost_usd']:.4f}{verified}")
    if latency["p50_s"] is not None:
        lines.append(f"  Latency p50 / p95      {latency['p50_s']} s / {latency['p95_s']} s")
    if result["judge"]["notice"]:
        lines.append(f"  Judge                  {result['judge']['notice']}")
    return lines


async def _main(options: RunOptions) -> int:
    if not _SPLIT_RE.match(options.split):
        print("--split-name must be lower-case letters, digits and '-'", file=sys.stderr)
        return 2
    try:
        if options.private_out is not None:
            check_private_dir(options.private_out)
        _check_recording(options)
        questions = load_questions(options.questions, limit=options.limit)
        _check_split_labels(options, questions)
        catalog = ReleaseCatalog.load(options.catalog) if options.catalog else None
        _check_documents(options)
    except (ValueError, QuestionSetError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    endpoint = (options.env.get("DOCWIKI_FOUNDRY_PROJECT_ENDPOINT") or "").strip() or None
    if options.extract_mode == "azure" and endpoint is None:
        print("error: --extract-mode azure needs DOCWIKI_FOUNDRY_PROJECT_ENDPOINT", file=sys.stderr)
        return 2
    cache = ExtractionCache(
        options.corpus,
        options.cache_dir,
        mode="azure" if options.extract_mode == "azure" else "local",
        cu_endpoint=endpoint,
    )
    corpus = await load_corpus(
        options.corpus,
        cache_dir=options.cache_dir,
        mode=cache.mode,
        cu_endpoint=endpoint,
        catalog=catalog,
    )
    judge: Judge | None = None
    judge_notice: str | None = None
    if options.judge:
        try:
            judge = Judge.from_env(options.env)
        except JudgeUnavailable as exc:
            judge_notice = str(exc)
            print(judge_notice, file=sys.stderr)
    try:
        result = await run_evaluation(
            options,
            questions=questions,
            corpus=corpus,
            judge=judge,
            judge_notice=judge_notice,
            extraction=cache.version(),
        )
    except SystemNotConfigured as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    name = result_name(
        result["system"],
        options.split,
        result["run"]["date"],
        limit=options.limit,
        complete=questions.complete,
    )
    public_path, private_path = write_results(
        result, out=options.out, name=name, private_out=options.private_out
    )
    for line in _summary_lines(result):
        print(line)
    print(f"results: {_display_path(public_path)}")
    if private_path is not None:
        print("per-question details written to --private-out")
    elif not options.public:
        print("per-question details not written (pass --private-out to keep them)")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    options = RunOptions(
        system=args.system,
        questions=args.questions,
        split=args.split,
        limit=args.limit,
        corpus=args.corpus,
        out=args.out,
        private_out=args.private_out,
        catalog=args.catalog,
        release_id=args.release_id,
        cache_dir=args.cache_dir,
        extract_mode=args.extract_mode,
        audience=args.audience,
        scope=args.scope,
        top_k=args.top_k,
        chunk_tokens=args.chunk_tokens,
        budget_tokens=args.budget_tokens,
        concurrency=args.concurrency,
        judge=args.judge,
    )
    try:
        return asyncio.run(_main(options))
    except KeyboardInterrupt:
        return 130
