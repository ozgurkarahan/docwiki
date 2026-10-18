"""Raster images: photographed handwritten checklist (JPG) and site layout plan (PNG).

Images are written without EXIF or text metadata.
"""

from __future__ import annotations

import io
import math
from pathlib import Path

import matplotlib
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .common import STAMP, rng
from .diagrams import site_layout, to_png
from .world import World

_FONT_DIR = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
INK = (28, 48, 128)


def font(size: int, style: str = "regular") -> ImageFont.FreeTypeFont:
    names = {
        "regular": "DejaVuSans.ttf",
        "bold": "DejaVuSans-Bold.ttf",
        "oblique": "DejaVuSans-Oblique.ttf",
        "mono": "DejaVuSansMono.ttf",
        "serif": "DejaVuSerif.ttf",
        "serif-bold": "DejaVuSerif-Bold.ttf",
    }
    return ImageFont.truetype(str(_FONT_DIR / names[style]), size)


def handwrite(
    img: Image.Image, xy: tuple[int, int], text: str, size: int, seed: str,
    color: tuple[int, int, int] = INK,
) -> int:
    """Draw text character by character with jitter so it looks hand-written; returns end x."""
    r = rng(f"hand-{seed}")
    x, y = xy
    for char in text:
        if char == " ":
            x += int(size * 0.38)
            continue
        scale = r.uniform(0.92, 1.1)
        glyph_font = font(int(size * scale), "oblique")
        bbox = glyph_font.getbbox(char)
        width = bbox[2] - bbox[0] + 8
        height = int(size * 1.6)
        glyph = Image.new("L", (width + 8, height), 0)
        ImageDraw.Draw(glyph).text((4 - bbox[0], 4), char, font=glyph_font, fill=255,
                                   stroke_width=1, stroke_fill=255)
        glyph = glyph.rotate(r.uniform(-7, 7), resample=Image.Resampling.BICUBIC, expand=True)
        glyph = glyph.filter(ImageFilter.GaussianBlur(0.6))
        ink = Image.new("RGB", glyph.size, color)
        img.paste(ink, (x, y + r.randint(-3, 3)), glyph)
        x += int(width * r.uniform(0.82, 0.95))
    return x


def tick(draw: ImageDraw.ImageDraw, x: int, y: int, seed: str, size: int = 26) -> None:
    r = rng(f"tick-{seed}")
    j = r.randint
    points = [
        (x + j(-2, 2), y + size // 2 + j(-2, 2)),
        (x + size // 3 + j(-2, 2), y + size + j(-2, 2)),
        (x + size + j(-3, 3), y + j(-3, 2)),
    ]
    draw.line(points, fill=INK, width=4, joint="curve")


def scribble(draw: ImageDraw.ImageDraw, x: int, y: int, width: int, seed: str,
             color: tuple[int, int, int] = INK) -> None:
    """A signature-like scribble."""
    r = rng(f"scribble-{seed}")
    points = []
    for i in range(28):
        t = i / 27
        px = x + t * width
        py = y + 14 * math.sin(t * 9 + r.uniform(0, 1.5)) + r.uniform(-6, 6)
        points.append((px, py))
    draw.line(points, fill=color, width=3, joint="curve")


def _perspective_coeffs(
    src: list[tuple[float, float]], dst: list[tuple[float, float]]
) -> list[float]:
    matrix = []
    for (x, y), (u, v) in zip(dst, src, strict=True):
        matrix.append([x, y, 1, 0, 0, 0, -u * x, -u * y])
        matrix.append([0, 0, 0, x, y, 1, -v * x, -v * y])
    a = np.array(matrix, dtype=float)
    b = np.array([c for point in src for c in point], dtype=float)
    return [float(v) for v in np.linalg.solve(a, b)]


def _checklist_form(w: World) -> Image.Image:
    width, height = 1240, 1700
    img = Image.new("RGB", (width, height), (250, 249, 244))
    d = ImageDraw.Draw(img)
    black = (25, 25, 25)
    d.text((70, 40), STAMP, font=font(26, "bold"), fill=(170, 20, 20))
    d.rectangle((70, 100, 1170, 230), outline=black, width=3)
    d.text((95, 115), "Daily turbine checklist", font=font(48, "bold"), fill=black)
    d.text((95, 180), "Form CHK-05  |  Quellmoor Ridge Wind Farm  |  Contoso Renewables",
           font=font(26), fill=black)
    fields = [("Date:", 280), ("Turbine:", 340), ("Technician:", 400)]
    for label, y in fields:
        d.text((80, y), label, font=font(30, "bold"), fill=black)
        d.line((290, y + 36, 760, y + 36), fill=black, width=2)
    handwrite(img, (305, 274), "14/07/2026", 38, "date")
    handwrite(img, (305, 334), "WTG-05", 38, "turbine")
    handwrite(img, (305, 394), "C. Rydings", 38, "tech")
    top = 480
    d.rectangle((70, top, 1170, top + 60), fill=(225, 225, 225), outline=black, width=2)
    d.text((85, top + 14), "Check", font=font(28, "bold"), fill=black)
    d.text((820, top + 14), "OK", font=font(28, "bold"), fill=black)
    d.text((920, top + 14), "Not OK", font=font(28, "bold"), fill=black)
    items = [
        "1. Tower base door, signage and lighting",
        "2. Ladder, fall arrest rail and service lift",
        "3. Nacelle housekeeping and hatch closed",
        "4. Gearbox oil level at sight glass",
        "5. Oil leaks (gearbox, hydraulics, yaw)",
        "6. Hydraulic pressure (160-180 bar)",
        "7. Yaw brakes - no abnormal noise",
        "8. Fire extinguishers in date",
        "9. Rescue kit present, seal intact",
        "10. Spill kit complete",
    ]
    row_h = 78
    for index, item in enumerate(items):
        y = top + 60 + index * row_h
        d.rectangle((70, y, 1170, y + row_h), outline=black, width=2)
        d.line((800, y, 800, y + row_h), fill=black, width=2)
        d.line((900, y, 900, y + row_h), fill=black, width=2)
        d.text((85, y + 22), item, font=font(28), fill=black)
        if item.startswith("6."):
            d.line((585, y + 58, 700, y + 58), fill=black, width=2)
            d.text((708, y + 28), "bar", font=font(26), fill=black)
            handwrite(img, (596, y + 6), "168", 44, "pressure")
        tick(d, 832, y + 24, f"ok-{index}")
    y = top + 60 + len(items) * row_h + 40
    d.text((80, y), "Remarks:", font=font(28, "bold"), fill=black)
    d.line((230, y + 34, 1170, y + 34), fill=black, width=2)
    handwrite(img, (245, y - 4), "all OK", 34, "remarks")
    d.text((80, y + 90), "Signature:", font=font(28, "bold"), fill=black)
    scribble(d, 260, y + 110, 260, "sig")
    d.text((70, height - 70), STAMP, font=font(26, "bold"), fill=(170, 20, 20))
    return img


def checklist_photo(w: World) -> bytes:
    """Photograph of the filled-in checklist: perspective, lighting, blur and noise."""
    form = _checklist_form(w)
    canvas_w, canvas_h = 1500, 1900
    gen = np.random.default_rng(424242)
    base = np.zeros((canvas_h, canvas_w, 3), dtype=float)
    gradient = np.linspace(0.0, 1.0, canvas_w)[None, :, None]
    base += np.array([118, 92, 66]) * (0.8 + 0.25 * gradient)
    base += gen.normal(0.0, 6.0, size=(canvas_h, canvas_w, 1))
    background = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")
    fw, fh = form.size
    dst = [(150.0, 120.0), (1390.0, 175.0), (1345.0, 1800.0), (95.0, 1745.0)]
    coeffs = _perspective_coeffs([(0, 0), (fw, 0), (fw, fh), (0, fh)], dst)
    warped = form.transform((canvas_w, canvas_h), Image.Transform.PERSPECTIVE, coeffs,
                            Image.Resampling.BICUBIC)
    mask = Image.new("L", form.size, 255).transform(
        (canvas_w, canvas_h), Image.Transform.PERSPECTIVE, coeffs, Image.Resampling.BICUBIC
    )
    shadow = mask.filter(ImageFilter.GaussianBlur(18))
    background.paste(Image.new("RGB", background.size, (40, 30, 22)), (14, 18), shadow)
    background.paste(warped, (0, 0), mask)
    arr = np.asarray(background).astype(float)
    yy, xx = np.mgrid[0:canvas_h, 0:canvas_w]
    dx = (xx - canvas_w * 0.35) / canvas_w
    dy = (yy - canvas_h * 0.3) / canvas_h
    light = 1.05 - 0.22 * (dx**2 + dy**2)
    arr = arr * light[..., None] + gen.normal(0.0, 3.5, size=arr.shape)
    photo = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    photo = photo.filter(ImageFilter.GaussianBlur(0.7))
    photo = photo.resize((1200, 1520), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    photo.save(buf, "JPEG", quality=80, optimize=True)
    return buf.getvalue()


def site_plan(w: World) -> bytes:
    return to_png(site_layout(w.turbines, w.stamp), dpi=110)
