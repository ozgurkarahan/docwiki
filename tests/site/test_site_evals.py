"""The home page's evaluation panel and the architecture page (site.md §12.1, §12.3)."""

from __future__ import annotations

import json
from pathlib import Path

from docwiki.contracts.frontmatter import read_frontmatter
from docwiki.site.build import ARCHITECTURE_STATIC, _publish_diagram
from docwiki.site.evals import (
    EVALS_FILE,
    PANEL_SYSTEMS,
    default_evals_file,
    eval_panel,
    read_eval_panel,
)
from docwiki.site.process_page import (
    ARCHITECTURE_SLUG,
    architecture_markdown,
    write_architecture_page,
)
from docwiki.site.security import REPO_URL

REPO_ROOT = Path(__file__).resolve().parents[2]


def _entry(accuracy: float, *, status: str = "ok", date: str = "2026-10-23") -> dict[str, object]:
    return {
        "status": status,
        "date": date,
        "questions": 32,
        "overall": {
            "answer_accuracy": {"value": accuracy, "n": 32, "passed": round(accuracy * 32)},
            "numeric_exactness": {"value": None, "n": 0, "passed": 0},
        },
        "cost": {"per_question_usd": 0.163555, "prices_verified": False},
        "latency": {"p50_s": 32.34, "p95_s": 71.0},
    }


def _latest(**systems: dict[str, object]) -> dict[str, object]:
    return {"format": "docwiki.evals.latest/v1", "splits": {"dev": systems}}


def test_the_repository_scoreboard_feeds_the_panel() -> None:
    assert default_evals_file() == REPO_ROOT / EVALS_FILE
    panel = read_eval_panel(REPO_ROOT / EVALS_FILE, REPO_URL)
    assert panel is not None
    assert [row["system"] for row in panel["systems"]] == list(PANEL_SYSTEMS)
    assert panel["split"] == "dev" and isinstance(panel["questions"], int)
    assert panel["scoreboardUrl"] == f"{REPO_URL}/blob/main/evals/SCOREBOARD.md"
    latest = json.loads((REPO_ROOT / EVALS_FILE).read_text(encoding="utf-8"))
    researcher = latest["splits"]["dev"]["docwiki-researcher"]
    row = panel["systems"][0]
    # The scoreboard's own numbers, never recomputed.
    assert row["accuracy"]["n"] == researcher["overall"]["answer_accuracy"]["n"]
    assert row["accuracy"]["passed"] == researcher["overall"]["answer_accuracy"]["passed"]
    assert row["costPerQuestion"] == round(researcher["cost"]["per_question_usd"], 4)
    assert row["latencyP50"] == round(researcher["latency"]["p50_s"], 1)


def test_panel_order_metrics_and_dates() -> None:
    panel = eval_panel(
        _latest(
            **{
                "baseline-rag": _entry(0.5625),
                "docwiki-local": _entry(0.9),
                "docwiki-researcher": _entry(0.75, date="2026-10-24"),
                "baseline-long-context": _entry(0.625, status="skipped"),
            }
        ),
        REPO_URL + "/",
    )
    assert panel is not None
    # The panel's three systems only, the wiki first; a skipped run is left out.
    assert [row["system"] for row in panel["systems"]] == ["docwiki-researcher", "baseline-rag"]
    ours = panel["systems"][0]
    assert ours["accuracy"] == {"value": 0.75, "n": 32, "passed": 24}
    assert ours["numeric"] is None  # n = 0: nothing to show
    assert ours["pricesVerified"] is False and ours["costPerQuestion"] == 0.1636
    assert panel["date"] == "2026-10-24" and panel["questions"] == 32
    assert panel["scoreboardUrl"].startswith(REPO_URL + "/blob/main/")


def test_no_panel_without_results(tmp_path: Path) -> None:
    assert read_eval_panel(None, REPO_URL) is None
    assert read_eval_panel(tmp_path / "missing.json", REPO_URL) is None
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert read_eval_panel(broken, REPO_URL) is None
    assert eval_panel({"format": "other", "splits": {}}, REPO_URL) is None
    # A comparison needs the wiki's own system.
    assert eval_panel(_latest(**{"baseline-rag": _entry(0.5)}), REPO_URL) is None


def test_architecture_page_in_both_languages(tmp_path: Path) -> None:
    for lang, heading in (("en", "## How it works"), ("fr", "## Comment ça marche")):
        text = architecture_markdown(lang)
        frontmatter, body = read_frontmatter(text)
        assert frontmatter == {"lang": lang, "title": "Architecture"}
        assert heading in body
        assert "azd up" in body and "14" in body
        # The MCP server is private; visitors use the drawer. No raw HTML in the page.
        assert ("private" if lang == "en" else "privé") in body
        assert "<" not in body
    assert architecture_markdown("de") == architecture_markdown("en").replace(
        "lang: en", "lang: de"
    )
    assert write_architecture_page(tmp_path, "fr")
    target = tmp_path / f"{ARCHITECTURE_SLUG}.md"
    assert target.read_text(encoding="utf-8") == architecture_markdown("fr")
    target.write_text("own page\n", encoding="utf-8")
    assert not write_architecture_page(tmp_path, "fr")  # a release's own page wins
    assert target.read_text(encoding="utf-8") == "own page\n"


def test_architecture_diagram_is_published(tmp_path: Path) -> None:
    quartz = tmp_path / "quartz"
    assert _publish_diagram(None, quartz) is None
    assert _publish_diagram(tmp_path / "missing.svg", quartz) is None
    diagram = REPO_ROOT / "docs" / "assets" / "architecture.svg"
    assert _publish_diagram(diagram, quartz) == ARCHITECTURE_STATIC
    assert (quartz / ARCHITECTURE_STATIC).read_bytes() == diagram.read_bytes()


def test_job_image_ships_the_panel_and_the_diagram() -> None:
    ignore = (REPO_ROOT / "docker" / "job.Dockerfile.dockerignore").read_text(encoding="utf-8")
    rules = {line.strip() for line in ignore.splitlines()}
    assert f"!{EVALS_FILE}" in rules and "!docs/assets/architecture.svg" in rules
    dockerfile = (REPO_ROOT / "docker" / "job.Dockerfile").read_text(encoding="utf-8")
    assert "/opt/docwiki/evals/results" in dockerfile
    assert "/opt/docwiki/docs/assets" in dockerfile
