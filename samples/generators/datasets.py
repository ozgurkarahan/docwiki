"""Document tables derived from the bible facts, with arithmetic checks.

Every number printed by the generators comes from ``samples/fiction/bible.yaml``. These helpers
select the rows of one document and recompute the totals the bible states, so a typo in the
bible fails the build instead of producing an inconsistent document (errors surface).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .common import dec, parse_day
from .world import World

CENT = Decimal("0.01")


def cents(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def share(base: Decimal, rate: int | float | Decimal) -> Decimal:
    """``rate`` percent of ``base``, rounded half up to the cent."""
    return cents(base * dec(rate) / 100)


def expect(label: str, stated: Any, computed: Decimal) -> Decimal:
    """The bible value, after checking that it equals the computed one."""
    value = dec(stated)
    if value != computed:
        raise ValueError(f"bible arithmetic: {label} is {value}, computed {computed}")
    return value


def lot_label(numbers: list[int]) -> str:
    """``lot 8`` or ``lots 1 à 7`` (contiguous) or ``lots 2, 5 et 7``."""
    numbers = sorted(numbers)
    if len(numbers) == 1:
        return f"lot {numbers[0]}"
    if numbers == list(range(numbers[0], numbers[-1] + 1)):
        return f"lots {numbers[0]} à {numbers[-1]}"
    return "lots " + ", ".join(str(n) for n in numbers[:-1]) + f" et {numbers[-1]}"


# ------------------------------------------------------------------------------------------
# Quote (devis), indice A and B


@dataclass(frozen=True)
class QuoteLine:
    ref: str
    lot: int
    designation: str
    unit: str
    qty: int | float
    unit_price: Decimal
    total: Decimal


@dataclass(frozen=True)
class VatLine:
    rate: int
    lots: list[int]
    base: Decimal
    amount: Decimal


@dataclass(frozen=True)
class Quote:
    indice: str
    date: str
    lines: list[QuoteLine]
    lot_subtotals: dict[int, Decimal]
    ht: Decimal
    vat: list[VatLine]
    vat_total: Decimal
    ttc: Decimal

    def lines_of(self, lot: int) -> list[QuoteLine]:
        return [line for line in self.lines if line.lot == lot]


def quote(w: World, indice: str) -> Quote:
    facts = w.facts["devis"]
    key = indice.lower()
    data = facts[f"indice_{key}"]
    lines: list[QuoteLine] = []
    for raw in facts["lines"]:
        values = raw.get(key)
        if values is None:
            continue
        designation = raw.get(f"designation_{key}") or raw["designation"]
        total = expect(
            f"devis {key} line {raw['ref']}",
            values["total"],
            cents(dec(values["qty"]) * dec(values["unit_price"])),
        )
        lines.append(QuoteLine(str(raw["ref"]), int(raw["lot"]), designation, str(raw["unit"]),
                               values["qty"], dec(values["unit_price"]), total))
    subtotals: dict[int, Decimal] = {}
    for lot in w.lots:
        number = int(lot["lot"])
        computed = sum((line.total for line in lines if line.lot == number), Decimal(0))
        subtotals[number] = expect(f"devis {key} lot {number}", data["lot_subtotals"][number],
                                   computed)
    totals = data["totals"]
    ht = expect(f"devis {key} HT", totals["ht"], sum(subtotals.values(), Decimal(0)))
    vat: list[VatLine] = []
    for rate in sorted({int(lot["vat_rate"]) for lot in w.lots}, reverse=True):
        numbers = [int(lot["lot"]) for lot in w.lots if int(lot["vat_rate"]) == rate]
        base = expect(f"devis {key} VAT {rate} base", totals[f"vat_{rate}_base"],
                      sum((subtotals[n] for n in numbers), Decimal(0)))
        amount = expect(f"devis {key} VAT {rate}", totals[f"vat_{rate}"], share(base, rate))
        vat.append(VatLine(rate, numbers, base, amount))
    vat_total = expect(f"devis {key} VAT total", totals["vat_total"],
                       sum((line.amount for line in vat), Decimal(0)))
    ttc = expect(f"devis {key} TTC", totals["ttc"], ht + vat_total)
    return Quote(key, str(data["date"]), lines, subtotals, ht, vat, vat_total, ttc)


def check_quote_difference(w: World) -> None:
    a, b = quote(w, "a"), quote(w, "b")
    diff = w.facts["devis"]["indice_b"]["difference_from_a"]
    expect("devis difference HT", diff["ht"], b.ht - a.ht)
    expect("devis difference TTC", diff["ttc"], b.ttc - a.ttc)


# ------------------------------------------------------------------------------------------
# Works contract and amendment


def check_contract(w: World) -> None:
    facts = w.facts["contrat"]
    b = quote(w, "b")
    expect("contract HT", facts["price"]["ht"], b.ht)
    ttc = expect("contract TTC", facts["price"]["ttc"], b.ttc)
    schedule = facts["payment_schedule"]
    if sum(int(item["percent"]) for item in schedule) != 100:
        raise ValueError("bible arithmetic: the payment schedule does not add up to 100 %")
    for item in schedule:
        expect(f"payment {item['n']}", item["amount"], share(ttc, item["percent"]))
    expect("payment schedule total", ttc, sum((dec(i["amount"]) for i in schedule), Decimal(0)))
    first, last = schedule[0], schedule[-1]
    expect("deposit", facts["deposit"]["amount"], dec(first["amount"]))
    expect("retention", facts["retention"]["amount"], dec(last["amount"]))
    if int(facts["deposit"]["percent"]) != int(first["percent"]):
        raise ValueError("bible: deposit percent differs from the payment schedule")
    if int(facts["retention"]["percent"]) != int(last["percent"]):
        raise ValueError("bible: retention percent differs from the payment schedule")
    start = parse_day(str(facts["start"]))
    end = parse_day(str(facts["planned_completion"]))
    if (end - start).days > int(facts["duration_weeks"]) * 7:
        raise ValueError("bible: the planned completion is later than the contract duration")


def check_amendment(w: World) -> None:
    facts = w.facts["avenant"]
    total = Decimal(0)
    for line in facts["lines"]:
        total += expect(f"avenant {line['ref']}", line["total"],
                        cents(dec(line["qty"]) * dec(line["unit_price"])))
    totals = facts["totals"]
    ht = expect("avenant HT", totals["ht"], total)
    vat = expect("avenant VAT", totals["vat"], share(ht, totals["vat_rate"]))
    ttc = expect("avenant TTC", totals["ttc"], ht + vat)
    initial = facts["initial_contract"]
    expect("avenant initial HT", initial["ht"], dec(w.facts["contrat"]["price"]["ht"]))
    expect("avenant initial TTC", initial["ttc"], dec(w.facts["contrat"]["price"]["ttc"]))
    expect("new contract HT", facts["new_contract_total"]["ht"], dec(initial["ht"]) + ht)
    expect("new contract TTC", facts["new_contract_total"]["ttc"], dec(initial["ttc"]) + ttc)
    retention = int(w.facts["contrat"]["retention"]["percent"])
    derived = facts["derived_not_printed"]
    on_amendment = expect("retention on the amendment", derived["retention_on_amendment"],
                          share(ttc, retention))
    expect("total retention", derived["total_retention_after_amendment"],
           dec(w.facts["contrat"]["retention"]["amount"]) + on_amendment)


# ------------------------------------------------------------------------------------------
# Planning and purchase tracking (PLN), indice A and B


def org_label(w: World, value: str) -> str:
    """An organisation key, optionally followed by words (``lamna-batiment et clients``)."""
    key, _, rest = value.partition(" ")
    name = w.org_name(key)
    return f"{name} {rest}" if rest else name


@dataclass(frozen=True)
class Task:
    id: str
    task: str
    lot: str
    by: str
    start: date
    end: date
    progress: int
    note: str


@dataclass(frozen=True)
class Purchase:
    order: str
    date: date
    supplier: str
    object: str
    ordered_ht: Decimal
    invoiced_ht: Decimal
    status: str


def planning_tasks(w: World, indice: str) -> list[Task]:
    facts = w.facts["planning"]
    key = indice.lower()
    by_id = {str(task["id"]): task for task in facts["tasks"]}
    tasks: list[Task] = []
    for task_id in facts[f"indice_{key}"]["row_order"]:
        raw = by_id[str(task_id)]
        values = raw[key]
        start, end = parse_day(str(values["start"])), parse_day(str(values["end"]))
        if end < start:
            raise ValueError(f"bible: task {task_id} ends before it starts")
        note = str(values.get("note") or raw.get("note") or "")
        tasks.append(Task(str(task_id), str(raw["task"]), str(raw["lot"]),
                          org_label(w, str(raw["by"])), start, end, int(values["progress"]),
                          note))
    expected = {str(t["id"]) for t in facts["tasks"] if key in t}
    if {task.id for task in tasks} != expected:
        raise ValueError(f"bible: row_order of planning indice {key} misses tasks")
    data = facts[f"indice_{key}"]
    windows = next(task for task in tasks if task.id == "T07")
    install = next(task for task in tasks if task.id == "T08")
    handover = next(task for task in tasks if task.id == "T17")
    if windows.start.isoformat() != str(data["windows_delivery"]):
        raise ValueError(f"bible: planning {key} window delivery differs from task T07")
    if (install.start.isoformat(), install.end.isoformat()) != (
        str(data["windows_installation"]["start"]), str(data["windows_installation"]["end"])
    ):
        raise ValueError(f"bible: planning {key} window installation differs from task T08")
    if handover.start.isoformat() != str(data["planned_handover"]):
        raise ValueError(f"bible: planning {key} handover differs from task T17")
    return tasks


def purchases(w: World, indice: str) -> tuple[list[Purchase], Decimal, Decimal]:
    facts = w.facts["planning"]
    key = indice.lower()
    rows = [
        Purchase(str(raw["order"]), parse_day(str(raw["date"])), w.org_name(str(raw["supplier"])),
                 str(raw["object"]), dec(raw["ordered_ht"]), dec(raw[key]["invoiced_ht"]),
                 str(raw[key]["status"]))
        for raw in facts["purchases"]
    ]
    totals = facts[f"indice_{key}"]["purchase_totals"]
    ordered = expect(f"planning {key} ordered", totals["ordered_ht"],
                     sum((row.ordered_ht for row in rows), Decimal(0)))
    invoiced = expect(f"planning {key} invoiced", totals["invoiced_ht"],
                      sum((row.invoiced_ht for row in rows), Decimal(0)))
    return rows, ordered, invoiced


# ------------------------------------------------------------------------------------------
# Builders' merchant: invoice and delivery note


@dataclass(frozen=True)
class InvoiceLine:
    code: str | None
    designation: str
    qty: int | float
    unit: str
    unit_price: Decimal
    total: Decimal


def invoice(w: World) -> tuple[list[InvoiceLine], Decimal, Decimal, Decimal]:
    facts = w.facts["zava_invoice"]
    lines = [
        InvoiceLine(raw.get("code"), str(raw["designation"]), raw["qty"], str(raw["unit"]),
                    dec(raw["unit_price"]),
                    expect(f"invoice line {raw['designation']}", raw["total"],
                           cents(dec(raw["qty"]) * dec(raw["unit_price"]))))
        for raw in facts["lines"]
    ]
    totals = facts["totals"]
    ht = expect("invoice HT", totals["ht"], sum((line.total for line in lines), Decimal(0)))
    vat = expect("invoice VAT", totals["vat"], share(ht, totals["vat_rate"]))
    ttc = expect("invoice TTC", totals["ttc"], ht + vat)
    expect(f"invoice vs order {facts['order']}", ht, _ordered(w, str(facts["order"])))
    derived = facts["derived_not_printed"]
    delivery = w.facts["zava_delivery"]
    missing = int(delivery["missing_pallets"])
    if int(derived["overbilled_pallets"]) != missing:
        raise ValueError("bible: overbilled pallets differ from the missing pallets")
    pallets = next(line for line in lines if line.unit == "palette")
    if int(pallets.qty) - missing != int(delivery["delivered_pallets"]):
        raise ValueError("bible: delivered pallets do not match the billed and missing pallets")
    over_ht = expect("overbilled HT", derived["overbilled_ht"], pallets.unit_price * missing)
    over_vat = expect("overbilled VAT", derived["overbilled_vat"],
                      share(over_ht, totals["vat_rate"]))
    expect("overbilled TTC", derived["overbilled_ttc"], over_ht + over_vat)
    expect("corrected HT", derived["corrected_ht"], ht - over_ht)
    expect("corrected TTC", derived["corrected_ttc"], ttc - over_ht - over_vat)
    return lines, ht, vat, ttc


def _ordered(w: World, order: str) -> Decimal:
    rows = [raw for raw in w.facts["planning"]["purchases"] if raw["order"] == order]
    if len(rows) != 1:
        raise ValueError(f"bible: order {order} is not in the purchase tracking")
    return dec(rows[0]["ordered_ht"])


def check_delivery(w: World) -> None:
    delivery = w.facts["zava_delivery"]
    invoice_lines = {line["code"]: line for line in w.facts["zava_invoice"]["lines"]}
    for line in delivery["printed_lines"]:
        billed = invoice_lines[line["code"]]
        if (billed["qty"], billed["unit"]) != (line["qty"], line["unit"]):
            raise ValueError(f"bible: delivery line {line['code']} differs from the invoice")
    pallet = next(line for line in delivery["printed_lines"] if line["unit"] == "palette")
    product = next(p for p in w.data["products"] if p.get("code") == pallet["code"])
    match = re.search(r"\d+", str(product["attributes"]["sale_unit"]))
    if match is None:
        raise ValueError("bible: the block sale unit does not state the blocks per pallet")
    blocks_per_pallet = int(match.group())
    if int(delivery["blocks_delivered"]) != int(delivery["delivered_pallets"]) * blocks_per_pallet:
        raise ValueError("bible: delivered blocks differ from the blocks per delivered pallet")
    if int(pallet["qty"]) != int(delivery["delivered_pallets"]) + int(
        delivery["missing_pallets"]
    ):
        raise ValueError("bible: printed pallets differ from delivered plus missing pallets")


# ------------------------------------------------------------------------------------------
# Restricted internal price study


@dataclass(frozen=True)
class StudyLot:
    lot: int
    title: str
    sale_ht: Decimal
    materials_ht: Decimal
    hours: int
    labour_ht: Decimal
    subcontract_ht: Decimal
    direct_cost_ht: Decimal
    gross_margin_ht: Decimal


def price_study(w: World) -> tuple[list[StudyLot], dict[str, Decimal]]:
    facts = w.facts["etude_de_prix"]
    hourly = dec(facts["hourly_cost"])
    b = quote(w, "b")
    lots: list[StudyLot] = []
    for raw in facts["lots"]:
        number = int(raw["lot"])
        sale = expect(f"study lot {number} sale", raw["sale_ht"], b.lot_subtotals[number])
        labour = expect(f"study lot {number} labour", raw["labour_ht"],
                        cents(hourly * int(raw["hours"])))
        direct = expect(
            f"study lot {number} direct cost",
            raw["direct_cost_ht"],
            dec(raw["materials_ht"]) + labour + dec(raw["subcontract_ht"]),
        )
        margin = expect(f"study lot {number} margin", raw["gross_margin_ht"], sale - direct)
        lots.append(StudyLot(number, str(w.lot(number)["title"]), sale,
                             dec(raw["materials_ht"]), int(raw["hours"]), labour,
                             dec(raw["subcontract_ht"]), direct, margin))
    totals = facts["totals"]
    sums: dict[str, Decimal] = {}
    for field in ("sale_ht", "materials_ht", "labour_ht", "subcontract_ht", "direct_cost_ht",
                  "gross_margin_ht"):
        sums[field] = expect(f"study total {field}", totals[field],
                             sum((getattr(lot, field) for lot in lots), Decimal(0)))
    sums["hours"] = expect("study total hours", totals["hours"],
                           Decimal(sum(lot.hours for lot in lots)))
    overheads = expect("study overheads", totals["overheads_ht"],
                       share(sums["direct_cost_ht"], facts["overheads_percent"]))
    cost_price = expect("study cost price", totals["cost_price_ht"],
                        sums["direct_cost_ht"] + overheads)
    net = expect("study net margin", totals["net_margin_ht"], sums["sale_ht"] - cost_price)
    rate = (net / sums["sale_ht"] * 100).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    if f"{rate} %".replace(".", ",") != totals["net_margin_percent"]:
        raise ValueError("bible arithmetic: net margin percent")
    coefficient = (sums["sale_ht"] / sums["direct_cost_ht"]).quantize(
        CENT, rounding=ROUND_HALF_UP
    )
    if str(coefficient).replace(".", ",") != totals["sale_coefficient"]:
        raise ValueError("bible arithmetic: sale coefficient")
    subcontractor = w.org_by_role("electrical-subcontractor")["key"]
    orders = [p for p in w.facts["planning"]["purchases"] if p["supplier"] == subcontractor]
    expect("study subcontracting vs the electrical order", sums["subcontract_ht"],
           sum((dec(p["ordered_ht"]) for p in orders), Decimal(0)))
    sums.update(overheads_ht=overheads, cost_price_ht=cost_price, net_margin_ht=net,
                hourly_cost=hourly)
    return lots, sums


def check_world(w: World) -> None:
    """Recompute every total of the bible facts (raises ValueError on the first mismatch)."""
    quote(w, "a")
    quote(w, "b")
    check_quote_difference(w)
    check_contract(w)
    check_amendment(w)
    planning_tasks(w, "a")
    planning_tasks(w, "b")
    purchases(w, "a")
    purchases(w, "b")
    invoice(w)
    check_delivery(w)
    price_study(w)
