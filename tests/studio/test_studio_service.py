from __future__ import annotations

from dataclasses import replace
from datetime import date

import pytest
from studio_testkit import (
    BROKEN_PATH,
    DONE_PATH,
    GONE_PATH,
    NEW_PATH,
    ODD_PATH,
    PENDING_PATH,
    RELEASE_ID,
    WIKI_URL,
)

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.storage import FolderStorage
from docwiki.studio.config import StudioConfig
from docwiki.studio.service import (
    StudioService,
    UploadConflictError,
    UploadError,
    UploadQuotaError,
    UploadTooLargeError,
)


def _service(storage: FolderStorage, config: StudioConfig, **kwargs: object) -> StudioService:
    return StudioService(storage, config, clock=iter(range(0, 10_000, 100)).__next__, **kwargs)  # type: ignore[arg-type]


def test_documents_merge_raw_files_with_pipeline_state(
    storage: FolderStorage, config: StudioConfig
) -> None:
    data = _service(storage, config).documents()
    by_path = {row["path"]: row for row in data["documents"]}
    assert {path: row["status"] for path, row in by_path.items()} == {
        NEW_PATH: "new",
        BROKEN_PATH: "failed",
        ODD_PATH: "quarantined",
        PENDING_PATH: "pending",
        GONE_PATH: "deleted",
        DONE_PATH: "done",
    }
    assert data["counts"] == {
        "new": 1,
        "failed": 1,
        "quarantined": 1,
        "pending": 1,
        "deleted": 1,
        "done": 1,
    }
    assert [row["status"] for row in data["documents"]] == [
        "new",
        "failed",
        "quarantined",
        "pending",
        "deleted",
        "done",
    ]
    done = by_path[DONE_PATH]
    assert done["in_release"] is True
    assert done["wiki_url"] == f"{WIKI_URL}/sources/2026-03-24-compte-rendu-de-chantier-n3"
    assert by_path[NEW_PATH]["source_id"] == source_id_for(NEW_PATH)
    assert by_path[BROKEN_PATH]["stage"] == "extract"
    assert "no text layer" in by_path[BROKEN_PATH]["last_error"]


def test_upload_writes_raw_and_shows_the_file_as_new(
    storage: FolderStorage, config: StudioConfig
) -> None:
    service = _service(storage, config)
    result = service.upload("uploads/Compte rendu (1).pdf", b"%PDF-1.7 report")
    assert result == {
        "path": "uploads/Compte rendu (1).pdf",
        "size": 15,
        "replaced": False,
        "source_id": source_id_for("uploads/Compte rendu (1).pdf"),
    }
    assert storage.read_bytes("raw/uploads/Compte rendu (1).pdf") == b"%PDF-1.7 report"
    rows = {row["path"]: row for row in service.documents()["documents"]}
    new = rows["uploads/Compte rendu (1).pdf"]
    assert new["status"] == "new"
    assert new["size"] == 15 and new["modified"] is not None
    assert service.uploads_left() == config.daily_uploads - 1


def test_upload_refuses_to_overwrite_unless_asked(
    storage: FolderStorage, config: StudioConfig
) -> None:
    service = _service(storage, config)
    with pytest.raises(UploadConflictError):
        service.upload(NEW_PATH, b"other")
    result = service.upload(NEW_PATH, b"# Fresh note v2\n", replace=True)
    assert result["replaced"] is True
    assert storage.read_bytes(f"raw/{NEW_PATH}") == b"# Fresh note v2\n"


@pytest.mark.parametrize(
    ("path", "data", "error"),
    [
        ("uploads/tool.exe", b"MZ", UploadError),
        ("../escape.md", b"x", UploadError),
        ("uploads/empty.md", b"", UploadError),
        ("uploads/big.md", b"x" * 11, UploadTooLargeError),
    ],
)
def test_invalid_uploads(
    storage: FolderStorage, config: StudioConfig, path: str, data: bytes, error: type[Exception]
) -> None:
    service = _service(storage, replace(config, max_upload_bytes=10))
    with pytest.raises(error):
        service.upload(path, data)
    if ".." not in path:
        assert not storage.exists(f"raw/{path}")


def test_daily_upload_allowance(storage: FolderStorage, config: StudioConfig) -> None:
    day = [date(2026, 3, 1)]
    service = StudioService(storage, replace(config, daily_uploads=1), today=lambda: day[0])
    service.upload("uploads/one.md", b"1")
    with pytest.raises(UploadQuotaError):
        service.upload("uploads/two.md", b"2")
    assert not storage.exists("raw/uploads/two.md")
    day[0] = date(2026, 3, 2)
    service.upload("uploads/two.md", b"2")
    assert storage.exists("raw/uploads/two.md")


def test_pipeline_shows_release_runs_and_queue(
    storage: FolderStorage, config: StudioConfig
) -> None:
    data = _service(storage, config, queue_depth=lambda: 3).pipeline()
    release = data["release"]
    assert release["release_id"] == RELEASE_ID
    assert (release["sources"], release["wiki_url"]) == (3, WIKI_URL)
    assert data["queued"] == 3
    newest, older = data["runs"]
    assert (newest["status"], older["status"]) == ("failed", "succeeded")
    assert (newest["is_current"], older["is_current"]) == (False, True)
    assert [stage["stage"] for stage in newest["stages"]] == ["discover", "extract"]
    assert newest["counts"]["quarantined"] == 1
    assert older["cost"] == {"currency": "USD", "total": 0.42, "duration_s": 540.0}
    assert newest["errors_total"] == 1


def test_queue_failures_degrade_to_unknown(storage: FolderStorage, config: StudioConfig) -> None:
    def broken() -> int:
        raise RuntimeError("queue unreachable")

    assert _service(storage, config, queue_depth=broken).pipeline()["queued"] is None
    assert _service(storage, config).pipeline()["queued"] is None


def test_reads_are_cached_briefly(storage: FolderStorage, config: StudioConfig) -> None:
    ticks = iter([0.0, 0.0, 1.0, 10.0, 10.0])
    service = StudioService(storage, config, clock=lambda: next(ticks))
    first = service.documents()
    storage.write_bytes("raw/uploads/late.md", b"late")
    assert service.documents() is first
    assert len(service.documents()["documents"]) == len(first["documents"]) + 1


def test_storage_check(storage: FolderStorage, config: StudioConfig) -> None:
    service = _service(storage, config)
    assert service.storage_ok() is True

    def fail(_prefix: str = "") -> list[str]:
        raise OSError("disk gone")

    storage.list = fail  # type: ignore[method-assign]
    assert service.storage_ok() is False
