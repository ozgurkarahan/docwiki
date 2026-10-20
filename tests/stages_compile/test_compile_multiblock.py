"""Quotes that run across blocks: footnotes and evidence sidecars show where the quote is."""

from __future__ import annotations

from pathlib import Path

from compile_testkit import (
    FIXED_NOW,
    amendment_doc,
    compile_handler,
    compiled,
    fact,
    make_state,
    no_repair,
    section,
)

from docwiki.contracts.markdown import extract_footnotes, markdown_to_text
from docwiki.contracts.pages import EvidencePage
from docwiki.contracts.runs import VersionInfo
from docwiki.domain import DomainPack
from docwiki.evidence import build_evidence
from docwiki.llm import FakeLlmClient
from docwiki.release import ReleaseWriter, validate_release
from docwiki.stages.classify import classify_source
from docwiki.stages.compile import compile_source
from docwiki.stages.render import render_source_page

TITLE = "Amendment n°1"


def amendment_output() -> dict:
    return compiled(
        TITLE,
        "Fictional amendment for the roof window.",
        [
            fact(
                "The amendment amounts to 2328,00 € TTC.",
                "b0001,b0002",
                "Le montant de l'avenant n°1 est de 2328,00 € TTC",
                ["2328,00 €"],
            ),
            fact(
                "The roof opening is checked before the amendment amount is stated.",
                "b0001,b0002",
                "contrôler l'ouverture de la toiture. Le montant de l'avenant",
            ),
        ],
        [section("Start of works", "Check the roof opening, then read the amount.[[cite:b1,b2]]")],
    )


async def test_multi_block_quotes_point_to_evidence_holding_them(
    tmp_path: Path, pack: DomainPack
) -> None:
    doc = amendment_doc()
    sid = doc.source_id
    llm = FakeLlmClient(
        {"compile": compile_handler({sid: amendment_output}), "compile_repair": no_repair}
    )
    classification = await classify_source(doc, pack, llm)
    result = await compile_source(doc, classification, pack, llm)
    by_ref = {citation.ref: citation for citation in result.citations}
    assert by_ref["kf1"].block_ids == ("b0002",)
    assert by_ref["kf2"].block_ids == ("b0001", "b0002")
    assert [c.block_id for f in result.compiled.key_facts for c in f.citations] == [
        "b0002",
        "b0001,b0002",
    ]

    writer = ReleaseWriter(
        tmp_path / "release",
        created_at=FIXED_NOW,
        audience="internal",
        versions=VersionInfo(
            docwiki="0.1.0", domain_pack=pack.name, domain_pack_hash=pack.content_hash()
        ),
    )
    page, cited = render_source_page(
        result,
        doc,
        classification,
        make_state(doc),
        slug="avenant-n1",
        stamp=writer.stamp,
        pack=pack,
    )
    facts = page.body.split("## Key facts\n\n", 1)[1].split("\n\n", 1)[0].splitlines()
    assert facts == [
        "- The amendment amounts to 2328,00 € TTC.[^c1]",
        "- The roof opening is checked before the amendment amount is stated.[^c2]",
    ]
    _, definitions = extract_footnotes(page.body)
    assert [d.content for d in definitions] == [
        f"[{TITLE} — ¶ 2](../evidence/{sid}/para-0002.md) · ✓ quote verified",
        f"[{TITLE} — ¶ 1](../evidence/{sid}/para-0001.md) · ✓ quote verified",
        f"[{TITLE} — ¶ 1](../evidence/{sid}/para-0001.md) · paraphrase",
    ]

    raw = tmp_path / "avenant-n1.docx"
    raw.write_bytes(b"placeholder: the evidence of a paragraph never reads the original")
    writer.write_page(page)
    written = build_evidence(
        doc=doc,
        raw_file=raw,
        cited=cited,
        source_title=page.frontmatter.title,
        source_page_path=page.path,
        sensitivity="internal",
        publish_original=False,
        writer=writer,
    )
    assert sorted(path.rsplit("/", 1)[1] for path in written) == [
        "index.md",
        "para-0001.md",
        "para-0002.md",
    ]

    def sidecar(key: str) -> str:
        rel = f"evidence/{sid}/{key}.md"
        text = (writer.root / rel).read_text(encoding="utf-8")
        return markdown_to_text(EvidencePage.parse(text, rel).body)

    second = sidecar("para-0002")
    assert "Le montant de l'avenant n°1 est de 2328,00 € TTC." in second
    assert "toiture" not in second
    first = sidecar("para-0001")
    assert "¶ 1" in first and "Avant la pose, contrôler l'ouverture de la toiture." in first
    assert "¶ 2" in first and "Le montant de l'avenant n°1 est de 2328,00 € TTC." in first

    violations = validate_release(writer.root, require_manifest=False, audience="internal")
    relevant = [
        violation
        for violation in violations
        if violation.gate in {"G01", "G02", "G03", "G05", "G06", "G09"}
        and (
            violation.path == f"wiki/{page.path}" or (violation.path or "").startswith("evidence/")
        )
    ]
    assert relevant == []
