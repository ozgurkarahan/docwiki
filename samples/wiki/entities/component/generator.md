---
id: component:generator
type: entity
title: generator
summary: The generator is a wind turbine component used with a 690 V double-fed asynchronous generator system. It is driven at 1,500 rpm from the gearbox output shaft, with an overall gearbox ratio of 1:118.4 from a rotor speed of 12.7 rpm. Current records include generator brush inspections and…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- component
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: component
key: generator
aliases:
- text: generator
  lang: en
- text: génératrice
  lang: fr
- text: Generator
  lang: de
sources:
- src-1b5b5135881d
- src-1c261d5b87b5
- src-21bd4ddf2ed6
- src-36f5b999211a
- src-42566abae6ef
- src-824b788eefc0
- src-86cb00fd2f6b
- src-9107d71821bf
- src-9a6703e054dc
- src-9fd435ef5956
- src-a011da5de982
- src-aba30cb7207f
- src-b7a218719725
- src-e7cd20fa7984
---

# generator

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

The generator is a wind turbine component used with a 690 V double-fed asynchronous generator system.[^c1][^c2][^c3] It is driven at 1,500 rpm from the [gearbox](gearbox.md) output shaft, with an overall gearbox ratio of 1:118.4 from a rotor speed of 12.7 rpm.[^c4][^c5][^c6][^c7] Current records include generator brush inspections and replacements, generator-side [HSS bearing](hss-bearing.md) maintenance, and generator winding temperature alarms.[^c8][^c9][^c10][^c11][^c12][^c13][^c14][^c15][^c16][^c17][^c18][^c19][^c20][^c21]

## Facts

- The [gearbox](gearbox.md) overall ratio is 1:118.4; at a rated rotor speed of 12.7 rpm, the output pinion shaft drives the generator at 1,500 rpm.[^c4]
- For [LT-32](../product/lt-32.md) electrical 690 V energy from the generator, converter, and auxiliaries is isolated at the main circuit breaker in the tower base.[^c3]
- [WI-GEN-014](../procedure/wi-gen-014.md) is a Revision A work instruction applicable from 2025-09-15 to [WTG-01](../asset/wtg-01.md) through [WTG-12](../asset/wtg-12.md) with a 690 V double-fed asynchronous generator.[^c1][^c2]
- The instruction describes checking and replacing the [generator brushes](generator-brushes.md) of Litware LT-32 wind turbines at the [Quellmoor Ridge wind farm](../asset/quellmoor-ridge-wind-farm.md).[^c8]
- The generator, including stator and rotor, must be locked out according to [SOP-LOTO-001](../procedure/sop-loto-001.md).[^c22]
- Alarm [A3210](../alarm-code/a3210.md), Generator brush wear limit reached, appears when the remaining brush length reaches approximately 20 mm.[^c23]
- The operating procedure begins by obtaining the PTW, stopping the turbine, and locking out the generator.[^c24]
- The [HSS bearing](hss-bearing.md) vibration on the generator side rose from 2.1 mm/s RMS to 5.2 mm/s RMS and exceeded the 4.5 mm/s alarm level.[^c25]
- A contributing factor was generator-side HSS bearing wear, supported by oil analysis TR-OA-2026-0614 with iron at 64 ppm, PQ index 112, and the vibration trend.[^c26]
- Replacing the generator-side HSS bearing [FGT-P-22328](../part/fgt-p-22328.md) under WO-26-0412 is waiting for parts and is planned on delivery of the bearing.[^c27]
- Generator brush inspection task MP-GEN-01 is scheduled every 6 months and references WI-GEN-014.[^c9]
- Read the sight glass on the generator side of the gearbox.[^c28]
- [WTG-09](../asset/wtg-09.md) had A3210 Generator brush wear limit reached raised on 2026-07-16 and cleared on 2026-07-18; WTG-09 was also in [S310 Maintenance mode](../status-code/s310.md) on 2026-07-18 from 07:58:12 to 11:52:40.[^c10][^c11][^c12][^c13]
- WTG-12 had [A3201 Generator winding temperature high](../alarm-code/a3201.md) raised at 147.3 °C and cleared at 139.5 °C on 2026-08-26.[^c14][^c15]
- FGT-P-22328, the HSS bearing on the generator side for [FGT-3200](../product/fgt-3200.md), is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c29][^c30]
- WO-26-0187 for [WTG-10](../asset/wtg-10.md) replaced the generator-side HSS bearing, was completed as high-priority corrective maintenance, used part FGT-P-22328 quantity 1, and notes that the last spare bearing was used.[^c16]
- WO-26-0412 for [WTG-07](../asset/wtg-07.md) is a high-priority corrective-maintenance work order to replace the generator-side HSS bearing, is waiting for parts, lists part FGT-P-22328 quantity 1, and remarks that vibration is above the alarm level of 4.5 mm/s.[^c17]
- WO-26-0436 for WTG-09 replaced generator brushes for A3210, was completed under WI-GEN-014, used part [LWS-P-51207](../part/lws-p-51207.md) quantity 1, and notes the shortest brush was 16 mm.[^c18]
- WO-26-0439 for [WTG-02](../asset/wtg-02.md) is waiting for parts for a generator-side HSS bearing replacement after spalling was found at endoscopy on 2026-07-23, and it lists part FGT-P-22328 quantity 1.[^c19]
- The gearbox raises rotor speed from 12.7 rpm to 1,500 rpm at the generator.[^c5]
- The overall gearbox ratio is 1:118.4, with rotor speed 12.7 rpm and generator speed 1,500 rpm.[^c6]
- HSS means high-speed shaft, the output shaft to the generator coupling.[^c7]
- The quiz answers state that the HSS drives the generator, [A2102](../alarm-code/a2102.md) trips at 82 °C, the oil used is [Proseware PWG 220](../product/pwg-220.md), and a rising PQ index means more ferrous wear debris, often from a bearing.[^c31]
- A stock snapshot dated 21 July showed that HSS bearing FGT-P-22328 on the generator side was below its minimum level.[^c32]
- WTG-09 had its generator brushes replaced under work order WO-26-0436 following alarm A3210 from 16/07.[^c20]
- WTG-02 had an endoscope inspection on 23/07 that found spalling on the HSS bearing on the generator side.[^c21]

## Timeline

- 2025-09-15: [WI-GEN-014](../procedure/wi-gen-014.md) is a Revision A work instruction applicable from 2025-09-15 to [WTG-01](../asset/wtg-01.md) through [WTG-12](../asset/wtg-12.md) with a 690 V double-fed asynchronous generator.[^c1][^c2]
- 2026-07-16: [WTG-09](../asset/wtg-09.md) had [A3210 Generator brush wear limit reached](../alarm-code/a3210.md) raised on 2026-07-16 and cleared on 2026-07-18; WTG-09 was also in [S310 Maintenance mode](../status-code/s310.md) on 2026-07-18 from 07:58:12 to 11:52:40.[^c10][^c11][^c12][^c13]
- 2026-07-23: WO-26-0439 for [WTG-02](../asset/wtg-02.md) is waiting for parts for a generator-side [HSS bearing](hss-bearing.md) replacement after spalling was found at endoscopy on 2026-07-23, and it lists part [FGT-P-22328](../part/fgt-p-22328.md) quantity 1.[^c19]
- 2026-08-26: WTG-12 had [A3201 Generator winding temperature high](../alarm-code/a3201.md) raised at 147.3 °C and cleared at 139.5 °C on 2026-08-26.[^c14][^c15]
- 2026-09-25: FGT-P-22328, the HSS bearing on the generator side for [FGT-3200](../product/fgt-3200.md), is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c29][^c30]

## Documents

- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines](../../sources/sop-loto-001-revc-lockout-tagout.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [SPL-012 Gearbox Oil Level Check](../../sources/spl-012-gearbox-oil-level-check.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../../sources/2026-07-18-note-de-releve.md)
- [Shift Handover for 2026-07-29 Day Shift](../../sources/2026-07-29-shift-handover.md)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [A2102 Gearbox oil sump temperature trip](../alarm-code/a2102.md)
- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Fabrikam FGT-3200](../product/fgt-3200.md)
- [FGT-P-22328](../part/fgt-p-22328.md)
- [gearbox](gearbox.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [HSS bearing](hss-bearing.md)
- [Litware LT-32](../product/lt-32.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [Proseware Lubricants](../organisation/proseware-lubricants.md)
- [Proseware PWG 220](../product/pwg-220.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Shift Handover for 2026-07-29 Day Shift](../../sources/2026-07-29-shift-handover.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../../sources/2026-07-18-note-de-releve.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../procedure/sop-loto-001.md)
- [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines](../../sources/sop-loto-001-revc-lockout-tagout.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [SPL-012 Gearbox Oil Level Check](../../sources/spl-012-gearbox-oil-level-check.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [WI-GEN-014 Generator brush replacement](../procedure/wi-gen-014.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [WTG-01](../asset/wtg-01.md)
- [WTG-02](../asset/wtg-02.md)
- [WTG-12](../asset/wtg-12.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 2](../../evidence/src-824b788eefc0/para-0002.md) · ✓ quote verified
[^c2]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 7](../../evidence/src-824b788eefc0/tbl-01-r0007-r0007.md) · table
[^c3]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 2](../../evidence/src-21bd4ddf2ed6/tbl-02-r0002-r0002.md) · table
[^c4]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../../evidence/src-1c261d5b87b5/p0002.md) · ✓ quote verified
[^c5]: [Gearbox Fundamentals for Wind Technicians — slide 2](../../evidence/src-1b5b5135881d/slide-02.md) · ✓ quote verified
[^c6]: [Gearbox Fundamentals for Wind Technicians — slide 3](../../evidence/src-1b5b5135881d/slide-03.md) · ✓ quote verified
[^c7]: [Gearbox Fundamentals for Wind Technicians — slide 4](../../evidence/src-1b5b5135881d/slide-04.md) · ✓ quote verified
[^c8]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 4](../../evidence/src-824b788eefc0/para-0004.md) · ✓ quote verified
[^c9]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 9](../../evidence/src-aba30cb7207f/sheet-tasks-r0009-r0009.md) · table
[^c10]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1281](../../evidence/src-36f5b999211a/r1281-r1281.md) · table
[^c11]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1317](../../evidence/src-36f5b999211a/r1317-r1317.md) · table
[^c12]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1313](../../evidence/src-36f5b999211a/r1313-r1313.md) · table
[^c13]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1318](../../evidence/src-36f5b999211a/r1318-r1318.md) · table
[^c14]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1878](../../evidence/src-36f5b999211a/r1878-r1878.md) · table
[^c15]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1879](../../evidence/src-36f5b999211a/r1879-r1879.md) · table
[^c16]: [Work Orders Export through 2026-08-31 — row 38](../../evidence/src-9fd435ef5956/r0038-r0038.md) · table
[^c17]: [Work Orders Export through 2026-08-31 — row 73](../../evidence/src-9fd435ef5956/r0073-r0073.md) · table
[^c18]: [Work Orders Export through 2026-08-31 — row 78](../../evidence/src-9fd435ef5956/r0078-r0078.md) · table
[^c19]: [Work Orders Export through 2026-08-31 — row 80](../../evidence/src-9fd435ef5956/r0080-r0080.md) · table
[^c20]: [Shift Handover Note - Day Shift - 18/07/2026 — lines 6–12](../../evidence/src-b7a218719725/l0006-l0012.md) · ✓ quote verified
[^c21]: [Shift Handover for 2026-07-29 Day Shift — lines 5–14](../../evidence/src-a011da5de982/l0005-l0014.md) · ✓ quote verified
[^c22]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 7](../../evidence/src-824b788eefc0/para-0007.md) · ✓ quote verified
[^c23]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 15](../../evidence/src-824b788eefc0/para-0015.md) · ✓ quote verified
[^c24]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 17](../../evidence/src-824b788eefc0/para-0017.md) · ✓ quote verified
[^c25]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 7](../../evidence/src-86cb00fd2f6b/para-0007.md) · ✓ quote verified
[^c26]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 18](../../evidence/src-86cb00fd2f6b/para-0018.md) · ✓ quote verified
[^c27]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 5](../../evidence/src-86cb00fd2f6b/tbl-02-r0005-r0005.md) · table
[^c28]: [SPL-012 Gearbox Oil Level Check — slide 2](../../evidence/src-9a6703e054dc/slide-02.md) · ✓ quote verified
[^c29]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 3](../../evidence/src-42566abae6ef/sheet-about-r0003-r0003.md) · table
[^c30]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 2](../../evidence/src-42566abae6ef/sheet-stock-r0002-r0002.md) · table
[^c31]: [Gearbox Fundamentals for Wind Technicians — slide 10](../../evidence/src-1b5b5135881d/slide-10.md) · ✓ quote verified
[^c32]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 5–6](../../evidence/src-9107d71821bf/msg-body-l0005-l0006.md) · ✓ quote verified
