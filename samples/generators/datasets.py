"""Deterministic datasets shared by several generators (SCADA log, work orders, trends, stock).

Every value is either planted (see ``samples/fiction/bible.yaml`` scenarios) or drawn from a
seeded random stream, so regenerating the corpus always yields the same rows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from functools import cache

from .common import rng

TURBINES = [f"WTG-{i:02d}" for i in range(1, 13)]
BAT_TURBINES = ("WTG-03", "WTG-04", "WTG-05")

SCADA_START = datetime(2026, 4, 1)
SCADA_END = datetime(2026, 9, 1)

SCADA_COLUMNS = [
    "timestamp",
    "turbine",
    "event_type",
    "code",
    "description",
    "state",
    "value",
    "unit",
    "wind_speed_ms",
    "ambient_temp_c",
]

ALARM_TEXT = {
    "A1001": "Emergency stop activated",
    "A2101": "Gearbox oil sump temperature high",
    "A2102": "Gearbox oil sump temperature trip",
    "A2110": "Gearbox HSS bearing temperature high",
    "A2120": "Gearbox oil pressure low",
    "A2140": "Gearbox oil filter differential pressure high",
    "A3201": "Generator winding temperature high",
    "A3210": "Generator brush wear limit reached",
    "A4105": "Pitch system fault",
    "A5001": "Yaw misalignment",
    "A6101": "Grid voltage out of range",
    "A7001": "Ice detected on rotor blades",
}
STATUS_TEXT = {
    "S200": "Ready - low wind",
    "S310": "Maintenance mode",
    "S420": "Curtailed - environmental condition",
    "S430": "Curtailed - grid operator setpoint",
    "S510": "Stopped - fault",
    "S600": "Stopped - icing",
}

# Planted: 27 A2101 warnings on WTG-07 between 2026-04-09 and 2026-06-21.
WTG07_A2101_DAYS = [
    "2026-04-09", "2026-04-14", "2026-04-18", "2026-04-23", "2026-04-27", "2026-04-30",
    "2026-05-04", "2026-05-07", "2026-05-11", "2026-05-14", "2026-05-18", "2026-05-21",
    "2026-05-25", "2026-05-27", "2026-05-29", "2026-05-30",
    "2026-06-02", "2026-06-04", "2026-06-06", "2026-06-08", "2026-06-10", "2026-06-12",
    "2026-06-14", "2026-06-16", "2026-06-18", "2026-06-19", "2026-06-21",
]  # fmt: skip


@dataclass(frozen=True)
class Weather:
    wind: list[float]
    temp: list[float]

    def at(self, moment: datetime) -> tuple[float, float]:
        index = int((moment - SCADA_START).total_seconds() // 3600)
        index = max(0, min(index, len(self.wind) - 1))
        return self.wind[index], self.temp[index]


@cache
def weather() -> Weather:
    """Hourly hub-height wind speed (m/s) and ambient temperature (degC), April-August 2026."""
    r = rng("weather-2026")
    hours = int((SCADA_END - SCADA_START).total_seconds() // 3600)
    days = hours // 24
    anomalies: list[float] = []
    previous = 0.0
    for _ in range(days):
        previous = 0.6 * previous + r.gauss(0.0, 1.8)
        anomalies.append(previous)
    month_mean = {4: 6.0, 5: 10.0, 6: 13.5, 7: 16.0, 8: 15.5}
    wind: list[float] = []
    temp: list[float] = []
    w = 7.0
    for h in range(hours):
        moment = SCADA_START + timedelta(hours=h)
        w = 0.92 * w + 0.08 * 7.0 + r.gauss(0.0, 0.85)
        w = max(0.4, min(23.5, w))
        diurnal = 4.5 * math.sin((moment.hour - 9) / 24 * 2 * math.pi)
        heat = 9.0 if date(2026, 7, 19) <= moment.date() <= date(2026, 7, 23) else 0.0
        t = month_mean[moment.month] + diurnal + anomalies[h // 24] + heat
        wind.append(round(w, 1))
        temp.append(round(t, 1))
    return Weather(wind=wind, temp=temp)


def _fmt(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%d %H:%M:%S")


def _row(
    moment: datetime,
    turbine: str,
    code: str,
    state: str,
    value: str = "",
    unit: str = "",
    wind_override: float | None = None,
) -> dict[str, str]:
    wind, temp = weather().at(moment)
    if wind_override is not None:
        # High-load events (over-temperature) happen in strong wind, whatever the weather model.
        wind = wind_override
    is_status = code.startswith("S")
    return {
        "timestamp": _fmt(moment),
        "turbine": turbine,
        "event_type": "STATUS" if is_status else "ALARM",
        "code": code,
        "description": STATUS_TEXT[code] if is_status else ALARM_TEXT[code],
        "state": state,
        "value": value,
        "unit": unit,
        "wind_speed_ms": f"{wind:.1f}",
        "ambient_temp_c": f"{temp:.1f}",
    }


def _night_curtailment() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    day = date(2026, 6, 1)
    while day <= date(2026, 8, 31):
        start = datetime(day.year, day.month, day.day, 22, 0, 0)
        wind, temp = weather().at(start)
        if wind < 6.0 and temp >= 10.0:
            end = start + timedelta(hours=7)
            for offset, turbine in enumerate(BAT_TURBINES):
                begin = start + timedelta(seconds=4 + 3 * offset)
                rows.append(_row(begin, turbine, "S420", "START"))
                rows.append(_row(end + timedelta(seconds=6 + 3 * offset), turbine, "S420", "END"))
        day += timedelta(days=1)
    return rows


def night_curtailment_nights() -> list[str]:
    """Dates (evening of the night) with environmental curtailment, for documentation."""
    nights = {row["timestamp"][:10] for row in _night_curtailment() if row["state"] == "START"}
    return sorted(nights)


def _grid_curtailment() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for day in (14, 15, 16):
        for index, turbine in enumerate(TURBINES):
            start = datetime(2026, 7, day, 8, 0, 5 + index)
            end = datetime(2026, 7, day, 18, 0, 8 + index)
            rows.append(_row(start, turbine, "S430", "START", "20.0", "MW"))
            rows.append(_row(end, turbine, "S430", "END", "20.0", "MW"))
    return rows


def _wtg07_overtemperature() -> list[dict[str, str]]:
    r = rng("wtg07-a2101")
    rows: list[dict[str, str]] = []
    for day in WTG07_A2101_DAYS:
        d = date.fromisoformat(day)
        if day == "2026-05-30":
            raised = datetime(2026, 5, 30, 13, 58, 41)
            rows.append(_row(raised, "WTG-07", "A2101", "RAISED", "75.3", "°C", 11.4))
            trip = datetime(2026, 5, 30, 14, 12, 37)
            rows.append(_row(trip, "WTG-07", "A2102", "RAISED", "82.6", "°C", 11.8))
            rows.append(_row(trip + timedelta(seconds=1), "WTG-07", "S510", "START"))
            rows.append(_row(datetime(2026, 5, 30, 15, 31, 2), "WTG-07", "A2102", "CLEARED",
                             "79.4", "°C"))
            rows.append(_row(datetime(2026, 5, 30, 15, 58, 20), "WTG-07", "A2101", "CLEARED",
                             "72.8", "°C"))
            rows.append(_row(datetime(2026, 5, 30, 16, 5, 44), "WTG-07", "S510", "END"))
            continue
        if day == "2026-06-19":
            raised = datetime(2026, 6, 19, 15, 21, 9)
            rows.append(_row(raised, "WTG-07", "A2101", "RAISED", "75.6", "°C", 12.1))
            trip = datetime(2026, 6, 19, 15, 47, 12)
            rows.append(_row(trip, "WTG-07", "A2102", "RAISED", "83.4", "°C", 12.6))
            rows.append(_row(trip + timedelta(seconds=1), "WTG-07", "S510", "START"))
            rows.append(_row(datetime(2026, 6, 19, 17, 2, 31), "WTG-07", "A2102", "CLEARED",
                             "79.1", "°C"))
            rows.append(_row(datetime(2026, 6, 19, 17, 24, 55), "WTG-07", "A2101", "CLEARED",
                             "72.6", "°C"))
            rows.append(_row(datetime(2026, 6, 19, 17, 40, 3), "WTG-07", "S510", "END"))
            continue
        raised = datetime(
            d.year, d.month, d.day, r.randint(12, 16), r.randint(0, 59), r.randint(0, 59)
        )
        peak = round(r.uniform(75.1, 79.8), 1)
        cleared = raised + timedelta(minutes=r.randint(14, 68), seconds=r.randint(0, 59))
        strong = round(r.uniform(9.5, 14.5), 1)
        rows.append(_row(raised, "WTG-07", "A2101", "RAISED", f"{peak:.1f}", "°C", strong))
        cleared_value = f"{r.uniform(72.0, 73.4):.1f}"
        rows.append(_row(cleared, "WTG-07", "A2101", "CLEARED", cleared_value, "°C"))
    # Corrective maintenance on 2026-06-24 (fan motor and radiator, WO-26-0398/WO-26-0399).
    rows.append(_row(datetime(2026, 6, 24, 8, 12, 30), "WTG-07", "S310", "START"))
    rows.append(_row(datetime(2026, 6, 24, 15, 36, 10), "WTG-07", "S310", "END"))
    return rows


def _other_planted() -> list[dict[str, str]]:
    rows = [
        _row(datetime(2026, 7, 21, 15, 20, 44), "WTG-03", "A2101", "RAISED", "75.4", "°C", 10.4),
        _row(datetime(2026, 7, 21, 15, 33, 2), "WTG-03", "A2101", "CLEARED", "72.9", "°C"),
        _row(datetime(2026, 8, 12, 16, 5, 2), "WTG-11", "A2101", "RAISED", "75.1", "°C", 10.9),
        _row(datetime(2026, 8, 12, 16, 14, 40), "WTG-11", "A2101", "CLEARED", "72.7", "°C"),
        _row(datetime(2026, 7, 19, 14, 40, 18), "WTG-02", "A2110", "RAISED", "91.2", "°C", 11.2),
        _row(datetime(2026, 7, 19, 15, 2, 51), "WTG-02", "A2110", "CLEARED", "88.4", "°C"),
        _row(datetime(2026, 7, 22, 15, 5, 26), "WTG-02", "A2110", "RAISED", "90.6", "°C", 10.7),
        _row(datetime(2026, 7, 22, 15, 19, 7), "WTG-02", "A2110", "CLEARED", "88.1", "°C"),
        _row(datetime(2026, 7, 23, 7, 45, 0), "WTG-02", "S310", "START"),
        _row(datetime(2026, 7, 23, 13, 20, 15), "WTG-02", "S310", "END"),
        _row(datetime(2026, 7, 16, 11, 2, 37), "WTG-09", "A3210", "RAISED"),
        _row(datetime(2026, 7, 18, 7, 58, 12), "WTG-09", "S310", "START"),
        _row(datetime(2026, 7, 18, 11, 41, 5), "WTG-09", "A3210", "CLEARED"),
        _row(datetime(2026, 7, 18, 11, 52, 40), "WTG-09", "S310", "END"),
    ]
    return rows


def _low_wind() -> list[dict[str, str]]:
    """S200 periods when the hub-height wind stays below cut-in for at least four hours."""
    w = weather()
    rows: list[dict[str, str]] = []
    run_start: int | None = None
    for hour, speed in enumerate([*w.wind, 99.0]):
        if speed < 3.0:
            if run_start is None:
                run_start = hour
            continue
        if run_start is not None and hour - run_start >= 4:
            start = SCADA_START + timedelta(hours=run_start)
            end = SCADA_START + timedelta(hours=hour)
            for index, turbine in enumerate(TURBINES):
                begin = start + timedelta(seconds=11 + 7 * index)
                rows.append(_row(begin, turbine, "S200", "START"))
                rows.append(_row(end + timedelta(seconds=13 + 7 * index), turbine, "S200", "END"))
        run_start = None
    return rows


def _icing() -> list[dict[str, str]]:
    r = rng("icing-april")
    rows: list[dict[str, str]] = []
    for day in (1, 2, 3, 6, 7):
        affected = sorted(r.sample(TURBINES, r.randint(2, 5)))
        for turbine in affected:
            start = datetime(2026, 4, day, r.randint(4, 6), r.randint(0, 59), r.randint(0, 59))
            end = start + timedelta(hours=r.randint(2, 5), minutes=r.randint(0, 59))
            rows.append(_row(start, turbine, "A7001", "RAISED"))
            rows.append(_row(start + timedelta(seconds=2), turbine, "S600", "START"))
            rows.append(_row(end, turbine, "A7001", "CLEARED"))
            rows.append(_row(end + timedelta(seconds=40), turbine, "S600", "END"))
    return rows


def _background() -> list[dict[str, str]]:
    """Seeded background alarms that make the log realistic."""
    r = rng("scada-background")
    rows: list[dict[str, str]] = []
    span = int((SCADA_END - SCADA_START).total_seconds())

    def when() -> datetime:
        return SCADA_START + timedelta(seconds=r.randint(0, span - 7200))

    for _ in range(250):
        turbine = r.choice(TURBINES)
        start = when()
        error = r.uniform(10.5, 19.5)
        rows.append(_row(start, turbine, "A5001", "RAISED", f"{error:.1f}", "deg"))
        rows.append(
            _row(start + timedelta(seconds=r.randint(40, 600)), turbine, "A5001", "CLEARED", "4.2",
                 "deg")
        )
    for _ in range(22):
        turbine = r.choice(TURBINES)
        start = when()
        dp = r.uniform(2.5, 2.9)
        rows.append(_row(start, turbine, "A2140", "RAISED", f"{dp:.2f}", "bar"))
        rows.append(
            _row(start + timedelta(minutes=r.randint(20, 240)), turbine, "A2140", "CLEARED", "1.90",
                 "bar")
        )
    for _ in range(14):
        turbine = r.choice([t for t in TURBINES if t != "WTG-07"])
        start = when()
        rows.append(_row(start, turbine, "A3201", "RAISED", f"{r.uniform(145.2, 149.0):.1f}", "°C"))
        rows.append(
            _row(start + timedelta(minutes=r.randint(10, 50)), turbine, "A3201", "CLEARED", "139.5",
                 "°C")
        )
    for _ in range(11):
        turbine = r.choice(TURBINES)
        start = when()
        axis = str(r.randint(1, 3))
        rows.append(_row(start, turbine, "A4105", "RAISED", axis, "axis"))
        rows.append(_row(start + timedelta(seconds=1), turbine, "S510", "START"))
        end = start + timedelta(minutes=r.randint(25, 180))
        rows.append(_row(end, turbine, "A4105", "CLEARED", axis, "axis"))
        rows.append(_row(end + timedelta(seconds=30), turbine, "S510", "END"))
    for _ in range(6):
        start = when()
        voltage = f"{r.uniform(86.0, 89.5):.1f}"
        for index, turbine in enumerate(TURBINES):
            moment = start + timedelta(seconds=index)
            rows.append(_row(moment, turbine, "A6101", "RAISED", voltage, "%"))
            rows.append(_row(moment + timedelta(seconds=1), turbine, "S510", "START"))
            back = moment + timedelta(minutes=r.randint(3, 9))
            rows.append(_row(back, turbine, "A6101", "CLEARED", "99.6", "%"))
            rows.append(_row(back + timedelta(seconds=20), turbine, "S510", "END"))
    for day in (2, 3, 7):
        for turbine in r.sample(TURBINES, 2):
            start = datetime(2026, 4, day, 7, r.randint(0, 40), r.randint(0, 59))
            pressure = f"{r.uniform(0.55, 0.78):.2f}"
            rows.append(_row(start, turbine, "A2120", "RAISED", pressure, "bar"))
            back = start + timedelta(minutes=r.randint(6, 25))
            rows.append(_row(back, turbine, "A2120", "CLEARED", "1.35", "bar"))
    for _ in range(64):
        turbine = r.choice([t for t in TURBINES if t != "WTG-07"])
        start = when().replace(hour=r.randint(7, 9))
        end = start + timedelta(hours=r.randint(2, 7), minutes=r.randint(0, 59))
        rows.append(_row(start, turbine, "S310", "START"))
        if r.random() < 0.08:
            stop = start + timedelta(minutes=r.randint(5, 30))
            rows.append(_row(stop, turbine, "A1001", "RAISED"))
            reset = start + timedelta(minutes=r.randint(31, 60))
            rows.append(_row(reset, turbine, "A1001", "CLEARED"))
        rows.append(_row(end, turbine, "S310", "END"))
    return rows


@cache
def scada_rows() -> list[dict[str, str]]:
    rows = (
        _night_curtailment()
        + _grid_curtailment()
        + _wtg07_overtemperature()
        + _other_planted()
        + _icing()
        + _low_wind()
        + _background()
    )
    rows.sort(key=lambda row: (row["timestamp"], row["turbine"], row["code"], row["state"]))
    return rows


# --------------------------------------------------------------------------------------------
# Vibration trend of the WTG-07 gearbox HSS bearing (generator side), weekly on Mondays.

VIBRATION_COLUMNS = [
    "date",
    "turbine",
    "sensor",
    "velocity_rms_mm_s",
    "envelope_ge",
    "oil_temp_avg_c",
    "power_avg_kw",
]
_VELOCITY = [
    2.1, 2.2, 2.1, 2.3,
    2.3, 2.4, 2.4, 2.6,
    2.7, 2.8, 2.9, 3.1, 3.2,
    3.4, 3.6, 3.7, 3.9,
    4.1, 4.3, 4.4, 4.7,
    4.9, 5.0, 5.2, 5.4, 5.1,
    5.0, 5.2, 5.3, 5.3,
    5.4, 5.5, 5.6, 5.6, 5.7,
]  # fmt: skip


@cache
def vibration_rows() -> list[dict[str, str]]:
    r = rng("vibration-wtg07")
    rows: list[dict[str, str]] = []
    day = date(2026, 1, 5)
    for velocity in _VELOCITY:
        envelope = max(0.3, 0.55 * velocity - 0.8 + r.uniform(-0.08, 0.08))
        if day < date(2026, 4, 6):
            oil = r.uniform(50.5, 56.0)
        elif day < date(2026, 6, 29):
            oil = r.uniform(64.0, 70.5)
        else:
            oil = r.uniform(57.0, 61.0)
        if date(2026, 6, 1) <= day < date(2026, 6, 29):
            power = r.uniform(780.0, 990.0)
        else:
            power = r.uniform(900.0, 1450.0) if day.month in (1, 2, 3) else r.uniform(620.0, 1100.0)
        rows.append(
            {
                "date": day.isoformat(),
                "turbine": "WTG-07",
                "sensor": "GBX HSS GS radial",
                "velocity_rms_mm_s": f"{velocity:.1f}",
                "envelope_ge": f"{envelope:.2f}",
                "oil_temp_avg_c": f"{oil:.1f}",
                "power_avg_kw": f"{power:.0f}",
            }
        )
        day += timedelta(days=7)
    return rows


# --------------------------------------------------------------------------------------------
# Oil samples of WTG-07 (laboratory history).

_OIL_SAMPLE_ROWS = [
    ("2025-06-11", "TR-OA-2025-0388", "PWG 320", 22, 19, 318, "NORMAL"),
    ("2025-12-09", "TR-OA-2025-0951", "PWG 220", 18, 21, 221, "NORMAL"),
    ("2026-03-17", "TR-OA-2026-0241", "PWG 220", 31, 44, 224, "NORMAL"),
    ("2026-06-10", "TR-OA-2026-0614", "PWG 220", 64, 112, 229, "ALERT"),
]
WTG07_OIL_SAMPLES = [
    dict(zip(("date", "report", "oil", "fe", "pq", "visc40", "status"), row, strict=True))
    for row in _OIL_SAMPLE_ROWS
]


# --------------------------------------------------------------------------------------------
# Work orders (export of 2026-08-31).

WORK_ORDER_COLUMNS = [
    "wo_number",
    "created",
    "turbine",
    "type",
    "title",
    "status",
    "priority",
    "part_number",
    "part_qty",
    "assigned_to",
    "planned_date",
    "completed_date",
    "reference",
    "remarks",
]

CONVERSION_DATES = {
    "WTG-01": "2025-09-03",
    "WTG-02": "2025-09-10",
    "WTG-03": "2025-09-17",
    "WTG-04": "2025-09-24",
    "WTG-05": "2025-10-01",
    "WTG-06": "2025-10-08",
    "WTG-07": "2025-10-15",
    "WTG-08": "2025-10-22",
    "WTG-09": "2026-01-20",
    "WTG-10": "2025-11-05",
    "WTG-11": "2025-11-12",
    "WTG-12": "2025-11-19",
}

TECHNICIANS = ("Callum Rydings", "\u00c9lise Ternaux")


def _wo(
    number: str,
    created: str,
    turbine: str,
    wo_type: str,
    title: str,
    status: str,
    priority: str = "Medium",
    part: str = "",
    qty: str = "",
    assigned: str = "Callum Rydings",
    planned: str = "",
    completed: str = "",
    reference: str = "",
    remarks: str = "",
) -> dict[str, str]:
    return {
        "wo_number": number,
        "created": created,
        "turbine": turbine,
        "type": wo_type,
        "title": title,
        "status": status,
        "priority": priority,
        "part_number": part,
        "part_qty": qty,
        "assigned_to": assigned,
        "planned_date": planned,
        "completed_date": completed,
        "reference": reference,
        "remarks": remarks,
    }


def _number(row: dict[str, str]) -> int:
    return int(row["wo_number"].split("-")[2])


def _assign_numbers(year: str, planted: list[dict[str, str]], routine: list[dict[str, str]],
                    first: int) -> list[dict[str, str]]:
    """Give routine work orders numbers that increase with their creation date.

    Planted work orders keep their fixed numbers; routine ones are numbered between them and
    dropped when no free number is left before the next planted one.
    """
    r = rng(f"wo-numbers-{year}")
    ordered = sorted(planted + routine, key=lambda row: (row["created"], row["wo_number"] or "~"))
    result: list[dict[str, str]] = []
    last = first
    for index, row in enumerate(ordered):
        if row["wo_number"]:
            if _number(row) <= last:
                raise ValueError(f"planted work order {row['wo_number']} is out of sequence")
            last = _number(row)
            result.append(row)
            continue
        upcoming = [_number(o) for o in ordered[index + 1 :] if o["wo_number"]]
        limit = min(upcoming) if upcoming else 9999
        candidate = last + r.randint(1, 4)
        if candidate >= limit:
            continue
        row = dict(row, wo_number=f"WO-{year}-{candidate:04d}")
        last = candidate
        result.append(row)
    return result


@cache
def work_order_rows() -> list[dict[str, str]]:
    r = rng("work-orders")
    planted_25: list[dict[str, str]] = []
    # Oil conversion campaign (MOC-2025-012), WO-25-0301 to WO-25-0312.
    for index, turbine in enumerate(TURBINES):
        done = CONVERSION_DATES[turbine]
        planned = done
        remarks = ""
        if turbine == "WTG-09":
            planned = "2025-11-24"
            remarks = "Deferred: access road closed by snow on 2025-11-24; completed 2026-01-20"
        planted_25.append(
            _wo(
                f"WO-25-{301 + index:04d}",
                "2025-08-27",
                turbine,
                "MOD",
                "Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07)",
                "Completed",
                "High",
                "PWS-220-D208",
                "3",
                TECHNICIANS[index % 2],
                planned,
                done,
                "MOC-2025-012",
                remarks,
            )
        )
    routine_tasks = [
        ("MP-GBX-02", "Gearbox oil filter element replacement", "FGT-P-11872", "1"),
        ("MP-GEN-01", "Generator brush inspection", "", ""),
        ("MP-HSE-01", "Rescue kit inspection", "", ""),
        ("MP-YAW-01", "Yaw brake pad inspection", "", ""),
        ("MP-HYD-01", "Hydraulic accumulator pre-charge check", "", ""),
        ("MP-GBX-05", "Gearbox visual inspection and leak check", "", ""),
    ]
    routine_25: list[dict[str, str]] = []
    for month in (9, 10, 11, 12):
        for task, title, part, qty in routine_tasks[:4]:
            day = f"2025-{month:02d}-{r.randint(3, 26):02d}"
            routine_25.append(
                _wo("", day, r.choice(TURBINES), "PM", f"{title} ({task})", "Completed", "Low",
                    part, qty, r.choice(TECHNICIANS), day, day, task)
            )
    routine_26: list[dict[str, str]] = []
    for month in range(1, 9):
        for task, title, part, qty in routine_tasks:
            if r.random() < 0.3:
                continue
            day = f"2026-{month:02d}-{r.randint(2, 27):02d}"
            status, completed = "Completed", day
            if month == 8 and r.random() < 0.5:
                status, completed = "Open", ""
            routine_26.append(
                _wo("", day, r.choice(TURBINES), "PM", f"{title} ({task})", status, "Low",
                    part, qty, r.choice(TECHNICIANS), day, completed, task)
            )
    planted_26: list[dict[str, str]] = [
        _wo("WO-26-0187", "2026-02-20", "WTG-10", "CM", "Replace HSS bearing, generator side",
            "Completed", "High", "FGT-P-22328", "1", "Callum Rydings", "2026-03-11", "2026-03-12",
            "CMS alarm 2026-02-20", "Last spare bearing used"),
        _wo("WO-26-0203", "2026-03-26", "WTG-11", "CM",
            "Install tool tether anchor points at yaw deck hatch", "Completed", "High",
            "AWI-31007", "1", "\u00c9lise Ternaux", "2026-04-02", "2026-04-02", "INC-2026-003"),
        _wo("WO-26-0355", "2026-06-05", "WTG-04", "CM",
            "Replace rotor blade B (trailing-edge crack)",
            "Planned", "High", "", "", "Dario Penwarden", "2026-09-08", "",
            "WBS-2026-031; LP-2026-009"),
        _wo("WO-26-0398", "2026-06-22", "WTG-07", "CM", "Replace oil cooler fan motor",
            "Completed", "High", "LWS-P-30418", "1", "Callum Rydings", "2026-06-24", "2026-06-24",
            "INC-2026-006"),
        _wo("WO-26-0399", "2026-06-22", "WTG-07", "CM", "Clean oil cooler radiator",
            "Completed", "High", "", "", "\u00c9lise Ternaux", "2026-06-24", "2026-06-24",
            "INC-2026-006", "Fins about 40 % blocked by insects and pollen"),
        _wo("WO-26-0412", "2026-06-26", "WTG-07", "CM", "Replace HSS bearing, generator side",
            "Waiting for parts", "High", "FGT-P-22328", "1", "Callum Rydings", "", "",
            "INC-2026-006", "Vibration above alarm level 4.5 mm/s"),
        _wo("WO-26-0430", "2026-07-06", "WTG-01", "PM",
            "Oil cooler radiator cleaning and fan current check (MP-GBX-07)", "Completed",
            "Medium", "", "", "\u00c9lise Ternaux", "2026-07-07", "2026-07-07", "MP-GBX-07"),
        _wo("WO-26-0431", "2026-07-06", "WTG-02", "PM",
            "Oil cooler radiator cleaning and fan current check (MP-GBX-07)", "Completed",
            "Medium", "", "", "\u00c9lise Ternaux", "2026-07-08", "2026-07-08", "MP-GBX-07"),
        _wo("WO-26-0436", "2026-07-16", "WTG-09", "CM", "Replace generator brushes (A3210)",
            "Completed", "Medium", "LWS-P-51207", "1", "\u00c9lise Ternaux", "2026-07-18",
            "2026-07-18", "WI-GEN-014", "Shortest brush 16 mm"),
        _wo("WO-26-0439", "2026-07-24", "WTG-02", "CM",
            "Replace HSS bearing, generator side (spalling found at endoscopy 2026-07-23)",
            "Waiting for parts", "High", "FGT-P-22328", "1", "Callum Rydings", "", "",
            "Endoscope inspection 2026-07-23"),
        _wo("WO-26-0444", "2026-07-27", "WTG-05", "PM", "Rescue kit inspection (MP-HSE-01)",
            "In progress", "Medium", "", "", "Callum Rydings", "2026-08-03", "", "MP-HSE-01"),
        _wo("WO-26-0450", "2026-07-30", "WTG-11", "CM",
            "Replace leaking hydraulic hose, yaw brake circuit", "Waiting for parts", "Medium",
            "AWI-10442", "1", "\u00c9lise Ternaux", "", "", "Shift handover 2026-07-29",
            "Hose not stocked; ordered from distributor"),
    ]
    # Pitch bearing bolt re-torque per SB-LWS-2025-11 Rev. A (MP-PIT-01).
    for index, turbine in enumerate(TURBINES[:6]):
        day = f"2026-05-{4 + 2 * index:02d}"
        planted_26.append(
            _wo(f"WO-26-{301 + index:04d}", "2026-04-20", turbine, "PM",
                "Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01)", "Completed",
                "Medium", "", "", TECHNICIANS[index % 2], day, day, "SB-LWS-2025-11 Rev. A")
        )
    for index, turbine in enumerate(TURBINES[6:]):
        day = f"2026-09-{7 + 2 * index:02d}"
        planted_26.append(
            _wo(f"WO-26-{471 + index:04d}", "2026-08-24", turbine, "PM",
                "Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01)", "Planned",
                "Medium", "", "", TECHNICIANS[index % 2], day, "", "SB-LWS-2025-11 Rev. A")
        )
    # Oil sampling campaign June 2026 (MP-GBX-01).
    for index, turbine in enumerate(TURBINES):
        day = f"2026-06-{8 + index // 3:02d}"
        planted_26.append(
            _wo(f"WO-26-{341 + index:04d}", "2026-05-28", turbine, "PM",
                "Gearbox oil sampling (MP-GBX-01)", "Completed", "Low", "", "",
                "Callum Rydings", day, day, "MP-GBX-01")
        )
    rows = _assign_numbers("25", planted_25, routine_25, 300)
    rows += _assign_numbers("26", planted_26, routine_26, 0)
    return rows


# --------------------------------------------------------------------------------------------
# KPI export (first half of 2026).

KPI_COLUMNS = [
    "month",
    "turbine",
    "availability_pct",
    "energy_mwh",
    "downtime_h",
    "alarm_count",
]
_CAPACITY_FACTOR = {1: 0.41, 2: 0.38, 3: 0.35, 4: 0.30, 5: 0.25, 6: 0.22}
_HOURS = {1: 744, 2: 672, 3: 744, 4: 720, 5: 744, 6: 720}
_PLANTED_AVAILABILITY = {
    ("2026-01", "WTG-09"): 96.1,
    ("2026-03", "WTG-10"): 93.8,
    ("2026-05", "WTG-07"): 95.2,
    ("2026-06", "WTG-07"): 90.4,
}


@cache
def kpi_rows() -> list[dict[str, str]]:
    r = rng("kpi-2026-h1")
    factors = {t: r.uniform(0.95, 1.05) for t in TURBINES}
    rows: list[dict[str, str]] = []
    for month in range(1, 7):
        key = f"2026-{month:02d}"
        for turbine in TURBINES:
            drawn = round(r.uniform(97.4, 99.4), 1)
            availability = _PLANTED_AVAILABILITY.get((key, turbine), drawn)
            hours = _HOURS[month]
            energy = 3.2 * hours * _CAPACITY_FACTOR[month] * factors[turbine] * availability / 100
            if turbine == "WTG-07" and month == 6:
                energy *= 0.86
            alarms = r.randint(6, 26)
            if turbine == "WTG-07" and month in (5, 6):
                alarms = {5: 31, 6: 38}[month]
            rows.append(
                {
                    "month": key,
                    "turbine": turbine,
                    "availability_pct": f"{availability:.1f}",
                    "energy_mwh": f"{energy:.1f}",
                    "downtime_h": f"{hours * (1 - availability / 100):.1f}",
                    "alarm_count": str(alarms),
                }
            )
    return rows
