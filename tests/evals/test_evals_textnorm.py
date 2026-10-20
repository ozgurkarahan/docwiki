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
        ("Ｆｕｌｌ-width ＢＣ－２０２６－０１２", "full width bc-2026-012"),
        ("soft\u00adhyphen and zero\u200bwidth", "softhyphen and zerowidth"),
        ("“Quoted” ‘text’", "\"quoted\" 'text'"),
        ("Révision B — 25 août", "revision b - 25 august"),
        ("Straße", "strasse"),
        ("extension de plain-pied", "extension de plain pied"),
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
        ("70 pour cent", "70 %"),
        ("300 metres", "300 m"),
        ("6.0 m/s", "6.0 m/s"),
        ("6 metres per second", "6 m/s"),
        ("5.4 mm/s", "5.4 mm/s"),
        ("410-litre fill", "410 l fill"),
        ("18 millimètres", "18 mm"),
        ("2,40 mètres", "2.40 m"),
        ("500 operating hours", "500 operating hours"),
        ("500 hours", "500 h"),
        ("12,345,678 rows", "12345678 rows"),
        ("0,450 bar", "0.450 bar"),
        ("1,450.5 Nm", "1450.5 nm"),
    ],
)
def test_numbers_and_units(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "47271,60 €",
        "47271.60 EUR",
        "47 271,60 €",
        "47\u00a0271,60\u00a0€",
        "47\u202f271,60\u202f€",
        "47\u2009271,60 €",
        "47 271.60 €",
        "47,271.60 €",
        "47,271.60 euros",
        "47 271,60 euros",
        "€47,271.60",
        "€47271.60",
        "€ 47271,60",
        "€\u00a047\u202f271,60",
        "EUR 47,271.60",
        "eur 47 271,60",
    ],
)
def test_one_amount_in_every_format(raw: str) -> None:
    """Currency sign before or after, any thousands separator (space, no-break space, narrow
    no-break space, comma), decimal comma or point: one number with its unit."""
    assert normalize_text(raw) == "47271.60 eur"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("€18,400", "18400 eur"),
        ("-€500", "-500 eur"),
        ("12 345,6 kg", "12345.6 kg"),
        ("1 234 567,89 €", "1234567.89 eur"),
        # a currency sign that follows an amount stays with it
        ("79,20 € 792,00 €", "79.20 eur 792.00 eur"),
        ("79,20 EUR 792,00 EUR", "79.20 eur 792.00 eur"),
        ("PU 79,20 € Total € 792,00", "pu 79.20 eur total 792.00 eur"),
        # no thousands separator in a list of small numbers
        ("lots 1 2 3 et 10 palettes", "lots 1 2 3 et 10 palettes"),
        ("Sous-total lot 2 3496,00 €", "sous total lot 2 3496.00 eur"),
        ("europe 5 pays", "europe 5 pays"),
    ],
)
def test_amounts_keep_their_own_currency_sign(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("30 m²", "30 m2"),
        ("30,00 m²", "30.00 m2"),
        ("30 m2", "30 m2"),
        ("30m2", "30 m2"),
        ("30 sq m", "30 m2"),
        ("30 sq. m", "30 m2"),
        ("30 sqm", "30 m2"),
        ("30 sq metres", "30 m2"),
        ("30 square metres", "30 m2"),
        ("30 square meters", "30 m2"),
        ("30 mètres carrés", "30 m2"),
        ("1 mètre carré", "1 m2"),
        ("22,00 m³", "22.00 m3"),
        ("22 m3", "22 m3"),
        ("22 cubic metres", "22 m3"),
        ("22 mètres cubes", "22 m3"),
        # other units that look alike stay apart
        ("30 sq mm", "30 sq mm"),
        ("30 m", "30 m"),
        ("30 m 2", "30 m 2"),
    ],
)
def test_area_and_volume_units(raw: str, expected: str) -> None:
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
        ("20 avr. 2026", "2026-04-20"),
        ("lundi 20 avril 2026", "lundi 2026-04-20"),
        ("17/03/2026", "2026-03-17"),
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
    ("raw", "expected"),
    [
        ("from 30 March to 20 April 2026", "from 2026-03-30 to 2026-04-20"),
        ("du 30 mars au 20 avril 2026", "du 2026-03-30 au 2026-04-20"),
        ("du 30/03 au 20/04/2026", "du 2026-03-30 au 2026-04-20"),
        ("du 30/03/2026 au 20/04/2026", "du 2026-03-30 au 2026-04-20"),
        ("between 30 March and 20 April 2026", "between 2026-03-30 and 2026-04-20"),
        ("30 March - 20 April 2026", "2026-03-30 - 2026-04-20"),
        ("Pose prévue du 21/04 au 23/04/2026.", "pose prevue du 2026-04-21 au 2026-04-23."),
        ("from 21 to 23 April 2026", "from 2026-04-21 to 2026-04-23"),
        ("du 21 au 23 avril 2026", "du 2026-04-21 au 2026-04-23"),
        ("du 1er au 5 avril 2026", "du 2026-04-01 au 2026-04-05"),
        ("21-23 April 2026", "2026-04-21 to 2026-04-23"),
        ("21–23 avril 2026", "2026-04-21 to 2026-04-23"),
        ("28. September bis 2. Oktober 2026", "2026-09-28 bis 2026-10-02"),
        # the first date of a range that crosses New Year belongs to the previous year
        ("from 20 December to 10 January 2027", "from 2026-12-20 to 2027-01-10"),
        # not ranges: no last date with a year, a start after the end, a bare day before a dash
        ("by 30 March", "by 30 march"),
        ("from 23 to 21 April 2026", "from 23 to 2026-04-21"),
        ("reçu 8 - 13/03/2026", "recu 8 - 2026-03-13"),
        ("from 31 April to 2 May 2026", "from 31 april to 2026-05-02"),
    ],
)
def test_date_ranges(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("from March 9 to April 20, 2026", "from 2026-03-09 to 2026-04-20"),
        ("from March 9th to April 20th, 2026", "from 2026-03-09 to 2026-04-20"),
        ("from Mar. 9 to Apr. 20, 2026", "from 2026-03-09 to 2026-04-20"),
        ("from March 9 to 20 April 2026", "from 2026-03-09 to 2026-04-20"),
        ("between March 9 and April 20, 2026", "between 2026-03-09 and 2026-04-20"),
        ("March 9 - April 20, 2026", "2026-03-09 - 2026-04-20"),
        ("from December 20 to January 10, 2027", "from 2026-12-20 to 2027-01-10"),
        # not a date: the start stays as written
        ("from February 30 to April 20, 2026", "from february 30 to 2026-04-20"),
        ("by March 9", "by march 9"),
    ],
)
def test_month_first_ranges(raw: str, expected: str) -> None:
    """A month name followed by a day starts a range: the month comes from the name."""
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # numbers that count weeks, items, versions...: no date is invented
        (
            "delivery moved from week 14 to 20 April 2026",
            "delivery moved from week 14 to 2026-04-20",
        ),
        ("weeks 14 to 20 April 2026", "weeks 14 to 2026-04-20"),
        ("week: 14 to 20 April 2026", "week: 14 to 2026-04-20"),
        ("kw 14 bis 20. April 2026", "kw 14 bis 2026-04-20"),
        ("semaine 14 au 20/04/2026", "semaine 14 au 2026-04-20"),
        ("item 7.3 and 2026-04-20", "item 7.3 and 2026-04-20"),
        ("item 7/3 and 2026-04-20", "item 7/3 and 2026-04-20"),
        ("poste 7/3 et 20/04/2026", "poste 7/3 et 2026-04-20"),
        ("version 1.2 - 2026-03-30", "version 1.2 - 2026-03-30"),
        ("version 2 to 20 April 2026", "version 2 to 2026-04-20"),
        ("lot 3 au 20/04/2026", "lot 3 au 2026-04-20"),
        ("lot 3 et le 20/04/2026", "lot 3 et le 2026-04-20"),
        ("indice 2 au 20/04/2026", "indice 2 au 2026-04-20"),
        ("étape 3 au 20/04/2026", "etape 3 au 2026-04-20"),
        ("n° 14 au 20/04/2026", "n° 14 au 2026-04-20"),
        ("n°14 au 20/04/2026", "n°14 au 2026-04-20"),
        ("no. 14 to 20 April 2026", "no. 14 to 2026-04-20"),
        ("#14 to 20 April 2026", "#14 to 2026-04-20"),
        ("task 12 to 20 April 2026", "task 12 to 2026-04-20"),
        ("T 14 au 20/04/2026", "t 14 au 2026-04-20"),
        # a number after a month name that is no date
        ("february 31 to 20 april 2026", "february 31 to 2026-04-20"),
        ("march, 9 to 20 april 2026", "march, 9 to 2026-04-20"),
        # a ratio or a decimal number is no day and month; a dotted day is a date with a full year
        ("1/2 - 2026-03-30", "1/2 - 2026-03-30"),
        ("du 30.03 au 20.04.2026", "du 30.03 au 2026-04-20"),
        # nor is the end of a time, of a ratio or of a decimal number
        ("meeting from 08:15 to 20 April 2026", "meeting from 08:15 to 2026-04-20"),
        ("score 3:2 and 2026-04-20", "score 3:2 and 2026-04-20"),
        ("price from 1,5 to 20 April 2026", "price from 1.5 to 2026-04-20"),
        ("price from 1.5 to 20 April 2026", "price from 1.5 to 2026-04-20"),
        # the end of a sentence before a joining word is no ordinal day
        ("total 14. To 20 April 2026", "total 14. to 2026-04-20"),
    ],
)
def test_numbers_that_are_not_days_do_not_start_a_range(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


@pytest.mark.parametrize(
    ("text", "dates"),
    [
        # no date is invented for a number that is not a day...
        ("delivery moved from week 14 to 20 April 2026", {"2026-04-20"}),
        ("semaine 14 au 20/04/2026", {"2026-04-20"}),
        ("item 7.3 and 2026-04-20", {"2026-04-20"}),
        ("version 1.2 - 2026-03-30", {"2026-03-30"}),
        ("8 - 13/03/2026", {"2026-03-13"}),
        # ...and the real ranges keep both dates
        ("from March 9 to April 20, 2026", {"2026-03-09", "2026-04-20"}),
        ("from 30 March to 20 April 2026", {"2026-03-30", "2026-04-20"}),
        ("du 30/03 au 20/04/2026", {"2026-03-30", "2026-04-20"}),
        ("du 21 au 23 avril 2026", {"2026-04-21", "2026-04-23"}),
        ("21-23 April 2026", {"2026-04-21", "2026-04-23"}),
        ("the 14th to 20 April 2026", {"2026-04-14", "2026-04-20"}),
        ("planned for 21 to 23 April 2026", {"2026-04-21", "2026-04-23"}),
        ("entre le 21 et le 23 avril 2026", {"2026-04-21", "2026-04-23"}),
        ("May 5 to May 8, 2026", {"2026-05-05", "2026-05-08"}),
        ("(21 to 23 April 2026)", {"2026-04-21", "2026-04-23"}),
        ("les 21 et 22 avril 2026", {"2026-04-21", "2026-04-22"}),
        ("9. bis 20. April 2026", {"2026-04-09", "2026-04-20"}),
        ("from 20 December to 10 January 2027", {"2026-12-20", "2027-01-10"}),
    ],
)
def test_range_dates_of_real_days_only(text: str, dates: set[str]) -> None:
    assert extract_values(normalize_text(text)).dates == dates


@pytest.mark.parametrize(
    ("item", "text", "found"),
    [
        ("week 14", "delivery moved from week 14 to 20 April 2026", True),
        ("2026-04-20", "delivery moved from week 14 to 20 April 2026", True),
        ("2026-04-14", "delivery moved from week 14 to 20 April 2026", False),
        ("14 April 2026", "delivery moved from week 14 to 20 April 2026", False),
        ("semaine 14", "semaine 14 au 20/04/2026", True),
        ("2026-04-14", "semaine 14 au 20/04/2026", False),
        ("7.3", "item 7.3 and 2026-04-20", True),
        ("2026-03-07", "item 7.3 and 2026-04-20", False),
        ("1.2", "version 1.2 - 2026-03-30", True),
        ("2026-02-01", "version 1.2 - 2026-03-30", False),
        ("2026-03-09", "from March 9 to April 20, 2026", True),
        ("March 9, 2026", "from March 9 to April 20, 2026", True),
        ("2026-04-09", "from March 9 to April 20, 2026", False),
        ("2026-04-21", "du 21 au 23 avril 2026", True),
    ],
)
def test_items_match_the_dates_of_ranges_only(item: str, text: str, found: bool) -> None:
    assert contains_item(item, normalize_text(text)) is found


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
        ("17", "semaine 17", True),
        ("12", "all 12 pallets", True),
        ("12", "BC-2026-009 to BC-2026-012", False),
        ("12", "DEV-2026-012", False),
        ("12", "412", False),
        ("12", "0.12 mm", False),
        ("12", "the 12th pallet", False),
        ("14", "DEV-2026-014", False),
        ("2026", "DEV-2026-014", False),
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
        ("7.3", "item 7.3.", True),
        ("7.3", "item 17.3", False),
        ("7.3", "item 7.35", False),
        ("2026-07-31", "due 31 July 2026", True),
        ("2026-07-31", "due 30 July 2026", False),
        ("31 January", "avant le 31 janvier", True),
        ("ZM 20450", "Zava article ZM 20450 (blocks)", True),
        ("ZM 20450", "ZM20450", True),
        ("ZM 20450", "ZM 204500", False),
        ("BC-2026-012", "order BC 2026 012", True),
        ("BC-2026-012", "order BC-2026-0123", False),
        ("FA-2026-0217", "invoice FA 2026 0217", True),
        ("FA-2026-0217", "invoice FA-2026-02170", False),
        ("T07", "task T07 (Livraison des menuiseries)", True),
        ("T07", "task XT07", False),
        ("palette", "deux palettes livrées", True),
        ("pallet", "two pallets delivered", True),
        ("pallet", "the palletised load", False),
        ("box", "two boxes", True),
        ("single-storey extension", "the single storey extension", True),
        ("Sliding Bay Window", "the sliding bay-window", True),
        ("lot 4", "the Lot 4 works", True),
        ("Adatum Électricité", "by ADATUM ELECTRICITE", True),
        ("18 mm", "moins de 18 millimètres", True),
        ("CANARY-1EC861DF", "reference canary-1ec861df", True),
        ("18,400", "€18400 per day", True),
        ("18 400", "18400", True),
        ("9200", "19200", False),
        ("", "anything", True),
    ],
)
def test_contains_item(item: str, text: str, found: bool) -> None:
    assert contains_item(item, normalize_text(text)) is found


@pytest.mark.parametrize("answer", ["47271,60 €", "47 271,60 €", "47\u202f271,60\u00a0€"])
@pytest.mark.parametrize(
    "written",
    [
        "47271,60 €",
        "47 271,60 €",
        "47\u00a0271,60\u00a0€",
        "47\u202f271,60\u202f€",
        "47,271.60 €",
        "€47,271.60",
        "€ 47271,60",
        "EUR 47,271.60",
        "47 271,60 euros",
        "47271.60 EUR",
        "47 271,6 €",
    ],
)
def test_amounts_match_whatever_the_format(answer: str, written: str) -> None:
    assert contains_item(answer, normalize_text(f"Total including VAT: {written}.")) is True
    assert contains_item(written, normalize_text(f"Total including VAT: {answer}.")) is True


@pytest.mark.parametrize(
    "written",
    ["47 271,61 €", "€47,271.16", "47 271 €", "4 271,60 €", "47271,60", "47 271,60 kg"],
)
def test_other_amounts_do_not_match(written: str) -> None:
    assert contains_item("47271,60 €", normalize_text(f"Total: {written}.")) is False


@pytest.mark.parametrize(
    "text",
    [
        "from 30 March to 20 April 2026",
        "du 30 mars au 20 avril 2026",
        "du 30/03 au 20/04/2026",
        "du 30/03/2026 au 20/04/2026",
        "between 30 March and 20 April 2026",
        "30 March - 20 April 2026",
    ],
)
def test_the_first_date_of_a_range_takes_the_year_of_the_last(text: str) -> None:
    normalised = normalize_text(text)
    for item in ("2026-03-30", "30/03/2026", "30 March 2026", "2026-04-20", "20/04/2026"):
        assert contains_item(item, normalised), (text, item)
    assert not contains_item("2025-03-30", normalised)
    assert not contains_item("2026-03-31", normalised)
    assert extract_values(normalised).dates == {"2026-03-30", "2026-04-20"}


@pytest.mark.parametrize(
    "text",
    [
        "from 21 to 23 April 2026",
        "du 21 au 23 avril 2026",
        "21-23 April 2026",
        "21–23 avril 2026",
        "du 21/04 au 23/04/2026",
    ],
)
def test_day_ranges_in_one_month(text: str) -> None:
    assert extract_values(normalize_text(text)).dates == {"2026-04-21", "2026-04-23"}


@pytest.mark.parametrize(
    "written",
    [
        "20/04/2026",
        "20.04.2026",
        "20 avril 2026",
        "lundi 20 avril 2026",
        "lundi 20/04/2026",
        "20 avr. 2026",
        "20 April 2026",
        "20th April 2026",
        "April 20, 2026",
        "2026-04-20",
        "2026/04/20",
    ],
)
def test_french_dates_match_iso_and_english_forms(written: str) -> None:
    text = normalize_text(f"Delivery on {written} at the latest")
    for item in ("2026-04-20", "20/04/2026", "20 April 2026", "20 avril 2026", "April 20, 2026"):
        assert contains_item(item, text), (written, item)
    assert not contains_item("2026-04-21", text)
    assert not contains_item("21/04/2026", text)
    assert not contains_item("2026-04-02", text)


@pytest.mark.parametrize(
    "written",
    [
        "30 m²",
        "30 m2",
        "30,00 m²",
        "30 sq m",
        "30 sq. m",
        "30 sqm",
        "30 square metres",
        "30 mètres carrés",
        "30 metres carres",
    ],
)
def test_area_units_match_each_other(written: str) -> None:
    text = normalize_text(f"A slab of {written} was poured")
    for item in ("30 m²", "30 m2", "30,0 m²", "30 sq m", "30 square metres", "30 mètres carrés"):
        assert contains_item(item, text), (written, item)
    assert not contains_item("30 m", text)
    assert not contains_item("31 m²", text)
    assert not contains_item("30 m³", text)
    assert not contains_item("30 m²", normalize_text("a slab of 30 m"))


def test_volume_units_match_each_other() -> None:
    text = normalize_text("Earthworks: 22,00 m³ of soil")
    for item in ("22 m³", "22 m3", "22 cubic metres", "22 mètres cubes"):
        assert contains_item(item, text), item
    assert not contains_item("22 m²", text)


def test_find_term_boundaries() -> None:
    assert find_term("zm 20450", "use zm 20450.")
    assert not find_term("zm 20450", "use zm 204501")
    assert find_term("bc-2026-012", "(bc-2026-012)")
    assert not find_term("bc", "bc2026")
    assert find_term("%", "90 %")


def test_extract_values_quantities_dates_and_codes() -> None:
    values = extract_values(
        normalize_text("Cure at 40-60 °C on 31 July 2026; 8 pallets; BC-2026-012; T07 at 75 °C")
    )
    assert Quantity(Decimal("40"), "°c") in values.quantities
    assert Quantity(Decimal("60"), "°c") in values.quantities
    assert Quantity(Decimal("8"), None) in values.quantities
    assert Quantity(Decimal("75"), "°c") in values.quantities
    assert values.dates == {"2026-07-31"}
    numbers = {quantity.value for quantity in values.quantities}
    assert Decimal("2026") not in numbers and Decimal("12") not in numbers
    assert Decimal("7") not in numbers


def test_has_quantity_compares_values_and_units() -> None:
    values = extract_values(normalize_text("6 m/s and 450 N·m and 50 ppm"))
    assert values.has_quantity(Quantity(Decimal("6.0"), "m/s"))
    assert values.has_quantity(Quantity(Decimal("450"), "nm"))
    assert values.has_quantity(Quantity(Decimal("50"), None))
    assert not values.has_quantity(Quantity(Decimal("6"), "mm/s"))
    assert str(Quantity(Decimal("6.0"), "m/s")) == "6 m/s"
    assert str(Quantity(Decimal("18400"))) == "18400"


def test_amounts_and_areas_are_quantities_with_their_unit() -> None:
    values = extract_values(normalize_text("Dallage de 30,00 m² à 96,00 € le m², soit €2 880,00"))
    assert values.has_quantity(Quantity(Decimal("30"), "m2"))
    assert values.has_quantity(Quantity(Decimal("96"), "eur"))
    assert values.has_quantity(Quantity(Decimal("2880"), "eur"))
    assert not values.has_quantity(Quantity(Decimal("30"), "m"))
    assert str(Quantity(Decimal("30.00"), "m2")) == "30 m2"


def test_value_tokens_keep_distinctive_values_only() -> None:
    tokens = value_tokens(
        normalize_text(
            "Cost price: 34,518.74; article ZM-61078; valid 2026-01-01 to 2026; 140 h; 9.5"
        )
    )
    assert tokens == {"34518.74", "zm-61078"}
    assert value_tokens(normalize_text("34 518,74 €")) == {"34518.74"}
    assert value_tokens(normalize_text("€ 34518,74")) == {"34518.74"}
    assert "140" in value_tokens(normalize_text("140 h"), min_digits=3)
