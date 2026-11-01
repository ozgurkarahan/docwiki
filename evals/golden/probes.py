"""Retrieval probe sets: format, checker and authoring aids.

A probe is a golden record (``author.py``) with three more fields: ``probe`` (what it tests),
``within`` (a scope value or null) and ``audience`` (always ``public``). The retrieval bench
(``evals/retrieval_bench.py``) runs each probe's question through ``answer_context`` with its
``within`` and ``lang``.

    uv run python evals/golden/probes.py --check --file evals/golden/retrieval-tune.jsonl
    uv run python evals/golden/probes.py --list                  # public documents of full/
    uv run python evals/golden/probes.py --dump <source_path>    # their units and locator keys

``--check`` prints aggregates, question ids, error codes and the file's SHA-256 only: never
question text, answers, items or cited paths, so a private (blind) set can be checked in public.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
import unicodedata
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml

GOLDEN = Path(__file__).resolve().parent
REPO_ROOT = GOLDEN.parents[1]
GLOSSARY = REPO_ROOT / "domains" / "batiment" / "glossary.yaml"

PROBE_FIELDS = ("probe", "within", "audience")
PROBES = frozenset({"paraphrase-fr", "en-to-fr", "lexical-control", "multi-chantier"})
SPLITS = frozenset({"retrieval-tune", "retrieval-blind"})
AUDIENCES = frozenset({"public"})
DEFAULT_SCOPE = "entreprise"
_CHANTIER = re.compile(r"^full/chantiers/([a-z0-9-]+)/")
_WORD = re.compile(r"[a-z0-9]+")
_CODE = re.compile(r"\S*\d\S*")

PROBE_ERRORS = {
    "probe-schema": "a probe field is missing or mistyped, or the record has an unknown field",
    "probe-kind": "probe is not one of the probe kinds",
    "probe-split": "split is neither retrieval-tune nor retrieval-blind",
    "probe-audience": "audience is not public",
    "probe-abstain": "a probe never abstains and always cites",
    "probe-within": "within is not a scope of the corpus, or a citation lies outside it",
    "probe-lang": "paraphrase-fr questions are in French, en-to-fr questions in English",
    "probe-glossary": "an en-to-fr question uses a term or synonym of the domain glossary",
    "probe-control": "a lexical-control question has no code or number printed in its evidence",
    "probe-multi": "a multi-chantier question has a within or cites fewer than two chantiers",
}


def _author() -> ModuleType:
    module = sys.modules.get("golden_author")
    if module is None:
        spec = importlib.util.spec_from_file_location("golden_author", GOLDEN / "author.py")
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules["golden_author"] = module
        spec.loader.exec_module(module)
    return module


def fold(text: str) -> str:
    """Case-folded, accent-free text (for word comparisons only)."""
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(char for char in text if not unicodedata.combining(char))


def words(text: str) -> list[str]:
    return _WORD.findall(fold(text))


def scope_of(source_path: str) -> str:
    """The scope value of a corpus path, by the rule of ``domains/batiment/scopes.yaml``."""
    match = _CHANTIER.match(source_path)
    return match.group(1) if match else DEFAULT_SCOPE


def glossary_terms(path: Path = GLOSSARY) -> list[tuple[str, ...]]:
    """Every term and synonym of the glossary, as word tuples."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    found: set[tuple[str, ...]] = set()
    for entry in data["terms"]:
        names = [entry["term"]]
        for values in (entry.get("synonyms") or {}).values():
            names.extend(values)
        found.update(tuple(words(name)) for name in names if words(name))
    return sorted(found)


def _has_phrase(tokens: Sequence[str], phrase: Sequence[str]) -> bool:
    size = len(phrase)
    return any(tuple(tokens[i : i + size]) == tuple(phrase) for i in range(len(tokens) - size + 1))


def overlap(question: str, evidence: str) -> float | None:
    """Share of the question's content words (four letters or more) found in the evidence."""
    content = {word for word in words(question) if len(word) >= 4 and not word.isdigit()}
    if not content:
        return None
    return len(content & set(words(evidence))) / len(content)


class Checker:
    """The per-record rules of a probe set (the golden rules plus the probe rules)."""

    def __init__(self) -> None:
        self.author = _author()
        self.corpus = self.author.Corpus()
        self.scopes = sorted(
            {
                scope_of(path)
                for path, entry in self.corpus.entries.items()
                if path.startswith("full/") and entry["sensitivity"] != "restricted"
            }
        )
        self.glossary = glossary_terms()

    def evidence(self, record: dict[str, Any]) -> str:
        texts: list[str] = []
        for citation in record.get("required_citations") or []:
            path = citation.get("source_path")
            if path not in self.corpus.entries:
                continue
            text = self.author.locator_text(self.corpus.doc(path), citation["locator_key"])
            if text:
                texts.append(text)
        return "\n".join(texts)

    def probe_codes(self, record: dict[str, Any]) -> list[str]:
        codes: list[str] = []
        known = set(self.author.FIELDS) | set(PROBE_FIELDS)
        within = record.get("within")
        if (
            not all(key in record for key in PROBE_FIELDS)
            or set(record) - known
            or not isinstance(record.get("probe"), str)
            or not (within is None or isinstance(within, str))
            or not isinstance(record.get("audience"), str)
        ):
            return ["probe-schema"]
        probe = record["probe"]
        if probe not in PROBES:
            codes.append("probe-kind")
        if record.get("split") not in SPLITS:
            codes.append("probe-split")
        if record["audience"] not in AUDIENCES:
            codes.append("probe-audience")
        citations = record.get("required_citations") or []
        if record.get("abstain") is not False or not citations:
            codes.append("probe-abstain")
        cited_scopes = {scope_of(str(citation.get("source_path"))) for citation in citations}
        if within is not None and (within not in self.scopes or cited_scopes - {within}):
            codes.append("probe-within")
        lang = record.get("lang")
        question = str(record.get("question", ""))
        if (probe == "paraphrase-fr" and lang != "fr") or (probe == "en-to-fr" and lang != "en"):
            codes.append("probe-lang")
        if probe == "en-to-fr":
            tokens = words(question)
            if any(_has_phrase(tokens, term) for term in self.glossary):
                codes.append("probe-glossary")
        if probe == "lexical-control":
            haystack = self.author.normalize_text(self.evidence(record))
            values = self.author.extract_values(haystack)
            tokens = [token.strip("?!.,;:()«»\"'") for token in _CODE.findall(question)]
            if not any(
                len(token) >= 3 and self.author.contains_item(token, haystack, values)
                for token in tokens
            ):
                codes.append("probe-control")
        if probe == "multi-chantier" and (
            within is not None or len(cited_scopes - {DEFAULT_SCOPE}) < 2
        ):
            codes.append("probe-multi")
        return codes

    def check(self, raw: bytes) -> tuple[int, list[str]]:
        """Verify a probe set. The report holds aggregates, ids, error codes and the SHA-256
        only."""
        sha256 = hashlib.sha256(raw).hexdigest()
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return 1, ["the probe file is not UTF-8", f"sha256: {sha256}"]
        records: list[tuple[str, dict[str, Any]]] = []
        problems: dict[str, list[str]] = {}
        for number, line in enumerate(text.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                record = None
            if not isinstance(record, dict):
                problems.setdefault(f"line {number}", []).append("json")
                continue
            records.append((f"line {number}", record))
        ids = Counter(qid for _, record in records if isinstance(qid := record.get("id"), str))
        labelled: list[tuple[str, dict[str, Any]]] = []
        for label, record in records:
            qid = record.get("id")
            safe = (
                isinstance(qid, str) and self.author.SAFE_ID.match(qid) and ids[qid] == 1
            )
            labelled.append((qid if safe else label, record))

        golden = [
            (label, {key: record[key] for key in self.author.FIELDS if key in record})
            for label, record in labelled
        ]
        found, _ = self.author.check_records(golden, self.corpus, private=True)
        for problem in found:
            problems.setdefault(problem.label, []).append(problem.code)
        overlaps: dict[str, list[float]] = {}
        for label, record in labelled:
            try:
                codes = self.probe_codes(record)
                value = overlap(str(record.get("question", "")), self.evidence(record))
            except Exception:
                codes, value = ["internal-error"], None
            problems.setdefault(label, []).extend(codes)
            if value is not None and isinstance(record.get("probe"), str):
                overlaps.setdefault(record["probe"], []).append(value)
        failing = {label: list(dict.fromkeys(codes)) for label, codes in problems.items() if codes}

        def tally(key: str, known: frozenset[str]) -> str:
            counts = Counter(
                value if isinstance(value := record.get(key), str) and value in known else "other"
                for _, record in labelled
            )
            return ", ".join(f"{name}={count}" for name, count in sorted(counts.items())) or "none"

        total = len(labelled) + sum(1 for codes in failing.values() if "json" in codes)
        scoped = sum(1 for _, record in labelled if isinstance(record.get("within"), str))
        report = [
            f"{total} probes checked: {total - len(failing)} passed, {len(failing)} failed",
            f"probes: {tally('probe', PROBES)}",
            f"languages: {tally('lang', self.author.LANGS)}",
            f"splits: {tally('split', SPLITS)}",
            f"with within: {scoped}",
            "mean word overlap of question and evidence: "
            + (
                ", ".join(
                    f"{name}={sum(values) / len(values):.2f}"
                    for name, values in sorted(overlaps.items())
                    if name in PROBES
                )
                or "none"
            ),
            f"sha256: {sha256}",
        ]
        report += [f"{label}: {', '.join(codes)}" for label, codes in failing.items()]
        return (1 if failing else 0), report

    # -------------------------------------------------------------------- authoring aids

    def public_paths(self) -> list[str]:
        return sorted(
            path
            for path, entry in self.corpus.entries.items()
            if path.startswith("full/")
            and entry["sensitivity"] != "restricted"
            and not entry.get("held_back")
            and not entry.get("copy_of")
            and entry["format"] not in self.author.IMAGE_FORMATS
        )

    def listing(self) -> list[str]:
        return [
            f"{path}\t{self.corpus.entries[path]['format']}\t{scope_of(path)}"
            for path in self.public_paths()
        ]

    def dump(self, source_path: str) -> list[str] | None:
        if source_path not in self.public_paths():
            return None
        return [f"{key}\t{text}" for key, text in self.corpus.doc(source_path).units]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check and author retrieval probe sets.")
    parser.add_argument("--check", action="store_true", help="verify the --file probe set")
    parser.add_argument("--file", type=Path, help="with --check: the JSONL probe set")
    parser.add_argument("--list", action="store_true", help="public documents of full/")
    parser.add_argument("--dump", metavar="SOURCE_PATH", help="units of one public document")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    checker = Checker()
    if args.list:
        print("\n".join(checker.listing()))
        return 0
    if args.dump:
        lines = checker.dump(args.dump)
        if lines is None:
            print("not a public document of full/ (see --list)")
            return 2
        print("\n".join(lines))
        return 0
    if not (args.check and args.file):
        parser.error("give --check --file <set>, --list or --dump <source_path>")
    try:
        raw = args.file.read_bytes()
    except OSError:
        print("cannot read the probe file")
        return 2
    code, report = checker.check(raw)
    print("\n".join(report))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
