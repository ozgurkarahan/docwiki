"""The overlay's pure accessibility helpers (docwiki-a11y.ts), run with Node when available."""

from __future__ import annotations

import json
import shutil
import subprocess
from functools import cache

import pytest
from site_testkit import OVERLAY

A11Y_MODULE = OVERLAY / "quartz" / "plugins" / "transformers" / "docwiki-a11y.ts"


@cache
def _node() -> tuple[str, ...] | None:
    """Node command able to import the ``.ts`` module (type stripping), or ``None``."""
    node = shutil.which("node")
    if node is None:
        return None
    probe = f"await import({json.dumps(A11Y_MODULE.as_uri())})"
    for flags in ((), ("--experimental-strip-types",)):
        command = (node, *flags, "--no-warnings", "--input-type=module")
        completed = subprocess.run(
            [*command, "-e", probe], capture_output=True, text=True, check=False
        )
        if completed.returncode == 0:
            return command
    return None


def run(expression: str) -> object:
    """Evaluate ``expression`` with the module as ``m`` and return its JSON value."""
    command = _node()
    if command is None:
        pytest.skip("Node 22.6+ (type stripping) is not available")
    program = (
        f"const m = await import({json.dumps(A11Y_MODULE.as_uri())});\n"
        f"console.log(JSON.stringify({expression}))"
    )
    completed = subprocess.run(
        [*command, "-e", program], capture_output=True, text=True, encoding="utf-8", check=False
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_foreign_language_tags() -> None:
    result = run(
        """[
          "fr", "FR", " fr-CA ", "de", "pt-BR", "en", "EN", "en-GB", "", "  ", "f", "french",
          "fr_FR", "fr-", null, 7, undefined,
        ].map(m.foreignLang)"""
    )
    assert result == [
        "fr", "fr", "fr-ca", "de", "pt-br", None, None, None, None, None, None, None,
        None, None, None, None, None,
    ]


def test_quoted_passages_are_split_out() -> None:
    result = run(
        """[
          'Minutes ("compte rendu de chantier") of site meeting n°3.',
          'The walls ("élévation des murs") at 70 %, then “Pose des menuiseries”.',
          "Le lot « Gros œuvre » est terminé.",
          'Sizes "12" and "mur" stay apart.',
          'An open " quote only.',
          'Nothing quoted here.',
          '"Livraison des menuiseries"',
          '""',
          '"' + "x".repeat(201) + '"',
        ].map((text) => m.splitQuoted(text).map((part) => part.quoted ? [part.text] : part.text))"""
    )
    assert result == [
        ['Minutes ("', ["compte rendu de chantier"], '") of site meeting n°3.'],
        [
            'The walls ("', ["élévation des murs"], '") at 70 %, then “',
            ["Pose des menuiseries"], "”.",
        ],
        ["Le lot « ", ["Gros œuvre"], " » est terminé."],
        ['Sizes "12" and "', ["mur"], '" stay apart.'],
        ['An open " quote only.'],
        ["Nothing quoted here."],
        ['"', ["Livraison des menuiseries"], '"'],
        ['""'],
        ['"' + "x" * 201 + '"'],
    ]


def test_split_quoted_keeps_every_character() -> None:
    texts = [
        'a "b" c "d" e',
        "« x »« y »",
        '"unclosed',
        'mixed “one” and "two" and « three »',
    ]
    result = run(
        f"{json.dumps(texts)}.map((text) => m.splitQuoted(text).map((p) => p.text).join(''))"
    )
    assert result == texts


def test_lone_element_index() -> None:
    result = run(
        """[
          [{type: "element", tagName: "a"}],
          [{type: "text", value: "\\n "}, {type: "element", tagName: "a"},
            {type: "text", value: " "}],
          [{type: "text", value: "Organisation: "}, {type: "element", tagName: "a"}],
          [{type: "element", tagName: "a"}, {type: "element", tagName: "a"}],
          [{type: "text", value: "  "}],
          [],
          [{type: "comment", value: "x"}, {type: "element", tagName: "a"}],
        ].map(m.loneElementIndex)"""
    )
    assert result == [0, 1, -1, -1, -1, -1, -1]


def test_focus_cycles_at_the_ends_only() -> None:
    result = run(
        """{
          forward: [0, 1, 2, 3, -1, 9].map((index) => m.cycleFocus(4, index, false)),
          backward: [0, 1, 2, 3, -1, 9].map((index) => m.cycleFocus(4, index, true)),
          one: [m.cycleFocus(1, 0, false), m.cycleFocus(1, 0, true)],
          none: [m.cycleFocus(0, 0, false), m.cycleFocus(0, -1, true)],
          target: m.SKIP_TARGET_ID,
        }"""
    )
    assert result == {
        "forward": [-1, -1, -1, 0, 0, 0],
        "backward": [3, -1, -1, -1, 3, 3],
        "one": [0, 0],
        "none": [-1, -1],
        "target": "docwiki-main",
    }


def test_data_tables_stack_as_cards_except_on_evidence() -> None:
    result = run(
        """{
          stacks: ["index", "hub", "view", "source", "topic", undefined, null, 3,
                   "evidence", "evidence-index"].map(m.stacksTables),
          labels: m.cellLabels(["Chantier", " Last  document\\n(dated) ", "", "Documents"], 5),
          none: m.cellLabels([], 2),
        }"""
    )
    assert result == {
        "stacks": [True, True, True, True, True, True, True, True, False, False],
        "labels": ["Chantier", "Last document (dated)", None, "Documents", None],
        "none": [None, None],
    }


def test_a_view_names_its_table_boxes_after_its_title() -> None:
    result = run(
        """[
          m.tableCaption("view", "Crew double bookings", "Rows", 0),
          m.tableCaption("view", " Crew double bookings ", "Totals", 1),
          m.tableCaption("view", "Crew double bookings", "", 1),
          m.tableCaption("hub", "Chantier Moreau", "Details", 0),
          m.tableCaption("view", "", "Rows", 0),
          m.tableCaption("view", undefined, "Rows", 0),
        ]"""
    )
    assert result == [
        "Crew double bookings",
        "Crew double bookings, totals",
        "Crew double bookings",
        None,
        None,
        None,
    ]
