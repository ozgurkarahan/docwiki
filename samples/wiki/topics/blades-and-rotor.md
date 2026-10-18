---
id: topic:blades-and-rotor
type: topic
title: Blades, pitch bearings and main-component lifts
summary: This page covers blade condition, pitch-bearing bolt re-torque, and crane lifts for blade replacement at Quellmoor Ridge Wind Farm.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- blades-and-rotor
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: blades-and-rotor
sources:
- src-15df96905f07
- src-1d8dff18b801
- src-383540987d7a
- src-67f6c3ce9754
- src-9fd435ef5956
- src-a6c9699afa37
- src-aba30cb7207f
confidence: medium
contradictions: 1
superseded_claims: 0
---

# Blades, pitch bearings and main-component lifts

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers blade condition, pitch-bearing bolt re-torque, and crane lifts for blade replacement at [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).

## Overview

The current blade inspection found one category 4 finding, four category 3 findings, and eleven blades with category 2 damage across the inspected blades.[^c1] [WTG-04](../entities/asset/wtg-04.md) blade B is the critical blade issue: it has a category 4 trailing-edge crack, is to be replaced before 2026-09-30, and requires monthly drone checks until replacement with immediate turbine stop if the crack exceeds 1.2 m.[^c2] The WTG-04 blade B replacement is planned as a single blade lift in a 2026-09-08 to 2026-09-10 daylight-only lift window.[^c3] For the pitch-bearing re-torque timing discrepancy, the reviewed resolution rule is authority then recency; the service bulletin requires compliance at the next 12-month service, while the maintenance plan schedules the referenced task every 12 months.[^c4][^c5]

## WTG-04 blade B lift controls

- The lift plan identifies the job as [WTG-04](../entities/asset/wtg-04.md) [rotor blade](../entities/component/rotor-blade.md) B replacement, described as a single blade lift.[^c3]
- The appointed person is Bram Okkerse of [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md), the client supervisor is Dario Penwarden of [Contoso Renewables](../entities/organisation/contoso-renewables.md), and the plan was prepared by Bram Okkerse and approved by Dario Penwarden.[^c3][^c6]
- The main crane is a 600 t crawler crane with fleet number TS-600C-02 and a 102 m main boom, and the assist crane is a 100 t mobile crane used for tailing the blade root.[^c3]
- The blade is 57.5 m long and 14.6 t, the blade yoke is 3.9 t, the rigging is 0.6 t, and the total hook load is 19.1 t.[^c3]
- The lift radius is 26 m, the capacity at radius is 31.0 t, the utilisation is 62 %, and the hook height is 96 m.[^c3]
- The maximum 10-minute mean wind speed at hub height is 8 m/s, the maximum gust is 11 m/s, and no lift is allowed in fog with visibility below 300 m, lightning within 15 km, or icing.[^c3]
- Wind is read at the WTG-04 nacelle anemometer and boom tip anemometer.[^c3]
- The lift exclusion zone is 150 m around WTG-04, two 120 m tag lines are fitted on the blade, and the site gate is closed by the banksman.[^c3]
- Ground bearing pressure under the crane mats is 180 kN/m2, against an allowable value of 250 kN/m2.[^c3]
- Before lifting, the sequence requires a pre-lift meeting and a permit to work signed by both parties, rotor lock with blade B pointing down, and pitch-system isolation.[^c6]
- The blade yoke is fitted and load tested at 0.5 m above the laydown area before blade B is unbolted and lowered with both tag lines manned.[^c6]
- The new blade is lifted, bolted, and torqued according to a [Litware](../entities/organisation/litware-wind-systems.md) instruction, and the exclusion zone may be released only by the appointed person.[^c6]

## Blade inspection findings

- The blade inspection report covers [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), which is recorded as having 12 [Litware LT-32](../entities/product/lt-32.md) turbines and 36 blades of 57.5 m.[^c1]
- The inspection was performed from 2026-05-18 to 2026-05-22 using drone visual inspection with three passes per blade and ground photography.[^c1]
- The report date was 2026-06-03 and the lead inspector was Leilani Hartfield.[^c1]
- In the inspection report, category 3 means significant damage requiring repair within 6 months, category 4 means serious damage requiring repair or replacement within 3 months plus monthly drone checks, and category 5 means critical damage requiring turbine stop.[^c1]
- [WTG-04](../entities/asset/wtg-04.md) had the highest turbine summary category, with blade A category 2, blade B category 4, blade C category 2, and highest category 4.[^c1]
- Finding F-01 is a category 4 trailing-edge crack on WTG-04 blade B, blade serial LB575-19-1187, measuring 0.9 m along the bond line between radius 37.6 m and 38.5 m, close to the spar cap.[^c2]
- Finding F-02 is category 3 leading-edge erosion on WTG-04 blade B, with coating loss between radius 52 m and 57 m and no exposed laminate.[^c2]
- Finding F-03 is category 3 lightning receptor damage on [WTG-08](../entities/asset/wtg-08.md) blade A; the tip receptor is burnt, the receptor is to be replaced within 6 months, and continuity of the down conductor is to be checked.[^c2]
- Finding F-04 is category 3 leading-edge erosion on [WTG-09](../entities/asset/wtg-09.md) blade C, with erosion between radius 50 m and 57 m, exposed laminate over 0.3 m, and a required leading-edge repair within 6 months.[^c2]
- Finding F-05 is a category 3 root gelcoat crack on [WTG-11](../entities/asset/wtg-11.md) blade C at radius 3.2 m, with repair within 6 months and a check at the next inspection.[^c2]
- The inspection recommendations are to replace WTG-04 blade B before 2026-09-30 using a crane lift, repair category 3 findings within 6 months using rope access, and perform the next full inspection in May 2027.[^c2]

## Pitch bearing bolt re-torque

- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) issued mandatory service bulletin [SB-LWS-2025-11](../entities/bulletin/sb-lws-2025-11.md) Rev. A on 2025-10-06.[^c4]
- The bulletin applies to all variants of [LT-32](../entities/product/lt-32.md) turbines with M30 10.9 [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), 72 bolts per blade bearing, and 216 bolts per turbine.[^c4]
- The reason for the bulletin is that loose pitch bearing bolts were found on two LT-32 turbines at another site after three years of operation, and a one-time re-torque restores the preload.[^c4]
- Before the work, the turbine must be stopped, the rotor locked, and the pitch system isolated.[^c4]
- The hydraulic torque wrench used for the work must have been calibrated within the last 12 months and have accuracy of +/- 3 %.[^c4]
- Technicians must re-torque 100 % of the pitch bearing bolts to 1,450 Nm in the cross pattern of the bolt map, blade by blade.[^c4]
- Each bolt must be marked with a paint line after re-torque.[^c4]
- Every bolt that turns more than 60 degrees before reaching the torque must be recorded and reported to Litware Wind Systems.[^c4]
- The turbine, blade, torque wrench serial number, and bolts that turned must be recorded on the re-torque form, which must be returned to Litware Wind Systems within 60 days.[^c4]
- The 2026 maintenance plan includes task MP-PIT-01 for 100 % of pitch bearing bolts at 1,450 Nm and references SB-LWS-2025-11 Rev. A.[^c5]
- Work orders record completed [pitch bearing](../entities/component/pitch-bearing.md) bolt re-torque for [WTG-01](../entities/asset/wtg-01.md) through [WTG-06](../entities/asset/wtg-06.md) at 1,450 Nm with 100 % bolt coverage and reference SB-LWS-2025-11 Rev. A.[^c7][^c8][^c9][^c10][^c11][^c12]
- Work orders record planned pitch bearing bolt re-torque for [WTG-07](../entities/asset/wtg-07.md) through [WTG-12](../entities/asset/wtg-12.md) in September 2026, with each title stating 1,450 Nm, 100 % of bolts, and reference SB-LWS-2025-11 Rev. A.[^c13][^c14][^c15][^c16][^c17][^c18]

## Contradictions

- **Whether [pitch bearing](../entities/component/pitch-bearing.md) bolt re-torque is a one-time next-service bulletin action or a recurring 12-month maintenance-plan task.** [SB-LWS-2025-11 Rev. A - Pitch Bearing Bolt Re-torque](../sources/sb-lws-2025-11-reva-pitch-bearing-bolt-retorque.md) states: Compliance is required at the next 12-month service.[^c4] The reason for the bulletin is that loose [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md) were found on two [LT-32](../entities/product/lt-32.md) turbines at another site after three years of operation, and a one-time re-torque restores the preload.[^c4] (authority 9, dated 2025-10-06). [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md) states: Pitch bearing bolt re-torque task MP-PIT-01 covers 100 % of bolts at 1,450 Nm, is scheduled every 12 months, and references [SB-LWS-2025-11](../entities/bulletin/sb-lws-2025-11.md) Rev. A.[^c5] (authority 6, dated 2026-07-01). Resolution rule (authority, then recency): SB-LWS-2025-11 Rev. A - Pitch Bearing Bolt Re-torque prevails (authority 9 vs 6).

Resolution policy: When two current sources disagree, the source with the higher document-type authority wins (environmental permit 10; service bulletin and grid instruction 9; maintenance manual and management of change 8; procedures, laboratory and inspection reports 7). With equal authority the more recent source wins. A service bulletin that amends a manual section for some turbines is shown next to the manual value, with the turbines it applies to.

## Superseded information

No superseded information.

## Sources consulted

- [SB-LWS-2025-11 Rev. A - Pitch Bearing Bolt Re-torque](../sources/sb-lws-2025-11-reva-pitch-bearing-bolt-retorque.md): current, authority 9, dated 2025-10-06
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../sources/wbs-2026-031-blade-inspection-report.md): current, authority 7, dated 2026-06-03
- [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement](../sources/lp-2026-009-lift-plan-wtg-04-blade-scanned.md): current, authority 7, dated 2026-08-19
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md): current, authority 6, dated 2026-07-01
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md): current, authority 5, date unknown
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md): current, authority 4, dated 2026-06-18
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md): current, authority 2, date unknown

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [slip ring](../entities/component/slip-ring.md), [yaw system](../entities/component/yaw-system.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-20915](../entities/part/awi-20915.md), [AWI-31007](../entities/part/awi-31007.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Litware LT-32](../entities/product/lt-32.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md), [TS-600C](../entities/product/ts-600c.md)
- Alarm code: [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- Status code: [S100 Running](../entities/status-code/s100.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletins: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md), [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md), [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-20915](../entities/part/awi-20915.md)
- [AWI-31007](../entities/part/awi-31007.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../sources/wbs-2026-031-blade-inspection-report.md)
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [gearbox](../entities/component/gearbox.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
- [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement](../sources/lp-2026-009-lift-plan-wtg-04-blade-scanned.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-51207](../entities/part/lws-p-51207.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md)
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [pitch bearing](../entities/component/pitch-bearing.md)
- [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [PWS-320-D208](../entities/part/pws-320-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [S100 Running](../entities/status-code/s100.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [SB-LWS-2025-11 Rev. A - Pitch Bearing Bolt Re-torque](../sources/sb-lws-2025-11-reva-pitch-bearing-bolt-retorque.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)
- [TS-600C](../entities/product/ts-600c.md)
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

[^c1]: [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026) — p. 1](../evidence/src-383540987d7a/p0001.md) · ✓ quote verified
[^c2]: [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026) — p. 2](../evidence/src-383540987d7a/p0002.md) · ✓ quote verified
[^c3]: [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement — p. 1](../evidence/src-67f6c3ce9754/p0001.md) · OCR
[^c4]: [SB-LWS-2025-11 Rev. A - Pitch Bearing Bolt Re-torque — p. 1](../evidence/src-a6c9699afa37/p0001.md) · ✓ quote verified
[^c5]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 11](../evidence/src-aba30cb7207f/sheet-tasks-r0011-r0011.md) · table
[^c6]: [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement — p. 2](../evidence/src-67f6c3ce9754/p0002.md) · OCR
[^c7]: [Work Orders Export through 2026-08-31 — row 45](../evidence/src-9fd435ef5956/r0045-r0045.md) · table
[^c8]: [Work Orders Export through 2026-08-31 — row 46](../evidence/src-9fd435ef5956/r0046-r0046.md) · table
[^c9]: [Work Orders Export through 2026-08-31 — row 47](../evidence/src-9fd435ef5956/r0047-r0047.md) · table
[^c10]: [Work Orders Export through 2026-08-31 — row 48](../evidence/src-9fd435ef5956/r0048-r0048.md) · table
[^c11]: [Work Orders Export through 2026-08-31 — row 49](../evidence/src-9fd435ef5956/r0049-r0049.md) · table
[^c12]: [Work Orders Export through 2026-08-31 — row 50](../evidence/src-9fd435ef5956/r0050-r0050.md) · table
[^c13]: [Work Orders Export through 2026-08-31 — row 90](../evidence/src-9fd435ef5956/r0090-r0090.md) · table
[^c14]: [Work Orders Export through 2026-08-31 — row 91](../evidence/src-9fd435ef5956/r0091-r0091.md) · table
[^c15]: [Work Orders Export through 2026-08-31 — row 92](../evidence/src-9fd435ef5956/r0092-r0092.md) · table
[^c16]: [Work Orders Export through 2026-08-31 — row 93](../evidence/src-9fd435ef5956/r0093-r0093.md) · table
[^c17]: [Work Orders Export through 2026-08-31 — row 94](../evidence/src-9fd435ef5956/r0094-r0094.md) · table
[^c18]: [Work Orders Export through 2026-08-31 — row 95](../evidence/src-9fd435ef5956/r0095-r0095.md) · table
