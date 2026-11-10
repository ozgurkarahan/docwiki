"""Compile fidelity on a hand-made release: no model, no Azure (evals/compile_fidelity.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from evals.compile_fidelity import (
    FIDELITY_FORMAT,
    FidelitySpecError,
    build_report,
    forbidden_strings,
    load_pages,
    load_spec,
    main,
)

BANNER = "> FICTIONAL SAMPLE - every name in this wiki is invented. Not for operational use."


def _page(root: Path, relative: str, frontmatter: str, body: str) -> None:
    path = root / "wiki" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\n{frontmatter}---\n\n{body}", encoding="utf-8", newline="\n")


@pytest.fixture
def release(tmp_path: Path) -> Path:
    root = tmp_path / "rel"
    _page(
        root,
        "sources/quote-a.md",
        "id: src-a\ntype: source\nsource_id: src-a\nsource_path: q/a.pdf\nstatus: superseded\n"
        "superseded_by:\n- src-b\nscope: moreau\nsummary: Quote A\n",
        f"# Quote A\n\n{BANNER}\n\n## Totals\n\nTotal 41 788,80 € TTC.\n",
    )
    _page(
        root,
        "sources/quote-b.md",
        "id: src-b\ntype: source\nsource_id: src-b\nsource_path: q/b.pdf\nstatus: current\n"
        "superseded_by: []\nscope: moreau\nsummary: Quote B\n",
        "# Quote B\n\n## Totals\n\nTotal 44 943,60 € TTC, bay 3,00 x 2,15 m.\n\n"
        "The page carries the mark « FICTIONAL - NOT FOR OPERATIONAL USE ».\n",
    )
    _page(
        root,
        "topics/moreau/marche.md",
        "id: topic:moreau/marche\ntype: topic\nscope: moreau\n",
        f"# Marché\n\n{BANNER}\n\n## Prix\n\n"
        "Le devis DEV-2026-014 indice B vaut 44 943,60 €.[^c1]\n\n"
        "## Planning\n\nLivraison reportée du 30/03/2026 au 20/04/2026.\n\n"
        "[^c1]: Devis indice A, 41 788,80 € TTC, Atelier Fabrikam.\n",
    )
    _page(
        root,
        "views/position.md",
        "id: view:position\ntype: view\n",
        "# Position\n\n## Totaux\n\n| Chantier | TTC (€) |\n|---|---|\n| Moreau | 47271,6 |\n"
        "| Nacrines | 202 939,00 |\n",
    )
    _page(root, "en/topics/moreau/marche.md", "id: x\ntype: topic\nscope: moreau\n", "41788,80 €")
    _page(root, ".agents/skills/a/SKILL.md", "name: a\n", "Atelier Fabrikam")
    evidence = root / "evidence" / "src-a" / "p0001.md"
    evidence.parent.mkdir(parents=True)
    evidence.write_text("Marge nette 3324,26 € HT.\n", encoding="utf-8", newline="\n")
    return root


SPEC = {
    "revisions": [
        {"id": "a", "source_path": "q/a.pdf", "status": "superseded", "superseded_by": "q/b.pdf"},
        {"id": "b", "source_path": "q/b.pdf", "status": "current"},
        {"id": "c", "source_path": "q/b.pdf", "status": "superseded"},
        {"id": "d", "source_path": "q/missing.pdf", "status": "current"},
    ],
    "facts": [
        {"id": "current", "scope": "moreau", "values": ["DEV-2026-014", "44943,60 €"]},
        {"id": "delivery", "scope": "moreau", "values": ["2026-03-30", "2026-04-20"]},
        {"id": "only-in-source", "scope": "moreau", "values": ["3,00 x 2,15 m"]},
        {"id": "only-in-footnote", "scope": "moreau", "values": ["41788,80 €", "DEV-2026-014"]},
        {"id": "company", "scope": "entreprise", "values": ["202939,00 €"]},
        {"id": "lost", "scope": "moreau", "values": ["2247,18 €"]},
    ],
    "cross": [
        {"id": "both", "values": ["47271,60 €", "202939,00 €"]},
        {"id": "split", "values": ["44943,60 €", "202939,00 €"]},
    ],
    "scope_absent": [{"id": "architect", "scope": "moreau", "terms": ["Atelier Fabrikam"]}],
}


def _by_id(rows: list[dict]) -> dict[str, dict]:
    return {row["id"]: row for row in rows}


def test_pages_skip_the_mirror_and_the_agent_kit(release: Path) -> None:
    paths = {page.path for page in load_pages(release)}
    assert "wiki/topics/moreau/marche.md" in paths
    assert not any(path.startswith(("wiki/en/", "wiki/.agents/")) for path in paths)


def test_report_measures_revisions_facts_cross_and_safety(release: Path) -> None:
    report = build_report(release, SPEC, ["3324,26", "CANARY-0000"])
    revisions = _by_id(report["revisions"])
    assert revisions["a"]["passed"] and revisions["b"]["passed"]
    assert revisions["c"]["problem"] == "status 'current'"
    assert revisions["d"]["problem"] == "no source page"

    facts = _by_id(report["facts"])
    assert facts["current"]["synthesised"] and facts["delivery"]["synthesised"]
    assert not facts["only-in-source"]["synthesised"]
    assert facts["only-in-source"]["compiled"]
    assert facts["only-in-source"]["where"]["page"] == "wiki/sources/quote-b.md"
    assert not facts["only-in-footnote"]["synthesised"]
    assert facts["company"]["synthesised"], "scope entreprise takes pages without a scope"
    assert facts["lost"]["where"]["missing"] == ["2247,18 €"]
    assert not facts["lost"]["compiled"]

    cross = _by_id(report["cross"])
    assert cross["both"]["passed"], "a bare number under a (€) header counts"
    assert not cross["split"]["passed"]

    assert report["scope_absent"][0]["passed"], "footnotes and the agent kit are not read"
    assert report["forbidden"]["found"] == {"3324,26": ["evidence/src-a/p0001.md"]}
    assert report["stamp_as_content"] == ["wiki/sources/quote-b.md"]

    aggregates = report["aggregates"]
    assert aggregates["revisions"] == {"passed": 2, "total": 4, "share": 0.5}
    assert aggregates["facts_synthesised"]["passed"] == 3
    assert aggregates["facts_compiled"]["passed"] == 4
    assert aggregates["forbidden_found"] == 1
    assert aggregates["stamp_as_content"] == {"pages": 1, "of": 4}


def test_spec_errors_surface(tmp_path: Path) -> None:
    spec = tmp_path / "spec.yaml"
    spec.write_text("schema: 1\nfacts:\n  - {id: x, scope: moreau}\n", encoding="utf-8")
    with pytest.raises(FidelitySpecError, match="lacks values"):
        load_spec(spec)
    spec.write_text(
        "schema: 1\ncross:\n  - {id: x, values: [a]}\n  - {id: x, values: [b]}\n", encoding="utf-8"
    )
    with pytest.raises(FidelitySpecError, match="duplicate id"):
        load_spec(spec)


def test_forbidden_strings_come_from_the_bible() -> None:
    bible = {
        "facts": {"study": {"restricted_only_values": {"long": ["30820,30"], "short": ["8,8 %"]}}},
        "injection": {"forbidden_in_outputs": ["CANARY-1", "VIR-1"]},
    }
    assert forbidden_strings(bible) == ["30820,30", "CANARY-1", "VIR-1"]
    with pytest.raises(FidelitySpecError):
        forbidden_strings({})


def test_cli_writes_a_report(release: Path, tmp_path: Path, repo_root: Path) -> None:
    out = tmp_path / "out.json"
    code = main(
        [
            "--release",
            str(release),
            "--spec",
            str(repo_root / "evals/golden/compile-fidelity.yaml"),
            "--bible",
            str(repo_root / "samples/fiction/bible.yaml"),
            "--out",
            str(out),
            "--date",
            "2026-11-09",
        ]
    )
    report = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0
    assert report["format"] == FIDELITY_FORMAT
    assert report["date"] == "2026-11-09"
    assert report["release_id"] == "rel"
    assert report["aggregates"]["forbidden_found"] == 1
