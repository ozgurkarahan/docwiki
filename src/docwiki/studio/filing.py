"""File to wiki: a reviewed Researcher answer becomes a wiki page (ADR 0007).

The owner previews the query page built from a completed Researcher answer
(:func:`docwiki.answers.build_query_page`, against the release the Studio serves): its path, its
Markdown and the warnings to review (numbers not found in the cited evidence, content removed by
the safety rules). Filing writes that page to the inbox ``work/inbox/queries/``; Event Grid wakes
the ingest job and its next run merges the inbox into ``queries/`` (every model output is cached:
about three minutes, no model cost). The Studio's identity may write only under that prefix and
never deletes; the jobs identity consumes the inbox.

Filings are kept in memory, like the questions: a restart forgets which answers were filed, not
the inbox.
"""

from __future__ import annotations

import hashlib
import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from docwiki.answers import FiledAnswer, StorageRelease, build_query_page, inbox_key, write_inbox
from docwiki.contracts.pages import QueryFrontmatter
from docwiki.contracts.storage import Storage
from docwiki.studio.jobs import AgentJob, JobStateError

__all__ = [
    "FILEABLE_AGENT",
    "AnswerFiler",
    "Filing",
    "FilingConflictError",
    "FilingQuotaError",
    "FilingRefusedError",
]

log = logging.getLogger("docwiki.studio.filing")

FILEABLE_AGENT = "researcher"
"""Only the Researcher's cited answers become wiki pages; the Librarian operates the pipeline."""
MAX_RECORDS = 100


class FilingRefusedError(ValueError):
    """The answer is not one the wiki takes (HTTP 400)."""


class FilingConflictError(RuntimeError):
    """The page is no longer the one the owner previewed (HTTP 409)."""


class FilingQuotaError(RuntimeError):
    """The daily filing allowance is used up (HTTP 429)."""


@dataclass(frozen=True)
class Filing:
    """An answer written to the inbox by this Studio."""

    job_id: str
    inbox_key: str
    path: str
    digest: str
    release_id: str
    filed_at: datetime

    def view(self) -> dict[str, Any]:
        return {
            "inbox_key": self.inbox_key,
            "path": self.path,
            "release_id": self.release_id,
            "filed_at": self.filed_at.isoformat().replace("+00:00", "Z"),
        }


def _digest(markdown: str) -> str:
    return hashlib.sha256(markdown.encode("utf-8")).hexdigest()


class AnswerFiler:
    """Previews and files the Researcher answers of the Studio's questions."""

    def __init__(
        self,
        storage: Storage,
        *,
        daily_filings: int,
        today: Callable[[], date] = lambda: datetime.now(UTC).date(),
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.storage = storage
        self.daily_filings = daily_filings
        self._today = today
        self._now = now
        self._filed: dict[str, Filing] = {}
        self._count: dict[date, int] = {}
        self._lock = threading.Lock()

    def filings_left(self) -> int:
        return max(self.daily_filings - self._count.get(self._today(), 0), 0)

    def filed(self, job_id: str) -> dict[str, Any] | None:
        """Where this Studio filed the answer of a question (``None``: not filed)."""
        record = self._filed.get(job_id)
        return record.view() if record is not None else None

    def _build(self, job: AgentJob) -> tuple[FiledAnswer, str]:
        """The query page of the job's answer from the current release, and that release's id.

        Raises :class:`~docwiki.answers.FilingError` when the answer cannot become a page.
        """
        if job.agent != FILEABLE_AGENT:
            raise FilingRefusedError(
                f"only Researcher answers can be filed to the wiki (this is a {job.agent} answer)"
            )
        if job.status != "done" or job.answer is None:
            raise JobStateError(f"question {job.id} has no answer to file ({job.status})")
        filed_on = self._today()
        answered = (job.finished_at or job.created_at).astimezone(UTC).date()
        release = StorageRelease(self.storage)
        filed = build_query_page(
            job.answer,
            question=job.question,
            release=release,
            filed_on=filed_on,
            answered_on=min(answered, filed_on),
            asked_by="human",
        )
        return filed, release.release_id

    def preview(self, job: AgentJob) -> dict[str, Any]:
        """The page that filing would write, without writing anything."""
        filed, release_id = self._build(job)
        page = filed.page
        assert isinstance(page.frontmatter, QueryFrontmatter)
        markdown = page.render()
        return {
            "job_id": job.id,
            "path": page.path,
            "inbox_key": inbox_key(page),
            "release_id": release_id,
            "sensitivity": page.frontmatter.sensitivity,
            "sources": len(page.frontmatter.sources),
            "not_found": filed.not_found,
            "numbers_checked": filed.numbers_checked,
            "warnings": list(filed.warnings),
            "markdown": markdown,
            "digest": _digest(markdown),
            "filed": self.filed(job.id),
            "filings_left": self.filings_left(),
        }

    def file(self, job: AgentJob, *, digest: str | None = None) -> dict[str, Any]:
        """Write the job's page to the inbox.

        ``digest`` (from :meth:`preview`) makes sure the owner files the page they reviewed. A
        repeated request for the same page returns the first filing (``repeated: true``) without
        writing again: the inbox key depends only on the day and the question.
        """
        with self._lock:
            filed, release_id = self._build(job)
            markdown = filed.page.render()
            current = _digest(markdown)
            if digest is not None and digest != current:
                raise FilingConflictError(
                    "the page changed since your preview (a new release or a new day): "
                    "review it again before filing"
                )
            key = inbox_key(filed.page)
            previous = self._filed.get(job.id)
            if previous is not None and (previous.inbox_key, previous.digest) == (key, current):
                return self._result(previous, repeated=True)
            today = self._today()
            if self._count.get(today, 0) >= self.daily_filings:
                raise FilingQuotaError(
                    f"the daily allowance of {self.daily_filings} filings is used up "
                    "(each filing starts a pipeline run)"
                )
            written = write_inbox(self.storage, filed.page)
            self._count = {today: self._count.get(today, 0) + 1}
            record = Filing(
                job_id=job.id,
                inbox_key=written,
                path=filed.page.path,
                digest=current,
                release_id=release_id,
                filed_at=self._now().astimezone(UTC).replace(microsecond=0),
            )
            self._filed[job.id] = record
            while len(self._filed) > MAX_RECORDS:
                self._filed.pop(next(iter(self._filed)))
            log.info("filed the answer of question %s as %s", job.id, written)
            return self._result(record, repeated=False)

    def _result(self, record: Filing, *, repeated: bool) -> dict[str, Any]:
        return {
            "job_id": record.job_id,
            **record.view(),
            "repeated": repeated,
            "filings_left": self.filings_left(),
        }
