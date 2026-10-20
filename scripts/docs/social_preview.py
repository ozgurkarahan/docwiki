"""Generate ``docs/assets/social-preview.png`` (1280 x 640), the repository's social preview.

Project name, tagline, a stylised mini knowledge graph and the "cited to the page" motif: a
claim whose footnote points at the highlighted paragraph of its source page. No third-party
logos; the icon is DocWiki's own (``site/quartz/static/docwiki/icon.svg``). Colours follow the
stone-and-sage palette of the site overlay. Text uses the DejaVu fonts bundled with matplotlib
(the ``gen`` extra), so the output does not depend on the fonts installed on the machine.

    uv run --extra gen python scripts/docs/social_preview.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "docs" / "assets" / "social-preview.png"

WIDTH, HEIGHT = 1280, 640
SCALE = 2  # draw at 2x, then downsample for smooth edges

BG = "#f7f6f2"
SURFACE = "#efede6"
CARD = "#ffffff"
FRAME = "#e2e0d8"
BORDER = "#d6d3c8"
EDGE = "#c9c5b9"
INK = "#22231f"
INK_SOFT = "#363732"
MUTED = "#6b6a62"
SAGE = "#3c6250"
ICON = "#3f6150"
PAPER = "#f4f2ec"
FOLD = "#b9c8bd"
SAGE_SOFT = "#e3eee5"
SAGE_LINE = "#9dbfa7"
BLUE_SOFT = "#e5eaef"
BLUE_LINE = "#a7b6c4"
AMBER_INK = "#674c12"
AMBER_LINE = "#b39a5e"
HIGHLIGHT = "#ecdf9c"

TAGLINE = (
    "Turn messy documents into a wiki",
    "humans can browse and agents",
    "can trust — ",
)
TAGLINE_ACCENT = "cited to the page."
FEATURES = (
    "Markdown wiki",
    "Evidence sidecars",
    "MCP server",
    "Agent Skills",
    "Foundry agents",
    "Azure Container Apps",
)
REPOSITORY = "github.com/ozgurkarahan/docwiki"
LEFT, LEFT_LIMIT = 80, 712


def s(value: float) -> int:
    """Scale a layout coordinate to the drawing resolution."""
    return round(value * SCALE)


def box(x0: float, y0: float, x1: float, y1: float) -> tuple[int, int, int, int]:
    return s(x0), s(y0), s(x1), s(y1)


class Fonts:
    """DejaVu Sans faces from matplotlib's data folder, cached per size."""

    def __init__(self) -> None:
        try:
            import matplotlib
        except ImportError as exc:  # pragma: no cover - environment guard
            raise SystemExit(
                "matplotlib is needed for its DejaVu fonts: "
                "uv run --extra gen python scripts/docs/social_preview.py"
            ) from exc
        self.folder = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
        self.cache: dict[tuple[str, float], ImageFont.FreeTypeFont] = {}

    def get(self, face: str, size: float) -> ImageFont.FreeTypeFont:
        key = (face, size)
        if key not in self.cache:
            name = {"regular": "DejaVuSans.ttf", "bold": "DejaVuSans-Bold.ttf"}.get(
                face, "DejaVuSansMono.ttf"
            )
            self.cache[key] = ImageFont.truetype(str(self.folder / name), s(size))
        return self.cache[key]


def width_of(font: ImageFont.FreeTypeFont, text: str) -> float:
    return font.getlength(text) / SCALE


def draw_icon(draw: ImageDraw.ImageDraw, x: float, y: float, size: float) -> None:
    """DocWiki's own icon (a page with two lines and a magnifier), drawn from its SVG."""
    k = size / 64

    def p(px: float, py: float) -> tuple[int, int]:
        return s(x + px * k), s(y + py * k)

    draw.rounded_rectangle((*p(0, 0), *p(64, 64)), radius=s(14 * k), fill=ICON)
    draw.rounded_rectangle((*p(16, 14), *p(46, 53)), radius=s(3 * k), fill=PAPER)
    draw.polygon([p(37, 13.5), p(46.5, 13.5), p(46.5, 23)], fill=ICON)
    draw.line([p(37, 14), p(37, 23), p(46, 23)], fill=FOLD, width=s(2 * k), joint="curve")
    for x0, x1, yy in ((22, 39, 30), (22, 34, 36)):
        draw.line([p(x0, yy), p(x1, yy)], fill=ICON, width=s(3 * k))
        for px in (x0, x1):
            cx, cy = p(px, yy)
            r = s(1.5 * k)
            draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=ICON)
    draw.ellipse((*p(33, 36), *p(47, 50)), outline=ICON, width=s(3 * k))
    draw.line([p(45, 48), p(50, 53)], fill=ICON, width=s(3.5 * k))


def draw_text(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str,
    *,
    anchor: str = "ls",
) -> float:
    """Draw ``text`` with its baseline at ``y``; return the x where it ends."""
    draw.text((s(x), s(y)), text, font=font, fill=fill, anchor=anchor)
    return x + width_of(font, text)


def draw_heading(draw: ImageDraw.ImageDraw, fonts: Fonts) -> None:
    draw_icon(draw, LEFT, 70, 84)
    draw_text(draw, LEFT + 108, 142, "DocWiki", fonts.get("bold", 76), INK)

    size = 40.0
    while size > 24:
        regular, bold = fonts.get("regular", size), fonts.get("bold", size)
        widths = [width_of(regular, line) for line in TAGLINE]
        widths[-1] += width_of(bold, TAGLINE_ACCENT)
        if LEFT + max(widths) <= LEFT_LIMIT:
            break
        size -= 1
    else:
        raise ValueError("the tagline does not fit the left column")
    baseline = 236.0
    for index, line in enumerate(TAGLINE):
        end = draw_text(draw, LEFT, baseline, line, regular, INK_SOFT)
        if index == len(TAGLINE) - 1:
            draw_text(draw, end, baseline, TAGLINE_ACCENT, bold, SAGE)
        baseline += size * 1.36


def draw_features(draw: ImageDraw.ImageDraw, fonts: Fonts) -> None:
    font = fonts.get("regular", 19)
    x, y, height, gap = float(LEFT), 432.0, 40.0, 10.0
    for label in FEATURES:
        width = width_of(font, label) + 32
        if x + width > LEFT_LIMIT:
            x, y = float(LEFT), y + height + gap
        draw.rounded_rectangle(
            box(x, y, x + width, y + height), radius=s(20), fill=CARD, outline=BORDER, width=s(1.5)
        )
        draw_text(draw, x + width / 2, y + height / 2, label, font, INK_SOFT, anchor="mm")
        x += width + gap
    if y + height > 540:
        raise ValueError("the feature pills overflow the left column")
    draw_text(draw, LEFT, 590, REPOSITORY, fonts.get("bold", 22), SAGE)


def dashed(
    draw: ImageDraw.ImageDraw,
    start: tuple[float, float],
    end: tuple[float, float],
    fill: str,
    *,
    width: float,
    dashes: int,
) -> None:
    """A straight dashed line made of ``dashes`` segments separated by equal gaps."""
    pieces = dashes * 2 - 1
    for index in range(0, pieces, 2):
        a, b = index / pieces, (index + 1) / pieces
        draw.line(
            [
                (s(start[0] + (end[0] - start[0]) * a), s(start[1] + (end[1] - start[1]) * a)),
                (s(start[0] + (end[0] - start[0]) * b), s(start[1] + (end[1] - start[1]) * b)),
            ],
            fill=fill,
            width=s(width),
        )


def page_icon(
    draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float, h: float, *, lines: int = 3
) -> None:
    x0, y0 = cx - w / 2, cy - h / 2
    draw.rounded_rectangle(
        box(x0, y0, x0 + w, y0 + h), radius=s(4), fill=CARD, outline=BORDER, width=s(2)
    )
    for row in range(lines):
        yy = y0 + h * 0.3 + row * h * 0.2
        draw.line(
            [(s(x0 + w * 0.2), s(yy)), (s(x0 + w * (0.8 if row % 2 == 0 else 0.62)), s(yy))],
            fill=FRAME,
            width=s(3),
        )


def draw_graph(draw: ImageDraw.ImageDraw) -> None:
    topic = (995.0, 205.0)
    sources = {"s1": (860.0, 128.0), "s2": (1125.0, 120.0), "s3": (858.0, 292.0)}
    sources["s4"] = (1130.0, 290.0)
    entities = {
        "e1": (992.0, 92.0),
        "e2": (1186.0, 205.0),
        "e3": (800.0, 208.0),
        "e4": (995.0, 320.0),
    }
    mentions = (
        ("s1", "e1"),
        ("s2", "e1"),
        ("s1", "e3"),
        ("s3", "e3"),
        ("s2", "e2"),
        ("s4", "e2"),
        ("s3", "e4"),
        ("s4", "e4"),
    )
    for key in sources:
        draw.line([(s(topic[0]), s(topic[1])), tuple(map(s, sources[key]))], fill=EDGE, width=s(3))
    for source, entity in mentions:
        draw.line(
            [tuple(map(s, sources[source])), tuple(map(s, entities[entity]))],
            fill=EDGE,
            width=s(2.5),
        )
    # "supersedes": the newer revision points at the older one.
    (sx, sy), (tx, ty) = sources["s2"], sources["s4"]
    dashed(draw, (sx, sy + 30), (tx, ty - 30), AMBER_LINE, width=3, dashes=5)
    for cx, cy in entities.values():
        draw.ellipse(
            box(cx - 14, cy - 14, cx + 14, cy + 14), fill=BLUE_SOFT, outline=BLUE_LINE, width=s(2)
        )
    for cx, cy in sources.values():
        page_icon(draw, cx, cy, 36, 46)
    tx, ty = topic
    draw.ellipse(box(tx - 34, ty - 34, tx + 34, ty + 34), fill=SAGE)
    draw.ellipse(box(tx - 22, ty - 22, tx + 22, ty + 22), outline=SAGE_SOFT, width=s(3))


def draw_citation(draw: ImageDraw.ImageDraw, fonts: Fonts) -> None:
    x0, y0, x1, y1 = 790.0, 372.0, 1192.0, 556.0
    draw.rounded_rectangle(box(x0, y0, x1, y1), radius=s(12), fill=CARD, outline=BORDER, width=s(2))
    title = fonts.get("bold", 21)
    body = fonts.get("regular", 18)
    small = fonts.get("mono", 15)
    badge = fonts.get("bold", 15)
    draw_text(draw, x0 + 22, y0 + 38, "Contract terms", title, INK)
    end = draw_text(draw, x0 + 22, y0 + 72, "The retention is 5 %.", body, INK_SOFT)
    draw_text(draw, end + 2, y0 + 64, "[1]", fonts.get("bold", 13), SAGE)
    draw.line(box(x0 + 22, y0 + 92, x0 + 270, y0 + 92), fill=FRAME, width=s(2))
    footnote = draw_text(draw, x0 + 22, y0 + 120, "[1] Works contract — ¶ 12", small, INK_SOFT)
    bx, by = x0 + 22, y0 + 136
    label = "✓ quote verified"
    bw = width_of(badge, label) + 24
    draw.rounded_rectangle(
        box(bx, by, bx + bw, by + 30), radius=s(8), fill=SAGE_SOFT, outline=SAGE_LINE, width=s(1.5)
    )
    draw_text(draw, bx + bw / 2, by + 15, label, badge, SAGE, anchor="mm")

    # The source page with the cited paragraph highlighted.
    px0, py0, px1, py1 = 1096.0, 392.0, 1170.0, 488.0
    draw.rounded_rectangle(
        box(px0, py0, px1, py1), radius=s(4), fill=PAPER, outline=BORDER, width=s(2)
    )
    for row in range(7):
        yy = py0 + 16 + row * 11
        cited = row == 4
        draw.rounded_rectangle(
            box(
                px0 + 10,
                yy - (3 if cited else 2),
                px1 - (10 if row % 3 else 18),
                yy + (3 if cited else 2),
            ),
            radius=s(2),
            fill=HIGHLIGHT if cited else FRAME,
        )
    draw_text(draw, (px0 + px1) / 2, py1 + 22, "¶ 12", fonts.get("regular", 15), MUTED, anchor="ms")
    # The footnote points at the exact paragraph it cites.
    start = (footnote + 10, y0 + 114)
    target = (px0 - 6, py0 + 16 + 4 * 11)
    dashed(draw, start, target, AMBER_INK, width=2, dashes=6)
    r = 3.5
    draw.ellipse(box(target[0] - r, target[1] - r, target[0] + r, target[1] + r), fill=AMBER_INK)


def build() -> Image.Image:
    fonts = Fonts()
    image = Image.new("RGB", (s(WIDTH), s(HEIGHT)), BG)
    draw = ImageDraw.Draw(image)
    draw.rectangle(box(0, 0, WIDTH, 8), fill=SAGE)
    draw.rounded_rectangle(
        box(760, 56, 1222, 584), radius=s(22), fill=SURFACE, outline=FRAME, width=s(2)
    )
    draw_heading(draw, fonts)
    draw_features(draw, fonts)
    draw_graph(draw)
    draw_citation(draw, fonts)
    return image.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate docs/assets/social-preview.png.")
    parser.add_argument("--out", type=Path, default=OUTPUT, help="output PNG file")
    args = parser.parse_args(argv)
    image = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    image.save(args.out, format="PNG", optimize=True)
    target = args.out.resolve()
    shown = target.relative_to(ROOT) if target.is_relative_to(ROOT) else target
    print(f"wrote {shown.as_posix()} ({WIDTH}x{HEIGHT})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
