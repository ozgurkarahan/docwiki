"""DOCX documents: SOPs, French work instruction, 8D report, MOC, minutes and IT documents."""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import date, timedelta

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor

from . import datasets
from .common import STAMP, meta_for
from .diagrams import to_png, wtg07_trend
from .ooxml import finalize_package
from .world import World


class DocxBuilder:
    """Small wrapper over python-docx that never creates empty body paragraphs."""

    def __init__(self, header: str, footer: str) -> None:
        self.doc = Document()
        section = self.doc.sections[0]
        section.page_width = Cm(21.0)
        section.page_height = Cm(29.7)
        for side in ("left_margin", "right_margin"):
            setattr(section, side, Cm(2.0))
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.0)
        normal = self.doc.styles["Normal"]
        normal.font.name = "Calibri"
        normal.font.size = Pt(10.5)
        head = section.header.paragraphs[0]
        head.text = f"{header}  |  {STAMP}"
        head.runs[0].font.size = Pt(8)
        foot = section.footer.paragraphs[0]
        foot.text = f"{STAMP}  |  {footer}"
        foot.runs[0].font.size = Pt(8)
        foot.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def title(self, text: str, subtitle: str = "") -> None:
        self.doc.add_heading(text, 0)
        if subtitle:
            self.para(subtitle, italic=True)

    def h1(self, text: str) -> None:
        self.doc.add_heading(text, 1)

    def h2(self, text: str) -> None:
        self.doc.add_heading(text, 2)

    def para(self, text: str, bold: bool = False, italic: bool = False) -> None:
        if not text.strip():
            raise ValueError("empty paragraphs are not allowed")
        paragraph = self.doc.add_paragraph()
        run = paragraph.add_run(text)
        run.bold = bold
        run.italic = italic

    def bullets(self, items: Sequence[str]) -> None:
        for item in items:
            self.doc.add_paragraph(item, style="List Bullet")

    def steps(self, items: Sequence[str]) -> None:
        """Numbered steps with the number written in the text (stable when extracted)."""
        for item in items:
            paragraph = self.doc.add_paragraph(item)
            paragraph.paragraph_format.left_indent = Cm(0.8)
            paragraph.paragraph_format.first_line_indent = Cm(-0.8)

    def table(self, header: Sequence[str], rows: Sequence[Sequence[object]],
              widths: Sequence[float] | None = None) -> None:
        table = self.doc.add_table(rows=1 + len(rows), cols=len(header))
        table.style = "Table Grid"
        for col, value in enumerate(header):
            cell = table.rows[0].cells[col]
            cell.text = str(value)
            for run in cell.paragraphs[0].runs:
                run.bold = True
        for r, values in enumerate(rows, start=1):
            for col, value in enumerate(values):
                table.rows[r].cells[col].text = str(value)
        if widths:
            for row in table.rows:
                for col, width in enumerate(widths):
                    row.cells[col].width = Cm(width)

    def figure(self, png: bytes, width_cm: float, caption: str) -> None:
        """Picture and caption share one paragraph, so no body paragraph is text-less."""
        paragraph = self.doc.add_paragraph()
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run().add_picture(io.BytesIO(png), width=Cm(width_cm))
        caption_run = paragraph.add_run("\n" + caption)
        caption_run.italic = True
        caption_run.font.size = Pt(9)
        caption_run.font.color.rgb = RGBColor(0x40, 0x40, 0x40)

    def render(self, w: World, doc_id: str) -> bytes:
        doc = w.doc(doc_id)
        meta = meta_for(doc, w.org_name(str(doc["organisation"])))
        buf = io.BytesIO()
        self.doc.save(buf)
        return finalize_package(buf.getvalue(), meta)


# ------------------------------------------------------------------------------------------
# Procedures


def _sop_gbx(w: World, revision: str) -> bytes:
    is_b = revision == "B"
    effective = "2025-08-25" if is_b else "2023-04-03"
    b = DocxBuilder(f"Contoso Renewables - SOP-GBX-010 Rev. {revision}",
                    f"SOP-GBX-010 Rev. {revision} - Gearbox oil change")
    b.title("SOP-GBX-010 - Gearbox oil change",
            f"Standard operating procedure - Revision {revision} - effective {effective}")
    b.table(
        ["Field", "Value"],
        [
            ["Document number", "SOP-GBX-010"],
            ["Revision", revision],
            ["Effective date", effective],
            ["Owner", "Dario Penwarden, O&M Supervisor"],
            ["Approved by", "Maren Ellingsby, Site Manager"],
            ["Applies to", "WTG-01 to WTG-12 (Litware LT-32 CCV, Fabrikam FGT-3200 gearbox)"],
        ],
        widths=(5, 12),
    )
    if is_b:
        b.para("This revision supersedes SOP-GBX-010 Rev. A. It implements MOC-2025-012 and "
               "service bulletin SB-LWS-2025-07 Rev. A.", bold=True)
    b.h1("1. Purpose")
    b.para("This procedure describes how to change the gearbox oil of the Quellmoor Ridge "
           "turbines safely and without contaminating the new oil.")
    b.h1("2. Scope")
    b.para("All gearbox oil changes on WTG-01 to WTG-12, whether planned or decided after an oil "
           "analysis.")
    b.h1("3. References")
    refs = [
        "LWS-MM-GBX-32 Rev. D, section 4.3 (Litware maintenance manual, gearbox)",
        "SOP-LOTO-001 Lockout/tagout of wind turbines",
        "SOP-WAH-003 Working at height and rescue",
        "SPL-012 Gearbox oil level check" if is_b else "Oil level check at the sight glass",
    ]
    if is_b:
        refs[1:1] = ["SB-LWS-2025-07 Rev. A (gear oil for CCV turbines)",
                     "MOC-2025-012 Gearbox oil grade change to PWG 220"]
    b.bullets(refs)
    b.h1("4. Safety")
    b.bullets(
        [
            "A PTW is required. Two technicians minimum; no lone working in the nacelle.",
            "Isolate the turbine according to SOP-LOTO-001 before opening the oil circuit.",
            "Do not start the job if the 10-minute mean wind speed exceeds 15 m/s.",
            "Hot oil: wear chemical gloves, face shield and long sleeves; drain only between 40 "
            "and 60 °C.",
            "Keep the spill kit ready at the gearbox and absorbent pads under every connection.",
        ]
    )
    b.h1("5. Materials and tools")
    if is_b:
        materials = [
            "Proseware PWG 220 (ISO VG 220): 470 L per turbine (60 L flush + 410 L fill), "
            "3 drums PWS-220-D208",
            "Oil filter element FGT-P-11872 (1)",
            "Filter cart with 10 micron element, transfer pump, 3 waste oil containers of 200 L",
            "Torque wrench 20 to 300 Nm, oil sample bottles, label kit 'PWG 220'",
        ]
    else:
        materials = [
            "Proseware PWG 320 (ISO VG 320): 410 L per turbine, 2 drums PWS-320-D208",
            "Oil filter element FGT-P-11872 (1)",
            "Filter cart with 10 micron element, transfer pump, 3 waste oil containers of 200 L",
            "Torque wrench 20 to 300 Nm, oil sample bottles",
        ]
    b.bullets(materials)
    b.h1("6. Procedure")
    steps = [
        "6.1 Obtain the PTW, stop the turbine and apply lockout/tagout according to SOP-LOTO-001 "
        "(rotor locked, drivetrain isolated).",
        "6.2 Check the oil temperature: drain between 40 and 60 °C. If the oil is colder, run "
        "the heaters and the electric oil pump before isolation.",
        "6.3 Take a used-oil sample at the sampling valve for the laboratory.",
        "6.4 Drain the gearbox sump and the cooling and filter circuit into the waste "
        "containers (about 410 L).",
        "6.5 Remove the magnetic plug, record the debris and clean the plug.",
        "6.6 Replace the filter element FGT-P-11872 and tighten the filter housing cover "
        "screws to 85 Nm.",
        "6.7 Refit the drain plug with a new seal and tighten it to 280 Nm.",
    ]
    if is_b:
        steps += [
            "6.8 Flush: fill 60 L of PWG 220, run the electric oil pump for 30 minutes, then "
            "drain the flush oil into the waste containers.",
            "6.9 Fill 410 L of Proseware PWG 220 through the filter cart (10 micron).",
            "6.10 Run the electric oil pump for 15 minutes and check all connections for leaks.",
            "6.11 After 20 minutes of standstill check the level at the sight glass (SPL-012) "
            "and top up with PWG 220 only.",
            "6.12 Check that the controller parameter GBX_TMIN_START is set to 5 °C and label "
            "the gearbox filler 'PWG 220'.",
            "6.13 Remove the lockout, restart and watch the oil temperature during the first "
            "hour. The turbine starts only when the oil sump has reached +5 °C.",
            "6.14 Take a reference oil sample after 24 hours of operation.",
            "6.15 Record the quantities and batch numbers in the work order and send the "
            "completion form to Litware Wind Systems within 30 days.",
        ]
    else:
        steps += [
            "6.8 Fill 410 L of Proseware PWG 320 through the filter cart (10 micron).",
            "6.9 Run the electric oil pump for 15 minutes and check all connections for leaks.",
            "6.10 After 20 minutes of standstill check the level at the sight glass and top up "
            "if needed.",
            "6.11 Remove the lockout, restart and watch the oil temperature during the first "
            "hour. The turbine starts only when the oil sump has reached +10 °C.",
            "6.12 Take a reference oil sample after 24 hours of operation.",
            "6.13 Record the quantities and batch numbers in the work order.",
        ]
    b.steps(steps)
    if is_b:
        b.para("Never top up a converted gearbox with PWG 320. Residual PWG 320 must stay below "
               "5 % of the oil volume.", bold=True)
    b.h1("7. Waste and records")
    b.para("Waste oil goes to the bunded store in the O&M building and is collected by the "
           "licensed carrier. Keep the oil sample results with the work order.")
    b.h1("8. Revision history")
    history = [["A", "2023-04-03", "First issue (PWG 320)."]]
    if is_b:
        history.append(["B", "2025-08-25", "Oil changed to PWG 220 per MOC-2025-012 and "
                        "SB-LWS-2025-07; flush step added; minimum start-up temperature +5 °C."])
    b.table(["Revision", "Date", "Change"], history, widths=(2.5, 3, 11.5))
    return b.render(w, "sop-gbx-b" if is_b else "sop-gbx-a")


def sop_gbx_a(w: World) -> bytes:
    return _sop_gbx(w, "A")


def sop_gbx_b(w: World) -> bytes:
    return _sop_gbx(w, "B")


def sop_loto(w: World) -> bytes:
    b = DocxBuilder("Contoso Renewables - SOP-LOTO-001 Rev. C",
                    "SOP-LOTO-001 Rev. C - Lockout/tagout")
    b.title("SOP-LOTO-001 - Lockout/tagout of wind turbines",
            "Standard operating procedure - Revision C - effective 2024-09-02")
    b.table(
        ["Field", "Value"],
        [
            ["Document number", "SOP-LOTO-001"],
            ["Revision", "C"],
            ["Effective date", "2024-09-02"],
            ["Owner", "Greta Vollan, HSE Coordinator"],
            ["Approved by", "Maren Ellingsby, Site Manager"],
        ],
        widths=(5, 12),
    )
    b.h1("1. Purpose")
    b.para("Protect people working on a turbine against the unexpected release of electrical, "
           "hydraulic, mechanical, rotational and thermal energy.")
    b.h1("2. Scope")
    b.para("All work on WTG-01 to WTG-12 and on the Quellmoor Ridge substation low-voltage "
           "boards. High-voltage switching is done only by authorised persons under the "
           "switching programme and is outside this procedure.")
    b.h1("3. Responsibilities")
    b.bullets(
        [
            "The PTW issuer checks the isolation list before signing the PTW.",
            "Each worker applies a personal padlock and keeps the key.",
            "The O&M Supervisor approves any deviation in writing.",
        ]
    )
    b.h1("4. Energy sources of the LT-32")
    b.table(
        ["Energy", "Source", "Isolation point"],
        [
            ["Electrical 690 V", "Generator, converter, auxiliaries", "Main circuit breaker in "
             "the tower base"],
            ["Electrical 33 kV", "Transformer feeder", "Ring main unit (authorised persons only)"],
            ["Uninterruptible power", "UPS of the controller", "UPS output breaker"],
            ["Hydraulic", "Pitch and yaw brake accumulators", "Relief valves to 0 bar"],
            ["Rotational", "Rotor and drivetrain", "Rotor lock pins"],
            ["Thermal", "Hot gear oil, heaters", "Cool-down and heater breaker"],
        ],
        widths=(4, 6, 7),
    )
    b.h1("5. Personal padlocks and tags")
    b.para("Every worker uses a personal padlock with a name tag. Padlocks without a name tag "
           "must not be used. Spare padlocks are issued by the HSE Coordinator.")
    b.h1("6. Isolation sequence")
    b.steps(
        [
            "6.1 Inform the control room and set the turbine to maintenance mode (status S310).",
            "6.2 Stop the turbine from the controller and wait until the rotor speed is below "
            "1 rpm.",
            "6.3 Engage the rotor lock pins; do not engage them above a 10-minute mean wind "
            "speed of 15 m/s.",
            "6.4 Open the main circuit breaker and the UPS output breaker; apply padlocks and "
            "tags.",
            "6.5 Release the hydraulic pressure of the pitch and yaw brake accumulators to 0 bar.",
            "6.6 Apply the group lock box when more than two people work on the turbine.",
        ]
    )
    b.h1("7. Verification")
    b.para("Try to start the turbine from the local panel, test for absence of voltage at the "
           "converter and read 0 bar on the accumulator gauges before work starts.")
    b.h1("8. Removal")
    b.para("Each worker removes only his or her own padlock. The last person checks that tools "
           "are removed and guards are fitted before the turbine leaves maintenance mode.")
    b.h1("9. Revision history")
    b.table(
        ["Revision", "Date", "Change"],
        [
            ["A", "2019-10-01", "First issue at commercial operation."],
            ["B", "2021-05-17", "Group lock box added."],
            ["C", "2024-09-02", "Energy table updated; wind limit for rotor lock pins."],
        ],
        widths=(2.5, 3, 11.5),
    )
    return b.render(w, "sop-loto")


def sop_wah(w: World) -> bytes:
    b = DocxBuilder("Contoso Renewables - SOP-WAH-003 Rev. B",
                    "SOP-WAH-003 Rev. B - Working at height and rescue")
    b.title("SOP-WAH-003 - Working at height and rescue",
            "Standard operating procedure - Revision B - effective 2026-04-07")
    b.table(
        ["Field", "Value"],
        [
            ["Document number", "SOP-WAH-003"],
            ["Revision", "B"],
            ["Effective date", "2026-04-07"],
            ["Owner", "Greta Vollan, HSE Coordinator"],
            ["Approved by", "Maren Ellingsby, Site Manager"],
        ],
        widths=(5, 12),
    )
    b.h1("1. Purpose")
    b.para("Prevent falls of people and objects during work in the towers and nacelles, and make "
           "sure that a casualty can be rescued quickly.")
    b.h1("2. Scope")
    b.para("All climbing, work in the nacelle and hub, and rescue on WTG-01 to WTG-12.")
    b.h1("3. Responsibilities")
    b.bullets(
        [
            "The O&M Supervisor plans work at height and checks the weather limits.",
            "Each technician checks his or her own harness and lanyards before use.",
            "The HSE Coordinator organises rescue drills twice a year.",
        ]
    )
    b.h1("4. Dropped objects and exclusion zones")
    b.para("Tool tethering is mandatory above 2 m. Hatches stay closed while tools or parts are "
           "passed. During nacelle work an exclusion zone with signage is set up at the tower "
           "base and nobody enters it without the agreement of the nacelle team.")
    b.h1("5. Climbing")
    b.bullets(
        [
            "Two persons minimum; climb one ladder section at a time.",
            "Use the fall arrest rail and rest platforms; use the service lift when available.",
            "Report any damaged ladder rung or fall arrest component immediately.",
        ]
    )
    b.h1("6. Weather limits")
    b.table(
        ["Activity", "Limit"],
        [
            ["Climbing and nacelle work", "10-minute mean wind speed up to 15 m/s"],
            ["Hub entry", "10-minute mean wind speed up to 12 m/s"],
            ["Work on the nacelle roof", "10-minute mean wind speed up to 10 m/s"],
            ["Thunderstorm", "no climbing when lightning is detected within 15 km"],
            ["Ice", "no access within 300 m of a turbine with ice detected (A7001)"],
        ],
        widths=(7, 10),
    )
    b.h1("7. Rescue equipment and inspection")
    b.para("Each nacelle holds a sealed rescue kit with a descent device. The kits are inspected "
           "every 6 months and the seal is checked on the daily checklist. A broken seal means "
           "that the kit must be inspected before the next climb.")
    b.h1("8. Rescue procedure")
    b.steps(
        [
            "8.1 Raise the alarm to the control room and to the emergency services.",
            "8.2 Make the turbine safe (stop, rotor lock).",
            "8.3 Attach the casualty to the descent device and lower him or her to the ground or "
            "through the tower.",
            "8.4 Target: casualty on the ground within 15 minutes of the alarm.",
        ]
    )
    b.h1("9. Training")
    b.para("Working at height and rescue training is refreshed every 2 years; rescue drills take "
           "place twice a year on site.")
    b.h1("10. Revision history")
    b.table(
        ["Revision", "Date", "Change"],
        [
            ["A", "2019-10-01", "First issue."],
            ["B", "2026-04-07", "Tool tethering mandatory above 2 m after near miss INC-2026-003; "
             "hatches closed when passing tools."],
        ],
        widths=(2.5, 3, 11.5),
    )
    return b.render(w, "sop-wah")


def wi_gen_fr(w: World) -> bytes:
    b = DocxBuilder("Contoso Renewables - WI-GEN-014 Rév. A",
                    "WI-GEN-014 Rév. A - Remplacement des balais de la génératrice")
    b.title("WI-GEN-014 - Remplacement des balais de la génératrice",
            "Instruction de travail - Révision A - applicable au 2025-09-15")
    b.table(
        ["Champ", "Valeur"],
        [
            ["Numéro", "WI-GEN-014"],
            ["Révision", "A"],
            ["Date d'application", "2025-09-15"],
            ["Rédigé par", "Élise Ternaux, technicienne éolienne"],
            ["Approuvé par", "Dario Penwarden, superviseur O&M"],
            ["Applicable à", "WTG-01 à WTG-12 (génératrice asynchrone à double alimentation, "
                             "690 V)"],
        ],
        widths=(5, 12),
    )
    b.h1("1. Objet")
    b.para("Cette instruction décrit le contrôle et le remplacement des balais de la génératrice "
           "des éoliennes Litware LT-32 du parc de Quellmoor Ridge.")
    b.h1("2. Sécurité")
    b.bullets(
        [
            "Un PTW est obligatoire. Deux techniciens minimum.",
            "Consigner la génératrice (stator et rotor) selon la procédure SOP-LOTO-001.",
            "Porter des gants, des lunettes et un masque anti-poussière : la poussière de "
            "carbone est conductrice.",
        ]
    )
    b.h1("3. Matériel")
    b.bullets(
        [
            "Jeu de balais LWS-P-51207 (18 balais)",
            "Kit de nettoyage de la bague collectrice LWS-P-55031",
            "Clé dynamométrique 5 à 25 N·m, pied à coulisse, aspirateur industriel",
        ]
    )
    b.h1("4. Critères de remplacement")
    b.para("Remplacer le jeu complet de balais lorsque la longueur restante d'un balai est "
           "inférieure à 18 mm. La longueur d'un balai neuf est de 40 mm. Ne jamais mélanger des "
           "balais neufs et des balais usés sur une même bague.")
    b.para("L'alarme A3210 (Generator brush wear limit reached) apparaît lorsque la longueur "
           "restante atteint environ 20 mm.")
    b.h1("5. Mode opératoire")
    b.steps(
        [
            "5.1 Obtenir le PTW, arrêter l'éolienne et consigner la génératrice.",
            "5.2 Ouvrir le capot du compartiment des bagues collectrices.",
            "5.3 Aspirer la poussière de carbone avant toute intervention.",
            "5.4 Mesurer la longueur de chaque balai au pied à coulisse et noter les valeurs.",
            "5.5 Déposer les porte-balais un par un.",
            "5.6 Nettoyer la bague collectrice avec le kit LWS-P-55031.",
            "5.7 Monter les balais neufs et vérifier qu'ils coulissent librement.",
            "5.8 Serrer les vis du porte-balais au couple de 12 N·m.",
            "5.9 Vérifier la pression des ressorts (repère vert visible).",
            "5.10 Refermer le capot, retirer les outils et déconsigner.",
            "5.11 Rodage : limiter la puissance de l'éolienne à 50 % pendant 8 heures, puis "
            "revenir à la puissance nominale.",
            "5.12 Noter les longueurs mesurées et le numéro de l'ordre de travail.",
        ]
    )
    b.h1("6. Durée")
    b.para("Durée estimée : 3 heures pour deux techniciens, rodage non compris.")
    b.h1("7. Historique des révisions")
    b.table(["Révision", "Date", "Modification"], [["A", "2025-09-15", "Première émission."]],
            widths=(2.5, 3, 11.5))
    return b.render(w, "wi-gen-fr")


# ------------------------------------------------------------------------------------------
# Incident, change and meeting records


def _weekly_a2101(until: str) -> tuple[list[str], list[float], list[int]]:
    """Weekly HSS vibration and A2101 warnings of WTG-07 up to ``until`` (ISO date, inclusive)."""
    rows = [row for row in datasets.vibration_rows() if row["date"] <= until]
    weeks = [row["date"] for row in rows]
    velocity = [float(row["velocity_rms_mm_s"]) for row in rows]
    counts = [0] * len(weeks)
    for event in datasets.scada_rows():
        if event["turbine"] == "WTG-07" and event["code"] == "A2101" and event["state"] == "RAISED":
            day = event["timestamp"][:10]
            if day > until:
                continue
            for index, week in enumerate(weeks):
                if week <= day and (index + 1 == len(weeks) or day < weeks[index + 1]):
                    counts[index] += 1
    return weeks, velocity, counts


def inc_8d(w: World) -> bytes:
    b = DocxBuilder("Contoso Renewables - 8D report INC-2026-006", "INC-2026-006 - 8D report")
    b.title("8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07",
            "Revision of 2026-07-10: D1 to D7 complete, D8 open until the bearing replacement.")
    b.table(
        ["Field", "Value"],
        [
            ["Report number", "INC-2026-006"],
            ["Turbine", "WTG-07 (serial LT32-19-0421, gearbox FGT-3200-18-07752)"],
            ["Opened", "2026-05-30 after the first A2102 trip"],
            ["8D lead", "Yusuf Arkwell, Reliability Engineer"],
        ],
        widths=(5, 12),
    )
    b.h1("D1 - Team")
    b.para("Yusuf Arkwell (lead), Dario Penwarden (O&M Supervisor), Callum Rydings (Lead Wind "
           "Technician), Élise Ternaux (Wind Technician), Katrin Ostermeier (Fabrikam "
           "Getriebetechnik GmbH, remote support) and Imogen Thackwray (Trey Research "
           "Laboratories, oil analysis).")
    b.h1("D2 - Problem description")
    b.para("Between 2026-04-09 and 2026-06-21 WTG-07 logged 27 A2101 warnings (gearbox oil sump "
           "temperature high, 75 °C) and two A2102 trips (82 °C): on 2026-05-30 at 14:12 "
           "(82.6 °C) and on 2026-06-19 at 15:47 (83.4 °C). No other turbine logged an A2101 "
           "warning in the same period.")
    b.para("The HSS bearing vibration (generator side) rose from 2.1 mm/s RMS on 2026-01-05 to "
           "5.2 mm/s RMS on 2026-06-15, above the alarm level of 4.5 mm/s.")
    # The figure only shows data known before the report date (2026-07-10).
    report_day = date.fromisoformat(str(w.doc("inc-8d")["date"]))
    weeks, velocity, counts = _weekly_a2101((report_day - timedelta(days=1)).isoformat())
    b.figure(to_png(wtg07_trend(weeks, velocity, counts), dpi=130), 15.5,
             "Figure 1 - WTG-07: weekly A2101 warnings and HSS bearing vibration (2026)")
    b.h1("D3 - Containment")
    b.para("From 2026-06-01 WTG-07 was limited to 2.6 MW by the park controller and the oil "
           "temperature was checked every day. The limit was removed on 2026-06-25 after the "
           "corrective actions of D6.")
    b.h1("D4 - Root cause analysis (5 Whys)")
    b.steps(
        [
            "Why 1 - Why did the oil overheat? The oil cooler did not reject enough heat at high "
            "load.",
            "Why 2 - Why? The cooler fan ran at reduced speed and the radiator fins were about "
            "40 % blocked by insects and pollen.",
            "Why 3 - Why did the fan run slowly? The bearing of the fan motor LWS-P-30418 had "
            "failed; the motor current was 35 % above nominal.",
            "Why 4 - Why was it not detected earlier? The fan motor current is not monitored by "
            "the SCADA system and the radiator was cleaned only when found dirty.",
            "Why 5 - Why? The maintenance plan followed the manual, which gives no interval for "
            "radiator cleaning ('as required').",
        ]
    )
    b.para("Root cause: missing preventive maintenance of the oil cooler (radiator cleaning and "
           "fan check) allowed a fan motor bearing failure and radiator fouling to reduce the "
           "cooling capacity.", bold=True)
    b.para("Contributing factor: wear of the HSS bearing on the generator side, confirmed by "
           "oil analysis TR-OA-2026-0614 (iron 64 ppm, PQ index 112) and by the vibration trend, "
           "increased the friction losses in the gearbox.")
    b.h1("D5 and D6 - Corrective actions")
    b.table(
        ["Action", "Work order", "Owner", "Date", "Status"],
        [
            ["Replace oil cooler fan motor LWS-P-30418", "WO-26-0398", "Callum Rydings",
             "2026-06-24", "done"],
            ["Clean oil cooler radiator", "WO-26-0399", "Élise Ternaux", "2026-06-24", "done"],
            ["Remove the 2.6 MW limit after verification", "-", "Dario Penwarden", "2026-06-25",
             "done"],
            ["Replace HSS bearing, generator side (FGT-P-22328)", "WO-26-0412", "Callum Rydings",
             "on delivery of the bearing", "waiting for parts"],
        ],
        widths=(6, 2.5, 3, 3, 2.5),
    )
    b.h1("D7 - Prevent recurrence")
    b.bullets(
        [
            "Task MP-GBX-07 'Oil cooler radiator cleaning and fan current check' added to the "
            "maintenance plan for all turbines, every 6 months (issue 2 of 2026-07-01).",
            "Minimum stock of fan motor LWS-P-30418 raised from 1 to 2 (2026-07-01).",
            "Request to Litware Wind Systems to add the fan motor current to the SCADA signals "
            "(ticket LWS-TS-51877, open).",
        ]
    )
    b.para("Verification: no A2101 warning on WTG-07 since 2026-06-24 (SCADA log). The vibration "
           "stays above the alarm level until the bearing is replaced.")
    b.h1("D8 - Closure")
    b.para("Open. The 8D will be closed after WO-26-0412 and an oil sample 500 operating hours "
           "after the bearing replacement.")
    return b.render(w, "inc-8d")


def moc_oil(w: World) -> bytes:
    b = DocxBuilder("Contoso Renewables - MOC-2025-012", "MOC-2025-012 - Management of change")
    b.title("MOC-2025-012 - Gearbox oil grade change to PWG 220",
            "Management of change record - approved 2025-06-18")
    b.table(
        ["Field", "Value"],
        [
            ["MOC number", "MOC-2025-012"],
            ["Raised", "2025-05-06 by Dario Penwarden, O&M Supervisor"],
            ["Type", "Technical change - lubricant"],
            ["Scope", "WTG-01 to WTG-12"],
            ["Reviewed by", "Greta Vollan (HSE Coordinator), Yusuf Arkwell (Reliability Engineer)"],
            ["Decision", "Approved on 2025-06-18 by Maren Ellingsby, Site Manager"],
        ],
        widths=(5, 12),
    )
    b.h1("1. Description of the change")
    b.para("Replace Proseware PWG 320 (ISO VG 320) with Proseware PWG 220 (ISO VG 220) in the "
           "gearboxes of all 12 turbines, as required by service bulletin SB-LWS-2025-07 Rev. A. "
           "Litware support confirmed on 2025-05-20 (ticket LWS-TS-48213) that the bulletin "
           "applies to all 12 CCV turbines of Quellmoor Ridge.")
    b.h1("2. Reason")
    b.para("On 2025-01-21, at -24.6 °C, WTG-02 and WTG-09 needed more than 6 hours of heating "
           "before they could start. The bulletin also makes the change a condition of the "
           "gearbox warranty.")
    b.h1("3. Risk assessment")
    b.table(
        ["Hazard", "Risk", "Control"],
        [
            ["Mixing of oils", "Residual PWG 320 above 5 %", "60 L flush; label the filler; "
             "remove PWG 320 drums from the shelf"],
            ["Cold start", "Wrong start parameter", "Set GBX_TMIN_START to 5 °C and verify it "
             "in the conversion checklist"],
            ["Hot oil and spills", "Burns, environmental spill", "SOP-GBX-010; spill kit; drain "
             "between 40 and 60 °C"],
            ["Availability", "About 6 hours downtime per turbine", "Plan the campaign in low-wind "
             "periods"],
            ["Waste oil", "12 x 470 L of waste oil", "Licensed carrier; check the bund capacity"],
        ],
        widths=(4, 5, 8),
    )
    b.h1("4. Actions")
    b.table(
        ["No.", "Action", "Owner", "Due"],
        [
            ["1", "Revise SOP-GBX-010 to Rev. B", "Dario Penwarden", "2025-08-29"],
            ["2", "Order 36 drums of PWG 220 and set the minimum stock of PWS-220-D208 to 8 "
             "drums", "Tomasz Lebrecht", "2025-08-15"],
            ["3", "Conversion campaign WTG-01 to WTG-12", "Dario Penwarden",
             "2025-09-01 to 2025-11-28"],
            ["4", "Toolbox talk on cold-weather start-up with the new oil", "Dario Penwarden",
             "2025-11-30"],
            ["5", "Update the maintenance plan and the oil sampling schedule", "Yusuf Arkwell",
             "2025-12-15"],
            ["6", "Send the Litware completion form within 30 days of each conversion",
             "Dario Penwarden", "per conversion"],
        ],
        widths=(1.2, 9, 3.5, 3.3),
    )
    b.h1("5. Cost")
    b.para("Estimated cost EUR 58,600 (36 drums of PWG 220, 12 filter elements, labour and waste "
           "oil disposal), within the 2025 maintenance budget.")
    b.h1("6. Approval")
    b.para("Approved by Maren Ellingsby, Site Manager, on 2025-06-18. Implementation is reported "
           "at the monthly O&M review.")
    return b.render(w, "moc-oil")


def _may_kpis() -> tuple[str, str]:
    rows = [row for row in datasets.kpi_rows() if row["month"] == "2026-05"]
    energy = sum(float(row["energy_mwh"]) for row in rows)
    availability = sum(float(row["availability_pct"]) for row in rows) / len(rows)
    return f"{availability:.1f}", f"{energy:,.0f}"


def minutes_june(w: World) -> bytes:
    availability, energy = _may_kpis()
    b = DocxBuilder("Contoso Renewables - Monthly O&M review", "Minutes 2026-06-18")
    b.title("Monthly O&M review - minutes",
            "2026-06-18, 10:00 to 11:30, Quellmoor Ridge O&M building")
    b.para("Chair: Maren Ellingsby (Site Manager). Present: Dario Penwarden, Yusuf Arkwell, "
           "Greta Vollan, Tomasz Lebrecht, Callum Rydings. Apologies: Élise Ternaux.")
    b.h1("1. Safety")
    b.para("No lost-time injury in May. The actions of near miss INC-2026-003 are closed.")
    b.para("Audit AUD-2026-02: F1 closed on 2026-03-27 (all rescue kits inspected), F2 closed "
           "on 2026-03-12, F5 closed on 2026-03-30. F3 is still open: the toolbox talk records "
           "are being reconstructed and the due date moves to 2026-07-31. F4 (oil drum bund) is "
           "open, due 2026-06-30.")
    b.h1("2. Performance in May 2026")
    b.para(f"Park availability {availability} % and energy {energy} MWh. WTG-07 availability "
           "95.2 % because of the gearbox trips.")
    b.h1("3. WTG-07 gearbox over-temperature")
    b.para("8D INC-2026-006 was opened on 2026-05-30. WTG-07 has been limited to 2.6 MW since "
           "2026-06-01. Oil analysis TR-OA-2026-0614 arrived on 2026-06-17 with condition ALERT "
           "(iron 64 ppm). Callum Rydings will inspect the cooler fan and the radiator; the "
           "inspection is planned for 2026-06-24.")
    b.h1("4. Blade inspection")
    b.para("Report WBS-2026-031 arrived on 2026-06-03. WTG-04 blade B has a category 4 "
           "trailing-edge crack and must be replaced before 2026-09-30 (WO-26-0355). A new blade "
           "is ordered from Litware Wind Systems for delivery at the end of August. The crane "
           "lift will be planned with Tailspin Heavy Lift for early September. Monthly drone "
           "checks continue; the next one is on 2026-07-02.")
    b.h1("5. Environment")
    b.para("The bat protection curtailment season started on 1 June for WTG-03, WTG-04 and "
           "WTG-05 (permit condition 7.3). Yusuf Arkwell checked the curtailment settings in the "
           "turbine controllers on 2026-05-28.")
    b.h1("6. Spare parts")
    b.para("There is no HSS bearing FGT-P-22328 in stock since the WTG-10 repair in March. "
           "Tomasz Lebrecht will raise a purchase order for two bearings; the supplier lead time "
           "is about 10 weeks.")
    b.h1("7. Any other business")
    b.para("City Power & Light announced network works on the Skelvane 132 kV circuits in July; "
           "the formal curtailment instruction is expected early July.")
    b.h1("Actions")
    b.table(
        ["No.", "Action", "Owner", "Due"],
        [
            ["1", "Inspect WTG-07 oil cooler fan and radiator", "Callum Rydings", "2026-06-24"],
            ["2", "Purchase order for two HSS bearings FGT-P-22328", "Tomasz Lebrecht",
             "2026-06-22"],
            ["3", "Plan the WTG-04 blade lift with Tailspin Heavy Lift", "Dario Penwarden",
             "2026-07-31"],
            ["4", "Close audit finding F3", "Greta Vollan", "2026-07-31"],
            ["5", "Bund capacity for oil drums (finding F4)", "Tomasz Lebrecht", "2026-06-30"],
        ],
        widths=(1.2, 9, 3.5, 3.3),
    )
    b.para("Next review: 2026-07-16.")
    return b.render(w, "minutes-june")


# ------------------------------------------------------------------------------------------
# IT runbook sample (Relecloud)


def it_runbook(w: World) -> bytes:
    b = DocxBuilder("Relecloud platform operations - RB-TKT-002", "RB-TKT-002 - ticketing-api")
    b.title("RB-TKT-002 - ticketing-api runbook", "Runbook - reviewed 2026-02-09")
    b.table(
        ["Field", "Value"],
        [
            ["Service", "ticketing-api (tier 1)"],
            ["Owner", "Relecloud platform operations; runbook owner Oskar Vennholm"],
            ["Runs on", "Kubernetes, 3 to 12 replicas with autoscaling"],
            ["Depends on", "orders-db (PostgreSQL), notification-worker"],
            ["Connection pool", "50 connections per pod (maximum)"],
        ],
        widths=(5, 12),
    )
    b.h1("1. Alerts")
    b.table(
        ["Alert", "Condition", "Severity"],
        [
            ["TicketingApiHighLatency", "p95 latency above 800 ms for 10 minutes", "SEV2"],
            ["TicketingApiErrorRate", "5xx responses above 2 % for 5 minutes", "SEV2"],
            ["TicketingApiDown", "no healthy pod for 2 minutes", "SEV1"],
            ["TicketingApiPoolSaturation", "connection pool above 90 % for 5 minutes", "SEV3"],
        ],
        widths=(6, 8, 3),
    )
    b.h1("2. First checks")
    b.steps(
        [
            "2.1 Check the deployment history of the last 2 hours; roll back a suspicious "
            "release first.",
            "2.2 Check the orders-db dashboard: connections, replication lag, slow queries.",
            "2.3 Check the pod restarts and memory of ticketing-api.",
        ]
    )
    b.h1("3. Actions")
    b.steps(
        [
            "3.1 Scale out to 6 replicas if latency is high and the database is healthy.",
            "3.2 Restart pods one by one if the connection pools are stuck.",
            "3.3 If orders-db is unavailable, page the database administrator on call; a "
            "failover follows PRC-DB-007 after the incident commander decides it.",
        ]
    )
    b.h1("4. Escalation")
    b.para("On-call SRE first, then the database administrator on call, then the engineering "
           "manager for SEV1 incidents. See the on-call handbook for response times.")
    return b.render(w, "it-runbook")


def it_postmortem(w: World) -> bytes:
    b = DocxBuilder("Relecloud platform operations - PM-2026-014", "PM-2026-014 - postmortem")
    b.title("PM-2026-014 - checkout outage postmortem", "Blameless postmortem - 2026-03-17")
    b.table(
        ["Field", "Value"],
        [
            ["Incident date", "2026-03-12"],
            ["Duration", "14:05 to 14:52 UTC (47 minutes)"],
            ["Severity", "SEV2"],
            ["Incident commander", "Jun Hallgarth, Engineering Manager"],
            ["Impact", "18 % of checkout requests failed; orders were retried by customers"],
        ],
        widths=(5, 12),
    )
    b.h1("Summary")
    b.para("A configuration change had reduced the maximum connection pool of checkout-web from "
           "50 to 20 connections per pod. When a campaign started at 14:00 the pools were "
           "exhausted and checkout requests timed out.")
    b.h1("Timeline (UTC)")
    b.bullets(
        [
            "14:00 campaign e-mail sent; traffic triples.",
            "14:05 first checkout timeouts.",
            "14:09 TicketingApiErrorRate alert pages the on-call SRE.",
            "14:31 connection pool exhaustion identified.",
            "14:44 configuration rolled back to 50 connections per pod.",
            "14:52 error rate back to normal.",
        ]
    )
    b.h1("Root cause")
    b.para("The pool size was changed in a refactoring pull request without load testing. The "
           "runbook RB-TKT-002 documents 50 connections per pod but the value was not validated "
           "in the deployment pipeline.")
    b.h1("Action items")
    b.table(
        ["No.", "Action", "Owner", "Due"],
        [
            ["1", "Validate connection pool settings in the deployment pipeline", "Oskar Vennholm",
             "2026-04-15"],
            ["2", "Add a pool saturation alert to checkout-web", "Oskar Vennholm", "2026-03-31"],
            ["3", "Load test before campaigns", "Jun Hallgarth", "2026-04-30"],
        ],
        widths=(1.2, 9, 3.5, 3.3),
    )
    return b.render(w, "it-postmortem")
