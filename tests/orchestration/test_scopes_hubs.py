"""A company-wide wiki (v1.7, ADR 0011): hub pages, the company dashboard and per-scope topics.

The real compile lane runs behind stub extraction on a corpus with two chantiers (alpha, beta)
and the company's own documents; scope and phase come from the raw paths only.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from engine_stubs import CANARY, build_evidence, extract_source, write_scoped_corpus
from test_real_compile_lane import real_lane_llm

from docwiki.contracts.ids import source_id_for
from docwiki.orchestration.registry import load_engine
from docwiki.release.reader import ReleaseReader
from docwiki.release.validate import validate_release

pytest.importorskip("docwiki.stages.compile")

SCOPED_PACK = Path(__file__).resolve().parent / "fixtures" / "scoped-pack"
ALPHA_A = source_id_for("chantiers/alpha/1-marche/quote/DEV-2026-014 indice A.txt")
ALPHA_NOTE = source_id_for("chantiers/alpha/3-execution/note/2026-03-02 supplier note.txt")
BETA_B = source_id_for("chantiers/beta/1-marche/quote/DEV-2026-014 indice B.txt")
BETA_VISIT = source_id_for("chantiers/beta/note/site visit.txt")
WORKSHOP = source_id_for("entreprise/note/workshop note.txt")


@pytest.fixture
async def scoped_release(make_harness, tmp_path: Path):
    corpus = write_scoped_corpus(tmp_path / "scoped-input")
    engine = load_engine({"extract_source": extract_source, "build_evidence": build_evidence})
    harness = make_harness(
        engine=engine,
        llm=real_lane_llm(),
        pack=SCOPED_PACK,
        domain=str(SCOPED_PACK),
        input_dir=corpus,
    )
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    return harness, harness.current_release()


def _page(root: Path, path: str) -> str:
    return (root / "wiki" / path).read_text(encoding="utf-8")


async def test_the_scoped_release_validates(scoped_release):
    _, root = scoped_release
    problems = [
        f"{v.gate} {v.severity} {v.code} {v.path}:{v.line} {v.message}"
        for v in validate_release(root, canaries=[CANARY], glossary_seeded=True)
    ]
    assert problems == []


async def test_hubs_list_the_sources_of_their_scope(scoped_release):
    harness, root = scoped_release
    reader = ReleaseReader.open(harness.settings.work_dir)
    hubs = {page.id: page for page in reader.list_pages("hub")}
    assert set(hubs) == {"hub:chantiers/alpha", "hub:chantiers/beta", "hub:chantiers/entreprise"}
    assert hubs["hub:chantiers/alpha"].path == "chantiers/alpha.md"
    assert hubs["hub:chantiers/alpha"].sources == sorted([ALPHA_A, ALPHA_NOTE])
    assert hubs["hub:chantiers/beta"].sources == sorted([BETA_B, BETA_VISIT])
    assert hubs["hub:chantiers/entreprise"].sources == [WORKSHOP]
    assert hubs["hub:chantiers/alpha"].scope == "alpha"

    alpha = _page(root, "chantiers/alpha.md")
    assert "# Chantier Alpha" in alpha
    assert "| Client | Famille Moreau |" in alpha
    assert "| Contract type | marché privé |" in alpha
    sections = [line for line in alpha.split("\n") if line.startswith("#")]
    assert sections[1:] == [
        "## Details",
        "## Documents",
        "### Phase 1 marché",
        "### Phase 3 exécution",
        "## Topics",
        "## Entities",
        "## Open contradictions",
        "## Last document received",
    ]
    assert "](../topics/alpha/schedule-and-window-delivery.md)" in alpha
    assert "](../entities/organisation/vanarsdel-menuiseries.md)" in alpha
    documents = alpha.split("## Documents", 1)[1].split("## Topics", 1)[0]
    assert documents.count("](../sources/") == 2 and ": current" in documents
    # the last document received is the dated supplier note (date prefix of its file name)
    last = alpha.split("## Last document received", 1)[1]
    assert "(2026-03-02)" in last

    beta = _page(root, "chantiers/beta.md")
    assert "### No phase" in beta and "### Phase 1 marché" in beta
    entreprise = _page(root, "chantiers/entreprise.md")
    assert "# Entreprise" in entreprise
    assert "registry has no entry for Entreprise." in entreprise

    index = _page(root, "chantiers/index.md")
    assert "[Chantier Alpha](alpha.md)" in index and "[Entreprise](entreprise.md)" in index
    assert index.index("Chantier Alpha") < index.index("Chantier Beta") < index.index("Entreprise")


async def test_the_home_page_starts_with_the_company_dashboard(scoped_release):
    _, root = scoped_release
    home = _page(root, "index.md")
    body = home.split("\n---\n", 1)[1]
    first = next(line for line in body.split("\n") if line.startswith("## "))
    assert first == "## Chantiers"
    table = body.split("## Chantiers", 1)[1].split("## How to navigate", 1)[0]
    assert (
        "| Chantier | Phase | Client | Documents | Last document received | Open contradictions |"
    ) in table
    alpha = next(line for line in table.split("\n") if "[Chantier Alpha]" in line)
    assert alpha.startswith(
        "| [Chantier Alpha](chantiers/alpha.md) | 3 exécution | Famille Moreau |"
    )
    assert "| 2 |" in alpha and "(2026-03-02)" in alpha and alpha.endswith("| 0 |")
    beta = next(line for line in table.split("\n") if "[Chantier Beta]" in line)
    assert "| 1 marché | Zava Matériaux | 2 |" in beta
    entreprise = next(line for line in table.split("\n") if "[Entreprise]" in line)
    assert "| — | — | 1 |" in entreprise
    assert "[all chantiers](chantiers/index.md)" in table
    # the other sections are still there, in their order
    order = ["## How to navigate", "## Categories", "## Topics", "## Stats", "## Recent changes"]
    positions = [body.index(heading) for heading in order]
    assert positions == sorted(positions)


async def test_per_scope_topics_are_written_once_per_scope(scoped_release):
    harness, root = scoped_release
    reader = ReleaseReader.open(harness.settings.work_dir)
    topics = {page.id: page for page in reader.list_pages("topic")}
    assert set(topics) == {
        "topic:alpha/schedule-and-window-delivery",
        "topic:beta/schedule-and-window-delivery",
    }
    alpha = topics["topic:alpha/schedule-and-window-delivery"]
    assert alpha.path == "topics/alpha/schedule-and-window-delivery.md"
    assert alpha.title == "Schedule and window delivery — Chantier Alpha"
    assert alpha.scope == "alpha"
    assert alpha.sources == sorted([ALPHA_A, ALPHA_NOTE])
    assert topics["topic:beta/schedule-and-window-delivery"].sources == sorted([BETA_B, BETA_VISIT])
    page = reader.read_page("topic:alpha/schedule-and-window-delivery")
    assert page.frontmatter.scope == "alpha"
    assert "](../../sources/" in page.body and "](../../evidence/" in page.body
    assert (
        "topic:alpha/schedule-and-window-delivery" in reader.read_page(ALPHA_A).frontmatter.topics
    )
    index = _page(root, "topics/index.md")
    assert "## Chantier Alpha" in index and "## Chantier Beta" in index
    assert "](alpha/schedule-and-window-delivery.md)" in index
    # one synthesis per (topic, scope)
    calls = [
        request for request in harness.llm.requests if request.metadata.get("stage") == "topics"
    ]
    assert sorted(request.metadata.get("scope") for request in calls) == ["alpha", "beta"]


async def test_the_same_number_in_two_scopes_never_supersedes(scoped_release):
    harness, _ = scoped_release
    reader = ReleaseReader.open(harness.settings.work_dir)
    for source_id in (ALPHA_A, BETA_B):
        fm = reader.read_page(source_id).frontmatter
        assert fm.status == "current"
        assert fm.supersedes == [] and fm.superseded_by == []
    assert reader.read_page(ALPHA_A).frontmatter.scope == "alpha"
    assert reader.read_page(BETA_B).frontmatter.phase == "1"
