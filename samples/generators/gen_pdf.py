"""Text-layer PDF documents (OEM manual, bulletins, reports, permits, IT procedure)."""

from __future__ import annotations

from .common import DocMeta, meta_for
from .datasets import WTG07_OIL_SAMPLES
from .diagrams import blade_defects, gearbox_exploded, oil_trend, to_svg
from .pdfdoc import StampedPDF
from .world import World


def _pdf(w: World, doc_id: str, header_left: str, footer_left: str = "") -> StampedPDF:
    doc = w.doc(doc_id)
    meta: DocMeta = meta_for(doc, w.org_name(str(doc["organisation"])))
    pdf = StampedPDF(meta, header_left, footer_left or str(doc.get("doc_number") or ""))
    pdf.add_page()
    return pdf


# ------------------------------------------------------------------------------------------
# OEM documentation


def manual_gbx(w: World) -> bytes:
    pdf = _pdf(w, "manual-gbx", "Litware Wind Systems - LT-32 maintenance manual",
               "LWS-MM-GBX-32 Rev. D")
    pdf.title_block(
        "Litware LT-32 wind turbine - Maintenance manual",
        "Chapter 4 - Gearbox (excerpt). Document LWS-MM-GBX-32 Rev. D, issued 2024-03-15 by "
        "Litware Wind Systems.",
    )
    pdf.grid(
        ["Field", "Value"],
        [
            ["Document number", "LWS-MM-GBX-32"],
            ["Revision", "D"],
            ["Issue date", "2024-03-15"],
            ["Applies to", "LT-32 turbines (all variants) with Fabrikam FGT-3200 gearbox"],
            ["Previous revision", "Rev. C of 2021-06-30 (withdrawn)"],
            ["Language", "English (original)"],
        ],
        widths=(45, 129),
    )
    pdf.note(
        "SAFETY",
        "Work on the gearbox requires the turbine to be stopped, the rotor locked and the "
        "drivetrain isolated according to the operator's lockout procedure. Hot oil up to 80 °C "
        "can cause burns. Wear the personal protective equipment defined by the site.",
    )
    pdf.h1("Contents of this excerpt")
    pdf.bullets(
        [
            "4.1 Gearbox description",
            "4.2 Lubrication",
            "4.3 Oil change (overview)",
            "4.4 Inspection and condition monitoring",
            "4.5 Troubleshooting of gearbox alarms",
        ]
    )
    pdf.para(
        "Changes to the content of this chapter are published by Litware Wind Systems as service "
        "bulletins. Always check the bulletin register before planning gearbox work."
    )

    pdf.add_page()
    pdf.h1("4.1 Gearbox description")
    pdf.para(
        "The LT-32 uses a Fabrikam FGT-3200 three-stage gearbox: one planetary stage followed by "
        "two parallel helical stages. The overall ratio is 1:118.4. At the rated rotor speed of "
        "12.7 rpm the output pinion shaft drives the generator at 1,500 rpm. The rated input "
        "torque is 2,410 kNm and the dry mass of the gearbox is 21.6 t."
    )
    pdf.para(
        "The gearbox is lubricated by splash and by forced lubrication. A shaft-driven pump "
        "supplies the bearings and gear meshes during operation; an electric pump runs during "
        "start-up and flushing. The oil passes an inline filter (10 micron) and an air/oil cooler "
        "with an electric fan. A thermostatic valve sends the oil through the cooler above 45 °C. "
        "Three immersion heaters (3 x 1.5 kW) warm the oil sump before a cold start."
    )
    pdf.figure(to_svg(gearbox_exploded()), 122,
               "Figure 4-1 - Exploded view of the FGT-3200 gearbox (item numbers in table 4-1)")
    pdf.para("Table 4-1 - Parts shown in figure 4-1.", size=8.5, style="I")
    pdf.grid(
        ["Item", "Description", "Spare part number"],
        [
            ["1", "Housing cover, rotor side", "-"],
            ["2", "Planet carrier with three planet gears", "-"],
            ["3", "Ring gear", "-"],
            ["4", "Sun pinion shaft", "-"],
            ["5", "Second-stage gear wheel", "-"],
            ["6", "Intermediate pinion shaft", "-"],
            ["7", "IMS bearing set", "FGT-P-21904"],
            ["8", "Output pinion shaft", "-"],
            ["9", "HSS bearing, rotor side", "FGT-P-22331"],
            ["10", "HSS bearing, generator side", "FGT-P-22328"],
            ["11", "Oil cooler with fan motor 1.5 kW", "LWS-P-30418 (fan motor)"],
            ["12", "Thermostatic valve insert", "LWS-P-30422"],
            ["13", "Oil filter element, 10 micron", "FGT-P-11872"],
            ["14", "Breather with desiccant", "FGT-P-11880"],
            ["15", "Oil level sight glass", "FGT-P-13010"],
            ["16", "Oil sampling valve", "FGT-P-14002"],
        ],
        widths=(14, 100, 60),
        size=8,
    )

    pdf.add_page()
    pdf.h1("4.2 Lubrication")
    pdf.para(
        "Only the lubricant listed in table 4-2 is approved for the FGT-3200 gearbox. Do not mix "
        "lubricants of different brands or viscosity grades."
    )
    pdf.grid(
        ["Item", "Specification"],
        [
            ["Gear oil", "Proseware PWG 320"],
            ["Viscosity grade", "ISO VG 320"],
            ["Base oil", "synthetic PAO"],
            ["Total oil volume", "410 L (gearbox sump 330 L + cooling and filter circuit 80 L)"],
            ["Oil change interval", "5 years, or earlier when the laboratory analysis requires it"],
            ["Oil sampling interval", "6 months"],
            ["Filter element FGT-P-11872", "replace every 12 months or at alarm A2140"],
            ["Breather FGT-P-11880", "replace every 12 months"],
        ],
        widths=(55, 119),
    )
    pdf.para("Table 4-2 - Lubricant specification.", size=8.5, style="I")
    pdf.h2("Operating temperatures")
    pdf.grid(
        ["Parameter", "Value"],
        [
            ["Normal oil sump temperature in operation", "50 to 65 °C"],
            ["Thermostatic valve opening (cooler circuit)", "45 °C"],
            ["Warning A2101 - oil sump temperature high", "75 °C"],
            ["Trip A2102 - oil sump temperature trip", "82 °C"],
            ["Minimum oil sump temperature before start-up", "+10 °C (heaters on below +10 °C)"],
        ],
        widths=(105, 69),
    )
    pdf.para("Table 4-3 - Gearbox oil temperatures.", size=8.5, style="I")
    pdf.para(
        "The turbine controller blocks the start of the drivetrain until the oil sump has reached "
        "the minimum start-up temperature. Do not bypass the start inhibit."
    )

    pdf.h1("4.3 Oil change (overview)")
    pdf.para(
        "The detailed oil change procedure is defined by the operator. The OEM requirements are:"
    )
    pdf.bullets(
        [
            "Stop the turbine, lock the rotor and isolate the drivetrain.",
            "Drain the oil at an oil temperature between 40 and 60 °C so that deposits drain "
            "with the oil.",
            "Replace the filter element FGT-P-11872 and inspect the magnetic plug.",
            "Fill only through a filter cart with a 10 micron element.",
            "Check the level at the sight glass after 20 minutes of standstill.",
            "Take a reference oil sample after 24 hours of operation.",
        ],
        numbered=True,
    )
    pdf.grid(
        ["Joint", "Thread", "Tightening torque"],
        [
            ["Drain plug", "M48 x 2", "280 Nm"],
            ["Filter housing cover screws", "M12", "85 Nm"],
            ["Oil cooler hose flange screws", "M16", "210 Nm"],
            ["Sight glass retaining screws", "M8", "22 Nm"],
        ],
        widths=(80, 40, 54),
    )
    pdf.para("Table 4-4 - Tightening torques for oil change work.", size=8.5, style="I")

    pdf.add_page()
    pdf.h1("4.4 Inspection and condition monitoring")
    pdf.grid(
        ["Task", "Interval"],
        [
            ["Visual inspection and leak check", "6 months"],
            ["Oil sampling and laboratory analysis", "6 months"],
            ["Endoscope inspection of gear teeth and bearings", "24 months"],
            ["Vibration monitoring (condition monitoring system)", "continuous"],
            ["Filter element replacement", "12 months"],
            ["Oil cooler radiator cleaning", "as required"],
        ],
        widths=(120, 54),
    )
    pdf.para("Table 4-5 - Inspection intervals.", size=8.5, style="I")
    pdf.h2("Oil analysis limits")
    pdf.grid(
        ["Parameter", "Alert", "Alarm"],
        [
            ["Iron (Fe)", "50 ppm", "100 ppm"],
            ["Copper (Cu)", "25 ppm", "50 ppm"],
            ["Silicon (Si)", "15 ppm", "25 ppm"],
            ["Water", "300 ppm", "500 ppm"],
            ["Viscosity change at 40 °C", "+/- 10 %", "+/- 15 %"],
            ["PQ index", "60", "120"],
            ["Cleanliness ISO 4406 (target 17/15/12)", "19/17/14", "21/19/16"],
        ],
        widths=(94, 40, 40),
    )
    pdf.para("Table 4-6 - Oil analysis limits.", size=8.5, style="I")
    pdf.h2("Vibration limits")
    pdf.para(
        "For the output stage bearings (HSS bearings, rotor side and generator side) the velocity "
        "RMS limits are 3.5 mm/s (alert) and 4.5 mm/s (alarm). Above the alarm level, plan a "
        "bearing inspection and reduce load if the trend keeps rising."
    )

    pdf.add_page()
    pdf.h1("4.5 Troubleshooting of gearbox alarms")
    pdf.grid(
        ["Code", "Message", "Possible causes", "Checks and actions"],
        [
            ["A2101", "Gearbox oil sump temperature high (75 °C)",
             "Cooler fan motor fault or reduced fan speed; radiator fins blocked; thermostatic "
             "valve insert stuck; low oil level; full load at high ambient temperature; bearing "
             "damage",
             "Check fan rotation and motor current; clean the radiator; check valve insert "
             "LWS-P-30422; check the oil level; review the vibration trend; take an oil sample"],
            ["A2102", "Gearbox oil sump temperature trip (82 °C)",
             "As for A2101; the turbine stops automatically",
             "Inspect the cooling circuit before restart; do not reset more than once without "
             "inspection"],
            ["A2110", "Gearbox HSS bearing temperature high (90 °C)",
             "Bearing damage; lubrication starvation",
             "Check the vibration trend; endoscope inspection of the bearing"],
            ["A2120", "Gearbox oil pressure low (0.8 bar)",
             "Cold oil at start-up; pump fault; filter blocked",
             "Allow heater time at cold start; check the pump and the filter"],
            ["A2130", "Gearbox oil level low", "Leak at seals, hoses or plugs",
             "Find and repair the leak; top up with the approved oil"],
            ["A2140", "Gearbox oil filter differential pressure high (2.5 bar)",
             "Filter element clogged; cold oil", "Replace filter element FGT-P-11872"],
        ],
        widths=(16, 40, 56, 62),
        size=8,
    )
    pdf.para("Table 4-7 - Gearbox alarms.", size=8.5, style="I")
    pdf.para("End of excerpt.", style="I")
    return pdf.render()


def sb_oil(w: World) -> bytes:
    pdf = _pdf(w, "sb-oil", "Litware Wind Systems - Service bulletin", "SB-LWS-2025-07 Rev. A")
    pdf.title_block(
        "SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines",
        "Service bulletin issued by Litware Wind Systems on 2025-03-14.",
    )
    pdf.grid(
        ["Field", "Value"],
        [
            ["Bulletin number", "SB-LWS-2025-07"],
            ["Revision", "A"],
            ["Issue date", "2025-03-14"],
            ["Category", "Recommended; mandatory to keep the gearbox warranty"],
            ["Applies to", "LT-32 turbines delivered in CCV configuration with Fabrikam FGT-3200 "
                           "gearboxes (all serial numbers), and LT-32 standard turbines at sites "
                           "where the ambient temperature regularly falls below -20 °C"],
            ["Affected document", "LWS-MM-GBX-32 Rev. D, section 4.2 (lubrication)"],
            ["Compliance", "At the next scheduled oil change and no later than 2025-12-31"],
        ],
        widths=(40, 134),
    )
    pdf.h1("1. Reason")
    pdf.para(
        "Field reports from cold sites show long heating times before start-up (more than 6 "
        "hours at -25 °C ambient) and filter bypass events with ISO VG 320 oil. A lower viscosity "
        "grade shortens the start-up time and keeps the filter element in service."
    )
    pdf.h1("2. Change")
    pdf.para(
        "This bulletin amends the lubricant specification in section 4.2 of LWS-MM-GBX-32 Rev. D "
        "for the turbines listed under 'Applies to':"
    )
    pdf.grid(
        ["Item", "LWS-MM-GBX-32 Rev. D", "After this bulletin"],
        [
            ["Gear oil", "Proseware PWG 320", "Proseware PWG 220"],
            ["Viscosity grade", "ISO VG 320", "ISO VG 220"],
            ["Total oil volume", "410 L", "410 L (unchanged)"],
            ["Minimum oil sump temperature before start-up", "+10 °C", "+5 °C"],
            ["Warning A2101 / trip A2102", "75 °C / 82 °C", "75 °C / 82 °C (unchanged)"],
        ],
        widths=(74, 50, 50),
    )
    pdf.h1("3. Instructions")
    pdf.bullets(
        [
            "Stop the turbine and isolate the drivetrain according to the site lockout procedure.",
            "Drain the PWG 320 at an oil temperature between 40 and 60 °C.",
            "Replace the oil filter element FGT-P-11872.",
            "Flush the gearbox with 60 L of PWG 220: fill, run the electric oil pump for 30 "
            "minutes, then drain.",
            "Fill with 410 L of PWG 220 through a filter cart with a 10 micron element.",
            "The residual PWG 320 after flushing must not exceed 5 % of the total oil volume.",
            "Change the controller parameter GBX_TMIN_START from 10 to 5 °C.",
            "Label the gearbox filler 'PWG 220' with the label kit supplied.",
            "Take a reference oil sample after 24 hours of operation.",
        ],
        numbered=True,
    )
    pdf.h1("4. Parts and labour")
    pdf.grid(
        ["Item", "Quantity per turbine"],
        [
            ["Proseware PWG 220 (60 L flush + 410 L fill)", "470 L"],
            ["Oil filter element FGT-P-11872", "1"],
            ["Label kit 'PWG 220'", "1"],
            ["Labour", "2 technicians, about 6 hours"],
        ],
        widths=(120, 54),
    )
    pdf.h1("5. Reporting")
    pdf.para(
        "Return the completion form (annex B) to Litware Wind Systems within 30 days of each "
        "conversion. Conversions made according to this bulletin keep the gearbox warranty valid."
    )
    pdf.h2("Annex B - Completion form")
    pdf.grid(
        ["Field", "Entry"],
        [
            ["Turbine serial number", ""],
            ["Gearbox serial number", ""],
            ["Conversion date", ""],
            ["PWG 220 batch number", ""],
            ["Estimated residual PWG 320 (%)", ""],
            ["Technician name and signature", ""],
        ],
        widths=(80, 94),
    )
    return pdf.render()


def _sb_pitch(w: World, doc_id: str, revision: str) -> bytes:
    is_b = revision == "B"
    pdf = _pdf(w, doc_id, "Litware Wind Systems - Service bulletin",
               f"SB-LWS-2025-11 Rev. {revision}")
    date = "2026-09-04" if is_b else "2025-10-06"
    pdf.title_block(
        f"SB-LWS-2025-11 Rev. {revision} - Pitch bearing bolt re-torque",
        f"Service bulletin issued by Litware Wind Systems on {date}.",
    )
    torque = "1,380 Nm" if is_b else "1,450 Nm"
    rows = [
        ["Bulletin number", "SB-LWS-2025-11"],
        ["Revision", revision],
        ["Issue date", date],
        ["Category", "Mandatory"],
        ["Applies to", "LT-32 turbines, all variants (M30 10.9 pitch bearing bolts, 72 per blade "
                       "bearing, 216 per turbine)"],
        ["Compliance", "At the next 12-month service"],
    ]
    if is_b:
        rows.append(["Supersedes", "SB-LWS-2025-11 Rev. A of 2025-10-06"])
    pdf.grid(["Field", "Value"], rows, widths=(40, 134))
    if is_b:
        pdf.note(
            "REVISION B",
            "This revision supersedes SB-LWS-2025-11 Rev. A. The re-torque value changes from "
            "1,450 Nm to 1,380 Nm.",
        )
    pdf.h1("1. Reason")
    if is_b:
        pdf.para(
            "Laboratory tests on bolts re-torqued according to Rev. A showed that 1,450 Nm "
            "combined with the factory-lubricated washers overloads the M30 bolts. Rev. B lowers "
            "the re-torque value and introduces a lubricated washer kit."
        )
    else:
        pdf.para(
            "Loose pitch bearing bolts were found on two LT-32 turbines at another site after "
            "three years of operation. A one-time re-torque of all bolts restores the preload."
        )
    pdf.h1("2. Instructions")
    steps = [
        "Stop the turbine, lock the rotor and isolate the pitch system.",
        "Use a hydraulic torque wrench calibrated within the last 12 months (accuracy +/- 3 %).",
        f"Re-torque 100 % of the pitch bearing bolts to {torque} in the cross pattern of the "
        "bolt map, blade by blade.",
        "Mark each bolt with a paint line after re-torque.",
    ]
    if is_b:
        steps.insert(2, "Fit the lubricated washer kit LWS-P-60477 under the nuts where washers "
                        "are damaged or missing.")
        steps.append("Replace any bolt that turns more than 30 degrees before reaching the torque.")
    else:
        steps.append("Record every bolt that turns more than 60 degrees before reaching the torque "
                     "and report it to Litware Wind Systems.")
    pdf.bullets(steps, numbered=True)
    pdf.h1("3. Records")
    pdf.para(
        "Record the turbine, blade, torque wrench serial number and the bolts that turned on the "
        "re-torque form and return it to Litware Wind Systems within 60 days."
    )
    if is_b:
        pdf.h2("Summary of changes")
        pdf.grid(
            ["Item", "Rev. A (2025-10-06)", "Rev. B (2026-09-04)"],
            [
                ["Re-torque value", "1,450 Nm", "1,380 Nm"],
                ["Washers", "factory washers", "lubricated washer kit LWS-P-60477 where needed"],
                ["Bolt turned during re-torque", "report above 60 degrees",
                 "replace above 30 degrees"],
            ],
            widths=(58, 58, 58),
        )
    return pdf.render()


def sb_pitch_a(w: World) -> bytes:
    return _sb_pitch(w, "sb-pitch-a", "A")


def sb_pitch_b(w: World) -> bytes:
    return _sb_pitch(w, "sb-pitch-b", "B")


# ------------------------------------------------------------------------------------------
# Lab and inspection


def oil_lab(w: World) -> bytes:
    pdf = _pdf(w, "oil-lab", "Trey Research Laboratories - Oil analysis report", "TR-OA-2026-0614")
    pdf.title_block("Oil analysis report TR-OA-2026-0614", "Gearbox oil - WTG-07 - Quellmoor Ridge")
    pdf.grid(
        ["Field", "Value"],
        [
            ["Customer", "Contoso Renewables, Quellmoor Ridge Wind Farm"],
            ["Asset", "WTG-07 main gearbox, Fabrikam FGT-3200, serial FGT-3200-18-07752"],
            ["Lubricant", "Proseware PWG 220 (ISO VG 220), in service since 2025-10-15"],
            ["Sample ID", "TR-26-11873"],
            ["Sampled", "2026-06-10 by Callum Rydings (sampling valve, oil at operating "
                        "temperature)"],
            ["Received / reported", "2026-06-12 / 2026-06-17"],
            ["Analyst", "Imogen Thackwray, Senior Lubrication Analyst"],
        ],
        widths=(40, 134),
    )
    pdf.note("OVERALL CONDITION", "ALERT - action required")
    pdf.grid(
        ["Test", "Method", "Result", "Unit", "Alert limit", "Status"],
        [
            ["Viscosity at 40 °C", "kinematic", "229", "mm²/s", "198 to 242", "normal"],
            ["Viscosity at 100 °C", "kinematic", "26.1", "mm²/s", "-", "normal"],
            ["Water", "coulometric titration", "180", "ppm", "300", "normal"],
            ["Total acid number", "titration", "0.9", "mg KOH/g", "1.5", "normal"],
            ["Iron (Fe)", "ICP", "64", "ppm", "50", "ALERT"],
            ["Copper (Cu)", "ICP", "7", "ppm", "25", "normal"],
            ["Chromium (Cr)", "ICP", "2", "ppm", "10", "normal"],
            ["Silicon (Si)", "ICP", "9", "ppm", "15", "normal"],
            ["PQ index", "ferrous debris", "112", "-", "60", "ALERT"],
            ["Particle count", "ISO 4406", "20/18/15", "code", "19/17/14", "ALERT"],
        ],
        widths=(36, 30, 22, 22, 34, 30),
    )
    pdf.h1("Comments")
    pdf.para(
        "Ferrous wear has increased sharply since the previous sample (TR-OA-2026-0241 of "
        "2026-03-17: Fe 31 ppm, PQ index 44). Large ferrous particles (PQ index 112) together "
        "with normal copper indicate rolling-element bearing distress rather than gear wear. "
        "Viscosity and water content are normal for PWG 220."
    )
    pdf.h1("Recommendations")
    pdf.bullets(
        [
            "Review the vibration trend of the output stage bearings.",
            "Inspect the HSS bearings by endoscope.",
            "Replace the filter element and resample within 30 days.",
        ],
        numbered=True,
    )
    pdf.add_page()
    pdf.h1("Trend")
    pdf.figure(to_svg(oil_trend(WTG07_OIL_SAMPLES)), 160,
               "Figure 1 - Iron and PQ index of the WTG-07 gearbox oil")
    pdf.grid(
        ["Sample date", "Report", "Oil", "Fe (ppm)", "PQ index", "Viscosity 40 °C", "Status"],
        [
            [s["date"], s["report"], s["oil"], s["fe"], s["pq"], s["visc40"], s["status"]]
            for s in WTG07_OIL_SAMPLES
        ],
        widths=(26, 32, 22, 20, 22, 28, 24),
    )
    pdf.para(
        "Results relate only to the sample received. Report approved by Imogen Thackwray, "
        "Senior Lubrication Analyst, Trey Research Laboratories."
    )
    return pdf.render()


def blade_inspection(w: World) -> bytes:
    pdf = _pdf(w, "blade-inspection", "Wingtip Blade Services - Blade inspection report",
               "WBS-2026-031")
    pdf.title_block("Blade inspection report WBS-2026-031", "Quellmoor Ridge Wind Farm - May 2026")
    pdf.grid(
        ["Field", "Value"],
        [
            ["Client", "Contoso Renewables"],
            ["Site", "Quellmoor Ridge Wind Farm, 12 x Litware LT-32, 36 blades of 57.5 m"],
            ["Inspection dates", "2026-05-18 to 2026-05-22"],
            ["Method", "Drone visual inspection (three passes per blade) and ground photography"],
            ["Report date", "2026-06-03"],
            ["Lead inspector", "Leilani Hartfield"],
        ],
        widths=(40, 134),
    )
    pdf.h1("1. Summary")
    pdf.para(
        "36 blades were inspected. One finding is category 4 (WTG-04 blade B), four findings are "
        "category 3 and eleven blades show category 2 damage. All other blades are category 0 or "
        "1."
    )
    pdf.grid(
        ["Category", "Meaning", "Required action"],
        [
            ["0", "No damage", "none"],
            ["1", "Cosmetic", "none"],
            ["2", "Minor", "monitor at the next inspection"],
            ["3", "Significant", "repair within 6 months"],
            ["4", "Serious", "repair or replace within 3 months; monthly drone check"],
            ["5", "Critical", "stop the turbine"],
        ],
        widths=(24, 40, 110),
    )
    pdf.grid(
        ["Turbine", "Blade A", "Blade B", "Blade C", "Highest"],
        [
            ["WTG-01", "1", "1", "2", "2"],
            ["WTG-02", "1", "2", "1", "2"],
            ["WTG-03", "2", "1", "1", "2"],
            ["WTG-04", "2", "4", "2", "4"],
            ["WTG-05", "1", "1", "1", "1"],
            ["WTG-06", "2", "1", "1", "2"],
            ["WTG-07", "1", "2", "1", "2"],
            ["WTG-08", "3", "1", "2", "3"],
            ["WTG-09", "1", "1", "3", "3"],
            ["WTG-10", "1", "2", "1", "2"],
            ["WTG-11", "2", "1", "3", "3"],
            ["WTG-12", "1", "1", "2", "2"],
        ],
        widths=(34, 35, 35, 35, 35),
    )
    pdf.add_page()
    pdf.h1("2. Detailed findings")
    pdf.h2("F-01 - WTG-04 blade B - trailing-edge crack - category 4")
    pdf.para(
        "Blade serial LB575-19-1187. A trailing-edge crack 0.9 m long runs along the bond line "
        "between radius 37.6 m and 38.5 m, close to the spar cap. Repair is not recommended at "
        "this location. Replace blade B before 2026-09-30. Until the replacement, check the crack "
        "by drone every month and stop the turbine immediately if the crack exceeds 1.2 m."
    )
    pdf.h2("F-02 - WTG-04 blade B - leading-edge erosion - category 3")
    pdf.para("Coating loss between radius 52 m and 57 m; laminate not exposed.")
    pdf.figure(
        to_svg(
            blade_defects(
                "WTG-04 blade B",
                57.5,
                [
                    {"r0": 37.6, "r1": 38.5, "edge": "TE", "cat": 4,
                     "label": "TE crack 0.9 m (cat. 4)"},
                    {"r0": 52.0, "r1": 57.0, "edge": "LE", "cat": 3,
                     "label": "LE erosion (cat. 3)"},
                ],
            )
        ),
        165,
        "Figure 1 - Findings F-01 and F-02 on WTG-04 blade B",
    )
    pdf.h2("F-03 - WTG-08 blade A - lightning receptor damage - category 3")
    pdf.para(
        "The tip receptor is burnt. Replace the receptor within 6 months and check the continuity "
        "of the down conductor."
    )
    pdf.figure(
        to_svg(
            blade_defects(
                "WTG-08 blade A",
                57.5,
                [{"r0": 56.6, "r1": 57.4, "edge": "LE", "cat": 3, "label": "receptor (cat. 3)"}],
            )
        ),
        165,
        "Figure 2 - Finding F-03 on WTG-08 blade A",
    )
    pdf.h2("F-04 - WTG-09 blade C - leading-edge erosion - category 3")
    pdf.para("Erosion between radius 50 m and 57 m with laminate exposed over 0.3 m. Leading-edge "
             "repair within 6 months.")
    pdf.h2("F-05 - WTG-11 blade C - root gelcoat crack - category 3")
    pdf.para("Gelcoat crack at radius 3.2 m. Repair within 6 months and check at the next "
             "inspection.")
    pdf.h1("3. Recommendations")
    pdf.bullets(
        [
            "Replace WTG-04 blade B before 2026-09-30 (crane lift required).",
            "Repair the category 3 findings within 6 months (rope access).",
            "Next full inspection: May 2027.",
        ]
    )
    pdf.para("Report prepared by Leilani Hartfield, Lead Blade Inspector, Wingtip Blade Services.")
    return pdf.render()


# ------------------------------------------------------------------------------------------
# Compliance


def env_permit(w: World) -> bytes:
    pdf = _pdf(w, "env-permit", "Skelvane District Environmental Authority", "EP-2018-0417")
    pdf.title_block(
        "Environmental permit EP-2018-0417 - Quellmoor Ridge Wind Farm",
        "Consolidated version incorporating variation 1 (2020-03-02) and variation 2 "
        "(2024-12-10).",
    )
    pdf.grid(
        ["Field", "Value"],
        [
            ["Permit holder", "Contoso Renewables"],
            ["Installation", "Quellmoor Ridge Wind Farm, 12 wind turbines WTG-01 to WTG-12, "
                             "38.4 MW"],
            ["Original issue", "2018-11-20"],
            ["Variation 1", "2020-03-02 - automatic shadow flicker control"],
            ["Variation 2", "2024-12-10 - bat protection curtailment (condition 7.3)"],
            ["Issued by", "Skelvane District Environmental Authority"],
        ],
        widths=(40, 134),
    )
    pdf.h1("Part 1 - General conditions")
    pdf.bullets(
        [
            "1.1 The installation shall be operated as described in the permit application.",
            "1.2 The permit holder shall notify the Authority of any change to the number or "
            "type of turbines before the change is made.",
            "1.3 A copy of this permit shall be kept at the site.",
        ]
    )
    pdf.h1("Part 6 - Noise and shadow flicker")
    pdf.bullets(
        [
            "6.1 The noise from the wind farm at the dwellings of Quellmoor shall not exceed "
            "40 dB(A) (LA90, 10 minutes) at night between 23:00 and 07:00 and 45 dB(A) during "
            "the day, at hub-height wind speeds up to 12 m/s.",
            "6.2 Shadow flicker at any dwelling shall not exceed 30 hours per year and 30 "
            "minutes per day. An automatic shadow flicker control shall be used.",
        ]
    )
    pdf.add_page()
    pdf.h1("Part 7 - Ecology")
    pdf.bullets(
        [
            "7.1 Bat activity shall be monitored at the nacelle of WTG-04 with an acoustic "
            "detector from April to October each year.",
            "7.2 The results of the monitoring shall be reported in the annual environmental "
            "report.",
            "7.3 Bat protection curtailment: from 1 June to 31 August each year, turbines "
            "WTG-03, WTG-04 and WTG-05 shall be stopped between 22:00 and 05:00 local time "
            "whenever the wind speed at hub height is below 6.0 m/s and the air temperature is "
            "10 °C or higher.",
            "7.4 The curtailment shall be implemented automatically by the turbine control "
            "system and each curtailment period shall be recorded in the turbine event log.",
            "7.5 Records of curtailment shall be kept for 5 years and summarised in an annual "
            "report submitted to the Authority by 31 January of the following year.",
            "7.6 The Authority may adjust the thresholds of condition 7.3 after three years of "
            "monitoring data.",
        ]
    )
    pdf.para(
        "Reason for variation 2: the woodland of Skelvane Wood, east of WTG-03, WTG-04 and "
        "WTG-05, holds a maternity roost of a protected bat species that forages near the "
        "turbines on warm, calm summer nights."
    )
    pdf.h1("Part 8 - Ice")
    pdf.bullets(
        [
            "8.1 Turbines shall stop automatically when ice is detected on the rotor blades and "
            "shall restart only when the ice has gone.",
            "8.2 Warning signs about falling ice shall be placed at all access points at a "
            "distance of 300 m from the turbines from November to March.",
        ]
    )
    pdf.h1("Part 9 - Pollution prevention")
    pdf.bullets(
        [
            "9.1 A spill kit shall be kept in each turbine and in the O&M building.",
            "9.2 Oil spills of more than 20 L outside a turbine shall be reported to the "
            "Authority within 24 hours.",
            "9.3 Oil drums shall be stored in a bunded area with a capacity of at least 110 % "
            "of the largest container or 25 % of the total stored volume, whichever is larger.",
            "9.4 Waste oil shall be collected by a licensed carrier.",
        ]
    )
    pdf.h1("Part 10 - Reporting and contacts")
    pdf.bullets(
        [
            "10.1 The annual environmental report shall be submitted by 31 January.",
            "10.2 Incidents with an effect on the environment shall be notified within 24 hours.",
            "10.3 Contact at the Authority: the Permitting Officer for the Skelvane district.",
        ]
    )
    pdf.para("For the Skelvane District Environmental Authority - Siobhan Carrick, Permitting "
             "Officer - 2024-12-10.")
    return pdf.render()


def grid_instruction(w: World) -> bytes:
    pdf = _pdf(w, "grid-instruction", "City Power & Light - Network Control", "CPL-CI-2026-018")
    pdf.title_block("Curtailment instruction CPL-CI-2026-018", "Planned network outage")
    pdf.grid(
        ["Field", "Value"],
        [
            ["Issued", "2026-07-02 10:15"],
            ["To", "Contoso Renewables, Quellmoor Ridge Wind Farm"],
            ["Connection point", "Skelvane 132 kV substation, circuit 2"],
            ["Reason", "Planned maintenance of Skelvane 132 kV circuit 1; the network runs on a "
                       "single circuit"],
        ],
        widths=(40, 134),
    )
    pdf.h1("Instruction")
    pdf.para(
        "Limit the active power export at the connection point to 20 MW on 14, 15 and 16 July "
        "2026, each day from 08:00 to 18:00 local time."
    )
    pdf.grid(
        ["Date", "From", "To", "Export limit"],
        [
            ["2026-07-14", "08:00", "18:00", "20 MW"],
            ["2026-07-15", "08:00", "18:00", "20 MW"],
            ["2026-07-16", "08:00", "18:00", "20 MW"],
        ],
        widths=(50, 40, 40, 44),
    )
    pdf.bullets(
        [
            "When the limit ends, restore the export with a ramp rate of at most 5 MW per minute.",
            "Acknowledge this instruction within 48 hours.",
            "Export above the limit by more than 1 MW for more than 5 minutes will be reported.",
            "Network Control may extend the outage; any extension is confirmed by phone and in "
            "writing.",
        ]
    )
    pdf.h1("Acknowledgement")
    pdf.para("Acknowledged for Contoso Renewables by Dario Penwarden, O&M Supervisor, on "
             "2026-07-02 at 14:40.")
    pdf.para("Network Control duty engineer, City Power & Light (available 24/7).")
    return pdf.render()


def safety_audit(w: World) -> bytes:
    pdf = _pdf(w, "safety-audit", "Contoso Renewables - Corporate HSE", "AUD-2026-02")
    pdf.title_block("Internal safety audit report AUD-2026-02", "Quellmoor Ridge Wind Farm")
    pdf.grid(
        ["Field", "Value"],
        [
            ["Audit dates", "2026-02-16 to 2026-02-17"],
            ["Report date", "2026-03-06"],
            ["Auditor", "Ruth Kessington, Corporate HSE Auditor"],
            ["Site team", "Maren Ellingsby (Site Manager), Dario Penwarden (O&M Supervisor), "
                          "Greta Vollan (HSE Coordinator)"],
            ["Scope", "PTW system, lockout/tagout, working at height and rescue, lifting "
                      "equipment, oil and chemical handling, training records, emergency "
                      "arrangements"],
            ["Method", "Document review, interviews and observation of two jobs (filter change "
                       "on WTG-02, rescue drill on WTG-06)"],
            ["Overall score", "86 % (target 85 %)"],
        ],
        widths=(40, 134),
    )
    pdf.h1("Findings")
    pdf.grid(
        ["ID", "Category", "Finding", "Action", "Owner", "Due"],
        [
            ["F1", "Major", "Rescue kit in the WTG-06 nacelle past its 6-monthly inspection "
             "(last inspection 2025-06-12, due 2025-12-12); requirement SOP-WAH-003 section 7",
             "Inspect all rescue kits; add the kit seal check to the daily checklist",
             "Greta Vollan", "2026-03-31"],
            ["F2", "Minor", "Two personal padlocks in use without name tags; requirement "
             "SOP-LOTO-001 section 5", "Issue tagged padlocks and brief all technicians",
             "Dario Penwarden", "2026-03-15"],
            ["F3", "Minor", "Toolbox talk attendance records incomplete for November 2025 (one of "
             "four sessions without sign-in sheet)", "Reconstruct the records; use a digital "
             "sign-in", "Greta Vollan", "2026-04-30"],
            ["F4", "Observation", "Oil drum storage bund at 85 % of its capacity with 12 drums "
             "stored; permit EP-2018-0417 condition 9.3", "Reduce the stock in the bund or extend "
             "the bund", "Tomasz Lebrecht", "2026-06-30"],
            ["F5", "Minor", "No dropped-object exclusion signage at the tower base of WTG-11 "
             "during nacelle work; requirement SOP-WAH-003 section 4",
             "Provide a portable exclusion signage set for each turbine", "Callum Rydings",
             "2026-03-31"],
        ],
        widths=(10, 20, 58, 44, 24, 18),
        size=7.8,
    )
    pdf.h1("Positive observations")
    pdf.bullets(
        [
            "The PTW system is well used and permits are closed correctly.",
            "Lockout boards are clear and up to date.",
            "The rescue drill on WTG-06 lowered the casualty to the ground in 9 minutes "
            "(target 15 minutes).",
        ]
    )
    pdf.h1("Conclusion")
    pdf.para(
        "The site meets the corporate standard. The major finding F1 must be closed before "
        "2026-03-31 and verified by the HSE Coordinator. The status of all actions is reviewed "
        "at the monthly O&M review."
    )
    pdf.para("Ruth Kessington, Corporate HSE Auditor, Contoso Renewables - 2026-03-06.")
    return pdf.render()


def near_miss(w: World) -> bytes:
    pdf = _pdf(w, "inc-near-miss", "Contoso Renewables - Incident management", "INC-2026-003")
    pdf.title_block("Near-miss report INC-2026-003", "Dropped socket at WTG-11")
    pdf.grid(
        ["Field", "Value"],
        [
            ["Date and time", "2026-03-24 10:40"],
            ["Location", "WTG-11, yaw deck hatch"],
            ["Classification", "Near miss - dropped object - potential severity high"],
            ["Reported by", "Callum Rydings, Lead Wind Technician"],
            ["Investigated by", "Greta Vollan, HSE Coordinator"],
            ["Report date", "2026-03-27"],
        ],
        widths=(40, 134),
    )
    pdf.h1("Description")
    pdf.para(
        "During the 12-month service a 24 mm impact socket (0.4 kg) slipped from a technician's "
        "hand at the yaw deck while tools were passed through the open hatch. It fell about 85 m "
        "inside the tower to the tower base platform. Nobody was at the tower base because the "
        "exclusion zone had been respected. There was no injury; a cable tray cover was dented."
    )
    pdf.h1("Immediate actions")
    pdf.bullets(["Work stopped and the area was checked.",
                 "A toolbox talk on dropped objects was held on 2026-03-26."])
    pdf.h1("Causes")
    pdf.bullets(
        [
            "The socket was not tethered.",
            "The hatch stayed open while tools were passed.",
            "There was no tool tether anchor point at the yaw deck hatch.",
        ]
    )
    pdf.h1("Actions")
    pdf.grid(
        ["ID", "Action", "Owner", "Due", "Status"],
        [
            ["A1", "Install tool tether anchor points at the yaw deck hatches (WTG-11 under "
             "WO-26-0203, then all turbines)", "Callum Rydings", "2026-04-30", "open"],
            ["A2", "Make tool tethering mandatory above 2 m and update SOP-WAH-003",
             "Greta Vollan", "2026-04-15", "open"],
            ["A3", "Toolbox talk on dropped objects", "Dario Penwarden", "2026-03-26", "done"],
            ["A4", "Order tool tether sets AWI-31007", "Tomasz Lebrecht", "2026-03-31", "open"],
        ],
        widths=(10, 92, 30, 22, 20),
    )
    pdf.h1("Lessons learned")
    pdf.para(
        "Exclusion zones under work at height work. Tethering every tool and keeping hatches "
        "closed removes the hazard at its source."
    )
    return pdf.render()


# ------------------------------------------------------------------------------------------
# IT runbook sample (Relecloud)


def it_failover(w: World) -> bytes:
    pdf = _pdf(w, "it-failover", "Relecloud platform operations - Procedure", "PRC-DB-007")
    pdf.title_block("PRC-DB-007 - orders-db failover",
                    "PostgreSQL primary to standby failover for the orders-db cluster")
    pdf.grid(
        ["Field", "Value"],
        [
            ["Owner", "Amara Teodorescu, Database Administrator"],
            ["Approved by", "Jun Hallgarth, Engineering Manager"],
            ["Effective", "2026-02-23"],
            ["Scope", "orders-db: primary in zone 1, synchronous standby in zone 2, asynchronous "
                      "read replica for reporting-batch"],
            ["Targets", "RPO 0 with the synchronous standby; RTO 15 minutes"],
        ],
        widths=(40, 134),
    )
    pdf.h1("1. When to use")
    pdf.para(
        "Use this procedure when the orders-db primary is unavailable or degraded and the "
        "incident commander of a SEV1 or SEV2 incident has decided to fail over. Do not fail "
        "over for a single slow query."
    )
    pdf.h1("2. Preconditions")
    pdf.bullets(
        [
            "An incident commander is assigned and the incident channel is open.",
            "Replication lag of the standby is below 30 seconds (unless the primary is lost).",
            "Deployments to checkout-web and ticketing-api are frozen.",
        ]
    )
    pdf.h1("3. Steps")
    pdf.bullets(
        [
            "Announce the failover in the incident channel with the expected impact.",
            "Check the replication lag on the standby and record it.",
            "Stop writes: scale the checkout-web order workers to 0 replicas.",
            "Promote the standby to primary.",
            "Point the DNS alias orders-db-rw to the new primary (TTL 30 s).",
            "Restart the ticketing-api pods to drop pooled connections.",
            "Verify writes with a synthetic test order.",
            "Scale the checkout-web order workers back to their normal count.",
            "Rebuild the old primary as the new standby.",
            "Confirm that monitoring shows replication healthy again.",
            "Hand over to the on-call engineer and update the incident timeline.",
            "Hold the postmortem within 5 working days.",
        ],
        numbered=True,
    )
    pdf.h1("4. Rollback")
    pdf.para(
        "If the promoted standby fails verification, stop and escalate to the database "
        "administrator on call. Do not promote the asynchronous read replica: it may miss "
        "committed orders."
    )
    pdf.h1("5. Verification checklist")
    pdf.grid(
        ["Check", "Expected"],
        [
            ["orders-db-rw resolves to the new primary", "yes"],
            ["Synthetic order written and read back", "yes"],
            ["checkout-web error rate", "below 1 %"],
            ["Replication to the new standby", "lag below 30 s"],
        ],
        widths=(110, 64),
    )
    return pdf.render()
