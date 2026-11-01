"""The retrieval probe sets (evals/golden/probes.py) follow the golden and probe rules."""

from __future__ import annotations

import copy
import importlib.util
import json
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest


@pytest.fixture(scope="module")
def probes(repo_root: Path) -> ModuleType:
    """The probe script, imported as a module (it is not a package)."""
    path = repo_root / "evals" / "golden" / "probes.py"
    spec = importlib.util.spec_from_file_location("golden_probes", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def checker(probes: ModuleType) -> Any:
    return probes.Checker()


@pytest.fixture(scope="module")
def tune(repo_root: Path) -> list[dict[str, Any]]:
    raw = (repo_root / "evals" / "golden" / "retrieval-tune.jsonl").read_bytes()
    assert b"\r" not in raw and raw.endswith(b"\n")
    return [json.loads(line) for line in raw.decode("utf-8").splitlines()]


def _encode(records: list[dict[str, Any]]) -> bytes:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    return ("\n".join(lines) + "\n").encode("utf-8")


def test_tune_set_passes(checker: Any, tune: list[dict[str, Any]]) -> None:
    code, report = checker.check(_encode(tune))
    assert code == 0, report
    assert report[0] == f"{len(tune)} probes checked: {len(tune)} passed, 0 failed"
    assert {record["split"] for record in tune} == {"retrieval-tune"}
    kinds = {record["probe"] for record in tune}
    assert kinds == {"paraphrase-fr", "en-to-fr", "lexical-control", "multi-chantier"}


def test_cli_checks_the_tune_set(probes: ModuleType, repo_root: Path) -> None:
    path = repo_root / "evals" / "golden" / "retrieval-tune.jsonl"
    assert probes.main(["--check", "--file", str(path)]) == 0


def _first(tune: list[dict[str, Any]], probe: str) -> dict[str, Any]:
    return copy.deepcopy(next(record for record in tune if record["probe"] == probe))


def _set(key: str, value: Any) -> Callable[[dict[str, Any]], None]:
    return lambda record: record.__setitem__(key, value)


MUTATIONS: list[tuple[str, str, Callable[[dict[str, Any]], None]]] = [
    ("probe-schema", "paraphrase-fr", lambda record: record.pop("within")),
    ("probe-kind", "paraphrase-fr", _set("probe", "rephrase")),
    ("probe-split", "paraphrase-fr", _set("split", "dev")),
    ("probe-audience", "paraphrase-fr", _set("audience", "internal")),
    ("probe-abstain", "paraphrase-fr", _set("abstain", True)),
    ("probe-within", "paraphrase-fr", _set("within", "nowhere")),
    ("probe-lang", "paraphrase-fr", _set("lang", "en")),
    (
        "probe-glossary",
        "en-to-fr",
        lambda record: record.__setitem__("question", record["question"] + " Which invoice?"),
    ),
    ("probe-control", "lexical-control", _set("question", "Quand le contrôle a-t-il eu lieu ?")),
    (
        "probe-multi",
        "multi-chantier",
        lambda record: record.__setitem__(
            "required_citations", record["required_citations"][:1]
        ),
    ),
]


@pytest.mark.parametrize(("code", "probe", "mutate"), MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_each_rule_fires(
    checker: Any,
    tune: list[dict[str, Any]],
    code: str,
    probe: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    record = _first(tune, probe)
    mutate(record)
    status, report = checker.check(_encode([record]))
    assert status == 1
    assert f"{record['id']}: " in "\n".join(report)
    (line,) = [line for line in report if line.startswith(f"{record['id']}: ")]
    assert code in line.split(": ", 1)[1].split(", ")


def test_bad_json_and_duplicate_ids_are_labelled_by_line(
    checker: Any, tune: list[dict[str, Any]]
) -> None:
    raw = _encode([tune[0], tune[0]]) + b"{not json\n"
    status, report = checker.check(raw)
    assert status == 1
    joined = "\n".join(report)
    assert "line 3: json" in joined
    assert tune[0]["id"] + ":" not in joined  # a duplicated id is not trusted as a label


def test_report_holds_no_question_or_evidence_text(
    checker: Any, tune: list[dict[str, Any]]
) -> None:
    records = copy.deepcopy(tune)
    records[0]["probe"] = "rephrase"
    _, report = checker.check(_encode(records))
    joined = "\n".join(report)
    for record in tune:
        assert record["question"] not in joined
        for item in record.get("must_include") or []:
            if len(str(item)) > 12:
                assert str(item) not in joined
    assert any(line.startswith("sha256: ") for line in report)


def test_dump_refuses_restricted_and_unknown_documents(checker: Any) -> None:
    restricted = sorted(
        path
        for path, entry in checker.corpus.entries.items()
        if entry["sensitivity"] == "restricted"
    )
    assert restricted
    assert checker.dump(restricted[0]) is None
    assert checker.dump("full/nowhere.pdf") is None
    public = checker.public_paths()
    assert public and not set(public) & set(restricted)
    lines = checker.dump(public[0])
    assert lines and all("\t" in line for line in lines)
