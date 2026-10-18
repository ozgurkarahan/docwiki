"""BlobStorage against a fake Blob SDK, with FolderStorage parity checks."""

from __future__ import annotations

from pathlib import Path

import pytest
from fake_azure import Clock, FakeAccount, FakeLeaseClient, FakeServiceClient

from docwiki.contracts.storage import (
    FolderStorage,
    KeyNotFoundError,
    LeaseLostError,
    PreconditionFailedError,
    Storage,
    StorageError,
)
from docwiki.storage.blob import BlobStorage, clamp_lease


def make_blob(clock: Clock | None = None, **kwargs) -> tuple[BlobStorage, FakeAccount]:
    clock = clock or Clock()
    account = FakeAccount(clock)
    storage = BlobStorage(
        service_client=FakeServiceClient(account),
        lease_client_factory=FakeLeaseClient,
        clock=clock,
        **kwargs,
    )
    return storage, account


@pytest.fixture(params=["folder", "blob"])
def backend(request, tmp_path: Path) -> tuple[Storage, Clock]:
    clock = Clock()
    if request.param == "folder":
        return FolderStorage(tmp_path / "store", clock=clock, fsync=False), clock
    storage, _ = make_blob(clock)
    return storage, clock


def test_read_write_and_conditional_writes(backend):
    storage, _ = backend
    with pytest.raises(KeyNotFoundError):
        storage.read_bytes("work/state/sources/missing.json")
    assert storage.etag("work/a.json") is None
    assert not storage.exists("work/a.json")
    first = storage.write_bytes("work/a.json", b"one", if_none_match="*")
    assert storage.exists("work/a.json")
    data, etag = storage.read_with_etag("work/a.json")
    assert (data, etag) == (b"one", first)
    with pytest.raises(PreconditionFailedError):
        storage.write_bytes("work/a.json", b"again", if_none_match="*")
    second = storage.write_bytes("work/a.json", b"two", if_match=first)
    assert second != first and storage.etag("work/a.json") == second
    with pytest.raises(PreconditionFailedError):
        storage.write_bytes("work/a.json", b"stale", if_match=first)
    with pytest.raises(PreconditionFailedError):
        storage.write_bytes("work/new.json", b"x", if_match=first)
    assert storage.read_bytes("work/a.json") == b"two"


def test_list_is_recursive_sorted_and_prefix_filtered(backend):
    storage, _ = backend
    for key in ("work/b/2.json", "work/a.json", "releases/r1/manifest.json", "work/b/1.json"):
        storage.write_bytes(key, b"{}")
    assert storage.list("work/") == ["work/a.json", "work/b/1.json", "work/b/2.json"]
    assert storage.list("work/b") == ["work/b/1.json", "work/b/2.json"]
    assert storage.list("releases/") == ["releases/r1/manifest.json"]
    assert storage.list("") == sorted(
        ["work/b/2.json", "work/a.json", "releases/r1/manifest.json", "work/b/1.json"]
    )


def test_delete_semantics(backend):
    storage, _ = backend
    assert storage.delete("work/none.json") is False
    etag = storage.write_bytes("work/x.json", b"1")
    with pytest.raises(PreconditionFailedError):
        storage.delete("work/x.json", if_match="not-the-etag")
    assert storage.delete("work/x.json", if_match=etag) is True
    assert not storage.exists("work/x.json")
    with pytest.raises(PreconditionFailedError):
        storage.delete("work/x.json", if_match=etag)


def test_leases_are_exclusive_renewable_and_expire(backend):
    storage, clock = backend
    lease = storage.acquire_lease("work/state/lease", 30, owner="a")
    assert lease is not None
    assert storage.exists("work/state/lease")
    assert storage.acquire_lease("work/state/lease", 30, owner="b") is None
    renewed = storage.renew_lease(lease)
    assert renewed.lease_id == lease.lease_id
    storage.release_lease(renewed)
    again = storage.acquire_lease("work/state/lease", 30, owner="b")
    assert again is not None
    with pytest.raises(LeaseLostError):
        storage.release_lease(lease)
    with pytest.raises(LeaseLostError):
        storage.renew_lease(lease)
    clock.now += 120
    taken = storage.acquire_lease("work/state/lease", 30, owner="c")
    assert taken is not None, "an expired lease can be taken over"
    with pytest.raises(LeaseLostError):
        storage.renew_lease(again)
    storage.release_lease(taken)
    storage.release_lease(taken)  # releasing twice is a no-op


def test_expired_lease_can_be_renewed_while_nobody_took_it(backend):
    storage, clock = backend
    lease = storage.acquire_lease("work/state/lease", 30)
    assert lease is not None
    clock.now += 120
    assert storage.renew_lease(lease).lease_id == lease.lease_id


def test_lease_durations_are_clamped_to_the_blob_range():
    storage, _ = make_blob()
    short = storage.acquire_lease("work/state/lease", 5)
    assert short is not None and short.duration_s == 15
    storage.release_lease(short)
    long = storage.acquire_lease("work/state/lease", 600)
    assert long is not None and long.duration_s == 60
    assert clamp_lease(37.4) == 37
    with pytest.raises(ValueError):
        clamp_lease(0)


def test_containers_prefix_and_single_container_mapping():
    storage, account = make_blob(prefix="env1")
    storage.write_bytes("raw/docs/a.txt", b"a")
    storage.write_bytes("work/state/x.json", b"x")
    assert set(account.containers["raw"]) == {"env1/docs/a.txt"}
    assert set(account.containers["work"]) == {"env1/state/x.json"}
    assert storage.list("raw/") == ["raw/docs/a.txt"]
    with pytest.raises(ValueError):
        storage.write_bytes("other/x", b"1")

    renamed, account2 = make_blob(containers={"raw": "inputs", "work": "work", "releases": "rel"})
    account2.containers["inputs"] = {}
    account2.containers["rel"] = {}
    renamed.write_bytes("raw/a.pdf", b"%PDF")
    renamed.write_bytes("releases/current.json", b"{}")
    assert set(account2.containers["inputs"]) == {"a.pdf"}
    assert set(account2.containers["rel"]) == {"current.json"}
    assert renamed.list("") == ["raw/a.pdf", "releases/current.json"]

    clock = Clock()
    account3 = FakeAccount(clock, containers=("docwiki",))
    single = BlobStorage.single(
        None,
        "docwiki",
        prefix="dev",
        service_client=FakeServiceClient(account3),
        lease_client_factory=FakeLeaseClient,
    )
    single.write_bytes("raw/a.txt", b"a")
    single.write_bytes("work/b.json", b"b")
    assert set(account3.containers["docwiki"]) == {"dev/raw/a.txt", "dev/work/b.json"}
    assert single.list("work/") == ["work/b.json"]
    assert single.list("") == ["raw/a.txt", "work/b.json"]


def test_missing_container_lists_empty_and_reads_raise_key_errors():
    clock = Clock()
    account = FakeAccount(clock, containers=("work",))
    storage = BlobStorage(
        service_client=FakeServiceClient(account), lease_client_factory=FakeLeaseClient
    )
    assert storage.list("raw/") == []
    with pytest.raises(KeyNotFoundError):
        storage.read_bytes("raw/a.txt")
    with pytest.raises(StorageError):
        storage.write_bytes("raw/a.txt", b"x")


def test_unexpected_service_errors_surface_as_storage_errors():
    from azure.core.exceptions import HttpResponseError
    from fake_azure import error

    class Broken(FakeServiceClient):
        def get_container_client(self, name):
            client = super().get_container_client(name)

            def boom(**_):
                raise error(HttpResponseError, 500, "InternalError")

            client.list_blob_names = boom  # type: ignore[method-assign]
            return client

    account = FakeAccount(Clock())
    storage = BlobStorage(service_client=Broken(account), lease_client_factory=FakeLeaseClient)
    with pytest.raises(StorageError):
        storage.list("work/")


def test_requires_an_account_or_a_client():
    with pytest.raises(ValueError):
        BlobStorage()
