"""The inbox of filed research answers: ``work/inbox/queries/<yyyy-mm-dd>-<slug>.md``.

The owner's ``docwiki file-answer`` (the CLI with the deployer's data role) puts one contract
query page per answer here; the next run merges the inbox into ``queries/``, deletes what it
published and moves what it could not use to ``work/inbox/rejected/`` with the reason. Both only
touch the version the run read (its ETag): an answer filed again under the same name meanwhile
stays in the inbox for the next run.
"""

from __future__ import annotations

from dataclasses import dataclass

from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.pages import Page, QueryFrontmatter
from docwiki.contracts.storage import KeyNotFoundError, PreconditionFailedError, Storage

__all__ = [
    "INBOX_PREFIX",
    "REJECTED_PREFIX",
    "InboxItem",
    "inbox_key",
    "read_inbox",
    "reject_inbox_item",
    "write_inbox",
]

INBOX_PREFIX = f"{StorageKeys.INBOX_QUERIES}/"
REJECTED_PREFIX = f"{StorageKeys.INBOX_REJECTED}/"


@dataclass(frozen=True)
class InboxItem:
    """One inbox file: its page, or why it cannot be merged, and the ETag of the version read."""

    key: str
    page: Page | None
    error: str | None = None
    etag: str | None = None
    """ETag of the content read; ``None`` accepts whichever version is there when consumed."""


def inbox_key(page: Page) -> str:
    """Inbox key of a query page (its file name under ``work/inbox/queries/``)."""
    if not isinstance(page.frontmatter, QueryFrontmatter):
        raise ValueError("only query pages go to the answers inbox")
    return INBOX_PREFIX + page.path.rsplit("/", 1)[-1]


def write_inbox(storage: Storage, page: Page) -> str:
    """Write ``page`` to the inbox (replacing an earlier filing of the same question that day)."""
    key = inbox_key(page)
    storage.write_bytes(key, page.render().encode("utf-8"))
    return key


def read_inbox(storage: Storage) -> list[InboxItem]:
    """Every inbox file, parsed, with the ETag of the version read. A file that is not a valid
    query page carries an ``error``."""
    items: list[InboxItem] = []
    for key in storage.list(INBOX_PREFIX):
        try:
            data, etag = storage.read_with_etag(key)
        except KeyNotFoundError:
            continue  # consumed meanwhile
        name = key[len(INBOX_PREFIX) :]
        if "/" in name or not name.endswith(".md"):
            error = "not a query page file (queries/<date>-<slug>.md)"
            items.append(InboxItem(key, None, error, etag))
            continue
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            items.append(InboxItem(key, None, "not UTF-8 text", etag))
            continue
        try:
            page = Page.parse(text, f"queries/{name}")
        except Exception as exc:  # contract validation errors of any kind
            items.append(InboxItem(key, None, f"invalid query page: {_short(exc)}", etag))
            continue
        if not isinstance(page.frontmatter, QueryFrontmatter):
            error = f"type {page.frontmatter.type!r}, not a query page"
            items.append(InboxItem(key, None, error, etag))
            continue
        expected = f"queries/{page.frontmatter.id.removeprefix('query:')}.md"
        if expected != page.path:
            error = f"file name does not match the page id ({expected})"
            items.append(InboxItem(key, None, error, etag))
            continue
        items.append(InboxItem(key, page, etag=etag))
    return items


def reject_inbox_item(storage: Storage, item: InboxItem, reason: str) -> str:
    """Move an inbox file to ``work/inbox/rejected/`` with a ``.reason.txt`` next to it.

    Only the version that was read moves: when the file was filed again since (another ETag),
    :class:`~docwiki.contracts.storage.PreconditionFailedError` is raised and the newer filing
    stays in the inbox for the next run (a filing that lands between the copy and the delete
    leaves the copy of the version read in ``rejected/`` as well).
    """
    name = item.key[len(INBOX_PREFIX) :].replace("/", "-") or "item"
    target = REJECTED_PREFIX + name
    try:
        data, etag = storage.read_with_etag(item.key)
    except KeyNotFoundError:
        return target
    if item.etag is not None and etag != item.etag:
        raise PreconditionFailedError(f"{item.key} changed since it was read")
    storage.write_bytes(target, data)
    storage.write_bytes(f"{target}.reason.txt", (reason.strip() + "\n").encode("utf-8"))
    storage.delete(item.key, if_match=etag)
    return target


def _short(exc: BaseException) -> str:
    return " ".join(str(exc).split())[:300]
