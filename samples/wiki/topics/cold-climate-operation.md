---
id: topic:cold-climate-operation
type: topic
title: Cold-climate operation and icing
summary: This page covers cold-weather operation, icing controls, gearbox oil heating, and winter access safety at Quellmoor Ridge.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- cold-climate-operation
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: cold-climate-operation
sources:
- src-05b9ebcb4d58
- src-0df0d0598e76
- src-1c261d5b87b5
- src-36f5b999211a
- src-70224c3b9c9f
- src-a20331a5431f
- src-a7e8d332dafd
- src-c4370c220559
- src-e7cd20fa7984
- src-ecc004b57dd5
confidence: medium
contradictions: 8
superseded_claims: 0
---

# Cold-climate operation and icing

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers cold-weather operation, icing controls, [gearbox](../entities/component/gearbox.md) oil heating, and winter access safety at [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).

## Overview

[Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md) comprises turbines [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), and current site oil-change procedures apply to WTG-01 to WTG-12 with [Litware LT-32](../entities/product/lt-32.md) CCV turbines and [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.[^c1][^c2] Ice detection is a permit-controlled condition: turbines must stop automatically when rotor-blade ice is detected and may restart only after the ice has gone, while site work-at-height rules prohibit access within 300 m of a turbine with ice detected under alarm [A7001](../entities/alarm-code/a7001.md).[^c3][^c4] For Quellmoor Ridge gearboxes under the current conversion procedure, [PWG 220](../entities/product/pwg-220.md) is used for flushing and filling, controller parameter GBX_TMIN_START is set to 5 °C, and restart is permitted only once the oil sump has reached +5 °C.[^c5][^c6][^c7][^c8] [Gearbox](../entities/component/gearbox.md) work planning must check the bulletin register because [Litware](../entities/organisation/litware-wind-systems.md) publishes gearbox-chapter changes as service bulletins, and the drivetrain start inhibit must not be bypassed.[^c9][^c10]

## Icing controls and exclusion zones

- Warning signs about falling ice must be placed at all access points at a distance of 300 m from the turbines from November to March.[^c3]
- SCADA records show that on 2026-04-01, icing alarms [A7001](../entities/alarm-code/a7001.md) led to [S600 Stopped - icing](../entities/status-code/s600.md) status starts for [WTG-12](../entities/asset/wtg-12.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-03](../entities/asset/wtg-03.md), and [WTG-02](../entities/asset/wtg-02.md), with later clears and S600 ends recorded for each turbine in that part of the log.[^c11][^c12][^c13][^c14][^c15][^c16][^c17][^c18]
- The onboarding deck also states that ice detection alarm A7001 stops the turbine automatically and that personnel must keep 300 m away from a turbine with ice on the blades.[^c19]

## Gearbox oil conversion and cold starts

- [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A applies to [LT-32](../entities/product/lt-32.md) turbines delivered in CCV configuration with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes, and [Litware](../entities/organisation/litware-wind-systems.md) support confirmed that the bulletin applies to all 12 CCV turbines of [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c20][^c21]
- For affected turbines, the service bulletin changes the gear oil from [Proseware PWG 320](../entities/product/pwg-320.md) to [Proseware PWG 220](../entities/product/pwg-220.md) and changes the viscosity grade from ISO VG 320 to ISO VG 220, while the total oil volume remains 410 L.[^c20]
- The service bulletin requires compliance at the next scheduled oil change and no later than 2025-12-31.[^c20]
- The stated reason for the oil-grade change is that cold-site reports showed start-up heating times of more than 6 hours at -25 °C ambient and filter bypass events with ISO VG 320 oil; Quellmoor’s MOC record also states that [WTG-02](../entities/asset/wtg-02.md) and [WTG-09](../entities/asset/wtg-09.md) needed more than 6 hours of heating before starting on 2025-01-21 at -24.6 °C.[^c20][^c22]
- The bulletin is categorized as recommended but mandatory to keep the [gearbox](../entities/component/gearbox.md) warranty, and conversions performed according to the bulletin keep the gearbox warranty valid.[^c20][^c23]

## Oil-change controls and contamination prevention

- [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) Rev. B is effective from 2025-08-25, supersedes SOP-GBX-010 Rev. A, and implements MOC-2025-012 and [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A.[^c24][^c25]
- A [gearbox](../entities/component/gearbox.md) oil change requires a PTW and at least two technicians, with no lone working in the nacelle, and the turbine must be isolated according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) before the oil circuit is opened.[^c26][^c27]
- The job must not start if the 10-minute mean wind speed exceeds 15 m/s, and hot-oil controls require chemical gloves, a face shield, long sleeves, and draining only between 40 and 60 °C.[^c28][^c29]
- Before draining, the turbine is stopped, lockout/tagout is applied, the rotor is locked, and the drivetrain is isolated; oil is drained between 40 and 60 °C, with heaters and the electric oil pump used before isolation if the oil is colder.[^c30][^c31]
- The conversion replaces filter element [FGT-P-11872](../entities/part/fgt-p-11872.md), flushes with 60 L of [PWG 220](../entities/product/pwg-220.md), runs the electric oil pump for 30 minutes, drains the flush oil, and fills the gearbox with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c32][^c5][^c6]
- A converted gearbox must never be topped up with [PWG 320](../entities/product/pwg-320.md), and residual PWG 320 must remain below 5 % of oil volume.[^c33]
- After filling, the electric oil pump is run for 15 minutes, connections are checked for leaks, the oil level is checked after 20 minutes of standstill, and a reference oil sample is taken after 24 hours of operation.[^c34][^c35][^c36]
- Quantities and batch numbers are recorded in the work order, and the [Litware](../entities/organisation/litware-wind-systems.md) completion form is sent within 30 days.[^c37]
- Waste oil is stored in the bunded store in the O&M building and collected by the licensed carrier; the environmental permit also requires waste oil to be collected by a licensed carrier.[^c38][^c3]

## Temperature and oil-pressure alarms

- For affected turbines, warning [A2101](../entities/alarm-code/a2101.md) and trip [A2102](../entities/alarm-code/a2102.md) temperature thresholds remain 75 °C and 82 °C.[^c20]
- The maintenance manual states that alarm A2101 is the gearbox oil sump temperature high alarm at 75 °C and that alarm A2102 is the gearbox oil sump temperature trip at 82 °C, which stops the turbine automatically.[^c39]
- SCADA records show [WTG-07](../entities/asset/wtg-07.md) raised A2101 and then A2102 on 2026-05-30, cleared both later, and also raised A2101 and then A2102 on 2026-06-19.[^c40][^c41][^c42][^c43][^c44][^c45][^c46][^c47][^c48]
- SCADA records show [WTG-11](../entities/asset/wtg-11.md) raised A2101 gearbox oil sump temperature high at 75.1 °C on 2026-08-12 and cleared it at 72.7 °C.[^c49][^c50]
- Alarm [A2120](../entities/alarm-code/a2120.md), gearbox oil pressure low at 0.8 bar, can be caused by cold oil at start-up, pump fault, or blocked filter; the manual action includes allowing heater time at cold start and checking the pump and filter.[^c39]
- SCADA records show [WTG-08](../entities/asset/wtg-08.md) and [WTG-09](../entities/asset/wtg-09.md) raised A2120 gearbox oil pressure low at 0.59 bar on 2026-04-02 and later cleared it at 1.35 bar.[^c51][^c52][^c53][^c54]
- Alarm [A2140](../entities/alarm-code/a2140.md), gearbox oil filter differential pressure high at 2.5 bar, can be caused by a clogged filter element or cold oil, and the manual action is to replace filter element [FGT-P-11872](../entities/part/fgt-p-11872.md).[^c39]
- SCADA records show A2140 events on [WTG-12](../entities/asset/wtg-12.md) on 2026-08-02, [WTG-04](../entities/asset/wtg-04.md) on 2026-08-11, and [WTG-06](../entities/asset/wtg-06.md) on 2026-08-31.[^c55][^c56][^c57][^c58][^c59][^c60]

## Winter work-at-height and rescue

- Climbing requires a minimum of two persons, with only one ladder section climbed at a time, and climbers must use the fall arrest rail and rest platforms and use the [service lift](../entities/component/service-lift.md) when available.[^c61][^c62]
- Climbing and nacelle work are limited to 10-minute mean wind speed up to 15 m/s, hub entry is limited to 12 m/s, and work on the nacelle roof is limited to 10 m/s.[^c63][^c64][^c65]
- Climbing is not allowed during a thunderstorm when lightning is detected within 15 km.[^c66]
- Tool tethering is mandatory above 2 m, hatches must stay closed while tools or parts are passed, and an exclusion zone with signage is set up at the tower base during nacelle work.[^c67]
- Each nacelle has a sealed [rescue kit](../entities/component/rescue-kit.md) with a descent device, rescue kits are inspected every 6 months, and a broken rescue-kit seal means the kit must be inspected before the next climb.[^c68]
- The rescue procedure begins by raising the alarm to the control room and emergency services, then making the turbine safe by stopping it and applying the rotor lock, and then attaching the casualty to the descent device and lowering the casualty to the ground or through the tower.[^c69][^c70][^c71]
- The rescue target is to have the casualty on the ground within 15 minutes of the alarm, and working-at-height and rescue training is refreshed every 2 years with rescue drills twice a year on site.[^c72][^c73]

## Contradictions

- **Approved [gearbox](../entities/component/gearbox.md) oil and viscosity for [LT-32](../entities/product/lt-32.md) turbines with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: The document applies to LT-32 turbines of all variants with the Fabrikam FGT-3200 gearbox.[^c9] Only the lubricant listed in Table 4-2 is approved for the FGT-3200 gearbox, and lubricants of different brands or viscosity grades must not be mixed.[^c10] The approved gear oil is [Proseware PWG 320](../entities/product/pwg-320.md) with viscosity grade ISO VG 320 and synthetic PAO base oil.[^c10] (authority 8, dated 2024-03-15). [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md) states: The bulletin applies to LT-32 turbines delivered in CCV configuration with Fabrikam FGT-3200 gearboxes and to LT-32 standard turbines at sites where ambient temperature regularly falls below -20 °C.[^c20] The affected document is LWS-MM-GBX-32 Rev. D, section 4.2 on lubrication.[^c20] For affected turbines, the gear oil changes from Proseware PWG 320 to [Proseware PWG 220](../entities/product/pwg-220.md).[^c20] For affected turbines, the viscosity grade changes from ISO VG 320 to ISO VG 220.[^c20] (authority 9, dated 2025-03-14). Resolution rule (authority, then recency): [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A - Gearbox oil viscosity grade change for [LT-32 CCV](../entities/product/lt-32-ccv.md) turbines prevails (authority 9 vs 8).
- **Approved gearbox oil and viscosity for [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) turbines.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: The document applies to LT-32 turbines of all variants with the Fabrikam FGT-3200 gearbox.[^c9] Only the lubricant listed in Table 4-2 is approved for the FGT-3200 gearbox, and lubricants of different brands or viscosity grades must not be mixed.[^c10] The approved gear oil is Proseware PWG 320 with viscosity grade ISO VG 320 and synthetic PAO base oil.[^c10] (authority 8, dated 2024-03-15). [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md) states: The change replaces Proseware PWG 320 (ISO VG 320) with Proseware PWG 220 (ISO VG 220) in the gearboxes of all 12 turbines, as required by SB-LWS-2025-07 Rev. A.[^c21] [Litware](../entities/organisation/litware-wind-systems.md) support confirmed on 2025-05-20 under ticket LWS-TS-48213 that SB-LWS-2025-07 applies to all 12 CCV turbines of Quellmoor Ridge.[^c21] (authority 8, dated 2025-06-18). Resolution rule (authority, then recency): MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 prevails (dated 2025-06-18 vs 2024-03-15).
- **Oil used by the current Quellmoor Ridge oil-change procedure.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: The document applies to LT-32 turbines of all variants with the Fabrikam FGT-3200 gearbox.[^c9] Only the lubricant listed in Table 4-2 is approved for the FGT-3200 gearbox, and lubricants of different brands or viscosity grades must not be mixed.[^c10] The approved gear oil is Proseware PWG 320 with viscosity grade ISO VG 320 and synthetic PAO base oil.[^c10] (authority 8, dated 2024-03-15). [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md) states: The procedure applies to [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) with Litware LT-32 CCV turbines and Fabrikam FGT-3200 gearboxes.[^c2] Each turbine requires 470 L of Proseware PWG 220, consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of [PWS-220-D208](../entities/part/pws-220-d208.md).[^c74] The gearbox is filled with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c6] A converted gearbox must never be topped up with PWG 320, and residual PWG 320 must remain below 5 % of oil volume.[^c33] (authority 7, dated 2025-08-25). Resolution rule (authority, then recency): LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt prevails (authority 8 vs 7).
- **Minimum oil sump temperature before start-up for affected turbines.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: Minimum oil sump temperature before start-up is +10 °C, with heaters on below +10 °C.[^c10] (authority 8, dated 2024-03-15). [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md) states: The minimum oil sump temperature before start-up changes from +10 °C to +5 °C.[^c20] The controller parameter GBX_TMIN_START must be changed from 10 to 5 °C.[^c20] (authority 9, dated 2025-03-14). Resolution rule (authority, then recency): SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines prevails (authority 9 vs 8).
- **Minimum oil sump temperature before start-up in the Quellmoor Ridge MOC controls.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: Minimum oil sump temperature before start-up is +10 °C, with heaters on below +10 °C.[^c10] (authority 8, dated 2024-03-15). [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md) states: For the cold-start hazard, the control is to set GBX_TMIN_START to 5 °C and verify it in the conversion checklist.[^c75] (authority 8, dated 2025-06-18). Resolution rule (authority, then recency): MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 prevails (dated 2025-06-18 vs 2024-03-15).
- **Minimum oil sump temperature before start-up in the current Quellmoor Ridge oil-change procedure.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: Minimum oil sump temperature before start-up is +10 °C, with heaters on below +10 °C.[^c10] (authority 8, dated 2024-03-15). [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md) states: Controller parameter GBX_TMIN_START must be set to 5 °C, and the gearbox filler must be labelled PWG 220.[^c7] On restart, oil temperature is watched during the first hour, and the turbine starts only once the oil sump has reached +5 °C.[^c8] (authority 7, dated 2025-08-25). Resolution rule (authority, then recency): LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt prevails (authority 8 vs 7).
- **Approved oil change stated in the Litware applicability email versus the maintenance manual.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: The document applies to LT-32 turbines of all variants with the Fabrikam FGT-3200 gearbox.[^c9] Only the lubricant listed in Table 4-2 is approved for the FGT-3200 gearbox, and lubricants of different brands or viscosity grades must not be mixed.[^c10] The approved gear oil is Proseware PWG 320 with viscosity grade ISO VG 320 and synthetic PAO base oil.[^c10] (authority 8, dated 2024-03-15). [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md) states: The configuration records checked for Quellmoor Ridge Wind Farm showed that all 12 turbines, WTG-01 through WTG-12, were delivered as LT-32 in CCV configuration with Fabrikam FGT-3200 gearboxes, so SB-LWS-2025-07 applies to all 12 turbines.[^c76] For the conversion, the oil is to be changed from Proseware PWG 320 to Proseware PWG 220 at the next scheduled oil change, and no later than 31 December 2025.[^c77] (authority 3, dated 2025-05-20). Resolution rule (authority, then recency): LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt prevails (authority 8 vs 3).
- **Minimum oil sump temperature stated in the Litware applicability email versus the maintenance manual.** [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md) states: Minimum oil sump temperature before start-up is +10 °C, with heaters on below +10 °C.[^c10] (authority 8, dated 2024-03-15). [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md) states: The minimum oil sump temperature for start-up is to be set to +5 degrees C using controller parameter GBX_TMIN_START.[^c78] (authority 3, dated 2025-05-20). Resolution rule (authority, then recency): LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt prevails (authority 8 vs 3).

Resolution policy: When two current sources disagree, the source with the higher document-type authority wins (environmental permit 10; service bulletin and grid instruction 9; maintenance manual and management of change 8; procedures, laboratory and inspection reports 7). With equal authority the more recent source wins. A service bulletin that amends a manual section for some turbines is shown next to the manual value, with the turbines it applies to.

## Superseded information

No superseded information.

## Sources consulted

- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../sources/ep-2018-0417-environmental-permit-consolidated.md): current, authority 10, dated 2024-12-10
- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md): current, authority 9, dated 2025-03-14
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md): current, authority 8, dated 2024-03-15
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md): current, authority 8, dated 2025-06-18
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md): current, authority 7, dated 2025-08-25
- [SOP-WAH-003 Revision B - Working at height and rescue](../sources/sop-wah-003-revb-working-at-height-and-rescue.md): current, authority 7, dated 2026-04-07
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md): current, authority 5, date unknown
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../sources/onboarding-and-site-rules.md): current, authority 4, dated 2025-02-03
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md): current, authority 3, dated 2025-05-20
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md): current, authority 2, date unknown

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [IMS bearing](../entities/component/ims-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [planetary stage](../entities/component/planetary-stage.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [service lift](../entities/component/service-lift.md), [yaw system](../entities/component/yaw-system.md)
- Spare parts: [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-11880](../entities/part/fgt-p-11880.md), [FGT-P-13010](../entities/part/fgt-p-13010.md), [FGT-P-14002](../entities/part/fgt-p-14002.md), [FGT-P-21904](../entities/part/fgt-p-21904.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [FGT-P-22331](../entities/part/fgt-p-22331.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-30422](../entities/part/lws-p-30422.md), [PWS-220-D208](../entities/part/pws-220-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A1001 Emergency stop activated](../entities/alarm-code/a1001.md), [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md), [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2130 Gearbox oil level low](../entities/alarm-code/a2130.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md), [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md), [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md), [A4105 Pitch system fault](../entities/alarm-code/a4105.md), [A5001 Yaw misalignment](../entities/alarm-code/a5001.md), [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Status codes: [S200 Ready - low wind](../entities/status-code/s200.md), [S310 Maintenance mode](../entities/status-code/s310.md), [S420 Curtailed - environmental condition](../entities/status-code/s420.md), [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md), [S510 Stopped - fault](../entities/status-code/s510.md), [S600 Stopped - icing](../entities/status-code/s600.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md)

<!-- docwiki:backlinks:start -->
## Referenced by

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
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-11880](../entities/part/fgt-p-11880.md)
- [FGT-P-13010](../entities/part/fgt-p-13010.md)
- [FGT-P-14002](../entities/part/fgt-p-14002.md)
- [FGT-P-21904](../entities/part/fgt-p-21904.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [FGT-P-22331](../entities/part/fgt-p-22331.md)
- [gearbox](../entities/component/gearbox.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [IMS bearing](../entities/component/ims-bearing.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-30422](../entities/part/lws-p-30422.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [planetary stage](../entities/component/planetary-stage.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../sources/onboarding-and-site-rules.md)
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
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [service lift](../entities/component/service-lift.md)
- [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
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
[^c2]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 1, row 7](../evidence/src-70224c3b9c9f/tbl-01-r0007-r0007.md) · table
[^c3]: [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2) — p. 2](../evidence/src-a7e8d332dafd/p0002.md) · ✓ quote verified
[^c4]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 6](../evidence/src-05b9ebcb4d58/tbl-02-r0006-r0006.md) · table
[^c5]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 34](../evidence/src-70224c3b9c9f/para-0034.md) · ✓ quote verified
[^c6]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 35](../evidence/src-70224c3b9c9f/para-0035.md) · ✓ quote verified
[^c7]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 38](../evidence/src-70224c3b9c9f/para-0038.md) · ✓ quote verified
[^c8]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 39](../evidence/src-70224c3b9c9f/para-0039.md) · ✓ quote verified
[^c9]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 1](../evidence/src-1c261d5b87b5/p0001.md) · ✓ quote verified
[^c10]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 3](../evidence/src-1c261d5b87b5/p0003.md) · ✓ quote verified
[^c11]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 4](../evidence/src-36f5b999211a/r0004-r0004.md) · table
[^c12]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 5](../evidence/src-36f5b999211a/r0005-r0005.md) · table
[^c13]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 6](../evidence/src-36f5b999211a/r0006-r0006.md) · table
[^c14]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 7](../evidence/src-36f5b999211a/r0007-r0007.md) · table
[^c15]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 8](../evidence/src-36f5b999211a/r0008-r0008.md) · table
[^c16]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 9](../evidence/src-36f5b999211a/r0009-r0009.md) · table
[^c17]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 12](../evidence/src-36f5b999211a/r0012-r0012.md) · table
[^c18]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 13](../evidence/src-36f5b999211a/r0013-r0013.md) · table
[^c19]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 7](../evidence/src-e7cd20fa7984/slide-07.md) · ✓ quote verified
[^c20]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 1](../evidence/src-c4370c220559/p0001.md) · ✓ quote verified
[^c21]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 4](../evidence/src-a20331a5431f/para-0004.md) · ✓ quote verified
[^c22]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 6](../evidence/src-a20331a5431f/para-0006.md) · ✓ quote verified
[^c23]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 2](../evidence/src-c4370c220559/p0002.md) · ✓ quote verified
[^c24]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 2](../evidence/src-70224c3b9c9f/para-0002.md) · ✓ quote verified
[^c25]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 3](../evidence/src-70224c3b9c9f/para-0003.md) · ✓ quote verified
[^c26]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 16](../evidence/src-70224c3b9c9f/para-0016.md) · ✓ quote verified
[^c27]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 17](../evidence/src-70224c3b9c9f/para-0017.md) · ✓ quote verified
[^c28]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 18](../evidence/src-70224c3b9c9f/para-0018.md) · ✓ quote verified
[^c29]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 19](../evidence/src-70224c3b9c9f/para-0019.md) · ✓ quote verified
[^c30]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 27](../evidence/src-70224c3b9c9f/para-0027.md) · ✓ quote verified
[^c31]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 28](../evidence/src-70224c3b9c9f/para-0028.md) · ✓ quote verified
[^c32]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 32](../evidence/src-70224c3b9c9f/para-0032.md) · ✓ quote verified
[^c33]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 42](../evidence/src-70224c3b9c9f/para-0042.md) · ✓ quote verified
[^c34]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 36](../evidence/src-70224c3b9c9f/para-0036.md) · ✓ quote verified
[^c35]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 37](../evidence/src-70224c3b9c9f/para-0037.md) · ✓ quote verified
[^c36]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 40](../evidence/src-70224c3b9c9f/para-0040.md) · ✓ quote verified
[^c37]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 41](../evidence/src-70224c3b9c9f/para-0041.md) · ✓ quote verified
[^c38]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 44](../evidence/src-70224c3b9c9f/para-0044.md) · ✓ quote verified
[^c39]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../evidence/src-1c261d5b87b5/p0005.md) · ✓ quote verified
[^c40]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 550](../evidence/src-36f5b999211a/r0550-r0550.md) · table
[^c41]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 551](../evidence/src-36f5b999211a/r0551-r0551.md) · table
[^c42]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 552](../evidence/src-36f5b999211a/r0552-r0552.md) · table
[^c43]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 555](../evidence/src-36f5b999211a/r0555-r0555.md) · table
[^c44]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 558](../evidence/src-36f5b999211a/r0558-r0558.md) · table
[^c45]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 559](../evidence/src-36f5b999211a/r0559-r0559.md) · table
[^c46]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 946](../evidence/src-36f5b999211a/r0946-r0946.md) · table
[^c47]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 947](../evidence/src-36f5b999211a/r0947-r0947.md) · table
[^c48]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 948](../evidence/src-36f5b999211a/r0948-r0948.md) · table
[^c49]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1660](../evidence/src-36f5b999211a/r1660-r1660.md) · table
[^c50]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1661](../evidence/src-36f5b999211a/r1661-r1661.md) · table
[^c51]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 32](../evidence/src-36f5b999211a/r0032-r0032.md) · table
[^c52]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 33](../evidence/src-36f5b999211a/r0033-r0033.md) · table
[^c53]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 34](../evidence/src-36f5b999211a/r0034-r0034.md) · table
[^c54]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 35](../evidence/src-36f5b999211a/r0035-r0035.md) · table
[^c55]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1436](../evidence/src-36f5b999211a/r1436-r1436.md) · table
[^c56]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1485](../evidence/src-36f5b999211a/r1485-r1485.md) · table
[^c57]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1654](../evidence/src-36f5b999211a/r1654-r1654.md) · table
[^c58]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1655](../evidence/src-36f5b999211a/r1655-r1655.md) · table
[^c59]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1896](../evidence/src-36f5b999211a/r1896-r1896.md) · table
[^c60]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1897](../evidence/src-36f5b999211a/r1897-r1897.md) · table
[^c61]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 14](../evidence/src-05b9ebcb4d58/para-0014.md) · ✓ quote verified
[^c62]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 15](../evidence/src-05b9ebcb4d58/para-0015.md) · ✓ quote verified
[^c63]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 2](../evidence/src-05b9ebcb4d58/tbl-02-r0002-r0002.md) · table
[^c64]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 3](../evidence/src-05b9ebcb4d58/tbl-02-r0003-r0003.md) · table
[^c65]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 4](../evidence/src-05b9ebcb4d58/tbl-02-r0004-r0004.md) · table
[^c66]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 5](../evidence/src-05b9ebcb4d58/tbl-02-r0005-r0005.md) · table
[^c67]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 12](../evidence/src-05b9ebcb4d58/para-0012.md) · ✓ quote verified
[^c68]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 19](../evidence/src-05b9ebcb4d58/para-0019.md) · ✓ quote verified
[^c69]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 21](../evidence/src-05b9ebcb4d58/para-0021.md) · ✓ quote verified
[^c70]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 22](../evidence/src-05b9ebcb4d58/para-0022.md) · ✓ quote verified
[^c71]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 23](../evidence/src-05b9ebcb4d58/para-0023.md) · ✓ quote verified
[^c72]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 24](../evidence/src-05b9ebcb4d58/para-0024.md) · ✓ quote verified
[^c73]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 26](../evidence/src-05b9ebcb4d58/para-0026.md) · ✓ quote verified
[^c74]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 22](../evidence/src-70224c3b9c9f/para-0022.md) · ✓ quote verified
[^c75]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 3](../evidence/src-a20331a5431f/tbl-02-r0003-r0003.md) · table
[^c76]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 10–12](../evidence/src-0df0d0598e76/msg-body-l0010-l0012.md) · paraphrase
[^c77]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 16–23](../evidence/src-0df0d0598e76/msg-body-l0016-l0023.md) · paraphrase
[^c78]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 16–23](../evidence/src-0df0d0598e76/msg-body-l0016-l0023.md) · ✓ quote verified
