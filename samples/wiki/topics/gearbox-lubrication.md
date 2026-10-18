---
id: topic:gearbox-lubrication
type: topic
title: Gearbox lubrication and oil changes
summary: This page covers gearbox lubricant requirements, oil-change procedures, level checks, maintenance tasks, and related condition findings.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- gearbox-lubrication
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: gearbox-lubrication
sources:
- src-0df0d0598e76
- src-1abc5aef1a40
- src-1b5b5135881d
- src-1c261d5b87b5
- src-36f5b999211a
- src-42566abae6ef
- src-70224c3b9c9f
- src-86cb00fd2f6b
- src-90ea27f71f0f
- src-990a047180b7
- src-9a6703e054dc
- src-9fd435ef5956
- src-a20331a5431f
- src-aba30cb7207f
- src-c4370c220559
- src-ecc004b57dd5
confidence: medium
contradictions: 2
superseded_claims: 4
---

# Gearbox lubrication and oil changes

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers [gearbox](../entities/component/gearbox.md) lubricant requirements, oil-change procedures, level checks, maintenance tasks, and related condition findings.

## Overview

The current site change record says the [gearbox](../entities/component/gearbox.md) oil change from [Proseware PWG 320](../entities/product/pwg-320.md) to [Proseware PWG 220](../entities/product/pwg-220.md) applies to [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md), and the service bulletin says the affected manual section is the lubrication section of LWS-MM-GBX-32 Rev. D.[^c1][^c2][^c3][^c4][^c5] For converted gearboxes, the procedure uses a 60 L PWG 220 flush, a 410 L PWG 220 final fill through a 10 micron filter cart, a GBX_TMIN_START setting of 5 °C, PWG 220 labelling, and a requirement that residual PWG 320 remain below 5 % of oil volume.[^c6][^c7][^c8][^c9] Routine gearbox lubrication maintenance includes oil sampling and laboratory analysis every 6 months, [oil filter element](../entities/component/oil-filter.md) replacement every 12 months, and gearbox oil changes every 5 years or on condition.[^c10][^c11][^c12] [WTG-07](../entities/asset/wtg-07.md) has a current gearbox condition issue: its oil analysis was ALERT, ferrous wear and particle count were above alert limits, and the related incident report says vibration remains above the alarm level until the bearing is replaced.[^c13][^c14]

## Applicability and document control

- [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) is categorized as recommended but mandatory to keep the [gearbox](../entities/component/gearbox.md) warranty, and it applies to [LT-32](../entities/product/lt-32.md) turbines delivered in CCV configuration with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes and to LT-32 standard turbines at sites where ambient temperature regularly falls below -20 °C.[^c1]
- For affected turbines, compliance with SB-LWS-2025-07 is required at the next scheduled oil change and no later than 2025-12-31.[^c1]
- MOC-2025-012 scopes the technical lubricant change to [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) and says [Litware](../entities/organisation/litware-wind-systems.md) support confirmed that SB-LWS-2025-07 applies to all 12 CCV turbines at [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c2][^c3][^c4][^c5]
- [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) Rev. B is effective from 2025-08-25, applies to WTG-01 through WTG-12 with Litware LT-32 CCV turbines and Fabrikam FGT-3200 gearboxes, and implements MOC-2025-012 and SB-LWS-2025-07 Rev. A.[^c15][^c16][^c17]
- The maintenance manual says Litware Wind Systems publishes gearbox chapter changes as service bulletins and that the bulletin register must be checked before planning gearbox work.[^c18]

## Lubricant specification and quantities

- The service bulletin changes affected turbines from [Proseware PWG 320](../entities/product/pwg-320.md) to [Proseware PWG 220](../entities/product/pwg-220.md) and from ISO VG 320 to ISO VG 220, while the total oil volume remains 410 L.[^c1]
- The Rev. D maintenance manual still lists Proseware PWG 320, ISO VG 320, with synthetic PAO base oil as the approved gear oil and states that the total oil volume is 410 L, made up of 330 L in the [gearbox](../entities/component/gearbox.md) sump and 80 L in the cooling and filter circuit.[^c19]
- Each SOP Rev. B oil change requires 470 L of Proseware PWG 220, consisting of 60 L for flushing and 410 L for filling, plus one [FGT-P-11872](../entities/part/fgt-p-11872.md) [oil filter element](../entities/component/oil-filter.md).[^c20][^c21]
- The maintenance manual says lubricants of different brands or viscosity grades must not be mixed, and SOP Rev. B says a converted gearbox must never be topped up with PWG 320.[^c19][^c9]
- The spare-parts snapshot lists [PWS-320-D208](../entities/part/pws-320-d208.md) as Proseware PWG 320 gear oil with a do-not-use note tied to MOC-2025-012.[^c22]

## Oil-change procedure and controls

- Before the oil circuit is opened, SOP Rev. B requires a permit to work, at least two technicians, no lone working in the nacelle, and isolation under [SOP-LOTO-001](../entities/procedure/sop-loto-001.md).[^c23][^c24]
- SOP Rev. B says the job must not start if the 10-minute mean wind speed exceeds 15 m/s, and hot-oil controls require chemical gloves, a face shield, long sleeves, and draining only between 40 and 60 °C.[^c25][^c26]
- Before draining, the turbine is stopped, lockout/tagout is applied with the rotor locked and drivetrain isolated, oil temperature is checked, and oil is drained between 40 and 60 °C.[^c27][^c28]
- The procedure takes a used-oil sample at the sampling valve, drains the [gearbox](../entities/component/gearbox.md) sump and cooling and filter circuit into waste containers, and gives the approximate drained volume as 410 L.[^c29][^c30]
- During the oil change, the [FGT-P-11872](../entities/part/fgt-p-11872.md) filter element is replaced, the filter housing cover screws are tightened to 85 Nm, and the drain plug is refitted with a new seal and tightened to 280 Nm.[^c31][^c32]
- After the flush and final fill, SOP Rev. B requires [running](../entities/status-code/s100.md) the electric oil pump for 15 minutes, checking all connections for leaks, and checking the oil level at the sight glass after 20 minutes of standstill.[^c6][^c7][^c33][^c34]
- SOP Rev. B requires a reference oil sample after 24 hours of operation, recording quantities and batch numbers in the work order, sending the completion form to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) within 30 days, and storing waste oil in the bunded store for licensed-carrier collection.[^c35][^c36][^c37]

## Oil level checks and top-up

- SOP Rev. B says the oil level is checked at the sight glass after 20 minutes of standstill according to [SPL-012](../entities/procedure/spl-012.md) and topped up only with [PWG 220](../entities/product/pwg-220.md).[^c34]
- SPL-012 says the [gearbox](../entities/component/gearbox.md) oil level is read at the generator-side sight glass and must be between MIN and MAX.[^c38]
- SPL-012 says top-up is only permitted with PWG 220 through the 10 micron filter cart and that [PWG 320](../entities/product/pwg-320.md) must not be used.[^c38]
- SPL-012 says that if the level is below MIN, the turbine must not be restarted and the condition is reported to the O&M Supervisor because of the risk of alarm [A2130](../entities/alarm-code/a2130.md).[^c39]

## Temperatures, filters, and alarms

- The manual gives normal oil sump temperature in operation as 50 to 65 °C and states that warning [A2101](../entities/alarm-code/a2101.md) is set at 75 °C and trip [A2102](../entities/alarm-code/a2102.md) is set at 82 °C.[^c19]
- [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) says the A2101 and A2102 temperature thresholds remain 75 °C and 82 °C after the viscosity-grade change.[^c1]
- The manual says the oil passes through a 10 micron inline filter and an air/[oil cooler](../entities/component/oil-cooler.md) with an electric fan, and that the thermostatic valve sends oil through the cooler above 45 °C.[^c40]
- The manual says the [FGT-P-11872](../entities/part/fgt-p-11872.md) filter element must be replaced every 12 months or at alarm [A2140](../entities/alarm-code/a2140.md), and that A2140 is gearbox oil filter differential pressure high at 2.5 bar.[^c19][^c41]
- The manual says [A2120](../entities/alarm-code/a2120.md) is gearbox oil pressure low at 0.8 bar and can be caused by cold oil at start-up, pump fault, or a blocked filter.[^c41]

## Oil analysis and condition monitoring

- The maintenance manual gives oil analysis alert and alarm limits for iron, copper, silicon, water, viscosity change, PQ index, and cleanliness ISO 4406.[^c42]
- For output-stage HSS bearings, the maintenance manual gives velocity RMS limits of 3.5 mm/s alert and 4.5 mm/s alarm.[^c42]
- [WTG-07](../entities/asset/wtg-07.md) oil sample TR-26-11873 used [Proseware PWG 220](../entities/product/pwg-220.md), ISO VG 220, and was sampled on 2026-06-10 from the sampling valve with oil at operating temperature.[^c13]
- The WTG-07 oil report says viscosity and water content were normal for PWG 220, but iron, PQ index, and particle count were at ALERT status.[^c13]
- The WTG-07 oil report interprets large ferrous particles with normal copper as indicating rolling-element bearing distress rather than gear wear, and recommends reviewing output-stage bearing vibration trends, endoscope inspection of HSS bearings, filter replacement, and resampling within 30 days.[^c13]

## WTG-07 overheating incident

- Between 2026-04-09 and 2026-06-21, [WTG-07](../entities/asset/wtg-07.md) logged 27 [A2101](../entities/alarm-code/a2101.md) warnings at 75 °C and two [A2102](../entities/alarm-code/a2102.md) trips at 82 °C, while no other turbine logged an A2101 warning in that period.[^c43]
- The WTG-07 [HSS bearing](../entities/component/hss-bearing.md) vibration on the [generator](../entities/component/generator.md) side rose from 2.1 mm/s RMS to 5.2 mm/s RMS and exceeded the 4.5 mm/s alarm level.[^c44]
- The incident report says the oil overheated because the [oil cooler](../entities/component/oil-cooler.md) did not reject enough heat at high load, the cooler fan ran at reduced speed, and the radiator fins were about 40 % blocked by insects and pollen.[^c45][^c46]
- The incident report identifies the root cause as missing preventive maintenance of the oil cooler, allowing fan motor bearing failure and radiator fouling to reduce cooling capacity.[^c47]
- Completed corrective actions on 2026-06-24 were replacing [oil cooler fan motor](../entities/component/cooler-fan-motor.md) [LWS-P-30418](../entities/part/lws-p-30418.md) and cleaning the oil cooler radiator, and verification reports no A2101 warning on WTG-07 since 2026-06-24.[^c48][^c49][^c14]
- Replacement of WTG-07 generator-side HSS bearing [FGT-P-22328](../entities/part/fgt-p-22328.md) is waiting for parts, and the 8D remains open until the bearing replacement and an oil sample 500 operating hours after the bearing replacement.[^c50][^c51]

## Maintenance plan and spares

- Maintenance Plan 2026 issue 2 added task MP-GBX-07 for [oil cooler](../entities/component/oil-cooler.md) radiator cleaning and fan current check on all turbines after INC-2026-006.[^c52][^c53]
- The plan schedules [gearbox](../entities/component/gearbox.md) oil sampling and laboratory analysis every 6 months, [oil filter element](../entities/component/oil-filter.md) replacement every 12 months, gearbox oil changes every 5 years or on condition, and monthly vibration trend review.[^c10][^c11][^c12][^c54]
- For [WTG-07](../entities/asset/wtg-07.md), the maintenance plan records oil analysis report TR-OA-2026-0614 with [PWG 220](../entities/product/pwg-220.md) oil, Fe 64 ppm, PQ index 112, ALERT condition, and next sample due 2026-07-10 with resampling within 30 days.[^c55]
- The spare-parts snapshot shows generator-side [HSS bearing](../entities/component/hss-bearing.md) [FGT-P-22328](../entities/part/fgt-p-22328.md) as a critical item below minimum stock, with 0 pieces on hand, a minimum of 1 piece, 2 pieces on order under PO-76994, and expected delivery on 2026-09-25.[^c56][^c57]
- The spare-parts snapshot shows [oil cooler fan motor](../entities/component/cooler-fan-motor.md) [LWS-P-30418](../entities/part/lws-p-30418.md) as a critical item below minimum stock, with 1 piece on hand, a minimum of 2 pieces, and 2 pieces on order under PO-77102 for expected delivery on 2026-08-14.[^c56][^c58]

## Conversion completion status

- The work-orders export records a completed high-priority modification campaign for [gearbox](../entities/component/gearbox.md) oil conversion from [PWG 320](../entities/product/pwg-320.md) to [PWG 220](../entities/product/pwg-220.md) with a 60 L flush for [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) under MOC-2025-012.[^c59][^c60][^c61][^c62][^c63][^c64][^c65][^c66][^c67][^c68][^c69][^c70]
- The [WTG-09](../entities/asset/wtg-09.md) gearbox oil conversion work order was deferred because the access road was closed by snow on 2025-11-24 and was completed on 2026-01-20.[^c67]

## Contradictions

- **Use of [SPL-012](../entities/procedure/spl-012.md) for oil-level checks.** [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md) states: After 20 minutes of standstill, the oil level is checked at the sight glass according to SPL-012 and topped up only with [PWG 220](../entities/product/pwg-220.md).[^c34] (authority 7, dated 2025-08-25). [SPL-012 Gearbox Oil Level Check](../sources/spl-012-gearbox-oil-level-check.md) states: The lesson is marked fictional and not for operational use.[^c71] (authority 6, dated 2025-09-29). Resolution rule (authority, then recency): [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) Rev. B - [Gearbox](../entities/component/gearbox.md) oil change prevails (authority 7 vs 6).
- **PO-76994 delivery timing for HSS bearings [FGT-P-22328](../entities/part/fgt-p-22328.md).** [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md) states: FGT-P-22328, the [HSS bearing](../entities/component/hss-bearing.md) on the [generator](../entities/component/generator.md) side for [FGT-3200](../entities/product/fgt-3200.md), is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c56][^c57] (authority 5, dated 2026-07-21). [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md) states: The two HSS bearings FGT-P-22328 from PO-76994 cannot be delivered in calendar week 39.[^c72] The new confirmed delivery window is calendar week 40, from 28.09.2026 to 02.10.2026.[^c72] (authority 3, date unknown). Resolution rule (authority, then recency): Spare Parts Stock Snapshot 2026-07-21 for [Quellmoor Ridge O&M Building](../entities/asset/om-building.md) prevails (authority 5 vs 3).

Resolution policy: When two current sources disagree, the source with the higher document-type authority wins (environmental permit 10; service bulletin and grid instruction 9; maintenance manual and management of change 8; procedures, laboratory and inspection reports 7). With equal authority the more recent source wins. A service bulletin that amends a manual section for some turbines is shown next to the manual value, with the turbines it applies to.

## Superseded information

- **SOP [gearbox](../entities/component/gearbox.md) oil specification and fill oil.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The specified new oil is [Proseware PWG 320](../entities/product/pwg-320.md) (ISO VG 320), with 410 L per turbine supplied as 2 drums [PWS-320-D208](../entities/part/pws-320-d208.md).[^c73] 410 L of Proseware PWG 320 is filled through a 10 micron filter cart.[^c74] Replacement: Each turbine requires 470 L of [Proseware PWG 220](../entities/product/pwg-220.md), consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of [PWS-220-D208](../entities/part/pws-220-d208.md).[^c20] The gearbox is filled with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c7] Revision B changed the oil to PWG 220 per MOC-2025-012 and [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md), added the flush step, and set a minimum start-up temperature of +5 °C.[^c75] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **SOP minimum oil sump temperature before start-up.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: After lockout removal and restart, oil temperature is watched during the first hour, and the turbine starts only when the oil sump has reached +10 °C.[^c76] Replacement: Controller parameter GBX_TMIN_START must be set to 5 °C, and the gearbox filler must be labelled PWG 220.[^c8] On restart, oil temperature is watched during the first hour, and the turbine starts only once the oil sump has reached +5 °C.[^c77] Revision B changed the oil to PWG 220 per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c75] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **SOP oil-change parts quantity.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The specified new oil is Proseware PWG 320 (ISO VG 320), with 410 L per turbine supplied as 2 drums PWS-320-D208.[^c73] One [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) is required.[^c78] Replacement: Each turbine requires 470 L of Proseware PWG 220, consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of PWS-220-D208.[^c20] One oil filter element FGT-P-11872 is required.[^c21] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **SOP revision status.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) is a standard operating procedure, Revision A, effective 2023-04-03.[^c79][^c80][^c81][^c82] Revision A is the first issue and is associated with PWG 320.[^c83] Replacement: SOP-GBX-010 is Revision B and is effective from 2025-08-25.[^c15] Revision B supersedes SOP-GBX-010 Rev. A and implements MOC-2025-012 and SB-LWS-2025-07 Rev. A.[^c17] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).

## Sources consulted

- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md): current, authority 9, dated 2025-03-14
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md): current, authority 8, dated 2024-03-15
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md): current, authority 8, dated 2025-06-18
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md): current, authority 7, dated 2026-06-17
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md): current, authority 7, dated 2025-08-25
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md): current, authority 6, dated 2026-07-10
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md): current, authority 6, dated 2026-07-01
- [SPL-012 Gearbox Oil Level Check](../sources/spl-012-gearbox-oil-level-check.md): current, authority 6, dated 2025-09-29
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md): current, authority 5, date unknown
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md): current, authority 5, dated 2026-07-21
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md): current, authority 5, date unknown
- [Gearbox Fundamentals for Wind Technicians](../sources/gearbox-fundamentals.md): current, authority 4, dated 2025-10-20
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md): current, authority 3, dated 2025-05-20
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md): current, authority 3, date unknown
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md): current, authority 2, date unknown
- [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md): superseded, authority 7, dated 2023-04-03

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [IMS bearing](../entities/component/ims-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [planetary stage](../entities/component/planetary-stage.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [service lift](../entities/component/service-lift.md), [slip ring](../entities/component/slip-ring.md), [yaw system](../entities/component/yaw-system.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-20915](../entities/part/awi-20915.md), [AWI-31007](../entities/part/awi-31007.md), [AWI-40210](../entities/part/awi-40210.md), [AWI-40388](../entities/part/awi-40388.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-11880](../entities/part/fgt-p-11880.md), [FGT-P-13010](../entities/part/fgt-p-13010.md), [FGT-P-14002](../entities/part/fgt-p-14002.md), [FGT-P-21904](../entities/part/fgt-p-21904.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [FGT-P-22331](../entities/part/fgt-p-22331.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-30422](../entities/part/lws-p-30422.md), [LWS-P-41120](../entities/part/lws-p-41120.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [LWS-P-55031](../entities/part/lws-p-55031.md), [LWS-P-60455](../entities/part/lws-p-60455.md), [LWS-P-72210](../entities/part/lws-p-72210.md), [LWS-P-80031](../entities/part/lws-p-80031.md), [LWS-P-90012](../entities/part/lws-p-90012.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A1001 Emergency stop activated](../entities/alarm-code/a1001.md), [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md), [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2130 Gearbox oil level low](../entities/alarm-code/a2130.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md), [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md), [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md), [A4105 Pitch system fault](../entities/alarm-code/a4105.md), [A5001 Yaw misalignment](../entities/alarm-code/a5001.md), [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Status codes: [S200 Ready - low wind](../entities/status-code/s200.md), [S310 Maintenance mode](../entities/status-code/s310.md), [S420 Curtailed - environmental condition](../entities/status-code/s420.md), [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md), [S510 Stopped - fault](../entities/status-code/s510.md), [S600 Stopped - icing](../entities/status-code/s600.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletins: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md), [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Organisations: [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md), [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [A1001 Emergency stop activated](../entities/alarm-code/a1001.md)
- [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md)
- [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md)
- [A2130 Gearbox oil level low](../entities/alarm-code/a2130.md)
- [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md)
- [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md)
- [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- [A4105 Pitch system fault](../entities/alarm-code/a4105.md)
- [A5001 Yaw misalignment](../entities/alarm-code/a5001.md)
- [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md)
- [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md)
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-20915](../entities/part/awi-20915.md)
- [AWI-31007](../entities/part/awi-31007.md)
- [AWI-40210](../entities/part/awi-40210.md)
- [AWI-40388](../entities/part/awi-40388.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-11880](../entities/part/fgt-p-11880.md)
- [FGT-P-13010](../entities/part/fgt-p-13010.md)
- [FGT-P-14002](../entities/part/fgt-p-14002.md)
- [FGT-P-21904](../entities/part/fgt-p-21904.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [FGT-P-22331](../entities/part/fgt-p-22331.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox Fundamentals for Wind Technicians](../sources/gearbox-fundamentals.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
- [IMS bearing](../entities/component/ims-bearing.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-30422](../entities/part/lws-p-30422.md)
- [LWS-P-41120](../entities/part/lws-p-41120.md)
- [LWS-P-51207](../entities/part/lws-p-51207.md)
- [LWS-P-55031](../entities/part/lws-p-55031.md)
- [LWS-P-60455](../entities/part/lws-p-60455.md)
- [LWS-P-72210](../entities/part/lws-p-72210.md)
- [LWS-P-80031](../entities/part/lws-p-80031.md)
- [LWS-P-90012](../entities/part/lws-p-90012.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [pitch bearing](../entities/component/pitch-bearing.md)
- [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md)
- [planetary stage](../entities/component/planetary-stage.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [PWS-320-D208](../entities/part/pws-320-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [S200 Ready - low wind](../entities/status-code/s200.md)
- [S310 Maintenance mode](../entities/status-code/s310.md)
- [S420 Curtailed - environmental condition](../entities/status-code/s420.md)
- [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md)
- [S510 Stopped - fault](../entities/status-code/s510.md)
- [S600 Stopped - icing](../entities/status-code/s600.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [service lift](../entities/component/service-lift.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md)
- [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md)
- [SPL-012 Gearbox Oil Level Check](../sources/spl-012-gearbox-oil-level-check.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)
- [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md)
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

[^c1]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 1](../evidence/src-c4370c220559/p0001.md) · ✓ quote verified
[^c2]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 3](../evidence/src-a20331a5431f/tbl-01-r0003-r0003.md) · table
[^c3]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 4](../evidence/src-a20331a5431f/tbl-01-r0004-r0004.md) · table
[^c4]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 5](../evidence/src-a20331a5431f/tbl-01-r0005-r0005.md) · table
[^c5]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 4](../evidence/src-a20331a5431f/para-0004.md) · ✓ quote verified
[^c6]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 34](../evidence/src-70224c3b9c9f/para-0034.md) · ✓ quote verified
[^c7]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 35](../evidence/src-70224c3b9c9f/para-0035.md) · ✓ quote verified
[^c8]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 38](../evidence/src-70224c3b9c9f/para-0038.md) · ✓ quote verified
[^c9]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 42](../evidence/src-70224c3b9c9f/para-0042.md) · ✓ quote verified
[^c10]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 2](../evidence/src-aba30cb7207f/sheet-tasks-r0002-r0002.md) · table
[^c11]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 3](../evidence/src-aba30cb7207f/sheet-tasks-r0003-r0003.md) · table
[^c12]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 4](../evidence/src-aba30cb7207f/sheet-tasks-r0004-r0004.md) · table
[^c13]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 1](../evidence/src-990a047180b7/p0001.md) · ✓ quote verified
[^c14]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 24](../evidence/src-86cb00fd2f6b/para-0024.md) · ✓ quote verified
[^c15]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 2](../evidence/src-70224c3b9c9f/para-0002.md) · ✓ quote verified
[^c16]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 1, row 7](../evidence/src-70224c3b9c9f/tbl-01-r0007-r0007.md) · table
[^c17]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 3](../evidence/src-70224c3b9c9f/para-0003.md) · ✓ quote verified
[^c18]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 1](../evidence/src-1c261d5b87b5/p0001.md) · ✓ quote verified
[^c19]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 3](../evidence/src-1c261d5b87b5/p0003.md) · ✓ quote verified
[^c20]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 22](../evidence/src-70224c3b9c9f/para-0022.md) · ✓ quote verified
[^c21]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 23](../evidence/src-70224c3b9c9f/para-0023.md) · ✓ quote verified
[^c22]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 19](../evidence/src-42566abae6ef/sheet-stock-r0019-r0019.md) · table
[^c23]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 16](../evidence/src-70224c3b9c9f/para-0016.md) · ✓ quote verified
[^c24]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 17](../evidence/src-70224c3b9c9f/para-0017.md) · ✓ quote verified
[^c25]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 18](../evidence/src-70224c3b9c9f/para-0018.md) · ✓ quote verified
[^c26]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 19](../evidence/src-70224c3b9c9f/para-0019.md) · ✓ quote verified
[^c27]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 27](../evidence/src-70224c3b9c9f/para-0027.md) · ✓ quote verified
[^c28]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 28](../evidence/src-70224c3b9c9f/para-0028.md) · ✓ quote verified
[^c29]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 29](../evidence/src-70224c3b9c9f/para-0029.md) · ✓ quote verified
[^c30]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 30](../evidence/src-70224c3b9c9f/para-0030.md) · ✓ quote verified
[^c31]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 32](../evidence/src-70224c3b9c9f/para-0032.md) · ✓ quote verified
[^c32]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 33](../evidence/src-70224c3b9c9f/para-0033.md) · ✓ quote verified
[^c33]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 36](../evidence/src-70224c3b9c9f/para-0036.md) · ✓ quote verified
[^c34]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 37](../evidence/src-70224c3b9c9f/para-0037.md) · ✓ quote verified
[^c35]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 40](../evidence/src-70224c3b9c9f/para-0040.md) · ✓ quote verified
[^c36]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 41](../evidence/src-70224c3b9c9f/para-0041.md) · ✓ quote verified
[^c37]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 44](../evidence/src-70224c3b9c9f/para-0044.md) · ✓ quote verified
[^c38]: [SPL-012 Gearbox Oil Level Check — slide 2](../evidence/src-9a6703e054dc/slide-02.md) · ✓ quote verified
[^c39]: [SPL-012 Gearbox Oil Level Check — slide 3](../evidence/src-9a6703e054dc/slide-03.md) · ✓ quote verified
[^c40]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../evidence/src-1c261d5b87b5/p0002.md) · ✓ quote verified
[^c41]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../evidence/src-1c261d5b87b5/p0005.md) · ✓ quote verified
[^c42]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 4](../evidence/src-1c261d5b87b5/p0004.md) · ✓ quote verified
[^c43]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 6](../evidence/src-86cb00fd2f6b/para-0006.md) · ✓ quote verified
[^c44]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 7](../evidence/src-86cb00fd2f6b/para-0007.md) · ✓ quote verified
[^c45]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 12](../evidence/src-86cb00fd2f6b/para-0012.md) · ✓ quote verified
[^c46]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 13](../evidence/src-86cb00fd2f6b/para-0013.md) · ✓ quote verified
[^c47]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 17](../evidence/src-86cb00fd2f6b/para-0017.md) · ✓ quote verified
[^c48]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 2](../evidence/src-86cb00fd2f6b/tbl-02-r0002-r0002.md) · table
[^c49]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 3](../evidence/src-86cb00fd2f6b/tbl-02-r0003-r0003.md) · table
[^c50]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 5](../evidence/src-86cb00fd2f6b/tbl-02-r0005-r0005.md) · table
[^c51]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 26](../evidence/src-86cb00fd2f6b/para-0026.md) · ✓ quote verified
[^c52]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Revision log", row 3](../evidence/src-aba30cb7207f/sheet-revision-log-r0003-r0003.md) · table
[^c53]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 8](../evidence/src-aba30cb7207f/sheet-tasks-r0008-r0008.md) · table
[^c54]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 7](../evidence/src-aba30cb7207f/sheet-tasks-r0007-r0007.md) · table
[^c55]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 8](../evidence/src-aba30cb7207f/sheet-oil-sampling-r0008-r0008.md) · table
[^c56]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 3](../evidence/src-42566abae6ef/sheet-about-r0003-r0003.md) · table
[^c57]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 2](../evidence/src-42566abae6ef/sheet-stock-r0002-r0002.md) · table
[^c58]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 9](../evidence/src-42566abae6ef/sheet-stock-r0009-r0009.md) · table
[^c59]: [Work Orders Export through 2026-08-31 — row 2](../evidence/src-9fd435ef5956/r0002-r0002.md) · table
[^c60]: [Work Orders Export through 2026-08-31 — row 3](../evidence/src-9fd435ef5956/r0003-r0003.md) · table
[^c61]: [Work Orders Export through 2026-08-31 — row 4](../evidence/src-9fd435ef5956/r0004-r0004.md) · table
[^c62]: [Work Orders Export through 2026-08-31 — row 5](../evidence/src-9fd435ef5956/r0005-r0005.md) · table
[^c63]: [Work Orders Export through 2026-08-31 — row 6](../evidence/src-9fd435ef5956/r0006-r0006.md) · table
[^c64]: [Work Orders Export through 2026-08-31 — row 7](../evidence/src-9fd435ef5956/r0007-r0007.md) · table
[^c65]: [Work Orders Export through 2026-08-31 — row 8](../evidence/src-9fd435ef5956/r0008-r0008.md) · table
[^c66]: [Work Orders Export through 2026-08-31 — row 9](../evidence/src-9fd435ef5956/r0009-r0009.md) · table
[^c67]: [Work Orders Export through 2026-08-31 — row 10](../evidence/src-9fd435ef5956/r0010-r0010.md) · table
[^c68]: [Work Orders Export through 2026-08-31 — row 11](../evidence/src-9fd435ef5956/r0011-r0011.md) · table
[^c69]: [Work Orders Export through 2026-08-31 — row 12](../evidence/src-9fd435ef5956/r0012-r0012.md) · table
[^c70]: [Work Orders Export through 2026-08-31 — row 13](../evidence/src-9fd435ef5956/r0013-r0013.md) · table
[^c71]: [SPL-012 Gearbox Oil Level Check — slide 1](../evidence/src-9a6703e054dc/slide-01.md) · ✓ quote verified
[^c72]: [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up — lines 8–11](../evidence/src-1abc5aef1a40/l0008-l0011.md) · ✓ quote verified
[^c73]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 19](../evidence/src-90ea27f71f0f/para-0019.md) · ✓ quote verified
[^c74]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 31](../evidence/src-90ea27f71f0f/para-0031.md) · ✓ quote verified
[^c75]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 2, row 3](../evidence/src-70224c3b9c9f/tbl-02-r0003-r0003.md) · table
[^c76]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 34](../evidence/src-90ea27f71f0f/para-0034.md) · ✓ quote verified
[^c77]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 39](../evidence/src-70224c3b9c9f/para-0039.md) · ✓ quote verified
[^c78]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 20](../evidence/src-90ea27f71f0f/para-0020.md) · ✓ quote verified
[^c79]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 2](../evidence/src-90ea27f71f0f/para-0002.md) · ✓ quote verified
[^c80]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 2](../evidence/src-90ea27f71f0f/tbl-01-r0002-r0002.md) · table
[^c81]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 3](../evidence/src-90ea27f71f0f/tbl-01-r0003-r0003.md) · table
[^c82]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 4](../evidence/src-90ea27f71f0f/tbl-01-r0004-r0004.md) · table
[^c83]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 2, row 2](../evidence/src-90ea27f71f0f/tbl-02-r0002-r0002.md) · table
