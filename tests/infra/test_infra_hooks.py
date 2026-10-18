"""azd hooks: shared helpers, Entra operations, postprovision and postdeploy (fake az/azd)."""

from __future__ import annotations

import base64
import io
import json
import re
import threading
import urllib.error
import urllib.request
from collections.abc import Mapping
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import azdlib
import entra
import postdeploy
import postprovision
import pytest
from azdlib import HookError, Result, Tools
from infra_testkit import REPO_ROOT, FakeRunner, not_found

ENV = "demo"
TOKEN = "tok123"
RG = "rg-demo"
SUB = "sub-test"
TENANT = "tenant-test"
MCP_APP = "ca-mcp-tok123"
MCP_FQDN = "ca-mcp-tok123.region.azurecontainerapps.example"
APP = "app-1"
APP_URI = f"api://{APP}"
STUDIO_APP = "ca-studio-tok123"
STUDIO_FQDN = "ca-studio-tok123.region.azurecontainerapps.example"


def base_env(**extra: str) -> dict[str, str]:
    values = {
        "AZURE_ENV_NAME": ENV,
        "AZURE_SUBSCRIPTION_ID": SUB,
        "AZURE_RESOURCE_GROUP": RG,
        "AZURE_TENANT_ID": TENANT,
        "DOCWIKI_RESOURCE_TOKEN": TOKEN,
        "DOCWIKI_MCP_APP_NAME": MCP_APP,
        "DOCWIKI_MCP_FQDN": MCP_FQDN,
        "DOCWIKI_PORTAL_APP_NAME": "ca-portal-tok123",
        "DOCWIKI_STUDIO_APP_NAME": STUDIO_APP,
        "DOCWIKI_CONTAINER_APPS_DEFAULT_DOMAIN": "region.azurecontainerapps.example",
        "DOCWIKI_FOUNDRY_ACCOUNT_ENDPOINT": "https://aif-tok123.services.ai.azure.com/",
        "DOCWIKI_INGEST_JOB_NAME": "caj-ingest-tok123",
        "DOCWIKI_RECONCILE_JOB_NAME": "caj-reconcile-tok123",
    }
    values.update(extra)
    return values


def fake_token(claims: dict[str, str]) -> str:
    def part(data: dict[str, str]) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    return ".".join([part({"alg": "none"}), part(claims), "sig"])


# A token for another audience, built at run time (never a literal token in the sources).
ARM_TOKEN = fake_token({"aud": "arm", "oid": "user-oid"})


def tools(runner: FakeRunner, root: Path, **extra: str) -> Tools:
    return Tools(env=base_env(**extra), root=root, runner=runner, sleep=lambda _: None)


# ---------------------------------------------------------------------------
# azdlib
# ---------------------------------------------------------------------------


def test_batch_launcher_arguments_are_guarded() -> None:
    azdlib.check_batch_arguments(
        "C:/tools/az.cmd", ["rest", "--url", "https://graph.example/v1?$top=9"]
    )
    with pytest.raises(HookError):
        azdlib.check_batch_arguments(
            "C:/tools/az.cmd", ["rest", "--url", "https://graph.example/v1?a=1&b=2"]
        )
    with pytest.raises(HookError):
        azdlib.check_batch_arguments("C:/tools/az.CMD", ["--body", '{"a": 1}'])
    azdlib.check_batch_arguments("/usr/bin/az", ["--url", "https://graph.example/v1?a=1&b=2"])


def test_batch_launcher_command_line_quotes_parentheses() -> None:
    # az.cmd expands %* inside an IF ( ... ) block: an unquoted ")" ends the block.
    line = azdlib.batch_command_line(
        "C:/Program Files/Azure/wbin/az.cmd",
        [
            "rest",
            "--url",
            "https://graph.example/v1.0/servicePrincipals(appId='app-1')",
            "--query",
            "[?name=='x']",
            "",
            "C:\\my dir\\",
            "C:\\dir\\",
        ],
    )
    assert line == (
        '"C:/Program Files/Azure/wbin/az.cmd" rest --url '
        "\"https://graph.example/v1.0/servicePrincipals(appId='app-1')\" "
        '--query "[?name==\'x\']" "" "C:\\my dir\\\\" C:\\dir\\'
    )
    assert azdlib.is_batch_launcher("C:/tools/AZ.CMD") and not azdlib.is_batch_launcher("/bin/az")


def test_dotenv_parsing() -> None:
    text = 'A="x y"\nB=\'z\'\n# comment\nC="line\\nnext \\"q\\""\nexport D=1\n'
    assert azdlib.parse_dotenv(text) == {"A": "x y", "B": "z", "C": 'line\nnext "q"', "D": "1"}


def test_booleans() -> None:
    assert azdlib.is_true("TRUE") and not azdlib.is_true("false")
    assert azdlib.is_true(None, default=True) and azdlib.is_true("", default=True)
    with pytest.raises(HookError):
        azdlib.is_true("maybe")


def test_jwt_claims_without_validation() -> None:
    assert azdlib.jwt_claims(fake_token({"oid": "o1", "idtyp": "app"}))["oid"] == "o1"
    assert azdlib.jwt_claims("not-a-token") == {}


def test_state_round_trip(tmp_path: Path) -> None:
    path = azdlib.state_path(ENV, tmp_path)
    assert azdlib.load_state(path) == {"schema": 1}
    azdlib.save_state(path, {"mcp_api": {"app_id": "a"}})
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["mcp_api"] == {"app_id": "a"} and data["schema"] == 1 and data["updated_at"]
    assert path.parent == tmp_path / ".azure" / ENV
    assert b"\r\n" not in path.read_bytes()


def test_environment_values_from_dotenv_and_process(tmp_path: Path) -> None:
    folder = tmp_path / ".azure" / ENV
    folder.mkdir(parents=True)
    (folder / ".env").write_text('AZURE_RESOURCE_GROUP="rg-demo"\nDOCWIKI_X="1"\n', "utf-8")
    (tmp_path / ".azure" / "config.json").write_text('{"defaultEnvironment": "demo"}', "utf-8")
    result = azdlib.tools_from_environment({"DOCWIKI_X": "2", "PATH": "p"}, root=tmp_path)
    assert result.env["AZURE_RESOURCE_GROUP"] == "rg-demo"
    assert result.env["DOCWIKI_X"] == "2", "process values override the .env file"
    assert "PATH" not in result.env


def test_signed_in_principal_from_token(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"^az account show", {"id": SUB, "user": {"type": "user"}})
    runner.on(r"^az account get-access-token", {"accessToken": fake_token({"oid": "user-oid"})})
    assert tools(runner, tmp_path).signed_in_object_id() == ("user-oid", "User")
    assert not runner.commands(r"^az ad ")


# Microsoft Graph through the azd sign-in (DOCWIKI_GRAPH_TOKEN_SOURCE=azd, opt-in) ---------------

CAE_REFUSAL = Result(
    1, "", "ERROR: AADSTS50173: TokenCreatedWithOutdatedPolicies (claims challenge)"
)
APPLICATIONS = f"{azdlib.GRAPH}/applications"
OPT_IN = {"DOCWIKI_GRAPH_TOKEN_SOURCE": "azd"}


class FakeHttp:
    """Replaces the HTTP client of the Graph fallback: records requests and answers in order
    (the last answer repeats). An answer is ``(status, JSON data | bytes | None)``."""

    def __init__(self, *answers: tuple[int, Any]) -> None:
        self.answers = list(answers)
        self.requests: list[tuple[str, str, dict[str, str], bytes | None]] = []

    def __call__(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes | None
    ) -> tuple[int, bytes]:
        self.requests.append((method, url, dict(headers), body))
        status, payload = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        if payload is None:
            return status, b""
        return status, payload if isinstance(payload, bytes) else json.dumps(payload).encode()


def graph_refused(
    runner: FakeRunner,
    azd_claims: dict[str, str] | None = None,
    cli_claims: dict[str, str] | None = None,
    *,
    cli_token: bool = True,
) -> str:
    """Graph refuses the Azure CLI's token (continuous access evaluation) and azd has another.

    The claims override the account both tokens carry (an empty value drops the claim). Returns
    the azd token, built at run time: no message may ever contain it.
    """

    def token(audience: str, claims: dict[str, str] | None) -> str:
        merged = {"aud": audience, "tid": TENANT, "oid": "user-oid", **(claims or {})}
        return fake_token({name: value for name, value in merged.items() if value})

    azd_token = token("graph", azd_claims)
    runner.on(r"^az rest ", CAE_REFUSAL)
    runner.on(r"^azd auth token", {"token": azd_token, "expiresOn": "2099-01-01T00:00:00Z"})
    if cli_token:
        runner.on(r"^az account get-access-token", {"accessToken": token("arm", cli_claims)})
    else:
        runner.on(r"^az account get-access-token", Result(1, "", "ERROR: no token"))
    return azd_token


def graph_tools(runner: FakeRunner, root: Path, http: FakeHttp, **extra: str) -> Tools:
    t = tools(runner, root, **extra)
    t.http = http
    return t


@pytest.mark.parametrize("source", ["", "az", "off", "azd-cli"])
def test_graph_refusal_stays_an_error_without_the_opt_in(
    runner: FakeRunner, tmp_path: Path, source: str
) -> None:
    graph_refused(runner)
    http = FakeHttp((200, {}))
    t = graph_tools(
        runner, tmp_path, http, **({"DOCWIKI_GRAPH_TOKEN_SOURCE": source} if source else {})
    )
    with pytest.raises(HookError) as raised:
        t.rest("GET", APPLICATIONS)
    assert "needs a fresh sign-in" in str(raised.value)
    remediation = raised.value.remediation or ""
    assert "az login" in remediation and "azd auth login" in remediation
    assert "DOCWIKI_GRAPH_TOKEN_SOURCE=azd" in remediation
    assert not runner.commands(r"^azd auth token") and not http.requests


@pytest.mark.parametrize("where", ["azd environment", "process environment"])
def test_graph_fallback_calls_graph_with_the_azd_token(
    runner: FakeRunner,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    where: str,
) -> None:
    if where == "process environment":
        monkeypatch.setenv("DOCWIKI_GRAPH_TOKEN_SOURCE", " AZD ")
    azd_token = graph_refused(runner)
    http = FakeHttp((200, {"value": [{"id": "obj-1"}]}), (201, {"id": "sp-1"}))
    t = graph_tools(runner, tmp_path, http, **(OPT_IN if where == "azd environment" else {}))
    url = f"{APPLICATIONS}?$filter=displayName eq 'docwiki-x'"
    assert t.rest("GET", url) == {"value": [{"id": "obj-1"}]}
    created = t.rest("POST", f"{azdlib.GRAPH}/servicePrincipals", body={"appId": "app-1"})
    assert created == {"id": "sp-1"}
    # One token for the run, for the tenant of the environment, as JSON.
    assert runner.commands(r"^azd auth token") == [
        "azd auth token --scope https://graph.microsoft.com/.default "
        f"--tenant-id {TENANT} --output json"
    ]
    (get, post) = http.requests
    assert get[:2] == ("GET", url) and get[3] is None
    assert get[2]["Authorization"] == f"Bearer {azd_token}"
    assert post[:2] == ("POST", f"{azdlib.GRAPH}/servicePrincipals")
    assert json.loads(post[3] or b"") == {"appId": "app-1"}
    assert post[2]["Content-Type"] == "application/json"
    shown = capsys.readouterr()
    assert azd_token not in shown.out + shown.err and azd_token not in repr(t)
    assert "azd sign-in" in shown.out, "the operator is told which token is used"
    assert not list((tmp_path / ".azure" / ENV / "hook-tmp").glob("*.json")), "no body left"


@pytest.mark.parametrize(
    ("azd_claims", "differs"),
    [({"oid": "someone-else"}, "object ID"), ({"tid": "another-tenant"}, "tenant")],
)
def test_graph_fallback_refuses_another_account(
    runner: FakeRunner, tmp_path: Path, azd_claims: dict[str, str], differs: str
) -> None:
    azd_token = graph_refused(runner, azd_claims=azd_claims)
    http = FakeHttp((200, {}))
    t = graph_tools(runner, tmp_path, http, **OPT_IN)
    with pytest.raises(HookError) as raised:
        t.rest("GET", APPLICATIONS)
    assert "different accounts" in str(raised.value) and differs in str(raised.value)
    assert "azd auth login" in (raised.value.remediation or "")
    assert azd_token not in str(raised.value) + (raised.value.remediation or "")
    assert not http.requests, "nothing is sent with a token of another account"
    # Nothing is cached: once the accounts agree, the same instance goes through.
    runner.rules.clear()
    graph_refused(runner)
    assert t.rest("GET", APPLICATIONS) == {}


@pytest.mark.parametrize(
    ("azd_claims", "cli_claims", "cli_token"),
    [
        ({"tid": ""}, None, True),
        ({"oid": ""}, None, True),
        (None, {"oid": ""}, True),
        (None, None, False),
    ],
)
def test_graph_fallback_needs_both_identities_to_compare(
    runner: FakeRunner,
    tmp_path: Path,
    azd_claims: dict[str, str] | None,
    cli_claims: dict[str, str] | None,
    cli_token: bool,
) -> None:
    graph_refused(runner, azd_claims, cli_claims, cli_token=cli_token)
    http = FakeHttp((200, {}))
    with pytest.raises(HookError, match="cannot tell whether azd and the Azure CLI"):
        graph_tools(runner, tmp_path, http, **OPT_IN).rest("GET", APPLICATIONS)
    assert not http.requests


@pytest.mark.parametrize(
    "url",
    [
        f"{azdlib.ARM}/subscriptions/{SUB}?api-version=2022-12-01",
        "https://graph.microsoft.com.example.net/v1.0/applications",
        "https://evilgraph.microsoft.com/v1.0/applications",
        "https://sub.graph.microsoft.com/v1.0/applications",
        "https://graph.microsoft.com./v1.0/applications",
        # Built at run time: a literal user@host in the sources trips the leak guard's e-mail rule.
        "https://" + "someone" + "@" + "graph.microsoft.com/v1.0/applications",
        "https://example.net/graph.microsoft.com/v1.0/applications",
        "https://graph.microsoft.com@example.net/v1.0/applications",
        "https://graph.microsoft.com:8443/v1.0/applications",
        "https://graph.microsoft.us/v1.0/applications",
        "http://graph.microsoft.com/v1.0/applications",
    ],
)
def test_graph_fallback_never_applies_to_another_host(
    runner: FakeRunner, tmp_path: Path, url: str
) -> None:
    graph_refused(runner)
    http = FakeHttp((200, {}))
    with pytest.raises(HookError, match="needs a fresh sign-in") as raised:
        graph_tools(runner, tmp_path, http, **OPT_IN).rest("GET", url)
    assert not runner.commands(r"^azd auth token") and not http.requests
    assert not azdlib.is_graph_url(url)
    if "management" in url:
        assert "DOCWIKI_GRAPH_TOKEN_SOURCE" not in (raised.value.remediation or "")


def test_the_azd_token_is_refused_for_any_other_url(runner: FakeRunner, tmp_path: Path) -> None:
    graph_refused(runner)
    http = FakeHttp((200, {}))
    with pytest.raises(HookError, match="refusing to send the Microsoft Graph token"):
        graph_tools(runner, tmp_path, http, **OPT_IN).graph_rest("GET", f"{azdlib.ARM}/x?y=1")
    assert not runner.commands(r"^azd auth token") and not http.requests


def test_graph_fallback_without_a_tenant_lets_azd_choose(
    runner: FakeRunner, tmp_path: Path
) -> None:
    graph_refused(runner)
    t = graph_tools(runner, tmp_path, FakeHttp((200, {})), **OPT_IN)
    del t.env["AZURE_TENANT_ID"]
    assert t.rest("GET", APPLICATIONS) == {}
    assert runner.commands(r"^azd auth token") == [
        "azd auth token --scope https://graph.microsoft.com/.default --output json"
    ]


@pytest.mark.parametrize(
    "answer",
    [
        Result(1, "AZD-STDOUT-SENTINEL", "AZD-STDERR-SENTINEL"),
        Result(0, "AZD-STDOUT-SENTINEL", ""),
        Result(0, "{}", ""),
        Result(0, '{"token": ""}', ""),
        Result(0, "[]", ""),
    ],
)
def test_graph_fallback_reports_azd_failures_without_its_output(
    runner: FakeRunner, tmp_path: Path, answer: Result
) -> None:
    runner.on(r"^az rest ", CAE_REFUSAL)
    runner.on(r"^azd auth token", answer)
    http = FakeHttp((200, {}))
    with pytest.raises(HookError) as raised:
        graph_tools(runner, tmp_path, http, **OPT_IN).rest("GET", APPLICATIONS)
    shown = str(raised.value) + (raised.value.remediation or "")
    assert "did not give a Microsoft Graph token" in shown and "azd auth login" in shown
    assert "SENTINEL" not in shown
    assert not http.requests and not runner.commands(r"^az account get-access-token")


def test_graph_fallback_answers_like_az_rest(runner: FakeRunner, tmp_path: Path) -> None:
    graph_refused(runner)
    missing = {"error": {"code": "Request_ResourceNotFound", "message": "Resource 'x' not found."}}
    http = FakeHttp((404, missing), (404, missing), (204, None), (200, b"  "), (200, b"{broken"))
    t = graph_tools(runner, tmp_path, http, **OPT_IN)
    assert t.rest("GET", APPLICATIONS, allow_not_found=True) is None
    with pytest.raises(azdlib.CommandError) as raised:
        t.rest("GET", APPLICATIONS)
    assert "HTTP 404" in str(raised.value) and "Request_ResourceNotFound" in str(raised.value)
    assert azdlib.is_not_found(raised.value.result), "callers that tolerate a 404 keep working"
    assert t.rest("DELETE", f"{APPLICATIONS}/obj-1") is None
    assert t.rest("PATCH", f"{APPLICATIONS}/obj-1", body={"web": {}}) is None
    with pytest.raises(HookError, match="did not return JSON"):
        t.rest("GET", APPLICATIONS)
    assert [request[0] for request in http.requests] == ["GET", "GET", "DELETE", "PATCH", "GET"]


def test_graph_fallback_errors_show_graphs_code_and_message_only(
    runner: FakeRunner, tmp_path: Path
) -> None:
    azd_token = graph_refused(runner)
    denied = {
        "error": {
            "code": "Authorization_RequestDenied",
            "message": "Insufficient privileges\nto complete the operation.",
            "innerError": {"request-id": "internal-detail"},
        }
    }
    http = FakeHttp((403, denied), (302, None), (400, b"<html>proxy error</html>"))
    t = graph_tools(runner, tmp_path, http, **OPT_IN)
    with pytest.raises(azdlib.CommandError) as raised:
        t.rest("POST", f"{APPLICATIONS}", body={"displayName": "x"})
    message = str(raised.value)
    assert "HTTP 403: Authorization_RequestDenied: Insufficient privileges to complete" in message
    assert "internal-detail" not in message and azd_token not in message
    assert isinstance(raised.value, HookError) and not azdlib.is_not_found(raised.value.result)
    with pytest.raises(azdlib.CommandError, match="HTTP 302"):
        t.rest("GET", APPLICATIONS)
    with pytest.raises(azdlib.CommandError) as raised:
        t.rest("GET", APPLICATIONS)
    assert "HTTP 400" in str(raised.value) and "proxy error" not in str(raised.value)


def test_graph_fallback_401_asks_for_a_new_azd_sign_in(runner: FakeRunner, tmp_path: Path) -> None:
    azd_token = graph_refused(runner)
    revoked = {"error": {"code": "InvalidAuthenticationToken", "message": "Token is revoked."}}
    with pytest.raises(HookError) as raised:
        graph_tools(runner, tmp_path, FakeHttp((401, revoked)), **OPT_IN).rest("GET", APPLICATIONS)
    assert not isinstance(raised.value, azdlib.CommandError), "not retried like a Graph failure"
    assert "refused the azd token too" in str(raised.value)
    assert "InvalidAuthenticationToken" in str(raised.value)
    assert "azd auth login" in (raised.value.remediation or "")
    assert azd_token not in str(raised.value) + (raised.value.remediation or "")


def test_graph_fallback_errors_are_retried_like_az_rest_errors(
    runner: FakeRunner, tmp_path: Path
) -> None:
    """A new application can take seconds to replicate: ``retry`` covers the fallback too."""
    graph_refused(runner)
    lagging = {"error": {"code": "Request_ResourceNotFound", "message": "not replicated yet"}}
    http = FakeHttp((404, lagging), (201, {"id": "sp-1"}))
    t = graph_tools(runner, tmp_path, http, **OPT_IN)
    created = azdlib.retry(
        lambda: t.rest("POST", f"{azdlib.GRAPH}/servicePrincipals", body={"appId": "app-1"}),
        sleep=lambda _: None,
    )
    assert created == {"id": "sp-1"} and len(http.requests) == 2
    assert len(runner.commands(r"^azd auth token")) == 1


def test_az_rest_that_succeeds_never_reaches_for_azd(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"^az rest ", {"value": []})
    http = FakeHttp((200, {}))
    assert graph_tools(runner, tmp_path, http, **OPT_IN).rest("GET", APPLICATIONS) == {"value": []}
    assert not http.requests and not runner.commands(r"^azd ")


class FakeOpener:
    """Stands in for ``urllib.request.build_opener(...)``: records the request, then answers."""

    def __init__(self, outcome: Any) -> None:
        self.outcome = outcome
        self.handlers: tuple[Any, ...] = ()
        self.request: urllib.request.Request | None = None
        self.timeout: float | None = None

    def build(self, *handlers: Any) -> FakeOpener:
        self.handlers = handlers
        return self

    def open(self, request: urllib.request.Request, timeout: float | None = None) -> Any:
        self.request, self.timeout = request, timeout
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class FakeResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status, self._body = status, body

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_default_http_client_encodes_the_url_and_sends_the_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    opener = FakeOpener(FakeResponse(200, b'{"value": []}'))
    monkeypatch.setattr(urllib.request, "build_opener", opener.build)
    url = f"{APPLICATIONS}?$filter=displayName eq 'docwiki-x'&$top=9"
    status, body = azdlib.urllib_http("PATCH", url, {"X-Docwiki-Test": "1"}, b"{}")
    assert (status, body) == (200, b'{"value": []}')
    assert opener.handlers == (azdlib._NoRedirect,), "redirects are not followed"
    assert opener.timeout == azdlib.GRAPH_HTTP_TIMEOUT_S
    request = opener.request
    assert request is not None
    assert request.full_url == f"{APPLICATIONS}?$filter=displayName%20eq%20'docwiki-x'&$top=9"
    assert request.get_method() == "PATCH" and request.data == b"{}"
    assert request.get_header("X-docwiki-test") == "1"


def test_default_http_client_returns_error_statuses_and_maps_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refused = urllib.error.HTTPError(
        APPLICATIONS, 403, "Forbidden", Message(), io.BytesIO(b'{"a": 1}')
    )
    monkeypatch.setattr(urllib.request, "build_opener", FakeOpener(refused).build)
    assert azdlib.urllib_http("GET", APPLICATIONS, {}, None) == (403, b'{"a": 1}')
    unreachable = FakeOpener(urllib.error.URLError("name resolution failed"))
    monkeypatch.setattr(urllib.request, "build_opener", unreachable.build)
    with pytest.raises(HookError, match=r"graph\.microsoft\.com could not be reached"):
        azdlib.urllib_http("GET", APPLICATIONS, {}, None)
    timed_out = FakeOpener(TimeoutError("timed out"))
    monkeypatch.setattr(urllib.request, "build_opener", timed_out.build)
    with pytest.raises(HookError, match="could not be reached"):
        azdlib.urllib_http("GET", APPLICATIONS, {}, None)


def test_default_http_client_only_speaks_https(monkeypatch: pytest.MonkeyPatch) -> None:
    opener = FakeOpener(FakeResponse(200, b"{}"))
    monkeypatch.setattr(urllib.request, "build_opener", opener.build)
    for url in ("http://graph.microsoft.com/v1.0/me", "file:///etc/hosts", "//graph.microsoft.com"):
        with pytest.raises(HookError, match="refusing to send a request"):
            azdlib.urllib_http("GET", url, {}, None)
    assert opener.request is None


def test_a_redirect_is_an_answer_the_token_does_not_follow() -> None:
    seen: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            seen.append(self.path)
            if self.path == "/start":
                self.send_response(302)
                self.send_header("Location", "/elsewhere")
                self.send_header("Content-Length", "0")
                self.end_headers()
            else:
                self.send_response(200)
                self.send_header("Content-Length", "2")
                self.end_headers()
                self.wfile.write(b"{}")

        def log_message(self, fmt: str, *args: object) -> None:
            return None

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = urllib.request.Request(
            f"http://127.0.0.1:{server.server_port}/start", headers={"X-Docwiki-Test": "1"}
        )
        with pytest.raises(urllib.error.HTTPError) as raised:
            # No proxy: the loopback server is reached directly, whatever the environment says.
            opener = urllib.request.build_opener(
                urllib.request.ProxyHandler({}), azdlib._NoRedirect
            )
            opener.open(request, timeout=10)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
    assert raised.value.code == 302 and seen == ["/start"]
    raised.value.close()


# ---------------------------------------------------------------------------
# entra
# ---------------------------------------------------------------------------


def test_app_roles_merge_keeps_ids_and_drops_origin() -> None:
    existing = [
        {
            "id": "keep-me",
            "value": "Wiki.Read",
            "description": "old",
            "origin": "Application",
            "allowedMemberTypes": ["User"],
            "isEnabled": True,
            "displayName": "x",
        },
        {
            "id": "other",
            "value": "Custom",
            "description": "c",
            "origin": "Application",
            "allowedMemberTypes": ["User"],
            "isEnabled": True,
            "displayName": "Custom",
        },
    ]
    merged = entra.merge_app_roles(existing, entra.MCP_APP_ROLES)
    by_value = {role["value"]: role for role in merged}
    assert by_value["Wiki.Read"]["id"] == "keep-me"
    assert by_value["Wiki.Read"]["allowedMemberTypes"] == ["Application"]
    assert by_value["Wiki.Operate"]["id"] == entra.app_role_id("Wiki.Operate")
    assert by_value["Custom"]["id"] == "other"
    assert all("origin" not in role for role in merged)
    assert entra.app_role_id("Wiki.Read") == entra.app_role_id("Wiki.Read")
    assert entra.app_role_id("Wiki.Read") != entra.app_role_id("Wiki.Operate")


def graph_app(app_id: str = "app-1", object_id: str = "obj-1", **extra: Any) -> dict[str, Any]:
    app = {
        "id": object_id,
        "appId": app_id,
        "displayName": f"docwiki-mcp-api-{ENV}-{TOKEN}",
        "tags": [f"docwiki-env:{ENV}-{TOKEN}", "docwiki"],
        "identifierUris": [f"api://{app_id}"],
        "api": {"requestedAccessTokenVersion": 2},
        "appRoles": [
            {**role, "origin": "Application"}
            for role in entra.merge_app_roles([], entra.MCP_APP_ROLES)
        ],
    }
    app.update(extra)
    return app


def test_mcp_api_is_created_once(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*applications\?\$filter", {"value": []})
    runner.on(r"POST .*/applications ", graph_app(identifierUris=[]))
    runner.on(r"PATCH .*/applications/obj-1", None)
    runner.on(r"GET .*servicePrincipals\(appId='app-1'\)", not_found())
    runner.on(r"POST .*/servicePrincipals ", {"id": "sp-1", "appRoleAssignmentRequired": True})
    runner.on(r"GET .*/servicePrincipals/sp-1/owners", {"value": []})
    runner.on(r"POST .*/servicePrincipals/sp-1/owners/\$ref", None)
    registration = entra.ensure_mcp_api(
        tools(runner, tmp_path),
        display_name=f"docwiki-mcp-api-{ENV}-{TOKEN}",
        tag=f"docwiki-env:{ENV}-{TOKEN}",
        known_app_id=None,
        owner_object_id="user-oid",
    )
    assert registration.created and registration.app_id == "app-1"
    assert registration.identifier_uri == APP_URI
    created = runner.body_for(r"POST .*/applications ")[0]
    assert created["signInAudience"] == "AzureADMyOrg"
    assert created["api"] == {"requestedAccessTokenVersion": 2}
    assert {role["value"] for role in created["appRoles"]} == {"Wiki.Read", "Wiki.Operate"}
    assert all(role["allowedMemberTypes"] == ["Application"] for role in created["appRoles"])
    assert runner.body_for(r"PATCH .*/applications/obj-1")[0] == {"identifierUris": [APP_URI]}
    assert runner.body_for(r"POST .*/servicePrincipals ")[0]["appRoleAssignmentRequired"] is True


def test_mcp_api_second_run_changes_nothing(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*applications\(appId='app-1'\)", graph_app())
    runner.on(
        r"GET .*servicePrincipals\(appId='app-1'\)",
        {"id": "sp-1", "appRoleAssignmentRequired": True},
    )
    runner.on(r"GET .*/servicePrincipals/sp-1/owners", {"value": [{"id": "user-oid"}]})
    registration = entra.ensure_mcp_api(
        tools(runner, tmp_path),
        display_name=f"docwiki-mcp-api-{ENV}-{TOKEN}",
        tag=f"docwiki-env:{ENV}-{TOKEN}",
        known_app_id="app-1",
        owner_object_id="user-oid",
    )
    assert not registration.created
    assert not runner.commands(r"--method (POST|PATCH)")


def test_app_role_assignment_is_idempotent(runner: FakeRunner, tmp_path: Path) -> None:
    role = entra.app_role_id("Wiki.Read")
    runner.queue(
        r"GET .*appRoleAssignedTo",
        {"value": []},
        {"value": [{"id": "as-1", "principalId": "p-1", "appRoleId": role}]},
    )
    runner.on(r"POST .*appRoleAssignedTo", {"id": "as-1", "principalId": "p-1", "appRoleId": role})
    t = tools(runner, tmp_path)
    first = entra.ensure_app_role_assignment(
        t, resource_sp_id="sp-1", principal_id="p-1", role_id=role
    )
    second = entra.ensure_app_role_assignment(
        t, resource_sp_id="sp-1", principal_id="p-1", role_id=role
    )
    assert first["id"] == second["id"] == "as-1"
    assert len(runner.commands(r"POST .*appRoleAssignedTo")) == 1
    assert runner.body_for(r"POST .*appRoleAssignedTo")[0] == {
        "principalId": "p-1",
        "resourceId": "sp-1",
        "appRoleId": role,
    }


def test_duplicate_tagged_registrations_are_refused(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(
        r"GET .*applications\?\$filter", {"value": [graph_app(), graph_app("app-2", "obj-2")]}
    )
    with pytest.raises(HookError):
        entra.ensure_mcp_api(
            tools(runner, tmp_path),
            display_name=f"docwiki-mcp-api-{ENV}-{TOKEN}",
            tag=f"docwiki-env:{ENV}-{TOKEN}",
            known_app_id=None,
        )


@pytest.mark.parametrize(
    ("kwargs", "description"),
    [
        ({}, "DocWiki private portal sign-in."),
        (
            {"description": "DocWiki Studio sign-in (owner only)."},
            "DocWiki Studio sign-in (owner only).",
        ),
    ],
)
def test_sign_in_app_describes_the_app_it_serves(
    runner: FakeRunner, tmp_path: Path, kwargs: dict[str, str], description: str
) -> None:
    runner.on(r"GET .*applications\?\$filter", {"value": []})
    runner.on(r"POST .*/applications ", {"id": "obj-9", "appId": "app-9", "web": {}})
    runner.on(r"PATCH .*/applications/obj-9", None)
    runner.on(
        r"GET .*servicePrincipals\(appId='app-9'\)",
        {"id": "sp-9", "appRoleAssignmentRequired": True},
    )
    registration = entra.ensure_portal_app(
        tools(runner, tmp_path),
        display_name=f"docwiki-x-{ENV}-{TOKEN}",
        tag=f"docwiki-env:{ENV}-{TOKEN}",
        known_app_id=None,
        redirect_uri="https://app.example/.auth/login/aad/callback",
        **kwargs,
    )
    created = runner.body_for(r"POST .*/applications ")[0]
    assert created["description"] == description
    assert created["web"]["redirectUris"] == ["https://app.example/.auth/login/aad/callback"]
    assert created["web"]["implicitGrantSettings"]["enableAccessTokenIssuance"] is False
    assert registration.created and registration.service_principal_id == "sp-9"


# ---------------------------------------------------------------------------
# postprovision
# ---------------------------------------------------------------------------

ISSUER = "https://login.microsoftonline.com/tenant-test/v2.0"
AUTH_OK = {
    "properties": {
        "platform": {"enabled": True},
        "globalValidation": {
            "unauthenticatedClientAction": "Return401",
            "excludedPaths": ["/healthz"],
        },
        "identityProviders": {
            "azureActiveDirectory": {
                "enabled": True,
                "registration": {"clientId": "app-1", "openIdIssuer": ISSUER},
                "validation": {"allowedAudiences": [APP_URI]},
            }
        },
        "login": {"tokenStore": {"enabled": False}},
    }
}


def auth_allowing(*client_ids: str) -> dict[str, Any]:
    config = json.loads(json.dumps(AUTH_OK))
    validation = config["properties"]["identityProviders"]["azureActiveDirectory"]["validation"]
    validation["defaultAuthorizationPolicy"] = {"allowedApplications": list(client_ids)}
    return config


def auth_shown(*client_ids: str, enabled: bool = True) -> dict[str, Any]:
    """``az containerapp auth show`` output: the auth config properties alone."""
    properties = auth_allowing(*client_ids)["properties"]
    properties["platform"] = {"enabled": enabled}
    return properties


def server_settings(*client_ids: str, validation: str = "required") -> dict[str, str]:
    """The token settings the hook gives the MCP server (same values as infra/main.bicep)."""
    values = {
        "DOCWIKI_MCP_TENANT_ID": TENANT,
        "DOCWIKI_MCP_AUDIENCE": f"{APP_URI},{APP}",
        "DOCWIKI_MCP_TOKEN_VALIDATION": validation,
    }
    if client_ids:
        values["DOCWIKI_MCP_ALLOWED_CLIENT_IDS"] = ",".join(client_ids)
    return values


def mcp_app(env: dict[str, str] | None = None, *, external: bool = False) -> dict[str, Any]:
    """ARM view of the MCP container app."""
    container = {
        "name": "mcp",
        "image": "crtok.azurecr.io/docwiki/mcp-demo:azd-1",
        "env": [{"name": "DOCWIKI_AUTH_MODE", "value": "easyauth"}]
        + [{"name": key, "value": value} for key, value in (env or {}).items()],
    }
    configuration = {"ingress": {"external": True, "fqdn": MCP_FQDN}} if external else {}
    return {"properties": {"configuration": configuration, "template": {"containers": [container]}}}


# What Bicep sets before the MCP API app registration exists (first provision).
FIRST_PROVISION_ENV = {"DOCWIKI_MCP_TENANT_ID": TENANT, "DOCWIKI_MCP_TOKEN_VALIDATION": "required"}
MCP_APP_GET = r"GET .*containerApps/ca-mcp-tok123\?"


def provisioned(runner: FakeRunner) -> FakeRunner:
    """Fake Azure where the MCP app registration does not exist yet."""
    runner.on(r"^az account show", {"id": SUB, "user": {"type": "user"}})
    runner.on(r"^az account get-access-token", {"accessToken": fake_token({"oid": "user-oid"})})
    runner.on(r"GET .*applications\?\$filter", {"value": []})
    runner.on(r"POST .*/applications ", graph_app(identifierUris=[]))
    runner.on(r"PATCH .*/applications/obj-1", None)
    runner.on(r"GET .*servicePrincipals\(appId='app-1'\)", not_found())
    runner.on(r"POST .*/servicePrincipals ", {"id": "sp-1", "appRoleAssignmentRequired": True})
    runner.on(r"GET .*/servicePrincipals/sp-1/owners", {"value": []})
    runner.on(r"POST .*/owners/\$ref", None)
    runner.on(r"^azd env set", None)
    runner.queue(r"GET .*authConfigs/current", not_found(), AUTH_OK)
    runner.on(r"^az deployment group create", None)
    runner.on(r"^az containerapp auth show", auth_shown())
    runner.queue(
        MCP_APP_GET, mcp_app(FIRST_PROVISION_ENV), mcp_app(server_settings(), external=True)
    )
    runner.on(r"^az containerapp update", None)
    runner.on(r"^az containerapp ingress enable", {"external": True, "fqdn": MCP_FQDN})
    runner.on(r"GET .*appRoleAssignedTo", {"value": []})
    runner.on(
        r"POST .*appRoleAssignedTo",
        lambda args: Result(0, json.dumps({"id": "as-" + str(len(args))}), ""),
    )
    return runner


def auth_parameters(runner: FakeRunner) -> list[dict[str, Any]]:
    return [body["parameters"] for body in runner.body_for(r"^az deployment group create")]


def exposure_order(runner: FakeRunner) -> list[str]:
    """Kinds of the auth and exposure commands, in call order."""
    kinds = {
        "deployment group create": "auth-deploy",
        "containerapp auth show": "auth-verify",
        "containerapp update": "settings",
        "containerapp ingress enable": "ingress",
    }
    return [
        kind
        for line in (" ".join(call) for call in runner.calls)
        for pattern, kind in kinds.items()
        if pattern in line
    ]


def test_postprovision_without_agents_secures_the_mcp_app(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = postprovision.main([], runner=provisioned(runner), environ=base_env(), root=tmp_path)
    assert code == 0
    state = json.loads(azdlib.state_path(ENV, tmp_path).read_text(encoding="utf-8"))
    assert state["mcp_api"]["app_id"] == "app-1"
    assert state["mcp_api"]["created_by_hook"] is True
    sets = runner.commands(r"^azd env set")
    assert any("DOCWIKI_MCP_API_CLIENT_ID app-1 --environment demo" in line for line in sets)
    deployment = runner.commands(r"^az deployment group create")
    assert len(deployment) == 1, "the empty allowlist already matches"
    assert "app-auth.bicep" in deployment[0] and f"--resource-group {RG}" in deployment[0]
    parameters = auth_parameters(runner)[0]
    assert parameters["unauthenticatedClientAction"]["value"] == "Return401"
    assert parameters["allowedAudiences"]["value"] == [APP_URI]
    assert parameters["excludedPaths"]["value"] == ["/healthz"]
    assert parameters["allowedApplications"]["value"] == []
    # Fail closed: auth applied and verified, then the server's token settings, then ingress;
    # the allowlist step verifies again and finds the app secured.
    assert exposure_order(runner) == [
        "auth-deploy",
        "auth-verify",
        "settings",
        "ingress",
        "auth-verify",
    ]
    update = runner.commands(r"^az containerapp update")[0]
    assert f"--name {MCP_APP}" in update and "--container-name mcp" in update
    assert f"--set-env-vars DOCWIKI_MCP_AUDIENCE={APP_URI},{APP} --output none" in update, (
        "only the missing setting is written; no agent yet: no caller allowlist"
    )
    ingress = runner.commands(r"ingress enable")
    assert len(ingress) == 1 and f"--name {MCP_APP}" in ingress[0], "portal disabled by default"
    assert "--type external" in ingress[0]
    assert not list((tmp_path / ".azure" / ENV / "hook-tmp").glob("*.json")), "bodies cleaned up"
    assert not runner.commands(r"POST .*appRoleAssignedTo")
    assert not runner.commands(r"connections/"), "no agents lane, no connection"
    assert not runner.commands(r"contentunderstanding"), "CU defaults are opt-in"
    output = capsys.readouterr().out
    assert "agents/deploy.py not found" in output
    assert "no agent identity for the researcher agent" in output and ADR_PATH in output
    assert "the MCP app answers 403" in output
    assert f"built-in auth on {MCP_APP} verified" in output


ADR_PATH = "docs/adr/0003-mcp-agent-identity.md"
MCP_URL = "https://ca-mcp-tok123.region.azurecontainerapps.example/mcp"
PROJECT = "https://aif-tok123.services.ai.azure.com/api/projects/docwiki"
CONNECTION_PATH = (
    f"/subscriptions/{SUB}/resourceGroups/{RG}/providers/Microsoft.CognitiveServices/"
    "accounts/aif-tok123/projects/docwiki/connections/docwiki-mcp"
)


def agents_repo(root: Path, strategy: str = "per-agent-identity") -> Path:
    """A minimal agents/ folder: deploy.py, two agent definitions and the Librarian routine."""
    agents = root / "agents"
    for key in ("researcher", "librarian"):
        (agents / key).mkdir(parents=True, exist_ok=True)
        (agents / key / "agent.yaml").write_text(
            f"name: docwiki-{key}\ntools:\n  - type: mcp\n    auth:\n      strategy: {strategy}\n",
            encoding="utf-8",
        )
    (agents / "librarian" / "routine.yaml").write_text("name: daily\n", encoding="utf-8")
    (agents / "deploy.py").write_text("print('deploy')\n", encoding="utf-8")
    return agents


def agent_env(**extra: str) -> dict[str, str]:
    values = {
        "DOCWIKI_MCP_URL": MCP_URL,
        "DOCWIKI_MCP_API_CLIENT_ID": APP,
        "DOCWIKI_MCP_API_AUDIENCE": APP_URI,
        "DOCWIKI_FOUNDRY_ACCOUNT_NAME": "aif-tok123",
        "DOCWIKI_FOUNDRY_PROJECT_NAME": "docwiki",
        "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": PROJECT,
        "DOCWIKI_SMART_DEPLOYMENT": "smart",
    }
    values.update(extra)
    return values


def context(
    runner: FakeRunner, root: Path, state: dict[str, Any] | None = None, **extra: str
) -> postprovision.Context:
    t = tools(runner, root, **agent_env(**extra))
    t.which = lambda name: "/usr/bin/uv" if name == "uv" else None
    return postprovision.Context(
        tools=t, state=dict(state or {}), state_file=azdlib.state_path(ENV, root)
    )


def deploy_report(*agents: tuple[str, str | None], client_ids: dict[str, str] | None = None) -> str:
    entries = []
    for key, principal in agents:
        entry: dict[str, Any] = {
            "key": key,
            "agent_name": f"docwiki-{key}",
            "status": "created",
            "version": "3",
            "previous_version": "2",
            "definition_sha256": "0" * 64,
            "identity_principal_id": principal,
        }
        if client_ids and key in client_ids:
            entry["identity_client_id"] = client_ids[key]
        entries.append(entry)
    return json.dumps({"agents": entries, "routines": []})


def connection(**overrides: Any) -> dict[str, Any]:
    properties = {
        "category": "RemoteTool",
        "authType": "AgenticIdentityToken",
        "target": MCP_URL,
        "audience": APP_URI,
        "metadata": {"type": "generic_mcp"},
    }
    properties.update(overrides)
    return {"name": "docwiki-mcp", "properties": properties}


def test_postprovision_end_to_end_with_agents(runner: FakeRunner, tmp_path: Path) -> None:
    """ADR 0003 order: registration -> auth -> connection -> agents -> roles -> allowlist."""
    agents_repo(tmp_path)
    provisioned(runner)
    runner.rules = [
        rule
        for rule in runner.rules
        if "authConfigs" not in rule[0].pattern and "auth show" not in rule[0].pattern
    ]
    runner.queue(
        r"GET .*authConfigs/current", not_found(), AUTH_OK, AUTH_OK, auth_allowing("r", "l")
    )
    runner.queue(r"^az containerapp auth show", auth_shown(), auth_shown("r", "l"))
    runner.on(r"GET .*connections/docwiki-mcp\?", not_found())
    runner.on(r"PUT .*connections/docwiki-mcp\?", connection())
    report = deploy_report(("researcher", "r"), ("librarian", "l"))
    runner.on(r"deploy\.py --json", report)
    environ = {**base_env(), **agent_env()}
    del environ["DOCWIKI_MCP_API_CLIENT_ID"], environ["DOCWIKI_MCP_API_AUDIENCE"]
    code = postprovision.main([], runner=runner, environ=environ, root=tmp_path)
    assert code == 0
    put = runner.commands(r"PUT .*connections/docwiki-mcp")
    assert len(put) == 1
    assert f"{CONNECTION_PATH}?api-version=2025-10-01-preview" in put[0]
    assert runner.body_for(r"PUT .*connections/docwiki-mcp")[0] == {
        "properties": connection()["properties"]
    }
    granted = {
        (body["principalId"], body["appRoleId"])
        for body in runner.body_for(r"POST .*appRoleAssignedTo")
    }
    read, operate = (entra.app_role_id(role) for role in (entra.ROLE_READ, entra.ROLE_OPERATE))
    assert granted == {("r", read), ("l", read), ("l", operate)}
    parameters = auth_parameters(runner)
    assert [item["allowedApplications"]["value"] for item in parameters] == [[], ["r", "l"]]
    assert runner.commands(r"^azd env set DOCWIKI_MCP_ALLOWED_CLIENT_IDS r,l --environment demo")
    assert runner.commands(r"^azd env set DOCWIKI_MCP_CONNECTION docwiki-mcp")
    lines = [" ".join(call) for call in runner.calls]

    def first(pattern: str) -> int:
        return next(i for i, line in enumerate(lines) if pattern in line)

    steps = [
        first(pattern)
        for pattern in (
            f"--method POST --url {azdlib.GRAPH}",
            "ingress enable",
            "--method PUT",
            "deploy.py",
            "appRoleAssignedTo",
        )
    ]
    assert steps == sorted(steps), "registration, secured ingress, connection, agents, roles"
    last_auth = max(i for i, line in enumerate(lines) if "deployment group create" in line)
    assert last_auth > steps[-1], "the allowlist is applied after the role assignments"
    # The server's own caller allowlist follows the built-in auth allowlist, once verified.
    assert exposure_order(runner) == [
        "auth-deploy",
        "auth-verify",
        "settings",
        "ingress",
        "auth-deploy",
        "auth-verify",
        "settings",
    ]
    updates = runner.commands(r"^az containerapp update")
    assert f"--set-env-vars DOCWIKI_MCP_AUDIENCE={APP_URI},{APP} --output" in updates[0]
    assert "--set-env-vars DOCWIKI_MCP_ALLOWED_CLIENT_IDS=r,l --output" in updates[1]
    state = json.loads(azdlib.state_path(ENV, tmp_path).read_text(encoding="utf-8"))
    assert state["mcp_allowed_applications"] == {"researcher": "r", "librarian": "l"}
    assert state["agents"]["librarian"]["client_id"] == "l"


def test_connection_matches_arm_properties() -> None:
    wanted = {"target": MCP_URL, "audience": APP_URI}
    assert postprovision.connection_matches(connection(), **wanted)
    assert postprovision.connection_matches(connection(target=MCP_URL + "/"), **wanted)
    assert not postprovision.connection_matches(
        connection(authType="ProjectManagedIdentity"), **wanted
    )
    assert not postprovision.connection_matches(connection(audience=APP), **wanted)
    unechoed = connection()
    del unechoed["properties"]["audience"]
    assert not postprovision.connection_matches(unechoed, **wanted), "re-applied when unknown"
    assert not postprovision.connection_matches(None, **wanted)


def test_connection_body_matches_the_bicep_module() -> None:
    body = postprovision.connection_body(MCP_URL, APP_URI)["properties"]
    module = (REPO_ROOT / "infra" / "modules" / "mcp-connection.bicep").read_text(encoding="utf-8")
    assert f"category: '{body['category']}'" in module
    assert f"authType: '{body['authType']}'" in module
    assert f"type: '{body['metadata']['type']}'" in module
    assert f"@{postprovision.CONNECTIONS_API}'" in module


def test_mcp_connection_unchanged_is_not_rewritten(runner: FakeRunner, tmp_path: Path) -> None:
    agents_repo(tmp_path)
    runner.on(r"GET .*connections/docwiki-mcp\?", connection())
    ctx = context(runner, tmp_path, DOCWIKI_MCP_CONNECTION="docwiki-mcp")
    postprovision.step_mcp_connection(ctx)
    assert not runner.commands(r"PUT ")
    assert not runner.commands(r"^azd env set"), "name already recorded"
    assert ctx.state["mcp_connection"]["auth_type"] == "AgenticIdentityToken"


def test_mcp_connection_with_another_audience_is_updated(
    runner: FakeRunner, tmp_path: Path
) -> None:
    agents_repo(tmp_path)
    runner.on(r"GET .*connections/docwiki-mcp\?", connection(audience=f"api://{APP}-previous"))
    runner.on(r"PUT .*connections/docwiki-mcp\?", connection())
    runner.on(r"^azd env set", None)
    postprovision.step_mcp_connection(context(runner, tmp_path))
    assert runner.body_for(r"PUT ")[0]["properties"]["audience"] == APP_URI


def test_stale_sign_in_is_reported_clearly(runner: FakeRunner, tmp_path: Path) -> None:
    refused = Result(1, "", "ERROR: TokenCreatedWithOutdatedPolicies: InteractionRequired")
    runner.on(r"GET .*connections/", refused)
    agents_repo(tmp_path)
    with pytest.raises(HookError) as raised:
        postprovision.step_mcp_connection(context(runner, tmp_path))
    assert "az login" in (raised.value.remediation or "")


def test_agents_step_runs_deploy_json_and_records_identities(
    runner: FakeRunner, tmp_path: Path
) -> None:
    agents_repo(tmp_path)
    report = deploy_report(
        ("researcher", "r-id"), ("librarian", "l-id"), client_ids={"librarian": "l-client"}
    )
    runner.on(r"^uv run --project .* --extra azure python .*deploy\.py --json", report)
    ctx = context(runner, tmp_path, DOCWIKI_ENABLE_ROUTINE="true")
    postprovision.step_agents(ctx)
    command = runner.commands(r"deploy\.py")
    assert len(command) == 1 and command[0].endswith("--json --routine enable")
    env = runner.envs[-1] or {}
    assert env["DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"] == PROJECT
    assert env["DOCWIKI_MCP_CONNECTION"] == "docwiki-mcp"
    assert env["DOCWIKI_MCP_URL"] == MCP_URL
    assert env["DOCWIKI_SMART_DEPLOYMENT"] == "smart"
    researcher, librarian = ctx.state["agents"]["researcher"], ctx.state["agents"]["librarian"]
    assert researcher["principal_id"] == "r-id" and researcher["client_id"] == "r-id"
    assert librarian["principal_id"] == "l-id" and librarian["client_id"] == "l-client"
    assert ctx.state["routine_enabled"] is True


def test_recreated_agent_identity_is_reported(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    agents_repo(tmp_path)
    runner.on(r"deploy\.py --json", deploy_report(("librarian", "new-id")))
    state = {"agents": {"librarian": {"principal_id": "old-id", "client_id": "old-id"}}}
    ctx = context(runner, tmp_path, state)
    postprovision.step_agents(ctx)
    assert "new agent identity" in capsys.readouterr().out
    assert ctx.state["agents"]["librarian"]["client_id"] == "new-id"


def test_agent_definitions_must_use_their_own_identity(runner: FakeRunner, tmp_path: Path) -> None:
    agents_repo(tmp_path, "project-managed-identity")
    with pytest.raises(HookError) as raised:
        postprovision.step_agents(context(runner, tmp_path))
    assert "project-managed-identity" in str(raised.value)
    assert "auth.strategy: per-agent-identity" in (raised.value.remediation or "")
    assert not runner.calls, "nothing deployed"


def test_routine_enabled_before_is_disabled(runner: FakeRunner, tmp_path: Path) -> None:
    agents_repo(tmp_path)
    runner.on(r"deploy\.py --json --routine disable", deploy_report(("librarian", "l-id")))
    ctx = context(runner, tmp_path, {"routine_enabled": True}, DOCWIKI_ENABLE_ROUTINE="false")
    postprovision.step_agents(ctx)
    assert ctx.state["routine_enabled"] is False
    runner.calls.clear()
    runner.on(r"deploy\.py --json$", deploy_report(("librarian", "l-id")))
    postprovision.step_agents(ctx)
    assert runner.commands(r"deploy\.py --json$"), "no routine flag once disabled"


def test_deploy_failure_shows_the_script_error(runner: FakeRunner, tmp_path: Path) -> None:
    agents_repo(tmp_path)
    failure = Result(2, "", "error: project connection 'docwiki-mcp' does not exist")
    runner.on(r"deploy\.py", failure)
    with pytest.raises(HookError) as raised:
        postprovision.step_agents(context(runner, tmp_path))
    assert "does not exist" in str(raised.value) and "exit code 2" in str(raised.value)


def test_deploy_output_parsing_tolerates_noise() -> None:
    text = "Resolved 42 packages\n" + deploy_report(("researcher", "r-id")) + "\ndone\n"
    assert postprovision.parse_deploy_output(text)["agents"][0]["key"] == "researcher"
    with pytest.raises(HookError):
        postprovision.parse_deploy_output("no json here")


def test_agents_skipped_on_request(runner: FakeRunner, tmp_path: Path) -> None:
    agents_repo(tmp_path)
    ctx = context(runner, tmp_path, DOCWIKI_SKIP_AGENTS="true")
    postprovision.step_mcp_connection(ctx)
    postprovision.step_agents(ctx)
    assert not runner.calls


def test_agent_roles_from_reported_identities(runner: FakeRunner, tmp_path: Path) -> None:
    state_file = azdlib.state_path(ENV, tmp_path)
    azdlib.save_state(
        state_file,
        {"agents": {"researcher": {"principal_id": "r-id"}, "librarian": {"principal_id": "l-id"}}},
    )
    code = postprovision.main(
        ["--only", "mcp-api,agent-roles"],
        runner=provisioned(runner),
        environ=base_env(),
        root=tmp_path,
    )
    assert code == 0
    principals = {body["principalId"] for body in runner.body_for(r"POST .*appRoleAssignedTo")}
    assert principals == {"r-id", "l-id"}


def test_unknown_steps_are_rejected(runner: FakeRunner, tmp_path: Path) -> None:
    assert (
        postprovision.main(["--only", "nope"], runner=runner, environ=base_env(), root=tmp_path)
        == 2
    )


def test_shared_agent_principal_gets_read_only(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    operate = entra.app_role_id(entra.ROLE_OPERATE)
    runner.on(
        r"GET .*appRoleAssignedTo",
        {"value": [{"id": "old-operate", "principalId": "shared-id", "appRoleId": operate}]},
    )
    runner.on(r"DELETE .*appRoleAssignedTo/old-operate", None)
    runner.on(r"POST .*appRoleAssignedTo", {"id": "as-read"})
    state = {
        "mcp_api": {"service_principal_id": "sp-1"},
        "agents": {
            "researcher": {"principal_id": "shared-id"},
            "librarian": {"principal_id": "shared-id"},
        },
        "app_role_assignments": [
            {"agent": "librarian", "role": entra.ROLE_OPERATE, "principal_id": "shared-id"}
        ],
    }
    ctx = context(runner, tmp_path, state)
    postprovision.step_agent_roles(ctx)
    posted = {body["appRoleId"] for body in runner.body_for(r"POST .*appRoleAssignedTo")}
    assert posted == {entra.app_role_id(entra.ROLE_READ)}
    assert runner.commands(r"DELETE .*appRoleAssignedTo/old-operate")
    roles = {item["role"] for item in ctx.state["app_role_assignments"]}
    assert roles == {entra.ROLE_READ}
    output = capsys.readouterr().out
    assert "Wiki.Operate withheld" in output and ADR_PATH in output


def test_allowlist_lists_client_ids_and_honours_blocks(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner.queue(
        r"GET .*authConfigs/current",
        auth_allowing("r-client", "l-client"),
        auth_allowing("r-client"),
    )
    runner.on(r"^az deployment group create", None)
    runner.on(r"^azd env set", None)
    runner.on(r"^az containerapp auth show", auth_shown("r-client"))
    runner.on(MCP_APP_GET, mcp_app(server_settings("r-client", "l-client"), external=True))
    runner.on(r"^az containerapp update", None)
    state = {
        "agents": {
            "researcher": {"principal_id": "r-id", "client_id": "r-client"},
            "librarian": {"principal_id": "l-id", "client_id": "l-client"},
        }
    }
    ctx = context(
        runner,
        tmp_path,
        state,
        DOCWIKI_MCP_APP_NAME=MCP_APP,
        DOCWIKI_MCP_ALLOWED_CLIENT_IDS="r-client,l-client",
        DOCWIKI_MCP_BLOCKED_AGENTS="librarian",
    )
    postprovision.step_mcp_allowlist(ctx)
    assert auth_parameters(runner)[0]["allowedApplications"]["value"] == ["r-client"]
    assert runner.commands(r"^azd env set DOCWIKI_MCP_ALLOWED_CLIENT_IDS r-client --environment")
    assert ctx.state["mcp_allowed_applications"] == {"researcher": "r-client"}
    assert "librarian is blocked" in capsys.readouterr().out
    # The server's own caller allowlist drops the blocked agent too (after verification).
    assert exposure_order(runner) == ["auth-deploy", "auth-verify", "settings"]
    update = runner.commands(r"^az containerapp update")[0]
    assert "--set-env-vars DOCWIKI_MCP_ALLOWED_CLIENT_IDS=r-client --output none" in update
    assert not runner.commands(r"ingress enable"), "already external"


def test_allowlist_already_applied_is_not_redeployed(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*authConfigs/current", auth_allowing("r-id", "l-id"))
    runner.on(r"^az containerapp auth show", auth_shown("r-id", "l-id"))
    runner.on(MCP_APP_GET, mcp_app(server_settings("r-id", "l-id"), external=True))
    state = {
        "agents": {"researcher": {"principal_id": "r-id"}, "librarian": {"principal_id": "l-id"}}
    }
    ctx = context(
        runner,
        tmp_path,
        state,
        DOCWIKI_MCP_APP_NAME=MCP_APP,
        DOCWIKI_MCP_ALLOWED_CLIENT_IDS="r-id,l-id",
    )
    postprovision.step_mcp_allowlist(ctx)
    assert not runner.commands(
        r"deployment group create|^azd env set|containerapp update|ingress enable"
    )


def test_blocking_every_agent_removes_the_server_allowlist(
    runner: FakeRunner, tmp_path: Path
) -> None:
    runner.queue(r"GET .*authConfigs/current", auth_allowing("r", "l"), AUTH_OK)
    runner.on(r"^az deployment group create", None)
    runner.on(r"^azd env set", None)
    runner.on(r"^az containerapp auth show", auth_shown())
    runner.on(MCP_APP_GET, mcp_app(server_settings("r", "l"), external=True))
    runner.on(r"^az containerapp update", None)
    state = {
        "agents": {
            "researcher": {"principal_id": "r", "client_id": "r"},
            "librarian": {"principal_id": "l", "client_id": "l"},
        }
    }
    ctx = context(
        runner,
        tmp_path,
        state,
        DOCWIKI_MCP_APP_NAME=MCP_APP,
        DOCWIKI_MCP_ALLOWED_CLIENT_IDS="r,l",
        DOCWIKI_MCP_BLOCKED_AGENTS="researcher,librarian",
    )
    postprovision.step_mcp_allowlist(ctx)
    updates = runner.commands(r"^az containerapp update")
    assert len(updates) == 1
    assert "--remove-env-vars DOCWIKI_MCP_ALLOWED_CLIENT_IDS --output none" in updates[0]


@pytest.mark.parametrize(
    ("shown", "problem"),
    [
        (auth_shown(enabled=False), "built-in auth is not enabled"),
        ({}, "built-in auth is not enabled"),
        (auth_shown("someone-else"), "the allowed applications differ"),
        (
            {**auth_shown(), "globalValidation": {"unauthenticatedClientAction": "AllowAnonymous"}},
            "not answered with Return401",
        ),
    ],
)
def test_mcp_ingress_waits_for_verified_auth(
    runner: FakeRunner, tmp_path: Path, shown: dict[str, Any], problem: str
) -> None:
    """Auth that ``az containerapp auth show`` does not confirm keeps the MCP app private."""
    runner.on(r"GET .*authConfigs/current", AUTH_OK)
    runner.on(r"^az containerapp auth show", shown)
    ctx = context(runner, tmp_path, DOCWIKI_MCP_APP_NAME=MCP_APP)
    with pytest.raises(HookError) as raised:
        postprovision.step_mcp_auth(ctx)
    assert problem in str(raised.value)
    assert "external ingress stays disabled" in str(raised.value)
    assert "az containerapp auth show" in (raised.value.remediation or "")
    assert not runner.commands(r"containerapp update|ingress enable")
    assert not runner.commands(MCP_APP_GET), "nothing else is touched"
    assert "mcp_auth" not in ctx.state


def test_failed_auth_deployment_never_enables_ingress(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*authConfigs/current", not_found())
    runner.on(r"^az deployment group create", Result(1, "", "ERROR: deployment refused"))
    ctx = context(runner, tmp_path, DOCWIKI_MCP_APP_NAME=MCP_APP)
    with pytest.raises(HookError) as raised:
        postprovision.step_mcp_auth(ctx)
    assert "deployment refused" in str(raised.value)
    assert "does not enable external ingress" in str(raised.value)
    assert "azd provision" in (raised.value.remediation or "")
    assert not runner.commands(r"auth show|containerapp update|ingress enable")


def test_secured_mcp_app_is_left_unchanged(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*authConfigs/current", AUTH_OK)
    runner.on(r"^az containerapp auth show", auth_shown())
    runner.on(MCP_APP_GET, mcp_app(server_settings(), external=True))
    ctx = context(runner, tmp_path, DOCWIKI_MCP_APP_NAME=MCP_APP)
    postprovision.step_mcp_auth(ctx)
    assert exposure_order(runner) == ["auth-verify"]
    assert ctx.state["mcp_auth"]["app"] == MCP_APP


def test_token_validation_opt_out_reaches_the_server(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner.on(r"GET .*authConfigs/current", AUTH_OK)
    runner.on(r"^az containerapp auth show", auth_shown())
    runner.on(MCP_APP_GET, mcp_app(server_settings(), external=True))
    runner.on(r"^az containerapp update", None)
    ctx = context(
        runner, tmp_path, DOCWIKI_MCP_APP_NAME=MCP_APP, DOCWIKI_MCP_TOKEN_VALIDATION="off"
    )
    postprovision.step_mcp_auth(ctx)
    update = runner.commands(r"^az containerapp update")[0]
    assert "--set-env-vars DOCWIKI_MCP_TOKEN_VALIDATION=off --output none" in update
    assert "WARNING: DOCWIKI_MCP_TOKEN_VALIDATION=off" in capsys.readouterr().out
    runner.calls.clear()
    invalid = context(
        runner, tmp_path, DOCWIKI_MCP_APP_NAME=MCP_APP, DOCWIKI_MCP_TOKEN_VALIDATION="sometimes"
    )
    with pytest.raises(HookError, match="DOCWIKI_MCP_TOKEN_VALIDATION"):
        postprovision.step_mcp_auth(invalid)
    assert not runner.commands(r"containerapp update|ingress enable")


def test_mcp_fqdn_other_than_the_recorded_one_is_reported(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner.on(r"GET .*authConfigs/current", AUTH_OK)
    runner.on(r"^az containerapp auth show", auth_shown())
    runner.on(MCP_APP_GET, mcp_app(server_settings()))
    elsewhere = "ca-mcp-tok123.elsewhere.azurecontainerapps.example"
    runner.on(r"^az containerapp ingress enable", {"external": True, "fqdn": elsewhere})
    postprovision.step_mcp_auth(context(runner, tmp_path, DOCWIKI_MCP_APP_NAME=MCP_APP))
    assert runner.commands(r"ingress enable .*--output json")
    assert f"answers at {elsewhere}, not at DOCWIKI_MCP_FQDN" in capsys.readouterr().out


def test_unknown_blocked_agent_is_rejected(runner: FakeRunner, tmp_path: Path) -> None:
    ctx = context(runner, tmp_path, DOCWIKI_MCP_BLOCKED_AGENTS="nobody")
    with pytest.raises(HookError):
        postprovision.step_mcp_allowlist(ctx)


def test_auth_already_configured_is_not_redeployed(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*authConfigs/current", AUTH_OK)
    spec = postprovision.AuthSpec("app-1", (APP_URI,), "Return401", ("/healthz",))
    deployed = postprovision.apply_auth(tools(runner, tmp_path), MCP_APP, spec, deployment_name="d")
    assert deployed is False
    assert not runner.commands(r"deployment group create")


def test_auth_with_a_client_secret_or_v1_issuer_is_reapplied(
    runner: FakeRunner, tmp_path: Path
) -> None:
    spec = postprovision.AuthSpec("app-1", (APP_URI,), "Return401", ("/healthz",))
    secret = json.loads(json.dumps(AUTH_OK))
    registration = secret["properties"]["identityProviders"]["azureActiveDirectory"]["registration"]
    registration["clientSecretSettingName"] = "microsoft-provider-authentication-secret"
    assert not postprovision.auth_matches(secret, spec)
    registration.pop("clientSecretSettingName")
    registration["openIdIssuer"] = "https://sts.windows.net/tenant-test/"
    assert not postprovision.auth_matches(secret, spec)
    assert postprovision.auth_matches(AUTH_OK, spec)


def test_auth_verification_failure_is_an_error(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*authConfigs/current", not_found())
    runner.on(r"^az deployment group create", None)
    spec = postprovision.AuthSpec("app-1", (APP_URI,), "Return401", ("/healthz",))
    with pytest.raises(HookError):
        postprovision.apply_auth(tools(runner, tmp_path), MCP_APP, spec, deployment_name="d")


def test_content_understanding_defaults_when_requested(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"PATCH .*contentunderstanding/defaults", None)
    t = tools(runner, tmp_path, DOCWIKI_CU_DEFAULTS="true", DOCWIKI_CU_EMBEDDING_DEPLOYMENT="emb")
    ctx = postprovision.Context(tools=t, state={}, state_file=azdlib.state_path(ENV, tmp_path))
    postprovision.step_content_understanding(ctx)
    command = runner.commands(r"contentunderstanding/defaults")[0]
    assert "api-version=2025-11-01" in command
    assert "--resource https://cognitiveservices.azure.com" in command
    assert runner.body_for(r"contentunderstanding")[0] == {
        "modelDeployments": {
            "prebuilt-analyzer-completion": "smart",
            "prebuilt-analyzer-completion-mini": "fast",
            "prebuilt-analyzer-embedding": "emb",
        }
    }


def test_portal_flow_configures_sign_in_then_ingress(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"^az account show", {"id": SUB, "user": {"type": "user"}})
    runner.on(r"^az account get-access-token", {"accessToken": fake_token({"oid": "user-oid"})})
    portal_app = {
        "id": "pobj",
        "appId": "portal-app",
        "displayName": f"docwiki-portal-{ENV}-{TOKEN}",
        "tags": [f"docwiki-env:{ENV}-{TOKEN}"],
        "web": {},
    }
    runner.on(r"GET .*applications\?\$filter", {"value": []})
    runner.on(r"POST .*/applications ", portal_app)
    runner.on(r"PATCH .*/applications/pobj", None)
    runner.on(r"GET .*servicePrincipals\(appId='portal-app'\)", not_found())
    runner.on(r"POST .*/servicePrincipals ", {"id": "psp", "appRoleAssignmentRequired": True})
    runner.on(r"GET .*/servicePrincipals/psp/owners", {"value": []})
    runner.on(r"POST .*/owners/\$ref", None)
    runner.on(r"^azd env set", None)
    runner.on(r"GET .*appRoleAssignedTo", {"value": []})
    runner.on(r"POST .*appRoleAssignedTo", {"id": "default-access"})
    portal_config = json.loads(json.dumps(AUTH_OK))
    portal_config["properties"]["globalValidation"] = {
        "unauthenticatedClientAction": "RedirectToLoginPage"
    }
    provider = portal_config["properties"]["identityProviders"]["azureActiveDirectory"]
    provider["registration"]["clientId"] = "portal-app"
    provider["validation"]["allowedAudiences"] = ["portal-app"]
    runner.queue(r"GET .*authConfigs/current", not_found(), portal_config)
    runner.on(r"^az deployment group create", None)
    runner.on(r"GET .*containerApps/ca-portal-tok123\?", {"properties": {"configuration": {}}})
    runner.on(r"^az containerapp ingress enable", None)
    code = postprovision.main(
        ["--only", "portal"],
        runner=runner,
        environ=base_env(DOCWIKI_ENABLE_PORTAL="true"),
        root=tmp_path,
    )
    assert code == 0
    web = runner.body_for(r"POST .*/applications ")[0]["web"]
    assert web["redirectUris"] == [
        "https://ca-portal-tok123.region.azurecontainerapps.example/.auth/login/aad/callback"
    ]
    assert web["implicitGrantSettings"] == {
        "enableIdTokenIssuance": True,
        "enableAccessTokenIssuance": False,
    }
    assert (
        runner.body_for(r"POST .*appRoleAssignedTo")[0]["appRoleId"] == entra.DEFAULT_ACCESS_ROLE_ID
    )
    order = [
        line
        for line in (" ".join(call) for call in runner.calls)
        if "deployment group create" in line or "ingress enable" in line
    ]
    assert "deployment group create" in order[0] and "ingress enable" in order[1], "auth first"
    assert not runner.commands(r"credential reset|secret"), "no client secret is ever created"


@pytest.mark.parametrize(("anonymous", "expected"), [("true", "no sign-in"), ("false", "stays")])
def test_public_portal_registers_nothing(
    runner: FakeRunner,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    anonymous: str,
    expected: str,
) -> None:
    code = postprovision.main(
        ["--only", "portal"],
        runner=runner,
        environ=base_env(
            DOCWIKI_ENABLE_PORTAL="true",
            DOCWIKI_PORTAL_ACCESS="public",
            DOCWIKI_PORTAL_ANONYMOUS=anonymous,
        ),
        root=tmp_path,
    )
    assert code == 0
    assert not runner.calls, "no Entra registration, auth config or ingress change"
    assert expected in capsys.readouterr().out


STUDIO_ID = "studio-app"
STUDIO_CALLBACK = f"https://{STUDIO_FQDN}/.auth/login/aad/callback"
STUDIO_GET = rf"GET .*containerApps/{STUDIO_APP}\?"
STUDIO_ENV = {"DOCWIKI_ENABLE_STUDIO": "true"}


def studio_auth_properties(
    *,
    enabled: bool = True,
    action: str = "RedirectToLoginPage",
    excluded: tuple[str, ...] = ("/healthz", "/livez"),
    allowed: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Built-in auth of the Studio app as ``az containerapp auth show`` prints it."""
    validation: dict[str, Any] = {"allowedAudiences": [STUDIO_ID]}
    if allowed:
        validation["defaultAuthorizationPolicy"] = {"allowedApplications": list(allowed)}
    return {
        "platform": {"enabled": enabled},
        "globalValidation": {
            "unauthenticatedClientAction": action,
            "excludedPaths": list(excluded),
        },
        "identityProviders": {
            "azureActiveDirectory": {
                "enabled": True,
                "registration": {"clientId": STUDIO_ID, "openIdIssuer": ISSUER},
                "validation": validation,
            }
        },
        "login": {"tokenStore": {"enabled": False}},
    }


def studio_app_view(env: dict[str, str] | None = None, *, external: bool = False) -> dict[str, Any]:
    """ARM view of the Studio container app."""
    container = {
        "name": "studio",
        "image": "mcr.microsoft.com/dotnet/samples:aspnetapp",
        "env": [{"name": key, "value": value} for key, value in (env or {}).items()],
    }
    configuration = {"ingress": {"external": True, "fqdn": STUDIO_FQDN}} if external else {}
    return {"properties": {"configuration": configuration, "template": {"containers": [container]}}}


def studio_azure(
    runner: FakeRunner,
    *,
    shown: dict[str, Any] | None = None,
    deployment: Result | None = None,
) -> FakeRunner:
    """Fake Azure for a first Studio provision: no app registration, no built-in auth yet."""
    runner.on(r"^az account show", {"id": SUB, "user": {"type": "user"}})
    runner.on(r"^az account get-access-token", {"accessToken": fake_token({"oid": "user-oid"})})
    runner.on(r"GET .*applications\?\$filter", {"value": []})
    runner.on(r"POST .*/applications ", {"id": "studio-obj", "appId": STUDIO_ID, "web": {}})
    runner.on(r"PATCH .*/applications/studio-obj", None)
    runner.on(rf"GET .*servicePrincipals\(appId='{STUDIO_ID}'\)", not_found())
    runner.on(r"POST .*/servicePrincipals ", {"id": "studio-sp", "appRoleAssignmentRequired": True})
    runner.on(r"GET .*/servicePrincipals/studio-sp/owners", {"value": []})
    runner.on(r"POST .*/owners/\$ref", None)
    runner.on(r"GET .*appRoleAssignedTo", {"value": []})
    runner.on(r"POST .*appRoleAssignedTo", {"id": "default-access"})
    runner.on(r"^azd env set", None)
    runner.queue(
        r"GET .*authConfigs/current", not_found(), {"properties": studio_auth_properties()}
    )
    runner.on(r"^az deployment group create", deployment)
    runner.on(r"^az containerapp auth show", studio_auth_properties() if shown is None else shown)
    runner.on(STUDIO_GET, studio_app_view())
    runner.on(r"^az containerapp update", None)
    runner.on(r"^az containerapp ingress enable", {"external": True, "fqdn": STUDIO_FQDN})
    return runner


def test_studio_flow_registers_its_owner_secures_then_exposes(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = postprovision.main(
        ["--only", "studio"],
        runner=studio_azure(runner),
        environ=base_env(**STUDIO_ENV),
        root=tmp_path,
    )
    assert code == 0
    created = runner.body_for(r"POST .*/applications ")[0]
    assert created["displayName"] == f"docwiki-studio-{ENV}-{TOKEN}"
    assert created["description"] == "DocWiki Studio sign-in (owner only)."
    assert created["signInAudience"] == "AzureADMyOrg"
    assert created["web"] == {
        "redirectUris": [STUDIO_CALLBACK],
        "implicitGrantSettings": {
            "enableIdTokenIssuance": True,
            "enableAccessTokenIssuance": False,
        },
    }
    assert runner.body_for(r"POST .*/servicePrincipals ")[0]["appRoleAssignmentRequired"] is True
    state = json.loads(azdlib.state_path(ENV, tmp_path).read_text(encoding="utf-8"))
    assert state["studio_app"]["app_id"] == STUDIO_ID
    assert state["studio_app"]["created_by_hook"] is True
    assert state["studio_app"]["service_principal_id"] == "studio-sp"
    assert "portal_app" not in state
    sets = runner.commands(r"^azd env set")
    assert any(f"DOCWIKI_STUDIO_CLIENT_ID {STUDIO_ID} --environment demo" in s for s in sets)
    assert any("DOCWIKI_STUDIO_ALLOWED_PRINCIPALS user-oid --environment demo" in s for s in sets)
    # Sign-in requires an assignment: the deployer is the only user assigned.
    assert runner.body_for(r"POST .*appRoleAssignedTo") == [
        {
            "principalId": "user-oid",
            "resourceId": "studio-sp",
            "appRoleId": entra.DEFAULT_ACCESS_ROLE_ID,
        }
    ]
    (parameters,) = auth_parameters(runner)
    assert parameters["containerAppName"]["value"] == STUDIO_APP
    assert parameters["clientId"]["value"] == STUDIO_ID
    assert parameters["allowedAudiences"]["value"] == [STUDIO_ID]
    assert parameters["unauthenticatedClientAction"]["value"] == "RedirectToLoginPage"
    assert parameters["excludedPaths"]["value"] == ["/healthz", "/livez"]
    assert parameters["allowedApplications"]["value"] == []
    deployment = runner.commands(r"^az deployment group create")[0]
    assert "--name docwiki-studio-auth" in deployment and "app-auth.bicep" in deployment
    # Fail closed: auth applied and verified, then the owner allowlist, then ingress.
    assert exposure_order(runner) == ["auth-deploy", "auth-verify", "settings", "ingress"]
    update = runner.commands(r"^az containerapp update")[0]
    assert f"--name {STUDIO_APP}" in update and "--container-name studio" in update
    assert "--set-env-vars DOCWIKI_STUDIO_ALLOWED_PRINCIPALS=user-oid --output none" in update
    (ingress,) = runner.commands(r"ingress enable")
    assert f"--name {STUDIO_APP}" in ingress and "--type external" in ingress
    assert "--target-port 8080" in ingress
    assert not runner.commands(r"credential reset|secret"), "no client secret is ever created"
    assert not list((tmp_path / ".azure" / ENV / "hook-tmp").glob("*.json")), "bodies cleaned up"
    output = capsys.readouterr().out
    assert f"studio ready at https://{STUDIO_FQDN}/ (Entra sign-in, owner only)" in output
    assert "owner allowlist" not in output, "set now, not 'already up to date'"


def test_studio_auth_declared_by_the_hook_is_what_bicep_declares(
    runner: FakeRunner, tmp_path: Path
) -> None:
    postprovision.main(
        ["--only", "studio"],
        runner=studio_azure(runner),
        environ=base_env(**STUDIO_ENV),
        root=tmp_path,
    )
    (parameters,) = auth_parameters(runner)
    bicep = (REPO_ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    block = bicep[bicep.index("module studioAuth") : bicep.index("module budget")]
    action = parameters["unauthenticatedClientAction"]["value"]
    assert f"unauthenticatedClientAction: '{action}'" in block
    assert re.findall(r"'(/[a-z]+)'", block) == parameters["excludedPaths"]["value"]
    assert re.search(r"allowedAudiences: \[\s*studioClientId\s*\]", block)
    assert "allowedApplications" not in block and parameters["allowedApplications"]["value"] == []
    # The values the hook writes to the azd environment are the ones Bicep reads.
    mapped = json.loads((REPO_ROOT / "infra" / "main.parameters.json").read_text("utf-8"))
    assert mapped["parameters"]["studioClientId"]["value"] == "${DOCWIKI_STUDIO_CLIENT_ID}"
    assert mapped["parameters"]["studioAllowedPrincipals"]["value"] == (
        "${" + postprovision.STUDIO_PRINCIPALS_SETTING + "}"
    )
    assert runner.commands(rf"^azd env set {postprovision.STUDIO_PRINCIPALS_SETTING} ")


def test_studio_step_follows_the_portal_step() -> None:
    names = [name for name, _ in postprovision.STEPS]
    assert names.index("studio") == names.index("portal") + 1
    assert "``studio``" in (postprovision.__doc__ or "")


def test_studio_second_run_changes_nothing(runner: FakeRunner, tmp_path: Path) -> None:
    azdlib.save_state(
        azdlib.state_path(ENV, tmp_path),
        {
            "studio_app": {
                "app_id": STUDIO_ID,
                "object_id": "studio-obj",
                "display_name": f"docwiki-studio-{ENV}-{TOKEN}",
                "service_principal_id": "studio-sp",
                "created_by_hook": True,
            }
        },
    )
    runner.on(r"^az account show", {"id": SUB, "user": {"type": "user"}})
    runner.on(r"^az account get-access-token", {"accessToken": fake_token({"oid": "user-oid"})})
    registered = {
        "id": "studio-obj",
        "appId": STUDIO_ID,
        "web": {
            "redirectUris": [STUDIO_CALLBACK],
            "implicitGrantSettings": {
                "enableIdTokenIssuance": True,
                "enableAccessTokenIssuance": False,
            },
        },
    }
    runner.on(rf"GET .*applications\(appId='{STUDIO_ID}'\)", registered)
    runner.on(
        rf"GET .*servicePrincipals\(appId='{STUDIO_ID}'\)",
        {"id": "studio-sp", "appRoleAssignmentRequired": True},
    )
    runner.on(r"GET .*/servicePrincipals/studio-sp/owners", {"value": [{"id": "user-oid"}]})
    assigned = {"id": "as-1", "principalId": "user-oid", "appRoleId": entra.DEFAULT_ACCESS_ROLE_ID}
    runner.on(r"GET .*appRoleAssignedTo", {"value": [assigned]})
    runner.on(r"GET .*authConfigs/current", {"properties": studio_auth_properties()})
    runner.on(r"^az containerapp auth show", studio_auth_properties())
    settled = {"DOCWIKI_STUDIO_ALLOWED_PRINCIPALS": "user-oid"}
    runner.on(STUDIO_GET, studio_app_view(settled, external=True))
    environ = base_env(
        **STUDIO_ENV,
        DOCWIKI_STUDIO_CLIENT_ID=STUDIO_ID,
        DOCWIKI_STUDIO_ALLOWED_PRINCIPALS="user-oid",
    )
    code = postprovision.main(["--only", "studio"], runner=runner, environ=environ, root=tmp_path)
    assert code == 0
    assert not runner.commands(
        r"--method (POST|PATCH|DELETE)|deployment group create|^azd env set|"
        r"containerapp update|ingress enable"
    )
    assert exposure_order(runner) == ["auth-verify"]


def test_studio_keeps_the_allowed_principals_of_the_environment(
    runner: FakeRunner, tmp_path: Path
) -> None:
    environ = base_env(**STUDIO_ENV, DOCWIKI_STUDIO_ALLOWED_PRINCIPALS="owner-a,owner-b")
    code = postprovision.main(
        ["--only", "studio"], runner=studio_azure(runner), environ=environ, root=tmp_path
    )
    assert code == 0
    assert not runner.commands(r"^azd env set DOCWIKI_STUDIO_ALLOWED_PRINCIPALS")
    update = runner.commands(r"^az containerapp update")[0]
    assert (
        "--set-env-vars DOCWIKI_STUDIO_ALLOWED_PRINCIPALS=owner-a,owner-b --output none" in update
    )


def test_studio_updates_a_stale_allowlist_on_the_running_container(
    runner: FakeRunner, tmp_path: Path
) -> None:
    """On the first provision Bicep ran before the hook set it; later provisions carry it."""
    studio_azure(runner)
    runner.rules = [rule for rule in runner.rules if rule[0].pattern != STUDIO_GET]
    stale = {"DOCWIKI_STUDIO_ALLOWED_PRINCIPALS": "previous-owner"}
    runner.on(STUDIO_GET, studio_app_view(stale))
    ctx = context(runner, tmp_path, **STUDIO_ENV, DOCWIKI_STUDIO_ALLOWED_PRINCIPALS="owner-a")
    postprovision.step_studio(ctx)
    update = runner.commands(r"^az containerapp update")[0]
    assert "--set-env-vars DOCWIKI_STUDIO_ALLOWED_PRINCIPALS=owner-a --output none" in update


@pytest.mark.parametrize("value", [None, "false", "FALSE"])
def test_studio_disabled_registers_nothing(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str], value: str | None
) -> None:
    environ = base_env() if value is None else base_env(DOCWIKI_ENABLE_STUDIO=value)
    code = postprovision.main(["--only", "studio"], runner=runner, environ=environ, root=tmp_path)
    assert code == 0
    assert not runner.calls, "no Entra registration, auth config or ingress change"
    assert "studio disabled" in capsys.readouterr().out


def test_studio_needs_a_user_as_its_owner(
    runner: FakeRunner, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runner.on(r"^az account show", {"id": SUB, "user": {"type": "servicePrincipal", "name": "sp"}})
    runner.on(
        r"^az account get-access-token",
        {"accessToken": fake_token({"oid": "sp-oid", "idtyp": "app"})},
    )
    code = postprovision.main(
        ["--only", "studio"], runner=runner, environ=base_env(**STUDIO_ENV), root=tmp_path
    )
    assert code == 0
    assert not runner.commands(r"graph\.microsoft\.com|deployment group|containerapp|^azd env set")
    output = capsys.readouterr().out
    assert "ServicePrincipal, not a user" in output and "without ingress" in output
    assert "studio ready" not in output


@pytest.mark.parametrize(
    ("shown", "problem"),
    [
        (studio_auth_properties(enabled=False), "built-in auth is not enabled"),
        ({}, "built-in auth is not enabled"),
        (studio_auth_properties(action="Return401"), "not answered with RedirectToLoginPage"),
        (studio_auth_properties(excluded=("/healthz",)), "the excluded paths differ"),
        (studio_auth_properties(allowed=("someone-else",)), "the allowed applications differ"),
    ],
)
def test_studio_ingress_waits_for_verified_auth(
    runner: FakeRunner, tmp_path: Path, shown: dict[str, Any], problem: str
) -> None:
    """Auth that ``az containerapp auth show`` does not confirm keeps the Studio private."""
    studio_azure(runner, shown=shown)
    ctx = context(runner, tmp_path, **STUDIO_ENV)
    with pytest.raises(HookError) as raised:
        postprovision.step_studio(ctx)
    assert problem in str(raised.value)
    assert "external ingress stays disabled" in str(raised.value)
    assert "az containerapp auth show" in (raised.value.remediation or "")
    assert not runner.commands(r"containerapp update|ingress enable")
    assert not runner.commands(rf"containerApps/{STUDIO_APP}\?"), "the app is not even read"


def test_studio_failed_auth_deployment_never_enables_ingress(
    runner: FakeRunner, tmp_path: Path
) -> None:
    studio_azure(runner, deployment=Result(1, "", "ERROR: deployment refused"))
    with pytest.raises(HookError, match="deployment refused"):
        postprovision.step_studio(context(runner, tmp_path, **STUDIO_ENV))
    assert not runner.commands(r"auth show|containerapp update|ingress enable")


def test_studio_unverifiable_registration_stops_before_any_exposure(
    runner: FakeRunner, tmp_path: Path
) -> None:
    """Graph refusing the registration (no Application Developer role) leaves the app private."""
    runner.on(r"^az account show", {"id": SUB, "user": {"type": "user"}})
    runner.on(r"^az account get-access-token", {"accessToken": fake_token({"oid": "user-oid"})})
    runner.on(r"GET .*applications\?\$filter", Result(1, "", "ERROR: Forbidden (403)"))
    with pytest.raises(azdlib.CommandError):
        postprovision.step_studio(context(runner, tmp_path, **STUDIO_ENV))
    assert not runner.commands(r"deployment group|containerapp|^azd env set")


# ---------------------------------------------------------------------------
# postdeploy
# ---------------------------------------------------------------------------


def job(image: str, args: list[str] | None = None) -> dict[str, Any]:
    container: dict[str, Any] = {"name": "c", "image": image}
    if args is not None:
        container["args"] = args
    return {"properties": {"template": {"containers": [container]}}}


def test_reconcile_job_follows_the_job_image(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(
        r"GET .*jobs/caj-reconcile-tok123", job("mcr.microsoft.com/k8se/quickstart-jobs:latest")
    )
    runner.on(r"^az containerapp job update", None)
    t = tools(runner, tmp_path, SERVICE_JOB_IMAGE_NAME="crtok.azurecr.io/docwiki/job-demo:azd-1")
    assert postdeploy.sync_reconcile_job(t) is True
    command = runner.commands(r"containerapp job update")[0]
    assert "--name caj-reconcile-tok123" in command
    assert "--image crtok.azurecr.io/docwiki/job-demo:azd-1" in command
    assert "--args reconcile" in command


def test_reconcile_job_already_in_sync(runner: FakeRunner, tmp_path: Path) -> None:
    image = "crtok.azurecr.io/docwiki/job-demo:azd-1"
    runner.on(r"GET .*jobs/caj-reconcile-tok123", job(image, ["reconcile"]))
    assert (
        postdeploy.sync_reconcile_job(tools(runner, tmp_path, SERVICE_JOB_IMAGE_NAME=image))
        is False
    )
    assert not runner.commands(r"containerapp job update")


def test_reconcile_job_waits_for_a_real_image(runner: FakeRunner, tmp_path: Path) -> None:
    runner.on(r"GET .*jobs/caj-ingest-tok123", job("mcr.microsoft.com/k8se/quickstart-jobs:latest"))
    assert postdeploy.sync_reconcile_job(tools(runner, tmp_path)) is False
    assert not runner.commands(r"containerapp job update")


def test_mcp_smoke_check(tmp_path: Path, runner: FakeRunner) -> None:
    runner.on(r"^az account get-access-token", {"accessToken": ARM_TOKEN})
    runner.on(r"^az containerapp auth show", auth_shown())
    t = tools(runner, tmp_path)

    def healthy(url: str, bearer: str | None, headers: Any) -> int:
        return 200 if url.endswith("/healthz") else 401

    postdeploy.verify_mcp(t, healthy)
    command = runner.commands(r"^az containerapp auth show")[0]
    assert f"--name {MCP_APP} --resource-group {RG} --subscription {SUB}" in command
    with pytest.raises(HookError):
        postdeploy.verify_mcp(t, lambda url, bearer, headers: 200)

    def wrong_audience_accepted(url: str, bearer: str | None, headers: Any) -> int:
        return 200 if bearer else 401

    with pytest.raises(HookError):
        postdeploy.verify_mcp(t, wrong_audience_accepted)
    postdeploy.verify_mcp(t, lambda url, bearer, headers: None, attempts=2, delay_s=0)


def test_smoke_check_sends_a_forged_principal_header_that_must_get_401(
    tmp_path: Path, runner: FakeRunner
) -> None:
    """Without built-in auth, a forged header used to get 200 and every tool."""
    runner.on(r"^az account get-access-token", {"accessToken": ARM_TOKEN})
    runner.on(r"^az containerapp auth show", auth_shown())
    sent: list[dict[str, str]] = []

    def forged_accepted(url: str, bearer: str | None, headers: Any) -> int:
        sent.append(dict(headers or {}))
        if url.endswith("/healthz"):
            return 200
        return 200 if headers and postdeploy.PRINCIPAL_HEADER in headers else 401

    with pytest.raises(HookError) as raised:
        postdeploy.verify_mcp(tools(runner, tmp_path), forged_accepted)
    assert "answered 200 to a forged X-MS-CLIENT-PRINCIPAL header" in str(raised.value)
    assert "ingress disable" in (raised.value.remediation or "")
    forged = next(headers[postdeploy.PRINCIPAL_HEADER] for headers in sent if headers)
    payload = json.loads(base64.b64decode(forged))
    roles = {claim["val"] for claim in payload["claims"] if claim["typ"] == payload["role_typ"]}
    assert roles == {"Wiki.Read", "Wiki.Operate"}, "the forgery claims every app role"
    with pytest.raises(HookError, match="answered 404 to a forged"):
        postdeploy.verify_mcp(
            tools(runner, tmp_path), lambda url, bearer, headers: 404 if headers else 401
        )


@pytest.mark.parametrize(
    "shown",
    [
        auth_shown(enabled=False),
        {},
        {**auth_shown(), "globalValidation": {"unauthenticatedClientAction": "AllowAnonymous"}},
        {"properties": auth_shown(enabled=False)},
    ],
)
def test_smoke_check_requires_enabled_builtin_auth(
    tmp_path: Path, runner: FakeRunner, shown: dict[str, Any]
) -> None:
    """A 401 alone proves nothing: the server answers 401 by itself without built-in auth."""
    runner.on(r"^az containerapp auth show", shown)
    probed: list[str] = []

    def probe(url: str, bearer: str | None, headers: Any) -> int:
        probed.append(url)
        return 401

    with pytest.raises(HookError) as raised:
        postdeploy.verify_mcp(tools(runner, tmp_path), probe)
    assert "built-in auth" in str(raised.value)
    assert "azd hooks run postprovision" in (raised.value.remediation or "")
    assert not probed, "checked before any HTTP probe"


def test_smoke_only_mode_skips_the_jobs(
    tmp_path: Path, runner: FakeRunner, capsys: pytest.CaptureFixture[str]
) -> None:
    runner.on(r"^az account get-access-token", {"accessToken": ARM_TOKEN})
    runner.on(r"^az containerapp auth show", auth_shown())
    seen: list[tuple[str, bool, bool]] = []

    def probe(url: str, bearer: str | None, headers: Any) -> int:
        seen.append((url, bool(bearer), bool(headers)))
        return 200 if url.endswith("/healthz") else 401

    code = postdeploy.main(
        ["--smoke-only"], runner=runner, environ=base_env(), root=tmp_path, probe=probe
    )
    assert code == 0
    assert not runner.commands(r"jobs/|containerapp job")
    url = f"https://{MCP_FQDN}/mcp"
    assert (url, True, False) in seen, "token for another audience"
    assert (url, False, True) in seen, "forged principal header without a token"
    output = capsys.readouterr().out
    assert ARM_TOKEN not in output
    assert "MCP built-in auth is enabled (Return401)" in output
    assert "rejects a forged principal header without a token (401)" in output


def test_smoke_test_failure_fails_the_hook(
    tmp_path: Path, runner: FakeRunner, capsys: pytest.CaptureFixture[str]
) -> None:
    runner.on(r"^az containerapp auth show", {})
    code = postdeploy.main(
        ["--smoke-only"],
        runner=runner,
        environ=base_env(),
        root=tmp_path,
        probe=lambda url, bearer, headers: 401,
    )
    assert code == 1
    assert "built-in auth is not enabled on ca-mcp-tok123" in capsys.readouterr().err


def test_hook_scripts_reject_old_python() -> None:
    for name in ("preprovision.py", "postprovision.py", "postdeploy.py"):
        text = (REPO_ROOT / "scripts" / "hooks" / name).read_text(encoding="utf-8")
        assert (
            "sys.version_info < (3, 12)"
            in text.split("import argparse")[0].split("from pathlib")[0]
        )
