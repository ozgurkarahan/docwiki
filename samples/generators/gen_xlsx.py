"""XLSX workbooks: asset register, maintenance plan, spare parts stock and the restricted rate card.

Every data sheet has its header in row 1 (locators count rows from the header = row 1).
Values only (no formulas); dates are ISO strings.
"""

from __future__ import annotations

import io
from collections.abc import Sequence

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from . import datasets
from .common import STAMP, meta_for, rng
from .ooxml import finalize_package
from .world import World

_HEADER_FILL = PatternFill("solid", fgColor="DCE6F1")


class WorkbookBuilder:
    def __init__(self, title: str) -> None:
        self.wb = Workbook()
        self.title = title
        self._first = True

    def sheet(self, name: str, header: Sequence[str], rows: Sequence[Sequence[object]],
              widths: Sequence[int] | None = None) -> None:
        if self._first:
            ws = self.wb.active
            ws.title = name
            self._first = False
        else:
            ws = self.wb.create_sheet(name)
        ws.append(list(header))
        for cell in ws[1]:
            cell.font = Font(bold=True)
            cell.fill = _HEADER_FILL
            cell.alignment = Alignment(vertical="top", wrap_text=True)
        for row in rows:
            ws.append(list(row))
        ws.freeze_panes = "A2"
        for index, width in enumerate(widths or [], start=1):
            ws.column_dimensions[get_column_letter(index)].width = width
        ws.oddHeader.left.text = self.title
        ws.oddHeader.right.text = STAMP
        ws.oddFooter.center.text = STAMP
        ws.oddFooter.right.text = "Page &P of &N"

    def about(self, lines: Sequence[str]) -> None:
        ws = self.wb.create_sheet("About")
        for line in [STAMP, *lines, STAMP]:
            ws.append([line])
        ws.column_dimensions["A"].width = 110
        ws.oddHeader.right.text = STAMP
        ws.oddFooter.center.text = STAMP

    def render(self, w: World, doc_id: str) -> bytes:
        doc = w.doc(doc_id)
        meta = meta_for(doc, w.org_name(str(doc["organisation"])))
        buf = io.BytesIO()
        self.wb.save(buf)
        return finalize_package(buf.getvalue(), meta)


def asset_register(w: World) -> bytes:
    b = WorkbookBuilder("Asset register 2026 - Quellmoor Ridge Wind Farm")
    rows = []
    for t in w.turbines:
        turbine = str(t["id"])
        if turbine == "WTG-09":
            note = "Gearbox oil conversion to PWG 220 pending (deferred, SB-LWS-2025-07)"
        else:
            note = f"Gearbox oil PWG 220 since {datasets.CONVERSION_DATES[turbine]}"
        rows.append(
            [turbine, t["serial"], "Litware LT-32", "CCV", "Fabrikam FGT-3200", t["gearbox_serial"],
             t["commissioned"], 92, 118, t["easting_m"], t["northing_m"], t["elevation_m"], note]
        )
    b.sheet(
        "Turbines",
        ["Turbine", "Serial number", "Model", "Variant", "Gearbox model", "Gearbox serial",
         "Commissioned", "Hub height (m)", "Rotor diameter (m)", "Easting (m)", "Northing (m)",
         "Elevation (m)", "Notes"],
        rows,
        widths=[10, 15, 15, 9, 18, 20, 13, 9, 9, 10, 10, 10, 60],
    )
    b.sheet(
        "Other assets",
        ["Asset", "Description", "Location", "Notes"],
        [
            ["Quellmoor Ridge substation", "33/132 kV substation, one 45 MVA transformer",
             "next to the O&M building", "Connection to City Power & Light, Skelvane 132 kV "
             "substation, circuit 2"],
            ["MM-01 met mast", "92 m meteorological mast", "north of WTG-01",
             "Reference for power curve tests"],
            ["Quellmoor Ridge O&M building", "Site office, workshop and stores",
             "site entrance", "Bunded oil drum store"],
        ],
        widths=[28, 45, 26, 60],
    )
    b.about(
        [
            "Asset register 2026 of Quellmoor Ridge Wind Farm (revision 2026-01-12).",
            "Owner: Yusuf Arkwell, Reliability Engineer, Contoso Renewables.",
            "Coordinates are in metres on the local site grid used by the site layout plan.",
        ]
    )
    return b.render(w, "asset-register")


_TASKS = [
    ["MP-GBX-01", "Gearbox oil sampling and laboratory analysis", "Gearbox", "6 months",
     "LWS-MM-GBX-32 section 4.4", 1.0, 1, ""],
    ["MP-GBX-02", "Gearbox oil filter element replacement (FGT-P-11872)", "Gearbox", "12 months",
     "SOP-GBX-010", 1.5, 2, ""],
    ["MP-GBX-03", "Gearbox oil change (PWG 220)", "Gearbox", "5 years or on condition",
     "SOP-GBX-010 Rev. B", 6.0, 2, "Next planned changes from 2030"],
    ["MP-GBX-04", "Gearbox endoscope inspection", "Gearbox", "24 months",
     "LWS-MM-GBX-32 section 4.4", 3.0, 2, ""],
    ["MP-GBX-05", "Gearbox visual inspection and leak check", "Gearbox", "6 months",
     "LWS-MM-GBX-32 section 4.4", 1.0, 2, ""],
    ["MP-GBX-06", "Vibration trend review (condition monitoring)", "Gearbox", "monthly",
     "LWS-MM-GBX-32 section 4.4", 0.5, 1, "Remote review by the Reliability Engineer"],
    ["MP-GBX-07", "Oil cooler radiator cleaning and fan current check", "Gearbox", "6 months",
     "INC-2026-006 (D7)", 2.0, 2, "Added in issue 2 (2026-07-01)"],
    ["MP-GEN-01", "Generator brush inspection", "Generator", "6 months", "WI-GEN-014", 1.5, 2,
     ""],
    ["MP-GEN-02", "Slip ring cleaning", "Generator", "12 months", "WI-GEN-014", 2.0, 2, ""],
    ["MP-PIT-01", "Pitch bearing bolt re-torque, 100 % of bolts, 1,450 Nm", "Pitch", "12 months",
     "SB-LWS-2025-11 Rev. A", 8.0, 2, ""],
    ["MP-BLD-01", "Blade drone inspection", "Rotor", "12 months", "Wingtip Blade Services", 1.0,
     2, "Contractor"],
    ["MP-YAW-01", "Yaw brake pad inspection", "Yaw", "12 months", "LT-32 manual chapter 7", 2.0,
     2, ""],
    ["MP-HYD-01", "Hydraulic accumulator pre-charge check", "Hydraulics", "12 months",
     "LT-32 manual chapter 9", 1.5, 2, ""],
    ["MP-HSE-01", "Rescue kit inspection", "Safety", "6 months", "SOP-WAH-003 section 7", 0.5, 1,
     ""],
    ["MP-HSE-02", "Fall arrest rail and ladder inspection", "Safety", "12 months", "SOP-WAH-003",
     1.0, 2, ""],
]

_PLAN_MONTHS = {
    "MP-GBX-01": ("2026-06", "2026-12"),
    "MP-GBX-05": ("2026-03", "2026-09"),
    "MP-GBX-07": ("2026-07", "2027-01"),
    "MP-GEN-01": ("2026-04", "2026-10"),
    "MP-HSE-01": ("2026-02", "2026-08"),
}


def maintenance_plan(w: World) -> bytes:
    b = WorkbookBuilder("Maintenance plan 2026 - issue 2 - Quellmoor Ridge Wind Farm")
    b.sheet(
        "Tasks",
        ["Task ID", "Task", "System", "Interval", "Procedure or reference", "Duration (h)", "Crew",
         "Notes"],
        _TASKS,
        widths=[11, 55, 12, 20, 28, 12, 7, 36],
    )
    r = rng("maintenance-plan")
    plan_rows: list[list[object]] = []
    for index, t in enumerate(w.turbines):
        turbine = str(t["id"])
        for task_id, months in _PLAN_MONTHS.items():
            first, second = months
            status = "done" if first < "2026-07" else "planned"
            plan_rows.append([turbine, task_id, f"{first}, {second}", status])
        filter_month = f"2026-{1 + index % 12:02d}"
        plan_rows.append([turbine, "MP-GBX-02", filter_month,
                          "done" if filter_month < "2026-07" else "planned"])
        pitch_month = "2026-05" if index < 6 else "2026-09"
        plan_rows.append([turbine, "MP-PIT-01", pitch_month,
                          "done" if pitch_month < "2026-07" else "planned"])
        plan_rows.append([turbine, "MP-BLD-01", "2026-05", "done"])
        endo = "2026-07" if turbine == "WTG-02" else ("2026-10" if index % 2 else "2027-04")
        plan_rows.append([turbine, "MP-GBX-04", endo,
                          "done" if turbine == "WTG-02" else "planned"])
    b.sheet(
        "Plan 2026",
        ["Turbine", "Task ID", "Planned months", "Status at 2026-07-01"],
        plan_rows,
        widths=[10, 11, 20, 20],
    )
    sampling = []
    for index, t in enumerate(w.turbines):
        turbine = str(t["id"])
        if turbine == "WTG-07":
            sampling.append([turbine, "2026-06-10", "TR-OA-2026-0614", "PWG 220", 64, 112, "ALERT",
                             "2026-07-10 (resample within 30 days)"])
            continue
        fe = r.randint(9, 27)
        pq = r.randint(8, 31)
        day = f"2026-06-{8 + index // 3:02d}"
        number = 603 + index
        if number == 614:
            # TR-OA-2026-0614 is the WTG-07 report; WTG-12 gets the next free number.
            number = 615
        sampling.append([turbine, day, f"TR-OA-2026-{number:04d}", "PWG 220", fe, pq, "NORMAL",
                         "2026-12"])
    b.sheet(
        "Oil sampling",
        ["Turbine", "Last sample", "Report", "Oil", "Fe (ppm)", "PQ index", "Condition",
         "Next sample due"],
        sampling,
        widths=[10, 13, 18, 10, 10, 10, 12, 34],
    )
    b.sheet(
        "Revision log",
        ["Issue", "Date", "Change", "Author"],
        [
            [1, "2025-12-15", "Plan 2026 issued; oil sampling schedule updated for PWG 220 "
             "(MOC-2025-012 action 5).", "Dario Penwarden"],
            [2, "2026-07-01", "Task MP-GBX-07 added for all turbines after INC-2026-006; WTG-02 "
             "endoscope brought forward to July.", "Dario Penwarden"],
        ],
        widths=[7, 13, 90, 18],
    )
    b.about(
        [
            "Maintenance plan 2026, issue 2 of 2026-07-01, Quellmoor Ridge Wind Farm.",
            "Owner: Dario Penwarden, O&M Supervisor, Contoso Renewables.",
            "Sheets: Tasks (task catalogue), Plan 2026 (per turbine), Oil sampling, Revision log.",
        ]
    )
    return b.render(w, "maintenance-plan")


STOCK_ROWS: list[list[object]] = [
    ["FGT-P-22328", "HSS bearing, generator side (FGT-3200)", "Fabrikam Getriebetechnik GmbH",
     "Bearings", "pc", 0, 1, 2, 2, "PO-76994", "2026-09-25", "B-04-2", "Y"],
    ["FGT-P-22331", "HSS bearing, rotor side (FGT-3200)", "Fabrikam Getriebetechnik GmbH",
     "Bearings", "pc", 1, 1, 1, 0, "", "", "B-04-3", "Y"],
    ["FGT-P-21904", "IMS bearing set (FGT-3200)", "Fabrikam Getriebetechnik GmbH", "Bearings",
     "set", 1, 1, 1, 0, "", "", "B-05-1", "Y"],
    ["FGT-P-11872", "Gearbox oil filter element, 10 micron", "Fabrikam Getriebetechnik GmbH",
     "Filters", "pc", 14, 12, 24, 0, "", "", "F-01-1", "Y"],
    ["FGT-P-11880", "Gearbox breather with desiccant", "Fabrikam Getriebetechnik GmbH",
     "Filters", "pc", 9, 6, 12, 0, "", "", "F-01-2", "N"],
    ["FGT-P-13010", "Oil level sight glass with seal", "Fabrikam Getriebetechnik GmbH",
     "Gearbox", "pc", 2, 2, 2, 0, "", "", "G-02-1", "N"],
    ["FGT-P-14002", "Oil sampling valve with dust cap", "Fabrikam Getriebetechnik GmbH",
     "Gearbox", "pc", 6, 4, 6, 0, "", "", "G-02-2", "N"],
    ["LWS-P-30418", "Oil cooler fan motor 1.5 kW", "Litware Wind Systems", "Electrical", "pc",
     1, 2, 2, 2, "PO-77102", "2026-08-14", "E-02-1", "Y"],
    ["LWS-P-30422", "Oil cooler thermostatic valve insert", "Litware Wind Systems", "Gearbox",
     "pc", 3, 2, 2, 0, "", "", "G-03-1", "N"],
    ["LWS-P-51207", "Generator brush set (18 brushes)", "Litware Wind Systems", "Electrical",
     "set", 3, 2, 4, 0, "", "", "E-03-2", "N"],
    ["LWS-P-55031", "Slip ring cleaning kit", "Litware Wind Systems", "Electrical", "kit", 4, 2,
     4, 0, "", "", "E-03-3", "N"],
    ["LWS-P-60455", "Pitch bearing bolt kit M30 10.9 (72 bolts)", "Litware Wind Systems",
     "Fasteners", "kit", 2, 1, 2, 0, "", "", "P-01-1", "N"],
    ["LWS-P-41120", "Yaw brake pad set", "Litware Wind Systems", "Mechanical", "set", 4, 2, 4, 0,
     "", "", "M-02-4", "N"],
    ["LWS-P-72210", "Hydraulic accumulator 4 L", "Litware Wind Systems", "Hydraulics", "pc", 2, 1,
     2, 0, "", "", "H-01-1", "N"],
    ["LWS-P-80031", "Ice detection sensor", "Litware Wind Systems", "Sensors", "pc", 2, 1, 1, 0,
     "", "", "S-01-2", "N"],
    ["LWS-P-90012", "Nacelle hatch gas strut", "Litware Wind Systems", "Mechanical", "pc", 4, 2,
     4, 0, "", "", "M-03-1", "N"],
    ["PWS-220-D208", "Proseware PWG 220 gear oil, 208 L drum", "Proseware Lubricants",
     "Lubricants", "drum", 11, 8, 6, 0, "", "", "L-01", "Y"],
    ["PWS-320-D208", "Proseware PWG 320 gear oil, 208 L drum - do not use (MOC-2025-012)",
     "Proseware Lubricants", "Lubricants", "drum", 1, 0, 0, 0, "", "", "L-02", "N"],
    ["AWI-10442", "Hydraulic hose assembly DN12, 1.6 m (not stocked)",
     "Adventure Works Industrial Supply", "Hydraulics", "pc", 0, 0, 0, 0, "", "", "H-02-3", "N"],
    ["AWI-20915", "Spill kit refill, 50 L", "Adventure Works Industrial Supply", "HSE", "kit", 5,
     4, 6, 0, "", "", "HSE-01", "N"],
    ["AWI-31007", "Tool tether set (10 lanyards)", "Adventure Works Industrial Supply", "HSE",
     "set", 6, 4, 4, 0, "", "", "HSE-02", "N"],
    ["AWI-40210", "Nitrile gloves, box of 100", "Adventure Works Industrial Supply", "HSE", "box",
     18, 10, 20, 0, "", "", "HSE-03", "N"],
    ["AWI-40388", "Oil absorbent pads, pack of 200", "Adventure Works Industrial Supply", "HSE",
     "pack", 7, 4, 6, 0, "", "", "HSE-04", "N"],
]


def spare_parts_stock(w: World) -> bytes:
    b = WorkbookBuilder("Spare parts stock 2026-07-21 - Quellmoor Ridge Wind Farm")
    b.sheet(
        "Stock",
        ["Part number", "Description", "Supplier", "Category", "Unit", "On hand", "Minimum",
         "Reorder qty", "On order", "PO number", "Expected delivery", "Bin", "Critical"],
        STOCK_ROWS,
        widths=[14, 52, 32, 12, 7, 9, 9, 11, 9, 11, 16, 9, 9],
    )
    b.sheet(
        "Movements",
        ["Date", "Part number", "Quantity", "Reference", "Turbine", "By"],
        [
            ["2026-03-12", "FGT-P-22328", -1, "WO-26-0187", "WTG-10", "Tomasz Lebrecht"],
            ["2026-04-02", "AWI-31007", -1, "WO-26-0203", "WTG-11", "Tomasz Lebrecht"],
            ["2026-04-14", "AWI-31007", 4, "PO-76410", "", "Tomasz Lebrecht"],
            ["2026-05-04", "LWS-P-60455", -1, "WO-26-0301", "WTG-01", "Tomasz Lebrecht"],
            ["2026-06-08", "FGT-P-14002", -1, "WO-26-0341", "WTG-01", "Tomasz Lebrecht"],
            ["2026-06-24", "LWS-P-30418", -1, "WO-26-0398", "WTG-07", "Tomasz Lebrecht"],
            ["2026-06-30", "PWS-220-D208", 2, "PO-76988", "", "Tomasz Lebrecht"],
            ["2026-07-07", "AWI-40388", -1, "WO-26-0430", "WTG-01", "Tomasz Lebrecht"],
            ["2026-07-18", "LWS-P-51207", -1, "WO-26-0436", "WTG-09", "Tomasz Lebrecht"],
        ],
        widths=[12, 14, 10, 13, 10, 18],
    )
    b.sheet(
        "Suppliers",
        ["Supplier", "Supplies", "Typical lead time (weeks)", "Ordering e-mail"],
        [
            ["Fabrikam Getriebetechnik GmbH", "Gearbox bearings, filters, gearbox parts", 10,
             "orders@fabrikam-getriebe.example"],
            ["Litware Wind Systems", "Turbine spare parts, electrical parts", 6,
             "spares@litware-wind.example"],
            ["Proseware Lubricants", "Gear oil", 3, "orders@contoso-renewables.example"],
            ["Adventure Works Industrial Supply", "Consumables, hydraulic hoses, HSE items", 2,
             "orders@contoso-renewables.example"],
        ],
        widths=[32, 42, 24, 36],
    )
    b.about(
        [
            "Spare parts stock of the Quellmoor Ridge O&M building, snapshot of 2026-07-21.",
            "A part is below its minimum level when 'On hand' is lower than 'Minimum'.",
            "Owner: Tomasz Lebrecht, Stores and Spare Parts Coordinator, Contoso Renewables.",
        ]
    )
    return b.render(w, "stock")


def rate_card(w: World) -> bytes:
    b = WorkbookBuilder("RESTRICTED - Contractor rate card 2026 - Contoso Renewables")
    b.sheet(
        "Rates 2026",
        ["Contractor", "Service", "Unit", "Rate (EUR)", "Notes"],
        [
            ["Tailspin Heavy Lift", "600 t crawler crane with operator", "day", 18400,
             "fleet no. TS-600C-02"],
            ["Tailspin Heavy Lift", "Mobilisation and demobilisation of the 600 t crane",
             "lump sum", 42000, ""],
            ["Tailspin Heavy Lift", "Weather standby", "day", 9200, "after the first standby day"],
            ["Tailspin Heavy Lift", "100 t assist crane with operator", "day", 3100, ""],
            ["Wingtip Blade Services", "Drone blade inspection", "turbine", 1150, "3 blades"],
            ["Wingtip Blade Services", "Rope-access repair team (2 technicians)", "day", 3900, ""],
            ["Wingtip Blade Services", "Inspection report", "site", 2500, ""],
            ["Trey Research Laboratories", "Standard oil analysis", "sample", 85, ""],
            ["Trey Research Laboratories", "Extended oil analysis (PQ index, particle count)",
             "sample", 140, ""],
        ],
        widths=[28, 50, 10, 12, 30],
    )
    b.sheet(
        "Terms",
        ["Item", "Value"],
        [
            ["Validity", "2026-01-01 to 2026-12-31"],
            ["Payment terms", "45 days end of month"],
            ["Indexation", "none during the validity period"],
            ["Sensitivity", "RESTRICTED - commercial in confidence"],
        ],
        widths=[20, 50],
    )
    b.about(
        [
            "RESTRICTED - commercial in confidence. Do not publish.",
            "Contractor rates negotiated by Contoso Renewables for Quellmoor Ridge, 2026-01-05.",
        ]
    )
    return b.render(w, "rate-card")
