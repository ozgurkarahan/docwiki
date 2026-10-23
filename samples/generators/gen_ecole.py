"""Chantier école de Montferrine (public contract, in preparation): the CCAP extract, the DPGF
indices A and B, the acte d'engagement, the VanArsdel purchase order, the summer planning, the
preparation meeting minutes, the mairie's e-mail and the PPSPS."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime

from .common import STAMP, eur, fr_date, meta_for, percent, quantity
from .datasets import org_label
from .datasets_f import dpgf, priced_lines, totals
from .gen_docx import DocxBuilder, _flat
from .gen_eml import _body, _message, _message_id, _wrap
from .gen_nacrines import signature_table
from .gen_pdf import _RIGHT_W, _RIGHT_X, _letterhead, _title_box
from .gen_xlsx import WorkbookBuilder
from .pdfdoc import StampedPDF
from .world import World

SITE_LABEL = "École élémentaire du Bourg, Montferrine"
MAIRIE_ADDRESS = "mairie, place de la Mairie, Montferrine"


def _facts(w: World) -> dict:
    return w.facts["ecole"]


def _person_line(w: World, key: str) -> str:
    return f"{w.name(key)}, {w.role(key).lower()}, {w.org_name(w.person(key)['organisation'])}"


# ------------------------------------------------------------------------------------------
# CCAP extract (2026-01-26), issued by the commune


def ccap(w: World) -> bytes:
    facts = _facts(w)["ccap"]
    doc = w.doc("eco-ccap")
    commune = w.org("commune-montferrine")
    pdf = StampedPDF(meta_for(doc, commune["name"]), f"{commune['name']} - CCAP", SITE_LABEL)
    pdf.add_page()
    bottom = _letterhead(pdf, w, commune["key"], MAIRIE_ADDRESS, "agnes-vautrelle")
    _title_box(pdf, "CCAP", ["Extrait", f"Date : {fr_date(str(facts['date']))}"])
    pdf.set_y(bottom + 6)
    pdf.title_line(str(facts["title"]), 13)
    pdf.label_para("Marché", _facts(w)["marche_title"])
    pdf.para(str(facts["procedure"]))
    for article in facts["articles"]:
        # Run-in headings keep the extract on one page.
        pdf.label_para(f"Article {article['n']} - {article['title']}", str(article["text"]))
        pdf.ln(1.2)
    if pdf.page_no() != 1:
        raise ValueError("the CCAP extract must stay on one page (PLANTED.md cites p0001)")
    return pdf.render()


# ------------------------------------------------------------------------------------------
# DPGF DEV-2026-031, indices A and B (company-wide quote series)


def _dpgf(w: World, indice: str, doc_id: str) -> bytes:
    facts = _facts(w)["dpgf"]
    lines, sums = dpgf(w, indice)
    data = facts[f"indice_{indice}"]
    revision = indice.upper()
    reference = f"{facts['title']} {facts['number']} indice {revision}"
    b = WorkbookBuilder(f"{w.builder['name']} - DPGF {facts['number']} indice {revision}")
    rate = int(facts["vat_rate"])
    rows: list[Sequence[object]] = [
        [line.ref, line.designation, line.unit, line.qty, line.unit_price, line.total]
        for line in lines
    ]
    rows += [
        ["Total HT", None, None, None, None, sums["ht"]],
        [f"TVA {percent(rate)}", None, None, None, None, sums["vat"]],
        ["Total TTC", None, None, None, None, sums["ttc"]],
        [],
        ["Marché", _facts(w)["marche_title"]],
        ["Maître d'ouvrage", w.org_name("commune-montferrine")],
        ["Candidat", f"{w.builder['name']}, {w.facts['site']['builder_address']}"],
        ["Document", f"{reference} du {fr_date(str(data['date']))}"],
        ["Établi par", _person_line(w, str(facts["author"]))],
    ]
    for key in ("supersedes_sentence", "changes_sentence"):
        if key in data:
            rows.append(["Observations", _flat(data[key])])
    if "difference_from_a" in data:
        diff = data["difference_from_a"]
        rows.append(["Observations", f"Écart par rapport à l'indice A : +{eur(diff['ht'])} HT, "
                                     f"soit +{eur(diff['ttc'])} TTC."])
    b.sheet("DPGF", facts["columns"], rows, widths=[16, 70, 8, 10, 16, 16],
            bold_rows=(len(lines) + 1, len(lines) + 3))
    return b.render(w, doc_id)


def dpgf_a(w: World) -> bytes:
    return _dpgf(w, "a", "eco-dpgf-a")


def dpgf_b(w: World) -> bytes:
    return _dpgf(w, "b", "eco-dpgf-b")


# ------------------------------------------------------------------------------------------
# Acte d'engagement (signed 2026-03-20, notified 2026-03-30)


def acte_engagement(w: World) -> bytes:
    facts = _facts(w)["acte_engagement"]
    doc = w.doc("eco-ae")
    commune = w.org("commune-montferrine")
    pdf = StampedPDF(meta_for(doc, w.builder["name"]), f"{commune['name']} - Acte d'engagement",
                     SITE_LABEL)
    pdf.add_page()
    bottom = _letterhead(pdf, w, commune["key"], MAIRIE_ADDRESS, "agnes-vautrelle")
    _title_box(pdf, "ACTE D'ENGAGEMENT", ["Marché public de travaux",
                                          "Procédure adaptée, lot unique"])
    pdf.set_y(bottom + 6)
    pdf.label_para("Objet du marché", _facts(w)["marche_title"])
    pdf.label_para("Maître d'ouvrage", f"{commune['name']}, représentée par son maire")
    pdf.h1("1. Engagement du titulaire")
    signer = str(facts["signatory"])
    pdf.para(f"{w.builder['name']}, {w.facts['site']['builder_address']}, représentée par "
             f"{w.name(signer)}, {w.role(signer).lower()}, s'engage à exécuter les travaux du "
             "marché aux conditions du CCAP et pour le prix ci-dessous.")
    pdf.label_para("Identification du titulaire", str(w.data["world"]["legal_identity"]))
    pdf.h1("2. Prix")
    price = facts["price"]
    pdf.para(f"Prix global et forfaitaire, selon la {facts['basis']} :")
    rate = int(_facts(w)["dpgf"]["vat_rate"])
    pdf.totals([("Montant HT", eur(price["ht"])), (f"TVA {percent(rate)}", eur(price["vat"])),
                ("Montant TTC", eur(price["ttc"]))])
    pdf.h1("3. Délais")
    pdf.para(f"Période de préparation : {facts['preparation']}. Exécution des travaux "
             f"{facts['works_period']}.")
    pdf.para(str(facts["advance_text"]))
    pdf.h1("4. Sous-traitance déclarée (paiement direct)")
    pdf.grid(["Sous-traitant", "Prestations", "Montant HT"],
             [[w.org_name(sub["org"]), str(sub["item"]), eur(sub["amount_ht"])]
              for sub in facts["subcontractors"]],
             widths=(48, 90, 36), align=("LEFT", "LEFT", "RIGHT"))
    pdf.signature_boxes([
        ("Le titulaire", [w.builder["name"], f"{w.name(signer)}, {w.role(signer).lower()}",
                          f"Signé le {fr_date(str(facts['date']))}"]),
        ("Le maître d'ouvrage", [f"Pour la commune de {commune['short']}, le maire",
                                 f"Offre acceptée le {fr_date(str(facts['accepted']))}",
                                 f"Notifié le {fr_date(str(facts['notified']))}"]),
    ])
    return pdf.render()


# ------------------------------------------------------------------------------------------
# Purchase order BC-2026-021 to VanArsdel Menuiseries (2026-04-02)


def bon_de_commande(w: World) -> bytes:
    facts = _facts(w)["bon_de_commande"]
    doc = w.doc("eco-bc-vanarsdel")
    builder = w.builder
    number = str(facts["number"])
    pdf = StampedPDF(meta_for(doc, builder["name"]), f"{builder['name']} - Bon de commande "
                     f"{number}", number, legal=w.legal_line(builder["key"]))
    pdf.add_page()
    bottom = _letterhead(pdf, w, builder["key"], w.facts["site"]["builder_address"],
                         str(facts["issuer"]))
    _title_box(pdf, "BON DE COMMANDE", [f"N° {number}", f"Date : {fr_date(str(facts['date']))}"])
    supplier = w.org(str(facts["supplier"]))
    supplier_bottom = pdf.framed_lines(_RIGHT_X, 52, _RIGHT_W, "Fournisseur",
                                       [supplier["name"], f"À l'attention de "
                                        f"{w.name('erwan-gouzelin')}"])
    pdf.set_y(max(bottom, supplier_bottom) + 5)
    pdf.label_para("Chantier", str(facts["delivered_to"]))
    pdf.label_para("Référence", str(facts["reference"]))
    lines = priced_lines(number, facts["lines"])
    rate = int(facts["totals"]["vat_rate"])
    sums = totals(number, facts["totals"], lines, rate)
    pdf.grid(["Réf.", "Désignation", "Qté", "U", "PU HT", "Total HT"],
             [[line.ref, line.designation, quantity(line.qty), line.unit, eur(line.unit_price),
               eur(line.total)] for line in lines],
             widths=(11, 87, 13, 10, 25, 28),
             align=("LEFT", "LEFT", "RIGHT", "CENTER", "RIGHT", "RIGHT"))
    pdf.totals([("Total HT", eur(sums["ht"])), (f"TVA {percent(rate)}", eur(sums["vat"])),
                ("Total TTC", eur(sums["ttc"]))])
    pdf.h1("Conditions")
    deposit = facts["deposit"]
    pdf.bullets([str(facts["delivery_text"]),
                 f"Acompte de {percent(deposit['percent'])} à la commande : "
                 f"{eur(deposit['amount_ht'])} HT.",
                 str(facts["payment_text"])])
    issuer = str(facts["issuer"])
    pdf.signature_boxes([
        (f"Pour {builder['name']}", [f"{w.name(issuer)}, {w.role(issuer).lower()}",
                                     f"{w.town}, le {fr_date(str(facts['date']))}"]),
        ("Accusé de réception du fournisseur", []),
    ])
    return pdf.render()


# ------------------------------------------------------------------------------------------
# Planning des travaux d'été PLN-2026-007 indice A (2026-04-10)


def planning(w: World) -> bytes:
    facts = _facts(w)["planning"]
    reference = f"{facts['title']} {facts['number']} indice {facts['revision']}"
    b = WorkbookBuilder(f"{w.builder['name']} - {reference}")
    rows: list[Sequence[object]] = [
        [t["id"], t["task"], t["item"], org_label(w, str(t["by"])),
         date.fromisoformat(str(t["start"])), date.fromisoformat(str(t["end"])),
         percent(t["progress"]), t["note"] or None]
        for t in facts["tasks"]
    ]
    rows.append([])
    rows += [
        ["Document", f"{reference} du {fr_date(str(facts['date']))}"],
        ["Chantier", f"{_facts(w)['marche_title']}, {_facts(w)['address']}"],
        ["Établi par", _person_line(w, str(facts["author"]))],
        ["Avancement au", date.fromisoformat(str(facts["date"]))],
        ["Observations", str(facts["holidays_note"])],
    ]
    b.sheet("Planning", facts["columns"], rows, widths=[8, 40, 8, 26, 12, 12, 12, 40])
    return b.render(w, "eco-planning")


# ------------------------------------------------------------------------------------------
# Preparation meeting minutes n°1 (2026-04-16)


def compte_rendu(w: World) -> bytes:
    facts = _facts(w)["compte_rendu_preparation"]
    day = str(facts["date"])
    title = f"Compte rendu de la réunion de préparation n°{facts['number']}"
    b = DocxBuilder(f"{w.builder['name']} - {title}", f"{title} - {SITE_LABEL}")
    b.title(title)
    b.label("Objet", str(facts["subject"]))
    b.label("Date de la réunion", f"{fr_date(day)} à {facts['time']}")
    b.label("Lieu", str(facts["place"]))
    b.label("Rédigé par", _person_line(w, str(facts["written_by"])))
    present, excused = list(facts["present"]), list(facts["excused"])
    people = [*present, *excused, *facts["distribution_extra"]]
    b.table(
        ["Nom", "Organisation", "Fonction", "Présent", "Excusé", "Diffusion"],
        [[w.name(k), w.org_name(w.person(k)["organisation"]), w.role(k),
          "x" if k in present else "", "x" if k in excused else "", "x"] for k in people],
        widths=(3.6, 3.8, 4.4, 1.7, 1.7, 1.8),
    )
    b.h1("1. Points examinés")
    b.bullets([str(item) for item in facts["points"]])
    b.h1("2. Décisions")
    for decision in facts["decisions"]:
        b.para(f"{decision['id']} - {decision['text']}")
    b.h1("3. Actions")
    b.table(["Action", "Responsable", "Échéance"],
            [[str(a["what"]), w.label(str(a["who"])), fr_date(str(a["due"]))]
             for a in facts["actions"]], widths=(10.5, 3.8, 2.7))
    b.h1("4. Prochaine réunion")
    b.para(str(facts["next_meeting"]))
    return b.render(w, "eco-cr-prep")


# ------------------------------------------------------------------------------------------
# E-mail of the mairie (2026-04-21)


def mail_mairie(w: World) -> bytes:
    facts = _facts(w)["mail_mairie"]
    sent = datetime.fromisoformat(str(facts["date"]))
    to = list(facts["to"])
    recipient = w.name(to[0]).split()[-1]
    body = _body([
        [f"Bonjour Madame {recipient},"],
        *(_wrap(paragraph) for paragraph in facts["paragraphs"]),
        ["Cordialement,"],
        [str(facts["signature"])],
    ])
    return _message(w, str(facts["from"]), to, list(facts["cc"]), str(facts["subject"]), sent,
                    _message_id(sent, "accueil-de-loisirs", w, str(facts["from"])), body)


# ------------------------------------------------------------------------------------------
# PPSPS (2026-04-24): procedure-like, stamped in the header, the footer and a notice


def ppsps(w: World) -> bytes:
    facts = _facts(w)["ppsps"]
    day = str(facts["date"])
    b = DocxBuilder(f"{w.builder['name']} - PPSPS", f"PPSPS - {SITE_LABEL}")
    b.title(str(facts["title"]))
    b.para(f"{STAMP} - {facts['notice']}", bold=True)
    b.h1("1. Renseignements généraux")
    b.table(["Rubrique", "Valeur"], [list(row) for row in facts["general"]], widths=(5.0, 12.0))
    b.h1("2. Entreprises intervenantes")
    b.table(["Entreprise", "Travaux", "Effectif", "Période"],
            [list(row) for row in facts["parties"]], widths=(3.8, 7.0, 1.8, 4.4))
    b.h1("3. Installations d'hygiène")
    b.para(str(facts["hygiene"]))
    b.para(str(facts["asbestos"]))
    b.h1("4. Analyse des risques et mesures de prévention")
    b.table(["Risque", "Situation de travail", "Mesures"],
            [list(row) for row in facts["risks"]], widths=(3.4, 5.0, 8.6))
    b.h1("5. Secours")
    b.para(str(facts["first_aid"]))
    b.table(["Secours", "Appel"], [list(row) for row in facts["emergency"]], widths=(8.0, 9.0))
    author = str(facts["author"])
    signature_table(b, [("Établi par", [w.builder["name"], f"{w.name(author)}, "
                                        f"{w.role(author).lower()}", f"Le {fr_date(day)}"])])
    b.para(STAMP, bold=True)
    return b.render(w, "eco-ppsps")
