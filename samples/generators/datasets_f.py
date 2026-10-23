"""Tables of the slice F documents (résidence Les Nacrines, école de Montferrine, entreprise),
derived from the bible facts with arithmetic checks.

As in :mod:`.datasets`, every printed number comes from ``samples/fiction/bible.yaml``; these
helpers recompute what the bible states (totals, VAT, retention, cumulative amounts, positions,
overdue dates, the one double booking) so that a typo in the bible fails the build.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .common import dec, parse_day
from .datasets import cents, expect, invoice, share
from .world import World

# ------------------------------------------------------------------------------------------
# Generic priced lines


@dataclass(frozen=True)
class Line:
    ref: str
    designation: str
    unit: str
    qty: int | float
    unit_price: Decimal
    total: Decimal


def priced_lines(label: str, raw_lines: list[dict[str, Any]], key: str | None = None) -> list[Line]:
    """Lines whose total is quantity x unit price; ``key`` selects an indice (``a``/``b``)."""
    lines: list[Line] = []
    for raw in raw_lines:
        values = raw if key is None else raw.get(key)
        if values is None:
            continue
        designation = (raw.get(f"designation_{key}") if key else None) or raw["designation"]
        total = expect(f"{label} line {raw.get('ref', designation)}", values["total"],
                       cents(dec(values["qty"]) * dec(values["unit_price"])))
        lines.append(Line(str(raw.get("ref") or raw.get("code") or "-"), str(designation),
                          str(raw["unit"]), values["qty"], dec(values["unit_price"]), total))
    return lines


def totals(label: str, stated: dict[str, Any], lines: list[Line], rate: int) -> dict[str, Decimal]:
    ht = expect(f"{label} HT", stated["ht"], sum((line.total for line in lines), Decimal(0)))
    vat = expect(f"{label} VAT", stated["vat"], share(ht, rate))
    ttc = expect(f"{label} TTC", stated["ttc"], ht + vat)
    return {"ht": ht, "vat": vat, "ttc": ttc}


def percent_text(value: Decimal) -> str:
    """``18,9 %`` (one decimal, half up)."""
    rounded = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return f"{rounded} %".replace(".", ",")


# ------------------------------------------------------------------------------------------
# Résidence Les Nacrines


def nacrines_marche(w: World) -> tuple[list[Line], dict[str, Decimal]]:
    facts = w.facts["nacrines"]["marche"]
    lines = priced_lines("marché Nacrines", facts["lines"])
    sums = totals("marché Nacrines", facts["totals"], lines, int(facts["totals"]["vat_rate"]))
    start, end = parse_day(str(facts["start"])), parse_day(str(facts["completion"]))
    if (end - start).days > int(facts["duration_weeks"]) * 7:
        raise ValueError("bible: the Nacrines completion is later than the contract duration")
    return lines, sums


def nacrines_os1(w: World) -> tuple[list[Line], dict[str, Decimal]]:
    facts = w.facts["nacrines"]["os1"]
    lines = priced_lines("OS n°1", facts["lines"])
    sums = totals("OS n°1", facts["totals"], lines, int(facts["totals"]["vat_rate"]))
    _, marche = nacrines_marche(w)
    new = facts["new_contract_total"]
    expect("Nacrines total HT after OS n°1", new["ht"], marche["ht"] + sums["ht"])
    expect("Nacrines total TTC after OS n°1", new["ttc"], marche["ttc"] + sums["ttc"])
    completion = parse_day(str(w.facts["nacrines"]["marche"]["completion"]))
    if (parse_day(str(facts["new_completion"])) - completion).days != int(facts["delay_days"]):
        raise ValueError("bible: the OS n°1 completion does not add its delay")
    expect("penalty per day", facts["derived_not_printed"]["penalties_per_day_before_os"],
           cents(marche["ht"] / 1000))
    return lines, sums


@dataclass(frozen=True)
class SituationRow:
    ref: str
    designation: str
    amount: Decimal
    progress: int
    cumul: Decimal


def nacrines_situation(w: World) -> tuple[list[SituationRow], dict[str, Decimal]]:
    facts = w.facts["nacrines"]
    sit = facts["situation4"]
    marche_lines, marche = nacrines_marche(w)
    os_lines, os_sums = nacrines_os1(w)
    rate = int(facts["marche"]["totals"]["vat_rate"])
    retention_rate = int(facts["marche"]["retention_percent"])
    rows: list[SituationRow] = []
    for line in [*marche_lines, *os_lines]:
        progress = int(sit["progress"][line.ref])
        rows.append(SituationRow(line.ref, line.designation, line.total, progress,
                                 cents(line.total * progress / 100)))
    if {row.ref for row in rows} != set(sit["progress"]):
        raise ValueError("bible: situation n°4 progress keys differ from the priced lines")
    cumul = expect("situation 4 cumul", sit["cumul_ht"], sum((r.cumul for r in rows), Decimal(0)))
    total_ht = marche["ht"] + os_sums["ht"]
    situations = facts["situations"]
    previous_cumul = Decimal(0)
    retention_sum = Decimal(0)
    for raw in situations:
        label = f"situation {raw['n']}"
        ht = expect(f"{label} HT", raw["ht"], dec(raw["cumul_ht"]) - previous_cumul)
        vat = expect(f"{label} VAT", raw["vat"], share(ht, rate))
        ttc = expect(f"{label} TTC", raw["ttc"], ht + vat)
        retention = expect(f"{label} retention", raw["retention"], share(ttc, retention_rate))
        expect(f"{label} net", raw["net"], ttc - retention)
        previous_cumul = dec(raw["cumul_ht"])
        retention_sum += retention
    last = situations[-1]
    if int(last["n"]) != int(sit["number"]):
        raise ValueError("bible: the last invoiced situation is not situation n°4")
    expect("situation 4 cumul vs invoices", last["cumul_ht"], cumul)
    previous = sit["previous"]
    expect("situations n°1 to n°3", previous["cumul_ht"], dec(situations[-2]["cumul_ht"]))
    this_ht = expect("situation 4 amount", sit["this_ht"], cumul - dec(previous["cumul_ht"]))
    vat = expect("situation 4 VAT", sit["vat"], share(this_ht, rate))
    ttc = expect("situation 4 TTC", sit["ttc"], this_ht + vat)
    retention = expect("situation 4 retention", sit["retention"], share(ttc, retention_rate))
    net = expect("situation 4 net", sit["net"], ttc - retention)
    retention_cumul = expect("retention to date", sit["retention_cumul"], retention_sum)
    left = expect("left to bill HT", sit["left_to_bill_ht"], total_ht - cumul)
    for sub in sit["subcontract"]:
        expect("Adatum statement cumul", sub["cumul_ht"],
               cents(dec(sub["amount_ht"]) * int(sub["progress"]) / 100))
        expect("Adatum subcontract amount", sub["amount_ht"],
               dec(facts["sous_traitance"]["price_ht"]))
    return rows, {
        "marche_ht": marche["ht"], "os_ht": os_sums["ht"], "total_ht": total_ht, "cumul": cumul,
        "previous": dec(previous["cumul_ht"]), "this_ht": this_ht, "vat": vat, "ttc": ttc,
        "retention": retention, "net": net, "retention_cumul": retention_cumul, "left": left,
    }


def framework_prices(w: World) -> dict[str, Decimal]:
    """Net framework prices by article code (and ``None`` for the delivery fee)."""
    rows = w.facts["entreprise"]["tarif"]["rows"]
    prices: dict[str, Decimal] = {}
    codes = {p.get("code"): p for p in w.data["products"] if p.get("code")}
    for row in rows:
        if dec(row["net"]) >= dec(row["public"]):
            raise ValueError(f"bible: tarif net price not below the public price for {row['code']}")
        code = row["code"]
        if code is not None:
            product = codes.get(code)
            if product is None:
                raise ValueError(f"bible: tarif code {code} is not a product")
            stated = product["attributes"].get("framework_net_price_ht")
            if stated is not None:
                expect(f"product {code} framework price", stated, dec(row["net"]))
        prices[str(code)] = dec(row["net"])
    expect("framework delivery fee", w.facts["entreprise"]["contrat_cadre"]["delivery_fee_ht"],
           prices["None"])
    return prices


def nacrines_invoice(w: World) -> tuple[list[Line], dict[str, Decimal]]:
    facts = w.facts["nacrines"]["zava_invoice"]
    lines = priced_lines("invoice FA-2026-0158", facts["lines"])
    sums = totals("invoice FA-2026-0158", facts["totals"], lines, int(facts["totals"]["vat_rate"]))
    prices = framework_prices(w)
    gaps = [
        (raw, dec(raw["unit_price"]) - prices[str(raw["code"])])
        for raw in facts["lines"]
        if dec(raw["unit_price"]) != prices[str(raw["code"])]
    ]
    if len(gaps) != 1:
        raise ValueError("bible: FA-2026-0158 must differ from the framework prices on one line")
    raw, gap = gaps[0]
    derived = facts["derived_not_printed"]
    expect("FA-2026-0158 unit gap", derived["framework_gap_unit"], gap)
    expect("FA-2026-0158 gap", derived["framework_gap_ht"], cents(gap * dec(raw["qty"])))
    return lines, sums


def moreau_framework_gap(w: World) -> Decimal:
    """FA-2026-0217 against the framework prices: one line differs (the blocks)."""
    lines, _, _, _ = invoice(w)
    prices = framework_prices(w)
    gaps = [(line, line.unit_price - prices[str(line.code)]) for line in lines
            if line.unit_price != prices[str(line.code)]]
    if len(gaps) != 1 or gaps[0][0].code != "ZM-20450":
        raise ValueError("bible: FA-2026-0217 must differ from the framework prices on the blocks")
    line, gap = gaps[0]
    derived = w.facts["entreprise"]["tarif"]["derived_not_printed"]
    expect("FA-2026-0217 unit gap", derived["moreau_gap_unit"], gap)
    return expect("FA-2026-0217 gap", derived["moreau_gap_ht"], cents(gap * dec(line.qty)))


# ------------------------------------------------------------------------------------------
# École de Montferrine


def dpgf(w: World, indice: str) -> tuple[list[Line], dict[str, Decimal]]:
    facts = w.facts["ecole"]["dpgf"]
    key = indice.lower()
    lines = priced_lines(f"DPGF {key}", facts["lines"], key)
    sums = totals(f"DPGF {key}", facts[f"indice_{key}"]["totals"], lines, int(facts["vat_rate"]))
    return lines, sums


def check_ecole(w: World) -> None:
    facts = w.facts["ecole"]
    _, a = dpgf(w, "a")
    _, b = dpgf(w, "b")
    diff = facts["dpgf"]["indice_b"]["difference_from_a"]
    expect("DPGF difference HT", diff["ht"], b["ht"] - a["ht"])
    expect("DPGF difference TTC", diff["ttc"], b["ttc"] - a["ttc"])
    price = facts["acte_engagement"]["price"]
    for field in ("ht", "vat", "ttc"):
        expect(f"acte d'engagement {field}", price[field], b[field])
    order = facts["bon_de_commande"]
    lines = priced_lines("BC-2026-021", order["lines"])
    rate = int(order["totals"]["vat_rate"])
    sums = totals("BC-2026-021", order["totals"], lines, rate)
    expect("BC-2026-021 deposit", order["deposit"]["amount_ht"],
           share(sums["ht"], order["deposit"]["percent"]))
    windows = next(line for line in lines)
    dpgf_windows = next(line for line in dpgf(w, "b")[0] if line.ref == "3")
    if windows.qty != dpgf_windows.qty:
        raise ValueError("bible: the school order and DPGF item 3 count different windows")
    tasks = facts["planning"]["tasks"]
    delivery = next(t for t in tasks if t["id"] == "T03")
    if str(delivery["start"]) != str(order["delivery"]):
        raise ValueError("bible: the school planning delivery differs from the order")
    for task in tasks:
        if parse_day(str(task["end"])) < parse_day(str(task["start"])):
            raise ValueError(f"bible: school task {task['id']} ends before it starts")


# ------------------------------------------------------------------------------------------
# Entreprise


def billing_position(w: World) -> dict[str, dict[str, Decimal]]:
    """Per chantier: total, billed, retained and left to bill, from the billing register rows."""
    facts = w.facts["entreprise"]["suivi_facturation"]
    contrat, avenant = w.facts["contrat"], w.facts["avenant"]
    marches = {row["chantier"]: row for row in facts["marches"]}
    moreau = marches["moreau"]
    expect("register Moreau initial", moreau["initial_ht"], dec(contrat["price"]["ht"]))
    expect("register Moreau avenant", moreau["changes_ht"], dec(avenant["totals"]["ht"]))
    expect("register Moreau TTC", moreau["total_ttc"], dec(avenant["new_contract_total"]["ttc"]))
    _, marche = nacrines_marche(w)
    _, os_sums = nacrines_os1(w)
    nac = marches["nacrines"]
    expect("register Nacrines initial", nac["initial_ht"], marche["ht"])
    expect("register Nacrines OS", nac["changes_ht"], os_sums["ht"])
    _, b = dpgf(w, "b")
    eco = marches["ecole-montferrine"]
    expect("register school initial", eco["initial_ht"], b["ht"])
    for code, row in marches.items():
        total_ht = expect(f"register {code} total HT", row["total_ht"],
                          dec(row["initial_ht"]) + dec(row["changes_ht"]))
        expect(f"register {code} TTC", row["total_ttc"], total_ht + dec(row["vat"]))
    acompte = facts["moreau_invoice"]
    deposit = contrat["deposit"]
    expect("Moreau acompte TTC", acompte["ttc"], dec(deposit["amount"]))
    expect("Moreau acompte HT", acompte["ht"], share(dec(contrat["price"]["ht"]),
                                                     deposit["percent"]))
    expect("Moreau acompte VAT", acompte["vat"], dec(acompte["ttc"]) - dec(acompte["ht"]))
    expect("Moreau acompte net", acompte["net"], dec(acompte["ttc"]) - dec(acompte["retention"]))
    invoices: dict[str, list[dict[str, Any]]] = {code: [] for code in marches}
    invoices["moreau"].append(acompte)
    invoices["nacrines"] += w.facts["nacrines"]["situations"]
    positions: dict[str, dict[str, Decimal]] = {}
    derived = facts["derived_not_printed"]["position"]
    for code, row in marches.items():
        billed_ttc = sum((dec(i["ttc"]) for i in invoices[code]), Decimal(0))
        billed_ht = sum((dec(i["ht"]) for i in invoices[code]), Decimal(0))
        retained = sum((dec(i["retention"]) for i in invoices[code]), Decimal(0))
        position = {
            "total_ttc": dec(row["total_ttc"]), "billed_ttc": billed_ttc, "retained": retained,
            "left_to_bill_ttc": dec(row["total_ttc"]) - billed_ttc,
            "total_ht": dec(row["total_ht"]), "billed_ht": billed_ht,
            "left_to_bill_ht": dec(row["total_ht"]) - billed_ht,
        }
        for field, value in position.items():
            expect(f"position {code} {field}", derived[code][field], value)
        positions[code] = position
    return positions


def check_margins(w: World) -> None:
    facts = w.facts["entreprise"]["tableau_marges"]
    positions = billing_position(w)
    sums = {field: Decimal(0) for field in ("contract_ht", "planned_cost_ht", "planned_margin_ht",
                                            "actual_cost_ht", "billed_ht", "margin_to_date_ht")}
    for row in facts["rows"]:
        code = row["chantier"]
        expect(f"margins {code} contract", row["contract_ht"], positions[code]["total_ht"])
        expect(f"margins {code} billed", row["billed_ht"], positions[code]["billed_ht"])
        margin = expect(f"margins {code} planned margin", row["planned_margin_ht"],
                        dec(row["contract_ht"]) - dec(row["planned_cost_ht"]))
        if percent_text(margin / dec(row["contract_ht"]) * 100) != row["rate"]:
            raise ValueError(f"bible arithmetic: margin rate of {code}")
        expect(f"margins {code} margin to date", row["margin_to_date_ht"],
               dec(row["billed_ht"]) - dec(row["actual_cost_ht"]))
        for field in sums:
            sums[field] += dec(row[field])
    total = facts["totals"]
    for field, value in sums.items():
        expect(f"margins total {field}", total[field], value)
    if percent_text(sums["planned_margin_ht"] / sums["contract_ht"] * 100) != total["rate"]:
        raise ValueError("bible arithmetic: total margin rate")


def crew_double_bookings(w: World) -> list[tuple[str, str, str, date, date]]:
    """(person, chantier A, chantier B, first day, last day) for overlapping bookings."""
    rows = w.facts["entreprise"]["planning_equipes"]["rows"]
    found = []
    for i, first in enumerate(rows):
        for second in rows[i + 1 :]:
            if first["person"] != second["person"] or first["chantier"] == second["chantier"]:
                continue
            start = max(parse_day(str(first["start"])), parse_day(str(second["start"])))
            end = min(parse_day(str(first["end"])), parse_day(str(second["end"])))
            if start <= end:
                found.append((first["person"], first["chantier"], second["chantier"], start, end))
    return found


def overdue_equipment(w: World) -> list[tuple[str, int]]:
    """(code, days overdue) at the date of the equipment register."""
    day = parse_day(str(w.facts["entreprise"]["registre_materiel"]["date"]))
    late = []
    for item in w.data["equipment"]:
        if item.get("next_inspection") and parse_day(str(item["next_inspection"])) < day:
            late.append((str(item["code"]), (day - parse_day(str(item["next_inspection"]))).days))
    return late


def check_entreprise(w: World) -> None:
    facts = w.facts["entreprise"]
    billing_position(w)
    check_margins(w)
    framework_prices(w)
    moreau_framework_gap(w)
    bookings = crew_double_bookings(w)
    booked = facts["planning_equipes"]["derived_not_printed"]["double_booking"]
    if [(p, start.isoformat(), end.isoformat()) for p, _, _, start, end in bookings] != [
        (booked["person"], str(booked["start"]), str(booked["end"]))
    ]:
        raise ValueError(f"bible: the crew schedule must have one double booking, found {bookings}")
    overdue = facts["registre_materiel"]["derived_not_printed"]["overdue"]
    if overdue_equipment(w) != [(overdue["code"], int(overdue["days_overdue_at_register_date"]))]:
        raise ValueError(f"bible: one overdue inspection expected, found {overdue_equipment(w)}")
    situation = facts["registre_attestations"]["derived_not_printed"]["adatum_situation"]
    vigilance = [row for row in facts["registre_attestations"]["rows"]
                 if row["org"] == "adatum-electricite" and row["document"].startswith(
                     "Attestation de vigilance")]
    at = parse_day(str(situation["date"]))
    valid = [row for row in vigilance
             if parse_day(str(row["issued"])) <= at <= parse_day(str(row["valid_until"]))]
    if valid or situation["valid_at_situation"]:
        raise ValueError("bible: Adatum's attestation must be expired at its situation date")
    statement = w.facts["nacrines"]["situation4"]["subcontract"][0]
    if str(statement["date"]) != str(situation["date"]):
        raise ValueError("bible: Adatum's situation date differs from situation n°4")
    reserves = w.facts["nacrines"]["reserves"]
    lifted = sum(1 for row in reserves["rows"] if row["lifted"])
    if (lifted, len(reserves["rows"]) - lifted) != (reserves["lifted_count"],
                                                     reserves["open_count"]):
        raise ValueError("bible: réserves counts")


def check_world_f(w: World) -> None:
    """Recompute every total of the slice F facts (raises ValueError on the first mismatch)."""
    nacrines_situation(w)
    nacrines_invoice(w)
    check_ecole(w)
    check_entreprise(w)
