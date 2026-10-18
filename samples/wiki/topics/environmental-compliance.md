---
id: topic:environmental-compliance
type: topic
title: Environmental permit and night curtailment
summary: This page covers environmental permit conditions and turbine curtailment for Quellmoor Ridge Wind Farm.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- environmental-compliance
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: environmental-compliance
sources:
- src-15df96905f07
- src-1d8dff18b801
- src-36f5b999211a
- src-867a6c78f5b5
- src-a011da5de982
- src-a14b304454ed
- src-a20331a5431f
- src-a7e8d332dafd
- src-e7cd20fa7984
confidence: high
contradictions: 0
superseded_claims: 0
---

# Environmental permit and night curtailment

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers environmental permit conditions and turbine curtailment for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).

## Overview

Environmental permit EP-2018-0417 applies to [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), is held by [Contoso Renewables](../entities/organisation/contoso-renewables.md), and was issued by the [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md).[^c1] The permitted installation comprises turbines [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) with a total capacity of 38.4 MW.[^c1] The permit sets requirements for noise, shadow flicker, bat monitoring and curtailment, ice, spill control, oil storage, waste oil, reporting, and environmental incident notification.[^c1][^c2] A July 2026 grid curtailment instruction limited active power export at the connection point to 20 MW on 14, 15, and 16 July 2026, and SCADA records show grid-operator curtailment at 20.0 MW on those dates.[^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11]

## Permit governance

- Environmental permit EP-2018-0417 is a consolidated version incorporating variation 1 and variation 2.[^c1]
- The original permit issue date was 2018-11-20; variation 1 concerned automatic shadow flicker control, and variation 2 concerned bat protection curtailment under condition 7.3.[^c1]
- The installation must be operated as described in the permit application, the Authority must be notified before any change to the number or type of turbines, and a copy of the permit must be kept at the site.[^c1]
- The permit is signed for the [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md) by Siobhan Carrick, Permitting Officer, on 2024-12-10.[^c2]

## Noise, shadow flicker, and ice

- Noise from the wind farm at dwellings of Quellmoor must not exceed 40 dB(A) LA90, 10 minutes at night between 23:00 and 07:00, and must not exceed 45 dB(A) during the day, at hub-height wind speeds up to 12 m/s.[^c1]
- Shadow flicker at any dwelling must not exceed 30 hours per year and 30 minutes per day, and automatic shadow flicker control must be used.[^c1]
- Turbines must stop automatically when ice is detected on rotor blades and may restart only when the ice has gone.[^c2]
- Warning signs about falling ice must be placed at all access points at a distance of 300 m from the turbines from November to March.[^c2]
- The site rules state that automatic turbine stops for permit reasons must never be overridden.[^c12]

## Bat protection curtailment

- Bat activity must be monitored at the nacelle of [WTG-04](../entities/asset/wtg-04.md) with an acoustic detector from April to October each year, and monitoring results must be reported in the annual environmental report.[^c2]
- From 1 June to 31 August each year, [WTG-03](../entities/asset/wtg-03.md), WTG-04, and [WTG-05](../entities/asset/wtg-05.md) must be stopped between 22:00 and 05:00 local time whenever hub-height wind speed is below 6.0 m/s and air temperature is 10 °C or higher.[^c2]
- Bat protection curtailment must be implemented automatically by the turbine control system, each curtailment period must be recorded in the turbine event log, and curtailment records must be kept for 5 years.[^c2]
- Curtailment records must be summarised in an annual report submitted to the Authority by 31 January of the following year.[^c2]
- The Authority may adjust the condition 7.3 thresholds after three years of monitoring data.[^c2]
- Variation 2 was justified by the presence of a protected bat species maternity roost in Skelvane Wood, east of WTG-03, WTG-04, and WTG-05, with foraging near the turbines on warm, calm summer nights.[^c2]
- The site layout plan labels WTG-03 to WTG-05 as an environmental permit curtailment group and labels Skelvane Wood as a bat roost.[^c13][^c14]
- The monthly O&M review recorded that the bat protection curtailment season started on 1 June for WTG-03, WTG-04, and WTG-05 under permit condition 7.3, and that the curtailment settings were checked in the turbine controllers on 2026-05-28.[^c15]

## Curtailment records

- SCADA records show [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), and [WTG-05](../entities/asset/wtg-05.md) entering [S420 Curtailed - environmental condition](../entities/status-code/s420.md) around 22:00 on 2026-06-01 and ending the curtailment around 05:00 on 2026-06-02.[^c16][^c17][^c18][^c19][^c20][^c21]
- SCADA records show WTG-03, WTG-04, and WTG-05 entering S420 Curtailed - environmental condition at 22:00 on 2026-08-25 and ending the curtailment at 05:00 on 2026-08-26.[^c22][^c23][^c24][^c25][^c26][^c27]
- A shift handover for 2026-07-15 stated that WTG-03, WTG-04, and WTG-05 were expected to stop from 22:00 if wind remained low due to bat curtailment, and that this should not be reset.[^c28]
- A shift handover for 2026-07-29 stated that WTG-03, WTG-04, and WTG-05 were expected to have bat curtailment again at night due to low wind.[^c29]

## Grid operator curtailment

- Curtailment instruction CPL-CI-2026-018 was issued by [City Power & Light](../entities/organisation/city-power-and-light.md) Network Control for a planned network outage and was addressed to [Contoso Renewables](../entities/organisation/contoso-renewables.md) for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c3]
- The connection point is Skelvane 132 kV substation, circuit 2, and the reason for the instruction is planned maintenance of Skelvane 132 kV circuit 1 while the network runs on a single circuit.[^c3]
- Active power export at the connection point must be limited to 20 MW from 08:00 to 18:00 local time on 14, 15, and 16 July 2026.[^c3]
- When the limit ends, export must be restored with a ramp rate of at most 5 MW per minute.[^c3]
- The instruction had to be acknowledged within 48 hours, and Dario Penwarden acknowledged it for Contoso Renewables on 2026-07-02 at 14:40.[^c3]
- Export above the limit by more than 1 MW for more than 5 minutes will be reported, and Network Control may extend the outage with any extension confirmed by phone and in writing.[^c3]
- SCADA records show [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md) at 20.0 MW for [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) on 2026-07-14, 2026-07-15, and 2026-07-16.[^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11]
- The 2026-07-15 shift handover recorded grid curtailment as day 2 of 3 under CPL-CI-2026-018, with park export limited to 20 MW from 08:00 to 18:00 and all turbines returned to normal at 18:00.[^c28]

## Pollution, spills, and waste oil

- A spill kit must be kept in each turbine and in the O&M building.[^c2]
- Oil spills of more than 20 L outside a turbine must be reported to the Authority within 24 hours.[^c2]
- Oil drums must be stored in a bunded area with capacity of at least 110 % of the largest container or 25 % of total stored volume, whichever is larger.[^c2]
- Waste oil must be collected by a licensed carrier.[^c2]
- Incidents with an effect on the environment must be notified within 24 hours, and the annual environmental report must be submitted by 31 January.[^c2]
- The [gearbox](../entities/component/gearbox.md) oil grade change record identified hot-oil and spill controls including [SOP-GBX-010](../entities/procedure/sop-gbx-010.md), a spill kit, and draining between 40 and 60 °C.[^c30]
- The gearbox oil grade change record identified a waste-oil risk of 12 x 470 L of waste oil, controlled by using a licensed carrier and checking bund capacity.[^c31]

## Contradictions

No contradictions were found between current sources.

## Superseded information

No superseded information.

## Sources consulted

- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../sources/ep-2018-0417-environmental-permit-consolidated.md): current, authority 10, dated 2024-12-10
- [Curtailment instruction CPL-CI-2026-018](../sources/cpl-ci-2026-018-grid-curtailment-instruction.md): current, authority 9, dated 2026-07-02
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md): current, authority 8, dated 2025-06-18
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md): current, authority 5, date unknown
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md): current, authority 4, dated 2026-06-18
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../sources/onboarding-and-site-rules.md): current, authority 4, dated 2025-02-03
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../sources/site-layout-plan.md): current, authority 4, date unknown
- [Shift Handover for 2026-07-29 Day Shift](../sources/2026-07-29-shift-handover.md): current, authority 2, date unknown
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md): current, authority 2, date unknown

## Related

- Assets: [MM-01 met mast](../entities/asset/mm-01.md), [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [yaw system](../entities/component/yaw-system.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-20915](../entities/part/awi-20915.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [PWS-220-D208](../entities/part/pws-220-d208.md)
- Products: [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A1001 Emergency stop activated](../entities/alarm-code/a1001.md), [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md), [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md), [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md), [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md), [A4105 Pitch system fault](../entities/alarm-code/a4105.md), [A5001 Yaw misalignment](../entities/alarm-code/a5001.md), [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Status codes: [S200 Ready - low wind](../entities/status-code/s200.md), [S310 Maintenance mode](../entities/status-code/s310.md), [S420 Curtailed - environmental condition](../entities/status-code/s420.md), [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md), [S510 Stopped - fault](../entities/status-code/s510.md), [S600 Stopped - icing](../entities/status-code/s600.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md), [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)

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
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-20915](../entities/part/awi-20915.md)
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Curtailment instruction CPL-CI-2026-018](../sources/cpl-ci-2026-018-grid-curtailment-instruction.md)
- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [gearbox](../entities/component/gearbox.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [MM-01 met mast](../entities/asset/mm-01.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
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
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md)
- [Shift Handover for 2026-07-29 Day Shift](../sources/2026-07-29-shift-handover.md)
- [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
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

[^c1]: [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2) — p. 1](../evidence/src-a7e8d332dafd/p0001.md) · ✓ quote verified
[^c2]: [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2) — p. 2](../evidence/src-a7e8d332dafd/p0002.md) · ✓ quote verified
[^c3]: [Curtailment instruction CPL-CI-2026-018 — p. 1](../evidence/src-867a6c78f5b5/p0001.md) · ✓ quote verified
[^c4]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1202](../evidence/src-36f5b999211a/r1202-r1202.md) · table
[^c5]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1213](../evidence/src-36f5b999211a/r1213-r1213.md) · table
[^c6]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1214](../evidence/src-36f5b999211a/r1214-r1214.md) · table
[^c7]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1225](../evidence/src-36f5b999211a/r1225-r1225.md) · table
[^c8]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1230](../evidence/src-36f5b999211a/r1230-r1230.md) · table
[^c9]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1257](../evidence/src-36f5b999211a/r1257-r1257.md) · table
[^c10]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1267](../evidence/src-36f5b999211a/r1267-r1267.md) · table
[^c11]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1296](../evidence/src-36f5b999211a/r1296-r1296.md) · table
[^c12]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 10](../evidence/src-e7cd20fa7984/slide-10.md) · ✓ quote verified
[^c13]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 8](../evidence/src-a14b304454ed/img-b08.md) · OCR
[^c14]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 7](../evidence/src-a14b304454ed/img-b07.md) · OCR
[^c15]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 14](../evidence/src-15df96905f07/para-0014.md) · ✓ quote verified
[^c16]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 622](../evidence/src-36f5b999211a/r0622-r0622.md) · table
[^c17]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 623](../evidence/src-36f5b999211a/r0623-r0623.md) · table
[^c18]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 624](../evidence/src-36f5b999211a/r0624-r0624.md) · table
[^c19]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 625](../evidence/src-36f5b999211a/r0625-r0625.md) · table
[^c20]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 626](../evidence/src-36f5b999211a/r0626-r0626.md) · table
[^c21]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 627](../evidence/src-36f5b999211a/r0627-r0627.md) · table
[^c22]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1870](../evidence/src-36f5b999211a/r1870-r1870.md) · table
[^c23]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1871](../evidence/src-36f5b999211a/r1871-r1871.md) · table
[^c24]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1872](../evidence/src-36f5b999211a/r1872-r1872.md) · table
[^c25]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1873](../evidence/src-36f5b999211a/r1873-r1873.md) · table
[^c26]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1874](../evidence/src-36f5b999211a/r1874-r1874.md) · table
[^c27]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1875](../evidence/src-36f5b999211a/r1875-r1875.md) · table
[^c28]: [Shift handover - 2026-07-15 (day shift to night shift) — lines 11–14](../evidence/src-1d8dff18b801/l0011-l0014.md) · ✓ quote verified
[^c29]: [Shift Handover for 2026-07-29 Day Shift — lines 5–14](../evidence/src-a011da5de982/l0005-l0014.md) · ✓ quote verified
[^c30]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 4](../evidence/src-a20331a5431f/tbl-02-r0004-r0004.md) · table
[^c31]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 6](../evidence/src-a20331a5431f/tbl-02-r0006-r0006.md) · table
