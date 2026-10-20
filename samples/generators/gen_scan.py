"""Image-only scanned PDF: the builders' merchant delivery note BL-2026-0391.

The printed form and the handwritten remarks ("2 palettes manquantes", "reçu 8 pal.", the
receiver's name and a signature) are drawn with Pillow, degraded like a scan and embedded as a
single JPEG page: the PDF has no text layer, so the remarks are only readable through OCR. The
stamp is printed at the top and bottom of the page image and the PDF Subject is the stamp.
"""

from __future__ import annotations

import io
import math

import numpy as np
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFilter

from .common import GENERATOR_AUTHOR, STAMP, fr_date, meta_for, quantity, rng
from .fonts import pil_font
from .world import World

PAGE_W, PAGE_H = 1240, 1754  # A4 at 150 dpi
BLACK = (22, 22, 22)
GREY = (215, 215, 215)
INK = (24, 40, 120)


def handwrite(
    img: Image.Image, xy: tuple[int, int], text: str, size: int, seed: str,
    color: tuple[int, int, int] = INK,
) -> int:
    """Draw text character by character with jitter so it looks hand-written; returns end x."""
    r = rng(f"hand-{seed}")
    x, y = xy
    for char in text:
        if char == " ":
            x += int(size * 0.42)
            continue
        scale = r.uniform(0.94, 1.08)
        glyph_font = pil_font(int(size * scale), "oblique")
        bbox = glyph_font.getbbox(char)
        width = bbox[2] - bbox[0] + 8
        height = int(size * 1.6)
        glyph = Image.new("L", (width + 8, height), 0)
        ImageDraw.Draw(glyph).text((4 - bbox[0], 4), char, font=glyph_font, fill=255,
                                   stroke_width=1, stroke_fill=255)
        glyph = glyph.rotate(r.uniform(-6, 6), resample=Image.Resampling.BICUBIC, expand=True)
        glyph = glyph.filter(ImageFilter.GaussianBlur(0.5))
        ink = Image.new("RGB", glyph.size, color)
        img.paste(ink, (x, y + r.randint(-2, 2)), glyph)
        x += int(width * r.uniform(0.84, 0.94))
    return x


def scribble(draw: ImageDraw.ImageDraw, x: int, y: int, width: int, seed: str,
             color: tuple[int, int, int] = INK) -> None:
    """A signature-like scribble."""
    r = rng(f"scribble-{seed}")
    points = []
    for i in range(32):
        t = i / 31
        px = x + t * width
        py = y + 16 * math.sin(t * 10 + r.uniform(0, 1.5)) + r.uniform(-7, 7)
        points.append((px, py))
    draw.line(points, fill=color, width=3, joint="curve")
    draw.line([(x + width * 0.1, y + 26), (x + width * 0.95, y + 18)], fill=color, width=2)


def _labelled(d: ImageDraw.ImageDraw, x: int, y: int, label: str, value: str,
              label_w: int = 290) -> None:
    d.text((x, y), label, font=pil_font(25, "bold"), fill=BLACK)
    d.text((x + label_w, y), value, font=pil_font(25), fill=BLACK)


def _box(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], title: str) -> None:
    d.rectangle(box, outline=BLACK, width=3)
    d.text((box[0] + 14, box[1] + 10), title, font=pil_font(24, "bold"), fill=BLACK)


def _page(w: World) -> Image.Image:
    facts = w.facts["zava_delivery"]
    doc = w.doc("bl-scan")
    merchant = w.org(str(doc["organisation"]))
    builder = w.builder
    site = w.facts["site"]
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    d.text((80, 40), STAMP, font=pil_font(24, "bold"), fill=BLACK)
    # Letterhead and title
    d.rectangle((80, 90, 640, 250), outline=BLACK, width=3)
    d.text((100, 104), merchant["name"], font=pil_font(44, "bold"), fill=BLACK)
    role = str(merchant["role_fr"])
    d.text((100, 162), role[:1].upper() + role[1:], font=pil_font(24), fill=BLACK)
    address = str(site["merchant_address"])
    d.text((100, 198), address[:1].upper() + address[1:], font=pil_font(21), fill=BLACK)
    d.text((690, 104), "BON DE LIVRAISON", font=pil_font(40, "bold"), fill=BLACK)
    d.text((690, 162), f"N° {facts['number']}", font=pil_font(36, "bold"), fill=BLACK)
    d.text((690, 214), "Exemplaire client", font=pil_font(22), fill=BLACK)
    # Delivery details
    y = 300
    for label, value in (
        ("Date de livraison :", f"{fr_date(str(facts['date']))} à {facts['time']}"),
        ("Client :", f"{builder['name']}, {site['builder_address']}"),
        ("Commande client :", str(facts["order"])),
        ("Livré à :", str(facts["delivered_to"])),
        ("Véhicule :", str(facts["vehicle"])),
    ):
        _labelled(d, 80, y, label, value)
        y += 46
    # Printed lines
    columns = [(80, "Code article"), (275, "Désignation"), (790, "Qté"), (875, "Unité")]
    right = 990
    top = 560
    row_h = 74
    d.rectangle((80, top, right, top + 56), fill=GREY, outline=BLACK, width=2)
    for x, title in columns:
        d.text((x + 12, top + 14), title, font=pil_font(24, "bold"), fill=BLACK)
    lines = facts["printed_lines"]
    for index, line in enumerate(lines):
        y0 = top + 56 + index * row_h
        d.rectangle((80, y0, right, y0 + row_h), outline=BLACK, width=2)
        designation = str(line["designation"])
        cells = [str(line["code"]), designation, quantity(line["qty"]), str(line["unit"])]
        for (x, _), text in zip(columns, cells, strict=True):
            size = 21 if len(text) > 34 else 23
            if len(text) > 40:
                first, _, rest = text.rpartition(" (")
                if first:
                    d.text((x + 12, y0 + 8), first, font=pil_font(size), fill=BLACK)
                    d.text((x + 12, y0 + 38), f"({rest}", font=pil_font(size), fill=BLACK)
                    continue
                first, _, rest = text.rpartition(", ")
                d.text((x + 12, y0 + 8), first + ",", font=pil_font(size), fill=BLACK)
                d.text((x + 12, y0 + 38), rest, font=pil_font(size), fill=BLACK)
                continue
            d.text((x + 12, y0 + 22), text, font=pil_font(size), fill=BLACK)
    for x, _ in columns[1:]:
        d.line((x, top, x, top + 56 + len(lines) * row_h), fill=BLACK, width=2)
    pallet_row = next(i for i, line in enumerate(lines) if line["unit"] == "palette")
    hand = facts["handwritten"]
    y_pallet = top + 56 + pallet_row * row_h
    d.ellipse((782, y_pallet + 10, 862, y_pallet + 64), outline=INK, width=3)
    handwrite(img, (1004, y_pallet + 14), str(hand["next_to_block_line"]), 34, "pallets")
    # Reserves, receiver and signature boxes
    boxes_top = top + 56 + len(lines) * row_h + 70
    titles = [str(title) for title in facts["printed_boxes"]]
    _box(d, (80, boxes_top, 1160, boxes_top + 220), titles[0])
    handwrite(img, (130, boxes_top + 90), str(hand["reserves"]), 50, "reserves")
    second = boxes_top + 260
    _box(d, (80, second, 600, second + 170), titles[1])
    handwrite(img, (130, second + 72), str(hand["received_by"]), 46, "received-by")
    _box(d, (640, second, 1160, second + 170), titles[2])
    scribble(d, 700, second + 102, 380, "receiver")
    d.text((80, PAGE_H - 80), STAMP, font=pil_font(24, "bold"), fill=BLACK)
    return img


def _scan(page: Image.Image, angle: float, seed: int) -> bytes:
    gray = page.convert("L")
    gray = gray.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    arr = np.asarray(gray).astype(float)
    gen = np.random.default_rng(seed)
    arr = arr * 0.95 + 9 + gen.normal(0.0, 6.0, size=arr.shape)
    shade = np.linspace(-22.0, 0.0, 50)
    arr[:, :50] += shade[None, :]
    specks = gen.integers(0, arr.size, size=240)
    arr.flat[specks] = gen.uniform(40, 120, size=240)
    scanned = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")
    scanned = scanned.filter(ImageFilter.GaussianBlur(0.6))
    buf = io.BytesIO()
    scanned.save(buf, "JPEG", quality=70, optimize=True)
    return buf.getvalue()


def bl_scan(w: World) -> bytes:
    doc = w.doc("bl-scan")
    meta = meta_for(doc, w.org_name(str(doc["organisation"])))
    pages = int(w.facts["zava_delivery"]["pages"])
    if pages != 1:
        raise ValueError("the delivery note scan has exactly one page")
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_title(meta.title)
    pdf.set_subject(STAMP)
    pdf.set_author(GENERATOR_AUTHOR)
    pdf.set_creator(GENERATOR_AUTHOR)
    pdf.set_producer(GENERATOR_AUTHOR)
    pdf.set_keywords(meta.keywords)
    pdf.set_creation_date(meta.created)
    pdf.set_lang(meta.lang)
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.image(io.BytesIO(_scan(_page(w), 0.45, 9001)), x=0, y=0, w=210, h=297)
    return bytes(pdf.output())
