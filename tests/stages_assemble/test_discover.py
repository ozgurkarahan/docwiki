"""Stage ``discover``: work plan, state shards with ETags, tombstones, supersession."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from assemble_helpers import pack

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.layout import source_state_key
from docwiki.contracts.state import SourceState
from docwiki.contracts.storage import FolderStorage
from docwiki.stages.discover import SupersessionRecord, discover, resolve_supersession
from docwiki.storage.routed import DirectorySource, RoutedStorage

NOW = datetime(2026, 2, 15, 9, 0, tzinfo=UTC)


class CountingStorage(RoutedStorage):
    """Counts content reads made through the storage (ETag probes are not reads)."""

    reads: list[str]

    def read_bytes(self, key: str) -> bytes:
        self.reads.append(key)
        return super().read_bytes(key)


def _write(root: Path, rel: str, text: str) -> None:
    path = root.joinpath(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def _setup(tmp_path: Path) -> tuple[CountingStorage, Path]:
    raw = tmp_path / "raw"
    _write(raw, "procedures/SOP-GBX-010 rev A.txt", "rev A\n")
    _write(raw, "procedures/SOP-GBX-010 rev B.txt", "rev B supersedes nothing\n")
    _write(raw, "contracts/rate card.txt", "rates\n")
    _write(raw, "images/diagram.svg", "<svg/>")
    _write(raw, ".git/config", "ignored")
    storage = CountingStorage(
        FolderStorage(tmp_path / "work", fsync=False), {"raw": DirectorySource(raw)}
    )
    storage.reads = []
    return storage, raw


def test_new_unchanged_changed_and_deleted_sources(tmp_path: Path):
    storage, raw = _setup(tmp_path)
    domain = pack()
    plan = discover(storage, domain, now=NOW)
    rev_a = source_id_for("procedures/SOP-GBX-010 rev A.txt")
    rev_b = source_id_for("procedures/SOP-GBX-010 rev B.txt")
    card = source_id_for("contracts/rate card.txt")
    assert sorted(plan.new) == sorted([rev_a, rev_b, card])
    assert [skipped.raw_path for skipped in plan.skipped] == ["images/diagram.svg"]
    assert plan.items[card].state.sensitivity == "restricted"
    assert plan.items[rev_a].state.revision_group == "SOP-GBX-010"
    assert plan.supersedes == [(rev_b, rev_a)]
    assert plan.has_changes
    shard = SourceState.from_json(storage.read_bytes(source_state_key(rev_a)))
    assert shard.content_hash.startswith("sha256:") and shard.stages["discover"].status == "done"

    storage.reads.clear()
    again = discover(storage, domain, now=NOW + timedelta(minutes=1))
    assert sorted(again.unchanged) == sorted([rev_a, rev_b, card])
    assert not again.has_changes
    assert [key for key in storage.reads if key.startswith("raw/")] == []

    _write(raw, "procedures/SOP-GBX-010 rev B.txt", "rev B changed\n")
    (raw / "contracts" / "rate card.txt").unlink()
    later = discover(storage, domain, now=NOW + timedelta(minutes=2))
    assert later.changed == [rev_b]
    assert later.deleted == [card]
    tombstone = SourceState.from_json(storage.read_bytes(source_state_key(card)))
    assert tombstone.deleted and tombstone.deleted_at == NOW + timedelta(minutes=2)
    assert tombstone.first_seen_at == NOW

    _write(raw, "contracts/rate card.txt", "rates again\n")
    back = discover(storage, domain, now=NOW + timedelta(minutes=3))
    assert back.new == [card]
    revived = SourceState.from_json(storage.read_bytes(source_state_key(card)))
    assert not revived.deleted and revived.first_seen_at == NOW


def test_recompile_scopes_and_restricted_runs(tmp_path: Path):
    storage, _ = _setup(tmp_path)
    domain = pack()
    rev_a = source_id_for("procedures/SOP-GBX-010 rev A.txt")
    first = discover(storage, domain, now=NOW, recompile={rev_a: "notes", "src-000000000000": None})
    assert first.forced == [rev_a]
    assert first.items[rev_a].hints == "notes"
    assert first.notes and "src-000000000000" in first.notes[0]
    limited = discover(storage, domain, now=NOW, only=[rev_a])
    assert list(limited.items) == [rev_a] and limited.restricted
    assert limited.deleted == []
    capped = discover(storage, domain, now=NOW, limit=1)
    assert len(capped.items) == 1 and capped.deleted == []


def test_resolve_supersession_revisions_explicit_references_and_cycles():
    domain = pack()
    records = [
        SupersessionRecord("src-00000000000a", "SOP-GBX-010", "A"),
        SupersessionRecord("src-00000000000b", "SOP-GBX-010", "B"),
        SupersessionRecord("src-00000000000c", "SOP-GBX-010", "C"),
        SupersessionRecord("src-00000000000d", "SOP-GBX-011", "Z"),
        SupersessionRecord("src-00000000000e", "SOP-GBX-012", None, ("SOP-GBX-010",)),
        SupersessionRecord("src-00000000000f", "SOP-GBX-013", None, ("SOP-GBX-014",)),
        SupersessionRecord("src-000000000010", "SOP-GBX-014", None, ("SOP-GBX-013",)),
    ]
    groups, pairs = resolve_supersession(domain, records)
    assert groups == {"SOP-GBX-010": ["src-00000000000a", "src-00000000000b", "src-00000000000c"]}
    assert ("src-00000000000b", "src-00000000000a") in pairs
    assert ("src-00000000000c", "src-00000000000b") in pairs
    assert ("src-00000000000e", "src-00000000000c") in pairs
    assert not any("src-00000000000d" in pair for pair in pairs), "revision Z is not in order"
    assert not any("src-00000000000f" in pair for pair in pairs), "contradictory declarations"
    assert pairs == sorted(pairs)
