from __future__ import annotations

import re

import pytest
from leakguard_core.config import DenyPattern, DomainPolicy, deny_rule_id
from leakguard_core.rules import (
    deny_hits,
    identifier_hits,
    is_lock_or_registry_file,
    policy_violation,
)
from leakguard_fixtures import (
    FAKE_ACCOUNT_KEY,
    FAKE_API_KEY_ASSIGNMENT,
    FAKE_BARE_INTERNAL,
    FAKE_EMAIL,
    FAKE_ENV_SECRET,
    FAKE_GITHUB_TOKEN,
    FAKE_GUID,
    FAKE_INDEX_LINE,
    FAKE_INTERNAL_URL,
    FAKE_JWT,
    FAKE_MAC_HOME,
    FAKE_MIRROR_URL,
    FAKE_PRIVATE_KEY,
    FAKE_SAS,
    FAKE_SHARED_KEY,
    FAKE_SINGLE_LABEL_URL,
    FAKE_UNIX_HOME,
    FAKE_URL_CREDENTIALS,
    FAKE_WIN_HOME,
    PUBLIC_REGISTRY_URL,
)

ROLE_ID = "ba92f5b4-2d11-453d-a403-e96b0029c9fe"  # public built-in role (allowed_guids.txt)


def rules_in(text: str, *, lockfile: bool = False, allowed: set[str] | None = None) -> list[str]:
    domains = DomainPolicy(suffixes={".example", ".test"})
    hits = identifier_hits(
        text, allowed_guids=allowed or {ROLE_ID}, domains=domains, lockfile=lockfile
    )
    return [hit.rule for hit in hits]


def test_guid_is_reported_unless_reviewed() -> None:
    assert rules_in(f"tenant {FAKE_GUID}") == ["guid"]
    assert rules_in(f"role {ROLE_ID.upper()}") == []


def test_subscription_resource_id_absorbs_its_guid() -> None:
    text = "/subscriptions/" + FAKE_GUID + "/resourceGroups/rg-demo"
    assert rules_in(text) == ["azure-resource-id"]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (f"contact {FAKE_EMAIL}", ["email"]),
        ("author 12345+octo@users.noreply.github.com", []),
        ("mail someone@example.com or team@sub.example.org", []),
        ("fictional ops@contoso.example", []),
        ("retina logo@2x.png", []),
        ("package @azure/identity and actions/checkout@v4", []),
    ],
)
def test_email_rule(text: str, expected: list[str]) -> None:
    assert rules_in(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (FAKE_WIN_HOME, ["home-path"]),
        (FAKE_UNIX_HOME, ["home-path"]),
        (FAKE_MAC_HOME, ["home-path"]),
        ("C:" + "\\Users\\Public\\Desktop", []),
        ("/" + "home/runner/work/repo", []),
        ("C:" + "\\Users\\<you>\\repo and %USERPROFILE%", []),
        ("https:" + "//api.example.com/home/about", []),
    ],
)
def test_home_path_rule(text: str, expected: list[str]) -> None:
    assert rules_in(text) == expected


@pytest.mark.parametrize(
    ("text", "rule"),
    [
        (FAKE_PRIVATE_KEY, "private-key"),
        (FAKE_GITHUB_TOKEN, "secret-github-token"),
        ("Endpoint=https:" + "//x.blob.core.windows.net/;" + FAKE_ACCOUNT_KEY, "secret-azure-key"),
        (FAKE_SHARED_KEY, "secret-azure-key"),
        ("https:" + "//account.blob.core.windows.net/c/b" + FAKE_SAS, "secret-azure-sas"),
        ("Authorization: Bearer " + FAKE_JWT, "secret-jwt"),
        (FAKE_API_KEY_ASSIGNMENT, "secret-assignment"),
        (FAKE_ENV_SECRET, "secret-assignment"),
        ("git clone " + FAKE_URL_CREDENTIALS, "secret-url-credentials"),
    ],
)
def test_secret_rules(text: str, rule: str) -> None:
    assert rule in rules_in(text)


@pytest.mark.parametrize(
    "text",
    [
        "api" + "_key = '<your-api-key>'",
        "pass" + "word: '${{ secrets.DB_PASSWORD }}'",
        "client" + "_secret = 'changeme-later'",
        "Account" + "Key=<storage-key>",
        "export DOCWIKI" + "_TOKEN=$DOCWIKI_TOKEN",
    ],
)
def test_secret_placeholders_are_ignored(text: str) -> None:
    assert rules_in(text) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (FAKE_INTERNAL_URL, ["internal-host"]),
        (FAKE_SINGLE_LABEL_URL, ["internal-host"]),
        ("ping " + FAKE_BARE_INTERNAL, ["internal-host"]),
        ("see build01." + "corp." + "zorblax-corp.com today", ["internal-host"]),
        ("http:" + "//localhost:8000/docs", []),
        ("http:" + "//host.docker." + "internal:5000", []),
        ("self.internal = True; threading.local()", []),
        ("from mypkg.internal.utils import x", []),
        ("http:" + "//intranet.contoso.example/", []),
    ],
)
def test_internal_host_rule(text: str, expected: list[str]) -> None:
    assert rules_in(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (FAKE_MIRROR_URL, ["package-mirror"]),
        (FAKE_INDEX_LINE, ["package-mirror"]),
        (PUBLIC_REGISTRY_URL, []),
        ("https:" + "//files.pythonhosted.org/packages/ab/cd/x.whl", []),
        ("https:" + "//registry.npmjs.org/quartz", []),
        ("https:" + "//docs.astral.sh/uv/ and https:" + "//www.npmjs.com/package/x", []),
    ],
)
def test_package_mirror_rule(text: str, expected: list[str]) -> None:
    assert rules_in(text) == expected


def test_lock_files_only_accept_public_hosts() -> None:
    text = (
        'source = { registry = "' + PUBLIC_REGISTRY_URL + '" }\n'
        'source = { registry = "https:' + '//mirror.zorblax-corp.com/simple" }\n'
        'url = "https:' + '//mirror.zorblax-corp.com/x.whl"\n'
    )
    assert rules_in(text, lockfile=True) == ["lockfile-mirror"]


def test_deny_hits_are_case_insensitive_and_sensitive() -> None:
    pattern = "zorblax[- ]?corp"
    deny = [DenyPattern(deny_rule_id(pattern), re.compile(pattern, re.IGNORECASE), 2)]
    hits = deny_hits("The ZORBLAX-CORP plant and zorblax corp office", deny)
    assert [hit.raw for hit in hits] == ["ZORBLAX-CORP", "zorblax corp"]
    assert all(hit.sensitive and hit.rule == deny_rule_id(pattern) for hit in hits)
    assert re.fullmatch(r"deny:[0-9a-f]{8}", deny_rule_id(pattern))


@pytest.mark.parametrize(
    ("path", "violates"),
    [
        ("uv.lock", True),
        ("site/package-lock.json", True),
        (".env", True),
        ("config/.env.local", True),
        ("certs/server.pfx", True),
        ("docs/environment.md", False),
        ("pyproject.toml", False),
    ],
)
def test_policy_files(path: str, violates: bool) -> None:
    assert (policy_violation(path) is not None) is violates


def test_lock_and_registry_file_detection() -> None:
    assert is_lock_or_registry_file("uv.lock")
    assert is_lock_or_registry_file("tools/requirements-dev.txt")
    assert is_lock_or_registry_file(".npmrc")
    assert not is_lock_or_registry_file("README.md")
