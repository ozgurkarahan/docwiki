from __future__ import annotations

import pytest

from docwiki.studio.config import StudioConfig, StudioConfigError
from docwiki.studio.paths import PathError, check_upload_path, wiki_link


def test_defaults_require_sign_in_and_disable_agents_without_foundry() -> None:
    config = StudioConfig.from_env({})
    assert config.require_sign_in is True
    assert config.allowed_principals == frozenset()
    assert config.agents_enabled is False
    assert config.wiki_url is None
    assert config.max_upload_bytes == 50 * 1024 * 1024
    assert (config.daily_questions, config.daily_uploads, config.daily_filings) == (100, 10, 20)


def test_local_mode_skips_sign_in_whatever_the_environment_says() -> None:
    env = {"DOCWIKI_STUDIO_REQUIRE_SIGN_IN": "true"}
    assert StudioConfig.from_env(env, local=True).require_sign_in is False
    assert StudioConfig.from_env(env).require_sign_in is True


def test_values_are_parsed_and_principals_normalised() -> None:
    config = StudioConfig.from_env(
        {
            "DOCWIKI_STUDIO_WIKI_URL": "https://wiki.example.org/",
            "DOCWIKI_STUDIO_ALLOWED_PRINCIPALS": " AAA-1 , bbb-2,, ",
            "DOCWIKI_STUDIO_MAX_UPLOAD_MB": "2",
            "DOCWIKI_STUDIO_DAILY_QUESTIONS": "7",
            "DOCWIKI_STUDIO_DAILY_UPLOADS": "3",
            "DOCWIKI_STUDIO_DAILY_FILINGS": "4",
            "DOCWIKI_STUDIO_APPROVAL_TIMEOUT_SECONDS": "30",
            "DOCWIKI_STUDIO_QUESTION_TIMEOUT_SECONDS": "90",
            "DOCWIKI_STUDIO_REQUIRE_SIGN_IN": "false",
            "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT": "https://x.services.ai.azure.com/api/projects/p",
        }
    )
    assert config.wiki_url == "https://wiki.example.org"
    assert config.allowed_principals == frozenset({"aaa-1", "bbb-2"})
    assert config.max_upload_bytes == 2 * 1024 * 1024
    assert (config.daily_questions, config.daily_uploads, config.daily_filings) == (7, 3, 4)
    assert (config.approval_timeout_s, config.question_timeout_s) == (30.0, 90.0)
    assert config.require_sign_in is False
    assert config.agents_enabled is True


@pytest.mark.parametrize(
    "env",
    [
        {"DOCWIKI_STUDIO_REQUIRE_SIGN_IN": "maybe"},
        {"DOCWIKI_STUDIO_MAX_UPLOAD_MB": "-1"},
        {"DOCWIKI_STUDIO_DAILY_QUESTIONS": "lots"},
        {"DOCWIKI_STUDIO_DAILY_FILINGS": "0"},
        {"DOCWIKI_STUDIO_WIKI_URL": "ftp://wiki.example.org"},
        {"DOCWIKI_STUDIO_WIKI_URL": "https://wiki.example.org/?x=1"},
    ],
)
def test_invalid_values_are_refused(env: dict[str, str]) -> None:
    with pytest.raises(StudioConfigError):
        StudioConfig.from_env(env)


@pytest.mark.parametrize(
    "path",
    [
        "uploads/report.pdf",
        "uploads/Compte rendu (v2).docx",
        "a/b/c/planning-2026_indice+1.xlsx",
        "notes.md",
    ],
)
def test_upload_paths_accepted(path: str) -> None:
    assert check_upload_path(path) == path


@pytest.mark.parametrize(
    "path",
    [
        "",
        "../escape.pdf",
        "/absolute.pdf",
        "uploads//double.pdf",
        "uploads\\windows.pdf",
        ".hidden/file.pdf",
        "uploads/.hidden.pdf",
        "a/b/c/d/too-deep.pdf",
        "uploads/script.exe",
        "uploads/no-extension",
        "uploads/trailing-dot.",
        "uploads/<tag>.pdf",
        "x" * 300 + ".pdf",
    ],
)
def test_upload_paths_refused(path: str) -> None:
    with pytest.raises(PathError):
        check_upload_path(path)


def test_unsupported_type_lists_the_supported_ones() -> None:
    with pytest.raises(PathError, match=r"\.pdf"):
        check_upload_path("uploads/archive.zip")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "evidence/src-165f1d3a109c/para-0011.md",
            "https://wiki.example.org/evidence/src-165f1d3a109c/para-0011",
        ),
        (
            "sources/2026-03-24-compte-rendu-de-chantier-n3.md#overview",
            "https://wiki.example.org/sources/2026-03-24-compte-rendu-de-chantier-n3",
        ),
        ("index.md", "https://wiki.example.org/"),
        ("topics/index.md", "https://wiki.example.org/topics/"),
    ],
)
def test_wiki_links(path: str, expected: str) -> None:
    assert wiki_link("https://wiki.example.org/", path) == expected


@pytest.mark.parametrize(
    "path",
    [
        None,
        "",
        "javascript:alert(1)",
        "https://evil.example/x.md",
        "../evidence/x.md",
        "evidence/../../x.md",
        "evidence/x.html",
        "evidence/a b.md",
        "/evidence/x.md",
    ],
)
def test_untrusted_paths_never_become_links(path: str | None) -> None:
    assert wiki_link("https://wiki.example.org", path) is None


def test_no_wiki_url_means_no_links() -> None:
    assert wiki_link(None, "evidence/src-165f1d3a109c/para-0011.md") is None
