---
id: topic:gearbox-condition-monitoring
type: topic
title: Gearbox temperature, vibration and oil analysis
summary: This page covers gearbox lubrication, temperature alarms, cooling performance, vibration trends, oil analysis, and bearing condition monitoring for the LT-32 fleet.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- gearbox-condition-monitoring
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: gearbox-condition-monitoring
sources:
- src-15df96905f07
- src-1abc5aef1a40
- src-1b5b5135881d
- src-1c261d5b87b5
- src-1d8dff18b801
- src-32ed1eb40d24
- src-36f5b999211a
- src-42566abae6ef
- src-70224c3b9c9f
- src-86cb00fd2f6b
- src-90ea27f71f0f
- src-9107d71821bf
- src-990a047180b7
- src-9fd435ef5956
- src-a011da5de982
- src-a6c9699afa37
- src-aba30cb7207f
- src-b7a218719725
- src-c4370c220559
- src-ecc004b57dd5
confidence: medium
contradictions: 5
superseded_claims: 5
---

# Gearbox temperature, vibration and oil analysis

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers [gearbox](../entities/component/gearbox.md) lubrication, temperature alarms, cooling performance, vibration trends, oil analysis, and bearing condition monitoring for the [LT-32](../entities/product/lt-32.md) fleet.

## Overview

[SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) amends the [gearbox](../entities/component/gearbox.md) manual lubrication section for affected [LT-32 CCV](../entities/product/lt-32-ccv.md) turbines with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes by changing the gear oil from [Proseware PWG 320](../entities/product/pwg-320.md), ISO VG 320, to [Proseware PWG 220](../entities/product/pwg-220.md), ISO VG 220.[^c1] For affected turbines, the total oil volume remains 410 L, the minimum oil sump temperature before start-up changes to +5 °C, and [A2101](../entities/alarm-code/a2101.md) and [A2102](../entities/alarm-code/a2102.md) remain at 75 °C and 82 °C.[^c1] [WTG-07](../entities/asset/wtg-07.md) had repeated gearbox over-temperature alarms caused by inadequate oil-cooler heat rejection from reduced fan speed and radiator fouling, with generator-side [HSS bearing](../entities/component/hss-bearing.md) wear identified as a contributing factor.[^c2][^c3][^c4][^c5][^c6][^c7] WTG-07 oil analysis and vibration data show alert-level ferrous wear and HSS bearing vibration above the alarm level, and the bearing replacement remains open until parts are available.[^c8][^c9][^c10][^c11]

## Lubrication configuration and operating limits

- The [LT-32](../entities/product/lt-32.md) [gearbox](../entities/component/gearbox.md) is a [Fabrikam FGT-3200](../entities/product/fgt-3200.md) three-stage gearbox with one [planetary stage](../entities/component/planetary-stage.md) followed by two parallel helical stages, and it uses splash and forced lubrication with a shaft-driven pump for operation and an electric pump for start-up and flushing.[^c12]
- The lubrication circuit passes oil through a 10 micron inline filter and an air/[oil cooler](../entities/component/oil-cooler.md) with an electric fan, and a thermostatic valve sends oil through the cooler above 45 °C.[^c12]
- Three immersion heaters rated 3 x 1.5 kW warm the oil sump before a cold start.[^c12]
- Normal gearbox oil sump temperature in operation is 50 to 65 °C, while [A2101](../entities/alarm-code/a2101.md) is the oil sump temperature warning at 75 °C and [A2102](../entities/alarm-code/a2102.md) is the oil sump temperature trip at 82 °C.[^c13]
- The current SOP for [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) applies to [LT-32 CCV](../entities/product/lt-32-ccv.md) turbines with Fabrikam FGT-3200 gearboxes and requires converted gearboxes to be topped up only with [PWG 220](../entities/product/pwg-220.md), with residual [PWG 320](../entities/product/pwg-320.md) below 5 % of oil volume.[^c14][^c15]

## WTG-07 over-temperature and cooler corrective actions

- Between 2026-04-09 and 2026-06-21, [WTG-07](../entities/asset/wtg-07.md) logged 27 [A2101](../entities/alarm-code/a2101.md) warnings at 75 °C and two [A2102](../entities/alarm-code/a2102.md) trips at 82 °C, while no other turbine logged an A2101 warning in that period.[^c2]
- SCADA records show WTG-07 raised A2101 and then A2102 on 2026-05-30, and again raised A2101 and then A2102 on 2026-06-19.[^c16][^c17][^c18][^c19][^c20][^c21]
- The 8D report says the oil overheated because the [oil cooler](../entities/component/oil-cooler.md) did not reject enough heat at high load, the cooler fan ran at reduced speed, the radiator fins were about 40 % blocked by insects and pollen, and the fan motor bearing had failed.[^c3][^c4][^c5]
- Corrective actions completed on 2026-06-24 replaced the [oil cooler fan motor](../entities/component/cooler-fan-motor.md) and cleaned the oil cooler radiator, and verification reported no A2101 warning on WTG-07 since 2026-06-24.[^c22][^c23][^c11]
- The maintenance plan added task MP-GBX-07 for all turbines every 6 months to clean the oil cooler radiator and check fan current after INC-2026-006.[^c24][^c25]

## Oil analysis and bearing condition

- Oil analysis report TR-OA-2026-0614 is for [WTG-07](../entities/asset/wtg-07.md) main [gearbox](../entities/component/gearbox.md) FGT-3200-18-07752, using [Proseware PWG 220](../entities/product/pwg-220.md), ISO VG 220, in service since 2025-10-15.[^c8]
- The WTG-07 sample was reported with overall condition ALERT and action required.[^c8]
- The WTG-07 oil sample had normal viscosity, water, and total acid number results, but iron was 64 ppm, PQ index was 112, and particle count was 20/18/15, each reported with ALERT status where stated.[^c8]
- The oil report says ferrous wear increased sharply since the previous sample and interprets large ferrous particles with normal copper as rolling-element bearing distress rather than gear wear.[^c8]
- The oil report recommends reviewing output-stage bearing vibration trends, inspecting the HSS bearings by endoscope, replacing the filter element, and resampling within 30 days.[^c8]
- For output-stage HSS bearings, the maintenance manual sets velocity RMS limits at 3.5 mm/s alert and 4.5 mm/s alarm, and WTG-07 trend data rose from 2.1 mm/s RMS on 2026-01-05 to 5.7 mm/s RMS on 2026-08-31.[^c26][^c27][^c28]
- [WTG-02](../entities/asset/wtg-02.md) also has generator-side [HSS bearing](../entities/component/hss-bearing.md) spalling found by endoscope, and WO-26-0439 is waiting for part [FGT-P-22328](../entities/part/fgt-p-22328.md).[^c29][^c30]

## Monitoring intervals and alarm responses

- The maintenance manual sets inspection intervals of 6 months for visual inspection and leak check, 6 months for oil sampling and laboratory analysis, 24 months for endoscope inspection, continuous for vibration monitoring, 12 months for filter element replacement, and as required for [oil cooler](../entities/component/oil-cooler.md) radiator cleaning.[^c26]
- The 2026 maintenance plan schedules [gearbox](../entities/component/gearbox.md) oil sampling and laboratory analysis every 6 months, [oil filter element](../entities/component/oil-filter.md) replacement every 12 months, gearbox oil change every 5 years or on condition, and monthly vibration trend review.[^c31][^c32][^c33][^c34]
- For [A2101](../entities/alarm-code/a2101.md), the manual lists cooling, oil level, load or ambient-temperature, and bearing issues as possible causes, with checks including fan rotation and motor current, radiator cleaning, valve insert [LWS-P-30422](../entities/part/lws-p-30422.md), oil level, vibration trend, and an oil sample.[^c35]
- For [A2102](../entities/alarm-code/a2102.md), the turbine stops automatically, the cooling circuit is inspected before restart, and reset is not performed more than once without inspection.[^c35]
- For [A2110](../entities/alarm-code/a2110.md), possible causes are bearing damage or lubrication starvation, with vibration trend review and endoscope inspection of the bearing as checks.[^c35]
- For [A2140](../entities/alarm-code/a2140.md), possible causes are a clogged filter element or cold oil, and the action is to replace filter element [FGT-P-11872](../entities/part/fgt-p-11872.md).[^c35]

## Oil-change and conversion controls

- The current SOP requires a permit to work, at least two technicians, no lone working in the nacelle, and isolation according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) before the oil circuit is opened.[^c36][^c37]
- Hot-oil controls require chemical gloves, a face shield, long sleeves, and draining only between 40 and 60 °C, with a spill kit ready at the [gearbox](../entities/component/gearbox.md) and absorbent pads under every connection.[^c38][^c39]
- Each oil change under the current SOP requires 470 L of [Proseware PWG 220](../entities/product/pwg-220.md), made up of 60 L for flushing and 410 L for filling, plus one [FGT-P-11872](../entities/part/fgt-p-11872.md) [oil filter element](../entities/component/oil-filter.md).[^c40][^c41]
- The current SOP drains the gearbox sump and cooling and filter circuit, replaces filter element FGT-P-11872, flushes with 60 L of PWG 220 while [running](../entities/status-code/s100.md) the electric oil pump for 30 minutes, and fills with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c42][^c43][^c44][^c45]
- After filling, the electric oil pump is run for 15 minutes, connections are checked for leaks, the oil level is checked after 20 minutes of standstill, GBX_TMIN_START is set to 5 °C, and the filler is labelled PWG 220.[^c46][^c47][^c48]
- A reference oil sample is taken after 24 hours of operation, quantities and batch numbers are recorded in the work order, and the completion form is sent to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) within 30 days.[^c49][^c50]

## Spares and open bearing work

- WO-26-0412 for [WTG-07](../entities/asset/wtg-07.md) is waiting for parts to replace the generator-side [HSS bearing](../entities/component/hss-bearing.md) [FGT-P-22328](../entities/part/fgt-p-22328.md), and the work order remarks that vibration is above the 4.5 mm/s alarm level.[^c51]
- The 2026-07-21 stock snapshot lists FGT-P-22328 as a critical item below minimum stock, with 0 on hand, a minimum of 1, and 2 on order under PO-76994 with expected delivery on 2026-09-25.[^c52][^c53]
- A supplier note says the two FGT-P-22328 HSS bearings under PO-76994 cannot be delivered in calendar week 39 and gives a new confirmed delivery window of 2026-09-28 to 2026-10-02.[^c54]
- The [oil cooler fan motor](../entities/component/cooler-fan-motor.md) [LWS-P-30418](../entities/part/lws-p-30418.md) is also listed as a critical item below minimum stock, with 1 on hand, a minimum of 2, and 2 on order under PO-77102 for expected delivery on 2026-08-14.[^c52][^c55]

## Contradictions

- **Gear oil grade for affected [LT-32](../entities/product/lt-32.md) turbines with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: The document applies to LT-32 turbines of all variants with the Fabrikam FGT-3200 [gearbox](../entities/component/gearbox.md).[^c56] Only the lubricant listed in Table 4-2 is approved for the FGT-3200 gearbox, and lubricants of different brands or viscosity grades must not be mixed.[^c13] The approved gear oil is [Proseware PWG 320](../entities/product/pwg-320.md) with viscosity grade ISO VG 320 and synthetic PAO base oil.[^c13] (authority 8, dated 2024-03-15). [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md) states: The bulletin applies to LT-32 turbines delivered in CCV configuration with Fabrikam FGT-3200 gearboxes and to LT-32 standard turbines at sites where ambient temperature regularly falls below -20 °C.[^c1] The affected document is LWS-MM-GBX-32 Rev. D, section 4.2 on lubrication.[^c1] For affected turbines, the gear oil changes from Proseware PWG 320 to [Proseware PWG 220](../entities/product/pwg-220.md).[^c1] For affected turbines, the viscosity grade changes from ISO VG 320 to ISO VG 220.[^c1] (authority 9, dated 2025-03-14). Resolution rule (authority, then recency): [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A - Gearbox oil viscosity grade change for [LT-32 CCV](../entities/product/lt-32-ccv.md) turbines prevails (authority 9 vs 8).
- **Minimum oil sump temperature before start-up for affected gearboxes.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: Minimum oil sump temperature before start-up is +10 °C, with heaters on below +10 °C.[^c13] The turbine controller blocks drivetrain start until the oil sump reaches the minimum start-up temperature, and the start inhibit must not be bypassed.[^c13] (authority 8, dated 2024-03-15). [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md) states: The minimum oil sump temperature before start-up changes from +10 °C to +5 °C.[^c1] The controller parameter GBX_TMIN_START must be changed from 10 to 5 °C.[^c1] (authority 9, dated 2025-03-14). Resolution rule (authority, then recency): SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines prevails (authority 9 vs 8).
- **Oil-change lubricant and start-temperature setting for [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md).** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: The approved gear oil is Proseware PWG 320 with viscosity grade ISO VG 320 and synthetic PAO base oil.[^c13] Minimum oil sump temperature before start-up is +10 °C, with heaters on below +10 °C.[^c13] (authority 8, dated 2024-03-15). [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md) states: The procedure applies to WTG-01 to WTG-12 with Litware LT-32 CCV turbines and Fabrikam FGT-3200 gearboxes.[^c14] Each turbine requires 470 L of Proseware PWG 220, consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of [PWS-220-D208](../entities/part/pws-220-d208.md).[^c40] Controller parameter GBX_TMIN_START must be set to 5 °C, and the gearbox filler must be labelled PWG 220.[^c48] On restart, oil temperature is watched during the first hour, and the turbine starts only once the oil sump has reached +5 °C.[^c57] A converted gearbox must never be topped up with PWG 320, and residual PWG 320 must remain below 5 % of oil volume.[^c15] (authority 7, dated 2025-08-25). Resolution rule (authority, then recency): LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt prevails (authority 8 vs 7).
- **Expected delivery timing for [FGT-P-22328](../entities/part/fgt-p-22328.md) HSS bearings under PO-76994.** [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md) states: FGT-P-22328, the [HSS bearing](../entities/component/hss-bearing.md) on the [generator](../entities/component/generator.md) side for FGT-3200, is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c52][^c53] (authority 5, dated 2026-07-21). [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md) states: The two HSS bearings FGT-P-22328 from PO-76994 cannot be delivered in calendar week 39.[^c54] The new confirmed delivery window is calendar week 40, from 28.09.2026 to 02.10.2026.[^c54] (authority 3, date unknown). Resolution rule (authority, then recency): Spare Parts Stock Snapshot 2026-07-21 for [Quellmoor Ridge O&M Building](../entities/asset/om-building.md) prevails (authority 5 vs 3).
- **Expected delivery timing for FGT-P-22328 HSS bearings under PO-76994.** [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../sources/2026-07-22-parts-shortage-hss-bearing.md) states: The last HSS bearing was used on [WTG-10](../entities/asset/wtg-10.md) in March under WO-26-0187, and [Fabrikam](../entities/organisation/fabrikam-getriebetechnik.md) confirmed delivery of two bearings in week 39, from 21 to 25 September 2026.[^c58] (authority 3, dated 2026-07-22). [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md) states: The two HSS bearings FGT-P-22328 from PO-76994 cannot be delivered in calendar week 39.[^c54] The new confirmed delivery window is calendar week 40, from 28.09.2026 to 02.10.2026.[^c54] (authority 3, date unknown). Resolution rule (authority, then recency): the rule does not decide between them (same authority and no usable dates); review both sources.

Resolution policy: When two current sources disagree, the source with the higher document-type authority wins (environmental permit 10; service bulletin and grid instruction 9; maintenance manual and management of change 8; procedures, laboratory and inspection reports 7). With equal authority the more recent source wins. A service bulletin that amends a manual section for some turbines is shown next to the manual value, with the turbines it applies to.

## Superseded information

- **Current [gearbox](../entities/component/gearbox.md) oil-change SOP revision.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) is a standard operating procedure, Revision A, effective 2023-04-03.[^c59][^c60][^c61][^c62] Revision A is the first issue and is associated with [PWG 320](../entities/product/pwg-320.md).[^c63] Replacement: SOP-GBX-010 is Revision B and is effective from 2025-08-25.[^c64] Revision B supersedes SOP-GBX-010 Rev. A and implements MOC-2025-012 and [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A.[^c65] Revision B changed the oil to [PWG 220](../entities/product/pwg-220.md) per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c66] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Specified oil for gearbox oil changes.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The specified new oil is Proseware PWG 320 (ISO VG 320), with 410 L per turbine supplied as 2 drums [PWS-320-D208](../entities/part/pws-320-d208.md).[^c67] 410 L of Proseware PWG 320 is filled through a 10 micron filter cart.[^c68] Replacement: Each turbine requires 470 L of Proseware PWG 220, consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of [PWS-220-D208](../entities/part/pws-220-d208.md).[^c40] The gearbox is filled with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c45] A converted gearbox must never be topped up with PWG 320, and residual PWG 320 must remain below 5 % of oil volume.[^c15] Revision B changed the oil to PWG 220 per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c66] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Minimum oil sump temperature for restart after oil change.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: After lockout removal and restart, oil temperature is watched during the first hour, and the turbine starts only when the oil sump has reached +10 °C.[^c69] Replacement: Controller parameter GBX_TMIN_START must be set to 5 °C, and the gearbox filler must be labelled PWG 220.[^c48] On restart, oil temperature is watched during the first hour, and the turbine starts only once the oil sump has reached +5 °C.[^c57] Revision B changed the oil to PWG 220 per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c66] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Flush step and oil quantities during gearbox oil change.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The specified new oil is Proseware PWG 320 (ISO VG 320), with 410 L per turbine supplied as 2 drums PWS-320-D208.[^c67] 410 L of Proseware PWG 320 is filled through a 10 micron filter cart.[^c68] Replacement: Each turbine requires 470 L of Proseware PWG 220, consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of PWS-220-D208.[^c40] The flush step uses 60 L of PWG 220, runs the electric oil pump for 30 minutes, and then drains the flush oil into waste containers.[^c44] The gearbox is filled with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c45] Revision B changed the oil to PWG 220 per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c66] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Magnetic plug removal and debris recording in the oil-change procedure.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The magnetic plug is removed, debris is recorded, and the plug is cleaned.[^c70] Replacement: no current source restates it. Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).

## Sources consulted

- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md): current, authority 9, dated 2025-03-14
- [SB-LWS-2025-11 Rev. A - Pitch Bearing Bolt Re-torque](../sources/sb-lws-2025-11-reva-pitch-bearing-bolt-retorque.md): current, authority 9, dated 2025-10-06
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md): current, authority 8, dated 2024-03-15
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md): current, authority 7, dated 2026-06-17
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md): current, authority 7, dated 2025-08-25
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md): current, authority 6, dated 2026-07-10
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md): current, authority 6, dated 2026-07-01
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md): current, authority 5, date unknown
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md): current, authority 5, dated 2026-07-21
- [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026](../sources/vibration-trend-wtg-07-gearbox-2026.md): current, authority 5, date unknown
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md): current, authority 5, date unknown
- [Gearbox Fundamentals for Wind Technicians](../sources/gearbox-fundamentals.md): current, authority 4, dated 2025-10-20
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md): current, authority 4, dated 2026-06-18
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md): current, authority 3, date unknown
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../sources/2026-07-22-parts-shortage-hss-bearing.md): current, authority 3, dated 2026-07-22
- [Shift Handover Note - Day Shift - 18/07/2026](../sources/2026-07-18-note-de-releve.md): current, authority 2, date unknown
- [Shift Handover for 2026-07-29 Day Shift](../sources/2026-07-29-shift-handover.md): current, authority 2, date unknown
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md): current, authority 2, date unknown
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md): current, authority 2, date unknown
- [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md): superseded, authority 7, dated 2023-04-03

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [IMS bearing](../entities/component/ims-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [planetary stage](../entities/component/planetary-stage.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [service lift](../entities/component/service-lift.md), [slip ring](../entities/component/slip-ring.md), [yaw system](../entities/component/yaw-system.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-20915](../entities/part/awi-20915.md), [AWI-31007](../entities/part/awi-31007.md), [AWI-40210](../entities/part/awi-40210.md), [AWI-40388](../entities/part/awi-40388.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-11880](../entities/part/fgt-p-11880.md), [FGT-P-13010](../entities/part/fgt-p-13010.md), [FGT-P-14002](../entities/part/fgt-p-14002.md), [FGT-P-21904](../entities/part/fgt-p-21904.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [FGT-P-22331](../entities/part/fgt-p-22331.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-30422](../entities/part/lws-p-30422.md), [LWS-P-41120](../entities/part/lws-p-41120.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [LWS-P-55031](../entities/part/lws-p-55031.md), [LWS-P-60455](../entities/part/lws-p-60455.md), [LWS-P-72210](../entities/part/lws-p-72210.md), [LWS-P-80031](../entities/part/lws-p-80031.md), [LWS-P-90012](../entities/part/lws-p-90012.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A1001 Emergency stop activated](../entities/alarm-code/a1001.md), [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md), [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2130 Gearbox oil level low](../entities/alarm-code/a2130.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md), [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md), [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md), [A4105 Pitch system fault](../entities/alarm-code/a4105.md), [A5001 Yaw misalignment](../entities/alarm-code/a5001.md), [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Status codes: [S100 Running](../entities/status-code/s100.md), [S200 Ready - low wind](../entities/status-code/s200.md), [S310 Maintenance mode](../entities/status-code/s310.md), [S420 Curtailed - environmental condition](../entities/status-code/s420.md), [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md), [S510 Stopped - fault](../entities/status-code/s510.md), [S600 Stopped - icing](../entities/status-code/s600.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletins: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md), [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Organisations: [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md), [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md), [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md), [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)

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
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
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
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../sources/2026-07-22-parts-shortage-hss-bearing.md)
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
- [S100 Running](../entities/status-code/s100.md)
- [S200 Ready - low wind](../entities/status-code/s200.md)
- [S310 Maintenance mode](../entities/status-code/s310.md)
- [S420 Curtailed - environmental condition](../entities/status-code/s420.md)
- [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md)
- [S510 Stopped - fault](../entities/status-code/s510.md)
- [S600 Stopped - icing](../entities/status-code/s600.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [SB-LWS-2025-11 Rev. A - Pitch Bearing Bolt Re-torque](../sources/sb-lws-2025-11-reva-pitch-bearing-bolt-retorque.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [service lift](../entities/component/service-lift.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md)
- [Shift Handover for 2026-07-29 Day Shift](../sources/2026-07-29-shift-handover.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../sources/2026-07-18-note-de-releve.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md)
- [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md)
- [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)
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
- [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026](../sources/vibration-trend-wtg-07-gearbox-2026.md)
- [WTG-08](../entities/asset/wtg-08.md)
- [WTG-09](../entities/asset/wtg-09.md)
- [WTG-10](../entities/asset/wtg-10.md)
- [WTG-11](../entities/asset/wtg-11.md)
- [WTG-12](../entities/asset/wtg-12.md)
- [yaw system](../entities/component/yaw-system.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 1](../evidence/src-c4370c220559/p0001.md) · ✓ quote verified
[^c2]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 6](../evidence/src-86cb00fd2f6b/para-0006.md) · ✓ quote verified
[^c3]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 12](../evidence/src-86cb00fd2f6b/para-0012.md) · ✓ quote verified
[^c4]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 13](../evidence/src-86cb00fd2f6b/para-0013.md) · ✓ quote verified
[^c5]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 14](../evidence/src-86cb00fd2f6b/para-0014.md) · ✓ quote verified
[^c6]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 17](../evidence/src-86cb00fd2f6b/para-0017.md) · ✓ quote verified
[^c7]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 18](../evidence/src-86cb00fd2f6b/para-0018.md) · ✓ quote verified
[^c8]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 1](../evidence/src-990a047180b7/p0001.md) · ✓ quote verified
[^c9]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 7](../evidence/src-86cb00fd2f6b/para-0007.md) · ✓ quote verified
[^c10]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 5](../evidence/src-86cb00fd2f6b/tbl-02-r0005-r0005.md) · table
[^c11]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 24](../evidence/src-86cb00fd2f6b/para-0024.md) · ✓ quote verified
[^c12]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../evidence/src-1c261d5b87b5/p0002.md) · ✓ quote verified
[^c13]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 3](../evidence/src-1c261d5b87b5/p0003.md) · ✓ quote verified
[^c14]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 1, row 7](../evidence/src-70224c3b9c9f/tbl-01-r0007-r0007.md) · table
[^c15]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 42](../evidence/src-70224c3b9c9f/para-0042.md) · ✓ quote verified
[^c16]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 550](../evidence/src-36f5b999211a/r0550-r0550.md) · table
[^c17]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 551](../evidence/src-36f5b999211a/r0551-r0551.md) · table
[^c18]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 552](../evidence/src-36f5b999211a/r0552-r0552.md) · table
[^c19]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 946](../evidence/src-36f5b999211a/r0946-r0946.md) · table
[^c20]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 947](../evidence/src-36f5b999211a/r0947-r0947.md) · table
[^c21]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 948](../evidence/src-36f5b999211a/r0948-r0948.md) · table
[^c22]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 2](../evidence/src-86cb00fd2f6b/tbl-02-r0002-r0002.md) · table
[^c23]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 3](../evidence/src-86cb00fd2f6b/tbl-02-r0003-r0003.md) · table
[^c24]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 21](../evidence/src-86cb00fd2f6b/para-0021.md) · ✓ quote verified
[^c25]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 8](../evidence/src-aba30cb7207f/sheet-tasks-r0008-r0008.md) · table
[^c26]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 4](../evidence/src-1c261d5b87b5/p0004.md) · ✓ quote verified
[^c27]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 2](../evidence/src-32ed1eb40d24/r0002-r0002.md) · table
[^c28]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 36](../evidence/src-32ed1eb40d24/r0036-r0036.md) · table
[^c29]: [Work Orders Export through 2026-08-31 — row 80](../evidence/src-9fd435ef5956/r0080-r0080.md) · table
[^c30]: [Shift Handover for 2026-07-29 Day Shift — lines 5–14](../evidence/src-a011da5de982/l0005-l0014.md) · ✓ quote verified
[^c31]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 2](../evidence/src-aba30cb7207f/sheet-tasks-r0002-r0002.md) · table
[^c32]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 3](../evidence/src-aba30cb7207f/sheet-tasks-r0003-r0003.md) · table
[^c33]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 4](../evidence/src-aba30cb7207f/sheet-tasks-r0004-r0004.md) · table
[^c34]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 7](../evidence/src-aba30cb7207f/sheet-tasks-r0007-r0007.md) · table
[^c35]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../evidence/src-1c261d5b87b5/p0005.md) · ✓ quote verified
[^c36]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 16](../evidence/src-70224c3b9c9f/para-0016.md) · ✓ quote verified
[^c37]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 17](../evidence/src-70224c3b9c9f/para-0017.md) · ✓ quote verified
[^c38]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 19](../evidence/src-70224c3b9c9f/para-0019.md) · ✓ quote verified
[^c39]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 20](../evidence/src-70224c3b9c9f/para-0020.md) · ✓ quote verified
[^c40]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 22](../evidence/src-70224c3b9c9f/para-0022.md) · ✓ quote verified
[^c41]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 23](../evidence/src-70224c3b9c9f/para-0023.md) · ✓ quote verified
[^c42]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 30](../evidence/src-70224c3b9c9f/para-0030.md) · ✓ quote verified
[^c43]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 32](../evidence/src-70224c3b9c9f/para-0032.md) · ✓ quote verified
[^c44]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 34](../evidence/src-70224c3b9c9f/para-0034.md) · ✓ quote verified
[^c45]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 35](../evidence/src-70224c3b9c9f/para-0035.md) · ✓ quote verified
[^c46]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 36](../evidence/src-70224c3b9c9f/para-0036.md) · ✓ quote verified
[^c47]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 37](../evidence/src-70224c3b9c9f/para-0037.md) · ✓ quote verified
[^c48]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 38](../evidence/src-70224c3b9c9f/para-0038.md) · ✓ quote verified
[^c49]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 40](../evidence/src-70224c3b9c9f/para-0040.md) · ✓ quote verified
[^c50]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 41](../evidence/src-70224c3b9c9f/para-0041.md) · ✓ quote verified
[^c51]: [Work Orders Export through 2026-08-31 — row 73](../evidence/src-9fd435ef5956/r0073-r0073.md) · table
[^c52]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 3](../evidence/src-42566abae6ef/sheet-about-r0003-r0003.md) · table
[^c53]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 2](../evidence/src-42566abae6ef/sheet-stock-r0002-r0002.md) · table
[^c54]: [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up — lines 8–11](../evidence/src-1abc5aef1a40/l0008-l0011.md) · ✓ quote verified
[^c55]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 9](../evidence/src-42566abae6ef/sheet-stock-r0009-r0009.md) · table
[^c56]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 1](../evidence/src-1c261d5b87b5/p0001.md) · ✓ quote verified
[^c57]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 39](../evidence/src-70224c3b9c9f/para-0039.md) · ✓ quote verified
[^c58]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 10–12](../evidence/src-9107d71821bf/msg-body-l0010-l0012.md) · ✓ quote verified
[^c59]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 2](../evidence/src-90ea27f71f0f/para-0002.md) · ✓ quote verified
[^c60]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 2](../evidence/src-90ea27f71f0f/tbl-01-r0002-r0002.md) · table
[^c61]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 3](../evidence/src-90ea27f71f0f/tbl-01-r0003-r0003.md) · table
[^c62]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 4](../evidence/src-90ea27f71f0f/tbl-01-r0004-r0004.md) · table
[^c63]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 2, row 2](../evidence/src-90ea27f71f0f/tbl-02-r0002-r0002.md) · table
[^c64]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 2](../evidence/src-70224c3b9c9f/para-0002.md) · ✓ quote verified
[^c65]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 3](../evidence/src-70224c3b9c9f/para-0003.md) · ✓ quote verified
[^c66]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 2, row 3](../evidence/src-70224c3b9c9f/tbl-02-r0003-r0003.md) · table
[^c67]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 19](../evidence/src-90ea27f71f0f/para-0019.md) · ✓ quote verified
[^c68]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 31](../evidence/src-90ea27f71f0f/para-0031.md) · ✓ quote verified
[^c69]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 34](../evidence/src-90ea27f71f0f/para-0034.md) · ✓ quote verified
[^c70]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 28](../evidence/src-90ea27f71f0f/para-0028.md) · ✓ quote verified
