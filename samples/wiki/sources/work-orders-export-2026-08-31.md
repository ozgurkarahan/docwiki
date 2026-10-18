---
id: src-9fd435ef5956
type: source
title: Work Orders Export through 2026-08-31
summary: This CSV export lists wind turbine work orders with creation dates, turbine identifiers, work types, titles, statuses, priorities, parts, assignments, planned and completed dates, references, and remarks. It covers modification, preventive maintenance, and corrective maintenance work from 2025-08-27 through 2026-08-24.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- records-and-data
- work-order-export
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-9fd435ef5956
source_path: full/records/work-orders-export-2026-08-31.csv
source_hash: sha256:d4a78fc8c32706338d09eabe574859b975f21475dd800730a8ee3c890b612529
media_type: text/csv
doc_type: work-order-export
category: records-and-data
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- alarm-code:a3210
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
- bulletin:sb-lws-2025-07
- bulletin:sb-lws-2025-11
- component:cooler-fan-motor
- component:gearbox
- component:generator
- component:generator-brushes
- component:hss-bearing
- component:hydraulic-system
- component:oil-cooler
- component:oil-filter
- component:pitch-bearing
- component:pitch-bearing-bolts
- component:rescue-kit
- component:rotor-blade
- part:awi-10442
- part:awi-31007
- part:fgt-p-11872
- part:fgt-p-22328
- part:lws-p-30418
- part:lws-p-51207
- part:pws-220-d208
- part:pws-320-d208
- procedure:wi-gen-014
- product:pwg-220
- product:pwg-320
topics:
- topic:blades-and-rotor
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:generator-and-electrical
- topic:safety-and-access
- topic:spare-parts-and-supply
authority: 5
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    deterministic-table: 94
---

# Work Orders Export through 2026-08-31

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This CSV export lists wind turbine work orders with creation dates, turbine identifiers, work types, titles, statuses, priorities, parts, assignments, planned and completed dates, references, and remarks. It covers modification, preventive maintenance, and corrective maintenance work from 2025-08-27 through 2026-08-24.

## Key facts

- The export records a completed high-priority modification campaign for [gearbox](../entities/component/gearbox.md) oil conversion from [PWG 320](../entities/product/pwg-320.md) to [PWG 220](../entities/product/pwg-220.md) with a 60 L flush for [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) under reference MOC-2025-012; each row lists part [PWS-220-D208](../entities/part/pws-220-d208.md) with quantity 3.[^c1][^c2][^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11][^c12]
- The [WTG-09](../entities/asset/wtg-09.md) gearbox oil conversion work order WO-25-0309 was deferred because the access road was closed by snow on 2025-11-24 and was completed on 2026-01-20.[^c9]
- WO-26-0187 for [WTG-10](../entities/asset/wtg-10.md) replaced the generator-side [HSS bearing](../entities/component/hss-bearing.md), was completed as high-priority corrective maintenance, used part [FGT-P-22328](../entities/part/fgt-p-22328.md) quantity 1, and notes that the last spare bearing was used.[^c13]
- WO-26-0203 installed tool tether anchor points at the [WTG-11](../entities/asset/wtg-11.md) yaw deck hatch, was completed as high-priority corrective maintenance, and used part [AWI-31007](../entities/part/awi-31007.md) quantity 1 under reference INC-2026-003.[^c14]
- [Pitch bearing](../entities/component/pitch-bearing.md) bolt re-torque work for WTG-01 through [WTG-06](../entities/asset/wtg-06.md) was completed with a stated torque of 1,450 Nm and coverage of 100 % of bolts, referenced to [SB-LWS-2025-11](../entities/bulletin/sb-lws-2025-11.md) Rev. A.[^c15][^c16][^c17][^c18][^c19][^c20]
- Gearbox oil sampling work orders WO-26-0341 through WO-26-0352 cover WTG-01 through WTG-12 and are all marked Completed.[^c21][^c22][^c23][^c24][^c25][^c26][^c27][^c28][^c29][^c30][^c31][^c32]
- WO-26-0355 for [WTG-04](../entities/asset/wtg-04.md) is a planned high-priority corrective-maintenance work order to replace [rotor blade](../entities/component/rotor-blade.md) B for a trailing-edge crack, with planned date 2026-09-08 and references WBS-2026-031 and LP-2026-009.[^c33]
- For [WTG-07](../entities/asset/wtg-07.md) under INC-2026-006, WO-26-0398 replaced the [oil cooler fan motor](../entities/component/cooler-fan-motor.md) with part [LWS-P-30418](../entities/part/lws-p-30418.md) quantity 1, and WO-26-0399 cleaned the [oil cooler](../entities/component/oil-cooler.md) radiator with remarks that fins were about 40 % blocked by insects and pollen.[^c34][^c35]
- WO-26-0412 for WTG-07 is a high-priority corrective-maintenance work order to replace the generator-side HSS bearing, is waiting for parts, lists part FGT-P-22328 quantity 1, and remarks that vibration is above the alarm level of 4.5 mm/s.[^c36]
- WO-26-0436 for WTG-09 replaced [generator brushes](../entities/component/generator-brushes.md) for [A3210](../entities/alarm-code/a3210.md), was completed under [WI-GEN-014](../entities/procedure/wi-gen-014.md), used part [LWS-P-51207](../entities/part/lws-p-51207.md) quantity 1, and notes the shortest brush was 16 mm.[^c37]
- WO-26-0439 for [WTG-02](../entities/asset/wtg-02.md) is waiting for parts for a generator-side HSS bearing replacement after spalling was found at endoscopy on 2026-07-23, and it lists part FGT-P-22328 quantity 1.[^c38]
- Near the end of the export, WO-26-0444 for [WTG-05](../entities/asset/wtg-05.md) is in progress for [rescue kit](../entities/component/rescue-kit.md) inspection, WO-26-0450 for WTG-11 is waiting for parts for a leaking hydraulic hose in the yaw brake circuit with part [AWI-10442](../entities/part/awi-10442.md) quantity 1, and WO-26-0457 for [WTG-03](../entities/asset/wtg-03.md) is open for yaw brake pad inspection.[^c39][^c40][^c41]
- Pitch bearing bolt re-torque work for WTG-07 through WTG-12 is planned for September 2026, with each title stating 1,450 Nm and 100 % of bolts and reference SB-LWS-2025-11 Rev. A.[^c42][^c43][^c44][^c45][^c46][^c47]

## Contents

### Export structure and early modification work

The source is a work-order table with fields for work order number, created date, turbine, type, title, status, priority, part number, part quantity, assignee, planned date, completed date, reference, and remarks.[^c1]

The first twelve data rows are high-priority MOD work orders for [gearbox](../entities/component/gearbox.md) oil conversion from [PWG 320](../entities/product/pwg-320.md) to [PWG 220](../entities/product/pwg-220.md), including a 60 L flush, using part [PWS-220-D208](../entities/part/pws-220-d208.md) with quantity 3 and reference MOC-2025-012; all twelve are marked Completed.[^c1][^c2][^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11][^c12]

The [WTG-09](../entities/asset/wtg-09.md) conversion row records a deferral because the access road was closed by snow on 2025-11-24, with completion on 2026-01-20.[^c9]

**Table t01** · rows 1–95

| Row | wo_number | created | turbine | type | title | status | priority | part_number | part_qty | assigned_to | planned_date | completed_date | reference | remarks |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | WO-25-0301 | 2025-08-27 | [WTG-01](../entities/asset/wtg-01.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush ([SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md)) | Completed | High | PWS-220-D208 | 3 | Callum Rydings | 2025-09-03 | 2025-09-03 | MOC-2025-012 |  |
| 3 | WO-25-0302 | 2025-08-27 | [WTG-02](../entities/asset/wtg-02.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Élise Ternaux | 2025-09-10 | 2025-09-10 | MOC-2025-012 |  |
| 4 | WO-25-0303 | 2025-08-27 | [WTG-03](../entities/asset/wtg-03.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Callum Rydings | 2025-09-17 | 2025-09-17 | MOC-2025-012 |  |
| 5 | WO-25-0304 | 2025-08-27 | [WTG-04](../entities/asset/wtg-04.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Élise Ternaux | 2025-09-24 | 2025-09-24 | MOC-2025-012 |  |
| 6 | WO-25-0305 | 2025-08-27 | [WTG-05](../entities/asset/wtg-05.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Callum Rydings | 2025-10-01 | 2025-10-01 | MOC-2025-012 |  |
| 7 | WO-25-0306 | 2025-08-27 | [WTG-06](../entities/asset/wtg-06.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Élise Ternaux | 2025-10-08 | 2025-10-08 | MOC-2025-012 |  |
| 8 | WO-25-0307 | 2025-08-27 | [WTG-07](../entities/asset/wtg-07.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Callum Rydings | 2025-10-15 | 2025-10-15 | MOC-2025-012 |  |
| 9 | WO-25-0308 | 2025-08-27 | [WTG-08](../entities/asset/wtg-08.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Élise Ternaux | 2025-10-22 | 2025-10-22 | MOC-2025-012 |  |
| 10 | WO-25-0309 | 2025-08-27 | WTG-09 | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Callum Rydings | 2025-11-24 | 2026-01-20 | MOC-2025-012 | Deferred: access road closed by snow on 2025-11-24, completed 2026-01-20 |
| 11 | WO-25-0310 | 2025-08-27 | [WTG-10](../entities/asset/wtg-10.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Élise Ternaux | 2025-11-05 | 2025-11-05 | MOC-2025-012 |  |
| 12 | WO-25-0311 | 2025-08-27 | [WTG-11](../entities/asset/wtg-11.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Callum Rydings | 2025-11-12 | 2025-11-12 | MOC-2025-012 |  |
| 13 | WO-25-0312 | 2025-08-27 | [WTG-12](../entities/asset/wtg-12.md) | MOD | Gearbox oil conversion PWG 320 to PWG 220 incl. 60 L flush (SB-LWS-2025-07) | Completed | High | PWS-220-D208 | 3 | Élise Ternaux | 2025-11-19 | 2025-11-19 | MOC-2025-012 |  |
| 14 | WO-25-0316 | 2025-09-10 | WTG-03 | PM | [Rescue kit](../entities/component/rescue-kit.md) inspection (MP-HSE-01) | Completed | Low |  |  | Callum Rydings | 2025-09-10 | 2025-09-10 | MP-HSE-01 |  |
| 15 | WO-25-0318 | 2025-09-11 | WTG-07 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Élise Ternaux | 2025-09-11 | 2025-09-11 | MP-YAW-01 |  |
| 16 | WO-25-0320 | 2025-09-15 | WTG-02 | PM | [Generator](../entities/component/generator.md) brush inspection (MP-GEN-01) | Completed | Low |  |  | Callum Rydings | 2025-09-15 | 2025-09-15 | MP-GEN-01 |  |
| 17 | WO-25-0324 | 2025-09-20 | WTG-02 | PM | Gearbox [oil filter element](../entities/component/oil-filter.md) replacement (MP-GBX-02) | Completed | Low | [FGT-P-11872](../entities/part/fgt-p-11872.md) | 1 | Callum Rydings | 2025-09-20 | 2025-09-20 | MP-GBX-02 |  |
| 18 | WO-25-0325 | 2025-10-03 | WTG-10 | PM | Gearbox oil filter element replacement (MP-GBX-02) | Completed | Low | FGT-P-11872 | 1 | Élise Ternaux | 2025-10-03 | 2025-10-03 | MP-GBX-02 |  |
| 19 | WO-25-0329 | 2025-10-08 | WTG-07 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Callum Rydings | 2025-10-08 | 2025-10-08 | MP-GEN-01 |  |
| 20 | WO-25-0333 | 2025-10-09 | WTG-06 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Élise Ternaux | 2025-10-09 | 2025-10-09 | MP-HSE-01 |  |
| 21 | WO-25-0337 | 2025-10-25 | WTG-10 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Élise Ternaux | 2025-10-25 | 2025-10-25 | MP-YAW-01 |  |
| 22 | WO-25-0338 | 2025-11-04 | WTG-03 | PM | Gearbox oil filter element replacement (MP-GBX-02) | Completed | Low | FGT-P-11872 | 1 | Élise Ternaux | 2025-11-04 | 2025-11-04 | MP-GBX-02 |  |
| 23 | WO-25-0342 | 2025-11-14 | WTG-02 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Élise Ternaux | 2025-11-14 | 2025-11-14 | MP-YAW-01 |  |
| 24 | WO-25-0344 | 2025-11-18 | WTG-07 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Élise Ternaux | 2025-11-18 | 2025-11-18 | MP-HSE-01 |  |
| 25 | WO-25-0346 | 2025-11-24 | WTG-05 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Callum Rydings | 2025-11-24 | 2025-11-24 | MP-GEN-01 |  |
| 26 | WO-25-0349 | 2025-12-13 | WTG-06 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Callum Rydings | 2025-12-13 | 2025-12-13 | MP-YAW-01 |  |
| 27 | WO-25-0352 | 2025-12-17 | WTG-10 | PM | Gearbox oil filter element replacement (MP-GBX-02) | Completed | Low | FGT-P-11872 | 1 | Callum Rydings | 2025-12-17 | 2025-12-17 | MP-GBX-02 |  |
| 28 | WO-25-0354 | 2025-12-18 | WTG-12 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Callum Rydings | 2025-12-18 | 2025-12-18 | MP-GEN-01 |  |
| 29 | WO-25-0356 | 2025-12-19 | WTG-03 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Callum Rydings | 2025-12-19 | 2025-12-19 | MP-HSE-01 |  |
| 30 | WO-26-0004 | 2026-01-03 | WTG-01 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Callum Rydings | 2026-01-03 | 2026-01-03 | MP-YAW-01 |  |
| 31 | WO-26-0007 | 2026-01-13 | WTG-07 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Élise Ternaux | 2026-01-13 | 2026-01-13 | MP-HSE-01 |  |
| 32 | WO-26-0011 | 2026-01-24 | WTG-11 | PM | Gearbox oil filter element replacement (MP-GBX-02) | Completed | Low | FGT-P-11872 | 1 | Élise Ternaux | 2026-01-24 | 2026-01-24 | MP-GBX-02 |  |
| 33 | WO-26-0013 | 2026-01-24 | WTG-11 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Élise Ternaux | 2026-01-24 | 2026-01-24 | MP-GEN-01 |  |
| 34 | WO-26-0016 | 2026-01-24 | WTG-02 | PM | Gearbox visual inspection and leak check (MP-GBX-05) | Completed | Low |  |  | Callum Rydings | 2026-01-24 | 2026-01-24 | MP-GBX-05 |  |
| 35 | WO-26-0020 | 2026-02-11 | WTG-07 | PM | Gearbox visual inspection and leak check (MP-GBX-05) | Completed | Low |  |  | Élise Ternaux | 2026-02-11 | 2026-02-11 | MP-GBX-05 |  |
| 36 | WO-26-0024 | 2026-02-15 | WTG-02 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Élise Ternaux | 2026-02-15 | 2026-02-15 | MP-GEN-01 |  |
| 37 | WO-26-0026 | 2026-02-17 | WTG-01 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Callum Rydings | 2026-02-17 | 2026-02-17 | MP-YAW-01 |  |
| 38 | WO-26-0187 | 2026-02-20 | WTG-10 | CM | Replace [HSS bearing](../entities/component/hss-bearing.md), generator side | Completed | High | [FGT-P-22328](../entities/part/fgt-p-22328.md) | 1 | Callum Rydings | 2026-03-11 | 2026-03-12 | CMS alarm 2026-02-20 | Last spare bearing used |
| 39 | WO-26-0191 | 2026-02-21 | WTG-03 | PM | Hydraulic accumulator pre-charge check (MP-HYD-01) | Completed | Low |  |  | Callum Rydings | 2026-02-21 | 2026-02-21 | MP-HYD-01 |  |
| 40 | WO-26-0195 | 2026-02-24 | WTG-08 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Élise Ternaux | 2026-02-24 | 2026-02-24 | MP-HSE-01 |  |
| 41 | WO-26-0198 | 2026-03-05 | WTG-12 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Callum Rydings | 2026-03-05 | 2026-03-05 | MP-YAW-01 |  |
| 42 | WO-26-0202 | 2026-03-08 | WTG-06 | PM | Hydraulic accumulator pre-charge check (MP-HYD-01) | Completed | Low |  |  | Callum Rydings | 2026-03-08 | 2026-03-08 | MP-HYD-01 |  |
| 43 | WO-26-0203 | 2026-03-26 | WTG-11 | CM | Install tool tether anchor points at yaw deck hatch | Completed | High | [AWI-31007](../entities/part/awi-31007.md) | 1 | Élise Ternaux | 2026-04-02 | 2026-04-02 | INC-2026-003 |  |
| 44 | WO-26-0207 | 2026-04-02 | WTG-07 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Callum Rydings | 2026-04-02 | 2026-04-02 | MP-HSE-01 |  |
| 45 | WO-26-0301 | 2026-04-20 | WTG-01 | PM | [Pitch bearing](../entities/component/pitch-bearing.md) bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Completed | Medium |  |  | Callum Rydings | 2026-05-04 | 2026-05-04 | [SB-LWS-2025-11](../entities/bulletin/sb-lws-2025-11.md) Rev. A |  |
| 46 | WO-26-0302 | 2026-04-20 | WTG-02 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Completed | Medium |  |  | Élise Ternaux | 2026-05-06 | 2026-05-06 | SB-LWS-2025-11 Rev. A |  |
| 47 | WO-26-0303 | 2026-04-20 | WTG-03 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Completed | Medium |  |  | Callum Rydings | 2026-05-08 | 2026-05-08 | SB-LWS-2025-11 Rev. A |  |
| 48 | WO-26-0304 | 2026-04-20 | WTG-04 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Completed | Medium |  |  | Élise Ternaux | 2026-05-10 | 2026-05-10 | SB-LWS-2025-11 Rev. A |  |
| 49 | WO-26-0305 | 2026-04-20 | WTG-05 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Completed | Medium |  |  | Callum Rydings | 2026-05-12 | 2026-05-12 | SB-LWS-2025-11 Rev. A |  |
| 50 | WO-26-0306 | 2026-04-20 | WTG-06 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Completed | Medium |  |  | Élise Ternaux | 2026-05-14 | 2026-05-14 | SB-LWS-2025-11 Rev. A |  |
| 51 | WO-26-0309 | 2026-04-21 | WTG-08 | PM | Hydraulic accumulator pre-charge check (MP-HYD-01) | Completed | Low |  |  | Élise Ternaux | 2026-04-21 | 2026-04-21 | MP-HYD-01 |  |
| 52 | WO-26-0310 | 2026-04-24 | WTG-09 | PM | Gearbox oil filter element replacement (MP-GBX-02) | Completed | Low | FGT-P-11872 | 1 | Élise Ternaux | 2026-04-24 | 2026-04-24 | MP-GBX-02 |  |
| 53 | WO-26-0312 | 2026-05-11 | WTG-10 | PM | Gearbox visual inspection and leak check (MP-GBX-05) | Completed | Low |  |  | Élise Ternaux | 2026-05-11 | 2026-05-11 | MP-GBX-05 |  |
| 54 | WO-26-0313 | 2026-05-12 | WTG-03 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Élise Ternaux | 2026-05-12 | 2026-05-12 | MP-GEN-01 |  |
| 55 | WO-26-0317 | 2026-05-26 | WTG-09 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Élise Ternaux | 2026-05-26 | 2026-05-26 | MP-YAW-01 |  |
| 56 | WO-26-0341 | 2026-05-28 | WTG-01 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-08 | 2026-06-08 | MP-GBX-01 |  |
| 57 | WO-26-0342 | 2026-05-28 | WTG-02 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-08 | 2026-06-08 | MP-GBX-01 |  |
| 58 | WO-26-0343 | 2026-05-28 | WTG-03 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-08 | 2026-06-08 | MP-GBX-01 |  |
| 59 | WO-26-0344 | 2026-05-28 | WTG-04 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-09 | 2026-06-09 | MP-GBX-01 |  |
| 60 | WO-26-0345 | 2026-05-28 | WTG-05 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-09 | 2026-06-09 | MP-GBX-01 |  |
| 61 | WO-26-0346 | 2026-05-28 | WTG-06 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-09 | 2026-06-09 | MP-GBX-01 |  |
| 62 | WO-26-0347 | 2026-05-28 | WTG-07 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-10 | 2026-06-10 | MP-GBX-01 |  |
| 63 | WO-26-0348 | 2026-05-28 | WTG-08 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-10 | 2026-06-10 | MP-GBX-01 |  |
| 64 | WO-26-0349 | 2026-05-28 | WTG-09 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-10 | 2026-06-10 | MP-GBX-01 |  |
| 65 | WO-26-0350 | 2026-05-28 | WTG-10 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-11 | 2026-06-11 | MP-GBX-01 |  |
| 66 | WO-26-0351 | 2026-05-28 | WTG-11 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-11 | 2026-06-11 | MP-GBX-01 |  |
| 67 | WO-26-0352 | 2026-05-28 | WTG-12 | PM | Gearbox oil sampling (MP-GBX-01) | Completed | Low |  |  | Callum Rydings | 2026-06-11 | 2026-06-11 | MP-GBX-01 |  |
| 68 | WO-26-0355 | 2026-06-05 | WTG-04 | CM | Replace [rotor blade](../entities/component/rotor-blade.md) B (trailing-edge crack) | Planned | High |  |  | Dario Penwarden | 2026-09-08 |  | WBS-2026-031, LP-2026-009 |  |
| 69 | WO-26-0357 | 2026-06-11 | WTG-06 | PM | Yaw brake pad inspection (MP-YAW-01) | Completed | Low |  |  | Callum Rydings | 2026-06-11 | 2026-06-11 | MP-YAW-01 |  |
| 70 | WO-26-0398 | 2026-06-22 | WTG-07 | CM | Replace [oil cooler fan motor](../entities/component/cooler-fan-motor.md) | Completed | High | [LWS-P-30418](../entities/part/lws-p-30418.md) | 1 | Callum Rydings | 2026-06-24 | 2026-06-24 | INC-2026-006 |  |
| 71 | WO-26-0399 | 2026-06-22 | WTG-07 | CM | Clean [oil cooler](../entities/component/oil-cooler.md) radiator | Completed | High |  |  | Élise Ternaux | 2026-06-24 | 2026-06-24 | INC-2026-006 | Fins about 40 % blocked by insects and pollen |
| 72 | WO-26-0403 | 2026-06-22 | WTG-05 | PM | Gearbox visual inspection and leak check (MP-GBX-05) | Completed | Low |  |  | Élise Ternaux | 2026-06-22 | 2026-06-22 | MP-GBX-05 |  |
| 73 | WO-26-0412 | 2026-06-26 | WTG-07 | CM | Replace HSS bearing, generator side | Waiting for parts | High | FGT-P-22328 | 1 | Callum Rydings |  |  | INC-2026-006 | Vibration above alarm level 4.5 mm/s |
| 74 | WO-26-0413 | 2026-06-26 | WTG-05 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Élise Ternaux | 2026-06-26 | 2026-06-26 | MP-GEN-01 |  |
| 75 | WO-26-0430 | 2026-07-06 | WTG-01 | PM | Oil cooler radiator cleaning and fan current check (MP-GBX-07) | Completed | Medium |  |  | Élise Ternaux | 2026-07-07 | 2026-07-07 | MP-GBX-07 |  |
| 76 | WO-26-0431 | 2026-07-06 | WTG-02 | PM | Oil cooler radiator cleaning and fan current check (MP-GBX-07) | Completed | Medium |  |  | Élise Ternaux | 2026-07-08 | 2026-07-08 | MP-GBX-07 |  |
| 77 | WO-26-0434 | 2026-07-06 | WTG-11 | PM | Gearbox oil filter element replacement (MP-GBX-02) | Completed | Low | FGT-P-11872 | 1 | Élise Ternaux | 2026-07-06 | 2026-07-06 | MP-GBX-02 |  |
| 78 | WO-26-0436 | 2026-07-16 | WTG-09 | CM | Replace [generator brushes](../entities/component/generator-brushes.md) ([A3210](../entities/alarm-code/a3210.md)) | Completed | Medium | [LWS-P-51207](../entities/part/lws-p-51207.md) | 1 | Élise Ternaux | 2026-07-18 | 2026-07-18 | [WI-GEN-014](../entities/procedure/wi-gen-014.md) | Shortest brush 16 mm |
| 79 | WO-26-0438 | 2026-07-22 | WTG-02 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Élise Ternaux | 2026-07-22 | 2026-07-22 | MP-HSE-01 |  |
| 80 | WO-26-0439 | 2026-07-24 | WTG-02 | CM | Replace HSS bearing, generator side (spalling found at endoscopy 2026-07-23) | Waiting for parts | High | FGT-P-22328 | 1 | Callum Rydings |  |  | Endoscope inspection 2026-07-23 |  |
| 81 | WO-26-0443 | 2026-07-25 | WTG-05 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Callum Rydings | 2026-07-25 | 2026-07-25 | MP-GEN-01 |  |
| 82 | WO-26-0444 | 2026-07-27 | WTG-05 | PM | Rescue kit inspection (MP-HSE-01) | In progress | Medium |  |  | Callum Rydings | 2026-08-03 |  | MP-HSE-01 |  |
| 83 | WO-26-0450 | 2026-07-30 | WTG-11 | CM | Replace leaking hydraulic hose, yaw brake circuit | Waiting for parts | Medium | [AWI-10442](../entities/part/awi-10442.md) | 1 | Élise Ternaux |  |  | Shift handover 2026-07-29 | Hose not stocked, ordered from distributor |
| 84 | WO-26-0452 | 2026-08-03 | WTG-10 | PM | Gearbox oil filter element replacement (MP-GBX-02) | Completed | Low | FGT-P-11872 | 1 | Élise Ternaux | 2026-08-03 | 2026-08-03 | MP-GBX-02 |  |
| 85 | WO-26-0454 | 2026-08-06 | WTG-06 | PM | Hydraulic accumulator pre-charge check (MP-HYD-01) | Completed | Low |  |  | Callum Rydings | 2026-08-06 | 2026-08-06 | MP-HYD-01 |  |
| 86 | WO-26-0457 | 2026-08-08 | WTG-03 | PM | Yaw brake pad inspection (MP-YAW-01) | Open | Low |  |  | Élise Ternaux | 2026-08-08 |  | MP-YAW-01 |  |
| 87 | WO-26-0461 | 2026-08-10 | WTG-09 | PM | Generator brush inspection (MP-GEN-01) | Completed | Low |  |  | Élise Ternaux | 2026-08-10 | 2026-08-10 | MP-GEN-01 |  |
| 88 | WO-26-0465 | 2026-08-14 | WTG-06 | PM | Gearbox visual inspection and leak check (MP-GBX-05) | Completed | Low |  |  | Élise Ternaux | 2026-08-14 | 2026-08-14 | MP-GBX-05 |  |
| 89 | WO-26-0467 | 2026-08-21 | WTG-01 | PM | Rescue kit inspection (MP-HSE-01) | Completed | Low |  |  | Callum Rydings | 2026-08-21 | 2026-08-21 | MP-HSE-01 |  |
| 90 | WO-26-0471 | 2026-08-24 | WTG-07 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Planned | Medium |  |  | Callum Rydings | 2026-09-07 |  | SB-LWS-2025-11 Rev. A |  |
| 91 | WO-26-0472 | 2026-08-24 | WTG-08 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Planned | Medium |  |  | Élise Ternaux | 2026-09-09 |  | SB-LWS-2025-11 Rev. A |  |
| 92 | WO-26-0473 | 2026-08-24 | WTG-09 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Planned | Medium |  |  | Callum Rydings | 2026-09-11 |  | SB-LWS-2025-11 Rev. A |  |
| 93 | WO-26-0474 | 2026-08-24 | WTG-10 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Planned | Medium |  |  | Élise Ternaux | 2026-09-13 |  | SB-LWS-2025-11 Rev. A |  |
| 94 | WO-26-0475 | 2026-08-24 | WTG-11 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Planned | Medium |  |  | Callum Rydings | 2026-09-15 |  | SB-LWS-2025-11 Rev. A |  |
| 95 | WO-26-0476 | 2026-08-24 | WTG-12 | PM | Pitch bearing bolt re-torque 1,450 Nm, 100 % of bolts (MP-PIT-01) | Planned | Medium |  |  | Élise Ternaux | 2026-09-17 |  | SB-LWS-2025-11 Rev. A |  |

Agents can query this table as `t01` with the `query_table` tool.

### Preventive maintenance work recorded in the export

Preventive-maintenance rows include [rescue kit](../entities/component/rescue-kit.md) inspection, yaw brake pad inspection, [generator](../entities/component/generator.md) brush inspection, [gearbox](../entities/component/gearbox.md) [oil filter element](../entities/component/oil-filter.md) replacement, gearbox visual inspection and leak check, hydraulic accumulator pre-charge check, gearbox oil sampling, [oil cooler](../entities/component/oil-cooler.md) radiator cleaning and fan current check, and [pitch bearing](../entities/component/pitch-bearing.md) bolt re-torque.[^c48][^c49][^c50][^c51][^c52][^c53][^c21][^c54][^c15]

Gearbox oil sampling was completed for [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) in work orders WO-26-0341 through WO-26-0352.[^c21][^c22][^c23][^c24][^c25][^c26][^c27][^c28][^c29][^c30][^c31][^c32]

Pitch bearing bolt re-torque work for WTG-01 through [WTG-06](../entities/asset/wtg-06.md) is completed and references [SB-LWS-2025-11](../entities/bulletin/sb-lws-2025-11.md) Rev. A; the titles state 1,450 Nm and 100 % of bolts.[^c15][^c16][^c17][^c18][^c19][^c20]

Pitch bearing bolt re-torque work for [WTG-07](../entities/asset/wtg-07.md) through WTG-12 is planned and also references SB-LWS-2025-11 Rev. A.[^c42][^c43][^c44][^c45][^c46][^c47]

See table t01 above.

### Corrective maintenance and notable remarks

[WTG-10](../entities/asset/wtg-10.md) work order WO-26-0187 replaced the generator-side [HSS bearing](../entities/component/hss-bearing.md), was completed, used part [FGT-P-22328](../entities/part/fgt-p-22328.md) quantity 1, and remarks that the last spare bearing was used.[^c13]

[WTG-11](../entities/asset/wtg-11.md) work order WO-26-0203 installed tool tether anchor points at the yaw deck hatch, was completed, and used part [AWI-31007](../entities/part/awi-31007.md) quantity 1 under reference INC-2026-003.[^c14]

[WTG-04](../entities/asset/wtg-04.md) work order WO-26-0355 is planned high-priority corrective maintenance to replace [rotor blade](../entities/component/rotor-blade.md) B for a trailing-edge crack, with planned date 2026-09-08 and references WBS-2026-031 and LP-2026-009.[^c33]

[WTG-07](../entities/asset/wtg-07.md) work orders WO-26-0398 and WO-26-0399 under INC-2026-006 completed [oil cooler fan motor](../entities/component/cooler-fan-motor.md) replacement and [oil cooler](../entities/component/oil-cooler.md) radiator cleaning; the cleaning row remarks that fins were about 40 % blocked by insects and pollen.[^c34][^c35]

[WTG-09](../entities/asset/wtg-09.md) work order WO-26-0436 completed [generator brush replacement](../entities/procedure/wi-gen-014.md) for [A3210](../entities/alarm-code/a3210.md) under WI-GEN-014, used part [LWS-P-51207](../entities/part/lws-p-51207.md) quantity 1, and remarks that the shortest brush was 16 mm.[^c37]

See table t01 above.

### Open, waiting, in-progress, and planned items near export end

[WTG-07](../entities/asset/wtg-07.md) work order WO-26-0412 is waiting for parts for generator-side [HSS bearing](../entities/component/hss-bearing.md) replacement, lists part [FGT-P-22328](../entities/part/fgt-p-22328.md) quantity 1, and remarks that vibration is above alarm level 4.5 mm/s.[^c36]

[WTG-02](../entities/asset/wtg-02.md) work order WO-26-0439 is waiting for parts for generator-side HSS bearing replacement after spalling was found at endoscopy on 2026-07-23, and lists part FGT-P-22328 quantity 1.[^c38]

[WTG-05](../entities/asset/wtg-05.md) work order WO-26-0444 is in progress for [rescue kit](../entities/component/rescue-kit.md) inspection.[^c39]

[WTG-11](../entities/asset/wtg-11.md) work order WO-26-0450 is waiting for parts to replace a leaking hydraulic hose in the yaw brake circuit, lists part [AWI-10442](../entities/part/awi-10442.md) quantity 1, and remarks that the hose was not stocked and was ordered from a distributor.[^c40]

[WTG-03](../entities/asset/wtg-03.md) work order WO-26-0457 is open for yaw brake pad inspection.[^c41]

See table t01 above.

## Figures

No figures were extracted from this document.

## Related

- Assets: [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-31007](../entities/part/awi-31007.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm code: [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- Procedure: [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletins: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md), [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Topics: [Blades, pitch bearings and main-component lifts](../topics/blades-and-rotor.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../topics/generator-and-electrical.md), [Safety, isolation and work at height](../topics/safety-and-access.md), [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-31007](../entities/part/awi-31007.md)
- [Blades, pitch bearings and main-component lifts](../topics/blades-and-rotor.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [Generator brushes and electrical systems](../topics/generator-and-electrical.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-51207](../entities/part/lws-p-51207.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [pitch bearing](../entities/component/pitch-bearing.md)
- [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [PWS-320-D208](../entities/part/pws-320-d208.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)
- [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
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

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Work Orders Export through 2026-08-31 — row 2](../evidence/src-9fd435ef5956/r0002-r0002.md) · table
[^c2]: [Work Orders Export through 2026-08-31 — row 3](../evidence/src-9fd435ef5956/r0003-r0003.md) · table
[^c3]: [Work Orders Export through 2026-08-31 — row 4](../evidence/src-9fd435ef5956/r0004-r0004.md) · table
[^c4]: [Work Orders Export through 2026-08-31 — row 5](../evidence/src-9fd435ef5956/r0005-r0005.md) · table
[^c5]: [Work Orders Export through 2026-08-31 — row 6](../evidence/src-9fd435ef5956/r0006-r0006.md) · table
[^c6]: [Work Orders Export through 2026-08-31 — row 7](../evidence/src-9fd435ef5956/r0007-r0007.md) · table
[^c7]: [Work Orders Export through 2026-08-31 — row 8](../evidence/src-9fd435ef5956/r0008-r0008.md) · table
[^c8]: [Work Orders Export through 2026-08-31 — row 9](../evidence/src-9fd435ef5956/r0009-r0009.md) · table
[^c9]: [Work Orders Export through 2026-08-31 — row 10](../evidence/src-9fd435ef5956/r0010-r0010.md) · table
[^c10]: [Work Orders Export through 2026-08-31 — row 11](../evidence/src-9fd435ef5956/r0011-r0011.md) · table
[^c11]: [Work Orders Export through 2026-08-31 — row 12](../evidence/src-9fd435ef5956/r0012-r0012.md) · table
[^c12]: [Work Orders Export through 2026-08-31 — row 13](../evidence/src-9fd435ef5956/r0013-r0013.md) · table
[^c13]: [Work Orders Export through 2026-08-31 — row 38](../evidence/src-9fd435ef5956/r0038-r0038.md) · table
[^c14]: [Work Orders Export through 2026-08-31 — row 43](../evidence/src-9fd435ef5956/r0043-r0043.md) · table
[^c15]: [Work Orders Export through 2026-08-31 — row 45](../evidence/src-9fd435ef5956/r0045-r0045.md) · table
[^c16]: [Work Orders Export through 2026-08-31 — row 46](../evidence/src-9fd435ef5956/r0046-r0046.md) · table
[^c17]: [Work Orders Export through 2026-08-31 — row 47](../evidence/src-9fd435ef5956/r0047-r0047.md) · table
[^c18]: [Work Orders Export through 2026-08-31 — row 48](../evidence/src-9fd435ef5956/r0048-r0048.md) · table
[^c19]: [Work Orders Export through 2026-08-31 — row 49](../evidence/src-9fd435ef5956/r0049-r0049.md) · table
[^c20]: [Work Orders Export through 2026-08-31 — row 50](../evidence/src-9fd435ef5956/r0050-r0050.md) · table
[^c21]: [Work Orders Export through 2026-08-31 — row 56](../evidence/src-9fd435ef5956/r0056-r0056.md) · table
[^c22]: [Work Orders Export through 2026-08-31 — row 57](../evidence/src-9fd435ef5956/r0057-r0057.md) · table
[^c23]: [Work Orders Export through 2026-08-31 — row 58](../evidence/src-9fd435ef5956/r0058-r0058.md) · table
[^c24]: [Work Orders Export through 2026-08-31 — row 59](../evidence/src-9fd435ef5956/r0059-r0059.md) · table
[^c25]: [Work Orders Export through 2026-08-31 — row 60](../evidence/src-9fd435ef5956/r0060-r0060.md) · table
[^c26]: [Work Orders Export through 2026-08-31 — row 61](../evidence/src-9fd435ef5956/r0061-r0061.md) · table
[^c27]: [Work Orders Export through 2026-08-31 — row 62](../evidence/src-9fd435ef5956/r0062-r0062.md) · table
[^c28]: [Work Orders Export through 2026-08-31 — row 63](../evidence/src-9fd435ef5956/r0063-r0063.md) · table
[^c29]: [Work Orders Export through 2026-08-31 — row 64](../evidence/src-9fd435ef5956/r0064-r0064.md) · table
[^c30]: [Work Orders Export through 2026-08-31 — row 65](../evidence/src-9fd435ef5956/r0065-r0065.md) · table
[^c31]: [Work Orders Export through 2026-08-31 — row 66](../evidence/src-9fd435ef5956/r0066-r0066.md) · table
[^c32]: [Work Orders Export through 2026-08-31 — row 67](../evidence/src-9fd435ef5956/r0067-r0067.md) · table
[^c33]: [Work Orders Export through 2026-08-31 — row 68](../evidence/src-9fd435ef5956/r0068-r0068.md) · table
[^c34]: [Work Orders Export through 2026-08-31 — row 70](../evidence/src-9fd435ef5956/r0070-r0070.md) · table
[^c35]: [Work Orders Export through 2026-08-31 — row 71](../evidence/src-9fd435ef5956/r0071-r0071.md) · table
[^c36]: [Work Orders Export through 2026-08-31 — row 73](../evidence/src-9fd435ef5956/r0073-r0073.md) · table
[^c37]: [Work Orders Export through 2026-08-31 — row 78](../evidence/src-9fd435ef5956/r0078-r0078.md) · table
[^c38]: [Work Orders Export through 2026-08-31 — row 80](../evidence/src-9fd435ef5956/r0080-r0080.md) · table
[^c39]: [Work Orders Export through 2026-08-31 — row 82](../evidence/src-9fd435ef5956/r0082-r0082.md) · table
[^c40]: [Work Orders Export through 2026-08-31 — row 83](../evidence/src-9fd435ef5956/r0083-r0083.md) · table
[^c41]: [Work Orders Export through 2026-08-31 — row 86](../evidence/src-9fd435ef5956/r0086-r0086.md) · table
[^c42]: [Work Orders Export through 2026-08-31 — row 90](../evidence/src-9fd435ef5956/r0090-r0090.md) · table
[^c43]: [Work Orders Export through 2026-08-31 — row 91](../evidence/src-9fd435ef5956/r0091-r0091.md) · table
[^c44]: [Work Orders Export through 2026-08-31 — row 92](../evidence/src-9fd435ef5956/r0092-r0092.md) · table
[^c45]: [Work Orders Export through 2026-08-31 — row 93](../evidence/src-9fd435ef5956/r0093-r0093.md) · table
[^c46]: [Work Orders Export through 2026-08-31 — row 94](../evidence/src-9fd435ef5956/r0094-r0094.md) · table
[^c47]: [Work Orders Export through 2026-08-31 — row 95](../evidence/src-9fd435ef5956/r0095-r0095.md) · table
[^c48]: [Work Orders Export through 2026-08-31 — row 14](../evidence/src-9fd435ef5956/r0014-r0014.md) · table
[^c49]: [Work Orders Export through 2026-08-31 — row 15](../evidence/src-9fd435ef5956/r0015-r0015.md) · table
[^c50]: [Work Orders Export through 2026-08-31 — row 16](../evidence/src-9fd435ef5956/r0016-r0016.md) · table
[^c51]: [Work Orders Export through 2026-08-31 — row 17](../evidence/src-9fd435ef5956/r0017-r0017.md) · table
[^c52]: [Work Orders Export through 2026-08-31 — row 34](../evidence/src-9fd435ef5956/r0034-r0034.md) · table
[^c53]: [Work Orders Export through 2026-08-31 — row 39](../evidence/src-9fd435ef5956/r0039-r0039.md) · table
[^c54]: [Work Orders Export through 2026-08-31 — row 75](../evidence/src-9fd435ef5956/r0075-r0075.md) · table
