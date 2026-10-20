"""Test helpers for the infrastructure lane (no Azure calls, no network).

Importing this module puts ``scripts/`` and ``scripts/hooks/`` on ``sys.path`` so that the
hook modules (stdlib-only scripts, not a package) can be imported by the tests.
"""

from __future__ import annotations

import json
import re
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
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


# -- Azure ABAC role-assignment conditions (the subset the Bicep templates use) ---------------

BLOB_SERVICE_ACTION = "Microsoft.Storage/storageAccounts/blobServices/"
CONTAINER_ACTION = BLOB_SERVICE_ACTION + "containers/"
BLOB_ACTION = CONTAINER_ACTION + "blobs/"
_ATTRIBUTES = {
    "Microsoft.Storage/storageAccounts/blobServices/containers/blobs:path": "path",
    "Microsoft.Storage/storageAccounts/blobServices/containers:name": "container",
}
_CONDITION_PART = re.compile(
    r"\s*(?:(?P<open>\()|(?P<close>\))|(?P<not>!)|(?P<and>AND\b|&&)|(?P<or>OR\b|\|\|)"
    r"|ActionMatches\{'(?P<action>[^']+)'\}"
    r"|@Resource\[(?P<attribute>[^\]]+)\]\s+(?P<op>StringEquals|StringStartsWith|StringLike)"
    r"\s+'(?P<value>[^']*)')"
)


def storage_action(action: str) -> str:
    """The full action name: ``blobs/…`` is short for a blob data action, ``containers/…`` and
    ``generateUserDelegationKey/action`` for a Blob service action; full names pass through."""
    if action.startswith("Microsoft."):
        return action
    if action.startswith("blobs/"):
        return CONTAINER_ACTION + action
    return BLOB_SERVICE_ACTION + action


def evaluate_condition(condition: str, action: str, *, path: str, container: str = "") -> bool:
    """Whether a role assignment with ``condition`` (condition format 2.0) allows ``action``
    (``blobs/read``… or a full data action) on the blob ``path`` of ``container``.

    Supports the grammar of the Microsoft Learn "condition format" article that the templates
    use: ``!``, ``AND``/``OR``, parentheses, ``ActionMatches`` and string comparisons of the
    blob path and container name. Anything else fails the test instead of being guessed.
    Only the condition is evaluated: :func:`role_allows` adds the role definition.
    """
    full_action = storage_action(action)
    request = {"path": path, "container": container}
    tokens: list[re.Match[str]] = []
    position, text = 0, condition.strip()
    while position < len(text):
        match = _CONDITION_PART.match(text, position)
        if match is None or match.end() == position:
            raise ValueError(f"unsupported condition syntax at: {text[position : position + 40]!r}")
        tokens.append(match)
        position = match.end()
    index = 0

    def peek(kind: str) -> bool:
        return index < len(tokens) and tokens[index].group(kind) is not None

    def take(kind: str) -> re.Match[str]:
        nonlocal index
        if not peek(kind):
            raise ValueError(f"expected {kind} at token {index}")
        index += 1
        return tokens[index - 1]

    def expression() -> bool:
        value = term()
        while peek("or"):
            take("or")
            value = term() or value
        return value

    def term() -> bool:
        value = factor()
        while peek("and"):
            take("and")
            value = factor() and value
        return value

    def factor() -> bool:
        if peek("not"):
            take("not")
            return not factor()
        if peek("open"):
            take("open")
            value = expression()
            take("close")
            return value
        if peek("action"):
            pattern = take("action").group("action")
            if pattern.endswith("*"):
                return full_action.startswith(pattern[:-1])
            return full_action == pattern
        match = take("op")
        attribute = _ATTRIBUTES.get(match.group("attribute"))
        if attribute is None:
            raise ValueError(f"unsupported attribute {match.group('attribute')}")
        actual, expected = request[attribute], match.group("value")
        if match.group("op") == "StringEquals":
            return actual == expected
        if match.group("op") == "StringStartsWith":
            return actual.startswith(expected)
        return re.fullmatch(".*".join(map(re.escape, expected.split("*"))), actual) is not None

    result = expression()
    if index != len(tokens):
        raise ValueError(f"unexpected token {tokens[index].group(0)!r}")
    return result


# -- Azure RBAC: what one role assignment allows (role definition and condition) -------------

_PERMISSION_KEYS = ("actions", "notActions", "dataActions", "notDataActions")


@dataclass(frozen=True)
class RolePermissions:
    """One ``permissions`` entry of an Azure role definition (full action names)."""

    actions: tuple[str, ...] = ()
    not_actions: tuple[str, ...] = ()
    data_actions: tuple[str, ...] = ()
    not_data_actions: tuple[str, ...] = ()

    @classmethod
    def from_json(cls, permission: Mapping[str, Any]) -> RolePermissions:
        """From a ``permissions`` entry of a compiled (ARM JSON) role definition."""
        return cls(*(tuple(permission.get(key, ())) for key in _PERMISSION_KEYS))

    @classmethod
    def from_bicep(cls, declaration: str) -> RolePermissions:
        """From the only ``permissions`` entry of a ``roleDefinitions`` declaration in Bicep.
        Its arrays may hold string literals only; anything else fails the test."""
        entries = re.findall(
            r"^\s*permissions: \[\s*\{(.*?)\}\s*\]", declaration, re.MULTILINE | re.DOTALL
        )
        if len(entries) != 1 or "{" in entries[0] or "}" in entries[0]:
            raise ValueError("expected exactly one permissions entry")
        values: list[tuple[str, ...]] = []
        for key in _PERMISSION_KEYS:
            match = re.search(rf"^\s*{key}: \[([^\]]*)\]", entries[0], re.MULTILINE)
            items = match.group(1) if match else ""
            if re.sub(r"'[^']*'", "", items).strip():
                raise ValueError(f"{key}: only string literals are supported")
            values.append(tuple(re.findall(r"'([^']*)'", items)))
        return cls(*values)


STORAGE_BLOB_DATA_READER = RolePermissions(
    actions=(CONTAINER_ACTION + "read", BLOB_SERVICE_ACTION + "generateUserDelegationKey/action"),
    data_actions=(BLOB_ACTION + "read",),
)
"""The built-in Storage Blob Data Reader role (Microsoft Learn, Azure built-in roles)."""

STORAGE_BLOB_DATA_CONTRIBUTOR = RolePermissions(
    actions=(
        CONTAINER_ACTION + "delete",
        CONTAINER_ACTION + "read",
        CONTAINER_ACTION + "write",
        BLOB_SERVICE_ACTION + "generateUserDelegationKey/action",
    ),
    data_actions=tuple(
        BLOB_ACTION + action for action in ("delete", "read", "write", "move/action", "add/action")
    ),
)
"""The built-in Storage Blob Data Contributor role (Microsoft Learn, Azure built-in roles)."""


def is_data_action(action: str) -> bool:
    """Blob data actions (``…/containers/blobs/…``), as opposed to the control-plane actions of
    the Blob service and its containers (the Blob Storage subset these tests use)."""
    return storage_action(action).startswith(BLOB_ACTION)


def _granted(allowed: Sequence[str], excluded: Sequence[str], action: str) -> bool:
    def matches(pattern: str) -> bool:
        regex = ".*".join(map(re.escape, pattern.split("*")))
        return re.fullmatch(regex, action, re.IGNORECASE) is not None

    return any(map(matches, allowed)) and not any(map(matches, excluded))


def role_allows(
    permissions: RolePermissions,
    action: str,
    *,
    condition: str | None = None,
    path: str = "",
    container: str = "",
) -> bool:
    """Whether one role assignment (role ``permissions`` and an optional condition) allows
    ``action`` (short names as in :func:`storage_action`) on the blob ``path`` of ``container``.

    Azure's rules: a control-plane action needs the role's ``actions`` minus ``notActions`` and
    is never filtered by the assignment's condition (conditions are not supported for
    management actions); a data action needs ``dataActions`` minus ``notDataActions`` and, when
    the assignment has a condition, that condition. Permission strings are case-insensitive
    and ``*`` is a wildcard.
    """
    full_action = storage_action(action)
    if not is_data_action(full_action):
        return _granted(permissions.actions, permissions.not_actions, full_action)
    if not _granted(permissions.data_actions, permissions.not_data_actions, full_action):
        return False
    return condition is None or evaluate_condition(
        condition, full_action, path=path, container=container
    )


# -- Bicep source -------------------------------------------------------------------------------


def bicep_multiline_var(text: str, name: str) -> str:
    """The value of ``var <name> = '''…'''`` in a Bicep file."""
    match = re.search(rf"^var {name} = '''\n(?P<value>.*?)'''$", text, re.MULTILINE | re.DOTALL)
    if match is None:
        raise AssertionError(f"no multi-line var {name}")
    return match.group("value")
