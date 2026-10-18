"""Original diagrams drawn with matplotlib (vector SVG for PDFs, PNG for Office files).

Output is deterministic: fixed SVG hash salt, no creation dates and no software metadata.
"""

from __future__ import annotations

import io
import math
import re
from collections.abc import Iterable, Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import (
    Circle,
    FancyArrowPatch,
    FancyBboxPatch,
    Polygon,
    Rectangle,
    Wedge,
)

plt.rcParams.update(
    {
        "svg.hashsalt": "docwiki-sample-corpus",
        "svg.fonttype": "path",
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.unicode_minus": False,
        # Pure black text gets no explicit fill in matplotlib SVG output, and the fpdf2 SVG
        # importer then inherits the fill of the previous shape; a near-black colour avoids it.
        "text.color": "#111111",
        "axes.labelcolor": "#111111",
        "xtick.color": "#111111",
        "ytick.color": "#111111",
    }
)

_SVG_METADATA = {
    "Creator": None,
    "Date": None,
    "Format": None,
    "Type": None,
}
_METADATA_BLOCK = re.compile(rb"<metadata>.*?</metadata>\s*", re.DOTALL)


def to_svg(fig: Figure) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="svg", metadata=_SVG_METADATA)
    plt.close(fig)
    return _METADATA_BLOCK.sub(b"", buf.getvalue())


def to_png(fig: Figure, dpi: int = 150) -> bytes:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, metadata={"Software": None})
    plt.close(fig)
    return buf.getvalue()


def _balloon(ax: plt.Axes, number: int, at: tuple[float, float], to: tuple[float, float]) -> None:
    ax.plot([at[0], to[0]], [at[1], to[1]], color="0.25", lw=0.6)
    ax.add_patch(Circle(at, 2.1, fc="white", ec="black", lw=0.9, zorder=5))
    ax.text(at[0], at[1], str(number), ha="center", va="center", fontsize=7.5, zorder=6)


def _ticks(ax: plt.Axes, x: float, y0: float, y1: float, step: float, length: float) -> None:
    y = y0
    while y <= y1:
        ax.plot([x, x + length], [y, y], color="black", lw=0.5)
        y += step


def _bearing(ax: plt.Axes, x: float, y: float, size: float = 3.2) -> None:
    half = size / 2
    ax.add_patch(Rectangle((x - half, y - half), size, size, fill=False, lw=1.0))
    ax.plot([x - half, x + half], [y - half, y + half], color="black", lw=0.6)
    ax.plot([x - half, x + half], [y + half, y - half], color="black", lw=0.6)


def gearbox_exploded() -> Figure:
    """Exploded view of the three-stage gearbox with numbered balloons 1-16."""
    fig, ax = plt.subplots(figsize=(7.4, 4.6))
    ax.set_xlim(0, 104)
    ax.set_ylim(0, 64)
    ax.set_aspect("equal")
    ax.axis("off")
    for y, x0, x1 in ((22, 2, 52), (36, 44, 80), (48, 66, 102)):
        ax.plot([x0, x1], [y, y], ls=(0, (8, 2, 1, 2)), lw=0.6, color="0.45")
    # 1 housing cover, rotor side
    ax.add_patch(FancyBboxPatch((4, 9), 6, 26, boxstyle="round,pad=0.7", fill=False, lw=1.3))
    for y in (12, 17, 27, 32):
        ax.add_patch(Circle((7, y), 0.8, fill=False, lw=0.7))
    # 2 planet carrier with planet gears
    ax.add_patch(Rectangle((14, 10), 8, 24, fill=False, lw=1.3))
    for y in (14, 22, 30):
        ax.add_patch(Rectangle((15.5, y - 1.6), 5, 3.2, fc="0.85", ec="black", lw=0.7))
    # 3 ring gear
    ax.add_patch(Rectangle((26, 6), 3, 32, fill=False, lw=1.3))
    _ticks(ax, 29, 7, 37, 2, 0.9)
    # 4 sun pinion shaft
    ax.add_patch(Rectangle((33, 20.4), 15, 3.2, fill=False, lw=1.2))
    for x in (34, 35.5, 37, 38.5):
        ax.plot([x, x], [20.4, 23.6], color="black", lw=0.5)
    # 5 second-stage gear wheel
    ax.add_patch(Rectangle((47, 24), 3, 24, fill=False, lw=1.3))
    _ticks(ax, 50, 25, 47, 2, 0.9)
    # 6 intermediate pinion shaft, 7 IMS bearing set
    ax.add_patch(Rectangle((55, 34.4), 22, 3.2, fill=False, lw=1.2))
    _bearing(ax, 57.5, 36)
    _bearing(ax, 74.5, 36)
    # 8 output pinion shaft, 9 and 10 bearings, coupling flange
    ax.add_patch(Rectangle((70, 46.6), 26, 2.8, fill=False, lw=1.2))
    _bearing(ax, 73, 48, 3.0)
    _bearing(ax, 92, 48, 3.0)
    ax.add_patch(Rectangle((97, 44), 2.5, 8, fill=False, lw=1.2))
    # 11 oil cooler with fan motor, 12 thermostatic valve insert
    ax.add_patch(Rectangle((8, 46), 26, 12, fill=False, lw=1.2))
    for x in range(10, 33, 2):
        ax.plot([x, x], [47, 57], color="0.35", lw=0.5)
    ax.add_patch(Circle((40, 52), 4.2, fill=False, lw=1.2))
    ax.add_patch(Wedge((40, 52), 4.2, 20, 70, fc="0.8", ec="black", lw=0.5))
    ax.add_patch(Wedge((40, 52), 4.2, 200, 250, fc="0.8", ec="black", lw=0.5))
    ax.add_patch(Rectangle((47, 55), 5, 4, fill=False, lw=1.0))
    # 13 oil filter element, 14 breather, 15 sight glass, 16 sampling valve
    ax.add_patch(FancyBboxPatch((78, 6), 7, 13, boxstyle="round,pad=0.5", fill=False, lw=1.2))
    for y in (8, 10, 12, 14, 16):
        ax.plot([78.5, 84.5], [y, y], color="0.4", lw=0.4)
    ax.add_patch(Rectangle((62, 10), 4, 6, fill=False, lw=1.0))
    ax.add_patch(Circle((64, 18), 1.6, fill=False, lw=1.0))
    ax.add_patch(Circle((92, 26), 3, fill=False, lw=1.1))
    ax.plot([89.5, 94.5], [25.2, 25.2], color="black", lw=0.6)
    ax.plot([89.5, 94.5], [27.0, 27.0], color="black", lw=0.6)
    ax.add_patch(Rectangle((96, 10), 2.4, 5, fill=False, lw=1.0))
    ax.add_patch(Rectangle((95.5, 15), 3.4, 1.4, fc="0.7", ec="black", lw=0.6))
    balloons = [
        (1, (3, 40), (5.5, 33)),
        (2, (15, 39), (17, 33)),
        (3, (28, 42), (27.5, 37)),
        (4, (40, 15), (40, 20.4)),
        (5, (48, 53), (48.5, 47)),
        (6, (66, 30), (66, 34.4)),
        (7, (57.5, 28), (57.5, 34.4)),
        (8, (83, 42), (83, 46.6)),
        (9, (73, 56), (73, 49.5)),
        (10, (92, 56), (92, 49.5)),
        (11, (21, 62), (21, 58)),
        (12, (55, 61), (52, 58)),
        (13, (81.5, 24), (81.5, 19.5)),
        (14, (60, 22), (63, 17)),
        (15, (100, 32), (94, 27.5)),
        (16, (101, 7), (98, 11)),
    ]
    for number, at, to in balloons:
        _balloon(ax, number, at, to)
    ax.annotate(
        "",
        xy=(2, 3),
        xytext=(12, 3),
        arrowprops={"arrowstyle": "->", "lw": 0.8},
    )
    ax.text(13, 3, "rotor side", va="center", fontsize=7)
    ax.annotate(
        "",
        xy=(102, 60),
        xytext=(92, 60),
        arrowprops={"arrowstyle": "->", "lw": 0.8},
    )
    ax.text(91, 60, "generator side", va="center", ha="right", fontsize=7)
    return fig


def drivetrain_schematic() -> Figure:
    """Rotor-to-generator drivetrain blocks with shaft names."""
    fig, ax = plt.subplots(figsize=(9.6, 3.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 30)
    ax.axis("off")
    blocks = [
        (2, "Rotor hub\n(3 blades)"),
        (17, "Main bearing"),
        (32, "LSS"),
        (45, "Planetary\nstage"),
        (58, "IMS"),
        (71, "HSS"),
        (84, "Generator\n1,500 rpm"),
    ]
    for x, label in blocks:
        face = "#dce8f5" if label in ("LSS", "IMS", "HSS") else "#f2f2f2"
        ax.add_patch(
            FancyBboxPatch((x, 9), 11, 12, boxstyle="round,pad=0.4", fc=face, ec="#1f4e79", lw=1.2)
        )
        ax.text(x + 5.5, 15, label, ha="center", va="center", fontsize=9)
    for x, _ in blocks[:-1]:
        ax.add_patch(
            FancyArrowPatch((x + 11.6, 15), (x + 14.6, 15), arrowstyle="-|>", mutation_scale=10)
        )
    ax.add_patch(Rectangle((43.5, 5.5), 40.0, 19, fill=False, ls="--", ec="0.4", lw=0.9))
    ax.text(63.5, 26.5, "Gearbox 1:118.4", ha="center", fontsize=9, color="0.25")
    ax.text(37.5, 2.5, "12.7 rpm", ha="center", fontsize=8, color="0.3")
    ax.text(76.5, 2.5, "1,500 rpm", ha="center", fontsize=8, color="0.3")
    return fig


def oil_trend(samples: Sequence[dict[str, object]]) -> Figure:
    """Iron and PQ index trend of the WTG-07 gearbox oil with alert limits."""
    fig, ax = plt.subplots(figsize=(6.6, 2.9))
    labels = [str(s["date"]) for s in samples]
    xs = list(range(len(samples)))
    fe = [float(s["fe"]) for s in samples]  # type: ignore[arg-type]
    pq = [float(s["pq"]) for s in samples]  # type: ignore[arg-type]
    ax.plot(xs, fe, marker="o", color="#1f4e79", label="Fe (ppm)")
    ax.plot(xs, pq, marker="s", color="#b85c00", label="PQ index")
    ax.axhline(50, color="#1f4e79", ls="--", lw=0.8)
    ax.axhline(60, color="#b85c00", ls="--", lw=0.8)
    ax.text(len(xs) - 0.95, 51.5, "Fe alert 50", fontsize=7, color="#1f4e79")
    ax.text(len(xs) - 0.95, 61.5, "PQ alert 60", fontsize=7, color="#b85c00")
    ax.set_xticks(xs, labels, fontsize=7.5)
    ax.set_ylim(0, 125)
    ax.set_xlim(-0.3, len(xs) - 0.2)
    ax.grid(axis="y", color="0.85", lw=0.6)
    ax.legend(loc="upper left", fontsize=7.5, frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    return fig


def _blade_outline(length: float) -> list[tuple[float, float]]:
    upper: list[tuple[float, float]] = []
    lower: list[tuple[float, float]] = []
    steps = 60
    for i in range(steps + 1):
        r = length * i / steps
        if r < 2.5:
            chord = 2.4
        elif r < 12:
            chord = 2.4 + (4.1 - 2.4) * (r - 2.5) / 9.5
        else:
            chord = 4.1 - (4.1 - 0.9) * ((r - 12) / (length - 12)) ** 0.85
        upper.append((r, chord * 0.42))
        lower.append((r, -chord * 0.58))
    return upper + lower[::-1]


def blade_defects(title: str, length: float, defects: Iterable[dict[str, object]]) -> Figure:
    """Planform sketch of one blade with defect markers along the radius."""
    fig, ax = plt.subplots(figsize=(7.0, 2.3))
    ax.add_patch(Polygon(_blade_outline(length), closed=True, fc="#f4f4f4", ec="black", lw=1.0))
    ax.plot([0, length], [0, 0], ls=(0, (6, 2, 1, 2)), color="0.5", lw=0.5)
    for defect in defects:
        r0 = float(defect["r0"])  # type: ignore[arg-type]
        r1 = float(defect["r1"])  # type: ignore[arg-type]
        edge = str(defect["edge"])
        y = 1.15 if edge == "LE" else -1.75
        color = "#c00000" if int(defect["cat"]) >= 4 else "#d98200"  # type: ignore[call-overload]
        ax.add_patch(Rectangle((r0, y - 0.25), max(r1 - r0, 0.5), 0.5, fc=color, ec=color))
        ax.text((r0 + r1) / 2, y + (0.75 if edge == "LE" else -0.85), str(defect["label"]),
                ha="center", fontsize=7, color=color)
    for r in range(0, int(length) + 1, 10):
        ax.plot([r, r], [-3.2, -3.0], color="black", lw=0.6)
        ax.text(r, -3.75, f"{r} m", ha="center", fontsize=6.5)
    ax.text(0.2, 2.9, title, fontsize=8.5, weight="bold")
    ax.text(length - 0.5, 1.05, "LE", fontsize=7, ha="right", color="0.3")
    ax.text(length - 0.5, -1.4, "TE", fontsize=7, ha="right", color="0.3")
    ax.set_xlim(-1, length + 1)
    ax.set_ylim(-4.2, 3.5)
    ax.set_aspect("auto")
    ax.axis("off")
    return fig


def sight_glass() -> Figure:
    """Gearbox oil level sight glass with MIN and MAX marks (single-point lesson picture)."""
    fig, axes = plt.subplots(1, 2, figsize=(6.4, 3.2))
    for ax, level, verdict, color in (
        (axes[0], 0.56, "OK - between MIN and MAX", "#2e7d32"),
        (axes[1], 0.18, "NOT OK - below MIN", "#c00000"),
    ):
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_aspect("equal")
        ax.axis("off")
        ax.add_patch(Rectangle((0.12, 0.08), 0.76, 0.84, fc="#d9d9d9", ec="black", lw=1.2))
        glass = Circle((0.5, 0.5), 0.3, fc="white", ec="black", lw=1.5)
        ax.add_patch(glass)
        level_y = 0.2 + 0.6 * level
        fill = Rectangle((0.2, 0.2), 0.6, level_y - 0.2, fc="#c8a24a", ec="none")
        ax.add_patch(fill)
        fill.set_clip_path(glass)
        ax.plot([0.18, 0.82], [0.62, 0.62], color="black", lw=1.0)
        ax.plot([0.18, 0.82], [0.38, 0.38], color="black", lw=1.0)
        ax.text(0.86, 0.62, "MAX", va="center", fontsize=8)
        ax.text(0.86, 0.38, "MIN", va="center", fontsize=8)
        ax.plot([0.24, 0.76], [level_y, level_y], color="#7a5a10", lw=2.2)
        ax.text(0.5, -0.02, verdict, ha="center", va="top", fontsize=8.5, color=color,
                weight="bold")
    fig.tight_layout()
    return fig


def wtg07_trend(weeks: Sequence[str], velocity: Sequence[float], alarms: Sequence[int]) -> Figure:
    """Weekly HSS bearing vibration of WTG-07 with weekly count of A2101 warnings."""
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    xs = list(range(len(weeks)))
    ax.bar(xs, alarms, color="#f0b27a", label="A2101 warnings per week")
    ax.set_ylabel("A2101 per week", fontsize=8)
    ax.set_ylim(0, max(alarms) + 2)
    ax2 = ax.twinx()
    ax2.plot(xs, velocity, color="#1f4e79", marker="o", ms=2.5, label="Velocity RMS (mm/s)")
    ax2.axhline(3.5, color="#d98200", ls="--", lw=0.8)
    ax2.axhline(4.5, color="#c00000", ls="--", lw=0.8)
    ax2.set_ylabel("mm/s RMS", fontsize=8)
    ax2.set_ylim(0, 7)
    step = 4
    ax.set_xticks(xs[::step], [w[5:] for w in weeks[::step]], fontsize=7)
    ax.tick_params(axis="y", labelsize=7)
    ax2.tick_params(axis="y", labelsize=7)
    lines = ax.get_legend_handles_labels()
    lines2 = ax2.get_legend_handles_labels()
    ax.legend(lines[0] + lines2[0], lines[1] + lines2[1], loc="upper left", fontsize=7,
              frameon=False)
    fig.tight_layout()
    return fig


def site_layout(turbines: Sequence[dict[str, object]], stamp: str) -> Figure:
    """Site layout plan: turbines, roads, substation, woodland, village, north arrow, scale."""
    fig, ax = plt.subplots(figsize=(11.0, 7.6))
    ax.set_xlim(0, 4200)
    ax.set_ylim(1300, 4300)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_linewidth(1.4)
    # contour-like terrain lines
    for level in range(6):
        pts = []
        for i in range(0, 4201, 60):
            y = 2350 + level * 230 + 160 * math.sin(i / 640 + level) - 0.18 * i
            pts.append((i, y + 900))
        ax.plot([p[0] for p in pts], [p[1] for p in pts], color="#c9b99a", lw=0.6)
    # woodland with bat roost
    wood = [(2050, 3420), (2600, 3560), (3150, 3480), (3350, 3260), (3050, 3150), (2500, 3260)]
    ax.add_patch(Polygon(wood, closed=True, fc="#cfe3c4", ec="#4f7942", lw=1.0, hatch="..."))
    ax.text(2720, 3380, "Skelvane Wood\n(bat roost)", ha="center", fontsize=8, color="#2f5a24",
            bbox={"fc": "white", "ec": "none", "alpha": 0.85, "pad": 1.5})
    # village
    ax.add_patch(Rectangle((250, 1450), 700, 450, fc="#f3e6d3", ec="#a0522d", lw=0.8))
    for x, y in ((330, 1530), (470, 1600), (610, 1520), (760, 1640), (420, 1760), (820, 1780)):
        ax.add_patch(Rectangle((x, y), 60, 45, fc="#a0522d", ec="none"))
    ax.text(600, 1950, "Quellmoor village\n(nearest dwellings)", ha="center", fontsize=8)
    # roads
    ids = [str(t["id"]) for t in turbines]
    pos = {str(t["id"]): (float(t["easting_m"]), float(t["northing_m"])) for t in turbines}  # type: ignore[arg-type]
    north = ids[:6]
    south = ids[6:]
    for row in (north, south):
        ax.plot([pos[i][0] for i in row], [pos[i][1] for i in row], color="#7f7f7f", lw=2.2)
    ax.plot([pos["WTG-01"][0], pos["WTG-07"][0]], [pos["WTG-01"][1], pos["WTG-07"][1]],
            color="#7f7f7f", lw=2.2)
    ax.plot([300, 1000, pos["WTG-07"][0]], [2050, 2450, pos["WTG-07"][1]], color="#7f7f7f",
            lw=2.6)
    ax.text(560, 2290, "site access road", rotation=30, fontsize=7.5, color="0.3")
    # substation and O&M building
    ax.add_patch(Rectangle((900, 2380), 160, 120, fc="#ffd966", ec="black", lw=1.0))
    ax.text(980, 2330, "Substation 33/132 kV", ha="center", fontsize=7.5)
    ax.add_patch(Rectangle((1100, 2420), 120, 90, fc="#bdd7ee", ec="black", lw=1.0))
    ax.text(1160, 2540, "O&M building", ha="center", fontsize=7.5)
    ax.plot([980, 980], [2380, 1500], color="#c00000", lw=1.2, ls="--")
    ax.text(1000, 1600, "132 kV line to Skelvane\nsubstation (City Power & Light)", fontsize=7,
            color="#c00000")
    # met mast
    ax.plot([1180], [3720], marker="^", ms=9, color="black")
    ax.text(1240, 3720, "MM-01 met mast", va="center", fontsize=7.5)
    # turbines
    for turbine in ids:
        x, y = pos[turbine]
        ax.add_patch(Circle((x, y), 34, fc="white", ec="#1f4e79", lw=1.6, zorder=4))
        ax.plot([x, x], [y, y + 70], color="#1f4e79", lw=1.0, zorder=4)
        ax.text(x + 50, y + 55, turbine, fontsize=8.5, weight="bold", zorder=5)
    # curtailment group
    ax.text(3700, 3180, "WTG-03 to WTG-05:\nenvironmental permit\ncurtailment group", fontsize=7,
            ha="center", color="#2f5a24")
    # north arrow and scale bar
    ax.add_patch(FancyArrowPatch((3950, 3850), (3950, 4180), arrowstyle="-|>", mutation_scale=18))
    ax.text(3950, 4210, "N", ha="center", fontsize=11, weight="bold")
    ax.plot([3200, 3700], [1450, 1450], color="black", lw=3)
    ax.plot([3200, 3450], [1450, 1450], color="white", lw=1.5)
    ax.text(3200, 1385, "0", ha="center", fontsize=7)
    ax.text(3700, 1385, "500 m", ha="center", fontsize=7)
    # title block
    ax.add_patch(Rectangle((2880, 1520), 1290, 330, fc="white", ec="black", lw=1.0))
    ax.text(3525, 1795, "Quellmoor Ridge Wind Farm", ha="center", fontsize=9.5, weight="bold")
    ax.text(3525, 1730, "Site layout plan - rev. C - 2024-05-06", ha="center", fontsize=8)
    ax.text(3525, 1670, "Contoso Renewables - local grid in metres", ha="center", fontsize=7.5)
    ax.text(3525, 1590, stamp, ha="center", fontsize=8, weight="bold", color="#c00000")
    ax.text(30, 4230, stamp, fontsize=8, weight="bold", color="#c00000", va="top")
    return fig


def crane_setup() -> Figure:
    """Plan view of the crane set-up for the blade lift (used in the scanned lift plan)."""
    fig, ax = plt.subplots(figsize=(6.0, 4.6))
    ax.set_xlim(-170, 170)
    ax.set_ylim(-170, 170)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Circle((0, 0), 150, fill=False, ls="--", lw=1.0, ec="#c00000"))
    ax.text(0, 154, "exclusion zone R = 150 m", ha="center", fontsize=8, color="#c00000")
    ax.add_patch(Circle((0, 0), 4.5, fc="black"))
    ax.text(8, -10, "WTG-04 tower", fontsize=8)
    ax.add_patch(Rectangle((-38, -14), 16, 28, fc="#ffd966", ec="black", lw=1.0))
    ax.text(-30, -26, "crane TS-600C-02", ha="center", fontsize=8)
    ax.add_patch(Wedge((-30, 0), 26, -40, 40, fill=False, lw=0.8, ls=":"))
    ax.text(-2, 22, "R 26 m", fontsize=8)
    ax.add_patch(Rectangle((30, -95), 70, 12, fc="#dce8f5", ec="black", lw=0.8))
    ax.text(65, -110, "blade laydown area", ha="center", fontsize=8)
    ax.add_patch(Rectangle((-120, 40), 50, 25, fc="#eeeeee", ec="black", lw=0.8))
    ax.text(-95, 72, "assist crane 100 t", ha="center", fontsize=8)
    ax.add_patch(FancyArrowPatch((85, 85), (125, 125), arrowstyle="-|>", mutation_scale=14))
    ax.text(60, 70, "prevailing wind from SW", fontsize=8)
    ax.plot([-150, -100], [-150, -150], color="black", lw=2.5)
    ax.text(-125, -163, "50 m", ha="center", fontsize=8)
    return fig
