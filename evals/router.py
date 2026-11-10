"""Knowledge-access router: classify questions, fit routing, and build virtual routed arms."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import statistics
import sys
from collections.abc import Mapping, Sequence
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docwiki.llm import CallRecord, LlmClient, LlmUsage, create_llm_client
from evals import METRICS_VERSION, RESULT_FORMAT
from evals.compare import expand_named_paths, load_arm_runs
from evals.metrics import aggregate
from evals.questions import GoldenQuestion, load_questions

ROUTER_CLASSIFY_FORMAT = "docwiki.evals.router-classify/v1"
ROUTER_TABLE_FORMAT = "docwiki.evals.router-table/v1"
ROUTER_PROMPT_VERSION = "knowledge-access-router-v1"
ROUTER_SCHEMA_NAME = "eval_router_classify"
ROUTE_CLASSES = ("lookup", "aggregate-or-cross", "revision-or-absent")


class RouteOutput(BaseModel):
    route: Literal["lookup", "aggregate-or-cross", "revision-or-absent"]


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _float(value: Any) -> float | None:
    if isinstance(value, int | float):
        return float(value)
    return None


def _pass_metric(record: Mapping[str, Any]) -> float:
    abstain = bool(record.get("abstain"))
    metrics = record.get("metrics") if isinstance(record.get("metrics"), Mapping) else {}
    key = "abstention_accuracy" if abstain else "answer_accuracy"
    value = _float(metrics.get(key))
    return 1.0 if value is not None and value >= 1.0 else 0.0


def _question_accuracy(records: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    by_id: dict[str, list[float]] = {}
    for record in records:
        qid = str(record.get("id") or "")
        if not qid:
            continue
        by_id.setdefault(qid, []).append(_pass_metric(record))
    return {qid: statistics.fmean(values) for qid, values in by_id.items() if values}


def _question_cost(records: Sequence[Mapping[str, Any]]) -> dict[str, float]:
    by_id: dict[str, list[float]] = {}
    for record in records:
        qid = str(record.get("id") or "")
        cost = _float(record.get("cost_usd"))
        if not qid or cost is None:
            continue
        by_id.setdefault(qid, []).append(cost)
    return {qid: statistics.fmean(values) for qid, values in by_id.items() if values}


def _classifier_prompt() -> str:
    return (
        "Classify one question into exactly one route for a knowledge-access benchmark.\n"
        "Routes:\n"
        '- "lookup": one direct fact, value, or table cell likely in one document.\n'
        '- "aggregate-or-cross": totals, lists, comparisons, or links across documents/chantiers.\n'
        '- "revision-or-absent": asks which version is current, what changed, or likely absent.\n'
        "Use only the question text. Return the route only."
    )


def _usage_dict(usage: LlmUsage) -> dict[str, int]:
    return {
        "input_tokens": usage.input_tokens,
        "output_tokens": usage.output_tokens,
        "cached_input_tokens": usage.cached_input_tokens,
        "reasoning_tokens": usage.reasoning_tokens,
        "calls": 1,
    }


def _call_cost(result: Any, *, pricing_model: str | None, llm: LlmClient) -> float | None:
    ledger = getattr(llm, "ledger", None)
    if ledger is None:
        return None
    record = CallRecord(
        tier=result.tier,
        deployment=result.deployment,
        model=result.model,
        model_version=result.model_version,
        pricing_model=pricing_model,
        schema_name=result.schema_name,
        prompt_version=result.prompt_version,
        request_hash=result.request_hash,
        origin=result.origin,
        usage=result.usage,
    )
    cost = ledger.cost_of(record)
    return None if cost is None else round(cost, 6)


def _load_classifications(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping) or data.get("format") != ROUTER_CLASSIFY_FORMAT:
        raise ValueError(f"{path.name} is not a {ROUTER_CLASSIFY_FORMAT} file")
    items = data.get("questions")
    if not isinstance(items, Mapping):
        raise ValueError(f"{path.name} has no question classifications")
    return dict(items)


async def classify_questions(
    *,
    questions_file: Path,
    cache_file: Path,
    llm: LlmClient,
    tier: str,
    concurrency: int,
) -> dict[str, Any]:
    questions = load_questions(questions_file).questions
    existing: dict[str, Any] = {}
    if cache_file.is_file():
        try:
            data = json.loads(cache_file.read_text(encoding="utf-8"))
            if isinstance(data, Mapping) and data.get("format") == ROUTER_CLASSIFY_FORMAT:
                known = data.get("questions")
                if isinstance(known, Mapping):
                    existing = dict(known)
        except json.JSONDecodeError:
            existing = {}

    semaphore = asyncio.Semaphore(max(1, concurrency))
    pricing_model = (
        os.environ.get("DOCWIKI_FAST_MODEL")
        if tier == "fast"
        else os.environ.get("DOCWIKI_SMART_MODEL")
    )
    pricing_model = pricing_model.strip() if pricing_model else None

    async def classify_one(question: GoldenQuestion) -> tuple[str, dict[str, Any]]:
        qid = question.id
        cached = existing.get(qid)
        if isinstance(cached, Mapping) and cached.get("route") in ROUTE_CLASSES:
            return qid, dict(cached)
        async with semaphore:
            result = await llm.structured(
                tier=tier,  # type: ignore[arg-type]
                system=_classifier_prompt(),
                user=question.question,
                output=RouteOutput,
                schema_name=ROUTER_SCHEMA_NAME,
                prompt_version=ROUTER_PROMPT_VERSION,
                max_output_tokens=50,
                metadata={"stage": "eval-router-classify", "question_id": qid},
            )
        return (
            qid,
            {
                "route": result.output.route,
                "usage": _usage_dict(result.usage),
                "cost_usd": _call_cost(result, pricing_model=pricing_model, llm=llm),
                "latency_s": round(result.latency_s, 6),
                "request_hash": result.request_hash,
            },
        )

    pairs = await asyncio.gather(*(classify_one(question) for question in questions))
    rows = {qid: value for qid, value in pairs}
    usage = {
        key: sum(int((row.get("usage") or {}).get(key) or 0) for row in rows.values())
        for key in (
            "input_tokens",
            "output_tokens",
            "cached_input_tokens",
            "reasoning_tokens",
            "calls",
        )
    }
    costs = [float(row["cost_usd"]) for row in rows.values() if row.get("cost_usd") is not None]
    latencies = [
        float(row["latency_s"]) for row in rows.values() if row.get("latency_s") is not None
    ]
    return {
        "format": ROUTER_CLASSIFY_FORMAT,
        "prompt_version": ROUTER_PROMPT_VERSION,
        "tier": tier,
        "questions_file": {
            "file": questions_file.name,
            "sha256": load_questions(questions_file).sha256,
            "count": len(questions),
        },
        "questions": rows,
        "totals": {
            "questions": len(rows),
            **usage,
            "estimated_cost_usd": round(sum(costs), 6) if costs else None,
            "latency_p50_s": round(statistics.median(latencies), 3) if latencies else None,
        },
    }


def _fit_routes(
    classes: Mapping[str, str],
    arms_accuracy: Mapping[str, Mapping[str, float]],
    arms_cost: Mapping[str, Mapping[str, float]],
    train_ids: Sequence[str],
) -> dict[str, str]:
    routes: dict[str, str] = {}
    all_ids = list(train_ids)
    labels = sorted(set(classes[qid] for qid in all_ids if qid in classes))
    for label in labels:
        ids = [qid for qid in all_ids if classes.get(qid) == label]
        candidate_scores: list[tuple[str, float, float]] = []
        for arm, score_by_q in arms_accuracy.items():
            observed = [score_by_q[qid] for qid in ids if qid in score_by_q]
            if not observed:
                continue
            mean_score = statistics.fmean(observed)
            cost_by_q = arms_cost.get(arm, {})
            mean_cost = (
                statistics.fmean([cost_by_q[qid] for qid in ids if qid in cost_by_q])
                if any(qid in cost_by_q for qid in ids)
                else float("inf")
            )
            candidate_scores.append((arm, mean_score, mean_cost))
        if not candidate_scores:
            continue
        best = sorted(candidate_scores, key=lambda item: (-item[1], item[2], item[0]))[0][0]
        routes[label] = best
    return routes


def _file_bundle_hash(
    classifications: Path, arm_paths: Mapping[str, Sequence[Path]]
) -> dict[str, Any]:
    payload = {
        "classifications": {"path": classifications.name, "sha256": _sha256(classifications)},
        "arms": {
            arm: [{"path": path.name, "sha256": _sha256(path)} for path in sorted(paths, key=str)]
            for arm, paths in sorted(arm_paths.items())
        },
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    payload["hash"] = hashlib.sha256(canonical).hexdigest()
    return payload


def fit_router(
    *,
    classifications_file: Path,
    arm_paths: Mapping[str, Sequence[Path]],
) -> dict[str, Any]:
    classes_raw = _load_classifications(classifications_file)
    classes = {
        qid: str(item.get("route"))
        for qid, item in classes_raw.items()
        if isinstance(item, Mapping)
    }
    arms = load_arm_runs(arm_paths)
    arm_accuracy: dict[str, dict[str, float]] = {}
    arm_cost: dict[str, dict[str, float]] = {}
    for name, arm in arms.items():
        merged = [record.raw for run in arm.runs for record in run.records.values()]
        arm_accuracy[name] = _question_accuracy(merged)
        arm_cost[name] = _question_cost(merged)
    ids = sorted(
        set(classes) & set.intersection(*(set(values) for values in arm_accuracy.values()))
    )
    routes = _fit_routes(classes, arm_accuracy, arm_cost, ids)

    loo_scores: list[float] = []
    loo_costs: list[float] = []
    classifier_cost = {qid: _float((classes_raw.get(qid) or {}).get("cost_usd")) for qid in ids}
    for qid in ids:
        train = [item for item in ids if item != qid]
        fitted = _fit_routes(classes, arm_accuracy, arm_cost, train)
        route = classes[qid]
        chosen = fitted.get(route) or routes.get(route)
        if chosen is None or qid not in arm_accuracy.get(chosen, {}):
            continue
        loo_scores.append(arm_accuracy[chosen][qid])
        question_cost = arm_cost.get(chosen, {}).get(qid)
        total_cost = (classifier_cost.get(qid) or 0.0) + (question_cost or 0.0)
        loo_costs.append(total_cost)

    fitted_on = _file_bundle_hash(classifications_file, arm_paths)
    return {
        "format": ROUTER_TABLE_FORMAT,
        "prompt_version": ROUTER_PROMPT_VERSION,
        "routes": routes,
        "classes": sorted(set(classes.values())),
        "fitted_on": fitted_on,
        "dev_estimate": {
            "questions": len(loo_scores),
            "loo_accuracy": round(statistics.fmean(loo_scores), 6) if loo_scores else None,
            "loo_cost_per_question_usd": (
                round(statistics.fmean(loo_costs), 6) if loo_costs else None
            ),
        },
    }


def _build_virtual_result(
    *,
    name: str,
    split: str,
    records: list[dict[str, Any]],
    mode: str,
    metadata: Mapping[str, Any],
) -> dict[str, Any]:
    start = datetime.now(UTC).replace(microsecond=0)
    costs = [
        float(record["cost_usd"])
        for record in records
        if _float(record.get("cost_usd")) is not None
    ]
    latencies = [
        float(record["latency_s"])
        for record in records
        if _float(record.get("latency_s")) is not None
    ]
    scored = aggregate(records)
    end = datetime.now(UTC).replace(microsecond=0)
    return {
        "format": RESULT_FORMAT,
        "system": name,
        "split": split,
        "status": "ok",
        "run": {
            "started_at": start.isoformat().replace("+00:00", "Z"),
            "finished_at": end.isoformat().replace("+00:00", "Z"),
            "date": start.date().isoformat(),
            "duration_s": round((end - start).total_seconds(), 3),
            "questions": len(records),
            "questions_total": len(records),
            "complete": True,
            "limit": None,
            "concurrency": 1,
            "label": None,
        },
        "questions_file": {"file": None, "sha256": None, "questions": len(records), "seal": None},
        "config": {"system": {"mode": mode, **metadata}},
        "versions": {
            "docwiki": None,
            "git_sha": None,
            "git_dirty": None,
            "metrics": METRICS_VERSION,
            "release_id": None,
            "release_audience": None,
            "corpus_manifest_sha256": None,
            "extraction": None,
            "extractors": None,
            "system": {"router_mode": mode, "prompt_version": ROUTER_PROMPT_VERSION},
            "judge": None,
        },
        "aggregates": {"overall": scored.get("overall"), "by_category": scored.get("by_category")},
        "failures": scored.get("failures", {}),
        "errors": scored.get("errors", []),
        "cost": {
            "currency": "USD",
            "input_tokens": sum(
                int((record.get("tokens") or {}).get("input") or 0) for record in records
            ),
            "cached_input_tokens": sum(
                int((record.get("tokens") or {}).get("cached_input") or 0) for record in records
            ),
            "output_tokens": sum(
                int((record.get("tokens") or {}).get("output") or 0) for record in records
            ),
            "reasoning_tokens": sum(
                int((record.get("tokens") or {}).get("reasoning") or 0) for record in records
            ),
            "estimated_cost_usd": round(sum(costs), 6) if costs else None,
            "per_question_usd": round(sum(costs) / len(costs), 6) if costs else None,
            "priced_questions": len(costs),
            "prices_verified": False,
            "receipt_totals": None,
        },
        "latency": {
            "mean_s": round(statistics.fmean(latencies), 3) if latencies else None,
            "p50_s": round(statistics.median(latencies), 3) if latencies else None,
            "p95_s": _p95(latencies),
            "max_s": round(max(latencies), 3) if latencies else None,
            "total_s": round(sum(latencies), 3) if latencies else 0.0,
        },
        "judge": {"enabled": False, "notice": None, "notices": [], "summary": None},
        "questions": records,
    }


def _p95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, round(0.95 * len(ordered) + 0.4999) - 1)
    index = min(index, len(ordered) - 1)
    return round(ordered[index], 3)


def _output_paths(path: Path, runs: int, *, prefix: str) -> list[Path]:
    if runs == 1:
        return [path]
    if path.suffix.lower() == ".json":
        stem = path.with_suffix("")
        return [stem.parent / f"{stem.name}-{prefix}{index + 1}.json" for index in range(runs)]
    path.mkdir(parents=True, exist_ok=True)
    return [path / f"{prefix}{index + 1}.json" for index in range(runs)]


def _load_table(path: Path) -> Mapping[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping) or data.get("format") != ROUTER_TABLE_FORMAT:
        raise ValueError(f"{path.name} is not a {ROUTER_TABLE_FORMAT} file")
    return data


def build_routed_results(
    *,
    table_file: Path,
    classifications_file: Path,
    arm_paths: Mapping[str, Sequence[Path]],
    name: str,
    mode: Literal["router", "oracle"],
) -> list[dict[str, Any]]:
    table = _load_table(table_file)
    classes_raw = _load_classifications(classifications_file)
    routes = table.get("routes") if isinstance(table.get("routes"), Mapping) else {}
    classes = {
        qid: str(item.get("route"))
        for qid, item in classes_raw.items()
        if isinstance(item, Mapping)
    }
    arms = load_arm_runs(arm_paths)
    run_counts = {len(arm.runs) for arm in arms.values()}
    if len(run_counts) != 1:
        raise ValueError("all arms must provide the same number of run files")
    runs = next(iter(run_counts))
    split_values = {arm.split for arm in arms.values()}
    if len(split_values) != 1:
        raise ValueError("all arms must be from the same split")
    split = next(iter(split_values))

    outputs: list[dict[str, Any]] = []
    for run_index in range(runs):
        rows: list[dict[str, Any]] = []
        for qid in sorted(classes):
            if mode == "router":
                route = classes[qid]
                arm_name = str(routes.get(route) or "")
                if arm_name not in arms:
                    continue
            else:
                candidates = [
                    arm_name for arm_name, arm in arms.items() if qid in arm.runs[run_index].records
                ]
                if not candidates:
                    continue

                def _oracle_key(
                    arm_name: str, *, _run_index: int = run_index, _qid: str = qid
                ) -> tuple[float, float, str]:
                    record = arms[arm_name].runs[_run_index].records[_qid].raw
                    cost = _float(record.get("cost_usd"))
                    return (
                        -_pass_metric(record),
                        float("inf") if cost is None else cost,
                        arm_name,
                    )

                arm_name = sorted(candidates, key=_oracle_key)[0]

            source_record = arms[arm_name].runs[run_index].records.get(qid)
            if source_record is None:
                continue
            row = deepcopy(dict(source_record.raw))
            info = row.get("info") if isinstance(row.get("info"), Mapping) else {}
            row["info"] = dict(info)
            row["info"]["router_arm"] = arm_name
            row["info"]["router_mode"] = mode
            if mode == "router":
                classifier = (
                    classes_raw.get(qid) if isinstance(classes_raw.get(qid), Mapping) else {}
                )
                usage = (
                    classifier.get("usage") if isinstance(classifier.get("usage"), Mapping) else {}
                )
                tokens = row.get("tokens") if isinstance(row.get("tokens"), Mapping) else {}
                merged = dict(tokens)
                merged["input"] = int(merged.get("input") or 0) + int(
                    usage.get("input_tokens") or 0
                )
                merged["output"] = int(merged.get("output") or 0) + int(
                    usage.get("output_tokens") or 0
                )
                merged["cached_input"] = int(merged.get("cached_input") or 0) + int(
                    usage.get("cached_input_tokens") or 0
                )
                merged["reasoning"] = int(merged.get("reasoning") or 0) + int(
                    usage.get("reasoning_tokens") or 0
                )
                merged["calls"] = int(merged.get("calls") or 0) + int(usage.get("calls") or 0)
                merged["total"] = (
                    int(merged.get("input") or 0)
                    + int(merged.get("output") or 0)
                    + int(merged.get("cached_input") or 0)
                )
                row["tokens"] = merged
                row["cost_usd"] = round(
                    (_float(row.get("cost_usd")) or 0.0)
                    + (_float(classifier.get("cost_usd")) or 0.0),
                    6,
                )
                row["latency_s"] = round(
                    (_float(row.get("latency_s")) or 0.0)
                    + (_float(classifier.get("latency_s")) or 0.0),
                    6,
                )
            rows.append(row)

        outputs.append(
            _build_virtual_result(
                name=name,
                split=split,
                records=rows,
                mode=mode,
                metadata={
                    "table_hash": table.get("fitted_on", {}).get("hash"),
                    "source_results": {
                        arm: [run.path.name for run in data.runs]
                        for arm, data in sorted(arms.items())
                    },
                },
            )
        )
    return outputs


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)

    classify = sub.add_parser("classify", help="classify questions with the fast tier")
    classify.add_argument("--questions", type=Path, required=True, help="questions JSONL")
    classify.add_argument("--cache", type=Path, required=True, help="classification cache JSON")
    classify.add_argument("--tier", choices=("fast", "smart"), default="fast")
    classify.add_argument("--concurrency", type=int, default=4)

    fit = sub.add_parser("fit", help="fit a routing table on dev data")
    fit.add_argument("--classifications", type=Path, required=True)
    fit.add_argument("--arm", action="append", required=True, help="NAME=run1[,run2,...]")
    fit.add_argument("--out", type=Path, required=True)

    for name, help_text in (
        ("apply", "build routed virtual result arm"),
        ("oracle", "build per-question best-arm upper bound"),
    ):
        cmd = sub.add_parser(name, help=help_text)
        cmd.add_argument("--table", type=Path, required=True)
        cmd.add_argument("--classifications", type=Path, required=True)
        cmd.add_argument("--arm", action="append", required=True, help="NAME=run1[,run2,...]")
        cmd.add_argument("--out", type=Path, required=True)
        cmd.add_argument("--name", default=name)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "classify":

        async def _run() -> dict[str, Any]:
            llm = create_llm_client()
            try:
                return await classify_questions(
                    questions_file=args.questions,
                    cache_file=args.cache,
                    llm=llm,
                    tier=args.tier,
                    concurrency=args.concurrency,
                )
            finally:
                await llm.aclose()

        payload = asyncio.run(_run())
        args.cache.parent.mkdir(parents=True, exist_ok=True)
        args.cache.write_text(_dumps(payload), encoding="utf-8", newline="\n")
        print(f"classifications: {args.cache}")
        return 0

    if args.command == "fit":
        try:
            arm_paths = expand_named_paths(args.arm, option="--arm")
            table = fit_router(classifications_file=args.classifications, arm_paths=arm_paths)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(_dumps(table), encoding="utf-8", newline="\n")
        print(f"routing table: {args.out}")
        return 0

    mode = "router" if args.command == "apply" else "oracle"
    try:
        arm_paths = expand_named_paths(args.arm, option="--arm")
        outputs = build_routed_results(
            table_file=args.table,
            classifications_file=args.classifications,
            arm_paths=arm_paths,
            name=args.name,
            mode=mode,  # type: ignore[arg-type]
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    paths = _output_paths(args.out, len(outputs), prefix=f"{mode}-r")
    for path, payload in zip(paths, outputs, strict=True):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_dumps(payload), encoding="utf-8", newline="\n")
        print(f"{mode} result: {path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
