"""Chantier résidence Les Nacrines (copropriété, at réception): the marché, the subcontract and
its DC4, OS n°1, the Zava invoice, situation n°4, site meeting minutes n°12, the scanned PV de
réception, the réserves list and VanArsdel's e-mail."""

from __future__ import annotations

import io
from collections.abc import Sequence
from datetime import date, datetime

from fpdf import FPDF
from PIL import Image, ImageDraw

from .common import GENERATOR_AUTHOR, STAMP, dec, eur, fr_date, meta_for, percent, quantity
from .datasets_f import nacrines_invoice, nacrines_marche, nacrines_os1, nacrines_situation
from .fonts import pil_font
from .gen_docx import DocxBuilder, _flat
from .gen_eml import _body, _message, _message_id, _wrap
from .gen_pdf import _RIGHT_W, _RIGHT_X, _letterhead, _title_box
from .gen_scan import BLACK, GREY, PAGE_H, PAGE_W, _box, _labelled, _scan, handwrite, scribble
from .gen_xlsx import WorkbookBuilder
from .pdfdoc import StampedPDF
from .world import World

SITE_LABEL = "Résidence Les Nacrines, Valbrise"


def _facts(w: World) -> dict:
    return w.facts["nacrines"]


def _person_line(w: World, key: str) -> str:
    return f"{w.name(key)}, {w.role(key).lower()}, {w.org_name(w.person(key)['organisation'])}"


def signature_table(b: DocxBuilder, boxes: Sequence[tuple[str, Sequence[str]]]) -> None:
    """One row of signature boxes (title in the header, lines in the cell)."""
    width = 17.0 / len(boxes)
    b.table([title for title, _ in boxes], [["\n".join(lines) for _, lines in boxes]],
            widths=[width] * len(boxes))


# ------------------------------------------------------------------------------------------
# Marché de travaux (2025-11-20)


def marche(w: World) -> bytes:
    facts = _facts(w)["marche"]
    lines, sums = nacrines_marche(w)
    day = str(facts["date"])
    b = DocxBuilder(f"{w.builder['name']} - Marché de travaux du {fr_date(day)}",
                    f"Marché de travaux - {SITE_LABEL}", legal=w.legal_line("lamna-batiment"))
    b.title(str(facts["title"]))
    parties = facts["parties"]
    b.para("Entre les soussignés :", bold=True)
    b.para(str(parties["maitre_d_ouvrage"]))
    b.para("et")
    b.para(str(parties["entreprise"]))
    b.para("en présence de")
    b.para(str(parties["maitre_d_oeuvre"]))
    b.para(str(facts["general_assembly"]))
    b.para("Il a été convenu ce qui suit.")
    articles: dict[str, str] = {}
    for raw in facts["articles"]:
        number, _, title = str(raw).partition(" ")
        articles[number] = f"Article {number} - {title}"
    b.h1(articles["1"])
    b.para(_flat(facts["object"]))
    b.h1(articles["2"])
    lots = {int(lot["lot"]): str(lot["title"]) for lot in facts["lots"]}
    rows: list[list[str]] = []
    for raw, line in zip(facts["lines"], lines, strict=True):
        rows.append([line.ref, f"Lot {raw['lot']} - {lots[int(raw['lot'])]} : {line.designation}",
                     quantity(line.qty), line.unit, eur(line.unit_price), eur(line.total)])
    rate = int(facts["totals"]["vat_rate"])
    rows += [
        ["", "Total HT", "", "", "", eur(sums["ht"])],
        ["", f"TVA {percent(rate)}", "", "", "", eur(sums["vat"])],
        ["", "Total TTC", "", "", "", eur(sums["ttc"])],
    ]
    b.table(["Poste", "Désignation", "Qté", "U", "PU HT", "Total HT"], rows,
            widths=(1.2, 9.0, 1.4, 1.0, 2.2, 2.2), right=(2, 4, 5),
            bold_rows=(len(lines) + 1, len(lines) + 3))
    b.h1(articles["3"])
    b.para(f"Le marché est conclu à prix global et forfaitaire de {eur(sums['ht'])} HT, soit "
           f"{eur(sums['ttc'])} TTC au taux de TVA de {percent(rate)}.")
    b.h1(articles["4"])
    b.para(f"Les travaux débutent le {fr_date(str(facts['start']))}. Le délai d'exécution est de "
           f"{facts['duration_weeks']} semaines ; l'achèvement des travaux est fixé au "
           f"{fr_date(str(facts['completion']))}.")
    b.h1(articles["5"])
    b.para(str(facts["penalties_text"]))
    b.h1(articles["6"])
    b.para(str(facts["payment_text"]))
    b.h1(articles["7"])
    b.para(str(facts["retention_text"]))
    b.h1(articles["8"])
    b.para(str(facts["subcontracting_text"]))
    b.h1(articles["9"])
    b.para(str(facts["changes_text"]))
    b.h1(articles["10"])
    b.para(str(facts["reception_text"]))
    b.h1(articles["11"])
    b.para(str(facts["insurance_text"]))
    b.para(f"Fait à {facts['place_signed']}, le {fr_date(day)}, en trois exemplaires originaux.")
    signed = f"Lu et approuvé, signé le {fr_date(day)}"
    mo, ent, moe = facts["signatories"]
    signature_table(b, [
        ("Pour le maître d'ouvrage", [w.org_name("syndicat-nacrines"),
                                      f"par son syndic {w.org_name('proseware-gestion')}",
                                      f"{w.name(mo)}, {w.role(mo).lower()}", signed]),
        ("Pour l'entrepreneur", [w.builder["name"], f"{w.name(ent)}, {w.role(ent).lower()}",
                                 signed]),
        ("Vu, le maître d'œuvre", [w.org_name("atelier-fabrikam"),
                                    f"{w.name(moe)}, {w.role(moe).lower()}"]),
    ])
    return b.render(w, "nac-marche")


# ------------------------------------------------------------------------------------------
# Subcontract (2025-12-10) and its DC4 (declared 2025-12-12, accepted 2026-01-08)


def sous_traitance(w: World) -> bytes:
    facts = _facts(w)["sous_traitance"]
    day = str(facts["date"])
    b = DocxBuilder(f"{w.builder['name']} - Contrat de sous-traitance du {fr_date(day)}",
                    f"Sous-traitance du lot 5 - {SITE_LABEL}",
                    legal=w.legal_line("lamna-batiment", "adatum-electricite"))
    b.title(str(facts["title"]))
    b.para("Entre les soussignés :", bold=True)
    b.para(str(facts["parties"]["entreprise"]))
    b.para("et")
    b.para(str(facts["parties"]["sous_traitant"]))
    articles = [
        ("Article 1 - Objet", _flat(facts["object"])),
        ("Article 2 - Prix", str(facts["price_text"])),
        ("Article 3 - Délais", f"Le sous-traitant intervient du {fr_date(str(facts['start']))} au "
                               f"{fr_date(str(facts['end']))}."),
        ("Article 4 - Paiement", str(facts["payment_text"])),
        ("Article 5 - Garantie de paiement", str(facts["guarantee_text"])),
        ("Article 6 - Obligation de vigilance", str(facts["vigilance_text"])),
        ("Article 7 - Assurances", str(facts["insurance_text"])),
        ("Article 8 - Acceptation par le maître d'ouvrage", str(facts["acceptance_text"])),
    ]
    for title, text in articles:
        b.h1(title)
        b.para(text)
    b.para(f"Fait à {w.town}, le {fr_date(day)}, en deux exemplaires originaux.")
    signed = f"Lu et approuvé, signé le {fr_date(day)}"
    ent, sub = facts["signatories"]
    signature_table(b, [
        ("Pour l'entrepreneur principal", [w.builder["name"],
                                           f"{w.name(ent)}, {w.role(ent).lower()}", signed]),
        ("Pour le sous-traitant", [w.org_name("adatum-electricite"), w.name(sub), signed]),
    ])
    return b.render(w, "nac-sous-traitance")


def dc4(w: World) -> bytes:
    facts = _facts(w)["dc4"]
    doc = w.doc("nac-dc4")
    marche_facts = _facts(w)["marche"]
    pdf = StampedPDF(meta_for(doc, w.builder["name"]),
                     "Déclaration de sous-traitance (modèle DC4)", SITE_LABEL,
                     legal=w.legal_line("lamna-batiment"))
    pdf.add_page()
    pdf.title_line("DÉCLARATION DE SOUS-TRAITANCE (DC4)", 15)
    pdf.para("Demande d'acceptation d'un sous-traitant et d'agrément de ses conditions de "
             f"paiement. {facts['model_note']}")
    sections = [
        ("A - Maître d'ouvrage", [
            f"{w.org_name('syndicat-nacrines')}, {_facts(w)['address']}",
            f"Représenté par son syndic {w.org_name('proseware-gestion')} "
            f"({w.name('clarisse-monfreuil')}, {w.role('clarisse-monfreuil').lower()})"]),
        ("B - Objet du marché", [
            f"Objet : {marche_facts['title']}, marché du {fr_date(str(marche_facts['date']))}",
            f"Maître d'œuvre : {w.org_name('atelier-fabrikam')}"]),
        ("C - Entrepreneur principal", [
            f"{w.builder['name']}, {w.facts['site']['builder_address']}",
            f"Représenté par {w.name('bertrand-sauzede')}, "
            f"{w.role('bertrand-sauzede').lower()}",
            str(w.data["world"]["legal_identity"])]),
        ("D - Sous-traitant", [
            f"{w.org_name('adatum-electricite')}, représentée par {w.name('damien-pradere')}",
            str(w.data["world"]["legal_identity"])]),
        ("E - Nature des prestations sous-traitées", [str(facts["nature"]),
                                                      f"Période : {facts['period']}"]),
        ("F - Montant maximum des prestations sous-traitées", [
            f"{eur(facts['amount_ht'])} HT ({facts['vat_text']})"]),
        ("G - Conditions de paiement", [str(facts["payment_text"]),
                                        str(facts["assignment_text"])]),
    ]
    for title, lines in sections:
        pdf.h1(title)
        for line in lines:
            pdf.para(line)
    pdf.label_para("Déclaration de l'entrepreneur principal",
                   f"faite à {w.town}, le {fr_date(str(facts['declared']))}.")
    pdf.h1("H - Acceptation et agrément")
    pdf.para(str(facts["acceptance_sentence"]), style="B")
    accepted = fr_date(str(facts["accepted"]))
    pdf.signature_boxes([
        ("L'entrepreneur principal", [w.builder["name"], w.name("bertrand-sauzede"),
                                      f"Le {fr_date(str(facts['declared']))}"]),
        ("Le maître d'ouvrage", [f"Pour le syndicat, {w.org_name('proseware-gestion')}",
                                 w.name(str(facts["accepted_by"])), f"Le {accepted}"]),
    ])
    return pdf.render()


# ------------------------------------------------------------------------------------------
# OS n°1 (2026-02-16)


def os1(w: World) -> bytes:
    facts = _facts(w)["os1"]
    marche_facts = _facts(w)["marche"]
    lines, sums = nacrines_os1(w)
    day = str(facts["date"])
    moe = w.org("atelier-fabrikam")
    title = f"Ordre de service n°{facts['number']}"
    b = DocxBuilder(f"{moe['name']} - {title} du {fr_date(day)}", f"{title} - {SITE_LABEL}")
    b.title(title)
    b.label("Opération", f"{marche_facts['title']}, {_facts(w)['address']}")
    b.label("Marché", f"marché de travaux du {fr_date(str(marche_facts['date']))}")
    b.label("Maître d'ouvrage", f"{w.org_name('syndicat-nacrines')}, représenté par "
                                f"{w.org_name('proseware-gestion')}")
    b.label("Maître d'œuvre", _person_line(w, str(facts["issued_by"])))
    b.label("Entrepreneur", w.builder["name"])
    b.label("Objet", str(facts["object"]))
    b.h1("1. Constat")
    b.para(str(facts["finding"]))
    b.h1("2. Travaux ordonnés")
    rate = int(facts["totals"]["vat_rate"])
    b.table(
        ["Réf.", "Désignation", "Qté", "U", "PU HT", "Total HT"],
        [
            *([line.ref, line.designation, quantity(line.qty), line.unit, eur(line.unit_price),
               eur(line.total)] for line in lines),
            ["", "Total HT", "", "", "", eur(sums["ht"])],
            ["", f"TVA {percent(rate)}", "", "", "", eur(sums["vat"])],
            ["", "Total TTC", "", "", "", eur(sums["ttc"])],
        ],
        widths=(1.4, 8.8, 1.2, 1.0, 2.3, 2.3), right=(2, 4, 5),
        bold_rows=(len(lines) + 1, len(lines) + 3),
    )
    b.h1("3. Incidence sur le prix et le délai")
    new = facts["new_contract_total"]
    b.para(f"Le montant du marché est porté de {eur(marche_facts['totals']['ht'])} HT à "
           f"{eur(new['ht'])} HT, soit {eur(new['ttc'])} TTC.")
    b.para(f"Le délai d'exécution est prolongé de {facts['delay_days']} jours calendaires : "
           f"l'achèvement des travaux est reporté du {fr_date(str(marche_facts['completion']))} "
           f"au {fr_date(str(facts['new_completion']))}.")
    accepted = fr_date(str(facts["accepted_on"]))
    signature_table(b, [
        ("Le maître d'œuvre", [moe["name"], w.name(str(facts["issued_by"])),
                               f"Émis le {fr_date(day)}"]),
        ("Le maître d'ouvrage", [w.org_name("proseware-gestion"),
                                 w.name(str(facts["countersigned_by"])),
                                 f"Contresigné le {fr_date(day)}"]),
        ("L'entrepreneur", [w.builder["name"], w.name(str(facts["accepted_by"])),
                            f"Reçu et accepté le {accepted}"]),
    ])
    return b.render(w, "nac-os1")


# ------------------------------------------------------------------------------------------
# Zava invoice FA-2026-0158 (2026-02-12)


def facture(w: World) -> bytes:
    facts = _facts(w)["zava_invoice"]
    doc = w.doc("nac-facture")
    merchant = w.org(str(doc["organisation"]))
    number = str(facts["number"])
    pdf = StampedPDF(meta_for(doc, merchant["name"]), f"{merchant['name']} - Facture {number}",
                     number, legal=w.legal_line(merchant["key"]))
    pdf.add_page()
    site = w.facts["site"]
    bottom = _letterhead(pdf, w, merchant["key"], site["merchant_address"], facts["contact"])
    _title_box(pdf, "FACTURE", [f"N° {number}", f"Date : {fr_date(str(facts['date']))}"])
    client_bottom = pdf.framed_lines(_RIGHT_X, 52, _RIGHT_W, "Client",
                                     [w.builder["name"], site["builder_address"]])
    pdf.set_y(max(bottom, client_bottom) + 5)
    pdf.label_para("Votre commande", str(facts["order"]))
    pdf.label_para("Bon de livraison",
                   f"{facts['delivery_note']} du {fr_date(str(facts['delivery_date']))}")
    pdf.label_para("Livré à", str(facts["delivered_to"]))
    lines, sums = nacrines_invoice(w)
    pdf.grid(
        ["Code", "Désignation", "Qté", "Unité", "PU HT", "Total HT"],
        [[raw.get("code") or "-", line.designation, quantity(line.qty), line.unit,
          eur(line.unit_price), eur(line.total)] for raw, line in zip(facts["lines"], lines,
                                                                      strict=True)],
        widths=(20, 72, 14, 17, 23, 28),
        align=("LEFT", "LEFT", "RIGHT", "CENTER", "RIGHT", "RIGHT"),
    )
    rate = facts["totals"]["vat_rate"]
    pdf.totals([("Total HT", eur(sums["ht"])), (f"TVA {percent(rate)}", eur(sums["vat"])),
                ("Total TTC", eur(sums["ttc"]))])
    pdf.label_para("Conditions de paiement", str(facts["payment_terms"]))
    pdf.label_para("Date d'échéance", fr_date(str(facts["due_date"])))
    pdf.label_para("Pénalités de retard", "trois fois le taux d'intérêt légal ; indemnité "
                   "forfaitaire pour frais de recouvrement de 40,00 €.")
    return pdf.render()


# ------------------------------------------------------------------------------------------
# Situation n°4 (2026-03-31)


def situation4(w: World) -> bytes:
    facts = _facts(w)
    sit = facts["situation4"]
    doc = w.doc("nac-situation4")
    rows, s = nacrines_situation(w)
    b = WorkbookBuilder(f"{w.builder['name']} - {doc['title']}")
    lots = {str(line["ref"]): int(line["lot"]) for line in facts["marche"]["lines"]}
    sheet_rows: list[Sequence[object]] = [
        [row.ref, row.designation if row.ref not in lots else f"Lot {lots[row.ref]} - "
         f"{row.designation}", row.amount, percent(row.progress), row.cumul]
        for row in rows
    ]
    sheet_rows.append(["Total", None, s["total_ht"], None, s["cumul"]])
    b.sheet("Situation", ["Poste", "Désignation", "Montant HT", "Avancement cumulé",
                          "Montant cumulé HT"], sheet_rows, widths=[9, 64, 15, 12, 17],
            bold_rows=(len(rows) + 1,))
    rate = int(facts["marche"]["totals"]["vat_rate"])
    retention = int(facts["marche"]["retention_percent"])
    previous = sit["previous"]
    recap: list[Sequence[object]] = [
        ["Opération", f"{facts['marche']['title']}, {facts['address']}"],
        ["Maître d'ouvrage", f"{w.org_name('syndicat-nacrines')}, représenté par "
                             f"{w.org_name('proseware-gestion')}"],
        ["Maître d'œuvre", w.org_name("atelier-fabrikam")],
        ["Situation", f"Situation n°{sit['number']} au {fr_date(str(sit['date']))}"],
        ["Établie par", _person_line(w, str(sit["author"]))],
        ["Montant du marché HT", s["marche_ht"]],
        [f"OS n°{facts['os1']['number']} du {fr_date(str(facts['os1']['date']))} HT", s["os_ht"]],
        ["Montant total du marché HT", s["total_ht"]],
        [f"Travaux cumulés HT au {fr_date(str(sit['date']))}", s["cumul"]],
        [f"Situations précédentes HT (n°1 à n°{previous['count']})", s["previous"]],
        [f"Montant de la situation n°{sit['number']} HT", s["this_ht"]],
        [f"TVA {percent(rate)}", s["vat"]],
        [f"Montant de la situation n°{sit['number']} TTC", s["ttc"]],
        [f"Retenue de garantie {percent(retention)} du TTC", s["retention"]],
        ["Net à payer TTC", s["net"]],
        [f"Retenue de garantie cumulée (situations n°1 à n°{sit['number']})",
         s["retention_cumul"]],
        ["Reste à facturer HT", s["left"]],
    ]
    b.sheet("Récapitulatif", ["Libellé", "Montant"], recap, widths=[58, 70])
    sub_rows: list[Sequence[object]] = [
        [w.org_name(str(sub["subcontractor"])), str(sub["object"]), dec(sub["amount_ht"]),
         str(sub["statement"]), date.fromisoformat(str(sub["date"])), dec(sub["cumul_ht"]),
         percent(sub["progress"]), str(sub["note"])]
        for sub in sit["subcontract"]
    ]
    b.sheet("Sous-traitance", ["Sous-traitant", "Objet", "Montant du sous-traité HT",
                               "Situation du sous-traitant", "Date", "Montant cumulé HT",
                               "Avancement", "Observations"], sub_rows,
            widths=[22, 34, 16, 26, 12, 16, 11, 52])
    if b.wb.sheetnames != list(sit["sheets"]):
        raise ValueError(f"situation sheets {b.wb.sheetnames} differ from the bible")
    return b.render(w, "nac-situation4")


# ------------------------------------------------------------------------------------------
# Site meeting minutes n°12 (2026-03-26), written by the maître d'œuvre


def compte_rendu(w: World) -> bytes:
    facts = _facts(w)["compte_rendu_12"]
    moe = w.org("atelier-fabrikam")
    day = str(facts["date"])
    title = f"Compte rendu de chantier n°{facts['number']}"
    b = DocxBuilder(f"{moe['name']} - {title}", f"{title} - {SITE_LABEL}")
    b.title(title)
    b.label("Opération", f"{_facts(w)['marche']['title']}, {_facts(w)['address']}")
    b.label("Date de la réunion", f"{fr_date(day)} à {facts['time']}")
    b.label("Lieu", str(facts["place"]))
    b.label("Rédigé par", f"{w.name(facts['written_by'])}, {w.role(facts['written_by']).lower()} "
                          f"({moe['name']}, maître d'œuvre)")
    present, excused = list(facts["present"]), list(facts["excused"])
    people = [*present, *excused, *facts["distribution_extra"]]
    b.table(
        ["Nom", "Organisation", "Fonction", "Présent", "Excusé", "Diffusion"],
        [[w.name(k), w.org_name(w.person(k)["organisation"]), w.role(k),
          "x" if k in present else "", "x" if k in excused else "", "x"] for k in people],
        widths=(3.6, 3.8, 4.4, 1.7, 1.7, 1.8),
    )
    b.h1("1. Avancement des travaux")
    b.bullets([str(item) for item in facts["progress"]])
    b.h1("2. Décisions")
    for decision in facts["decisions"]:
        b.para(f"{decision['id']} - {decision['text']}")
    b.h1("3. Actions")
    b.table(["Action", "Responsable", "Échéance"],
            [[str(a["what"]), w.label(str(a["who"])), fr_date(str(a["due"]))]
             for a in facts["actions"]], widths=(10.5, 3.8, 2.7))
    b.h1("4. Prochaine réunion")
    b.para(str(facts["next_meeting"]))
    return b.render(w, "nac-cr12")


# ------------------------------------------------------------------------------------------
# Scanned PV de réception (2026-04-03): image-only, the decisive marks are handwritten


def _checkbox(d: ImageDraw.ImageDraw, x: int, y: int, label: str) -> None:
    d.rectangle((x, y, x + 34, y + 34), outline=BLACK, width=3)
    d.text((x + 50, y + 2), label, font=pil_font(26), fill=BLACK)


def _pv_page(w: World) -> Image.Image:
    facts = _facts(w)["pv_reception"]
    marche_facts = _facts(w)["marche"]
    img = Image.new("RGB", (PAGE_W, PAGE_H), "white")
    d = ImageDraw.Draw(img)
    d.text((80, 40), STAMP, font=pil_font(24, "bold"), fill=BLACK)
    d.rectangle((80, 90, 1160, 170), fill=GREY, outline=BLACK, width=3)
    d.text((110, 110), str(facts["printed_title"]), font=pil_font(34, "bold"), fill=BLACK)
    y = 200
    for label, value in (
        ("Opération :", f"Résidence Les Nacrines, {_facts(w)['address']}"),
        ("Maître d'ouvrage :",
         f"Syndicat des copropriétaires, par {w.org_name('proseware-gestion')}"),
        ("Maître d'œuvre :", w.org_name("atelier-fabrikam")),
        ("Entreprise :", w.builder["name"]),
        ("Marché :", f"du {fr_date(str(marche_facts['date']))} et OS n°1 du "
                     f"{fr_date(str(_facts(w)['os1']['date']))}"),
        ("OPR :", f"opérations préalables du {fr_date(str(facts['opr_date']))}"),
    ):
        _labelled(d, 80, y, label, value, label_w=270)
        y += 44
    y += 16
    d.text((80, y), "Après les opérations préalables à la réception, le maître d'ouvrage décide :",
           font=pil_font(24), fill=BLACK)
    y += 54
    choices = [str(choice) for choice in facts["printed_choices"]]
    xs = [100, 470, 840]
    for x, label in zip(xs, choices, strict=True):
        _checkbox(d, x, y, label)
    chosen = xs[choices.index(str(facts["chosen"]))]
    handwrite(img, (chosen + 2, y - 8), "X", 40, "pv-cross")
    y += 70
    hand = facts["handwritten"]
    d.text((80, y + 6), "Date d'effet de la réception :", font=pil_font(26, "bold"), fill=BLACK)
    handwrite(img, (520, y - 2), str(hand["effective_date"]), 40, "pv-date")
    y += 70
    box_top = y
    _box(d, (80, box_top, 1160, box_top + 470), "Réserves")
    ry = box_top + 56
    for line in facts["printed_reserves"]:
        d.text((110, ry), str(line), font=pil_font(22), fill=BLACK)
        ry += 46
    handwrite(img, (110, ry + 6), str(hand["added_reserve"]), 30, "pv-r07")
    y = box_top + 500
    d.text((80, y + 6), "Délai de levée des réserves :", font=pil_font(26, "bold"), fill=BLACK)
    handwrite(img, (520, y - 2), str(hand["lifting_delay"]), 40, "pv-delay")
    y += 80
    titles = ["Le maître d'ouvrage", "Le maître d'œuvre", "L'entrepreneur"]
    width = 340
    for index, (title, signer) in enumerate(zip(titles, hand["signers"], strict=True)):
        x0 = 80 + index * (width + 30)
        _box(d, (x0, y, x0 + width, y + 230), title)
        handwrite(img, (x0 + 24, y + 70), str(signer), 32, f"pv-signer-{index}")
        scribble(d, x0 + 30, y + 170, width - 70, f"pv-sign-{index}")
    d.text((80, PAGE_H - 80), STAMP, font=pil_font(24, "bold"), fill=BLACK)
    return img


def pv_scan(w: World) -> bytes:
    doc = w.doc("nac-pv")
    meta = meta_for(doc, w.org_name(str(doc["organisation"])))
    if int(_facts(w)["pv_reception"]["pages"]) != 1:
        raise ValueError("the PV scan has exactly one page")
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_title(meta.title)
    pdf.set_subject(STAMP)
    pdf.set_author(GENERATOR_AUTHOR)
    pdf.set_creator(GENERATOR_AUTHOR)
    pdf.set_producer(GENERATOR_AUTHOR)
    pdf.set_keywords(meta.keywords)
    pdf.set_creation_date(meta.created)
    pdf.set_lang(meta.lang)
    pdf.set_auto_page_break(False)
    pdf.add_page()
    pdf.image(io.BytesIO(_scan(_pv_page(w), -0.35, 9017)), x=0, y=0, w=210, h=297)
    return bytes(pdf.output())


# ------------------------------------------------------------------------------------------
# Réserves list and lifting status (2026-04-14)


def reserves(w: World) -> bytes:
    facts = _facts(w)["reserves"]
    doc = w.doc("nac-reserves")
    b = WorkbookBuilder(f"{w.builder['name']} - {doc['title']}")
    rows: list[Sequence[object]] = []
    for row in facts["rows"]:
        lifted = row["lifted"]
        rows.append([row["id"], row["where"], row["what"], row["lot"], w.org_name(row["by"]),
                     "Levée" if lifted else "Non levée",
                     date.fromisoformat(str(lifted)) if lifted else None, row["note"] or None])
    rows.append([])
    rows += [
        ["Réserves levées", None, None, None, None, int(facts["lifted_count"])],
        ["Réserves non levées", None, None, None, None, int(facts["open_count"])],
        ["Document", f"Liste des réserves au {fr_date(str(facts['date']))}"],
        ["Établi par", _person_line(w, str(facts["author"]))],
        ["Observations", str(facts["header_note"])],
    ]
    b.sheet("Réserves", facts["columns"], rows, widths=[8, 30, 46, 10, 22, 12, 12, 52])
    return b.render(w, "nac-reserves")


# ------------------------------------------------------------------------------------------
# VanArsdel e-mail (2026-04-08): the aluminium shortage reaches the hall doors


def mail_vanarsdel(w: World) -> bytes:
    facts = _facts(w)["mail_vanarsdel"]
    sent = datetime.fromisoformat(str(facts["date"]))
    to = list(facts["to"])
    recipient = w.name(to[0]).split()[-1]
    body = _body([
        [f"Bonjour Monsieur {recipient},"],
        _wrap(facts["delay_paragraph"]),
        _wrap(facts["scope_paragraph"]),
        _wrap(facts["apology"]),
        ["Cordialement,"],
        [str(facts["signature"])],
    ])
    return _message(w, str(facts["from"]), to, list(facts["cc"]), str(facts["subject"]), sent,
                    _message_id(sent, "report-portes", w, str(facts["from"])), body)
