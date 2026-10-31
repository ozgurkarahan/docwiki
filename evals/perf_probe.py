"""Performance probe of a deployed DocWiki site (P0): page timings, live ask, run stages.

    uv run python evals/perf_probe.py --base-url https://<your-portal> [--path /pipeline ...] \
        [--repeat 3] [--ask "question"] [--run-report <run report.json>] [--json]

1. Every path is fetched ``--repeat`` times on a fresh connection: the first fetch is cold, the
   next ones are warm and revalidate with ``If-None-Match`` when the first one returned an ETag
   (a ``304`` proves the cache validator works). Reported: status, ``content-encoding``, bytes
   transferred on the wire (before decompression), time to the response headers (TTFB) and total
   time.
2. ``--ask`` posts one question to ``/api/ask`` like the Researcher drawer (JSON, same-origin
   ``Origin``), then reads ``/api/ask/{job_id}/events`` when the portal serves Server-Sent Events
   and otherwise polls ``GET /api/ask/{job_id}`` every ``--poll-interval`` seconds. Reported: time
   to ``202``, to the first progress event, and to the final answer. A live question spends model
   tokens on the deployment: ask one question, not a batch.
3. ``--run-report`` reads a pipeline run report (``RunReport`` JSON) and prints each stage's
   duration.

Only ``httpx`` and the standard library; no URL is built in. See ``docs/evaluation.md``.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

DEFAULT_PATHS = ("/", "/en/", "/pipeline", "/static/contentIndex.json")
"""Home, the English mirror's home, the pipeline page and Quartz's search/content index."""
DEFAULT_REPEAT = 3
DEFAULT_ACCEPT_ENCODING = "gzip, br"
DEFAULT_POLL_INTERVAL_S = 1.0
DEFAULT_ASK_TIMEOUT_S = 180.0
DEFAULT_TIMEOUT_S = 30.0
ASK_PATH = "/api/ask"
FINAL_STATES = frozenset({"done", "unverified", "error", "busy"})
"""Poll states that end a live question (see ``src/docwiki/portal/live_ask.py``)."""
FINAL_EVENTS = frozenset({"done", "answer", "final", "error", "end"})
PROGRESS_KEYS = ("progress", "stage", "step", "steps", "events", "tool_calls")
"""Poll payload keys that carry progress beyond a bare ``running`` status."""
JOB_ID = re.compile(r"^[0-9a-f]{32}$")
SSE_MISSING = frozenset({404, 405, 406, 501})

Clock = Callable[[], float]
Sleep = Callable[[float], None]


# ---------------------------------------------------------------------------- page timings


@dataclass
class Fetch:
    """One GET of one path."""

    status: int
    ttfb_s: float
    total_s: float
    bytes: int
    encoding: str | None
    etag: str | None
    redirects: int


@dataclass
class PathResult:
    path: str
    cold: Fetch
    warm: list[Fetch] = field(default_factory=list)

    def summary(self) -> dict[str, Any]:
        warm_ttfb = [f.ttfb_s for f in self.warm]
        warm_total = [f.total_s for f in self.warm]
        return {
            "path": self.path,
            "status": self.cold.status,
            "encoding": self.cold.encoding,
            "bytes": self.cold.bytes,
            "etag": self.cold.etag is not None,
            "redirects": self.cold.redirects,
            "cold_ttfb_s": self.cold.ttfb_s,
            "cold_total_s": self.cold.total_s,
            "warm_ttfb_p50_s": statistics.median(warm_ttfb) if warm_ttfb else None,
            "warm_total_p50_s": statistics.median(warm_total) if warm_total else None,
            "warm_statuses": [f.status for f in self.warm],
            "warm_bytes": [f.bytes for f in self.warm],
        }


def normalise_base_url(base_url: str) -> str:
    """``base_url`` without its trailing slash; only absolute http(s) URLs are accepted."""
    parts = urlsplit(base_url.strip())
    if parts.scheme not in ("http", "https") or not parts.netloc:
        raise ValueError(f"--base-url must be an absolute http(s) URL, got {base_url!r}")
    return f"{parts.scheme}://{parts.netloc}{parts.path.rstrip('/')}"


def _url(base_url: str, path: str) -> str:
    return base_url + (path if path.startswith("/") else f"/{path}")


def fetch(
    client: httpx.Client, url: str, headers: dict[str, str], clock: Clock = time.perf_counter
) -> Fetch:
    """GET ``url``: TTFB is the time to the response headers, bytes are counted before
    decompression (what travels on the wire)."""
    start = clock()
    with client.stream("GET", url, headers=headers) as response:
        ttfb = clock() - start
        if response.is_stream_consumed:  # an in-memory response: no wire bytes to count
            size = int(response.headers.get("content-length") or len(response.content))
        else:
            size = sum(len(chunk) for chunk in response.iter_raw())
        total = clock() - start
        return Fetch(
            status=response.status_code,
            ttfb_s=ttfb,
            total_s=total,
            bytes=size,
            encoding=response.headers.get("content-encoding"),
            etag=response.headers.get("etag"),
            redirects=len(response.history),
        )


def probe_path(
    base_url: str,
    path: str,
    repeat: int = DEFAULT_REPEAT,
    *,
    accept_encoding: str = DEFAULT_ACCEPT_ENCODING,
    revalidate: bool = True,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    transport: httpx.BaseTransport | None = None,
    clock: Clock = time.perf_counter,
) -> PathResult:
    """Fetch one path ``repeat`` times on its own (fresh, then kept-alive) connection."""
    headers = {"accept-encoding": accept_encoding}
    with httpx.Client(
        transport=transport, follow_redirects=True, timeout=timeout_s, headers=headers
    ) as client:
        url = _url(base_url, path)
        cold = fetch(client, url, {}, clock)
        result = PathResult(path, cold)
        for _ in range(max(0, repeat - 1)):
            extra = {"if-none-match": cold.etag} if revalidate and cold.etag else {}
            result.warm.append(fetch(client, url, extra, clock))
    return result


# ---------------------------------------------------------------------------- live ask


@dataclass
class AskResult:
    question: str
    status_code: int
    accepted_s: float
    job_id: str | None = None
    mode: str = "refused"
    """``sse``, ``poll`` or ``refused`` (the question was not accepted)."""
    first_progress_s: float | None = None
    first_status_s: float | None = None
    final_s: float | None = None
    final_status: str | None = None
    server_elapsed_s: float | None = None
    polls: int = 0
    events: int = 0
    citations: int | None = None
    steps: list[str] = field(default_factory=list)
    """Distinct progress steps seen (``step`` of the poll payload or of an event), in order."""
    message: str | None = None


def _payload(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def _finish(result: AskResult, payload: dict[str, Any], elapsed: float) -> None:
    result.final_s = elapsed
    result.final_status = str(payload.get("status") or result.final_status or "")
    server = payload.get("elapsed_s")
    if isinstance(server, int | float):
        result.server_elapsed_s = float(server)
    answer = payload.get("answer")
    if isinstance(answer, dict) and isinstance(answer.get("citations"), list):
        result.citations = len(answer["citations"])
    message = payload.get("message")
    if isinstance(message, str) and message.strip():
        result.message = message.strip()[:300]


def _note_step(result: AskResult, payload: dict[str, Any]) -> None:
    step = payload.get("step")
    if isinstance(step, str) and step and (not result.steps or result.steps[-1] != step):
        result.steps.append(step[:60])


def _sse_events(lines: Iterator[str]) -> Iterator[tuple[str, str]]:
    """``(event, data)`` pairs of a Server-Sent Events stream (``message`` by default)."""
    name, data = "message", []
    for line in lines:
        if not line:
            if data:
                yield name, "\n".join(data)
            name, data = "message", []
        elif line.startswith(":"):
            continue
        elif line.startswith("event:"):
            name = line[6:].strip() or "message"
        elif line.startswith("data:"):
            data.append(line[5:].removeprefix(" "))
    if data:
        yield name, "\n".join(data)


def _read_sse(
    client: httpx.Client, url: str, result: AskResult, start: float, clock: Clock
) -> bool | None:
    """Follow the job's event stream; ``None`` when the portal has none, else whether a final
    event arrived."""
    with client.stream("GET", url, headers={"accept": "text/event-stream"}) as response:
        kind = response.headers.get("content-type", "").split(";")[0].strip().lower()
        if response.status_code in SSE_MISSING or kind != "text/event-stream":
            return None
        if response.status_code != 200:
            result.message = f"event stream answered HTTP {response.status_code}"
            return False
        result.mode = "sse"
        for name, data in _sse_events(response.iter_lines()):
            now = clock() - start
            result.events += 1
            if result.first_progress_s is None:
                result.first_progress_s = now
            try:
                payload = json.loads(data)
            except ValueError:
                payload = None
            if not isinstance(payload, dict):
                payload = {}
            _note_step(result, payload)
            if result.first_status_s is None and "status" in payload:
                result.first_status_s = now
            if name in FINAL_EVENTS or payload.get("status") in FINAL_STATES:
                if "status" not in payload:
                    result.final_status = name
                _finish(result, payload, now)
                return True
    return False


def _poll(
    client: httpx.Client,
    url: str,
    result: AskResult,
    start: float,
    *,
    interval_s: float,
    timeout_s: float,
    clock: Clock,
    sleep: Sleep,
) -> None:
    if result.mode != "sse":
        result.mode = "poll"
    while clock() - start < timeout_s:
        response = client.get(url, headers={"accept": "application/json"})
        now = clock() - start
        result.polls += 1
        if response.status_code == 404:
            result.final_status = "expired"
            result.final_s = now
            return
        payload = _payload(response)
        if response.status_code == 200 and isinstance(payload, dict):
            if result.first_status_s is None:
                result.first_status_s = now
            _note_step(result, payload)
            if result.first_progress_s is None and any(k in payload for k in PROGRESS_KEYS):
                result.first_progress_s = now
            if payload.get("status") in FINAL_STATES:
                _finish(result, payload, now)
                return
        sleep(interval_s)
    result.final_status = "timeout"
    result.message = f"no final answer within {timeout_s:g} s"


def probe_ask(
    base_url: str,
    question: str,
    *,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    timeout_s: float = DEFAULT_ASK_TIMEOUT_S,
    request_timeout_s: float = DEFAULT_TIMEOUT_S,
    use_sse: bool = True,
    transport: httpx.BaseTransport | None = None,
    clock: Clock = time.perf_counter,
    sleep: Sleep = time.sleep,
) -> AskResult:
    """Ask one live question the way the drawer does and time its life cycle."""
    parts = urlsplit(base_url)
    origin = f"{parts.scheme}://{parts.netloc}"
    with httpx.Client(transport=transport, timeout=request_timeout_s) as client:
        start = clock()
        response = client.post(
            _url(base_url, ASK_PATH),
            json={"question": question},
            headers={"origin": origin, "accept": "application/json"},
        )
        result = AskResult(question, response.status_code, clock() - start)
        payload = _payload(response)
        if response.status_code != 202:
            if isinstance(payload, dict) and isinstance(payload.get("message"), str):
                result.message = payload["message"][:300]
            return result
        job_id = payload.get("job_id") if isinstance(payload, dict) else None
        if not isinstance(job_id, str) or not JOB_ID.match(job_id):
            result.message = "the portal accepted the question without a valid job id"
            return result
        result.job_id = job_id
        job_url = _url(base_url, f"{ASK_PATH}/{job_id}")
        if use_sse and _read_sse(client, f"{job_url}/events", result, start, clock):
            return result
        _poll(
            client,
            job_url,
            result,
            start,
            interval_s=poll_interval_s,
            timeout_s=timeout_s,
            clock=clock,
            sleep=sleep,
        )
        return result


# ---------------------------------------------------------------------------- run report


def read_run_report(path: Path) -> dict[str, Any]:
    """Run id, status, total duration and the stages (duration and share) of a run report."""
    report = json.loads(path.read_text(encoding="utf-8"))
    stages = report.get("stages") if isinstance(report, dict) else None
    if not isinstance(stages, list):
        raise ValueError(f"{path} is not a pipeline run report: no 'stages' list")
    rows = [
        {
            "stage": str(stage.get("stage", "?")),
            "status": str(stage.get("status", "?")),
            "duration_s": float(stage.get("duration_s") or 0.0),
            "items": int(stage.get("items") or 0),
            "cache_hits": int(stage.get("cache_hits") or 0),
            "failures": int(stage.get("failures") or 0),
            "llm_calls": int(stage.get("llm_calls") or 0),
            "cost": stage.get("cost"),
        }
        for stage in stages
        if isinstance(stage, dict)
    ]
    stage_total = sum(row["duration_s"] for row in rows)
    cost = report.get("cost") if isinstance(report.get("cost"), dict) else {}
    total = float(cost.get("duration_s") or 0.0) or stage_total
    for row in rows:
        row["share"] = row["duration_s"] / stage_total if stage_total else None
    return {
        "run_id": report.get("run_id"),
        "kind": report.get("kind"),
        "status": report.get("status"),
        "started_at": report.get("started_at"),
        "finished_at": report.get("finished_at"),
        "duration_s": total,
        "stages_duration_s": stage_total,
        "stages": rows,
    }


# ---------------------------------------------------------------------------- output


def _ms(seconds: float | None) -> str:
    return "-" if seconds is None else f"{seconds * 1000:.0f}"


def _s(seconds: float | None) -> str:
    return "-" if seconds is None else f"{seconds:.1f}"


def _statuses(values: Sequence[int]) -> str:
    if not values:
        return "-"
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return ", ".join(f"{status} x{n}" for status, n in sorted(counts.items()))


def render_markdown(
    paths: Sequence[PathResult], ask: AskResult | None, run: dict[str, Any] | None
) -> str:
    out: list[str] = []
    if paths:
        out += [
            "### Pages",
            "",
            "| Path | Status | Encoding | Bytes | ETag | Cold TTFB (ms) | Cold total (ms) "
            "| Warm TTFB p50 (ms) | Warm total p50 (ms) | Warm statuses |",
            "|---|---|---|---:|---|---:|---:|---:|---:|---|",
        ]
        for result in paths:
            s = result.summary()
            redirect = f" ({s['redirects']} redirect)" if s["redirects"] else ""
            out.append(
                f"| `{s['path']}` | {s['status']}{redirect} | {s['encoding'] or 'identity'} "
                f"| {s['bytes']} | {'yes' if s['etag'] else 'no'} | {_ms(s['cold_ttfb_s'])} "
                f"| {_ms(s['cold_total_s'])} | {_ms(s['warm_ttfb_p50_s'])} "
                f"| {_ms(s['warm_total_p50_s'])} | {_statuses(s['warm_statuses'])} |"
            )
        out.append("")
    if ask is not None:
        out += [
            "### Live ask",
            "",
            "| HTTP | Mode | To 202 (s) | First status (s) | First progress (s) | Final (s) "
            "| Final status | Server elapsed (s) | Polls | Events | Citations |",
            "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|",
            f"| {ask.status_code} | {ask.mode} | {_s(ask.accepted_s)} | {_s(ask.first_status_s)} "
            f"| {_s(ask.first_progress_s)} | {_s(ask.final_s)} | {ask.final_status or '-'} "
            f"| {_s(ask.server_elapsed_s)} | {ask.polls} | {ask.events} "
            f"| {'-' if ask.citations is None else ask.citations} |",
            "",
        ]
        if ask.steps:
            out += [f"Steps: {' > '.join(ask.steps)}", ""]
        if ask.message:
            out += [f"Message: {ask.message}", ""]
    if run is not None:
        out += [
            f"### Run `{run['run_id']}` ({run['kind']}, {run['status']}): "
            f"{run['duration_s']:.1f} s",
            "",
            "| Stage | Status | Duration (s) | Share | Items | Cache hits | Failures | LLM calls |",
            "|---|---|---:|---:|---:|---:|---:|---:|",
        ]
        for row in run["stages"]:
            share = "-" if row["share"] is None else f"{row['share'] * 100:.0f} %"
            out.append(
                f"| {row['stage']} | {row['status']} | {row['duration_s']:.1f} | {share} "
                f"| {row['items']} | {row['cache_hits']} | {row['failures']} | {row['llm_calls']} |"
            )
        out += [f"| **total** | | {run['stages_duration_s']:.1f} | | | | | |", ""]
    return "\n".join(out).rstrip() + "\n"


def to_json(paths: Sequence[PathResult], ask: AskResult | None, run: dict[str, Any] | None) -> str:
    payload: dict[str, Any] = {
        "paths": [
            {**r.summary(), "cold": asdict(r.cold), "warm": [asdict(f) for f in r.warm]}
            for r in paths
        ],
        "ask": asdict(ask) if ask is not None else None,
        "run_report": run,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


# ---------------------------------------------------------------------------- command line


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="perf_probe", description="Time a deployed DocWiki site (pages, live ask, run)."
    )
    parser.add_argument("--base-url", help="site root, e.g. https://<your-portal>")
    parser.add_argument(
        "--path",
        action="append",
        dest="paths",
        help=f"path to time (repeatable; default: {' '.join(DEFAULT_PATHS)})",
    )
    parser.add_argument("--no-paths", action="store_true", help="skip the page timings")
    parser.add_argument("--repeat", type=int, default=DEFAULT_REPEAT, help="fetches per path")
    parser.add_argument(
        "--no-revalidate", action="store_true", help="warm fetches without If-None-Match"
    )
    parser.add_argument("--accept-encoding", default=DEFAULT_ACCEPT_ENCODING)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_S, help="per request (s)")
    parser.add_argument("--ask", metavar="QUESTION", help="also ask one live question")
    parser.add_argument("--poll-interval", type=float, default=DEFAULT_POLL_INTERVAL_S)
    parser.add_argument("--ask-timeout", type=float, default=DEFAULT_ASK_TIMEOUT_S)
    parser.add_argument("--no-sse", action="store_true", help="poll even when SSE is served")
    parser.add_argument("--run-report", type=Path, help="local pipeline run report (JSON)")
    parser.add_argument("--json", action="store_true", help="print JSON instead of Markdown")
    return parser


def main(argv: Sequence[str] | None = None, *, transport: httpx.BaseTransport | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if not args.base_url and (args.ask or args.run_report is None):
        parser.error("--base-url is required (unless only --run-report is given)")
    if args.repeat < 1:
        parser.error("--repeat must be at least 1")
    base_url = ""
    if args.base_url:
        try:
            base_url = normalise_base_url(args.base_url)
        except ValueError as error:
            parser.error(str(error))
    paths: list[PathResult] = []
    ask: AskResult | None = None
    run: dict[str, Any] | None = None
    try:
        if base_url and not args.no_paths:
            for path in args.paths or DEFAULT_PATHS:
                paths.append(
                    probe_path(
                        base_url,
                        path,
                        args.repeat,
                        accept_encoding=args.accept_encoding,
                        revalidate=not args.no_revalidate,
                        timeout_s=args.timeout,
                        transport=transport,
                    )
                )
        if base_url and args.ask:
            ask = probe_ask(
                base_url,
                args.ask,
                poll_interval_s=args.poll_interval,
                timeout_s=args.ask_timeout,
                request_timeout_s=args.timeout,
                use_sse=not args.no_sse,
                transport=transport,
            )
        if args.run_report is not None:
            run = read_run_report(args.run_report)
    except (httpx.HTTPError, OSError, ValueError) as error:
        print(f"perf_probe: {error}", file=sys.stderr)
        return 1
    sys.stdout.write(to_json(paths, ask, run) if args.json else render_markdown(paths, ask, run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
