"""Export JSON Schemas of all v1 contracts to ``src/docwiki/contracts/schemas/``.

Usage: ``uv run python -m docwiki.contracts.export_schemas`` (``--check`` fails when stale).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, TypeAdapter

SCHEMA_DIR = Path(__file__).with_name("schemas")
META_SCHEMA = "https://json-schema.org/draft/2020-12/schema"


def _model(model: type[BaseModel]) -> Callable[[], dict[str, Any]]:
    return lambda: model.model_json_schema(by_alias=True, mode="validation")


def _adapter(annotation: Any) -> Callable[[], dict[str, Any]]:
    return lambda: TypeAdapter(annotation).json_schema(by_alias=True, mode="validation")


def _registry() -> dict[str, tuple[str, Callable[[], dict[str, Any]]]]:
    from docwiki.contracts.catalog import Catalog
    from docwiki.contracts.compiled import CompiledSource
    from docwiki.contracts.extracted import ExtractedDoc
    from docwiki.contracts.gates import GateResult, Violation
    from docwiki.contracts.locators import Locator
    from docwiki.contracts.manifest import CurrentPointer, ReleaseManifest
    from docwiki.contracts.pages import (
        EvidenceFrontmatter,
        EvidenceIndexFrontmatter,
        Frontmatter,
        SkillFrontmatter,
    )
    from docwiki.contracts.proposals import Proposal
    from docwiki.contracts.queue import QueueMessage
    from docwiki.contracts.runs import RunReport
    from docwiki.contracts.state import SourceState
    from docwiki.domain.models import (
        EntitiesFile,
        GlossaryFile,
        PackInfo,
        ResolutionFile,
        SensitivityFile,
        SupersessionFile,
        TaxonomyFile,
        TopicsFile,
    )
    from docwiki.domain.overlay import Overlay
    from docwiki.release.tables import SourceTablesIndex
    from docwiki.search.index import SearchHit

    return {
        "page-frontmatter": (
            "Wiki page frontmatter (discriminated on type)",
            _adapter(Frontmatter),
        ),
        "evidence-frontmatter": ("Evidence sidecar frontmatter", _model(EvidenceFrontmatter)),
        "evidence-index-frontmatter": (
            "Evidence index frontmatter",
            _model(EvidenceIndexFrontmatter),
        ),
        "skill-frontmatter": ("SKILL.md frontmatter", _model(SkillFrontmatter)),
        "catalog": ("catalog.json", _model(Catalog)),
        "locator": ("Locator (discriminated on kind)", _adapter(Locator)),
        "extracted-doc": ("ExtractedDoc", _model(ExtractedDoc)),
        "compiled-source": ("CompiledSource", _model(CompiledSource)),
        "compiled-source.strict": (
            "CompiledSource for strict structured outputs",
            CompiledSource.strict_schema,
        ),
        "queue-message": ("docwiki.ingest/v1 queue message", _model(QueueMessage)),
        "source-state": ("Per-source state shard", _model(SourceState)),
        "run-report": ("Run report and cost receipt", _model(RunReport)),
        "proposal": ("Proposal (discriminated on kind)", _adapter(Proposal)),
        "release-manifest": ("Release manifest.json", _model(ReleaseManifest)),
        "current-pointer": ("releases/current.json", _model(CurrentPointer)),
        "gate-result": ("Quality gate result", _model(GateResult)),
        "violation": ("Release validation violation", _model(Violation)),
        "tables-index": ("tables/<source_id>/index.json", _model(SourceTablesIndex)),
        "search-hit": ("Search hit returned by SearchIndex.search", _model(SearchHit)),
        "domain-pack": ("Domain pack pack.yaml", _model(PackInfo)),
        "domain-taxonomy": ("Domain pack taxonomy.yaml", _model(TaxonomyFile)),
        "domain-entities": ("Domain pack entities.yaml", _model(EntitiesFile)),
        "domain-topics": ("Domain pack topics.yaml", _model(TopicsFile)),
        "domain-glossary": ("Domain pack glossary.yaml", _model(GlossaryFile)),
        "domain-sensitivity": ("Domain pack sensitivity.yaml", _model(SensitivityFile)),
        "domain-supersession": ("Domain pack supersession.yaml", _model(SupersessionFile)),
        "domain-resolution": ("Domain pack resolution.yaml", _model(ResolutionFile)),
        "domain-overlay": ("Runtime overlay work/state/overlay.yaml", _model(Overlay)),
    }


def render_schemas() -> dict[str, str]:
    """File name → JSON text for every exported schema."""
    rendered: dict[str, str] = {}
    for name, (title, build) in _registry().items():
        schema = build()
        document = {
            "$schema": META_SCHEMA,
            "title": title,
            **{k: v for k, v in schema.items() if k != "title"},
        }
        rendered[f"{name}.schema.json"] = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    return rendered


def stale_files(directory: Path = SCHEMA_DIR) -> list[str]:
    """Names of schema files that are missing, outdated or unexpected."""
    expected = render_schemas()
    problems = [
        name
        for name, text in expected.items()
        if not (directory / name).is_file()
        or (directory / name).read_text(encoding="utf-8") != text
    ]
    if directory.is_dir():
        problems += sorted(p.name for p in directory.glob("*.json") if p.name not in expected)
    return sorted(problems)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="fail when the committed schemas are stale"
    )
    parser.add_argument("--out", type=Path, default=SCHEMA_DIR)
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_files(args.out)
        for name in stale:
            print(f"stale: {name}")
        return 1 if stale else 0
    args.out.mkdir(parents=True, exist_ok=True)
    expected = render_schemas()
    for stale in args.out.glob("*.json"):
        if stale.name not in expected:
            stale.unlink()
    for name, text in expected.items():
        (args.out / name).write_text(text, encoding="utf-8", newline="\n")
    print(f"wrote {len(expected)} schemas to {args.out.as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
