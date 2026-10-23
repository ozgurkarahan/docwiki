"""A company-wide wiki (v1.7, ADR 0011): hub pages, the company dashboard and per-scope topics.

The real compile lane runs behind stub extraction on a corpus with two chantiers (alpha, beta)
and the company's own documents; scope and phase come from the raw paths only.
"""

from __future__ import annotations

import shutil
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
    # the title already shows its date, so the date is not repeated
    assert "[2026-03-02 supplier note]" in last and "(2026-03-02)" not in last

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
        "| Chantier | Phase | Open contradictions | Documents | Last document (dated) |"
    ) in table
    alpha = next(line for line in table.split("\n") if "[Chantier Alpha]" in line)
    assert alpha.startswith(
        "| [Chantier Alpha](chantiers/alpha.md) | 3 exécution "
        "| [0](chantiers/alpha.md#open-contradictions) | 2 |"
    )
    # the client is on the hub, not on the dashboard; the dated title shows its date once
    assert "Famille Moreau" not in table
    assert "2026-03-02" in alpha and "(2026-03-02)" not in alpha
    beta = next(line for line in table.split("\n") if "[Chantier Beta]" in line)
    assert "| 1 marché | [0](chantiers/beta.md#open-contradictions) | 2 |" in beta
    entreprise = next(line for line in table.split("\n") if "[Entreprise]" in line)
    assert "| — | [0](chantiers/entreprise.md#open-contradictions) | 1 |" in entreprise
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


SCOPED_LOTS = """
  - type: work-package
    key: lot-5-windows
    label: Lot 5 - Windows
    aliases:
      - {text: window delivery, lang: en}
    attributes: {lot: 5, chantier: alpha}
"""


async def test_an_entity_bound_to_one_scope_stays_in_it(make_harness, tmp_path: Path):
    """A work package of the alpha quote (``chantier: alpha``) whose alias every chantier's
    documents use: only alpha's documents mention it, on its page, the source pages and hubs."""
    pack_dir = tmp_path / "scoped-pack"
    shutil.copytree(SCOPED_PACK, pack_dir)
    entities = pack_dir / "entities.yaml"
    text = entities.read_text(encoding="utf-8").replace(
        "types:\n", "types:\n  - key: work-package\n    title: Work packages\n", 1
    )
    entities.write_text(text.rstrip("\n") + "\n" + SCOPED_LOTS, encoding="utf-8")
    corpus = write_scoped_corpus(tmp_path / "scoped-input")
    engine = load_engine({"extract_source": extract_source, "build_evidence": build_evidence})
    harness = make_harness(
        engine=engine, llm=real_lane_llm(), pack=pack_dir, domain=str(pack_dir), input_dir=corpus
    )
    outcome = await harness.run()
    assert outcome.status == "succeeded", outcome.errors
    root = harness.current_release()
    assert [
        f"{v.gate} {v.code} {v.path}: {v.message}"
        for v in validate_release(root, canaries=[CANARY], glossary_seeded=True)
    ] == []
    reader = ReleaseReader.open(harness.settings.work_dir)
    lot = reader.read_page("work-package:lot-5-windows")
    # the compiled mentions of the beta documents name it too (the alias is in their text)
    assert lot.frontmatter.sources == sorted([ALPHA_A, ALPHA_NOTE])
    assert "Chantier Beta" not in lot.body and "May 2026" not in lot.body
    for source_id in (BETA_B, BETA_VISIT, WORKSHOP):
        assert "work-package:lot-5-windows" not in reader.read_page(source_id).frontmatter.entities
    assert "work-package:lot-5-windows" in reader.read_page(ALPHA_A).frontmatter.entities
    # links: the beta pages and the company pages never link it; alpha's do
    beta_topic = _page(root, "topics/beta/schedule-and-window-delivery.md")
    alpha_topic = _page(root, "topics/alpha/schedule-and-window-delivery.md")
    assert "lot-5-windows.md" not in beta_topic and "lot-5-windows.md" in alpha_topic
    beta_hub = _page(root, "chantiers/beta.md")
    assert "lot-5-windows.md" not in beta_hub and "Lot 5" not in beta_hub
    assert "](../entities/work-package/lot-5-windows.md)" in _page(root, "chantiers/alpha.md")
    assert "lot-5-windows.md" not in _page(root, "chantiers/entreprise.md")
