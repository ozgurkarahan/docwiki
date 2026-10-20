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

NOW = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
QUOTE_A = "devis/DEV-2026-014 indice A.txt"
QUOTE_B = "devis/DEV-2026-014 indice B.txt"
PRICE_STUDY = "restricted/etude de prix.txt"


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
    _write(raw, QUOTE_A, "indice A\n")
    _write(raw, QUOTE_B, "indice B without any explicit reference\n")
    _write(raw, PRICE_STUDY, "prices\n")
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
    rev_a = source_id_for(QUOTE_A)
    rev_b = source_id_for(QUOTE_B)
    study = source_id_for(PRICE_STUDY)
    assert sorted(plan.new) == sorted([rev_a, rev_b, study])
    assert [skipped.raw_path for skipped in plan.skipped] == ["images/diagram.svg"]
    assert plan.items[study].state.sensitivity == "restricted"
    assert plan.items[rev_a].state.revision_group == "DEV-2026-014"
    assert plan.supersedes == [(rev_b, rev_a)]
    assert plan.has_changes
    shard = SourceState.from_json(storage.read_bytes(source_state_key(rev_a)))
    assert shard.content_hash.startswith("sha256:") and shard.stages["discover"].status == "done"

    storage.reads.clear()
    again = discover(storage, domain, now=NOW + timedelta(minutes=1))
    assert sorted(again.unchanged) == sorted([rev_a, rev_b, study])
    assert not again.has_changes
    assert [key for key in storage.reads if key.startswith("raw/")] == []

    _write(raw, QUOTE_B, "indice B changed\n")
    (raw / "restricted" / "etude de prix.txt").unlink()
    later = discover(storage, domain, now=NOW + timedelta(minutes=2))
    assert later.changed == [rev_b]
    assert later.deleted == [study]
    tombstone = SourceState.from_json(storage.read_bytes(source_state_key(study)))
    assert tombstone.deleted and tombstone.deleted_at == NOW + timedelta(minutes=2)
    assert tombstone.first_seen_at == NOW

    _write(raw, PRICE_STUDY, "prices again\n")
    back = discover(storage, domain, now=NOW + timedelta(minutes=3))
    assert back.new == [study]
    revived = SourceState.from_json(storage.read_bytes(source_state_key(study)))
    assert not revived.deleted and revived.first_seen_at == NOW


def test_recompile_scopes_and_restricted_runs(tmp_path: Path):
    storage, _ = _setup(tmp_path)
    domain = pack()
    rev_a = source_id_for(QUOTE_A)
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
        SupersessionRecord("src-00000000000a", "DEV-2026-014", "A"),
        SupersessionRecord("src-00000000000b", "DEV-2026-014", "B"),
        SupersessionRecord("src-00000000000c", "DEV-2026-014", "C"),
        SupersessionRecord("src-00000000000d", "DEV-2026-015", "Z"),
        SupersessionRecord("src-00000000000e", "DEV-2026-016", None, ("DEV-2026-014",)),
        SupersessionRecord("src-00000000000f", "DEV-2026-017", None, ("DEV-2026-018",)),
        SupersessionRecord("src-000000000010", "DEV-2026-018", None, ("DEV-2026-017",)),
    ]
    groups, pairs = resolve_supersession(domain, records)
    assert groups == {"DEV-2026-014": ["src-00000000000a", "src-00000000000b", "src-00000000000c"]}
    assert ("src-00000000000b", "src-00000000000a") in pairs
    assert ("src-00000000000c", "src-00000000000b") in pairs
    assert ("src-00000000000e", "src-00000000000c") in pairs
    assert not any("src-00000000000d" in pair for pair in pairs), "revision Z is not in order"
    assert not any("src-00000000000f" in pair for pair in pairs), "contradictory declarations"
    assert pairs == sorted(pairs)
