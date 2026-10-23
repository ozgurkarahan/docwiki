"""Company documents (scope `entreprise`): general terms, organisation chart, the Zava framework
contract and 2026 price list, the crew schedule, the equipment and subcontractor-attestation
registers, the billing register and the restricted margin dashboard."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from .common import dec, fr_date, meta_for
from .datasets_f import billing_position, check_margins, framework_prices
from .gen_docx import DocxBuilder
from .gen_nacrines import signature_table
from .gen_xlsx import WorkbookBuilder
from .pdfdoc import StampedPDF
from .world import World

CHANTIER_LABELS = {
    "moreau": "Chantier Moreau",
    "nacrines": "Résidence Les Nacrines",
    "ecole-montferrine": "École de Montferrine",
    "depot": "Dépôt",
}


def _facts(w: World) -> dict:
    return w.facts["entreprise"]


def _day(value: object) -> date | None:
    return date.fromisoformat(str(value)) if value else None


def _chantier(w: World, code: str) -> dict:
    return next(c for c in w.data["chantiers"] if c["code"] == code)


def _contract_type(code: str, w: World) -> str:
    return {"particulier": "Marché privé (particulier)", "privé": "Marché privé (copropriété)",
            "public": "Marché public"}[str(_chantier(w, code)["contract_type"])]


# ------------------------------------------------------------------------------------------
# General terms 2026 (PDF)


def conditions_generales(w: World) -> bytes:
    facts = _facts(w)["conditions_generales"]
    doc = w.doc("ent-cgv")
    builder = w.builder
    pdf = StampedPDF(meta_for(doc, builder["name"]), f"{builder['name']} - {facts['title']}",
                     builder["name"])
    pdf.add_page()
    pdf.title_line(builder["name"], 16)
    pdf.para(f"{builder['role_fr'][:1].upper()}{builder['role_fr'][1:]}, "
             f"{w.facts['site']['builder_address']}")
    pdf.title_line(f"{facts['title']} (en vigueur au {fr_date(str(facts['date']))})", 14)
    for section in facts["sections"]:
        pdf.h1(str(section["title"]))
        pdf.bullets([str(item) for item in section["items"]])
    return pdf.render()


# ------------------------------------------------------------------------------------------
# Organisation chart (PDF table)


def organigramme(w: World) -> bytes:
    facts = _facts(w)["organigramme"]
    doc = w.doc("ent-organigramme")
    builder = w.builder
    pdf = StampedPDF(meta_for(doc, builder["name"]), f"{builder['name']} - Organigramme",
                     builder["name"])
    pdf.add_page()
    pdf.title_line(f"Organigramme {builder['name']}", 16)
    pdf.para(f"Mis à jour le {fr_date(str(facts['date']))}")
    pdf.grid(
        ["Service", "Nom", "Fonction", "Rattachement", "Chantiers ou missions"],
        [[str(row["unit"]), w.name(row["person"]), w.role(row["person"]),
          w.name(row["reports_to"]) if row["reports_to"] else "-", str(row["chantiers"])]
         for row in facts["rows"]],
        widths=(29, 33, 46, 31, 35),
        align=("LEFT", "LEFT", "LEFT", "LEFT", "LEFT"),
    )
    pdf.para(str(facts["note"]))
    return pdf.render()


# ------------------------------------------------------------------------------------------
# Zava framework contract (DOCX) and its 2026 price list (XLSX)


def contrat_cadre(w: World) -> bytes:
    facts = _facts(w)["contrat_cadre"]
    day = str(facts["date"])
    merchant = w.org("zava-materiaux")
    b = DocxBuilder(f"{merchant['name']} - {facts['title']}",
                    f"{facts['title']} - {merchant['name']} et {w.builder['name']}")
    b.title(str(facts["title"]))
    b.para("Entre les soussignés :", bold=True)
    b.para(str(facts["parties"]["fournisseur"]))
    b.para("et")
    b.para(str(facts["parties"]["client"]))
    for article in facts["articles"]:
        b.h1(str(article["title"]))
        b.para(str(article["text"]))
    b.label("Annexe", f"Tarif 2026 contrat-cadre du {fr_date(str(_facts(w)['tarif']['date']))}.")
    b.para(f"Fait à {w.town}, le {fr_date(day)}, en deux exemplaires originaux.")
    supplier, client = facts["signatories"]
    signed = f"Lu et approuvé, signé le {fr_date(day)}"
    signature_table(b, [
        ("Pour le fournisseur", [merchant["name"], f"{w.name(supplier)}, "
                                 f"{w.role(supplier).lower()}", signed]),
        ("Pour le client", [w.builder["name"], f"{w.name(client)}, {w.role(client).lower()}",
                            signed]),
    ])
    return b.render(w, "ent-contrat-cadre")


def tarif(w: World) -> bytes:
    facts = _facts(w)["tarif"]
    framework_prices(w)
    merchant = w.org("zava-materiaux")
    b = WorkbookBuilder(f"{merchant['name']} - {facts['title']}")
    rows: list[Sequence[object]] = [
        [row["code"] or "-", row["designation"], row["unit"], dec(row["public"]), dec(row["net"])]
        for row in facts["rows"]
    ]
    rows.append([])
    rows += [
        ["Document", f"{facts['title']} du {fr_date(str(facts['date']))}, annexé au contrat-cadre "
                     "d'approvisionnement 2026"],
        ["Client", f"{w.builder['name']}, {w.facts['site']['builder_address']}"],
        ["Observations", "Prix nets HT, fermes du 01/01/2026 au 31/12/2026, applicables à tous "
                         "les chantiers du client."],
    ]
    b.sheet("Tarif 2026", facts["columns"], rows, widths=[12, 54, 18, 16, 20])
    return b.render(w, "ent-tarif")


# ------------------------------------------------------------------------------------------
# Crew schedule, weeks 15 to 17 (XLSX)


def planning_equipes(w: World) -> bytes:
    facts = _facts(w)["planning_equipes"]
    b = WorkbookBuilder(f"{w.builder['name']} - {facts['title']}")
    rows: list[Sequence[object]] = [
        [int(row["week"]), _day(row["start"]), _day(row["end"]), w.name(row["person"]),
         w.role(row["person"]), row["chantier"], CHANTIER_LABELS[row["chantier"]], row["task"]]
        for row in facts["rows"]
    ]
    rows.append([])
    author = str(facts["author"])
    rows += [
        ["Document", f"{facts['title']}, établi le {fr_date(str(facts['date']))}"],
        ["Établi par", f"{w.name(author)}, {w.role(author).lower()}"],
        ["Observations", str(facts["note"])],
    ]
    b.sheet("Équipes", facts["columns"], rows, widths=[9, 12, 12, 20, 24, 18, 22, 56])
    return b.render(w, "ent-planning-equipes")


# ------------------------------------------------------------------------------------------
# Equipment register (XLSX)


def registre_materiel(w: World) -> bytes:
    facts = _facts(w)["registre_materiel"]
    b = WorkbookBuilder(f"{w.builder['name']} - {facts['title']}")
    rows: list[Sequence[object]] = [
        [item["code"], item["name"], item["category"], _day(item["in_service"]),
         item["inspection"] or "Non soumis", _day(item["last_inspection"]),
         _day(item["next_inspection"]), CHANTIER_LABELS[item["assignment"]]]
        for item in w.data["equipment"]
    ]
    rows.append([])
    author = str(facts["author"])
    rows += [
        ["Document", f"{facts['title']} au {fr_date(str(facts['date']))}"],
        ["Tenu par", f"{w.name(author)}, {w.role(author).lower()}"],
    ]
    b.sheet("Matériel", facts["columns"], rows, widths=[9, 40, 28, 13, 40, 14, 14, 22])
    return b.render(w, "ent-registre-materiel")


# ------------------------------------------------------------------------------------------
# Subcontractor attestations register (XLSX)


def registre_attestations(w: World) -> bytes:
    facts = _facts(w)["registre_attestations"]
    b = WorkbookBuilder(f"{w.builder['name']} - {facts['title']}")
    rows: list[Sequence[object]] = [
        [w.org_name(row["org"]), row["chantiers"], row["document"], _day(row["issued"]),
         _day(row["valid_until"]), _day(row["received"]), row["note"] or None]
        for row in facts["rows"]
    ]
    rows.append([])
    author = str(facts["author"])
    rows += [
        ["Document", f"{facts['title']} au {fr_date(str(facts['date']))}"],
        ["Tenu par", f"{w.name(author)}, {w.role(author).lower()}"],
        ["Observations", "Attestation de vigilance : validité de six mois à compter de sa date ; "
                         "à obtenir à la signature puis tous les six mois jusqu'à la fin des "
                         "travaux sous-traités."],
    ]
    b.sheet("Attestations", facts["columns"], rows, widths=[22, 40, 46, 14, 14, 12, 20])
    return b.render(w, "ent-registre-attestations")


# ------------------------------------------------------------------------------------------
# Billing register (XLSX): every chantier's contract and client invoices


def suivi_facturation(w: World) -> bytes:
    facts = _facts(w)["suivi_facturation"]
    billing_position(w)
    b = WorkbookBuilder(f"{w.builder['name']} - {facts['title']}")
    marches: list[Sequence[object]] = []
    for row in facts["marches"]:
        chantier = _chantier(w, row["chantier"])
        marches.append([row["chantier"], CHANTIER_LABELS[row["chantier"]],
                        w.org_name(str(chantier["client"])), _contract_type(row["chantier"], w),
                        dec(row["initial_ht"]), dec(row["changes_ht"]), dec(row["total_ht"]),
                        dec(row["vat"]), dec(row["total_ttc"]), row["retention"]])
    b.sheet("Marchés", facts["columns_marches"], marches,
            widths=[18, 22, 34, 24, 16, 16, 16, 14, 16, 36])
    invoices = [dict(facts["moreau_invoice"], chantier="moreau")]
    invoices += [dict(raw, chantier="nacrines", object=f"Situation n°{raw['n']}")
                 for raw in w.facts["nacrines"]["situations"]]
    invoices.sort(key=lambda item: (str(item["date"]), str(item["invoice"])))
    factures: list[Sequence[object]] = [
        [item["chantier"], item["invoice"], _day(item["date"]), item["object"], dec(item["ht"]),
         dec(item["vat"]), dec(item["ttc"]), dec(item["retention"]), dec(item["net"]),
         item["status"]]
        for item in invoices
    ]
    factures.append([])
    author = str(facts["author"])
    factures += [
        ["Document", f"{facts['title']} au {fr_date(str(facts['date']))}"],
        ["Tenu par", f"{w.name(author)}, {w.role(author).lower()}"],
    ]
    b.sheet("Factures", facts["columns_factures"], factures,
            widths=[18, 14, 12, 40, 14, 12, 14, 16, 16, 52])
    if b.wb.sheetnames != list(facts["sheets"]):
        raise ValueError(f"billing register sheets {b.wb.sheetnames} differ from the bible")
    return b.render(w, "ent-suivi-facturation")


# ------------------------------------------------------------------------------------------
# Margin dashboard (XLSX, restricted)


def tableau_marges(w: World) -> bytes:
    facts = _facts(w)["tableau_marges"]
    check_margins(w)
    b = WorkbookBuilder(str(w.doc("ent-marges")["title"]))
    fields = ("contract_ht", "planned_cost_ht", "planned_margin_ht", "rate", "actual_cost_ht",
              "billed_ht", "margin_to_date_ht")

    def values(row: dict) -> list[object]:
        return [row["rate"] if field == "rate" else dec(row[field]) for field in fields]

    rows: list[Sequence[object]] = [
        [row["chantier"], CHANTIER_LABELS[row["chantier"]], *values(row)] for row in facts["rows"]
    ]
    rows.append(["Total", None, *values(facts["totals"])])
    rows.append([])
    author = str(facts["author"])
    rows += [
        ["Document", f"{facts['title']}, établi le {fr_date(str(facts['date']))}"],
        ["Établi par", f"{w.name(author)}, {w.role(author).lower()}"],
        ["Diffusion", "Restreinte à la direction"],
    ]
    b.sheet("Marges", facts["columns"], rows, widths=[18, 22, 16, 18, 18, 12, 16, 14, 16],
            bold_rows=(len(facts["rows"]) + 1,))
    return b.render(w, "ent-marges")
