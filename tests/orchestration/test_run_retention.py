"""Retention of old releases is best effort once the pointer is swapped."""

from __future__ import annotations

import json

from storage_doubles import RemoteStorage

from docwiki.contracts.layout import StorageKeys
from docwiki.contracts.storage import StorageError
from docwiki.orchestration.pipeline import build_state_key
from docwiki.release.publish import list_release_ids, read_current_pointer


async def test_retention_failure_after_the_swap_is_a_warning(make_harness, corpus):
    harness = make_harness(retention=1)
    remote = RemoteStorage(harness.storage)
    harness.storage = remote
    first = await harness.run()
    assert first.status == "succeeded", first.errors
    build_state: list[str] = []

    def transient_failure(key: str) -> None:
        if key.startswith(StorageKeys.RELEASES + "/"):
            state = json.loads(remote.inner.read_bytes(build_state_key("internal")))
            build_state.append(state["release_id"])
            raise StorageError("connection reset while deleting")

    remote.on_delete = transient_failure
    (corpus / "notes" / "extra.txt").write_text("Gearbox oil note for WTG-12.\n", encoding="utf-8")
    second = await harness.run()
    assert second.status == "succeeded", second.errors
    assert second.published
    assert read_current_pointer(harness.storage)[0].release_id == second.release_id
    assert any(warning.startswith("retention:") for warning in second.report.warnings)
    assert build_state and set(build_state) == {second.release_id}, "build state saved first"
    assert first.release_id in list_release_ids(harness.storage), "pruned by a later publish"
    remote.on_delete = None
    third = await harness.run()
    assert third.status == "no-op", "the build state of the published release was recorded"
