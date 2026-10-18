"""Test helpers for the infrastructure lane (no Azure calls, no network).

Importing this module puts ``scripts/`` and ``scripts/hooks/`` on ``sys.path`` so that the
hook modules (stdlib-only scripts, not a package) can be imported by the tests.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (REPO_ROOT / "scripts", REPO_ROOT / "scripts" / "hooks"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from azdlib import Result  # noqa: E402

Response = Result | Mapping[str, Any] | list[Any] | str | Callable[[list[str]], Result] | None


class FakeRunner:
    """Replaces the process runner: matches commands by regex and records calls.

    Responses: a :class:`Result`, JSON-serialisable data (returned as stdout), a string
    (stdout), ``None`` (empty success) or a callable returning a Result. A list of responses
    registered with :meth:`queue` is consumed call after call (the last one repeats).
    """

    def __init__(self) -> None:
        self.rules: list[tuple[re.Pattern[str], list[Response]]] = []
        self.calls: list[list[str]] = []
        self.bodies: list[tuple[str, Any]] = []
        self.envs: list[Mapping[str, str] | None] = []

    def on(self, pattern: str, response: Response) -> FakeRunner:
        self.rules.append((re.compile(pattern), [response]))
        return self

    def queue(self, pattern: str, *responses: Response) -> FakeRunner:
        self.rules.append((re.compile(pattern), list(responses)))
        return self

    def __call__(
        self, args: Sequence[str], *, env: Mapping[str, str] | None = None, stream: bool = False
    ) -> Result:
        command = [str(arg) for arg in args]
        self.calls.append(command)
        self.envs.append(env)
        line = " ".join(command)
        for arg in command:
            if arg.startswith("@") and Path(arg[1:]).is_file():
                self.bodies.append((line, json.loads(Path(arg[1:]).read_text(encoding="utf-8"))))
        for pattern, responses in self.rules:
            if pattern.search(line):
                response = responses.pop(0) if len(responses) > 1 else responses[0]
                return _to_result(response, command)
        raise AssertionError(f"unexpected command: {line}")

    def commands(self, pattern: str) -> list[str]:
        regex = re.compile(pattern)
        return [" ".join(call) for call in self.calls if regex.search(" ".join(call))]

    def body_for(self, pattern: str) -> list[Any]:
        regex = re.compile(pattern)
        return [body for line, body in self.bodies if regex.search(line)]


def _to_result(response: Response, command: list[str]) -> Result:
    if isinstance(response, Result):
        return response
    if callable(response):
        return response(command)
    if response is None:
        return Result(0, "", "")
    if isinstance(response, str):
        return Result(0, response, "")
    return Result(0, json.dumps(response), "")


def not_found() -> Result:
    return Result(1, "", "ERROR: Not Found({'error': {'code': 'Request_ResourceNotFound'}})")
