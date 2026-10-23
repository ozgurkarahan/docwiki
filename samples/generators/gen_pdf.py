"""Text-layer PDF documents: the two quote revisions and the builders' merchant invoice."""

from __future__ import annotations

from .common import eur, fr_date, meta_for, percent, quantity
from .datasets import Quote, invoice, lot_label, quote
from .pdfdoc import LEFT, WIDTH, Group, StampedPDF, Subtotal
from .world import World

_RIGHT_X = LEFT + 90.0
_RIGHT_W = WIDTH - 90.0


def _sentence(text: str) -> str:
    return text[:1].upper() + text[1:]


def _client_names(w: World) -> str:
    """``Mme ... et M. ...``: the client party of the contract, without its address."""
    return str(w.facts["contrat"]["parties"]["client"]).split(",", 1)[0]


def _letterhead(pdf: StampedPDF, w: World, org_key: str, address: str,
                contact_key: str) -> float:
    org = w.org(org_key)
    contact = w.person(contact_key)
    return pdf.lines_at(
        LEFT,
        22,
        96,
        [
            (org["name"], 16, "B"),
            (_sentence(org["role_fr"]), 9, ""),
            (_sentence(address), 9, ""),
            (f"Contact : {contact['name']}, {contact['role'].lower()}", 9, ""),
            (contact["email"], 9, ""),
        ],
    )


def _title_box(pdf: StampedPDF, kind: str, lines: list[str]) -> float:
    rows = [(kind, 19, "B")] + [(line, 9.5, "B" if i == 0 else "") for i, line in
                                enumerate(lines)]
    return pdf.lines_at(_RIGHT_X, 22, _RIGHT_W, rows, align="R")


# ------------------------------------------------------------------------------------------
# Quote DEV-2026-014, indice A and B


def _quote_rows(w: World, q: Quote) -> list[list[str] | Group | Subtotal]:
    rows: list[list[str] | Group | Subtotal] = []
    for lot in w.lots:
        number = int(lot["lot"])
        rows.append(Group(f"Lot {number} - {lot['title']} (TVA {percent(lot['vat_rate'])})"))
        for line in q.lines_of(number):
            rows.append([line.ref, line.designation, quantity(line.qty), line.unit,
                         eur(line.unit_price), eur(line.total)])
        rows.append(Subtotal(f"Sous-total lot {number}", eur(q.lot_subtotals[number])))
    return rows


def _devis(w: World, indice: str) -> bytes:
    facts = w.facts["devis"]
    q = quote(w, indice)
    revision = indice.upper()
    doc = w.doc(f"devis-{indice}")
    builder = w.builder
    reference = f"{facts['number']} indice {revision}"
    pdf = StampedPDF(meta_for(doc, builder["name"]), f"{builder['name']} - Devis {reference}",
                     reference, legal=w.legal_line(builder["key"]))
    pdf.add_page()
    site = w.facts["site"]
    bottom = _letterhead(pdf, w, builder["key"], site["builder_address"], facts["issuer"])
    _title_box(pdf, "DEVIS", [f"N° {reference}", f"Date : {fr_date(q.date)}"])
    client_bottom = pdf.framed_lines(_RIGHT_X, 52, _RIGHT_W, "Client",
                                     [_client_names(w), site["address"]])
    pdf.set_y(max(bottom, client_bottom) + 5)
    pdf.label_para("Lieu des travaux", site["address"])
    pdf.label_para("Objet", facts["object"])
    pdf.para(facts["reference_sentence"])
    data = facts[f"indice_{indice}"]
    if "supersedes_sentence" in data:
        pdf.para(data["supersedes_sentence"], style="B")
        pdf.para(" ".join(str(data["changes_sentence"]).split()))
        diff = data["difference_from_a"]
        pdf.para(f"Écart par rapport à l'indice A : +{eur(diff['ht'])} HT, soit "
                 f"+{eur(diff['ttc'])} TTC.")
    pdf.grid(
        ["Réf.", "Désignation", "Qté", "U", "PU HT", "Total HT"],
        _quote_rows(w, q),
        widths=(11, 83, 15, 11, 25, 29),
        align=("LEFT", "LEFT", "RIGHT", "CENTER", "RIGHT", "RIGHT"),
    )
    totals = [("Total HT", eur(q.ht))]
    for vat in q.vat:
        totals.append(
            (f"TVA {percent(vat.rate)} ({lot_label(vat.lots)}) sur {eur(vat.base)}",
             eur(vat.amount))
        )
    totals += [("Total TVA", eur(q.vat_total)), ("Total TTC", eur(q.ttc))]
    pdf.totals(totals)
    pdf.h1("Conditions")
    pdf.bullets([str(item) for item in facts["conditions"]])
    issuer = w.person(facts["issuer"])
    pdf.signature_boxes(
        [
            (f"Pour {builder['name']}", [f"{issuer['name']}, {issuer['role'].lower()}",
                                         f"{w.town}, le {fr_date(q.date)}"]),
            (str(facts["signature_box"]), []),
        ]
    )
    return pdf.render()


def devis_a(w: World) -> bytes:
    return _devis(w, "a")


def devis_b(w: World) -> bytes:
    return _devis(w, "b")


# ------------------------------------------------------------------------------------------
# Builders' merchant invoice FA-2026-0217


def facture(w: World) -> bytes:
    facts = w.facts["zava_invoice"]
    doc = w.doc("facture")
    merchant = w.org(str(doc["organisation"]))
    number = str(facts["number"])
    pdf = StampedPDF(meta_for(doc, merchant["name"]), f"{merchant['name']} - Facture {number}",
                     number, legal=w.legal_line(merchant["key"]))
    pdf.add_page()
    site = w.facts["site"]
    bottom = _letterhead(pdf, w, merchant["key"], site["merchant_address"], facts["contact"])
    _title_box(pdf, "FACTURE", [f"N° {number}", f"Date : {fr_date(str(facts['date']))}"])
    builder = w.builder
    client_bottom = pdf.framed_lines(_RIGHT_X, 52, _RIGHT_W, "Client",
                                     [builder["name"], site["builder_address"]])
    pdf.set_y(max(bottom, client_bottom) + 5)
    delivery = w.facts["zava_delivery"]
    pdf.label_para("Votre commande", str(facts["order"]))
    pdf.label_para(
        "Bon de livraison",
        f"{facts['delivery_note']} du {fr_date(str(facts['delivery_date']))}",
    )
    pdf.label_para("Livré à", str(delivery["delivered_to"]))
    lines, ht, vat, ttc = invoice(w)
    pdf.grid(
        ["Code", "Désignation", "Qté", "Unité", "PU HT", "Total HT"],
        [
            [line.code or "-", line.designation, quantity(line.qty), line.unit,
             eur(line.unit_price), eur(line.total)]
            for line in lines
        ],
        widths=(20, 72, 12, 19, 23, 28),
        align=("LEFT", "LEFT", "RIGHT", "CENTER", "RIGHT", "RIGHT"),
    )
    rate = facts["totals"]["vat_rate"]
    pdf.totals([("Total HT", eur(ht)), (f"TVA {percent(rate)}", eur(vat)),
                ("Total TTC", eur(ttc))])
    pdf.label_para("Conditions de paiement", str(facts["payment_terms"]))
    pdf.label_para("Date d'échéance", fr_date(str(facts["due_date"])))
    pdf.label_para("Pénalités de retard", "trois fois le taux d'intérêt légal ; indemnité "
                   "forfaitaire pour frais de recouvrement de 40,00 €.")
    return pdf.render()
