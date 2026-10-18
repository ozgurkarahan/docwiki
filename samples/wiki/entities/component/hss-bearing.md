---
id: component:hss-bearing
type: entity
title: HSS bearing
summary: The HSS bearing is a gearbox bearing on the generator side, identified in records as part FGT-P-22328. It is linked in the records to high temperature alarms, elevated vibration, wear, and spalling. The bearing is currently below minimum stock, with replacements on order and work orders waiting…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- component
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: component
key: hss-bearing
aliases:
- text: HSS bearing
  lang: en
- text: roulement HSS
  lang: fr
- text: HSS-Lager
  lang: de
sources:
- src-15df96905f07
- src-1abc5aef1a40
- src-1b5b5135881d
- src-1c261d5b87b5
- src-1d8dff18b801
- src-36f5b999211a
- src-42566abae6ef
- src-86cb00fd2f6b
- src-9107d71821bf
- src-990a047180b7
- src-9fd435ef5956
- src-a011da5de982
---

# HSS bearing

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

The HSS bearing is a [gearbox](gearbox.md) bearing on the [generator](generator.md) side, identified in records as part [FGT-P-22328](../part/fgt-p-22328.md).[^c1][^c2][^c3][^c4][^c5] It is linked in the records to high temperature alarms, elevated vibration, wear, and spalling.[^c6][^c7][^c8][^c9][^c10][^c4][^c5][^c11][^c12] The bearing is currently below minimum stock, with replacements on order and work orders waiting for parts.[^c1][^c2][^c13][^c14][^c15][^c16][^c17]

## Facts

- Alarm [A2110](../alarm-code/a2110.md), Gearbox HSS bearing temperature high at 90 °C, can be caused by bearing damage or lubrication starvation; checks are vibration trend review and endoscope inspection of the bearing.[^c6]
- The HSS bearing vibration on the [generator](generator.md) side rose from 2.1 mm/s RMS to 5.2 mm/s RMS and exceeded the 4.5 mm/s alarm level.[^c7]
- A contributing factor was generator-side HSS bearing wear, supported by oil analysis TR-OA-2026-0614 with iron at 64 ppm, PQ index 112, and the vibration trend.[^c8]
- Replacing the generator-side HSS bearing [FGT-P-22328](../part/fgt-p-22328.md) under WO-26-0412 is waiting for parts and is planned on delivery of the bearing.[^c18]
- [WTG-02](../asset/wtg-02.md) recorded A2110 Gearbox HSS bearing temperature high twice in this part, with raised values of 91.2 °C on 2026-07-19 and 90.6 °C on 2026-07-22.[^c9][^c10]
- FGT-P-22328, the HSS bearing on the generator side for [FGT-3200](../product/fgt-3200.md), is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c1][^c2]
- WO-26-0187 for [WTG-10](../asset/wtg-10.md) replaced the generator-side HSS bearing, was completed as high-priority corrective maintenance, used part FGT-P-22328 quantity 1, and notes that the last spare bearing was used.[^c3]
- WO-26-0412 for [WTG-07](../asset/wtg-07.md) is a high-priority corrective-maintenance work order to replace the generator-side HSS bearing, is waiting for parts, lists part FGT-P-22328 quantity 1, and remarks that vibration is above the alarm level of 4.5 mm/s.[^c4]
- WO-26-0439 for WTG-02 is waiting for parts for a generator-side HSS bearing replacement after spalling was found at endoscopy on 2026-07-23, and it lists part FGT-P-22328 quantity 1.[^c5]
- Typical gearbox-related failure modes listed are HSS bearing damage, micropitting on gear teeth, cooler fouling and fan motor failures, and oil leaks at seals and hoses.[^c19]
- There had been no HSS bearing FGT-P-22328 in stock since the WTG-10 repair in March.[^c13]
- The email was sent by Tomasz Lebrecht to Dario Penwarden on 22 July 2026 with the subject “Parts shortage - HSS bearing FGT-P-22328 below minimum stock.”[^c14]
- A stock snapshot dated 21 July showed that HSS bearing FGT-P-22328 on the generator side was below its minimum level.[^c20]
- For HSS bearing FGT-P-22328, stock was 0 on hand, minimum 1, and 2 on order under PO-76994 to [Fabrikam](../organisation/fabrikam-getriebetechnik.md).[^c15]
- The last HSS bearing was used on WTG-10 in March under WO-26-0187, and Fabrikam confirmed delivery of two bearings in week 39, from 21 to 25 September 2026.[^c16]
- WO-26-0412 for WTG-07 HSS bearing replacement cannot start until the bearings arrive.[^c17]
- WTG-02 had an endoscope inspection on 23/07 that found spalling on the HSS bearing on the generator side.[^c11]
- WTG-07 still has HSS bearing vibration around 5.3 mm/s; oil temperature has been normal since the fan motor replacement, and WO-26-0412 is waiting for the bearing.[^c12]

## Timeline

- 2026-07-19: [WTG-02](../asset/wtg-02.md) recorded [A2110 Gearbox HSS bearing temperature high](../alarm-code/a2110.md) twice in this part, with raised values of 91.2 °C on 2026-07-19 and 90.6 °C on 2026-07-22.[^c9][^c10]
- 2026-07-22: The email was sent by Tomasz Lebrecht to Dario Penwarden on 22 July 2026 with the subject “Parts shortage - HSS bearing [FGT-P-22328](../part/fgt-p-22328.md) below minimum stock.”[^c14]
- 2026-07-23: WO-26-0439 for WTG-02 is waiting for parts for a generator-side HSS bearing replacement after spalling was found at endoscopy on 2026-07-23, and it lists part FGT-P-22328 quantity 1.[^c5]
- 2026-09-25: FGT-P-22328, the HSS bearing on the [generator](generator.md) side for [FGT-3200](../product/fgt-3200.md), is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c1][^c2]
- 2026-09-25: The last HSS bearing was used on [WTG-10](../asset/wtg-10.md) in March under WO-26-0187, and [Fabrikam](../organisation/fabrikam-getriebetechnik.md) confirmed delivery of two bearings in week 39, from 21 to 25 September 2026.[^c16]

## Documents

- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [Shift Handover for 2026-07-29 Day Shift](../../sources/2026-07-29-shift-handover.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../../sources/2026-07-15-shift-handover.md)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Fabrikam FGT-3200](../product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../organisation/fabrikam-getriebetechnik.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [FGT-P-22328](../part/fgt-p-22328.md)
- [gearbox](gearbox.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [generator](generator.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../../sources/2026-07-15-shift-handover.md)
- [Shift Handover for 2026-07-29 Day Shift](../../sources/2026-07-29-shift-handover.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [WTG-02](../asset/wtg-02.md)
- [WTG-07](../asset/wtg-07.md)
- [WTG-10](../asset/wtg-10.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 3](../../evidence/src-42566abae6ef/sheet-about-r0003-r0003.md) · table
[^c2]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 2](../../evidence/src-42566abae6ef/sheet-stock-r0002-r0002.md) · table
[^c3]: [Work Orders Export through 2026-08-31 — row 38](../../evidence/src-9fd435ef5956/r0038-r0038.md) · table
[^c4]: [Work Orders Export through 2026-08-31 — row 73](../../evidence/src-9fd435ef5956/r0073-r0073.md) · table
[^c5]: [Work Orders Export through 2026-08-31 — row 80](../../evidence/src-9fd435ef5956/r0080-r0080.md) · table
[^c6]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../../evidence/src-1c261d5b87b5/p0005.md) · ✓ quote verified
[^c7]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 7](../../evidence/src-86cb00fd2f6b/para-0007.md) · ✓ quote verified
[^c8]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 18](../../evidence/src-86cb00fd2f6b/para-0018.md) · ✓ quote verified
[^c9]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1330](../../evidence/src-36f5b999211a/r1330-r1330.md) · table
[^c10]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1366](../../evidence/src-36f5b999211a/r1366-r1366.md) · table
[^c11]: [Shift Handover for 2026-07-29 Day Shift — lines 5–14](../../evidence/src-a011da5de982/l0005-l0014.md) · ✓ quote verified
[^c12]: [Shift handover - 2026-07-15 (day shift to night shift) — lines 11–14](../../evidence/src-1d8dff18b801/l0011-l0014.md) · ✓ quote verified
[^c13]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 16](../../evidence/src-15df96905f07/para-0016.md) · ✓ quote verified
[^c14]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message headers](../../evidence/src-9107d71821bf/msg-headers.md) · ✓ quote verified
[^c15]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, line 8](../../evidence/src-9107d71821bf/msg-body-l0008-l0008.md) · ✓ quote verified
[^c16]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 10–12](../../evidence/src-9107d71821bf/msg-body-l0010-l0012.md) · ✓ quote verified
[^c17]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 14–16](../../evidence/src-9107d71821bf/msg-body-l0014-l0016.md) · ✓ quote verified
[^c18]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 5](../../evidence/src-86cb00fd2f6b/tbl-02-r0005-r0005.md) · table
[^c19]: [Gearbox Fundamentals for Wind Technicians — slide 8](../../evidence/src-1b5b5135881d/slide-08.md) · ✓ quote verified
[^c20]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 5–6](../../evidence/src-9107d71821bf/msg-body-l0005-l0006.md) · ✓ quote verified
