---
id: component:oil-cooler
type: entity
title: oil cooler
summary: An oil cooler is a component that cools oil, using an air/oil cooler with an electric fan and a thermostatic valve that sends oil through the cooler above 45 °C. At Quellmoor Ridge, preventive maintenance for the oil cooler includes radiator cleaning and fan current checks every 6 months. A recent…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- component
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: component
key: oil-cooler
aliases:
- text: oil cooler
  lang: en
- text: refroidisseur d'huile
  lang: fr
- text: Ölkühler
  lang: de
sources:
- src-15df96905f07
- src-1b5b5135881d
- src-1c261d5b87b5
- src-42566abae6ef
- src-86cb00fd2f6b
- src-9107d71821bf
- src-9fd435ef5956
- src-aba30cb7207f
---

# oil cooler

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

An oil cooler is a component that cools oil, using an air/oil cooler with an electric fan and a thermostatic valve that sends oil through the cooler above 45 °C.[^c1] At [Quellmoor Ridge](../asset/quellmoor-ridge-wind-farm.md), preventive maintenance for the oil cooler includes radiator cleaning and fan current checks every 6 months.[^c2][^c3] A recent over-temperature issue was linked to reduced oil cooler cooling capacity, and corrective work replaced the fan motor and cleaned the radiator.[^c4][^c5][^c6][^c7][^c8][^c9]

## Facts

- The oil passes through a 10 micron inline filter and an air/oil cooler with an electric fan; a thermostatic valve sends oil through the cooler above 45 °C.[^c1]
- Oil-change tightening torques are 280 Nm for the drain plug, 85 Nm for filter housing cover screws, 210 Nm for oil cooler hose flange screws, and 22 Nm for sight glass retaining screws.[^c10]
- Inspection intervals are 6 months for visual inspection and leak check, 6 months for oil sampling and laboratory analysis, 24 months for endoscope inspection, continuous for vibration monitoring, 12 months for filter element replacement, and as required for oil cooler radiator cleaning.[^c11]
- The root-cause analysis says the oil overheated because the oil cooler did not reject enough heat at high load.[^c4]
- The report identifies the root cause as missing preventive maintenance of the oil cooler, allowing fan motor bearing failure and radiator fouling to reduce cooling capacity.[^c5]
- Corrective actions completed on 2026-06-24 included replacing [oil cooler fan motor](cooler-fan-motor.md) [LWS-P-30418](../part/lws-p-30418.md) under WO-26-0398 and cleaning the oil cooler radiator under WO-26-0399.[^c6][^c7]
- Preventive task MP-GBX-07 for oil cooler radiator cleaning and fan current check was added to the maintenance plan for all turbines every 6 months.[^c2]
- Oil cooler radiator cleaning and fan current check task MP-GBX-07 is scheduled every 6 months, references INC-2026-006 (D7), and was added in issue 2 on 2026-07-01.[^c3]
- LWS-P-30418, the 1.5 kW oil cooler fan motor, is a critical item below minimum stock: 1 pc on hand, minimum 2 pc, reorder quantity 2 pc, and 2 pc on order under PO-77102 for expected delivery on 2026-08-14.[^c12][^c13]
- For [WTG-07](../asset/wtg-07.md) under INC-2026-006, WO-26-0398 replaced the oil cooler fan motor with part LWS-P-30418 quantity 1, and WO-26-0399 cleaned the oil cooler radiator with remarks that fins were about 40 % blocked by insects and pollen.[^c8][^c9]
- The action list assigned Callum Rydings to inspect the WTG-07 oil cooler fan and radiator by 2026-06-24.[^c14]
- Oil cooler fan motor LWS-P-30418 is also below minimum after the WTG-07 repair, with 1 on hand and a minimum of 2.[^c15]
- Two oil cooler fan motors are on order under PO-77102 with an expected date of 14 August, and no work order is waiting for that motor.[^c15]

## Timeline

- 2026-06-24: Corrective actions completed on 2026-06-24 included replacing [oil cooler fan motor](cooler-fan-motor.md) [LWS-P-30418](../part/lws-p-30418.md) under WO-26-0398 and cleaning the oil cooler radiator under WO-26-0399.[^c6][^c7]
- 2026-06-24: The action list assigned Callum Rydings to inspect the [WTG-07](../asset/wtg-07.md) oil cooler fan and radiator by 2026-06-24.[^c14]
- 2026-07-01: Oil cooler radiator cleaning and fan current check task MP-GBX-07 is scheduled every 6 months, references INC-2026-006 (D7), and was added in issue 2 on 2026-07-01.[^c3]
- 2026-08-14: LWS-P-30418, the 1.5 kW oil cooler fan motor, is a critical item below minimum stock: 1 pc on hand, minimum 2 pc, reorder quantity 2 pc, and 2 pc on order under PO-77102 for expected delivery on 2026-08-14.[^c12][^c13]

## Documents

- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [LWS-P-30418](../part/lws-p-30418.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [oil cooler fan motor](cooler-fan-motor.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [WTG-07](../asset/wtg-07.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../../evidence/src-1c261d5b87b5/p0002.md) · ✓ quote verified
[^c2]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 21](../../evidence/src-86cb00fd2f6b/para-0021.md) · ✓ quote verified
[^c3]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 8](../../evidence/src-aba30cb7207f/sheet-tasks-r0008-r0008.md) · table
[^c4]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 12](../../evidence/src-86cb00fd2f6b/para-0012.md) · ✓ quote verified
[^c5]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 17](../../evidence/src-86cb00fd2f6b/para-0017.md) · ✓ quote verified
[^c6]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 2](../../evidence/src-86cb00fd2f6b/tbl-02-r0002-r0002.md) · table
[^c7]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 3](../../evidence/src-86cb00fd2f6b/tbl-02-r0003-r0003.md) · table
[^c8]: [Work Orders Export through 2026-08-31 — row 70](../../evidence/src-9fd435ef5956/r0070-r0070.md) · table
[^c9]: [Work Orders Export through 2026-08-31 — row 71](../../evidence/src-9fd435ef5956/r0071-r0071.md) · table
[^c10]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 3](../../evidence/src-1c261d5b87b5/p0003.md) · ✓ quote verified
[^c11]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 4](../../evidence/src-1c261d5b87b5/p0004.md) · ✓ quote verified
[^c12]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 3](../../evidence/src-42566abae6ef/sheet-about-r0003-r0003.md) · table
[^c13]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 9](../../evidence/src-42566abae6ef/sheet-stock-r0009-r0009.md) · table
[^c14]: [Monthly O&M Review Minutes – 2026-06-18 — table 1, row 2](../../evidence/src-15df96905f07/tbl-01-r0002-r0002.md) · table
[^c15]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 18–20](../../evidence/src-9107d71821bf/msg-body-l0018-l0020.md) · ✓ quote verified
