"""Normalisation and matching used by every deterministic metric."""

from __future__ import annotations

from decimal import Decimal

import pytest
from evals.textnorm import (
    Quantity,
    contains_item,
    extract_values,
    find_term,
    fold,
    normalize_text,
    value_tokens,
)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Total: 410 L", "total: 410 l"),
        ("Ｆｕｌｌ-width ＷＴＧ－０７", "full width wtg-07"),
        ("soft\u00adhyphen and zero\u200bwidth", "softhyphen and zerowidth"),
        ("“Quoted” ‘text’", "\"quoted\" 'text'"),
        ("Révision B — 25 août", "revision b - 25 august"),
        ("Straße", "strasse"),
        ("high-speed shaft", "high speed shaft"),
        ("  many \n\t spaces  ", "many spaces"),
    ],
)
def test_folding_and_normalisation(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_fold_keeps_numbers_and_units_unchanged() -> None:
    assert fold("1,450 N·m") == "1,450 n·m"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1,450 Nm", "1450 nm"),
        ("1 450 N·m", "1450 nm"),
        ("1\u202f450\u00a0N⋅m", "1450 nm"),
        ("450Nm", "450 nm"),
        ("450 N.m", "450 nm"),
        ("450 N-m", "450 nm"),
        ("450 newton metres", "450 nm"),
        ("10°C", "10 °c"),
        ("10 ° C", "10 °c"),
        ("-24.6 degrees C", "-24.6 °c"),
        ("+5 ℃", "+5 °c"),
        ("90,4 %", "90.4 %"),
        ("90.4%", "90.4 %"),
        ("90.4 percent", "90.4 %"),
        ("300 metres", "300 m"),
        ("6.0 m/s", "6.0 m/s"),
        ("6 metres per second", "6 m/s"),
        ("5.4 mm/s", "5.4 mm/s"),
        ("410-litre fill", "410 l fill"),
        ("18 millimètres", "18 mm"),
        ("500 operating hours", "500 operating hours"),
        ("500 hours", "500 h"),
        ("€18,400", "€18400"),
        ("12,345,678 rows", "12345678 rows"),
        ("0,450 bar", "0.450 bar"),
        ("1,450.5 Nm", "1450.5 nm"),
    ],
)
def test_numbers_and_units(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("31 July 2026", "2026-07-31"),
        ("31st July 2026", "2026-07-31"),
        ("July 31, 2026", "2026-07-31"),
        ("Jul. 31 2026", "2026-07-31"),
        ("31/07/2026", "2026-07-31"),
        ("31.07.2026", "2026-07-31"),
        ("31. Juli 2026", "2026-07-31"),
        ("31 juillet 2026", "2026-07-31"),
        ("1er juin 2026", "2026-06-01"),
        ("2026/07/31", "2026-07-31"),
        ("07/31/2026", "2026-07-31"),
        ("31 janvier", "31 january"),
        ("by 31 January", "by 31 january"),
        ("31 February 2026", "31 february 2026"),
        ("KW 40 (28.09.2026 bis 02.10.2026)", "kw 40 (2026-09-28 bis 2026-10-02)"),
    ],
)
def test_dates(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("item", "text", "found"),
    [
        ("410 L", "The total is 410 L.", True),
        ("410 L", "The total is 410 litres.", True),
        ("410 L", "**410 L** in total", True),
        ("410 L", "a 410-litre fill", True),
        ("410 L", "4100 L", False),
        ("40", "410 L", False),
        ("40", "40.5 bar", False),
        ("40", "week 40 (28 September)", True),
        ("40", "KW 40", True),
        ("12", "all 12 turbines", True),
        ("12", "WTG-01 to WTG-12", False),
        ("12", "0.12 mm", False),
        ("12", "the 12th turbine", False),
        ("1,450 Nm", "re-torque to 1450 N·m", True),
        ("1,450 Nm", "re-torque to 1 450 Nm", True),
        ("1,450 Nm", "re-torque to 1,380 Nm", False),
        ("450 Nm", "450 N·m", True),
        ("6.0 m/s", "below 6 m/s", True),
        ("6.0 m/s", "below 6.0 metres per second", True),
        ("4.5 mm/s", "alarm level 4.5 m/s", False),
        ("4.5 mm/s", "alarm level 4.5 mm/s RMS", True),
        ("5 °C", "minimum +5 °C", True),
        ("5 °C", "minimum -5 °C", False),
        ("75", "warning at 75 °C", True),
        ("90.4", "availability 90,4 %", True),
        ("7.3", "condition 7.3.", True),
        ("7.3", "condition 17.3", False),
        ("7.3", "condition 7.35", False),
        ("2026-07-31", "due 31 July 2026", True),
        ("2026-07-31", "due 30 July 2026", False),
        ("31 January", "avant le 31 janvier", True),
        ("PWG 220", "Proseware PWG 220 oil", True),
        ("PWG 220", "PWG220", True),
        ("PWG 220", "PWG 2200", False),
        ("FGT-P-22328", "part FGT P 22328", True),
        ("FGT-P-22328", "part FGT-P-223281", False),
        ("WTG-07", "turbine WTG 07", True),
        ("WTG-07", "turbine WTG-070", False),
        ("S420", "status S420 'Curtailed'", True),
        ("S420", "status XS420", False),
        ("fan", "two cooler fans", True),
        ("fan", "the fanatic", False),
        ("radiator", "radiators cleaned", True),
        ("high-speed shaft", "the high speed shaft (HSS)", True),
        ("Cold Climate Version", "the cold-climate version", True),
        ("category 4", "a Category 4 crack", True),
        ("Wingtip Blade Services", "by WINGTIP BLADE SERVICES", True),
        ("18 mm", "moins de 18 millimètres", True),
        ("CANARY-B08DE0CB", "reference canary-b08de0cb", True),
        ("18,400", "€18400 per day", True),
        ("18 400", "18400", True),
        ("9200", "19200", False),
        ("", "anything", True),
    ],
)
def test_contains_item(item: str, text: str, found: bool) -> None:
    assert contains_item(item, normalize_text(text)) is found


def test_find_term_boundaries() -> None:
    assert find_term("pwg 220", "use pwg 220.")
    assert not find_term("pwg 220", "use pwg 2201")
    assert find_term("wtg-07", "(wtg-07)")
    assert not find_term("wtg", "wtg07")
    assert find_term("%", "90 %")


def test_extract_values_quantities_dates_and_codes() -> None:
    values = extract_values(
        normalize_text("Drain at 40-60 °C on 31 July 2026; 12 turbines; WO-26-0412; A2101 at 75 °C")
    )
    assert Quantity(Decimal("40"), "°c") in values.quantities
    assert Quantity(Decimal("60"), "°c") in values.quantities
    assert Quantity(Decimal("12"), None) in values.quantities
    assert Quantity(Decimal("75"), "°c") in values.quantities
    assert values.dates == {"2026-07-31"}
    numbers = {quantity.value for quantity in values.quantities}
    assert Decimal("26") not in numbers and Decimal("412") not in numbers
    assert Decimal("2101") not in numbers


def test_has_quantity_compares_values_and_units() -> None:
    values = extract_values(normalize_text("6 m/s and 450 N·m and 50 ppm"))
    assert values.has_quantity(Quantity(Decimal("6.0"), "m/s"))
    assert values.has_quantity(Quantity(Decimal("450"), "nm"))
    assert values.has_quantity(Quantity(Decimal("50"), None))
    assert not values.has_quantity(Quantity(Decimal("6"), "mm/s"))
    assert str(Quantity(Decimal("6.0"), "m/s")) == "6 m/s"
    assert str(Quantity(Decimal("18400"))) == "18400"


def test_value_tokens_keep_distinctive_values_only() -> None:
    tokens = value_tokens(
        normalize_text("Rate (EUR): 18,400; fleet TS-600C-02; valid 2026-01-01 to 2026; 140 h; 9.5")
    )
    assert tokens == {"18400", "ts-600c-02"}
    assert "140" in value_tokens(normalize_text("140 h"), min_digits=3)
