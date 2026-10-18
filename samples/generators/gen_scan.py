"""Image-only scanned PDF: Tailspin lift plan LP-2026-009 (no text layer, OCR needed)."""

from __future__ import annotations

import io

import numpy as np
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFilter

from .common import GENERATOR_AUTHOR, STAMP, latin1, meta_for
from .diagrams import crane_setup, to_png
from .gen_images import font, handwrite, scribble
from .world import World

PAGE_W, PAGE_H = 1240, 1754
BLACK = (20, 20, 20)


def _page_header(d: ImageDraw.ImageDraw, page: int) -> None:
    d.text((90, 50), STAMP, font=font(24, "bold"), fill=BLACK)
    d.rectangle((90, 100, 380, 170), outline=BLACK, width=4)
    d.text((108, 112), "TAILSPIN", font=font(30, "bold"), fill=BLACK)
    d.text((108, 142), "HEAVY LIFT", font=font(20, "bold"), fill=BLACK)
    d.text((440, 108), "LIFT PLAN  LP-2026-009", font=font(40, "bold"), fill=BLACK)
    d.text((1000, 120), f"Page {page} of 2", font=font(22), fill=BLACK)
    d.line((90, 195, 1150, 195), fill=BLACK, width=3)


def _rows(d: ImageDraw.ImageDraw, top: int, rows: list[tuple[str, str]], label_w: int = 330) -> int:
    y = top
    for label, value in rows:
        d.text((95, y), label, font=font(24, "bold"), fill=BLACK)
        d.text((95 + label_w, y), value, font=font(24), fill=BLACK)
        y += 40
    return y


def _section(d: ImageDraw.ImageDraw, y: int, title: str) -> int:
    d.text((90, y), title, font=font(28, "bold"), fill=BLACK)
    return y + 46


def _page_one() -> Image.Image:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    _page_header(d, 1)
    y = _rows(
        d,
        225,
        [
            ("Client:", "Contoso Renewables - Quellmoor Ridge Wind Farm"),
            ("Job:", "WTG-04 rotor blade B replacement (single blade lift)"),
            ("Lift window:", "2026-09-08 to 2026-09-10, daylight only"),
            ("Plan date:", "2026-08-19"),
            ("Appointed person:", "Bram Okkerse, Tailspin Heavy Lift"),
            ("Client supervisor:", "Dario Penwarden, Contoso Renewables"),
        ],
    )
    y = _section(d, y + 20, "1. Crane and rigging")
    y = _rows(
        d,
        y,
        [
            ("Main crane:", "600 t crawler crane, fleet no. TS-600C-02, 102 m main boom"),
            ("Assist crane:", "100 t mobile crane (tailing the blade root)"),
            ("Blade:", "57.5 m, 14.6 t"),
            ("Blade yoke:", "3.9 t"),
            ("Rigging:", "0.6 t"),
            ("Total hook load:", "19.1 t"),
            ("Radius:", "26 m      capacity at radius 31.0 t      utilisation 62 %"),
            ("Hook height:", "96 m"),
        ],
    )
    y = _section(d, y + 20, "2. Weather limits")
    for line in (
        "Maximum 10-minute mean wind speed at hub height: 8 m/s",
        "Maximum gust: 11 m/s",
        "No lift in fog (visibility below 300 m), with lightning within 15 km or with icing.",
        "Wind is read at the WTG-04 nacelle anemometer and at the boom tip anemometer.",
    ):
        d.text((95, y), line, font=font(24), fill=BLACK)
        y += 40
    y = _section(d, y + 20, "3. Exclusion zone")
    for line in (
        "Radius 150 m around WTG-04 during the lift.",
        "Two tag lines of 120 m on the blade. Site gate closed by the banksman.",
    ):
        d.text((95, y), line, font=font(24), fill=BLACK)
        y += 40
    y = _section(d, y + 20, "4. Ground")
    d.text((95, y), "Ground bearing pressure under crane mats: 180 kN/m2 (allowable 250 kN/m2).",
           font=font(24), fill=BLACK)
    d.text((90, PAGE_H - 80), STAMP, font=font(24, "bold"), fill=BLACK)
    return img


def _page_two() -> Image.Image:
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    _page_header(d, 2)
    y = _section(d, 225, "5. Crane set-up (plan view)")
    sketch = Image.open(io.BytesIO(to_png(crane_setup(), dpi=110))).convert("RGB")
    sketch = sketch.resize((760, int(sketch.height * 760 / sketch.width)))
    img.paste(sketch, (240, y))
    y += sketch.height + 10
    y = _section(d, y, "6. Sequence")
    steps = (
        "1. Pre-lift meeting; PTW signed by both parties.",
        "2. Rotor locked with blade B pointing down; pitch system isolated.",
        "3. Blade yoke fitted and load test at 0.5 m above the laydown area.",
        "4. Blade B unbolted and lowered with both tag lines manned.",
        "5. New blade lifted, bolted and torqued per Litware instruction.",
        "6. Exclusion zone released only by the appointed person.",
    )
    for step in steps:
        d.text((95, y), step, font=font(24), fill=BLACK)
        y += 40
    y = _section(d, y + 20, "7. Sign-off")
    d.text((95, y), "Prepared: Bram Okkerse, Appointed Person", font=font(24), fill=BLACK)
    scribble(d, 720, y + 18, 220, "okkerse", (30, 30, 30))
    handwrite(img, (980, y - 2), "19/08/26", 30, "okkerse-date", (30, 30, 30))
    y += 70
    d.text((95, y), "Approved: Dario Penwarden, O&M Supervisor", font=font(24), fill=BLACK)
    scribble(d, 720, y + 18, 220, "penwarden", (30, 30, 30))
    handwrite(img, (980, y - 2), "21/08/26", 30, "penwarden-date", (30, 30, 30))
    d.text((90, PAGE_H - 80), STAMP, font=font(24, "bold"), fill=BLACK)
    return img


def _scan(page: Image.Image, angle: float, seed: int) -> bytes:
    gray = page.convert("L")
    gray = gray.rotate(angle, resample=Image.Resampling.BICUBIC, fillcolor=255)
    arr = np.asarray(gray).astype(float)
    gen = np.random.default_rng(seed)
    arr = arr * 0.94 + 10 + gen.normal(0.0, 7.0, size=arr.shape)
    shade = np.linspace(-26.0, 0.0, 60)
    arr[:, :60] += shade[None, :]
    specks = gen.integers(0, arr.size, size=260)
    arr.flat[specks] = gen.uniform(40, 120, size=260)
    scanned = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "L")
    scanned = scanned.filter(ImageFilter.GaussianBlur(0.65))
    buf = io.BytesIO()
    scanned.save(buf, "JPEG", quality=62, optimize=True)
    return buf.getvalue()


def lift_plan_scan(w: World) -> bytes:
    doc = w.doc("lift-plan-scan")
    meta = meta_for(doc, w.org_name(str(doc["organisation"])))
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_title(latin1(meta.title))
    pdf.set_subject(STAMP)
    pdf.set_author(GENERATOR_AUTHOR)
    pdf.set_creator(GENERATOR_AUTHOR)
    pdf.set_producer(GENERATOR_AUTHOR)
    pdf.set_keywords(latin1(meta.keywords))
    pdf.set_creation_date(meta.created)
    pdf.set_auto_page_break(False)
    for page, angle, seed in ((_page_one(), 0.6, 9001), (_page_two(), -0.45, 9002)):
        pdf.add_page()
        pdf.image(io.BytesIO(_scan(page, angle, seed)), x=0, y=0, w=210, h=297)
    return bytes(pdf.output())
