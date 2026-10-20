"""Generate ``docs/assets/architecture.svg``: how DocWiki works, at a glance.

The diagram is laid out in code so that it stays reviewable, deterministic and free of
third-party logos. Colours follow the stone-and-sage palette of the site overlay
(``site/quartz.config.ts`` and ``site/quartz/styles/custom.scss``). A rough text-width estimate
guards every label against overflowing its box, so an edit that does not fit fails loudly.

    uv run python scripts/docs/architecture_svg.py           # write docs/assets/architecture.svg
    uv run python scripts/docs/architecture_svg.py --check   # exit 1 when the file is stale
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "assets" / "architecture.svg"

WIDTH, HEIGHT = 1280, 690
SANS = "'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'Cascadia Mono', Consolas, 'DejaVu Sans Mono', Menlo, monospace"

# Stone and sage, as on the site.
BG = "#f7f6f2"
CARD = "#ffffff"
FRAME = "#e2e0d8"
BORDER = "#d6d3c8"
INK = "#22231f"
INK_SOFT = "#363732"
MUTED = "#6b6a62"
SAGE = "#3c6250"
SAGE_SOFT = "#e3eee5"
SAGE_LINE = "#9dbfa7"
BLUE_INK = "#33485c"
BLUE_SOFT = "#e5eaef"
BLUE_LINE = "#a7b6c4"
AMBER_INK = "#674c12"
AMBER_SOFT = "#f3ecda"
AMBER_LINE = "#b39a5e"
HIGHLIGHT = "#ecdf9c"

NARROW = set("iljtfr.,:;'!|()[]/ ·")
WIDE = set("mwMW@%")

TEXT = (SAGE_SOFT, SAGE_LINE, SAGE)
TABLE = (BLUE_SOFT, BLUE_LINE, BLUE_INK)
OCR = (AMBER_SOFT, AMBER_LINE, AMBER_INK)

STAGES = (
    ("discover", False),
    ("extract", True),
    ("classify", True),
    ("compile", True),
    ("entities", True),
    ("topics", True),
    ("links", False),
    ("indexes", False),
    ("agent kit", False),
    ("evidence", False),
    ("verify", False),
    ("site", False),
    ("publish", False),
)


class LayoutError(ValueError):
    """A label does not fit the box it belongs to."""


def text_width(text: str, size: float, *, bold: bool = False, mono: bool = False) -> float:
    """Generous estimate of the rendered width of ``text`` in a sans-serif or monospace font."""
    if mono:
        return len(text) * size * 0.62
    units = 0.0
    for char in text:
        if char in NARROW:
            units += 0.32
        elif char in WIDE:
            units += 0.88
        elif char.isupper() or char.isdigit():
            units += 0.66
        else:
            units += 0.55
    return units * size * (1.07 if bold else 1.0)


class Canvas:
    """Minimal SVG writer with overflow checks."""

    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self.items: list[str] = []

    def rect(
        self,
        x: float,
        y: float,
        w: float,
        h: float,
        *,
        fill: str,
        stroke: str | None = None,
        radius: float = 10,
        stroke_width: float = 1.2,
        dash: str | None = None,
    ) -> None:
        attrs = f'x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius:g}" fill="{fill}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="{stroke_width:g}"'
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        self.items.append(f"<rect {attrs}/>")

    def circle(self, cx: float, cy: float, r: float, *, fill: str) -> None:
        self.items.append(f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{fill}"/>')

    def path(
        self,
        d: str,
        *,
        stroke: str = MUTED,
        width: float = 1.6,
        dash: str | None = None,
        marker: str | None = "arrow",
    ) -> None:
        attrs = f'd="{d}" fill="none" stroke="{stroke}" stroke-width="{width:g}"'
        attrs += ' stroke-linecap="round" stroke-linejoin="round"'
        if dash:
            attrs += f' stroke-dasharray="{dash}"'
        if marker:
            attrs += f' marker-end="url(#{marker})"'
        self.items.append(f"<path {attrs}/>")

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float = 12.5,
        weight: int = 400,
        fill: str = INK_SOFT,
        anchor: str = "start",
        mono: bool = False,
        within: tuple[float, float] | None = None,
    ) -> None:
        if within is not None:
            width = text_width(value, size, bold=weight >= 600, mono=mono)
            start = {"start": x, "middle": x - width / 2, "end": x - width}[anchor]
            left, right = within
            if start < left - 0.5 or start + width > right + 0.5:
                raise LayoutError(
                    f"label {value!r} (~{width:.0f}px from x={start:.0f}) overflows "
                    f"[{left:g}, {right:g}]"
                )
        family = MONO if mono else SANS
        attrs = (
            f'x="{x:g}" y="{y:g}" font-family="{family}" font-size="{size:g}" '
            f'font-weight="{weight}" fill="{fill}"'
        )
        if anchor != "start":
            attrs += f' text-anchor="{anchor}"'
        self.items.append(f"<text {attrs}>{escape(value)}</text>")

    def render(self, *, title: str, description: str) -> str:
        head = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}" '
            f'width="{self.width}" height="{self.height}" role="img" '
            'aria-labelledby="title desc">'
        )
        markers = [
            f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
            f'markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="{colour}"/></marker>'
            for name, colour in (("arrow", MUTED), ("arrow-amber", AMBER_INK))
        ]
        body = [
            head,
            f'<title id="title">{escape(title)}</title>',
            f'<desc id="desc">{escape(description)}</desc>',
            "<defs>",
            *markers,
            "</defs>",
            *self.items,
            "</svg>",
        ]
        return "\n".join(body) + "\n"


def badge(canvas: Canvas, cx: float, cy: float, number: str) -> None:
    canvas.circle(cx, cy, 11, fill=SAGE)
    canvas.text(cx, cy + 4.5, number, size=12.5, weight=700, fill=CARD, anchor="middle")


def card(canvas: Canvas, x: float, y: float, w: float, h: float) -> tuple[float, float]:
    """Draw a white card; return its inner horizontal bounds (16 px padding)."""
    canvas.rect(x, y, w, h, fill=CARD, stroke=BORDER, radius=12)
    return x + 16, x + w - 16


def chip(
    canvas: Canvas,
    x: float,
    y: float,
    w: float,
    label: str,
    colours: tuple[str, str, str],
    *,
    h: float = 26,
    centred: bool = True,
) -> None:
    soft, line, ink = colours
    canvas.rect(x, y, w, h, fill=soft, stroke=line, radius=7, stroke_width=1)
    baseline = y + h / 2 + 4.5
    if centred:
        canvas.text(
            x + w / 2,
            baseline,
            label,
            weight=600,
            fill=ink,
            anchor="middle",
            within=(x + 4, x + w - 4),
        )
    else:
        canvas.text(x + 12, baseline, label, weight=600, fill=ink, within=(x + 8, x + w - 8))


def documents_column(canvas: Canvas) -> None:
    left, right = card(canvas, 40, 104, 210, 226)
    badge(canvas, 62, 128, "1")
    canvas.text(80, 133, "Documents", size=16, weight=700, fill=INK, within=(left, right))
    formats = [
        ("PDF", TEXT),
        ("Word", TEXT),
        ("Excel", TABLE),
        ("CSV", TABLE),
        ("PowerPoint", TEXT),
        ("E-mail", TEXT),
        ("Scans", OCR),
        ("Transcripts", TEXT),
    ]
    for index, (label, colours) in enumerate(formats):
        row, column = divmod(index, 2)
        chip(canvas, 56 + column * 92, 150 + row * 32, 86, label, colours)
    for x, label, (soft, line, _) in ((56, "text", TEXT), (108, "table", TABLE), (166, "OCR", OCR)):
        canvas.rect(x, 285, 10, 10, fill=soft, stroke=line, radius=2, stroke_width=1)
        canvas.text(x + 14, 294, label, size=11.5, fill=MUTED, within=(left, right))
    canvas.text(56, 318, "Blob raw/ or a local folder", size=12, fill=MUTED, within=(left, right))

    left, right = card(canvas, 40, 346, 210, 214)
    canvas.text(56, 374, "Wake-ups", size=15, weight=700, fill=INK, within=(left, right))
    wakeups = ("Event Grid on raw/ changes", "Librarian: ingest_start", "reconcile job every 6 h")
    for row, label in enumerate(wakeups):
        y = 400 + row * 22
        canvas.circle(60, y - 4, 2.5, fill=MUTED)
        canvas.text(70, y, label, size=12, within=(left, right))
    canvas.path("M145,458 V474")
    chip(canvas, 56, 480, 178, "storage queue ingest", TABLE)
    canvas.text(56, 528, "KEDA starts one execution;", size=12, fill=MUTED, within=(left, right))
    canvas.text(56, 546, "a blob lease keeps it single", size=12, fill=MUTED, within=(left, right))


def compile_column(canvas: Canvas) -> None:
    left, right = card(canvas, 290, 104, 300, 456)
    badge(canvas, 312, 128, "2")
    canvas.text(330, 133, "Compile", size=16, weight=700, fill=INK, within=(left, right))
    canvas.text(
        306,
        156,
        "Azure Container Apps Job · docwiki worker",
        size=12,
        fill=MUTED,
        within=(left, right),
    )
    for index, (name, uses_model) in enumerate(STAGES):
        column, row = divmod(index, 7)
        x, y = 306 + column * 140, 172 + row * 32
        canvas.rect(x, y, 128, 24, fill=BG, stroke=BORDER, radius=7, stroke_width=1)
        canvas.text(x + 10, y + 16.5, str(index + 1), size=11.5, weight=600, fill=MUTED)
        canvas.text(x + 30, y + 16.5, name, size=12.5, fill=INK, within=(x + 4, x + 108))
        if uses_model:
            canvas.circle(x + 116, y + 12, 4, fill=SAGE)
    canvas.circle(310, 408, 4, fill=SAGE)
    canvas.text(
        320,
        412,
        "model call: structured output, no tools",
        size=12,
        fill=MUTED,
        within=(left, right),
    )
    canvas.rect(306, 428, 268, 74, fill=SAGE_SOFT, stroke=SAGE_LINE, radius=8, stroke_width=1)
    canvas.text(318, 449, "Microsoft Foundry", size=13.5, weight=700, fill=SAGE, within=(318, 562))
    canvas.text(318, 468, "models fast and smart", size=12, fill=INK_SOFT, within=(318, 562))
    canvas.text(
        318,
        486,
        "Content Understanding (PDF, images)",
        size=12,
        fill=INK_SOFT,
        within=(318, 562),
    )
    canvas.text(306, 528, "15 quality gates; a failing blocking", size=12, within=(left, right))
    canvas.text(306, 546, "gate keeps the previous release", size=12, within=(left, right))


def release_column(canvas: Canvas) -> None:
    left, right = card(canvas, 630, 104, 290, 456)
    badge(canvas, 652, 128, "3")
    canvas.text(670, 133, "Immutable release", size=16, weight=700, fill=INK, within=(left, right))
    canvas.text(
        646, 156, "releases/<id>/ in Blob or a folder", size=12, fill=MUTED, within=(left, right)
    )
    rows = (
        "wiki/ · sources, entities, topics",
        "index, glossary, log, queries",
        "evidence/ · one sidecar per locator",
        "catalog.json · search.db · tables/",
        "AGENTS.md · llms.txt · skills",
        "manifest.json · hashes, gate results",
    )
    for row, label in enumerate(rows):
        y = 186 + row * 28
        canvas.rect(646, y - 11, 11, 14, fill=SAGE_SOFT, stroke=SAGE_LINE, radius=2, stroke_width=1)
        canvas.text(666, y, label, size=12.5, within=(left, right))
    chip(canvas, 646, 346, 258, "current.json · atomic pointer swap", TABLE, h=30, centred=False)

    canvas.rect(646, 392, 258, 150, fill=BG, stroke=BORDER, radius=8, stroke_width=1)
    canvas.text(
        660,
        414,
        "Every claim cites its evidence",
        size=12.5,
        weight=700,
        fill=INK,
        within=(656, 894),
    )
    canvas.text(660, 440, "[^c1] SOP rev B, ¶ 4", size=11.5, mono=True, within=(656, 842))
    chip(canvas, 660, 448, 132, "✓ quote verified", TEXT, h=22, centred=False)
    canvas.text(660, 494, "[^c2] Plan 2026, rows 2–4", size=11.5, mono=True, within=(656, 842))
    chip(canvas, 660, 502, 70, "table", TABLE, h=22, centred=False)
    # A miniature page with the cited line highlighted.
    canvas.rect(848, 426, 42, 56, fill=CARD, stroke=BORDER, radius=3, stroke_width=1)
    for row in range(6):
        cited = row == 3
        canvas.rect(
            854,
            436 + row * 7.5,
            30 if row % 3 == 0 else 26,
            4.5 if cited else 3.5,
            fill=HIGHLIGHT if cited else FRAME,
            radius=1.5,
        )
    canvas.path(
        "M800,436 C820,436 832,460 852,460", stroke=AMBER_LINE, width=1.2, dash="3 3", marker=None
    )
    canvas.text(869, 498, "¶ 4", size=11, fill=MUTED, anchor="middle", within=(846, 892))


def consumers_column(canvas: Canvas) -> None:
    left, right = card(canvas, 960, 104, 280, 128)
    canvas.text(976, 133, "Humans", size=16, weight=700, fill=INK, within=(left, right))
    humans = (
        "Quartz site: graph, search, backlinks",
        "Evidence microscope on every footnote",
        "Served by the portal Container App",
    )
    for row, label in enumerate(humans):
        canvas.text(976, 158 + row * 22, label, size=12.5, within=(left, right))

    left, right = card(canvas, 960, 248, 280, 184)
    canvas.text(976, 277, "Foundry agents", size=16, weight=700, fill=INK, within=(left, right))
    canvas.text(976, 301, "MCP server on Container Apps", size=12.5, within=(left, right))
    canvas.text(976, 322, "Built-in auth, roles checked per tool", size=12.5, within=(left, right))
    chip(canvas, 976, 336, 248, "Researcher · Wiki.Read", TEXT, h=28, centred=False)
    chip(canvas, 976, 372, 248, "Librarian · Read + Operate", OCR, h=28, centred=False)
    canvas.text(976, 422, "Each has its own Entra agent identity", size=12.5, within=(left, right))

    left, right = card(canvas, 960, 448, 280, 112)
    canvas.text(
        976, 477, "Local coding agents", size=16, weight=700, fill=INK, within=(left, right)
    )
    local = (
        "stdio MCP + Agent Skills, no Azure",
        "Copilot · Claude Code · Codex",
        "or plain Markdown file reads",
    )
    for row, label in enumerate(local):
        canvas.text(976, 501 + row * 22, label, size=12.5, within=(left, right))


def connectors(canvas: Canvas) -> None:
    canvas.path("M250,217 H286")
    canvas.path("M250,453 H286")
    canvas.path("M590,332 H626")
    canvas.path("M920,332 H940", marker=None)
    for target in (168, 340, 504):
        canvas.path(f"M940,332 V{target} H956")
    # Control plane: the Librarian enqueues work; a human approves every such call.
    canvas.path(
        "M1224,386 H1256 V604 H145 V564",
        stroke=AMBER_INK,
        width=1.4,
        dash="5 4",
        marker="arrow-amber",
    )
    canvas.text(
        700,
        626,
        "Librarian, with human approval: ingest_start · recompile → queue",
        size=12.5,
        fill=AMBER_INK,
        anchor="middle",
        within=(160, 1240),
    )


def build() -> str:
    canvas = Canvas(WIDTH, HEIGHT)
    canvas.rect(0.5, 0.5, WIDTH - 1, HEIGHT - 1, fill=BG, stroke=FRAME, radius=18)
    canvas.text(40, 50, "How DocWiki works", size=24, weight=700, fill=INK, within=(40, 1240))
    canvas.text(
        40,
        76,
        "Compile once, cite every claim, serve humans and agents from one validated release.",
        size=14,
        fill=MUTED,
        within=(40, 1240),
    )
    documents_column(canvas)
    compile_column(canvas)
    release_column(canvas)
    consumers_column(canvas)
    connectors(canvas)
    canvas.text(
        640,
        666,
        "Zero secrets: managed identities and per-agent Entra identities · "
        "documents are data, never instructions",
        size=12.5,
        fill=INK_SOFT,
        anchor="middle",
        within=(40, 1240),
    )
    return canvas.render(
        title="How DocWiki works",
        description=(
            "Documents (PDF, Word, Excel, CSV, PowerPoint, e-mail, scans, transcripts) land in "
            "Blob raw/. Event Grid, the Librarian agent or the reconcile schedule enqueue a "
            "wake-up; an Azure Container Apps Job runs 13 stages with Microsoft Foundry models "
            "and quality gates, then publishes an immutable release (wiki, evidence sidecars, "
            "catalog, search index, agent kit) behind an atomic pointer. Humans browse a Quartz "
            "site; Foundry agents use the MCP server with their own Entra identities; local "
            "coding agents use stdio MCP and Agent Skills."
        ),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate docs/assets/architecture.svg.")
    parser.add_argument("--check", action="store_true", help="fail if the SVG is out of date")
    args = parser.parse_args(argv)
    svg = build()
    target = OUTPUT.relative_to(ROOT).as_posix()
    if args.check:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.is_file() else ""
        if current != svg:
            print(f"{target} is stale: run scripts/docs/architecture_svg.py")
            return 1
        print(f"{target} is up to date")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(svg, encoding="utf-8", newline="\n")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
