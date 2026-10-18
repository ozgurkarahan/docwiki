"""Plain text and Markdown documents: shift notes (EN, FR), supplier note (DE), IT handbook."""

from __future__ import annotations

from .common import STAMP
from .world import World


def _join(lines: list[str]) -> str:
    return "\n".join(lines) + "\n"


def shift_en_1(w: World) -> str:
    return _join(
        [
            STAMP,
            "",
            "# Shift handover - 2026-07-15 (day shift to night shift)",
            "",
            "Written by: Callum Rydings, Lead Wind Technician",
            "",
            "Site: Quellmoor Ridge Wind Farm",
            "",
            "## Status",
            "",
            "- Grid curtailment day 2 of 3 (CPL-CI-2026-018): park export limited to 20 MW from "
            "08:00 to 18:00. All turbines back to normal at 18:00.",
            "- WTG-03, WTG-04 and WTG-05 will stop tonight from 22:00 if the wind stays low "
            "(bat curtailment). This is normal, do not reset.",
            "- WTG-07: HSS bearing vibration still around 5.3 mm/s. Oil temperature normal since "
            "the fan motor replacement. WO-26-0412 is waiting for the bearing.",
            "- WTG-04: drone check of blade B on 2026-07-02, crack unchanged at 0.9 m.",
            "",
            "## Work done today",
            "",
            "- WTG-05 daily checklist CHK-05 completed yesterday, all items OK.",
            "- Rescue kit inspections on WTG-01 to WTG-04 (MP-HSE-01).",
            "- Radiator cleaning MP-GBX-07 on WTG-03 postponed to next week.",
            "",
            "## For the next shift",
            "",
            "- Watch the WTG-07 oil temperature in the afternoon.",
            "- The spill kit of WTG-12 needs a refill (AWI-20915).",
            "",
            STAMP,
        ]
    )


def shift_fr(w: World) -> str:
    return _join(
        [
            STAMP,
            "Note de relève - équipe de jour - 18/07/2026",
            "Rédigée par : Élise Ternaux, technicienne éolienne",
            "Parc : Quellmoor Ridge Wind Farm",
            "",
            "WTG-09 : remplacement des balais de génératrice (OT WO-26-0436) suite à l'alarme "
            "A3210 du 16/07.",
            "  Longueur la plus courte mesurée : 16 mm (balai B3), donc sous le seuil de 18 mm de "
            "la WI-GEN-014.",
            "  Jeu complet remplacé (LWS-P-51207), vis du porte-balais serrées à 12 N·m.",
            "  Rodage à 50 % de puissance pendant 8 heures, jusqu'à 20:00 ce soir.",
            "WTG-07 : température d'huile maximale 66 °C aujourd'hui, pas d'alarme. Vibration "
            "toujours élevée, en attente du roulement.",
            "WTG-04 : contrôle visuel de la pale B depuis le sol, rien de nouveau.",
            "WTG-12 : kit antipollution réapprovisionné.",
            "",
            "Pour l'équipe suivante : vérifier la fin du rodage de WTG-09 à 20:00 (retour à 100 % "
            "de puissance).",
            STAMP,
        ]
    )


def shift_en_2(w: World) -> str:
    return _join(
        [
            STAMP,
            "SHIFT HANDOVER 2026-07-29 - day shift",
            "By: Callum Rydings",
            "",
            "WTG-02: the endoscope inspection on 23/07 found spalling on the HSS bearing",
            "  (generator side). WO-26-0439 raised on 24/07, waiting for the same bearing as",
            "  WTG-07 (FGT-P-22328). Turbine kept in operation, vibration reviewed weekly.",
            "WTG-11: small hydraulic oil leak at a yaw brake hose found today. The hose",
            "  AWI-10442 is not stocked, order to be raised. Leak contained with absorbent",
            "  pads and checked every shift.",
            "WTG-05: rescue kit inspection started (WO-26-0444), to finish next week.",
            "WTG-07: no oil temperature alarm since 24/06.",
            "Night: WTG-03, WTG-04 and WTG-05 bat curtailment expected again (low wind).",
            STAMP,
        ]
    )


def supplier_de(w: World) -> str:
    return _join(
        [
            STAMP,
            "Fabrikam Getriebetechnik GmbH - Lieferantenhinweis",
            "Datum: 03.08.2026",
            "An: Contoso Renewables, Quellmoor Ridge Wind Farm (Tomasz Lebrecht, Dario Penwarden)",
            "Von: Katrin Ostermeier, Field Service",
            "Betreff: Bestellung PO-76994 - HSS-Lager FGT-P-22328 / Hinweise nach der Ölumstellung",
            "",
            "1. Liefertermin",
            "Die zwei HSS-Lager FGT-P-22328 aus der Bestellung PO-76994 können nicht in KW 39 "
            "geliefert werden.",
            "Neuer bestätigter Liefertermin: KW 40 (28.09.2026 bis 02.10.2026).",
            "Grund: Verzögerung bei der Wärmebehandlung der Außenringe. Eine Luftfracht verkürzt "
            "die Lieferzeit nicht mehr.",
            "",
            "2. Hinweis nach der Umstellung auf PWG 220",
            "Nach der Umstellung von PWG 320 auf PWG 220 ist das Ölfilterelement FGT-P-11872 nach "
            "500 Betriebsstunden ein zweites Mal zu wechseln, da sich gelöste Ablagerungen im "
            "Filter sammeln.",
            "Zum gleichen Zeitpunkt empfehlen wir eine Ölprobe.",
            "",
            "3. Einbau der HSS-Lager",
            "Das neue Lager vor der Montage induktiv auf 110 °C erwärmen (maximal 120 °C).",
            "Anzugsmoment der Lagerdeckelschrauben M16: 210 Nm.",
            "Nach dem Einbau eine Ölprobe nach 500 Betriebsstunden nehmen.",
            "",
            "Für Rückfragen stehe ich gerne zur Verfügung.",
            "",
            "Mit freundlichen Grüßen",
            "Katrin Ostermeier",
            "Field Service Engineer, Fabrikam Getriebetechnik GmbH",
            "katrin.ostermeier@fabrikam-getriebe.example",
            STAMP,
        ]
    )


def it_handbook(w: World) -> str:
    return _join(
        [
            STAMP,
            "",
            "# Relecloud on-call handbook",
            "",
            "Owner: Oskar Vennholm, Site Reliability Engineering Lead. Last review: 2026-01-19.",
            "",
            "## Rotations",
            "",
            "- sre-primary and sre-secondary: weekly, handover on Monday at 10:00.",
            "- dba-primary: weekly, handover on Tuesday at 10:00.",
            "- business-hours: Monday to Friday, 08:00 to 18:00.",
            "",
            "## Severity levels",
            "",
            "| Severity | Definition | Acknowledge within | Incident commander |",
            "|---|---|---|---|",
            "| SEV1 | Tier 1 service down or data loss | 5 minutes | within 15 minutes |",
            "| SEV2 | Tier 1 service degraded or tier 2 service down | 15 minutes | within 30 "
            "minutes |",
            "| SEV3 | Minor degradation without customer impact | 1 hour | not required |",
            "| SEV4 | Cosmetic or internal only | next business day | not required |",
            "",
            "## During an incident",
            "",
            "1. Acknowledge the page and open an incident channel.",
            "2. For SEV1 and SEV2, name an incident commander; the commander decides on rollbacks "
            "and failovers (for orders-db see PRC-DB-007).",
            "3. Post a status update every 30 minutes for SEV1 and every hour for SEV2.",
            "4. Keep a timeline; it becomes the basis of the postmortem.",
            "",
            "## After an incident",
            "",
            "- A blameless postmortem is written within 5 working days for every SEV1 and SEV2.",
            "- Action items get an owner and a due date and are reviewed weekly.",
            "",
            "## Escalation",
            "",
            "On-call SRE, then the database administrator on call (dba-primary), then the "
            "engineering manager (Jun Hallgarth) for SEV1.",
            "",
            STAMP,
        ]
    )
