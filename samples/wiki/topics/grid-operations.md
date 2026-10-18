---
id: topic:grid-operations
type: topic
title: Grid connection and grid operator instructions
summary: This page covers the site grid connection, grid operator curtailment instructions, export limits, and related SCADA evidence.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- grid-operations
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: grid-operations
sources:
- src-15df96905f07
- src-36f5b999211a
- src-867a6c78f5b5
- src-a14b304454ed
- src-b342a2d5bfdf
- src-e7cd20fa7984
confidence: high
contradictions: 0
superseded_claims: 0
---

# Grid connection and grid operator instructions

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers the site grid connection, grid operator curtailment instructions, export limits, and related SCADA evidence.

## Overview

[Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) connects to [City Power & Light](../entities/organisation/city-power-and-light.md) at Skelvane 132 kV substation, circuit 2.[^c1][^c2] City Power & Light Network Control issued curtailment instruction CPL-CI-2026-018 to [Contoso Renewables](../entities/organisation/contoso-renewables.md) for Quellmoor Ridge Wind Farm for a planned network outage.[^c1] The instruction required active power export at the connection point to be limited to 20 MW during the specified daytime periods on 14, 15, and 16 July 2026.[^c1] SCADA records show [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) entering [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md) at 20.0 MW on 14, 15, and 16 July 2026, with the 15 and 16 July curtailments starting at about 08:00 and ending at about 18:00.[^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10]

## Connection assets

- The [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md) is a 33/132 kV substation with one 45 MVA transformer located next to the O&M building.[^c2]
- The site layout plan labels a substation rated 33/132 kV and a 132 kV line going to Skelvane substation with [City Power & Light](../entities/organisation/city-power-and-light.md) named in the label.[^c11][^c12]
- The onboarding deck states that [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) connects to City Power & Light at the Skelvane 132 kV substation.[^c13]

## Curtailment instruction details

- The curtailment instruction was issued on 2026-07-02 at 10:15 and was acknowledged for [Contoso Renewables](../entities/organisation/contoso-renewables.md) by Dario Penwarden on 2026-07-02 at 14:40.[^c1]
- The reason for the curtailment instruction was planned maintenance of Skelvane 132 kV circuit 1 while the network ran on a single circuit.[^c1]
- The export-limit schedule listed 20 MW from 08:00 to 18:00 on 2026-07-14, 2026-07-15, and 2026-07-16.[^c1]
- When the limit ends, export must be restored with a ramp rate of at most 5 MW per minute.[^c1]
- Export above the limit by more than 1 MW for more than 5 minutes will be reported.[^c1]

## Instruction handling

- The instruction had to be acknowledged within 48 hours.[^c1]
- Network Control may extend the outage, and any extension is confirmed by phone and in writing.[^c1]
- The Network Control duty engineer at [City Power & Light](../entities/organisation/city-power-and-light.md) is available 24/7.[^c1]

## Operational evidence

- On 2026-07-14, [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) started [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md) at 20.0 MW, with END entries shown through WTG-12 across the part boundary.[^c3][^c4][^c5][^c6]
- On 2026-07-15 and 2026-07-16, S430 Curtailed - grid operator setpoint at 20.0 MW started for WTG-01 through WTG-12 at about 08:00 and ended at about 18:00.[^c7][^c8][^c9][^c10]
- The June O&M review recorded that [City Power & Light](../entities/organisation/city-power-and-light.md) had announced July network works on the Skelvane 132 kV circuits and that the formal curtailment instruction was expected in early July.[^c14]

## Other grid-related events

- On 2026-04-20, [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md) cleared at 99.6 %, with corresponding [S510 Stopped - fault](../entities/status-code/s510.md) END entries recorded between 20:49:12 and 20:55:06.[^c15][^c16][^c17][^c18]
- On 2026-06-06, A6101 Grid voltage out of range alarms were raised across [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) with value 87.2 %, accompanied by S510 Stopped - fault START entries; later A6101 clear entries showed value 99.6 % and S510 END entries.[^c19][^c20][^c21][^c22][^c23][^c24]
- On 2026-06-18, A6101 Grid voltage out of range alarms were raised on WTG-01 through WTG-12 at 89.2 %, and the alarms later cleared at 99.6 % with S510 Stopped - fault statuses ending between [WTG-06](../entities/asset/wtg-06.md) at 14:15:04 and WTG-12 at 14:20:10.[^c25][^c26][^c27][^c28][^c29][^c30][^c31][^c32][^c33][^c34][^c35][^c36][^c37][^c38][^c39][^c40]
- On 2026-08-02, A6101 Grid voltage out of range was raised for WTG-01 through WTG-12 with value 89.3 %, S510 Stopped - fault started, then the A6101 alarms cleared at 99.6 % and S510 ended.[^c41][^c42][^c43][^c44][^c45][^c46]
- On 2026-08-21, WTG-01 through WTG-12 raised A6101 Grid voltage out of range at 87.8 %, entered S510 Stopped - fault, then cleared A6101 at 99.6 % and ended S510.[^c47][^c48][^c49][^c50][^c51][^c52][^c53][^c54]

## Contradictions

No contradictions were found between current sources.

## Superseded information

No superseded information.

## Sources consulted

- [Curtailment instruction CPL-CI-2026-018](../sources/cpl-ci-2026-018-grid-curtailment-instruction.md): current, authority 9, dated 2026-07-02
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../sources/asset-register-2026.md): current, authority 6, dated 2026-01-12
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md): current, authority 5, date unknown
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md): current, authority 4, dated 2026-06-18
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../sources/onboarding-and-site-rules.md): current, authority 4, dated 2025-02-03
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../sources/site-layout-plan.md): current, authority 4, date unknown

## Related

- Assets: [MM-01 met mast](../entities/asset/mm-01.md), [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil filter element](../entities/component/oil-filter.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [yaw system](../entities/component/yaw-system.md)
- Spare part: [FGT-P-22328](../entities/part/fgt-p-22328.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md)
- Alarm codes: [A1001 Emergency stop activated](../entities/alarm-code/a1001.md), [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md), [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md), [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md), [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md), [A4105 Pitch system fault](../entities/alarm-code/a4105.md), [A5001 Yaw misalignment](../entities/alarm-code/a5001.md), [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Status codes: [S200 Ready - low wind](../entities/status-code/s200.md), [S310 Maintenance mode](../entities/status-code/s310.md), [S420 Curtailed - environmental condition](../entities/status-code/s420.md), [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md), [S510 Stopped - fault](../entities/status-code/s510.md), [S600 Stopped - icing](../entities/status-code/s600.md)
- Procedures: [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A1001 Emergency stop activated](../entities/alarm-code/a1001.md)
- [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md)
- [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md)
- [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md)
- [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md)
- [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- [A4105 Pitch system fault](../entities/alarm-code/a4105.md)
- [A5001 Yaw misalignment](../entities/alarm-code/a5001.md)
- [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md)
- [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../sources/asset-register-2026.md)
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Curtailment instruction CPL-CI-2026-018](../sources/cpl-ci-2026-018-grid-curtailment-instruction.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [gearbox](../entities/component/gearbox.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [MM-01 met mast](../entities/asset/mm-01.md)
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../sources/onboarding-and-site-rules.md)
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../sources/site-layout-plan.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [S200 Ready - low wind](../entities/status-code/s200.md)
- [S310 Maintenance mode](../entities/status-code/s310.md)
- [S420 Curtailed - environmental condition](../entities/status-code/s420.md)
- [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md)
- [S510 Stopped - fault](../entities/status-code/s510.md)
- [S600 Stopped - icing](../entities/status-code/s600.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)
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

[^c1]: [Curtailment instruction CPL-CI-2026-018 — p. 1](../evidence/src-867a6c78f5b5/p0001.md) · ✓ quote verified
[^c2]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Other assets", row 2](../evidence/src-b342a2d5bfdf/sheet-other-assets-r0002-r0002.md) · table
[^c3]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1202](../evidence/src-36f5b999211a/r1202-r1202.md) · table
[^c4]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1213](../evidence/src-36f5b999211a/r1213-r1213.md) · table
[^c5]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1214](../evidence/src-36f5b999211a/r1214-r1214.md) · table
[^c6]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1225](../evidence/src-36f5b999211a/r1225-r1225.md) · table
[^c7]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1230](../evidence/src-36f5b999211a/r1230-r1230.md) · table
[^c8]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1257](../evidence/src-36f5b999211a/r1257-r1257.md) · table
[^c9]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1267](../evidence/src-36f5b999211a/r1267-r1267.md) · table
[^c10]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1296](../evidence/src-36f5b999211a/r1296-r1296.md) · table
[^c11]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 19](../evidence/src-a14b304454ed/img-b19.md) · OCR
[^c12]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 24](../evidence/src-a14b304454ed/img-b24.md) · OCR
[^c13]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 2](../evidence/src-e7cd20fa7984/slide-02.md) · ✓ quote verified
[^c14]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 18](../evidence/src-15df96905f07/para-0018.md) · ✓ quote verified
[^c15]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 236](../evidence/src-36f5b999211a/r0236-r0236.md) · table
[^c16]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 237](../evidence/src-36f5b999211a/r0237-r0237.md) · table
[^c17]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 258](../evidence/src-36f5b999211a/r0258-r0258.md) · table
[^c18]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 259](../evidence/src-36f5b999211a/r0259-r0259.md) · table
[^c19]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 690](../evidence/src-36f5b999211a/r0690-r0690.md) · table
[^c20]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 691](../evidence/src-36f5b999211a/r0691-r0691.md) · table
[^c21]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 712](../evidence/src-36f5b999211a/r0712-r0712.md) · table
[^c22]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 713](../evidence/src-36f5b999211a/r0713-r0713.md) · table
[^c23]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 714](../evidence/src-36f5b999211a/r0714-r0714.md) · table
[^c24]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 737](../evidence/src-36f5b999211a/r0737-r0737.md) · table
[^c25]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 864](../evidence/src-36f5b999211a/r0864-r0864.md) · table
[^c26]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 866](../evidence/src-36f5b999211a/r0866-r0866.md) · table
[^c27]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 868](../evidence/src-36f5b999211a/r0868-r0868.md) · table
[^c28]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 870](../evidence/src-36f5b999211a/r0870-r0870.md) · table
[^c29]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 872](../evidence/src-36f5b999211a/r0872-r0872.md) · table
[^c30]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 874](../evidence/src-36f5b999211a/r0874-r0874.md) · table
[^c31]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 876](../evidence/src-36f5b999211a/r0876-r0876.md) · table
[^c32]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 878](../evidence/src-36f5b999211a/r0878-r0878.md) · table
[^c33]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 880](../evidence/src-36f5b999211a/r0880-r0880.md) · table
[^c34]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 882](../evidence/src-36f5b999211a/r0882-r0882.md) · table
[^c35]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 884](../evidence/src-36f5b999211a/r0884-r0884.md) · table
[^c36]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 886](../evidence/src-36f5b999211a/r0886-r0886.md) · table
[^c37]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 888](../evidence/src-36f5b999211a/r0888-r0888.md) · table
[^c38]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 889](../evidence/src-36f5b999211a/r0889-r0889.md) · table
[^c39]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 909](../evidence/src-36f5b999211a/r0909-r0909.md) · table
[^c40]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 911](../evidence/src-36f5b999211a/r0911-r0911.md) · table
[^c41]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1437](../evidence/src-36f5b999211a/r1437-r1437.md) · table
[^c42]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1459](../evidence/src-36f5b999211a/r1459-r1459.md) · table
[^c43]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1461](../evidence/src-36f5b999211a/r1461-r1461.md) · table
[^c44]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1482](../evidence/src-36f5b999211a/r1482-r1482.md) · table
[^c45]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1466](../evidence/src-36f5b999211a/r1466-r1466.md) · table
[^c46]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1484](../evidence/src-36f5b999211a/r1484-r1484.md) · table
[^c47]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1714](../evidence/src-36f5b999211a/r1714-r1714.md) · table
[^c48]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1736](../evidence/src-36f5b999211a/r1736-r1736.md) · table
[^c49]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1715](../evidence/src-36f5b999211a/r1715-r1715.md) · table
[^c50]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1737](../evidence/src-36f5b999211a/r1737-r1737.md) · table
[^c51]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1738](../evidence/src-36f5b999211a/r1738-r1738.md) · table
[^c52]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1758](../evidence/src-36f5b999211a/r1758-r1758.md) · table
[^c53]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1740](../evidence/src-36f5b999211a/r1740-r1740.md) · table
[^c54]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1761](../evidence/src-36f5b999211a/r1761-r1761.md) · table
