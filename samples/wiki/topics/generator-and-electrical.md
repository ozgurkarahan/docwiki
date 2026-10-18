---
id: topic:generator-and-electrical
type: topic
title: Generator brushes and electrical systems
summary: This page covers generator brush maintenance, slip-ring work, generator temperatures, and electrical alarms for the wind farm turbines.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- generator-and-electrical
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: generator-and-electrical
sources:
- src-1b5b5135881d
- src-1c261d5b87b5
- src-36f5b999211a
- src-824b788eefc0
- src-86cb00fd2f6b
- src-9fd435ef5956
- src-aba30cb7207f
- src-b7a218719725
confidence: high
contradictions: 0
superseded_claims: 0
---

# Generator brushes and electrical systems

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers [generator](../entities/component/generator.md) brush maintenance, slip-ring work, generator temperatures, and electrical alarms for the wind farm turbines.

## Overview

[WI-GEN-014](../entities/procedure/wi-gen-014.md) applies to [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) with a 690 V double-fed asynchronous [generator](../entities/component/generator.md) and describes checking and replacing [generator brushes](../entities/component/generator-brushes.md) on [Litware LT-32](../entities/product/lt-32.md) turbines at [Quellmoor Ridge wind farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c1][^c2][^c3] Generator brush work requires a permit to work, at least two technicians, generator lockout including stator and rotor, and protective equipment because carbon dust is conductive.[^c4][^c5][^c6] The brush-maintenance rule is to replace the complete brush set when any brush has less than 18 mm remaining; alarm [A3210](../entities/alarm-code/a3210.md) appears when remaining brush length reaches approximately 20 mm.[^c7][^c8] The maintenance plan schedules generator brush inspection every 6 months and slip-ring cleaning every 12 months, both referencing WI-GEN-014.[^c9][^c10]

## Brush replacement materials and tools

- The required brush set is [LWS-P-51207](../entities/part/lws-p-51207.md) and contains 18 brushes.[^c11]
- The required slip-ring cleaning kit is [LWS-P-55031](../entities/part/lws-p-55031.md).[^c12]
- Required tools include a 5 to 25 N·m torque wrench, a caliper, and an industrial vacuum cleaner.[^c13]

## Replacement procedure

- The operating procedure begins by obtaining the permit to work, stopping the turbine, and locking out the [generator](../entities/component/generator.md).[^c14]
- Each brush length must be measured with a caliper and recorded.[^c15]
- The [slip ring](../entities/component/slip-ring.md) must be cleaned with kit [LWS-P-55031](../entities/part/lws-p-55031.md), then new brushes must be installed and checked for free sliding.[^c16][^c17]
- Brush-holder screws must be tightened to 12 N·m.[^c18]
- After replacement, turbine power must be limited to 50 % for 8 hours before returning to rated power.[^c19]
- Measured brush lengths and the work order number must be recorded.[^c20]
- The estimated work duration is 3 hours for two technicians, excluding run-in.[^c21]

## Recent brush alarm and corrective work

- [WTG-09](../entities/asset/wtg-09.md) had alarm [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md) raised on 2026-07-16 and cleared on 2026-07-18, and WTG-09 was in [maintenance mode](../entities/status-code/s310.md) on 2026-07-18 from 07:58:12 to 11:52:40.[^c22][^c23][^c24][^c25]
- Work order WO-26-0436 for WTG-09 replaced [generator brushes](../entities/component/generator-brushes.md) for A3210 under [WI-GEN-014](../entities/procedure/wi-gen-014.md), used part [LWS-P-51207](../entities/part/lws-p-51207.md) quantity 1, and recorded the shortest brush as 16 mm.[^c26]
- The shift handover note also records that WTG-09 had its generator brushes replaced under WO-26-0436 following alarm A3210 from 16/07, with the shortest measured brush below the WI-GEN-014 threshold.[^c27]
- For WTG-09, a complete LWS-P-51207 set was replaced, the brush-holder screws were tightened to 12 N·m, and run-in was performed at 50 % power for 8 hours.[^c27]

## Generator temperature and electrical alarms

- [WTG-12](../entities/asset/wtg-12.md) had alarm [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md) raised at 147.3 °C and cleared at 139.5 °C on 2026-08-26.[^c28][^c29]
- [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md) alarms affected [WTG-01](../entities/asset/wtg-01.md) through WTG-12 on 2026-06-06, with value 87.2 %, followed by clear entries at 99.6 %.[^c30][^c31][^c32][^c33][^c34][^c35]
- A6101 Grid voltage out of range alarms affected WTG-01 through WTG-12 on 2026-06-18 at 89.2 %, and the alarms cleared at 99.6 %.[^c36][^c37][^c38][^c39][^c40][^c41][^c42][^c43][^c44][^c45][^c46][^c47][^c48][^c49][^c50][^c51]
- A6101 Grid voltage out of range was raised for WTG-01 through WTG-12 on 2026-08-02 with value 89.3 %, then cleared at 99.6 %.[^c52][^c53][^c54][^c55][^c56][^c57]
- On 2026-08-21, WTG-01 through WTG-12 raised A6101 Grid voltage out of range at 87.8 %, entered stopped-fault status, then cleared A6101 at 99.6 % and ended the stopped-fault status.[^c58][^c59][^c60][^c61][^c62][^c63][^c64][^c65]

## Contradictions

No contradictions were found between current sources.

## Superseded information

No superseded information.

## Sources consulted

- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md): current, authority 8, dated 2024-03-15
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../sources/wi-gen-014-reva-remplacement-balais-generatrice.md): current, authority 7, dated 2025-09-15
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md): current, authority 6, dated 2026-07-10
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md): current, authority 6, dated 2026-07-01
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md): current, authority 5, date unknown
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md): current, authority 5, date unknown
- [Gearbox Fundamentals for Wind Technicians](../sources/gearbox-fundamentals.md): current, authority 4, dated 2025-10-20
- [Shift Handover Note - Day Shift - 18/07/2026](../sources/2026-07-18-note-de-releve.md): current, authority 2, date unknown

## Related

- Assets: [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [IMS bearing](../entities/component/ims-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [planetary stage](../entities/component/planetary-stage.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [slip ring](../entities/component/slip-ring.md), [yaw system](../entities/component/yaw-system.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-31007](../entities/part/awi-31007.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-11880](../entities/part/fgt-p-11880.md), [FGT-P-13010](../entities/part/fgt-p-13010.md), [FGT-P-14002](../entities/part/fgt-p-14002.md), [FGT-P-21904](../entities/part/fgt-p-21904.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [FGT-P-22331](../entities/part/fgt-p-22331.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-30422](../entities/part/lws-p-30422.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [LWS-P-55031](../entities/part/lws-p-55031.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A1001 Emergency stop activated](../entities/alarm-code/a1001.md), [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md), [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2130 Gearbox oil level low](../entities/alarm-code/a2130.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md), [A3201 Generator winding temperature high](../entities/alarm-code/a3201.md), [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md), [A4105 Pitch system fault](../entities/alarm-code/a4105.md), [A5001 Yaw misalignment](../entities/alarm-code/a5001.md), [A6101 Grid voltage out of range](../entities/alarm-code/a6101.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Status codes: [S200 Ready - low wind](../entities/status-code/s200.md), [S310 Maintenance mode](../entities/status-code/s310.md), [S420 Curtailed - environmental condition](../entities/status-code/s420.md), [S430 Curtailed - grid operator setpoint](../entities/status-code/s430.md), [S510 Stopped - fault](../entities/status-code/s510.md), [S600 Stopped - icing](../entities/status-code/s600.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletins: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md), [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Organisations: [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md), [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)

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
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-31007](../entities/part/awi-31007.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
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
- [Gearbox Fundamentals for Wind Technicians](../sources/gearbox-fundamentals.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
- [IMS bearing](../entities/component/ims-bearing.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-30422](../entities/part/lws-p-30422.md)
- [LWS-P-51207](../entities/part/lws-p-51207.md)
- [LWS-P-55031](../entities/part/lws-p-55031.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md)
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
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../sources/2026-07-18-note-de-releve.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)
- [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
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

[^c1]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 2](../evidence/src-824b788eefc0/para-0002.md) · ✓ quote verified
[^c2]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 7](../evidence/src-824b788eefc0/tbl-01-r0007-r0007.md) · table
[^c3]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 4](../evidence/src-824b788eefc0/para-0004.md) · ✓ quote verified
[^c4]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 6](../evidence/src-824b788eefc0/para-0006.md) · ✓ quote verified
[^c5]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 7](../evidence/src-824b788eefc0/para-0007.md) · ✓ quote verified
[^c6]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 8](../evidence/src-824b788eefc0/para-0008.md) · ✓ quote verified
[^c7]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 14](../evidence/src-824b788eefc0/para-0014.md) · ✓ quote verified
[^c8]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 15](../evidence/src-824b788eefc0/para-0015.md) · ✓ quote verified
[^c9]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 9](../evidence/src-aba30cb7207f/sheet-tasks-r0009-r0009.md) · table
[^c10]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 10](../evidence/src-aba30cb7207f/sheet-tasks-r0010-r0010.md) · table
[^c11]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 10](../evidence/src-824b788eefc0/para-0010.md) · ✓ quote verified
[^c12]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 11](../evidence/src-824b788eefc0/para-0011.md) · ✓ quote verified
[^c13]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 12](../evidence/src-824b788eefc0/para-0012.md) · ✓ quote verified
[^c14]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 17](../evidence/src-824b788eefc0/para-0017.md) · ✓ quote verified
[^c15]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 20](../evidence/src-824b788eefc0/para-0020.md) · ✓ quote verified
[^c16]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 22](../evidence/src-824b788eefc0/para-0022.md) · ✓ quote verified
[^c17]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 23](../evidence/src-824b788eefc0/para-0023.md) · ✓ quote verified
[^c18]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 24](../evidence/src-824b788eefc0/para-0024.md) · ✓ quote verified
[^c19]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 27](../evidence/src-824b788eefc0/para-0027.md) · ✓ quote verified
[^c20]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 28](../evidence/src-824b788eefc0/para-0028.md) · ✓ quote verified
[^c21]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 30](../evidence/src-824b788eefc0/para-0030.md) · ✓ quote verified
[^c22]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1281](../evidence/src-36f5b999211a/r1281-r1281.md) · table
[^c23]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1317](../evidence/src-36f5b999211a/r1317-r1317.md) · table
[^c24]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1313](../evidence/src-36f5b999211a/r1313-r1313.md) · table
[^c25]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1318](../evidence/src-36f5b999211a/r1318-r1318.md) · table
[^c26]: [Work Orders Export through 2026-08-31 — row 78](../evidence/src-9fd435ef5956/r0078-r0078.md) · table
[^c27]: [Shift Handover Note - Day Shift - 18/07/2026 — lines 6–12](../evidence/src-b7a218719725/l0006-l0012.md) · ✓ quote verified
[^c28]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1878](../evidence/src-36f5b999211a/r1878-r1878.md) · table
[^c29]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1879](../evidence/src-36f5b999211a/r1879-r1879.md) · table
[^c30]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 690](../evidence/src-36f5b999211a/r0690-r0690.md) · table
[^c31]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 691](../evidence/src-36f5b999211a/r0691-r0691.md) · table
[^c32]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 712](../evidence/src-36f5b999211a/r0712-r0712.md) · table
[^c33]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 713](../evidence/src-36f5b999211a/r0713-r0713.md) · table
[^c34]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 714](../evidence/src-36f5b999211a/r0714-r0714.md) · table
[^c35]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 737](../evidence/src-36f5b999211a/r0737-r0737.md) · table
[^c36]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 864](../evidence/src-36f5b999211a/r0864-r0864.md) · table
[^c37]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 866](../evidence/src-36f5b999211a/r0866-r0866.md) · table
[^c38]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 868](../evidence/src-36f5b999211a/r0868-r0868.md) · table
[^c39]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 870](../evidence/src-36f5b999211a/r0870-r0870.md) · table
[^c40]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 872](../evidence/src-36f5b999211a/r0872-r0872.md) · table
[^c41]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 874](../evidence/src-36f5b999211a/r0874-r0874.md) · table
[^c42]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 876](../evidence/src-36f5b999211a/r0876-r0876.md) · table
[^c43]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 878](../evidence/src-36f5b999211a/r0878-r0878.md) · table
[^c44]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 880](../evidence/src-36f5b999211a/r0880-r0880.md) · table
[^c45]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 882](../evidence/src-36f5b999211a/r0882-r0882.md) · table
[^c46]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 884](../evidence/src-36f5b999211a/r0884-r0884.md) · table
[^c47]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 886](../evidence/src-36f5b999211a/r0886-r0886.md) · table
[^c48]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 888](../evidence/src-36f5b999211a/r0888-r0888.md) · table
[^c49]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 889](../evidence/src-36f5b999211a/r0889-r0889.md) · table
[^c50]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 909](../evidence/src-36f5b999211a/r0909-r0909.md) · table
[^c51]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 911](../evidence/src-36f5b999211a/r0911-r0911.md) · table
[^c52]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1437](../evidence/src-36f5b999211a/r1437-r1437.md) · table
[^c53]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1459](../evidence/src-36f5b999211a/r1459-r1459.md) · table
[^c54]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1461](../evidence/src-36f5b999211a/r1461-r1461.md) · table
[^c55]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1482](../evidence/src-36f5b999211a/r1482-r1482.md) · table
[^c56]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1466](../evidence/src-36f5b999211a/r1466-r1466.md) · table
[^c57]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1484](../evidence/src-36f5b999211a/r1484-r1484.md) · table
[^c58]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1714](../evidence/src-36f5b999211a/r1714-r1714.md) · table
[^c59]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1736](../evidence/src-36f5b999211a/r1736-r1736.md) · table
[^c60]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1715](../evidence/src-36f5b999211a/r1715-r1715.md) · table
[^c61]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1737](../evidence/src-36f5b999211a/r1737-r1737.md) · table
[^c62]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1738](../evidence/src-36f5b999211a/r1738-r1738.md) · table
[^c63]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1758](../evidence/src-36f5b999211a/r1758-r1758.md) · table
[^c64]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1740](../evidence/src-36f5b999211a/r1740-r1740.md) · table
[^c65]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1761](../evidence/src-36f5b999211a/r1761-r1761.md) · table
