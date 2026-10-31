"""Performance probe: page timings, live ask (SSE and polling), run report stages. No network:
every request goes to an ``httpx.MockTransport`` stub of the portal."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from evals.perf_probe import (
    DEFAULT_PATHS,
    main,
    normalise_base_url,
    probe_ask,
    probe_path,
    read_run_report,
    render_markdown,
)

BASE = "https://wiki.example"
JOB = "0123456789abcdef0123456789abcdef"
PAGE = b"<html>" + b"x" * 4000 + b"</html>"


class WireStream(httpx.SyncByteStream):
    """Bytes streamed like a network transport (``content=`` would be read up front)."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def __iter__(self) -> Iterator[bytes]:
        yield self.data[: len(self.data) // 2]
        yield self.data[len(self.data) // 2 :]


class FakeClock:
    """Advances by ``step`` seconds per reading; ``sleep`` advances it too."""

    def __init__(self, step: float = 0.01) -> None:
        self.now = 0.0
        self.step = step

    def __call__(self) -> float:
        self.now += self.step
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


class Portal:
    """A stub of the portal: static pages with ETags, gzip, the live ask API."""

    def __init__(
        self,
        *,
        sse: bool = False,
        running_polls: int = 2,
        accept: int = 202,
        steps: tuple[str, ...] = (),
    ) -> None:
        self.sse = sse
        self.running_polls = running_polls
        self.accept = accept
        self.steps = steps
        self.requests: list[httpx.Request] = []
        self.polls = 0

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if path == "/api/ask" and request.method == "POST":
            if self.accept != 202:
                return httpx.Response(self.accept, json={"message": "Too many questions."})
            return httpx.Response(202, json={"job_id": JOB})
        if path == f"/api/ask/{JOB}/events":
            if not self.sse:
                return httpx.Response(404, text="Not found")
            stream = (
                'event: progress\ndata: {"status": "running", "step": "answer_context"}\n\n'
                ": keep-alive\n\n"
                'event: done\ndata: {"status": "done", "elapsed_s": 12.5, '
                '"answer": {"citations": [1, 2]}}\n\n'
            )
            return httpx.Response(
                200, headers={"content-type": "text/event-stream"}, content=stream.encode()
            )
        if path == f"/api/ask/{JOB}":
            self.polls += 1
            if self.polls <= self.running_polls:
                payload: dict[str, Any] = {"status": "running", "elapsed_s": self.polls}
                if self.polls <= len(self.steps):
                    payload["step"] = self.steps[self.polls - 1]
                return httpx.Response(200, json=payload)
            return httpx.Response(
                200,
                json={"status": "done", "elapsed_s": 9.0, "answer": {"citations": [{}, {}, {}]}},
            )
        if path == "/":
            return httpx.Response(302, headers={"location": "/en/"})
        if path in ("/en/", "/pipeline", "/static/contentIndex.json"):
            etag = f'"{abs(hash(path))}"'
            if request.headers.get("if-none-match") == etag:
                return httpx.Response(304, headers={"etag": etag})
            accepts_gzip = "gzip" in request.headers.get("accept-encoding", "")
            body = gzip.compress(PAGE) if accepts_gzip else PAGE
            headers = {"etag": etag, "content-type": "text/html"}
            if accepts_gzip:
                headers["content-encoding"] = "gzip"
            return httpx.Response(200, headers=headers, stream=WireStream(body))
        return httpx.Response(404, text="Not found")


def test_base_url_is_validated_and_normalised() -> None:
    assert normalise_base_url(f"{BASE}/") == BASE
    with pytest.raises(ValueError):
        normalise_base_url("wiki.example")


def test_cold_then_warm_revalidation_counts_wire_bytes() -> None:
    portal = Portal()
    result = probe_path(
        BASE, "/pipeline", 3, transport=httpx.MockTransport(portal), clock=FakeClock()
    )
    assert result.cold.status == 200
    assert result.cold.encoding == "gzip"
    assert result.cold.bytes == len(gzip.compress(PAGE)) < len(PAGE)
    assert result.cold.etag is not None
    assert [f.status for f in result.warm] == [304, 304]
    assert all(f.bytes == 0 for f in result.warm)
    assert portal.requests[1].headers["if-none-match"] == result.cold.etag
    assert 0 < result.cold.ttfb_s <= result.cold.total_s
    summary = result.summary()
    assert summary["warm_statuses"] == [304, 304]
    assert summary["warm_ttfb_p50_s"] is not None


def test_no_revalidate_and_identity_encoding() -> None:
    portal = Portal()
    result = probe_path(
        BASE,
        "/en/",
        2,
        accept_encoding="identity",
        revalidate=False,
        transport=httpx.MockTransport(portal),
    )
    assert result.cold.encoding is None
    assert result.cold.bytes == len(PAGE)
    assert [f.status for f in result.warm] == [200]
    assert "if-none-match" not in portal.requests[1].headers


def test_redirects_are_followed_and_counted() -> None:
    result = probe_path(BASE, "/", 1, transport=httpx.MockTransport(Portal()))
    assert result.cold.status == 200
    assert result.cold.redirects == 1
    assert result.warm == []


def test_ask_falls_back_to_polling_without_event_stream() -> None:
    portal = Portal(running_polls=2)
    clock = FakeClock()
    result = probe_ask(
        BASE,
        "When are the windows delivered?",
        poll_interval_s=1.0,
        transport=httpx.MockTransport(portal),
        clock=clock,
        sleep=clock.sleep,
    )
    post = portal.requests[0]
    assert post.method == "POST"
    assert post.headers["content-type"] == "application/json"
    assert post.headers["origin"] == BASE
    assert json.loads(post.content) == {"question": "When are the windows delivered?"}
    assert result.status_code == 202
    assert result.job_id == JOB
    assert result.mode == "poll"
    assert result.polls == 3
    assert result.final_status == "done"
    assert result.server_elapsed_s == 9.0
    assert result.citations == 3
    assert result.first_progress_s is None
    assert result.first_status_s is not None
    assert result.final_s is not None and result.final_s >= 2.0
    assert result.accepted_s < result.first_status_s <= result.final_s


def test_ask_polled_steps_mark_the_first_progress() -> None:
    portal = Portal(running_polls=4, steps=("tool:answer_context", "tool:read_page", "writing"))
    clock = FakeClock()
    result = probe_ask(
        BASE,
        "q?",
        poll_interval_s=1.0,
        transport=httpx.MockTransport(portal),
        clock=clock,
        sleep=clock.sleep,
    )
    assert result.mode == "poll"
    assert result.steps == ["tool:answer_context", "tool:read_page", "writing"]
    assert result.first_progress_s == result.first_status_s
    assert "Steps: tool:answer_context > tool:read_page > writing" in render_markdown(
        [], result, None
    )


def test_ask_reads_the_event_stream_when_served() -> None:
    portal = Portal(sse=True)
    result = probe_ask(
        BASE,
        "Quand les fenêtres sont-elles livrées ?",
        transport=httpx.MockTransport(portal),
        clock=FakeClock(),
    )
    assert result.mode == "sse"
    assert result.events == 2
    assert result.first_progress_s is not None
    assert result.final_status == "done"
    assert result.citations == 2
    assert result.server_elapsed_s == 12.5
    assert result.polls == 0
    assert result.steps == ["answer_context"]
    assert portal.requests[1].headers["accept"] == "text/event-stream"


def test_ask_refused_reports_the_message() -> None:
    result = probe_ask(BASE, "q?", transport=httpx.MockTransport(Portal(accept=429)))
    assert result.status_code == 429
    assert result.mode == "refused"
    assert result.message == "Too many questions."
    assert result.job_id is None


def test_ask_times_out() -> None:
    clock = FakeClock()
    result = probe_ask(
        BASE,
        "q?",
        poll_interval_s=1.0,
        timeout_s=3.0,
        transport=httpx.MockTransport(Portal(running_polls=99)),
        clock=clock,
        sleep=clock.sleep,
    )
    assert result.final_status == "timeout"
    assert result.final_s is None
    assert 1 <= result.polls <= 4


def _run_report(tmp_path: Path) -> Path:
    report: dict[str, Any] = {
        "schema": 1,
        "run_id": "run-20260412-0001",
        "kind": "ingest",
        "status": "succeeded",
        "started_at": "2026-04-12T08:00:00Z",
        "finished_at": "2026-04-12T08:05:00Z",
        "stages": [
            {
                "stage": "extract",
                "status": "done",
                "duration_s": 60.0,
                "items": 39,
                "cache_hits": 30,
                "llm_calls": 0,
            },
            {
                "stage": "compile",
                "status": "done",
                "duration_s": 180.0,
                "items": 9,
                "llm_calls": 42,
                "cost": 0.8,
            },
            {"stage": "publish", "status": "done", "duration_s": 60.0},
        ],
        "cost": {"price_table": "prices.yaml", "duration_s": 310.0},
    }
    path = tmp_path / "run.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_run_report_stage_durations(tmp_path: Path) -> None:
    run = read_run_report(_run_report(tmp_path))
    assert run["duration_s"] == 310.0
    assert run["stages_duration_s"] == 300.0
    compile_stage = run["stages"][1]
    assert compile_stage["stage"] == "compile"
    assert compile_stage["share"] == pytest.approx(0.6)
    assert compile_stage["llm_calls"] == 42
    text = render_markdown([], None, run)
    assert "| compile | done | 180.0 | 60 % | 9 | 0 | 0 | 42 |" in text
    assert "| **total** | | 300.0 |" in text


def test_run_report_rejects_other_json(tmp_path: Path) -> None:
    path = tmp_path / "other.json"
    path.write_text('{"hello": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="stages"):
        read_run_report(path)


def test_main_markdown_and_json(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    transport = httpx.MockTransport(Portal())
    assert (
        main(
            [
                "--base-url",
                BASE,
                "--repeat",
                "2",
                "--ask",
                "q?",
                "--poll-interval",
                "0",
                "--run-report",
                str(_run_report(tmp_path)),
            ],
            transport=transport,
        )
        == 0
    )
    text = capsys.readouterr().out
    for path in DEFAULT_PATHS:
        assert f"| `{path}` |" in text
    assert "### Live ask" in text and "| 202 | poll |" in text
    assert "### Run `run-20260412-0001`" in text

    assert main(["--base-url", BASE, "--path", "/pipeline", "--json"], transport=transport) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [p["path"] for p in payload["paths"]] == ["/pipeline"]
    assert payload["paths"][0]["warm_statuses"] == [304, 304]
    assert payload["ask"] is None and payload["run_report"] is None


def test_main_requires_a_base_url_unless_run_report_only(tmp_path: Path) -> None:
    with pytest.raises(SystemExit):
        main([])
    with pytest.raises(SystemExit):
        main(["--base-url", "not-a-url"])
    assert main(["--run-report", str(_run_report(tmp_path))]) == 0


def test_main_reports_transport_errors(capsys: pytest.CaptureFixture[str]) -> None:
    def broken(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    assert main(["--base-url", BASE], transport=httpx.MockTransport(broken)) == 1
    assert "perf_probe:" in capsys.readouterr().err
