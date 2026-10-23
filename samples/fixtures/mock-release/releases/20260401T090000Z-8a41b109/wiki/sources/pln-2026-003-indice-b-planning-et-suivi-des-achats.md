---
id: src-59cf9366e50c
type: source
title: Planning and purchase tracking, indice B
summary: Current indice B of the schedule PLN-2026-003, a workbook that postpones the window delivery.
lang: en
sensitivity: public
updated: 2026-04-01
tags:
- planning
- schedule
- windows
docwiki:
  schema: 1
  release: 20260401T090000Z-8a41b109
source_id: src-59cf9366e50c
source_path: chantiers/moreau/3-execution/schedule/PLN-2026-003_indice-B_planning-et-suivi-des-achats.xlsx
source_hash: sha256:3b46c47a34540bef170340c12f4bfdbc59b5e368d269bc8ca3d0cf36e5419ea0
media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
doc_type: schedule
category: schedule-and-purchases
doc_number: PLN-2026-003
revision: B
scope: null
phase: null
lot: null
status: current
supersedes:
- src-7630d0741377
superseded_by: []
original_lang: fr
pages: null
entities:
- organisation:vanarsdel-menuiseries
- work-package:lot-3-gros-oeuvre
- work-package:lot-5-menuiseries-exterieures
topics:
- topic:planning
authority: 4
extraction:
  adapter: local
  version: mock-1
  provenance_mix:
    deterministic-table: 33
---

# Planning and purchase tracking, indice B

> FICTIONAL SAMPLE - Lamna Bâtiment, its chantiers (the Moreau household, the résidence Les Nacrines, the école de Montferrine), Valbrise, Montferrine and every organisation, person, product, amount and date in this wiki are invented. Not for operational use.

Indice B of the schedule ("planning") PLN-2026-003, a workbook with the sheets "Planning" and "Achats". It cancels and replaces [indice A](pln-2026-003-indice-a-planning-et-suivi-des-achats.md) and postpones the delivery of the windows.

## Key facts

- Indice B of the schedule PLN-2026-003 cancels and replaces indice A of 2026-03-17.[^c1]
- The reason is the postponement of the delivery of the windows to 2026-04-20, announced by [VanArsdel Menuiseries](../entities/organisation/vanarsdel-menuiseries.md) on 2026-03-18, and the decisions of site meeting n°3 of 2026-03-24.[^c1]
- Task T07, the delivery of the windows, is planned on 2026-04-20, with the remark "Livraison reportée".[^c2]
- Task T08, the installation of the windows, is planned from 2026-04-21 to 2026-04-23.[^c2]
- The walls ("élévation des murs", task T05) are at 100 %.[^c2]

## Contents

### Sheet "Planning"

The sheet lists the tasks of the job with their work package ("lot"), the company that carries them out, their dates and their progress; rows 6 to 9 hold the walls, the roof work, the delivery of the windows and their installation.[^c2] Agents can query the sheet as `t01` with the `query_table` tool.

### Sheet "Achats"

The sheet follows the purchase orders ("bons de commande") of the job. Agents can query it as `t02`.

### Document notes

Rows 24 and 25 of the sheet "Planning" state that indice B replaces indice A and give the reason.[^c1]

## Figures

No figures were extracted from this document.

## Related

- Organisation: [VanArsdel Menuiseries](../entities/organisation/vanarsdel-menuiseries.md)
- Work packages: [Lot 3 - Gros œuvre](../entities/work-package/lot-3-gros-oeuvre.md), [Lot 5 - Menuiseries extérieures](../entities/work-package/lot-5-menuiseries-exterieures.md)
- Topic: [Planning](../topics/planning.md)
- Supersedes: [Planning and purchase tracking, indice A](pln-2026-003-indice-a-planning-et-suivi-des-achats.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Lot 3 - Gros œuvre](../entities/work-package/lot-3-gros-oeuvre.md)
- [Lot 5 - Menuiseries extérieures](../entities/work-package/lot-5-menuiseries-exterieures.md)
- [Planning and purchase tracking, indice A](pln-2026-003-indice-a-planning-et-suivi-des-achats.md)
- [Planning](../topics/planning.md)
- [VanArsdel Menuiseries](../entities/organisation/vanarsdel-menuiseries.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Planning and purchase tracking, indice B — sheet "Planning", rows 24–25](../evidence/src-59cf9366e50c/sheet-planning-r0024-r0025.md) · table
[^c2]: [Planning and purchase tracking, indice B — sheet "Planning", rows 6–9](../evidence/src-59cf9366e50c/sheet-planning-r0006-r0009.md) · table
