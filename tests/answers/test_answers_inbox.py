"""The answers inbox ``work/inbox/queries/`` (ADR 0007)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from docwiki.answers import (
    INBOX_PREFIX,
    FolderRelease,
    build_query_page,
    inbox_key,
    read_inbox,
    reject_inbox_item,
    write_inbox,
)
from docwiki.answers.inbox import REJECTED_PREFIX
from docwiki.contracts.storage import FolderStorage, PreconditionFailedError

MOCK_DIR = (
    Path(__file__).resolve().parents[2]
    / "samples"
    / "fixtures"
    / "mock-release"
    / "releases"
    / "20260401T090000Z-8a41b109"
)


@pytest.fixture
def storage(tmp_path: Path) -> FolderStorage:
    return FolderStorage(tmp_path / "work-root")


def filed_page():  # type: ignore[no-untyped-def]
    text = (
        "The windows arrive on 2026-04-20 [1].\n\nSources:\n"
        "[1] Minutes — ¶ 11 — evidence/src-f0757603684a/para-0011.md\n"
    )
    answer = SimpleNamespace(text=text, sources=None, tool_calls=[], agent="a", version=None)
    return build_query_page(
        answer,
        question="Window delivery?",
        release=FolderRelease(MOCK_DIR),
        filed_on=date(2026, 10, 20),
    ).page


def test_write_then_read(storage: FolderStorage) -> None:
    page = filed_page()
    key = write_inbox(storage, page)
    assert key == inbox_key(page) == f"{INBOX_PREFIX}2026-10-20-window-delivery.md"
    items = read_inbox(storage)
    assert len(items) == 1 and items[0].error is None and items[0].page == page
    # filing the same question again the same day replaces the earlier filing
    write_inbox(storage, page)
    assert [item.key for item in read_inbox(storage)] == [key]


def test_files_that_are_not_query_pages_carry_an_error(storage: FolderStorage) -> None:
    storage.write_bytes(f"{INBOX_PREFIX}2026-10-20-broken.md", b"not a page")
    storage.write_bytes(f"{INBOX_PREFIX}notes.txt", b"x")
    storage.write_bytes(f"{INBOX_PREFIX}nested/2026-10-20-x.md", b"x")
    page = filed_page()
    renamed = page.render()
    storage.write_bytes(f"{INBOX_PREFIX}2026-10-20-other-name.md", renamed.encode("utf-8"))
    errors = {item.key.removeprefix(INBOX_PREFIX): item.error for item in read_inbox(storage)}
    assert errors["2026-10-20-broken.md"] and "invalid query page" in errors["2026-10-20-broken.md"]
    assert "not a query page file" in errors["notes.txt"]
    assert "not a query page file" in errors["nested/2026-10-20-x.md"]
    assert "does not match the page id" in errors["2026-10-20-other-name.md"]


def test_reject_moves_the_file_with_its_reason(storage: FolderStorage) -> None:
    storage.write_bytes(f"{INBOX_PREFIX}2026-10-20-broken.md", b"not a page")
    (item,) = read_inbox(storage)
    target = reject_inbox_item(storage, item, "invalid query page")
    assert target == "work/inbox/rejected/2026-10-20-broken.md"
    assert storage.read_bytes(target) == b"not a page"
    assert storage.read_bytes(f"{target}.reason.txt") == b"invalid query page\n"
    assert read_inbox(storage) == []


def test_items_carry_the_etag_of_the_version_read(storage: FolderStorage) -> None:
    key = write_inbox(storage, filed_page())
    storage.write_bytes(f"{INBOX_PREFIX}2026-10-20-broken.md", b"not a page")
    etags = {item.key: item.etag for item in read_inbox(storage)}
    assert etags == {
        f"{INBOX_PREFIX}2026-10-20-broken.md": storage.etag(f"{INBOX_PREFIX}2026-10-20-broken.md"),
        key: storage.etag(key),
    }


def test_an_answer_filed_again_after_the_read_is_neither_rejected_nor_deleted(
    storage: FolderStorage,
) -> None:
    key = f"{INBOX_PREFIX}2026-10-20-window-delivery.md"
    storage.write_bytes(key, b"not a page")
    (item,) = read_inbox(storage)
    newer = filed_page().render().encode("utf-8")
    storage.write_bytes(key, newer)  # the owner files the answer again while the run works
    with pytest.raises(PreconditionFailedError):
        reject_inbox_item(storage, item, "invalid query page")
    assert storage.read_bytes(key) == newer
    assert storage.list(REJECTED_PREFIX) == []
    with pytest.raises(PreconditionFailedError):
        storage.delete(item.key, if_match=item.etag)  # how a run consumes a published answer
    (current,) = read_inbox(storage)
    assert current.error is None and current.page == filed_page()
