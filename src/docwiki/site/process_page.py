"""The ``pipeline`` and ``documents`` pages (ADR 0009, 0010): the first two of the site's three
tabs, ① Documents · ② Pipeline · ③ Wiki.

The site build writes them next to the release's content, so they carry the wiki's navigation,
search and drawer. Their text is static. On ``pipeline`` the live part (the owner's box, each
document's status, the queue and the runs) is filled on the client from the portal's
``/api/process`` by the ``Process`` and ``OwnerBox`` components, which also show the 13 technical
steps of :data:`STAGES` in a disclosure. On ``documents`` the ``Documents`` component lists the
release's documents.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "DOCUMENTS_SLUG",
    "PROCESS_SLUG",
    "STAGES",
    "documents_markdown",
    "process_markdown",
    "write_documents_page",
    "write_process_page",
]

PROCESS_SLUG = "pipeline"
DOCUMENTS_SLUG = "documents"

STAGES: tuple[tuple[str, str], ...] = (
    ("discover", "Lists the documents, spots what is new, changed or deleted, groups revisions."),
    ("extract", "Reads the text, tables and figures of each file, page by page and row by row."),
    ("classify", "Gives each document its type, revision and sensitivity (rules first)."),
    ("compile", "A model writes the source page: summary, key facts and sections, each cited."),
    ("entities", "Builds a page for each known thing (equipment, site, party) from the facts."),
    ("topics", "Writes topic pages across documents, with contradictions and superseded parts."),
    ("links", "Links pages to each other and adds the backlinks, by rule, not by a model."),
    ("indexes", "Writes the home page, indexes, glossary, change log and search index."),
    ("agentkit", "Writes the agent guide and skills from reviewed templates."),
    ("evidence", "Saves the exact passage behind every citation, with the original page image."),
    (
        "translate",
        "Writes the wiki in its other languages; numbers, citations and trade terms are checked.",
    ),
    ("verify", "Runs the quality gates: a blocking failure stops the release."),
    ("site", "Builds this website from the candidate release."),
    ("publish", "Publishes the release atomically: the site switches to it within a minute."),
)


def process_markdown() -> str:
    return """---
title: Pipeline
---

This wiki was not written by hand. Ordinary documents (PDF, Word, Excel, e-mail, scans) are
compiled into the pages you read, and every fact keeps a footnote that opens the exact passage it
came from. When a document is added, the pipeline runs again and a new release of the whole wiki
replaces the old one.

Below, live: every document and where it is in the pipeline, and the runs that changed the wiki,
with their timings and cost. Models are used only where judgement is needed; everything derivable
from structure is computed by code, and a run reuses what did not change.

## Live
"""


def documents_markdown() -> str:
    return """---
title: Documents
---

The raw documents this wiki is compiled from, as they were received: quotes, contracts, plans,
invoices, e-mails, photos and scans. Open the original, or the wiki page compiled from it.
"""


def _write_once(target: Path, text: str) -> bool:
    if target.exists():
        return False
    target.write_text(text, encoding="utf-8", newline="\n")
    return True


def write_process_page(content_dir: Path) -> bool:
    """Write ``pipeline.md`` into the Quartz content unless the release has its own."""
    return _write_once(content_dir / f"{PROCESS_SLUG}.md", process_markdown())


def write_documents_page(content_dir: Path) -> bool:
    """Write ``documents.md`` into the Quartz content unless the release has its own."""
    return _write_once(content_dir / f"{DOCUMENTS_SLUG}.md", documents_markdown())
