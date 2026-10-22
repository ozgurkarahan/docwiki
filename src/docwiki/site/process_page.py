"""The ``how-it-works`` page (ADR 0009): how a document becomes cited wiki pages.

The site build writes it next to the release's content, so it carries the wiki's navigation,
search and drawer. Its text is static; the live part (each document's status, the queue, the
runs and, for the signed-in owner, the upload form) is filled on the client from the portal's
``/api/process`` by the ``Process`` component, and says so on a static host.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["PROCESS_SLUG", "STAGES", "process_markdown", "write_process_page"]

PROCESS_SLUG = "how-it-works"

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
    ("verify", "Runs the quality gates: a blocking failure stops the release."),
    ("site", "Builds this website from the candidate release."),
    ("publish", "Publishes the release atomically: the site switches to it within a minute."),
)


def process_markdown() -> str:
    rows = "\n".join(
        f"| {number} | `{stage}` | {text} |" for number, (stage, text) in enumerate(STAGES, 1)
    )
    return f"""---
title: How it works
---

This wiki was not written by hand. A folder of ordinary documents (PDF, Word, Excel, CSV,
PowerPoint, e-mail, scans) is compiled into the pages you read, and every fact keeps a footnote
that opens the exact passage it came from. When a document is added, the pipeline runs again and
a new release of the whole wiki replaces the old one.

Below, live: every document and where it is in the pipeline, and the last runs with their stages,
timings and cost. The owner, signed in, adds documents here and follows them until their pages
appear.

## The pipeline

| # | Stage | What it does |
|---|---|---|
{rows}

Models are used only where judgement is needed (classifying an unusual document, writing source
and topic pages); everything derivable from structure is computed by code. A run reuses what did
not change, so adding one document costs well under a dollar and takes a few minutes.

## Live
"""


def write_process_page(content_dir: Path) -> bool:
    """Write ``how-it-works.md`` into the Quartz content unless the release has its own."""
    target = content_dir / f"{PROCESS_SLUG}.md"
    if target.exists():
        return False
    target.write_text(process_markdown(), encoding="utf-8", newline="\n")
    return True
