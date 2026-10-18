---
id: src-aba30cb7207f
type: source
title: Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm
summary: This spreadsheet is the 2026 maintenance plan, issue 2 dated 2026-07-01, for Quellmoor Ridge Wind Farm. It contains a maintenance task catalogue, a per-turbine 2026 plan, oil sampling results, and a revision log.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- maintenance-plan
- records-and-data
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-aba30cb7207f
source_path: full/records/maintenance-plan-2026.xlsx
source_hash: sha256:4b362c6062ec7e36275a51c6bb8d495646640209b0a31576bce9f76cf3cf07d4
media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
doc_type: maintenance-plan
category: records-and-data
doc_number: null
revision: B
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- asset:quellmoor-ridge-wind-farm
- asset:wtg-01
- asset:wtg-02
- asset:wtg-03
- asset:wtg-04
- asset:wtg-05
- asset:wtg-06
- asset:wtg-07
- asset:wtg-08
- asset:wtg-09
- asset:wtg-10
- asset:wtg-11
- asset:wtg-12
- bulletin:sb-lws-2025-11
- component:gearbox
- component:generator
- component:generator-brushes
- component:hydraulic-system
- component:oil-cooler
- component:oil-filter
- component:pitch-bearing
- component:pitch-bearing-bolts
- component:rescue-kit
- component:rotor-blade
- component:slip-ring
- component:yaw-system
- organisation:contoso-renewables
- organisation:wingtip-blade-services
- part:fgt-p-11872
- procedure:sop-gbx-010
- procedure:sop-wah-003
- procedure:wi-gen-014
- product:lt-32
- product:pwg-220
topics:
- topic:blades-and-rotor
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:generator-and-electrical
- topic:safety-and-access
authority: 6
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    deterministic-table: 146
---

# Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This spreadsheet is the 2026 maintenance plan, issue 2 dated 2026-07-01, for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md). It contains a maintenance task catalogue, a per-turbine 2026 plan, oil sampling results, and a revision log.

## Key facts

- The document is Maintenance plan 2026, issue 2 dated 2026-07-01, for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c1]
- The plan owner is Dario Penwarden, O&M Supervisor at [Contoso Renewables](../entities/organisation/contoso-renewables.md).[^c2]
- The spreadsheet contains the Tasks, Plan 2026, Oil sampling, and Revision log sheets.[^c3]
- Issue 2 added task MP-GBX-07 for all turbines after INC-2026-006 and brought the [WTG-02](../entities/asset/wtg-02.md) endoscope inspection forward to July.[^c4]
- [Gearbox](../entities/component/gearbox.md) oil sampling and laboratory analysis task MP-GBX-01 is scheduled every 6 months, with a duration field of 1 h and crew field of 1.[^c5]
- Gearbox [oil filter element](../entities/component/oil-filter.md) replacement task MP-GBX-02 uses part [FGT-P-11872](../entities/part/fgt-p-11872.md), is scheduled every 12 months, and references [SOP-GBX-010](../entities/procedure/sop-gbx-010.md).[^c6]
- Gearbox oil change task MP-GBX-03 for [PWG 220](../entities/product/pwg-220.md) is scheduled every 5 years or on condition, references SOP-GBX-010 Rev. B, has a duration field of 6 h, and notes that the next planned changes start from 2030.[^c7]
- Vibration trend review task MP-GBX-06 is monthly, has a duration field of 0.5 h, and is noted as a remote review by the Reliability Engineer.[^c8]
- [Oil cooler](../entities/component/oil-cooler.md) radiator cleaning and fan current check task MP-GBX-07 is scheduled every 6 months, references INC-2026-006 (D7), and was added in issue 2 on 2026-07-01.[^c9]
- [Generator](../entities/component/generator.md) brush inspection task MP-GEN-01 is scheduled every 6 months and references [WI-GEN-014](../entities/procedure/wi-gen-014.md).[^c10]
- [Slip ring](../entities/component/slip-ring.md) cleaning task MP-GEN-02 is scheduled every 12 months and references WI-GEN-014.[^c11]
- [Pitch bearing](../entities/component/pitch-bearing.md) bolt re-torque task MP-PIT-01 covers 100 % of bolts at 1,450 Nm, is scheduled every 12 months, and references [SB-LWS-2025-11](../entities/bulletin/sb-lws-2025-11.md) Rev. A.[^c12]
- Blade drone inspection task MP-BLD-01 is scheduled every 12 months and is noted as a contractor task for [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md).[^c13]
- [Rescue kit](../entities/component/rescue-kit.md) inspection task MP-HSE-01 is scheduled every 6 months and references [SOP-WAH-003](../entities/procedure/sop-wah-003.md) section 7.[^c14]
- Fall arrest rail and ladder inspection task MP-HSE-02 is scheduled every 12 months and references SOP-WAH-003.[^c15]
- In the Plan 2026 sheet, WTG-02 gearbox endoscope inspection task MP-GBX-04 is planned for 2026-07 and has status done at 2026-07-01.[^c16]
- [WTG-07](../entities/asset/wtg-07.md) oil sampling report TR-OA-2026-0614 recorded PWG 220 oil, Fe of 64 ppm, PQ index of 112, condition ALERT, and next sample due 2026-07-10 with resampling within 30 days.[^c17]
- Issue 1 was issued on 2025-12-15 and updated the oil sampling schedule for PWG 220 under MOC-2025-012 action 5.[^c18]

## Contents

### Tasks

The Tasks sheet is the task catalogue for the plan.[^c3]

It includes [gearbox](../entities/component/gearbox.md) tasks for oil sampling, [oil filter element](../entities/component/oil-filter.md) replacement, oil change, endoscope inspection, visual inspection and leak check, vibration trend review, and [oil cooler](../entities/component/oil-cooler.md) radiator cleaning with fan current check.[^c5][^c6][^c7][^c19][^c20][^c8][^c9]

It also includes [generator](../entities/component/generator.md) brush inspection, [slip ring](../entities/component/slip-ring.md) cleaning, [pitch bearing](../entities/component/pitch-bearing.md) bolt re-torque, blade drone inspection, yaw brake pad inspection, hydraulic accumulator pre-charge check, [rescue kit](../entities/component/rescue-kit.md) inspection, and fall arrest rail and ladder inspection.[^c10][^c11][^c12][^c13][^c21][^c22][^c14][^c15]

The pitch bearing bolt re-torque task specifies 100 % of bolts and 1,450 Nm.[^c12]

**Table t01** · sheet "Tasks", rows 1–16

| Row | Task ID | Task | System | Interval | Procedure or reference | Duration (h) | Crew | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | MP-GBX-01 | Gearbox oil sampling and laboratory analysis | Gearbox | 6 months | LWS-MM-GBX-32 section 4.4 | 1 | 1 |  |
| 3 | MP-GBX-02 | Gearbox oil filter element replacement ([FGT-P-11872](../entities/part/fgt-p-11872.md)) | Gearbox | 12 months | [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) | 1.5 | 2 |  |
| 4 | MP-GBX-03 | Gearbox oil change ([PWG 220](../entities/product/pwg-220.md)) | Gearbox | 5 years or on condition | SOP-GBX-010 Rev. B | 6 | 2 | Next planned changes from 2030 |
| 5 | MP-GBX-04 | Gearbox endoscope inspection | Gearbox | 24 months | LWS-MM-GBX-32 section 4.4 | 3 | 2 |  |
| 6 | MP-GBX-05 | Gearbox visual inspection and leak check | Gearbox | 6 months | LWS-MM-GBX-32 section 4.4 | 1 | 2 |  |
| 7 | MP-GBX-06 | Vibration trend review (condition monitoring) | Gearbox | monthly | LWS-MM-GBX-32 section 4.4 | 0.5 | 1 | Remote review by the Reliability Engineer |
| 8 | MP-GBX-07 | Oil cooler radiator cleaning and fan current check | Gearbox | 6 months | INC-2026-006 (D7) | 2 | 2 | Added in issue 2 (2026-07-01) |
| 9 | MP-GEN-01 | Generator brush inspection | Generator | 6 months | [WI-GEN-014](../entities/procedure/wi-gen-014.md) | 1.5 | 2 |  |
| 10 | MP-GEN-02 | Slip ring cleaning | Generator | 12 months | WI-GEN-014 | 2 | 2 |  |
| 11 | MP-PIT-01 | Pitch bearing bolt re-torque, 100 % of bolts, 1,450 Nm | Pitch | 12 months | [SB-LWS-2025-11](../entities/bulletin/sb-lws-2025-11.md) Rev. A | 8 | 2 |  |
| 12 | MP-BLD-01 | Blade drone inspection | Rotor | 12 months | [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md) | 1 | 2 | Contractor |
| 13 | MP-YAW-01 | Yaw brake pad inspection | Yaw | 12 months | [LT-32](../entities/product/lt-32.md) manual chapter 7 | 2 | 2 |  |
| 14 | MP-HYD-01 | Hydraulic accumulator pre-charge check | Hydraulics | 12 months | LT-32 manual chapter 9 | 1.5 | 2 |  |
| 15 | MP-HSE-01 | Rescue kit inspection | Safety | 6 months | [SOP-WAH-003](../entities/procedure/sop-wah-003.md) section 7 | 0.5 | 1 |  |
| 16 | MP-HSE-02 | Fall arrest rail and ladder inspection | Safety | 12 months | SOP-WAH-003 | 1 | 2 |  |

Agents can query this table as `t01` with the `query_table` tool.

### Plan 2026

The Plan 2026 sheet gives the per-turbine plan and status at 2026-07-01.[^c3]

[WTG-01](../entities/asset/wtg-01.md) has MP-GBX-07 planned for 2026-07 and 2027-01 with status planned at 2026-07-01.[^c23]

[WTG-02](../entities/asset/wtg-02.md) has MP-GBX-04 planned for 2026-07 with status done at 2026-07-01.[^c16]

[WTG-07](../entities/asset/wtg-07.md) has MP-GBX-02 planned for 2026-07 with status planned, and MP-PIT-01 planned for 2026-09 with status planned.[^c24][^c25]

[WTG-12](../entities/asset/wtg-12.md) has MP-GBX-02 planned for 2026-12, MP-PIT-01 planned for 2026-09, and MP-GBX-04 planned for 2026-10; each listed status is planned at 2026-07-01.[^c26][^c27][^c28]

**Table t02** · sheet "Plan 2026", rows 1–109

| Row | Turbine | Task ID | Planned months | Status at 2026-07-01 |
| --- | --- | --- | --- | --- |
| 2 | WTG-01 | MP-GBX-01 | 2026-06, 2026-12 | done |
| 3 | WTG-01 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 4 | WTG-01 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 5 | WTG-01 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 6 | WTG-01 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 7 | WTG-01 | MP-GBX-02 | 2026-01 | done |
| 8 | WTG-01 | MP-PIT-01 | 2026-05 | done |
| 9 | WTG-01 | MP-BLD-01 | 2026-05 | done |
| 10 | WTG-01 | MP-GBX-04 | 2027-04 | planned |
| 11 | WTG-02 | MP-GBX-01 | 2026-06, 2026-12 | done |
| 12 | WTG-02 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 13 | WTG-02 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 14 | WTG-02 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 15 | WTG-02 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 16 | WTG-02 | MP-GBX-02 | 2026-02 | done |
| 17 | WTG-02 | MP-PIT-01 | 2026-05 | done |
| 18 | WTG-02 | MP-BLD-01 | 2026-05 | done |
| 19 | WTG-02 | MP-GBX-04 | 2026-07 | done |
| 20 | [WTG-03](../entities/asset/wtg-03.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 21 | WTG-03 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 22 | WTG-03 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 23 | WTG-03 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 24 | WTG-03 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 25 | WTG-03 | MP-GBX-02 | 2026-03 | done |
| 26 | WTG-03 | MP-PIT-01 | 2026-05 | done |
| 27 | WTG-03 | MP-BLD-01 | 2026-05 | done |
| 28 | WTG-03 | MP-GBX-04 | 2027-04 | planned |
| 29 | [WTG-04](../entities/asset/wtg-04.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 30 | WTG-04 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 31 | WTG-04 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 32 | WTG-04 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 33 | WTG-04 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 34 | WTG-04 | MP-GBX-02 | 2026-04 | done |
| 35 | WTG-04 | MP-PIT-01 | 2026-05 | done |
| 36 | WTG-04 | MP-BLD-01 | 2026-05 | done |
| 37 | WTG-04 | MP-GBX-04 | 2026-10 | planned |
| 38 | [WTG-05](../entities/asset/wtg-05.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 39 | WTG-05 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 40 | WTG-05 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 41 | WTG-05 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 42 | WTG-05 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 43 | WTG-05 | MP-GBX-02 | 2026-05 | done |
| 44 | WTG-05 | MP-PIT-01 | 2026-05 | done |
| 45 | WTG-05 | MP-BLD-01 | 2026-05 | done |
| 46 | WTG-05 | MP-GBX-04 | 2027-04 | planned |
| 47 | [WTG-06](../entities/asset/wtg-06.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 48 | WTG-06 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 49 | WTG-06 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 50 | WTG-06 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 51 | WTG-06 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 52 | WTG-06 | MP-GBX-02 | 2026-06 | done |
| 53 | WTG-06 | MP-PIT-01 | 2026-05 | done |
| 54 | WTG-06 | MP-BLD-01 | 2026-05 | done |
| 55 | WTG-06 | MP-GBX-04 | 2026-10 | planned |
| 56 | WTG-07 | MP-GBX-01 | 2026-06, 2026-12 | done |
| 57 | WTG-07 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 58 | WTG-07 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 59 | WTG-07 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 60 | WTG-07 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 61 | WTG-07 | MP-GBX-02 | 2026-07 | planned |
| 62 | WTG-07 | MP-PIT-01 | 2026-09 | planned |
| 63 | WTG-07 | MP-BLD-01 | 2026-05 | done |
| 64 | WTG-07 | MP-GBX-04 | 2027-04 | planned |
| 65 | [WTG-08](../entities/asset/wtg-08.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 66 | WTG-08 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 67 | WTG-08 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 68 | WTG-08 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 69 | WTG-08 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 70 | WTG-08 | MP-GBX-02 | 2026-08 | planned |
| 71 | WTG-08 | MP-PIT-01 | 2026-09 | planned |
| 72 | WTG-08 | MP-BLD-01 | 2026-05 | done |
| 73 | WTG-08 | MP-GBX-04 | 2026-10 | planned |
| 74 | [WTG-09](../entities/asset/wtg-09.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 75 | WTG-09 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 76 | WTG-09 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 77 | WTG-09 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 78 | WTG-09 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 79 | WTG-09 | MP-GBX-02 | 2026-09 | planned |
| 80 | WTG-09 | MP-PIT-01 | 2026-09 | planned |
| 81 | WTG-09 | MP-BLD-01 | 2026-05 | done |
| 82 | WTG-09 | MP-GBX-04 | 2027-04 | planned |
| 83 | [WTG-10](../entities/asset/wtg-10.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 84 | WTG-10 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 85 | WTG-10 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 86 | WTG-10 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 87 | WTG-10 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 88 | WTG-10 | MP-GBX-02 | 2026-10 | planned |
| 89 | WTG-10 | MP-PIT-01 | 2026-09 | planned |
| 90 | WTG-10 | MP-BLD-01 | 2026-05 | done |
| 91 | WTG-10 | MP-GBX-04 | 2026-10 | planned |
| 92 | [WTG-11](../entities/asset/wtg-11.md) | MP-GBX-01 | 2026-06, 2026-12 | done |
| 93 | WTG-11 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 94 | WTG-11 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 95 | WTG-11 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 96 | WTG-11 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 97 | WTG-11 | MP-GBX-02 | 2026-11 | planned |
| 98 | WTG-11 | MP-PIT-01 | 2026-09 | planned |
| 99 | WTG-11 | MP-BLD-01 | 2026-05 | done |
| 100 | WTG-11 | MP-GBX-04 | 2027-04 | planned |
| 101 | WTG-12 | MP-GBX-01 | 2026-06, 2026-12 | done |
| 102 | WTG-12 | MP-GBX-05 | 2026-03, 2026-09 | done |
| 103 | WTG-12 | MP-GBX-07 | 2026-07, 2027-01 | planned |
| 104 | WTG-12 | MP-GEN-01 | 2026-04, 2026-10 | done |
| 105 | WTG-12 | MP-HSE-01 | 2026-02, 2026-08 | done |
| 106 | WTG-12 | MP-GBX-02 | 2026-12 | planned |
| 107 | WTG-12 | MP-PIT-01 | 2026-09 | planned |
| 108 | WTG-12 | MP-BLD-01 | 2026-05 | done |
| 109 | WTG-12 | MP-GBX-04 | 2026-10 | planned |

Agents can query this table as `t02` with the `query_table` tool.

### Oil sampling

The Oil sampling sheet records per-turbine last sample date, report, oil, Fe (ppm), PQ index, condition, and next sample due.[^c29]

[WTG-07](../entities/asset/wtg-07.md) is the only highlighted exception in the key facts: its row shows report TR-OA-2026-0614, oil [PWG 220](../entities/product/pwg-220.md), Fe 64, PQ index 112, condition ALERT, and next sample due 2026-07-10 with resampling within 30 days.[^c17]

[WTG-01](../entities/asset/wtg-01.md) through [WTG-06](../entities/asset/wtg-06.md) and [WTG-08](../entities/asset/wtg-08.md) through [WTG-12](../entities/asset/wtg-12.md) rows show condition NORMAL and next sample due 2026-12.[^c29][^c30][^c31][^c32][^c33][^c34][^c35][^c36][^c37][^c38][^c39]

**Table t03** · sheet "Oil sampling", rows 1–13

| Row | Turbine | Last sample | Report | Oil | Fe (ppm) | PQ index | Condition | Next sample due |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | WTG-01 | 2026-06-08 | TR-OA-2026-0603 | PWG 220 | 10 | 25 | NORMAL | 2026-12 |
| 3 | [WTG-02](../entities/asset/wtg-02.md) | 2026-06-08 | TR-OA-2026-0604 | PWG 220 | 27 | 22 | NORMAL | 2026-12 |
| 4 | [WTG-03](../entities/asset/wtg-03.md) | 2026-06-08 | TR-OA-2026-0605 | PWG 220 | 22 | 25 | NORMAL | 2026-12 |
| 5 | [WTG-04](../entities/asset/wtg-04.md) | 2026-06-09 | TR-OA-2026-0606 | PWG 220 | 27 | 22 | NORMAL | 2026-12 |
| 6 | [WTG-05](../entities/asset/wtg-05.md) | 2026-06-09 | TR-OA-2026-0607 | PWG 220 | 13 | 9 | NORMAL | 2026-12 |
| 7 | WTG-06 | 2026-06-09 | TR-OA-2026-0608 | PWG 220 | 24 | 12 | NORMAL | 2026-12 |
| 8 | WTG-07 | 2026-06-10 | TR-OA-2026-0614 | PWG 220 | 64 | 112 | ALERT | 2026-07-10 (resample within 30 days) |
| 9 | WTG-08 | 2026-06-10 | TR-OA-2026-0610 | PWG 220 | 27 | 17 | NORMAL | 2026-12 |
| 10 | [WTG-09](../entities/asset/wtg-09.md) | 2026-06-10 | TR-OA-2026-0611 | PWG 220 | 22 | 11 | NORMAL | 2026-12 |
| 11 | [WTG-10](../entities/asset/wtg-10.md) | 2026-06-11 | TR-OA-2026-0612 | PWG 220 | 14 | 26 | NORMAL | 2026-12 |
| 12 | [WTG-11](../entities/asset/wtg-11.md) | 2026-06-11 | TR-OA-2026-0613 | PWG 220 | 14 | 12 | NORMAL | 2026-12 |
| 13 | WTG-12 | 2026-06-11 | TR-OA-2026-0615 | PWG 220 | 25 | 26 | NORMAL | 2026-12 |

Agents can query this table as `t03` with the `query_table` tool.

### Revision log

Issue 1, dated 2025-12-15, issued Plan 2026 and updated the oil sampling schedule for [PWG 220](../entities/product/pwg-220.md) under MOC-2025-012 action 5.[^c18]

Issue 2, dated 2026-07-01, added MP-GBX-07 for all turbines after INC-2026-006 and brought the [WTG-02](../entities/asset/wtg-02.md) endoscope inspection forward to July.[^c4]

**Table t04** · sheet "Revision log", rows 1–3

| Row | Issue | Date | Change | Author |
| --- | --- | --- | --- | --- |
| 2 | 1 | 2025-12-15 | Plan 2026 issued; oil sampling schedule updated for PWG 220 (MOC-2025-012 action 5). | Dario Penwarden |
| 3 | 2 | 2026-07-01 | Task MP-GBX-07 added for all turbines after INC-2026-006; WTG-02 endoscope brought forward to July. | Dario Penwarden |

Agents can query this table as `t04` with the `query_table` tool.

### About

The About sheet identifies the document as Maintenance plan 2026, issue 2 of 2026-07-01, for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c1]

The owner is Dario Penwarden, O&M Supervisor, [Contoso Renewables](../entities/organisation/contoso-renewables.md).[^c2]

The document is marked fictional and not for operational use.[^c40]

**Table t05** · sheet "About", rows 1–5

| Row | FICTIONAL - NOT FOR OPERATIONAL USE |
| --- | --- |
| 2 | Maintenance plan 2026, issue 2 of 2026-07-01, Quellmoor Ridge Wind Farm. |
| 3 | Owner: Dario Penwarden, O&M Supervisor, Contoso Renewables. |
| 4 | Sheets: Tasks (task catalogue), Plan 2026 (per turbine), Oil sampling, Revision log. |
| 5 | FICTIONAL - NOT FOR OPERATIONAL USE |

Agents can query this table as `t05` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [hydraulic system](../entities/component/hydraulic-system.md), [oil cooler](../entities/component/oil-cooler.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [slip ring](../entities/component/slip-ring.md), [yaw system](../entities/component/yaw-system.md)
- Spare part: [FGT-P-11872](../entities/part/fgt-p-11872.md)
- Products: [Litware LT-32](../entities/product/lt-32.md), [Proseware PWG 220](../entities/product/pwg-220.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletin: [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Organisations: [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)
- Topics: [Blades, pitch bearings and main-component lifts](../topics/blades-and-rotor.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../topics/generator-and-electrical.md), [Safety, isolation and work at height](../topics/safety-and-access.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Blades, pitch bearings and main-component lifts](../topics/blades-and-rotor.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [Generator brushes and electrical systems](../topics/generator-and-electrical.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil filter element](../entities/component/oil-filter.md)
- [pitch bearing](../entities/component/pitch-bearing.md)
- [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)
- [WTG-01](../entities/asset/wtg-01.md)
- [WTG-02](../entities/asset/wtg-02.md)
- [WTG-03](../entities/asset/wtg-03.md)
- [WTG-04](../entities/asset/wtg-04.md)
- [WTG-05](../entities/asset/wtg-05.md)
- [WTG-06](../entities/asset/wtg-06.md)
- [WTG-07](../entities/asset/wtg-07.md)
- [WTG-08](../entities/asset/wtg-08.md)
- [WTG-09](../entities/asset/wtg-09.md)
- [WTG-10](../entities/asset/wtg-10.md)
- [WTG-11](../entities/asset/wtg-11.md)
- [WTG-12](../entities/asset/wtg-12.md)
- [yaw system](../entities/component/yaw-system.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "About", row 2](../evidence/src-aba30cb7207f/sheet-about-r0002-r0002.md) · table
[^c2]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "About", row 3](../evidence/src-aba30cb7207f/sheet-about-r0003-r0003.md) · table
[^c3]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "About", row 4](../evidence/src-aba30cb7207f/sheet-about-r0004-r0004.md) · table
[^c4]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Revision log", row 3](../evidence/src-aba30cb7207f/sheet-revision-log-r0003-r0003.md) · table
[^c5]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 2](../evidence/src-aba30cb7207f/sheet-tasks-r0002-r0002.md) · table
[^c6]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 3](../evidence/src-aba30cb7207f/sheet-tasks-r0003-r0003.md) · table
[^c7]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 4](../evidence/src-aba30cb7207f/sheet-tasks-r0004-r0004.md) · table
[^c8]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 7](../evidence/src-aba30cb7207f/sheet-tasks-r0007-r0007.md) · table
[^c9]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 8](../evidence/src-aba30cb7207f/sheet-tasks-r0008-r0008.md) · table
[^c10]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 9](../evidence/src-aba30cb7207f/sheet-tasks-r0009-r0009.md) · table
[^c11]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 10](../evidence/src-aba30cb7207f/sheet-tasks-r0010-r0010.md) · table
[^c12]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 11](../evidence/src-aba30cb7207f/sheet-tasks-r0011-r0011.md) · table
[^c13]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 12](../evidence/src-aba30cb7207f/sheet-tasks-r0012-r0012.md) · table
[^c14]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 15](../evidence/src-aba30cb7207f/sheet-tasks-r0015-r0015.md) · table
[^c15]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 16](../evidence/src-aba30cb7207f/sheet-tasks-r0016-r0016.md) · table
[^c16]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 19](../evidence/src-aba30cb7207f/sheet-plan-2026-r0019-r0019.md) · table
[^c17]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 8](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0008-r0008.md) · table
[^c18]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Revision log", row 2](../evidence/src-aba30cb7207f/sheet-revision-log-r0002-r0002.md) · table
[^c19]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 5](../evidence/src-aba30cb7207f/sheet-tasks-r0005-r0005.md) · table
[^c20]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 6](../evidence/src-aba30cb7207f/sheet-tasks-r0006-r0006.md) · table
[^c21]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 13](../evidence/src-aba30cb7207f/sheet-tasks-r0013-r0013.md) · table
[^c22]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 14](../evidence/src-aba30cb7207f/sheet-tasks-r0014-r0014.md) · table
[^c23]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 4](../evidence/src-aba30cb7207f/sheet-plan-2026-r0004-r0004.md) · table
[^c24]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 61](../evidence/src-aba30cb7207f/sheet-plan-2026-r0061-r0061.md) · table
[^c25]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 62](../evidence/src-aba30cb7207f/sheet-plan-2026-r0062-r0062.md) · table
[^c26]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 106](../evidence/src-aba30cb7207f/sheet-plan-2026-r0106-r0106.md) · table
[^c27]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 107](../evidence/src-aba30cb7207f/sheet-plan-2026-r0107-r0107.md) · table
[^c28]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 109](../evidence/src-aba30cb7207f/sheet-plan-2026-r0109-r0109.md) · table
[^c29]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 2](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0002-r0002.md) · table
[^c30]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 3](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0003-r0003.md) · table
[^c31]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 4](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0004-r0004.md) · table
[^c32]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 5](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0005-r0005.md) · table
[^c33]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 6](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0006-r0006.md) · table
[^c34]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 7](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0007-r0007.md) · table
[^c35]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 9](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0009-r0009.md) · table
[^c36]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 10](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0010-r0010.md) · table
[^c37]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 11](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0011-r0011.md) · table
[^c38]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 12](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0012-r0012.md) · table
[^c39]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 13](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0013-r0013.md) · table
[^c40]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "About", row 5](../evidence/src-aba30cb7207f/sheet-about-r0005-r0005.md) · table
