"""Studio settings (``DOCWIKI_STUDIO_*`` and the shared ``DOCWIKI_*`` variables)."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from urllib.parse import urlsplit

__all__ = ["StudioConfig", "StudioConfigError"]

WIKI_URL_ENV = "DOCWIKI_STUDIO_WIKI_URL"
REQUIRE_SIGN_IN_ENV = "DOCWIKI_STUDIO_REQUIRE_SIGN_IN"
ALLOWED_PRINCIPALS_ENV = "DOCWIKI_STUDIO_ALLOWED_PRINCIPALS"
MAX_UPLOAD_MB_ENV = "DOCWIKI_STUDIO_MAX_UPLOAD_MB"
DAILY_QUESTIONS_ENV = "DOCWIKI_STUDIO_DAILY_QUESTIONS"
DAILY_UPLOADS_ENV = "DOCWIKI_STUDIO_DAILY_UPLOADS"
APPROVAL_TIMEOUT_ENV = "DOCWIKI_STUDIO_APPROVAL_TIMEOUT_SECONDS"
QUESTION_TIMEOUT_ENV = "DOCWIKI_STUDIO_QUESTION_TIMEOUT_SECONDS"
FOUNDRY_ENDPOINT_ENV = "DOCWIKI_FOUNDRY_PROJECT_ENDPOINT"

DEFAULT_MAX_UPLOAD_MB = 50
DEFAULT_DAILY_QUESTIONS = 100
DEFAULT_DAILY_UPLOADS = 10
DEFAULT_APPROVAL_TIMEOUT_S = 600.0
DEFAULT_QUESTION_TIMEOUT_S = 1200.0


class StudioConfigError(ValueError):
    """An invalid ``DOCWIKI_STUDIO_*`` value."""


def _flag(value: str | None, default: bool) -> bool:
    if value is None or not value.strip():
        return default
    text = value.strip().lower()
    if text in ("1", "true", "yes", "on"):
        return True
    if text in ("0", "false", "no", "off"):
        return False
    raise StudioConfigError(f"expected true or false, got {value!r}")


def _positive(value: str | None, default: float, name: str) -> float:
    if value is None or not value.strip():
        return default
    try:
        number = float(value)
    except ValueError as exc:
        raise StudioConfigError(f"{name} must be a number") from exc
    if number <= 0:
        raise StudioConfigError(f"{name} must be positive")
    return number


def _wiki_url(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    url = value.strip().rstrip("/")
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http") or not parts.netloc or parts.query or parts.fragment:
        raise StudioConfigError(f"{WIKI_URL_ENV} must be an http(s) URL without query: {value!r}")
    return url


@dataclass(frozen=True)
class StudioConfig:
    """What the Studio serves and how it protects itself."""

    wiki_url: str | None = None
    """Site that renders the live release (the portal): citations and documents link to it."""
    require_sign_in: bool = True
    """Refuse API calls without the principal headers of Container Apps built-in auth."""
    allowed_principals: frozenset[str] = frozenset()
    """Object IDs allowed in (empty: anyone the sign-in lets through, i.e. assigned users)."""
    max_upload_bytes: int = DEFAULT_MAX_UPLOAD_MB * 1024 * 1024
    daily_questions: int = DEFAULT_DAILY_QUESTIONS
    daily_uploads: int = DEFAULT_DAILY_UPLOADS
    """Each upload of a new or changed file triggers a pipeline run (model calls cost money)."""
    approval_timeout_s: float = DEFAULT_APPROVAL_TIMEOUT_S
    question_timeout_s: float = DEFAULT_QUESTION_TIMEOUT_S
    """Overall deadline of one question, approvals and retries included."""
    agents_enabled: bool = True

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, *, local: bool = False) -> StudioConfig:
        values = os.environ if env is None else env
        principals = frozenset(
            item.strip().lower()
            for item in (values.get(ALLOWED_PRINCIPALS_ENV) or "").split(",")
            if item.strip()
        )
        return cls(
            wiki_url=_wiki_url(values.get(WIKI_URL_ENV)),
            require_sign_in=False if local else _flag(values.get(REQUIRE_SIGN_IN_ENV), True),
            allowed_principals=principals,
            max_upload_bytes=int(
                _positive(values.get(MAX_UPLOAD_MB_ENV), DEFAULT_MAX_UPLOAD_MB, MAX_UPLOAD_MB_ENV)
                * 1024
                * 1024
            ),
            daily_questions=int(
                _positive(
                    values.get(DAILY_QUESTIONS_ENV), DEFAULT_DAILY_QUESTIONS, DAILY_QUESTIONS_ENV
                )
            ),
            daily_uploads=int(
                _positive(values.get(DAILY_UPLOADS_ENV), DEFAULT_DAILY_UPLOADS, DAILY_UPLOADS_ENV)
            ),
            approval_timeout_s=_positive(
                values.get(APPROVAL_TIMEOUT_ENV), DEFAULT_APPROVAL_TIMEOUT_S, APPROVAL_TIMEOUT_ENV
            ),
            question_timeout_s=_positive(
                values.get(QUESTION_TIMEOUT_ENV), DEFAULT_QUESTION_TIMEOUT_S, QUESTION_TIMEOUT_ENV
            ),
            agents_enabled=bool((values.get(FOUNDRY_ENDPOINT_ENV) or "").strip()),
        )
