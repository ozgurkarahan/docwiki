"""Compile fidelity: does the compiled wiki say what the documents say? No model, no Azure.

Run on a release folder::

    uv run python evals/compile_fidelity.py --release <release folder> \
        --out evals/results/<date>-compile-fidelity.json

The expectations come from the fictional world's ground truth (``samples/fiction/bible.yaml``)
through ``evals/golden/compile-fidelity.yaml``, never from a compiled wiki. Measures:

* **revisions** - a source page's ``status`` and ``superseded_by`` (by source path);
* **facts** - every value of a fact appears in one section of one topic or view page of its
  scope (``synthesised``) and, less strictly, in one section of any page of the French tree
  (``compiled``). A fact that is not even compiled was lost at compilation; one that is compiled
  but not synthesised stayed on source or entity pages. Footnote definitions are not read: the
  measure is what the wiki states, not what it quotes;
* **cross** - every value in one section of one topic or view page, any scope (cross-chantier
  syntheses);
* **scope_absent** - abstain facts: none of the terms on a page of the scope;
* **forbidden** - the bible's restricted-only values and injection strings anywhere in the wiki,
  the evidence or the catalog (0 expected);
* **stamp_as_content** - pages that state the document stamp ("NOT FOR OPERATIONAL USE") outside
  the wiki's own fictional banner (a known limitation, counted).

Values are compared with the evaluation's normalisation (``evals/textnorm.py``): ``47 271,60 €``
matches ``47271,60 €`` and ``30/03/2026`` matches ``2026-03-30``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from docwiki.contracts.frontmatter import load_yaml_mapping, split_frontmatter
from evals.textnorm import Values, contains_item, extract_values, normalize_text

__all__ = [
    "FIDELITY_FORMAT",
    "FidelitySpecError",
    "Page",
    "build_report",
    "forbidden_strings",
    "load_pages",
    "load_spec",
    "main",
    "value_found",
]

FIDELITY_FORMAT = "docwiki.evals.compile-fidelity/v1"
DEFAULT_SPEC = Path("evals/golden/compile-fidelity.yaml")
DEFAULT_BIBLE = Path("samples/fiction/bible.yaml")
SYNTHESIS_TYPES = frozenset({"topic", "view"})
COMPANY_SCOPE = "entreprise"
STAMP_TERM = "not for operational use"
BANNER_PREFIX = "> fictional sample"
_SKIPPED_TOP = frozenset({"en", "_meta"})


class FidelitySpecError(ValueError):
    """The fidelity spec or the bible is malformed."""


@dataclass(frozen=True)
class Section:
    heading: str
    norm: str
    values: Values


@dataclass(frozen=True)
class Page:
    path: str
    data: Mapping[str, Any]
    sections: tuple[Section, ...]
    stated_norm: str

    @property
    def type(self) -> str:
        return str(self.data.get("type") or "")

    @property
    def scope(self) -> str | None:
        scope = self.data.get("scope")
        return str(scope) if scope else None


# ------------------------------------------------------------------------------------ loading


def _sections(body: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, list[str]]] = [("", [])]
    for line in body.split("\n"):
        stripped = line.lstrip()
        if stripped.startswith("[^") and "]:" in stripped:
            continue
        if line.startswith("#"):
            sections.append((line.lstrip("#").strip(), []))
            continue
        sections[-1][1].append(line)
    return [(heading, "\n".join(lines)) for heading, lines in sections]


def _page(path: str, text: str) -> Page:
    yaml_text, body = split_frontmatter(text)
    data = load_yaml_mapping(yaml_text, where=path) if yaml_text is not None else {}
    parsed: list[Section] = []
    stated: list[str] = [str(data.get("summary") or "")]
    for heading, section_text in _sections(body):
        kept = [
            line
            for line in section_text.split("\n")
            if not normalize_text(line).startswith(BANNER_PREFIX)
        ]
        norm = normalize_text(heading + "\n" + "\n".join(kept))
        stated.append(norm)
        parsed.append(Section(heading, norm, extract_values(norm)))
    return Page(path, data, tuple(parsed), normalize_text("\n".join(stated)))


def load_pages(release: Path) -> list[Page]:
    """Pages of the French wiki tree (no English mirror, agent kit folders or ``_meta``)."""
    wiki = release / "wiki"
    if not wiki.is_dir():
        raise FileNotFoundError(f"no wiki folder in {release}")
    pages: list[Page] = []
    for file in sorted(wiki.rglob("*.md")):
        parts = file.relative_to(wiki).parts
        if parts[0] in _SKIPPED_TOP or any(part.startswith(".") for part in parts):
            continue
        relative = file.relative_to(release).as_posix()
        pages.append(_page(relative, file.read_text(encoding="utf-8")))
    return pages


def load_spec(path: Path) -> dict[str, list[dict[str, Any]]]:
    data = load_yaml_mapping(path.read_text(encoding="utf-8"), where=str(path))
    if data.get("schema") != 1:
        raise FidelitySpecError(f"{path}: schema 1 expected")
    spec: dict[str, list[dict[str, Any]]] = {}
    seen: set[str] = set()
    for kind, required in (
        ("revisions", ("source_path", "status")),
        ("facts", ("scope", "values")),
        ("cross", ("values",)),
        ("scope_absent", ("scope", "terms")),
    ):
        items = data.get(kind) or []
        if not isinstance(items, list):
            raise FidelitySpecError(f"{path}: {kind} must be a list")
        for item in items:
            if not isinstance(item, Mapping) or not item.get("id"):
                raise FidelitySpecError(f"{path}: every {kind} item needs an id")
            missing = [key for key in required if not item.get(key)]
            if missing:
                raise FidelitySpecError(f"{path}: {item['id']} lacks {', '.join(missing)}")
            if item["id"] in seen:
                raise FidelitySpecError(f"{path}: duplicate id {item['id']}")
            seen.add(item["id"])
        spec[kind] = [dict(item) for item in items]
    return spec


def _collect(node: Any, key: str) -> Iterable[Any]:
    if isinstance(node, Mapping):
        for name, value in node.items():
            if name == key:
                yield value
            else:
                yield from _collect(value, key)
    elif isinstance(node, list):
        for value in node:
            yield from _collect(value, key)


def forbidden_strings(bible: Mapping[str, Any]) -> list[str]:
    """Restricted-only values (``long``) and the injection's forbidden outputs of the bible."""
    found: list[str] = []
    for block in _collect(bible, "restricted_only_values"):
        found.extend(str(value) for value in (block or {}).get("long", []))
    injection = bible.get("injection") or {}
    found.extend(str(value) for value in injection.get("forbidden_in_outputs", []))
    if not found:
        raise FidelitySpecError("the bible lists no forbidden strings")
    return list(dict.fromkeys(found))


# ----------------------------------------------------------------------------------- checks


def value_found(value: str, norm: str, values: Values) -> bool:
    """``value`` in a normalised text; a euro amount also matches its bare number (spreadsheet
    cells and table columns print ``15157,3`` under a ``(€)`` header)."""
    if contains_item(value, norm, values):
        return True
    bare = value.strip()
    if bare.endswith("€"):
        return contains_item(bare[:-1].strip(), norm, values)
    return False


def _best_section(pages: Iterable[Page], values: Sequence[str]) -> dict[str, Any]:
    """The section holding the most of ``values`` (all of them when the fact is found)."""
    best: dict[str, Any] = {"found": False, "page": None, "section": None, "missing": list(values)}
    for page in pages:
        for section in page.sections:
            missing = [
                value for value in values if not value_found(value, section.norm, section.values)
            ]
            if len(missing) < len(best["missing"]):
                best = {
                    "found": not missing,
                    "page": page.path,
                    "section": section.heading,
                    "missing": missing,
                }
                if not missing:
                    return best
    return best


def _in_scope(page: Page, scope: str) -> bool:
    if page.scope == scope:
        return True
    return scope == COMPANY_SCOPE and page.scope is None


def _check_revisions(pages: Sequence[Page], items: Sequence[Mapping[str, Any]]) -> list[dict]:
    sources = {str(page.data.get("source_path")): page for page in pages if page.type == "source"}
    path_of = {str(page.data.get("source_id")): path for path, page in sources.items()}
    results = []
    for item in items:
        page = sources.get(str(item["source_path"]))
        if page is None:
            results.append(
                {
                    "id": item["id"],
                    "scenario": item.get("scenario"),
                    "passed": False,
                    "problem": "no source page",
                }
            )
            continue
        status = page.data.get("status")
        successors = sorted(
            path_of.get(str(sid), str(sid)) for sid in page.data.get("superseded_by") or []
        )
        expected_successor = item.get("superseded_by")
        problems = []
        if status != item["status"]:
            problems.append(f"status {status!r}")
        if expected_successor and expected_successor not in successors:
            problems.append("superseding source not linked")
        if not expected_successor and successors:
            problems.append("unexpected superseded_by")
        results.append(
            {
                "id": item["id"],
                "scenario": item.get("scenario"),
                "passed": not problems,
                "page": page.path,
                "status": status,
                **({"problem": "; ".join(problems)} if problems else {}),
            }
        )
    return results


def _check_facts(pages: Sequence[Page], items: Sequence[Mapping[str, Any]]) -> list[dict]:
    results = []
    for item in items:
        values = [str(value) for value in item["values"]]
        scoped = [
            page
            for page in pages
            if page.type in SYNTHESIS_TYPES and _in_scope(page, str(item["scope"]))
        ]
        synthesised = _best_section(scoped, values)
        compiled = synthesised if synthesised["found"] else _best_section(pages, values)
        results.append(
            {
                "id": item["id"],
                "scenario": item.get("scenario"),
                "scope": item["scope"],
                "synthesised": synthesised["found"],
                "compiled": compiled["found"],
                "where": _where(synthesised if synthesised["found"] else compiled),
            }
        )
    return results


def _check_cross(pages: Sequence[Page], items: Sequence[Mapping[str, Any]]) -> list[dict]:
    synthesis = [page for page in pages if page.type in SYNTHESIS_TYPES]
    results = []
    for item in items:
        best = _best_section(synthesis, [str(value) for value in item["values"]])
        results.append(
            {
                "id": item["id"],
                "scenario": item.get("scenario"),
                "passed": best["found"],
                "where": _where(best),
            }
        )
    return results


def _where(best: Mapping[str, Any]) -> dict[str, Any]:
    where: dict[str, Any] = {"page": best["page"], "section": best["section"]}
    if not best["found"]:
        where["missing"] = best["missing"]
    return where


def _check_scope_absent(pages: Sequence[Page], items: Sequence[Mapping[str, Any]]) -> list[dict]:
    results = []
    for item in items:
        hits = sorted(
            {
                page.path
                for page in pages
                if page.scope == item["scope"]
                for term in item["terms"]
                if contains_item(str(term), page.stated_norm)
            }
        )
        results.append(
            {"id": item["id"], "scenario": item.get("scenario"), "passed": not hits, "pages": hits}
        )
    return results


def _scan_forbidden(release: Path, terms: Sequence[str]) -> dict[str, list[str]]:
    files = [release / "catalog.json"] if (release / "catalog.json").is_file() else []
    for folder in ("wiki", "evidence"):
        if (release / folder).is_dir():
            files.extend(sorted((release / folder).rglob("*.md")))
    found: dict[str, list[str]] = {}
    for file in files:
        norm = normalize_text(file.read_text(encoding="utf-8"))
        values = extract_values(norm)
        for term in terms:
            if contains_item(term, norm, values):
                found.setdefault(term, []).append(file.relative_to(release).as_posix())
    return found


def _ratio(passed: int, total: int) -> dict[str, Any]:
    return {"passed": passed, "total": total, "share": round(passed / total, 4) if total else None}


def build_report(
    release: Path, spec: Mapping[str, Sequence[Mapping[str, Any]]], forbidden: Sequence[str]
) -> dict[str, Any]:
    pages = load_pages(release)
    revisions = _check_revisions(pages, spec.get("revisions", []))
    facts = _check_facts(pages, spec.get("facts", []))
    cross = _check_cross(pages, spec.get("cross", []))
    absent = _check_scope_absent(pages, spec.get("scope_absent", []))
    leaks = _scan_forbidden(release, forbidden)
    stamp_pages = sorted(page.path for page in pages if STAMP_TERM in page.stated_norm)
    by_scope: dict[str, dict[str, Any]] = {}
    for scope in sorted({str(fact["scope"]) for fact in facts}):
        rows = [fact for fact in facts if fact["scope"] == scope]
        by_scope[scope] = _ratio(sum(row["synthesised"] for row in rows), len(rows))
    return {
        "aggregates": {
            "revisions": _ratio(sum(row["passed"] for row in revisions), len(revisions)),
            "facts_synthesised": _ratio(sum(row["synthesised"] for row in facts), len(facts)),
            "facts_compiled": _ratio(sum(row["compiled"] for row in facts), len(facts)),
            "facts_synthesised_by_scope": by_scope,
            "cross": _ratio(sum(row["passed"] for row in cross), len(cross)),
            "scope_absent": _ratio(sum(row["passed"] for row in absent), len(absent)),
            "forbidden_found": sum(len(paths) for paths in leaks.values()),
            "stamp_as_content": {"pages": len(stamp_pages), "of": len(pages)},
        },
        "revisions": revisions,
        "facts": facts,
        "cross": cross,
        "scope_absent": absent,
        "forbidden": {"checked": len(forbidden), "found": leaks},
        "stamp_as_content": stamp_pages,
    }


# -------------------------------------------------------------------------------------- CLI


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _release_id(release: Path) -> str:
    manifest = release / "manifest.json"
    if manifest.is_file():
        return str(json.loads(manifest.read_text(encoding="utf-8")).get("release_id") or "")
    return release.name


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--release", type=Path, required=True, help="release folder")
    parser.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    parser.add_argument("--bible", type=Path, default=DEFAULT_BIBLE)
    parser.add_argument("--out", type=Path, help="output JSON (default: standard output)")
    parser.add_argument("--date", help="date written in the output (default: today, UTC)")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    spec = load_spec(args.spec)
    bible = load_yaml_mapping(args.bible.read_text(encoding="utf-8"), where=str(args.bible))
    report = {
        "format": FIDELITY_FORMAT,
        "date": args.date or datetime.now(UTC).date().isoformat(),
        "release_id": _release_id(args.release),
        "spec": {"path": args.spec.as_posix(), "sha256": _sha256(args.spec)},
        "bible_sha256": _sha256(args.bible),
        **build_report(args.release, spec, forbidden_strings(bible)),
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8", newline="\n")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
