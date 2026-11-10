"""Compare evaluation arms for the knowledge-access study."""

from __future__ import annotations

import argparse
import glob
import hashlib
import json
import math
import random
import re
import statistics
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals import RESULT_FORMAT
from evals.textnorm import normalize_text

__all__ = [
    "COMPARE_FORMAT",
    "Contrast",
    "expand_named_paths",
    "load_arm_runs",
    "main",
    "summarise_arm",
]

COMPARE_FORMAT = "docwiki.evals.compare/v1"
SIGNIFICANCE_ALPHA = 0.05
DEFAULT_BOOTSTRAP = 10_000
DEFAULT_PERMUTATIONS = 10_000
DEFAULT_SEED = 20261110
ABSTENTION_VERSIONS = ("v1", "v2")

_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+$")
_LEADING_MARKS = "*_#>'\" -:`"
_ABSTENTION_V2 = (
    re.compile(r"^not found\b"),
    re.compile(r"^i (?:did not|didnt) find\b"),
    re.compile(r"^no .{0,80}\b(?:is|are)\b .{0,20}\b(?:named|mentioned)\b"),
    re.compile(r"^je nai pas trouve\b"),
    re.compile(r"^aucun .{0,100}\bnest mentionne\b"),
)


@dataclass(frozen=True)
class RunQuestion:
    id: str
    category: str
    abstain: bool
    metrics: Mapping[str, Any]
    answer_text: str
    answer_abstained: bool
    citation_count: int
    latency_s: float | None
    cost_usd: float | None
    tool_calls: int
    raw: Mapping[str, Any]


@dataclass(frozen=True)
class ArmRun:
    path: Path
    split: str
    records: Mapping[str, RunQuestion]


@dataclass(frozen=True)
class ArmData:
    name: str
    runs: tuple[ArmRun, ...]

    @property
    def split(self) -> str:
        return self.runs[0].split

    @property
    def question_ids(self) -> tuple[str, ...]:
        ids = sorted({qid for run in self.runs for qid in run.records})
        return tuple(ids)


@dataclass(frozen=True)
class Contrast:
    name: str
    plus: tuple[str, ...]
    minus: tuple[str, ...]


def _dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False, indent=2) + "\n"


def _percentile(sorted_values: Sequence[float], share: float) -> float:
    if not sorted_values:
        return math.nan
    if len(sorted_values) == 1:
        return sorted_values[0]
    position = (len(sorted_values) - 1) * share
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return sorted_values[low]
    weight = position - low
    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


def _p95(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return round(ordered[index], 3)


def _safe_mean(values: Sequence[float]) -> float | None:
    return round(statistics.fmean(values), 6) if values else None


def _looks_like_glob(value: str) -> bool:
    return any(mark in value for mark in "*?[]")


def _parse_named_spec(spec: str, *, option: str) -> tuple[str, list[str]]:
    if "=" not in spec:
        raise ValueError(f"{option} expects NAME=path[,path2,...], got {spec!r}")
    name, raw = spec.split("=", 1)
    name = name.strip()
    if not name or not _NAME_RE.fullmatch(name):
        raise ValueError(f"{option}: invalid name {name!r}")
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    if not parts:
        raise ValueError(f"{option}: {name!r} has no path")
    return name, parts


def _expand_paths(patterns: Sequence[str], *, option: str, name: str) -> list[Path]:
    found: list[Path] = []
    for token in patterns:
        if _looks_like_glob(token):
            matches = [Path(path) for path in sorted(glob.glob(token))]
            if not matches:
                raise ValueError(f"{option}: {name!r} pattern {token!r} matched no file")
            found.extend(matches)
            continue
        path = Path(token)
        if not path.is_file():
            raise ValueError(f"{option}: {name!r} file not found: {token}")
        found.append(path)
    deduped = sorted({path.resolve(): path for path in found}.values(), key=lambda item: str(item))
    return deduped


def expand_named_paths(specs: Sequence[str], *, option: str) -> dict[str, list[Path]]:
    groups: dict[str, list[Path]] = {}
    for spec in specs:
        name, patterns = _parse_named_spec(spec, option=option)
        if name in groups:
            raise ValueError(f"{option}: duplicate name {name!r}")
        groups[name] = _expand_paths(patterns, option=option, name=name)
    return groups


def _load_result(path: Path) -> Mapping[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read {path.name}: {type(exc).__name__}") from None
    if not isinstance(data, Mapping) or data.get("format") != RESULT_FORMAT:
        raise ValueError(f"{path.name} is not a {RESULT_FORMAT} result file")
    questions = data.get("questions")
    if not isinstance(questions, list):
        raise ValueError(
            f"{path.name} has no per-question records (use private files for non-dev splits)"
        )
    return data


def _float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _load_run(path: Path) -> ArmRun:
    data = _load_result(path)
    split = str(data.get("split") or "")
    records: dict[str, RunQuestion] = {}
    for item in data.get("questions") or []:
        if not isinstance(item, Mapping):
            continue
        qid = str(item.get("id") or "").strip()
        if not qid:
            continue
        answer = item.get("answer") or {}
        citations = answer.get("citations") if isinstance(answer, Mapping) else None
        metrics = item.get("metrics") if isinstance(item.get("metrics"), Mapping) else {}
        if qid in records:
            raise ValueError(f"{path.name} has duplicate question id {qid!r}")
        records[qid] = RunQuestion(
            id=qid,
            category=str(item.get("category") or ""),
            abstain=bool(item.get("abstain")),
            metrics=metrics,
            answer_text=str((answer or {}).get("text") or ""),
            answer_abstained=bool((answer or {}).get("abstained")),
            citation_count=len(citations) if isinstance(citations, list) else 0,
            latency_s=_float_or_none(item.get("latency_s")),
            cost_usd=_float_or_none(item.get("cost_usd")),
            tool_calls=len(item.get("tool_calls") or []),
            raw=item,
        )
    if not records:
        raise ValueError(f"{path.name} has no usable question record")
    return ArmRun(path=path, split=split, records=records)


def load_arm_runs(specs: Mapping[str, Sequence[Path]]) -> dict[str, ArmData]:
    arms: dict[str, ArmData] = {}
    for name, paths in specs.items():
        if not paths:
            raise ValueError(f"arm {name!r} has no result file")
        runs = tuple(_load_run(path) for path in paths)
        splits = {run.split for run in runs}
        if len(splits) != 1:
            raise ValueError(f"arm {name!r} mixes splits: {', '.join(sorted(splits))}")
        arms[name] = ArmData(name=name, runs=runs)
    return arms


def _answer_body(text: str) -> str:
    for marker in ("\n\nSources:", "\nSources:"):
        if marker in text:
            return text.split(marker, 1)[0]
    return text


def abstention_v2(body: str) -> bool:
    text = normalize_text(body).lstrip(_LEADING_MARKS)
    return any(pattern.search(text) for pattern in _ABSTENTION_V2)


def _abstention_score(record: RunQuestion, *, version: str) -> float:
    metric = _float_or_none(record.metrics.get("abstention_accuracy"))
    if version == "v1":
        return float(metric) if metric is not None else 0.0
    if version != "v2":
        raise ValueError(f"unknown abstention version {version!r}")
    if not record.abstain:
        return float(metric) if metric is not None else 0.0
    if record.answer_abstained:
        return 1.0
    return 1.0 if abstention_v2(_answer_body(record.answer_text)) else 0.0


def _pass(record: RunQuestion, *, abstention: str) -> float:
    if record.abstain:
        return 1.0 if _abstention_score(record, version=abstention) >= 1.0 else 0.0
    value = _float_or_none(record.metrics.get("answer_accuracy"))
    return 1.0 if value is not None and value >= 1.0 else 0.0


def _question_values(
    arm: ArmData, *, abstention: str
) -> tuple[dict[str, list[float]], dict[str, str], list[RunQuestion]]:
    values: dict[str, list[float]] = {}
    categories: dict[str, str] = {}
    flat: list[RunQuestion] = []
    for run in arm.runs:
        for qid, record in run.records.items():
            categories.setdefault(qid, record.category)
            values.setdefault(qid, []).append(_pass(record, abstention=abstention))
            flat.append(record)
    return values, categories, flat


def _question_metric_means(records: Sequence[RunQuestion], key: str) -> float | None:
    values = [_float_or_none(record.metrics.get(key)) for record in records]
    scores = [value for value in values if value is not None]
    return _safe_mean(scores)


def _bootstrap(
    per_question: Mapping[str, Sequence[float]],
    *,
    seed: int,
    samples: int,
) -> tuple[float, float]:
    ids = [qid for qid, values in per_question.items() if values]
    if not ids:
        return (math.nan, math.nan)
    rng = random.Random(seed)
    boot: list[float] = []
    for _ in range(samples):
        total = 0.0
        count = 0
        for _ in range(len(ids)):
            values = per_question[ids[rng.randrange(len(ids))]]
            total += float(sum(values))
            count += len(values)
        boot.append(total / count if count else 0.0)
    ordered = sorted(boot)
    return (
        round(_percentile(ordered, 0.025), 6),
        round(_percentile(ordered, 0.975), 6),
    )


def _arm_cost_per_correct(
    records: Sequence[RunQuestion], *, abstention: str
) -> tuple[float | None, int]:
    total_cost = 0.0
    passes = 0
    priced = 0
    for record in records:
        if record.cost_usd is None:
            continue
        priced += 1
        total_cost += record.cost_usd
        if _pass(record, abstention=abstention) >= 1.0:
            passes += 1
    if priced == 0 or passes == 0:
        return (None, priced)
    return (round(total_cost / passes, 6), priced)


def summarise_arm(
    arm: ArmData,
    *,
    abstention: str,
    bootstrap: int,
    seed: int,
) -> dict[str, Any]:
    per_question, categories, records = _question_values(arm, abstention=abstention)
    passes = [value for values in per_question.values() for value in values]
    mean_single = _safe_mean(passes) or 0.0
    ci_low, ci_high = _bootstrap(per_question, seed=seed, samples=bootstrap)
    question_means = {
        qid: statistics.fmean(values) for qid, values in per_question.items() if values
    }
    majority = _safe_mean([1.0 if value > 0.5 else 0.0 for value in question_means.values()])
    per_category: dict[str, float] = {}
    for category in sorted({name for name in categories.values() if name}):
        values = [
            question_means[qid]
            for qid, current in categories.items()
            if current == category and qid in question_means
        ]
        if values:
            per_category[category] = round(statistics.fmean(values), 6)

    restricted = sorted(
        record.id
        for record in records
        if _float_or_none(record.metrics.get("restricted_exclusion")) == 0.0
    )
    injection = sorted(
        record.id
        for record in records
        if _float_or_none(record.metrics.get("injection_resistance")) == 0.0
    )
    excluded_ids = sorted(set(restricted) | set(injection))
    latency = [record.latency_s for record in records if record.latency_s is not None]
    tools = [float(record.tool_calls) for record in records]
    costs = [record.cost_usd for record in records if record.cost_usd is not None]
    cost_total = round(sum(costs), 6) if costs else None
    cost_per_question = round(sum(costs) / len(costs), 6) if costs else None
    cost_per_correct, priced = _arm_cost_per_correct(records, abstention=abstention)
    abstention_v1 = _safe_mean([_abstention_score(record, version="v1") for record in records])
    abstention_v2_mean = _safe_mean([_abstention_score(record, version="v2") for record in records])
    return {
        "arm": arm.name,
        "split": arm.split,
        "runs": len(arm.runs),
        "questions": len(question_means),
        "excluded": bool(excluded_ids),
        "excluded_question_ids": excluded_ids,
        "safety": {
            "restricted_exclusion_failures": restricted,
            "injection_resistance_failures": injection,
        },
        "primary": {
            "mean_accuracy": round(mean_single, 6),
            "ci95": [ci_low, ci_high],
        },
        "secondary": {
            "majority_accuracy": majority,
            "per_category_accuracy": per_category,
            "numeric_exactness": _question_metric_means(records, "numeric_exactness"),
            "citation_precision": _question_metric_means(records, "citation_precision"),
            "citation_recall": _question_metric_means(records, "citation_recall"),
            "abstention_accuracy": abstention_v2_mean if abstention == "v2" else abstention_v1,
            "abstention_accuracy_v1": abstention_v1,
            "abstention_accuracy_v2": abstention_v2_mean,
            "latency_p50_s": round(statistics.median(latency), 3) if latency else None,
            "latency_p95_s": _p95([value for value in latency if value is not None]),
            "tool_calls_p50": round(statistics.median(tools), 3) if tools else None,
            "tool_calls_p95": _p95(tools),
            "cost_total_usd": cost_total,
            "cost_per_question_usd": cost_per_question,
            "cost_per_correct_usd": cost_per_correct,
            "priced_records": priced,
        },
        "question_accuracy": {
            qid: round(value, 6) for qid, value in sorted(question_means.items())
        },
    }


def _paired_deltas(
    left: Mapping[str, float], right: Mapping[str, float]
) -> tuple[list[float], list[str]]:
    ids = sorted(set(left) & set(right))
    return [left[qid] - right[qid] for qid in ids], ids


def _sign_flip_test(
    deltas: Sequence[float], *, seed: int, permutations: int
) -> tuple[float, float, float]:
    if not deltas:
        return (math.nan, math.nan, math.nan)
    observed = statistics.fmean(deltas)
    if all(delta == 0.0 for delta in deltas):
        return (round(observed, 6), 1.0, 1.0)
    rng = random.Random(seed)
    count_two = 0
    count_one = 0
    trials = 0
    exhaustive = len(deltas) <= 18 and (1 << len(deltas)) <= permutations
    if exhaustive:
        total = 1 << len(deltas)
        for mask in range(total):
            signed = [
                (delta if (mask >> index) & 1 else -delta) for index, delta in enumerate(deltas)
            ]
            stat = statistics.fmean(signed)
            if abs(stat) >= abs(observed):
                count_two += 1
            if stat >= observed:
                count_one += 1
        trials = total
    else:
        for _ in range(permutations):
            signed = [delta if rng.random() >= 0.5 else -delta for delta in deltas]
            stat = statistics.fmean(signed)
            if abs(stat) >= abs(observed):
                count_two += 1
            if stat >= observed:
                count_one += 1
        trials = permutations
    p_two = (count_two + 1) / (trials + 1)
    p_one = (count_one + 1) / (trials + 1)
    return (round(observed, 6), round(p_two, 6), round(p_one, 6))


def _holm(raw: Sequence[float]) -> list[float]:
    indexed = sorted(enumerate(raw), key=lambda item: item[1])
    adjusted = [math.nan] * len(raw)
    running = 0.0
    total = len(raw)
    for rank, (index, p_value) in enumerate(indexed):
        scaled = min(1.0, (total - rank) * p_value)
        running = max(running, scaled)
        adjusted[index] = running
    return [round(value, 6) for value in adjusted]


def parse_contrast(spec: str) -> Contrast:
    name, raw = _parse_named_spec(spec, option="--contrast")
    expression = raw[0]
    if len(raw) > 1:
        expression = ",".join(raw)
    tokens = [token.strip() for token in re.findall(r"[+-]?[^+-]+", expression) if token.strip()]
    plus: list[str] = []
    minus: list[str] = []
    for token in tokens:
        sign = "-" if token.startswith("-") else "+"
        arm = token[1:] if token[0] in "+-" else token
        arm = arm.strip()
        if not arm or not _NAME_RE.fullmatch(arm):
            raise ValueError(f"--contrast {name!r}: invalid arm {arm!r}")
        (minus if sign == "-" else plus).append(arm)
    if not plus or not minus:
        raise ValueError(f"--contrast {name!r} needs plus and minus arms (A+B-C-D)")
    return Contrast(name=name, plus=tuple(plus), minus=tuple(minus))


def _contrast_values(
    contrast: Contrast, accuracy: Mapping[str, Mapping[str, float]]
) -> tuple[list[float], list[str]]:
    required = [*contrast.plus, *contrast.minus]
    ids = sorted(set.intersection(*(set(accuracy[arm]) for arm in required)))
    values: list[float] = []
    for qid in ids:
        positive = statistics.fmean([accuracy[arm][qid] for arm in contrast.plus])
        negative = statistics.fmean([accuracy[arm][qid] for arm in contrast.minus])
        values.append(positive - negative)
    return values, ids


def _load_judge_supported(files: Sequence[Path]) -> float | None:
    values: list[float] = []
    for path in files:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        aggregates = data.get("aggregates") if isinstance(data, Mapping) else None
        mean = _float_or_none((aggregates or {}).get("supported_mean"))
        if mean is not None:
            values.append(mean)
            continue
        for item in data.get("questions") or []:
            if not isinstance(item, Mapping):
                continue
            score = _float_or_none(item.get("claims_supported"))
            if score is not None:
                values.append(score)
    return round(statistics.fmean(values), 6) if values else None


def _decision(
    summaries: Mapping[str, Mapping[str, Any]],
    per_arm_accuracy: Mapping[str, Mapping[str, float]],
    *,
    seed: int,
    permutations: int,
) -> dict[str, Any]:
    eligible = [name for name, summary in summaries.items() if not bool(summary.get("excluded"))]
    if not eligible:
        return {"status": "no-eligible", "eligible": [], "winner": None, "set": []}
    ordered = sorted(
        eligible,
        key=lambda arm: float((summaries[arm]["primary"] or {}).get("mean_accuracy") or 0.0),
        reverse=True,
    )
    best = ordered[0]
    comparisons: list[dict[str, Any]] = []
    raw: list[float] = []
    for rank, other in enumerate(ordered[1:], 1):
        deltas, ids = _paired_deltas(per_arm_accuracy[best], per_arm_accuracy[other])
        effect, _p_two, p_one = _sign_flip_test(
            deltas,
            seed=seed + 1000 + rank,
            permutations=permutations,
        )
        raw.append(p_one)
        comparisons.append(
            {
                "left": best,
                "right": other,
                "effect": effect,
                "raw_p": p_one,
                "n_questions": len(ids),
            }
        )
    if raw:
        adjusted = _holm(raw)
        for item, adj in zip(comparisons, adjusted, strict=True):
            item["holm_p"] = adj
    all_significant = comparisons and all(
        item["effect"] > 0.0 and item["holm_p"] < SIGNIFICANCE_ALPHA for item in comparisons
    )
    if len(ordered) == 1:
        all_significant = True
    if all_significant:
        return {
            "status": "winner",
            "winner": best,
            "best": best,
            "eligible": ordered,
            "set": [best],
            "comparisons": comparisons,
            "margin_points": 5.0,
        }

    best_mean = float((summaries[best]["primary"] or {}).get("mean_accuracy") or 0.0)
    margin = 0.05
    in_set = [
        arm
        for arm in ordered
        if best_mean - float((summaries[arm]["primary"] or {}).get("mean_accuracy") or 0.0)
        <= margin
    ]
    by_other = {item["right"]: item for item in comparisons}
    kept: list[str] = [best]
    for arm in in_set:
        if arm == best:
            continue
        comparison = by_other.get(arm)
        if comparison is None:
            kept.append(arm)
            continue
        if comparison["effect"] > 0.0 and comparison["holm_p"] < SIGNIFICANCE_ALPHA:
            continue
        kept.append(arm)
    return {
        "status": "set",
        "winner": None,
        "best": best,
        "eligible": ordered,
        "set": kept,
        "comparisons": comparisons,
        "margin_points": 5.0,
    }


def build_report(
    arms: Mapping[str, ArmData],
    *,
    reference: str,
    seed: int,
    bootstrap: int,
    permutations: int,
    abstention: str,
    contrasts: Sequence[Contrast],
    judges: Mapping[str, float | None],
    per_question: bool,
) -> dict[str, Any]:
    if reference not in arms:
        raise ValueError(f"--reference {reference!r} is not among --arm names")
    summaries = {
        name: summarise_arm(
            arm,
            abstention=abstention,
            bootstrap=bootstrap,
            seed=seed + index,
        )
        for index, (name, arm) in enumerate(sorted(arms.items()))
    }
    per_arm_accuracy = {
        name: dict(summary.get("question_accuracy") or {}) for name, summary in summaries.items()
    }

    tests: list[dict[str, Any]] = []
    raw_family: list[float] = []
    family_seed = seed + 10_000
    others = [name for name in sorted(arms) if name != reference]
    for index, name in enumerate(others, 1):
        deltas, ids = _paired_deltas(per_arm_accuracy[name], per_arm_accuracy[reference])
        effect, raw_p, _one = _sign_flip_test(
            deltas,
            seed=family_seed + index,
            permutations=permutations,
        )
        raw_family.append(raw_p)
        tests.append(
            {
                "family": "vs_reference",
                "label": f"{name} - {reference}",
                "left": name,
                "right": reference,
                "effect": effect,
                "raw_p": raw_p,
                "n_questions": len(ids),
            }
        )

    eligible = [name for name, summary in summaries.items() if not summary["excluded"]]
    ranked = sorted(
        eligible,
        key=lambda arm: float((summaries[arm]["primary"] or {}).get("mean_accuracy") or 0.0),
        reverse=True,
    )
    if len(ranked) >= 2:
        best, second = ranked[0], ranked[1]
        deltas, ids = _paired_deltas(per_arm_accuracy[best], per_arm_accuracy[second])
        effect, raw_p, _one = _sign_flip_test(
            deltas,
            seed=family_seed + 500,
            permutations=permutations,
        )
        raw_family.append(raw_p)
        tests.append(
            {
                "family": "best_vs_second",
                "label": f"{best} - {second}",
                "left": best,
                "right": second,
                "effect": effect,
                "raw_p": raw_p,
                "n_questions": len(ids),
            }
        )

    for index, contrast in enumerate(contrasts, 1):
        missing = [arm for arm in [*contrast.plus, *contrast.minus] if arm not in arms]
        if missing:
            raise ValueError(f"--contrast {contrast.name!r} references unknown arm(s): {missing}")
        values, ids = _contrast_values(contrast, per_arm_accuracy)
        effect, raw_p, _one = _sign_flip_test(
            values,
            seed=family_seed + 1000 + index,
            permutations=permutations,
        )
        raw_family.append(raw_p)
        tests.append(
            {
                "family": "contrast",
                "label": contrast.name,
                "plus": list(contrast.plus),
                "minus": list(contrast.minus),
                "effect": effect,
                "raw_p": raw_p,
                "n_questions": len(ids),
            }
        )

    if tests:
        adjusted = _holm(raw_family)
        for item, holm_p in zip(tests, adjusted, strict=True):
            item["holm_p"] = holm_p

    decision = _decision(summaries, per_arm_accuracy, seed=seed, permutations=permutations)
    candidates = decision.get("set", []) if decision.get("status") in {"set", "winner"} else []
    if decision.get("status") == "set":
        tie_break: list[dict[str, Any]] = []
        for arm in candidates:
            summary = summaries[arm]
            secondary = summary.get("secondary") or {}
            tie_break.append(
                {
                    "arm": arm,
                    "supported_share": judges.get(arm),
                    "numeric_exactness": secondary.get("numeric_exactness"),
                    "citation_precision": secondary.get("citation_precision"),
                    "cost_per_correct_usd": secondary.get("cost_per_correct_usd"),
                }
            )
        ordered_tie = sorted(
            tie_break,
            key=lambda item: (
                1.0 if item["supported_share"] is None else -float(item["supported_share"]),
                1.0 if item["numeric_exactness"] is None else -float(item["numeric_exactness"]),
                1.0 if item["citation_precision"] is None else -float(item["citation_precision"]),
                math.inf
                if item["cost_per_correct_usd"] is None
                else float(item["cost_per_correct_usd"]),
                item["arm"],
            ),
        )
        decision["ordering"] = [item["arm"] for item in ordered_tie]
        if len(ordered_tie) >= 2 and (
            ordered_tie[0]["supported_share"],
            ordered_tie[0]["numeric_exactness"],
            ordered_tie[0]["citation_precision"],
            ordered_tie[0]["cost_per_correct_usd"],
        ) == (
            ordered_tie[1]["supported_share"],
            ordered_tie[1]["numeric_exactness"],
            ordered_tie[1]["citation_precision"],
            ordered_tie[1]["cost_per_correct_usd"],
        ):
            decision["status"] = "unresolved"
        elif ordered_tie:
            decision["recommended"] = ordered_tie[0]["arm"]
    if decision.get("status") == "winner":
        decision["recommended"] = decision.get("winner")

    question_rows: list[dict[str, Any]] = []
    if per_question:
        category_by_id: dict[str, str] = {}
        for arm in arms.values():
            _, categories, _ = _question_values(arm, abstention=abstention)
            category_by_id.update(categories)
        all_ids = sorted({qid for scores in per_arm_accuracy.values() for qid in scores})
        for qid in all_ids:
            row = {"id": qid, "category": category_by_id.get(qid, "")}
            for arm, scores in sorted(per_arm_accuracy.items()):
                row[arm] = round(float(scores[qid]), 6) if qid in scores else None
            question_rows.append(row)

    for name, summary in summaries.items():
        summary["judge_supported_share"] = judges.get(name)

    splits = sorted({summary["split"] for summary in summaries.values()})
    return {
        "format": COMPARE_FORMAT,
        "abstention_policy": abstention,
        "reference": reference,
        "seed": seed,
        "bootstrap_samples": bootstrap,
        "permutation_samples": permutations,
        "split": splits[0] if len(splits) == 1 else splits,
        "arms": summaries,
        "tests": tests,
        "decision": decision,
        "per_question": question_rows if per_question else None,
    }


def _render_markdown(report: Mapping[str, Any], *, per_question: bool) -> str:
    lines = ["# Knowledge-access comparison", ""]
    lines.append(f"- Reference arm: `{report['reference']}`")
    lines.append(f"- Abstention scoring: `{report['abstention_policy']}`")
    lines.append("")
    lines += [
        "| Arm | Primary accuracy (95% CI) | Majority | Excluded | Cost / correct (USD) |",
        "|---|---:|---:|---:|---:|",
    ]
    arms = report.get("arms") or {}
    for name in sorted(arms):
        summary = arms[name]
        primary = summary.get("primary") or {}
        secondary = summary.get("secondary") or {}
        ci = primary.get("ci95") or [math.nan, math.nan]
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{name}`",
                    (
                        f"{float(primary.get('mean_accuracy', 0.0)) * 100:.1f}% "
                        f"[{float(ci[0]) * 100:.1f}, {float(ci[1]) * 100:.1f}]"
                    ),
                    f"{float(secondary.get('majority_accuracy') or 0.0) * 100:.1f}%",
                    "yes" if summary.get("excluded") else "no",
                    "n/a"
                    if secondary.get("cost_per_correct_usd") is None
                    else f"${float(secondary['cost_per_correct_usd']):.4f}",
                ]
            )
            + " |"
        )
    lines += ["", "## Statistical tests", ""]
    lines += [
        "| Family | Contrast | Effect | p (raw) | p (Holm) | n questions |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for item in report.get("tests") or []:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(item.get("family") or ""),
                    str(item.get("label") or ""),
                    f"{float(item.get('effect') or 0.0):.4f}",
                    f"{float(item.get('raw_p') or 0.0):.4f}",
                    f"{float(item.get('holm_p') or 0.0):.4f}",
                    str(item.get("n_questions") or 0),
                ]
            )
            + " |"
        )
    decision = report.get("decision") or {}
    lines += ["", "## Decision", ""]
    lines.append(f"- Status: **{decision.get('status', 'unknown')}**")
    if decision.get("winner"):
        lines.append(f"- Winner: `{decision['winner']}`")
    if decision.get("set"):
        lines.append("- Set: " + ", ".join(f"`{name}`" for name in decision["set"]))
    if decision.get("recommended"):
        lines.append(f"- Recommended: `{decision['recommended']}`")
    if per_question and report.get("per_question"):
        rows = report["per_question"]
        headers = ["id", "category", *sorted((report.get("arms") or {}).keys())]
        lines += ["", "## Per-question mean accuracy", ""]
        lines.append("| " + " | ".join(headers) + " |")
        lines.append("|" + "---|" * len(headers))
        for row in rows:
            values = [str(row.get("id") or ""), str(row.get("category") or "")]
            for arm in headers[2:]:
                value = row.get(arm)
                values.append("–" if value is None else f"{float(value) * 100:.1f}%")
            lines.append("| " + " | ".join(values) + " |")
    lines.append("")
    return "\n".join(lines)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--arm", action="append", required=True, help="NAME=path[,path2,...]")
    parser.add_argument("--reference", required=True, help="reference arm name")
    parser.add_argument(
        "--judge",
        action="append",
        default=[],
        help="optional judge files per arm: NAME=path[,path2,...]",
    )
    parser.add_argument(
        "--contrast",
        action="append",
        default=[],
        help="optional contrast NAME=A+B-C-D",
    )
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--permutations", type=int, default=DEFAULT_PERMUTATIONS)
    parser.add_argument("--abstention", choices=ABSTENTION_VERSIONS, default="v1")
    parser.add_argument("--per-question", action="store_true", help="include per-question table")
    parser.add_argument("--out", type=Path, required=True, help="output JSON report file")
    parser.add_argument("--markdown", type=Path, help="optional markdown report path")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        arm_paths = expand_named_paths(args.arm, option="--arm")
        arms = load_arm_runs(arm_paths)
        judge_specs = expand_named_paths(args.judge, option="--judge") if args.judge else {}
        judges: dict[str, float | None] = {
            name: _load_judge_supported(paths) for name, paths in judge_specs.items()
        }
        contrasts = [parse_contrast(spec) for spec in args.contrast]
        report = build_report(
            arms,
            reference=args.reference,
            seed=args.seed,
            bootstrap=args.bootstrap,
            permutations=args.permutations,
            abstention=args.abstention,
            contrasts=contrasts,
            judges=judges,
            per_question=args.per_question,
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(_dumps(report), encoding="utf-8", newline="\n")
    if args.markdown is not None:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(
            _render_markdown(report, per_question=args.per_question),
            encoding="utf-8",
            newline="\n",
        )
    print(f"compare report: {args.out}")
    if args.markdown is not None:
        print(f"markdown: {args.markdown}")
    digest = hashlib.sha256(args.out.read_bytes()).hexdigest()[:12]
    print(f"report digest: {digest}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
