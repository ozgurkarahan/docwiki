"""Live "Ask this wiki" (ADR 0008): the gate, the converter, the guards and the routes.

No test reaches a model or the network: the agent is a fake that returns scripted answers.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from starlette.testclient import TestClient

from docwiki.agents_client.citations import parse_answer
from docwiki.agents_client.client import AgentAnswer, AgentUsage, ToolCall
from docwiki.agents_client.errors import AgentInvocationError
from docwiki.portal import create_app
from docwiki.portal.live_ask import (
    BUSY_MESSAGE,
    FAILED_MESSAGE,
    LIVE_BANNER,
    UNVERIFIED_MESSAGE,
    LiveAsk,
    LiveAskRefused,
    LiveAskSettings,
    live_answer,
)

SID_A = "src-165f1d3a109c"
SID_B = "src-86eabe3d6d0d"
QUESTION = "When are the windows of the extension delivered?"
TODAY = date(2026, 10, 21)
LISTING = (
    "Sources:\n"
    f"[1] Site meeting minutes n°3 — ¶ 7 (native-text) — evidence/{SID_A}/para-0007.md\n"
    f'[2] Planning, indice B — sheet "Planning", rows 6–9 (deterministic-table) — '
    f"evidence/{SID_B}/sheet-planning-r0006-r0009.md"
)
GOOD_TEXT = (
    "The walls of the extension are **70 % complete** [1]. Task T05 is listed at 100 % [2].\n\n"
    + LISTING
)


def agent_answer(text: str, *, tool_calls: list[ToolCall] | None = None) -> AgentAnswer:
    return AgentAnswer(
        text=text,
        sources=parse_answer(text),
        tool_calls=tool_calls or [],
        usage=AgentUsage(total_tokens=1200),
        agent="docwiki-researcher",
        version="7",
        latency_s=31.0,
    )


@pytest.fixture
def site(tmp_path: Path) -> Path:
    root = tmp_path / "site"
    for sid, key in ((SID_A, "para-0007"), (SID_B, "sheet-planning-r0006-r0009")):
        page = root / "evidence" / sid / f"{key}.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text("<!DOCTYPE html><title>evidence</title>", encoding="utf-8")
    (root / "index.html").write_text("<!DOCTYPE html><title>home</title>", encoding="utf-8")
    return root


def gate(text: str, site: Path | None) -> tuple[str, dict[str, Any], str | None]:
    return live_answer(
        agent_answer(text), question=QUESTION, job_id="job1", site_root=site, today=TODAY
    )


# ---------------------------------------------------------------------- converter


def test_a_checked_answer_has_the_drawer_shape(site: Path) -> None:
    calls = [ToolCall(name="search", arguments={"query": "window delivery"}, status="completed")]
    status, item, message = live_answer(
        agent_answer(GOOD_TEXT, tool_calls=calls),
        question=QUESTION,
        job_id="job1",
        site_root=site,
        today=TODAY,
    )
    assert (status, message) == ("done", None)
    assert item["id"] == "live:job1"
    assert item["slug"] == "index"
    assert item["live"] is True
    assert item["question"] == QUESTION and item["date"] == "2026-10-21"
    assert item["banners"] == [LIVE_BANNER]
    assert item["paragraphs"] == [
        [
            {"text": "The walls of the extension are 70 % complete"},
            {"cite": 1},
            {"text": ". Task T05 is listed at 100 %"},
            {"cite": 2},
            {"text": "."},
        ]
    ]
    assert item["citations"] == [
        {
            "n": 1,
            "title": "Site meeting minutes n°3",
            "label": "¶ 7",
            "href": f"evidence/{SID_A}/para-0007",
            "badge": "paraphrase",  # the live quote is not verified: never "quote verified"
        },
        {
            "n": 2,
            "title": "Planning, indice B",
            "label": 'sheet "Planning", rows 6–9',
            "href": f"evidence/{SID_B}/sheet-planning-r0006-r0009",
            "badge": "table",
        },
    ]
    assert item["steps"] == ["search `window delivery`"]
    assert "docwiki-researcher version 7" in item["provenance"]
    assert item["pages"] == []


def test_sources_that_are_listed_but_not_cited_are_left_out(site: Path) -> None:
    text = f"The walls are 70 % complete [1].\n\n{LISTING}"
    status, item, _ = gate(text, site)
    assert status == "done"
    assert [citation["n"] for citation in item["citations"]] == [1]


@pytest.mark.parametrize(
    ("name", "text"),
    [
        ("missing from the list", f"Walls [1]. Windows [3].\n\n{LISTING}"),
        ("no source list", "The walls are 70 % complete [1]."),
        (
            "page not in the site",
            "Walls [1].\n\nSources:\n[1] Minutes — ¶ 9 (native-text) — "
            f"evidence/{SID_A}/para-0009.md",
        ),
        (
            "unknown source",
            "Walls [1].\n\nSources:\n[1] Minutes — ¶ 7 (native-text) — "
            "evidence/src-000000000000/para-0007.md",
        ),
        (
            "not an evidence path",
            "Walls [1].\n\nSources:\n[1] Home — page (native-text) — queries/index.md",
        ),
        (
            "path outside the site",
            "Walls [1].\n\nSources:\n[1] Home — page (native-text) — ../../etc/passwd.md",
        ),
        ("source without a path", "Walls [1].\n\nSources:\n[1] Site meeting minutes — ¶ 7"),
        ("uncited text", "The walls are 70 % complete."),
    ],
)
def test_an_answer_that_cannot_be_checked_is_unverified(name: str, text: str, site: Path) -> None:
    status, item, message = gate(text, site)
    assert status == "unverified", name
    assert message == UNVERIFIED_MESSAGE
    assert item["citations"] == []
    assert item["banners"] == [LIVE_BANNER]
    flat = [segment for paragraph in item["paragraphs"] for segment in paragraph]
    assert flat and all("cite" not in segment for segment in flat)
    assert "[" not in "".join(segment["text"] for segment in flat)


def test_one_bad_citation_makes_the_whole_answer_unverified(site: Path) -> None:
    (site / "evidence" / SID_B / "sheet-planning-r0006-r0009.html").unlink()
    status, item, _ = gate(GOOD_TEXT, site)
    assert status == "unverified" and item["citations"] == []


def test_without_a_site_nothing_is_verified() -> None:
    assert gate(GOOD_TEXT, None)[0] == "unverified"


def test_an_honest_abstention_needs_no_citation(site: Path) -> None:
    status, item, message = gate("Not found in the wiki.", site)
    assert (status, message) == ("done", None)
    assert item["citations"] == []
    assert item["paragraphs"] == [[{"text": "Not found in the wiki."}]]


def test_unsafe_markup_in_the_answer_is_neutralised(site: Path) -> None:
    text = (
        "Walls [1]. <script>alert(1)</script> See [more](https://example.org/x) and "
        f"https://example.org/y.\n\n{LISTING}"
    )
    _, item, _ = gate(text, site)
    plain = "".join(
        segment.get("text", "") for paragraph in item["paragraphs"] for segment in paragraph
    )
    assert "<script" not in plain and "example.org/x" not in plain


def test_an_empty_answer_is_an_error(site: Path) -> None:
    assert gate("   ", site)[0] == "error"


# ---------------------------------------------------------------------- the service


class FakeAsker:
    """Scripted outcomes (an answer or an exception), optionally held until released."""

    def __init__(self, *outcomes: AgentAnswer | BaseException, hold: bool = False) -> None:
        self.outcomes = list(outcomes)
        self.calls: list[tuple[str, str, dict[str, str] | None]] = []
        self.release = asyncio.Event() if hold else None
        self.closed = False

    async def ask(
        self, question: str, *, agent: str = "researcher", headers: Any = None
    ) -> AgentAnswer:
        self.calls.append((question, agent, dict(headers) if headers else None))
        if self.release is not None:
            await self.release.wait()
        outcome = self.outcomes.pop(0) if self.outcomes else agent_answer(GOOD_TEXT)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def aclose(self) -> None:
        self.closed = True


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def service(
    asker: FakeAsker,
    site: Path | None = None,
    clock: Clock | None = None,
    **limits: Any,
) -> LiveAsk:
    return LiveAsk(
        LiveAskSettings(**limits),
        lambda: asker,
        site_root=lambda: site,
        clock=clock or time.monotonic,
        today=lambda: TODAY,
    )


async def finished(live: LiveAsk, job_id: str) -> dict[str, Any]:
    for _ in range(200):
        view = live.view(job_id)
        assert view is not None
        if view["status"] != "running":
            return view
        await asyncio.sleep(0.005)
    raise AssertionError("the job did not finish")


async def test_a_question_runs_the_researcher_with_the_visitor_header(site: Path) -> None:
    asker = FakeAsker()
    live = service(asker, site)
    job = live.start(f"  {QUESTION}  ", "203.0.113.9")
    view = await finished(live, job.id)
    assert view["status"] == "done" and view["answer"]["citations"]
    assert "message" not in view
    assert asker.calls == [(QUESTION, "researcher", {"X-Visitor-IP": "203.0.113.9"})]


@pytest.mark.parametrize("question", ["", "  ", "ab", "  a  "])
async def test_a_question_shorter_than_three_characters_is_refused(question: str) -> None:
    live = service(FakeAsker())
    with pytest.raises(LiveAskRefused) as refused:
        live.start(question, "198.51.100.1")
    assert refused.value.status_code == 400


async def test_the_question_length_limits_count_after_stripping() -> None:
    live = service(FakeAsker(), questions_per_ip=10)
    live.start("abc", "198.51.100.1")
    live.start(" " + "x" * 500 + " ", "198.51.100.2")
    with pytest.raises(LiveAskRefused) as refused:
        live.start("x" * 501, "198.51.100.3")
    assert refused.value.status_code == 400 and "500" in refused.value.message


async def test_one_running_question_per_visitor() -> None:
    asker = FakeAsker(hold=True)
    live = service(asker)
    live.start(QUESTION, "198.51.100.1")
    with pytest.raises(LiveAskRefused) as refused:
        live.start(QUESTION, "198.51.100.1")
    assert refused.value.status_code == 429
    live.start(QUESTION, "198.51.100.2")  # another visitor is fine
    assert asker.release is not None
    asker.release.set()
    await live.aclose()


async def test_at_most_three_questions_run_in_total() -> None:
    asker = FakeAsker(hold=True)
    live = service(asker)
    for index in range(3):
        live.start(QUESTION, f"198.51.100.{index}")
    with pytest.raises(LiveAskRefused) as refused:
        live.start(QUESTION, "198.51.100.9")
    assert refused.value.status_code == 429 and "busy" in refused.value.message
    assert asker.release is not None
    asker.release.set()
    await live.aclose()


async def test_questions_per_visitor_are_counted_per_window() -> None:
    clock = Clock()
    live = service(FakeAsker(), clock=clock)
    for _ in range(3):
        job = live.start(QUESTION, "198.51.100.1")
        await finished(live, job.id)
    with pytest.raises(LiveAskRefused) as refused:
        live.start(QUESTION, "198.51.100.1")
    assert refused.value.status_code == 429
    assert "3 questions every 5 minutes" in refused.value.message
    live.start(QUESTION, "198.51.100.2")  # the limit is per visitor
    clock.now += 301
    job = live.start(QUESTION, "198.51.100.1")
    await finished(live, job.id)


async def test_a_finished_job_expires_after_fifteen_minutes(site: Path) -> None:
    clock = Clock()
    live = service(FakeAsker(), site, clock=clock)
    job = live.start(QUESTION, "198.51.100.1")
    await finished(live, job.id)
    clock.now += 899
    assert live.view(job.id) is not None
    clock.now += 2
    assert live.view(job.id) is None


async def test_the_gateway_limit_is_a_busy_status_without_exception_text(
    caplog: pytest.LogCaptureFixture,
) -> None:
    secret = "HTTP 429 (TooManyRequests) from https://gateway.internal.example/ai"
    live = service(FakeAsker(AgentInvocationError(secret, status_code=429)))
    with caplog.at_level(logging.INFO, logger="docwiki.portal.live_ask"):
        job = live.start(QUESTION, "198.51.100.1")
        view = await finished(live, job.id)
    assert view["status"] == "busy" and view["message"] == BUSY_MESSAGE
    assert "answer" not in view
    assert secret not in str(view)
    assert secret in caplog.text  # logged for the operator


@pytest.mark.parametrize(
    "error",
    [
        AgentInvocationError("HTTP 500 (server_error) at https://gateway.internal.example"),
        AgentInvocationError("not allowed", status_code=401),
        RuntimeError("boom with a private path"),
    ],
)
async def test_other_errors_get_a_generic_message(error: Exception) -> None:
    live = service(FakeAsker(error))
    job = live.start(QUESTION, "198.51.100.1")
    view = await finished(live, job.id)
    assert view["status"] == "error" and view["message"] == FAILED_MESSAGE
    assert str(error) not in str(view)


async def test_a_question_that_takes_too_long_is_stopped() -> None:
    live = service(FakeAsker(hold=True), timeout_s=0.05)
    job = live.start(QUESTION, "198.51.100.1")
    view = await finished(live, job.id)
    assert view["status"] == "error" and "too long" in view["message"]


async def test_an_unverified_answer_carries_its_message() -> None:
    live = service(FakeAsker(), None)  # no site: nothing can be checked
    job = live.start(QUESTION, "198.51.100.1")
    view = await finished(live, job.id)
    assert view["status"] == "unverified" and view["message"] == UNVERIFIED_MESSAGE
    assert view["answer"]["citations"] == [] and view["answer"]["live"] is True


async def test_the_question_is_not_logged_above_debug_and_visitors_are_hashed(
    site: Path, caplog: pytest.LogCaptureFixture
) -> None:
    live = service(FakeAsker(), site)
    private = "Does Mrs Ancelin at 12 rue Imaginaire owe us anything?"
    with caplog.at_level(logging.INFO, logger="docwiki.portal.live_ask"):
        job = live.start(private, "203.0.113.77")
        await finished(live, job.id)
    assert "live_ask.start" in caplog.text and "live_ask.finish" in caplog.text
    assert "Ancelin" not in caplog.text and "203.0.113.77" not in caplog.text
    assert live.hashed("203.0.113.77") in caplog.text


async def test_close_cancels_running_questions_and_closes_the_client() -> None:
    asker = FakeAsker(hold=True)
    live = service(asker)
    job = live.start(QUESTION, "198.51.100.1")
    await asyncio.sleep(0)
    await live.aclose()
    assert asker.closed
    view = live.view(job.id)
    assert view is not None and view["status"] == "error"


# ---------------------------------------------------------------------- settings


def test_the_service_is_off_unless_enabled_and_configured(caplog: pytest.LogCaptureFixture) -> None:
    endpoint = {"DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": "https://gateway.example/api/projects/demo"}
    assert LiveAsk.from_env({}) is None
    assert LiveAsk.from_env(endpoint) is None
    assert LiveAsk.from_env({"DOCWIKI_LIVE_ASK": "0", **endpoint}) is None
    with caplog.at_level(logging.ERROR, logger="docwiki.portal.live_ask"):
        assert LiveAsk.from_env({"DOCWIKI_LIVE_ASK": "1"}) is None
        wrong = {"DOCWIKI_LIVE_ASK": "1", **endpoint, "DOCWIKI_LIVE_ASK_MAX_RUNNING": "x"}
        assert LiveAsk.from_env(wrong) is None
    assert "live ask is off" in caplog.text
    assert LiveAsk.from_env({"DOCWIKI_LIVE_ASK": "1", **endpoint}) is not None


def test_the_guards_are_set_by_environment_variables() -> None:
    assert LiveAskSettings.from_env({}) == LiveAskSettings()
    settings = LiveAskSettings.from_env(
        {
            "DOCWIKI_LIVE_ASK_MAX_BODY_BYTES": "2048",
            "DOCWIKI_LIVE_ASK_MIN_QUESTION_CHARS": "5",
            "DOCWIKI_LIVE_ASK_MAX_QUESTION_CHARS": "300",
            "DOCWIKI_LIVE_ASK_QUESTIONS_PER_IP": "2",
            "DOCWIKI_LIVE_ASK_IP_WINDOW_SECONDS": "60",
            "DOCWIKI_LIVE_ASK_MAX_RUNNING": "1",
            "DOCWIKI_LIVE_ASK_TIMEOUT_SECONDS": "100",
            "DOCWIKI_LIVE_ASK_RESULT_TTL_SECONDS": "30",
        }
    )
    assert settings == LiveAskSettings(2048, 5, 300, 2, 60.0, 1, 100.0, 30.0)
    assert LiveAskSettings() == LiveAskSettings(4096, 3, 500, 3, 300.0, 3, 200.0, 900.0)
    with pytest.raises(ValueError, match="MAX_RUNNING"):
        LiveAskSettings.from_env({"DOCWIKI_LIVE_ASK_MAX_RUNNING": "0"})


# ---------------------------------------------------------------------- routes

BASE_URL = "http://wiki.example"
JSON = {"content-type": "application/json"}


def poll(client: TestClient, job_id: str) -> dict[str, Any]:
    for _ in range(400):
        body = client.get(f"/api/ask/{job_id}").json()
        if body["status"] != "running":
            return body  # type: ignore[no-any-return]
        time.sleep(0.005)
    raise AssertionError("the job did not finish")


def test_status_says_disabled_without_the_service(site: Path) -> None:
    with TestClient(create_app(site_dir=site)) as client:
        response = client.get("/api/ask/status")
        assert (response.status_code, response.json()) == (200, {"enabled": False})
        assert client.post("/api/ask", json={"question": QUESTION}).status_code == 405
        assert client.get("/api/ask/0123456789abcdef").status_code == 404


def test_a_question_flows_through_the_routes(site: Path) -> None:
    asker = FakeAsker()
    app = create_app(site_dir=site, live_ask=service(asker, site))
    with TestClient(app, base_url=BASE_URL) as client:
        assert client.get("/api/ask/status").json() == {"enabled": True}
        accepted = client.post(
            "/api/ask",
            json={"question": QUESTION},
            headers={
                "origin": "http://wiki.example",
                "x-forwarded-for": "198.51.100.9, 203.0.113.5",
            },
        )
        assert accepted.status_code == 202
        assert accepted.headers["cache-control"] == "no-store"
        assert accepted.headers["content-security-policy"]  # the portal's security headers
        result = poll(client, accepted.json()["job_id"])
    assert result["status"] == "done" and result["elapsed_s"] >= 0
    assert result["answer"]["citations"][0]["href"] == f"evidence/{SID_A}/para-0007"
    # The edge appends the real address last; the forged first entry never keys the limits.
    assert asker.calls[0][2] == {"X-Visitor-IP": "203.0.113.5"}
    assert asker.closed  # closed with the app


def test_the_routes_gate_against_the_served_site(site: Path) -> None:
    (site / "evidence" / SID_A / "para-0007.html").unlink()
    app = create_app(site_dir=site, live_ask=service(FakeAsker()))
    with TestClient(app, base_url=BASE_URL) as client:
        job = client.post("/api/ask", json={"question": QUESTION}).json()["job_id"]
        result = poll(client, job)
    assert result["status"] == "unverified" and result["message"] == UNVERIFIED_MESSAGE
    assert result["answer"]["citations"] == []


def test_a_gateway_429_reaches_the_visitor_as_busy(site: Path) -> None:
    error = AgentInvocationError("HTTP 429 from the gateway", status_code=429)
    app = create_app(site_dir=site, live_ask=service(FakeAsker(error)))
    with TestClient(app, base_url=BASE_URL) as client:
        job = client.post("/api/ask", json={"question": QUESTION}).json()["job_id"]
        result = poll(client, job)
    assert result == {"status": "busy", "elapsed_s": result["elapsed_s"], "message": BUSY_MESSAGE}


@pytest.fixture
def client(site: Path) -> Any:
    app = create_app(site_dir=site, live_ask=service(FakeAsker(), site))
    with TestClient(app, base_url=BASE_URL) as test_client:
        yield test_client


def test_only_json_is_accepted(client: TestClient) -> None:
    body = '{"question": "When are the windows delivered?"}'
    for headers in ({}, {"content-type": "text/plain"}, {"content-type": "multipart/form-data"}):
        response = client.post("/api/ask", content=body, headers=headers)
        assert response.status_code == 415, headers
    ok = client.post(
        "/api/ask", content=body, headers={"content-type": "application/json; charset=utf-8"}
    )
    assert ok.status_code == 202


def test_a_foreign_origin_is_refused(client: TestClient) -> None:
    payload = {"question": QUESTION}
    for foreign in (
        "http://evil.example",
        "null",
        "http://wiki.example.evil",
        "http://wiki.example:81",
    ):
        got = client.post("/api/ask", json=payload, headers={"origin": foreign})
        assert got.status_code == 403, foreign
    # The site's own origin (the scheme may differ behind a TLS proxy) passes.
    for own in ("http://wiki.example", "https://wiki.example"):
        got = client.post("/api/ask", json=payload, headers={"origin": own})
        assert got.status_code == 202, own


def test_the_body_is_limited_to_four_kilobytes(client: TestClient) -> None:
    big = '{"question": "' + "x" * 4100 + '"}'
    assert client.post("/api/ask", content=big, headers=JSON).status_code == 413

    def chunks() -> Any:  # no Content-Length: the stream is cut
        yield b'{"question": "'
        yield b"x" * 4100
        yield b'"}'

    assert client.post("/api/ask", content=chunks(), headers=JSON).status_code == 413


@pytest.mark.parametrize(
    "body",
    [b"", b"not json", b"[]", b'{"question": 7}', b'{"q": "hello there"}', b'{"question": "ab"}'],
)
def test_bad_questions_are_a_400(client: TestClient, body: bytes) -> None:
    response = client.post("/api/ask", content=body, headers=JSON)
    assert response.status_code == 400 and response.json()["message"]


def test_the_visitor_limits_answer_429_with_a_message(site: Path) -> None:
    app = create_app(site_dir=site, live_ask=service(FakeAsker(), site, questions_per_ip=1))
    with TestClient(app, base_url=BASE_URL) as client:
        first = client.post("/api/ask", json={"question": QUESTION})
        poll(client, first.json()["job_id"])
        second = client.post("/api/ask", json={"question": QUESTION})
        assert second.status_code == 429
        assert "1 question every 5 minutes" in second.json()["message"]
        other = client.post(
            "/api/ask", json={"question": QUESTION}, headers={"x-forwarded-for": "203.0.113.200"}
        )
        assert other.status_code == 202


@pytest.mark.parametrize("status_code", [429, 403])
def test_gateway_limits_and_spent_quotas_tell_the_visitor_to_wait(
    site: Path, status_code: int
) -> None:
    error = AgentInvocationError(f"HTTP {status_code} from the gateway", status_code=status_code)
    app = create_app(site_dir=site, live_ask=service(FakeAsker(error), site))
    with TestClient(app, base_url=BASE_URL) as client:
        job = client.post("/api/ask", json={"question": QUESTION}).json()["job_id"]
        result = poll(client, job)
    assert result["status"] == "busy"
