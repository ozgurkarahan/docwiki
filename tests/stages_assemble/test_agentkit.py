"""Stage ``agentkit``: template-only skills, strict rendering, escaping and projections."""

from __future__ import annotations

from pathlib import Path

import pytest
from assemble_helpers import DAY, STAMP, entity_page, pack, source_page, topic_page

from docwiki.contracts.ids import source_id_for
from docwiki.contracts.layout import CORE_SKILLS, SKILL_PROJECTIONS
from docwiki.contracts.pages import SkillFile
from docwiki.contracts.safety import find_violations
from docwiki.domain.loader import load_pack
from docwiki.stages.agentkit import (
    AgentKitError,
    Safe,
    build_agent_kit,
    default_templates_dir,
    render_template,
    write_agent_kit,
)


def _pages():
    a = source_id_for("procedures/SOP-GBX-010 rev A.txt")
    return [
        source_page("procedures/SOP-GBX-010 rev A.txt", "Rev A", "# Rev A\n", slug="rev-a"),
        entity_page("asset:wtg-07", "WTG-07", "# WTG-07\n", sources=[a]),
        topic_page("gearbox-oil", "Gearbox oil", "# Gearbox oil\n", sources=[a]),
    ]


def _kit(**kwargs):
    return build_agent_kit(
        _pages(),
        kwargs.pop("domain", pack()),
        stamp=STAMP,
        updated=DAY,
        sensitivity="public",
        audience="public",
        **kwargs,
    )


def test_core_and_domain_skills_render_valid_files():
    kit = _kit()
    assert set(kit.skills) == {*CORE_SKILLS, "troubleshoot-alarm"}
    for name, text in kit.skills.items():
        skill = SkillFile.parse(text, name)
        assert skill.frontmatter.name == name
        assert find_violations(text, allow_markers=False) == []
    assert "stop after 12 tool calls" in kit.skills["troubleshoot-alarm"]
    agents = kit.agents
    assert agents.path == "AGENTS.md" and agents.frontmatter.id == "meta:agents"
    assert "[Gearbox oil](topics/gearbox-oil.md)" in agents.body
    assert "- `troubleshoot-alarm`:" in agents.body
    assert "1 topic synthesis" in agents.body and "1 entity page" in agents.body


@pytest.mark.parametrize("domain", ["wind-om", "it-runbooks"])
def test_shipped_domain_pack_skills_render(domain: str) -> None:
    # The shipped packs use the documented `paths.index` (docs/skills.md); a context without
    # it made the first Azure run fail in the agentkit stage (StrictUndefined).
    repo = Path(__file__).resolve().parents[2]
    shipped = load_pack(repo / "domains" / domain)
    kit = _kit(domain=shipped)
    skills_dir = repo / "domains" / domain / "skills"
    domain_skills = {path.name for path in skills_dir.iterdir() if path.is_dir()}
    assert domain_skills and domain_skills <= set(kit.skills)
    for name in domain_skills:
        text = kit.skills[name]
        assert SkillFile.parse(text, name).frontmatter.name == name
        assert "`index.md`" in text
        assert find_violations(text, allow_markers=False) == []


def test_projections_are_written_identically():
    kit = _kit()
    written: dict[str, str] = {}
    paths = write_agent_kit(kit, lambda path, text: written.__setitem__(path, text))
    assert len(paths) == len(kit.skills) * len(SKILL_PROJECTIONS)
    for name in kit.skills:
        copies = {written[f"{projection}/{name}/SKILL.md"] for projection in SKILL_PROJECTIONS}
        assert copies == {kit.skills[name]}


def test_strict_undefined_and_escaping():
    with pytest.raises(AgentKitError, match="undefined"):
        render_template("{{ missing }}", {}, name="x")
    with pytest.raises(AgentKitError, match="may only print"):
        render_template("{{ items }}", {"items": [1, 2]}, name="x")
    text = render_template(
        "[{{ title }}]({{ path }})",
        {"title": "a [b](http://example.com) <i>", "path": Safe("p.md")},
        name="x",
    )
    assert text == "[a \\[b\\](http://example.com) \\<i\\>](p.md)\n"
    with pytest.raises(AgentKitError):
        render_template("{{ ''.__class__.__mro__ }}", {}, name="x")


def test_unsafe_or_canary_output_is_rejected(tmp_path: Path):
    templates = tmp_path / "templates"
    for name in CORE_SKILLS:
        source = (default_templates_dir() / name / "SKILL.md.j2").read_text(encoding="utf-8")
        (templates / name).mkdir(parents=True)
        (templates / name / "SKILL.md.j2").write_text(source, encoding="utf-8", newline="\n")
    agents = (default_templates_dir() / "AGENTS.md.j2").read_text(encoding="utf-8")
    (templates / "AGENTS.md.j2").write_text(
        agents + "\n<script>alert(1)</script>\n", encoding="utf-8", newline="\n"
    )
    with pytest.raises(AgentKitError, match="unsafe Markdown"):
        _kit(templates_dir=templates)
    (templates / "AGENTS.md.j2").write_text(agents, encoding="utf-8", newline="\n")
    domain = pack()
    canary = domain.info.wiki_title.split()[0]
    with pytest.raises(AgentKitError, match="canary"):
        _kit(templates_dir=templates, canaries=[canary])


def test_invalid_skill_frontmatter_is_rejected():
    domain = pack()
    broken = domain.model_copy(
        update={
            "skill_templates": {"bad-skill": "---\nname: other-name\ndescription: x\n---\n\nBody\n"}
        }
    )
    with pytest.raises(AgentKitError, match=r"invalid SKILL\.md"):
        _kit(domain=broken)


def test_missing_core_template_is_an_error(tmp_path: Path):
    with pytest.raises(AgentKitError, match="core skill template missing"):
        _kit(templates_dir=tmp_path)
