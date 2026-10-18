"""Shared helpers for the DocWiki azd hooks, preflight and teardown scripts.

Standard library only: the hooks run with the Python found on PATH, before any project
environment exists. Every external command goes through :class:`Tools`, so tests replace the
process runner and never call Azure.
"""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_REGIONS = ("swedencentral", "eastus2", "westeurope")
STATE_FILE_NAME = "docwiki-state.json"
STATE_SCHEMA = 1

ARM = "https://management.azure.com"
GRAPH = "https://graph.microsoft.com/v1.0"
COGNITIVE_SERVICES_RESOURCE = "https://cognitiveservices.azure.com"

# Characters that cmd.exe interprets even inside quoted arguments of a .cmd/.bat launcher
# (az on Windows is az.cmd). Arguments containing them must travel through a file.
_BATCH_UNSAFE = re.compile(r"[&|<>^%\"\r\n]")
# Characters that are only safe inside quotes: az.cmd expands `%*` inside an
# `IF EXIST "..." ( ... )` block, so an unquoted `)` (a Microsoft Graph key lookup such as
# `servicePrincipals(appId='...')`) ends the block early ("... was unexpected at this time").
_BATCH_QUOTE = re.compile(r"[()\s,;=]")

_TRUE = {"1", "true", "yes", "on"}
_FALSE = {"0", "false", "no", "off", ""}


class HookError(RuntimeError):
    """A failure with an operator-facing remediation message."""

    def __init__(self, message: str, remediation: str | None = None) -> None:
        super().__init__(message)
        self.remediation = remediation


class ToolMissingError(HookError):
    """A required command-line tool is not on PATH."""


@dataclass(frozen=True)
class Result:
    """Outcome of one external command."""

    returncode: int
    stdout: str = ""
    stderr: str = ""

    @property
    def ok(self) -> bool:
        return self.returncode == 0


class CommandError(HookError):
    """An external command failed."""

    def __init__(self, args: Sequence[str], result: Result) -> None:
        detail = (result.stderr or result.stdout).strip()
        super().__init__(f"command failed ({result.returncode}): {display_command(args)}: {detail}")
        self.args_list = list(args)
        self.result = result


Runner = Callable[..., Result]
"""``runner(args, *, env=None, stream=False) -> Result``; ``stream`` inherits the console."""


def display_command(args: Sequence[str]) -> str:
    """Printable form of a command (bodies are passed by file, never inline)."""
    return " ".join(args)


def resolve_executable(name: str) -> str:
    """Absolute path of ``name`` on PATH (``az`` resolves to ``az.cmd`` on Windows)."""
    found = shutil.which(name)
    if not found:
        raise ToolMissingError(f"'{name}' was not found on PATH", f"Install {name} and retry.")
    return found


def check_batch_arguments(executable: str, args: Sequence[str]) -> None:
    """Refuse arguments that cmd.exe would reinterpret when launching a .cmd/.bat file."""
    if not is_batch_launcher(executable):
        return
    for arg in args:
        if _BATCH_UNSAFE.search(arg):
            raise HookError(
                f"refusing an argument with shell metacharacters for {Path(executable).name}",
                "Pass JSON bodies and parameters through files (@file).",
            )


def is_batch_launcher(executable: str) -> bool:
    """Whether Windows starts ``executable`` through cmd.exe (a .cmd or .bat file)."""
    return executable.lower().endswith((".cmd", ".bat"))


def batch_command_line(executable: str, args: Sequence[str]) -> str:
    """Command line for a .cmd/.bat launcher: every argument that cmd.exe could split or
    reinterpret (spaces, parentheses, ``,;=``) is double-quoted.

    ``check_batch_arguments`` refuses ``"`` and the other metacharacters first, so quoting only
    has to double trailing backslashes (they would otherwise escape the closing quote).
    """
    parts: list[str] = []
    for arg in (executable, *args):
        if arg and not _BATCH_QUOTE.search(arg):
            parts.append(arg)
            continue
        trailing = len(arg) - len(arg.rstrip("\\"))
        parts.append('"' + arg + "\\" * trailing + '"')
    return " ".join(parts)


def subprocess_runner(
    args: Sequence[str], *, env: Mapping[str, str] | None = None, stream: bool = False
) -> Result:
    """Default runner: run a command without a shell; capture UTF-8 output unless streaming."""
    executable = resolve_executable(args[0])
    check_batch_arguments(executable, args[1:])
    command: str | list[str] = [executable, *args[1:]]
    if os.name == "nt" and is_batch_launcher(executable):
        # Python quotes only arguments with spaces; cmd.exe also needs quoted parentheses.
        command = batch_command_line(executable, args[1:])
    completed = subprocess.run(
        command,
        capture_output=not stream,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=dict(env) if env is not None else None,
        check=False,
    )
    return Result(completed.returncode, completed.stdout or "", completed.stderr or "")


def is_true(value: str | None, default: bool = False) -> bool:
    """Parse an azd environment boolean ("true"/"false", case-insensitive)."""
    if value is None:
        return default
    text = value.strip().lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False if text else default
    raise HookError(f"expected a boolean, got {value!r}")


def parse_version(text: str) -> tuple[int, ...]:
    """First dotted number in ``text`` as a tuple (``'azd version 1.28.1 (...)'`` -> (1, 28, 1))."""
    match = re.search(r"(\d+(?:\.\d+)+)", text)
    if not match:
        raise ValueError(f"no version number in {text!r}")
    return tuple(int(part) for part in match.group(1).split("."))


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def info(message: str) -> None:
    print(f"[docwiki] {message}", flush=True)


def warn(message: str) -> None:
    print(f"[docwiki] WARNING: {message}", flush=True)


def error(message: str, remediation: str | None = None) -> None:
    print(f"[docwiki] ERROR: {message}", file=sys.stderr, flush=True)
    if remediation:
        print(f"[docwiki]   remediation: {remediation}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# azd environment files
# ---------------------------------------------------------------------------


def parse_dotenv(text: str) -> dict[str, str]:
    """Parse an azd ``.env`` file (``KEY="value"`` lines with backslash escapes)."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key.startswith("export "):
            key = key[len("export ") :].strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            quote = value[0]
            value = value[1:-1]
            if quote == '"':
                value = re.sub(r"\\(.)", lambda m: {"n": "\n"}.get(m.group(1), m.group(1)), value)
        values[key] = value
    return values


def default_environment_name(root: Path = REPO_ROOT) -> str | None:
    """The default azd environment of the repository (``.azure/config.json``)."""
    config = root / ".azure" / "config.json"
    if not config.is_file():
        return None
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    name = data.get("defaultEnvironment")
    return name if isinstance(name, str) and name else None


def load_environment(env_name: str, root: Path = REPO_ROOT) -> dict[str, str]:
    """Values of ``.azure/<env>/.env`` (empty when the environment has not been created)."""
    path = root / ".azure" / env_name / ".env"
    if not path.is_file():
        return {}
    return parse_dotenv(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Bicep parameter defaults (single source of truth for the model defaults)
# ---------------------------------------------------------------------------

_PARAM_DEFAULT = re.compile(
    r"^param\s+(?P<name>\w+)\s+(?P<type>string|int|bool)\s*=\s*(?P<value>.+?)\s*$", re.MULTILINE
)


def bicep_parameter_defaults(path: Path | None = None) -> dict[str, str]:
    """Literal defaults of ``param`` declarations in ``infra/main.bicep`` (expressions skipped)."""
    source = (path or REPO_ROOT / "infra" / "main.bicep").read_text(encoding="utf-8")
    defaults: dict[str, str] = {}
    for match in _PARAM_DEFAULT.finditer(source):
        value = match.group("value")
        if match.group("type") == "string":
            literal = re.fullmatch(r"'((?:[^'\\]|\\.)*)'", value)
            if literal and "${" not in literal.group(1):
                defaults[match.group("name")] = literal.group(1)
        elif re.fullmatch(r"-?\d+|true|false", value):
            defaults[match.group("name")] = value
    return defaults


# ---------------------------------------------------------------------------
# Local state file (.azure/<env>/docwiki-state.json, git-ignored)
# ---------------------------------------------------------------------------


def state_path(env_name: str, root: Path = REPO_ROOT) -> Path:
    return root / ".azure" / env_name / STATE_FILE_NAME


def load_state(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"schema": STATE_SCHEMA}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise HookError(f"{path} is not a JSON object", "Fix or delete the state file.")
    return data


def save_state(path: Path, state: Mapping[str, Any]) -> None:
    """Write the state atomically (UTF-8, sorted keys, LF)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(state)
    payload["schema"] = STATE_SCHEMA
    payload["updated_at"] = utc_now()
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
    os.replace(temporary, path)


# ---------------------------------------------------------------------------
# Tool wrappers
# ---------------------------------------------------------------------------


@dataclass
class Tools:
    """az / azd / Graph helpers bound to one azd environment and a replaceable runner."""

    env: dict[str, str] = field(default_factory=dict)
    root: Path = REPO_ROOT
    runner: Runner = subprocess_runner
    scratch_dir: Path | None = None
    sleep: Callable[[float], None] = time.sleep
    which: Callable[[str], str | None] = shutil.which

    # -- generic ---------------------------------------------------------------

    def run(
        self,
        args: Sequence[str],
        *,
        check: bool = True,
        env: Mapping[str, str] | None = None,
        stream: bool = False,
    ) -> Result:
        if env is None and not stream:
            result = self.runner(list(args))
        else:
            result = self.runner(list(args), env=env, stream=stream)
        if check and not result.ok:
            raise CommandError(args, result)
        return result

    def get(self, key: str, default: str = "") -> str:
        value = self.env.get(key)
        return value if value not in (None, "") else default

    def require(self, *keys: str) -> dict[str, str]:
        missing = [key for key in keys if not self.get(key)]
        if missing:
            raise HookError(
                "missing azd environment values: " + ", ".join(missing),
                "Run `azd provision` (the values are Bicep outputs) or `azd env refresh`.",
            )
        return {key: self.get(key) for key in keys}

    @property
    def env_name(self) -> str:
        return self.require("AZURE_ENV_NAME")["AZURE_ENV_NAME"]

    def env_dir(self) -> Path:
        return self.root / ".azure" / self.env_name

    def write_scratch(self, name: str, payload: Any) -> Path:
        """Write a JSON payload passed to az with ``@file`` (git-ignored folder)."""
        directory = self.scratch_dir or self.env_dir() / "hook-tmp"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{name}-{uuid.uuid4().hex[:8]}.json"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        return path

    # -- az --------------------------------------------------------------------

    def az(self, *args: str, check: bool = True) -> Result:
        return self.run(["az", *args, "--only-show-errors"], check=check)

    def az_json(self, *args: str, check: bool = True) -> Any:
        result = self.az(*args, "--output", "json", check=check)
        if not result.ok:
            return None
        text = result.stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise HookError(f"az {' '.join(args[:3])} did not return JSON: {exc}") from None

    def rest(
        self,
        method: str,
        url: str,
        *,
        body: Any = None,
        resource: str | None = None,
        allow_not_found: bool = False,
    ) -> Any:
        """``az rest`` call returning parsed JSON (``None`` for empty bodies or tolerated 404)."""
        args = ["rest", "--method", method, "--url", url]
        body_file: Path | None = None
        if body is not None:
            body_file = self.write_scratch("body", body)
            args += ["--body", f"@{body_file}", "--headers", "Content-Type=application/json"]
        if resource:
            args += ["--resource", resource]
        try:
            result = self.az(*args, "--output", "json", check=False)
        finally:
            if body_file is not None:
                body_file.unlink(missing_ok=True)
        if not result.ok:
            if allow_not_found and is_not_found(result):
                return None
            if needs_fresh_sign_in(result):
                # Continuous access evaluation revoked the CLI's cached token (spike F9).
                raise HookError(
                    f"az rest {method} was refused: the signed-in session needs a fresh sign-in",
                    "Run `az logout`, `az login` and `azd auth login`, then re-run the hook "
                    "(azd hooks run postprovision).",
                )
            raise CommandError(["az", *args], result)
        text = result.stdout.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise HookError(f"az rest {method} did not return JSON: {exc}") from None

    # -- azd -------------------------------------------------------------------

    def azd_env_set(self, key: str, value: str) -> None:
        """Persist a value in the azd environment and in this process' view of it."""
        if self.env.get(key) == value:
            return
        self.run(["azd", "env", "set", key, value, "--environment", self.env_name])
        self.env[key] = value

    # -- identity ----------------------------------------------------------------

    def account(self) -> dict[str, Any]:
        data = self.az_json("account", "show", check=False)
        if not isinstance(data, dict):
            raise HookError("Azure CLI is not signed in", "Run `az login` (and `azd auth login`).")
        return data

    def signed_in_object_id(self) -> tuple[str, str]:
        """Object ID and principal type ('User' or 'ServicePrincipal') of the az CLI login.

        Read from the ``oid``/``idtyp`` claims of the CLI's ARM access token (no Microsoft
        Graph call, so it works when Graph requires a fresh sign-in); the token is never
        printed or stored. Falls back to Microsoft Graph.
        """
        account = self.account()
        user = account.get("user") or {}
        principal_type = "ServicePrincipal" if user.get("type") == "servicePrincipal" else "User"
        token = self.az_json("account", "get-access-token", check=False)
        claims = jwt_claims(str((token or {}).get("accessToken", ""))) if token else {}
        object_id = str(claims.get("oid") or "")
        if object_id:
            if claims.get("idtyp") == "app":
                principal_type = "ServicePrincipal"
            return object_id, principal_type
        if principal_type == "ServicePrincipal":
            data = self.az_json("ad", "sp", "show", "--id", str(user.get("name", "")))
        else:
            data = self.az_json("ad", "signed-in-user", "show")
        object_id = str((data or {}).get("id", ""))
        if not object_id:
            raise HookError(
                "could not determine the signed-in principal",
                "Sign in again with `az login`, then re-run.",
            )
        return object_id, principal_type


def jwt_claims(token: str) -> dict[str, Any]:
    """Claims of a JWT payload (not validated: only used to read the caller's own IDs)."""
    parts = token.split(".")
    if len(parts) != 3:
        return {}
    payload = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode("ascii")))
    except (ValueError, UnicodeDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def is_not_found(result: Result) -> bool:
    text = f"{result.stderr}\n{result.stdout}"
    return bool(re.search(r"\b404\b|Not ?Found|ResourceNotFound|does not exist", text, re.I))


_FRESH_SIGN_IN = re.compile(
    r"TokenCreatedWithOutdatedPolicies|InteractionRequired|AADSTS50173|claims challenge",
    re.IGNORECASE,
)


def needs_fresh_sign_in(result: Result) -> bool:
    """Microsoft Graph or ARM rejected the cached token (continuous access evaluation)."""
    return bool(_FRESH_SIGN_IN.search(f"{result.stderr}\n{result.stdout}"))


def tools_from_environment(
    environ: Mapping[str, str] | None = None,
    *,
    root: Path = REPO_ROOT,
    runner: Runner | None = None,
    env_name: str | None = None,
) -> Tools:
    """Tools for the current azd environment.

    Inside an azd hook every environment value is already exported to the process; when a
    script runs by hand the values are read from ``.azure/<env>/.env``.
    """
    process_env = dict(os.environ if environ is None else environ)
    name = env_name or process_env.get("AZURE_ENV_NAME") or default_environment_name(root)
    values: dict[str, str] = {}
    if name:
        values.update(load_environment(name, root))
        values["AZURE_ENV_NAME"] = name
    for key, value in process_env.items():
        if key.startswith(("AZURE_", "DOCWIKI_", "SERVICE_", "BUDGET_", "APPLICATIONINSIGHTS_")):
            if name and key == "AZURE_ENV_NAME" and value != name:
                continue
            values[key] = value
    return Tools(env=values, root=root, runner=runner or subprocess_runner)


def unique(items: Iterable[str]) -> list[str]:
    seen: dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def retry[T](
    action: Callable[[], T],
    *,
    attempts: int = 4,
    delay_s: float = 5.0,
    sleep: Callable[[float], None] = time.sleep,
    retry_on: tuple[type[BaseException], ...] = (CommandError,),
) -> T:
    """Run ``action`` until it succeeds (directory replication makes new objects lag)."""
    for attempt in range(1, attempts + 1):
        try:
            return action()
        except retry_on:
            if attempt == attempts:
                raise
            sleep(delay_s * attempt)
    raise AssertionError("unreachable")
