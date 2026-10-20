"""Filed research answers (ADR 0007): reviewed Researcher answers become ``queries/`` pages.

* :mod:`docwiki.answers.filing` turns an answer into a contract query page (citations, badges,
  number checks, content safety, how it was produced).
* :mod:`docwiki.answers.inbox` reads and writes the inbox ``work/inbox/queries/`` that the next
  run merges into the wiki.
"""

from __future__ import annotations

from docwiki.answers.filing import (
    APPROVED_BY,
    FiledAnswer,
    FilingError,
    FolderRelease,
    ReleaseLookup,
    StorageRelease,
    build_query_page,
)
from docwiki.answers.inbox import (
    INBOX_PREFIX,
    InboxItem,
    inbox_key,
    read_inbox,
    reject_inbox_item,
    write_inbox,
)

__all__ = [
    "APPROVED_BY",
    "INBOX_PREFIX",
    "FiledAnswer",
    "FilingError",
    "FolderRelease",
    "InboxItem",
    "ReleaseLookup",
    "StorageRelease",
    "build_query_page",
    "inbox_key",
    "read_inbox",
    "reject_inbox_item",
    "write_inbox",
]
