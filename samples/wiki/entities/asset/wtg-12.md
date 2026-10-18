---
id: asset:wtg-12
type: entity
title: WTG-12
summary: WTG-12 is one of the 12 Litware LT-32 CCV turbines at Quellmoor Ridge Wind Farm. It is part of the WTG-01 to WTG-12 scope for site procedures and the PWG 320 to PWG 220 gearbox oil conversion campaign. WTG-12 has recorded SCADA events including pitch system fault, gearbox oil filter differential…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- asset
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: asset
key: wtg-12
aliases:
- text: WTG-12
  lang: en
- text: WTG12
  lang: en
- text: WTG 12
  lang: en
- text: éolienne WTG-12
  lang: fr
- text: Anlage WTG-12
  lang: de
sources:
- src-05b9ebcb4d58
- src-0df0d0598e76
- src-1d8dff18b801
- src-21bd4ddf2ed6
- src-36f5b999211a
- src-383540987d7a
- src-65680eb5afcc
- src-70224c3b9c9f
- src-824b788eefc0
- src-90ea27f71f0f
- src-9fd435ef5956
- src-a14b304454ed
- src-a20331a5431f
- src-a7e8d332dafd
- src-aba30cb7207f
- src-b342a2d5bfdf
- src-b7a218719725
- src-e7cd20fa7984
- src-ecc004b57dd5
---

# WTG-12

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

WTG-12 is one of the 12 [Litware LT-32](../product/lt-32.md) CCV turbines at [Quellmoor Ridge Wind Farm](quellmoor-ridge-wind-farm.md).[^c1][^c2][^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11][^c12][^c13][^c14][^c15] It is part of the [WTG-01](wtg-01.md) to WTG-12 scope for site procedures and the [PWG 320](../product/pwg-320.md) to [PWG 220](../product/pwg-220.md) [gearbox](../component/gearbox.md) oil conversion campaign.[^c16][^c17][^c18][^c19][^c20][^c21][^c22][^c23][^c24][^c25][^c26][^c27][^c28][^c29][^c30][^c31][^c32][^c33][^c34][^c35][^c36][^c37][^c38][^c39][^c40][^c41][^c42][^c43][^c44][^c45][^c46][^c47][^c48][^c49] WTG-12 has recorded SCADA events including [pitch system fault](../alarm-code/a4105.md), [gearbox oil filter differential pressure high](../alarm-code/a2140.md), and [generator winding temperature high](../alarm-code/a3201.md).[^c50][^c51][^c52][^c53][^c54][^c55][^c56][^c57]

## Facts

- The installation is [Quellmoor Ridge Wind Farm](quellmoor-ridge-wind-farm.md), comprising 12 wind turbines [WTG-01](wtg-01.md) to WTG-12 with a capacity of 38.4 MW.[^c1]
- The change was raised on 2025-05-06 by Dario Penwarden, O&M Supervisor, and is a technical lubricant change scoped to WTG-01 through WTG-12.[^c16][^c17][^c18]
- Action 3 is the conversion campaign for WTG-01 to WTG-12, owned by Dario Penwarden and due from 2025-09-01 to 2025-11-28.[^c19]
- The procedure applies to WTG-01 to WTG-12 with [Litware LT-32](../product/lt-32.md) CCV turbines and [Fabrikam FGT-3200](../product/fgt-3200.md) gearboxes.[^c20]
- The scope covers all [gearbox](../component/gearbox.md) oil changes on WTG-01 to WTG-12, including planned changes and changes decided after oil analysis.[^c21]
- The procedure applies to all work on WTG-01 to WTG-12 and on the [Quellmoor Ridge substation](quellmoor-ridge-substation.md) low-voltage boards.[^c22]
- The scope covers all climbing, work in the nacelle and hub, and rescue on WTG-01 to WTG-12.[^c23]
- [WI-GEN-014](../procedure/wi-gen-014.md) is a Revision A work instruction applicable from 2025-09-15 to WTG-01 through WTG-12 with a 690 V double-fed asynchronous [generator](../component/generator.md).[^c58][^c59]
- On 2026-04-01, icing alarms [A7001](../alarm-code/a7001.md) led to [S600 Stopped - icing](../status-code/s600.md) status starts for WTG-12, [WTG-09](wtg-09.md), [WTG-03](wtg-03.md), and [WTG-02](wtg-02.md), with later clears and S600 ends recorded for each turbine in this part.[^c60][^c61][^c62][^c63][^c64][^c65][^c66][^c67]
- On 2026-04-10, [S200 Ready - low wind](../status-code/s200.md) started for WTG-01 through WTG-12 between 11:00:11 and 11:01:28 and ended between 16:00:13 and 16:01:30.[^c68][^c69][^c70][^c71]
- On 2026-04-14 and 2026-04-16, WTG-12 logged [A4105 Pitch system fault](../alarm-code/a4105.md) events with [S510 Stopped - fault](../status-code/s510.md) starts and ends; the first event had value 1 axis and the second had value 2 axis.[^c50][^c51][^c52][^c53]
- On 2026-06-06, [A6101 Grid voltage out of range](../alarm-code/a6101.md) alarms were raised across WTG-01 through WTG-12 with value 87.2 %, accompanied by S510 Stopped - fault START entries; later A6101 clear entries show value 99.6 % and S510 END entries.[^c72][^c73][^c74][^c75][^c76][^c77]
- On 2026-06-18 at about 14:10, A6101 Grid voltage out of range alarms were raised on WTG-01 through WTG-12 at 89.2 %, with S510 Stopped - fault status starts recorded for each turbine in the same sequence.[^c78][^c79][^c80][^c81][^c82][^c83][^c84][^c85][^c86][^c87][^c88][^c89]
- The 2026-06-18 grid-voltage alarms cleared at 99.6 %, and the S510 Stopped - fault statuses ended between [WTG-06](wtg-06.md) at 14:15:04 and WTG-12 at 14:20:10.[^c90][^c91][^c92][^c93]
- On 2026-07-14, WTG-01 through WTG-12 started [S430 Curtailed - grid operator setpoint](../status-code/s430.md) at 20.0 MW; END entries are shown through WTG-12 across the part boundary.[^c94][^c95][^c96][^c97]
- On 2026-07-15 and 2026-07-16, S430 Curtailed - grid operator setpoint at 20.0 MW started for WTG-01 through WTG-12 at about 08:00 and ended at about 18:00.[^c98][^c99][^c100][^c101]
- On 2026-07-24, WTG-01 through WTG-12 entered S200 Ready - low wind status around 07:00 at 2.2 wind_speed_ms and ended S200 around 12:00 at 3.6 wind_speed_ms.[^c102][^c103][^c104][^c105]
- On 2026-08-02, A6101 Grid voltage out of range was raised for WTG-01 through WTG-12 with value 89.3 %, S510 Stopped - fault started, then the A6101 alarms cleared at 99.6 % and S510 ended.[^c106][^c107][^c108][^c109][^c110][^c111]
- WTG-12 raised [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md) at 2.56 bar on 2026-08-02 and cleared it at 1.90 bar later the same day.[^c54][^c55]
- On 2026-08-21, WTG-01 through WTG-12 raised A6101 Grid voltage out of range at 87.8 %, entered S510 Stopped - fault, then cleared A6101 at 99.6 % and ended S510.[^c112][^c113][^c114][^c115][^c116][^c117][^c118][^c119]
- On 2026-08-23, WTG-01 through WTG-12 started S200 Ready - low wind at wind speed 2.4 m/s and later ended S200 at wind speed 3.3 m/s.[^c120][^c121][^c122][^c123]
- WTG-12 had [A3201 Generator winding temperature high](../alarm-code/a3201.md) raised at 147.3 °C and cleared at 139.5 °C on 2026-08-26.[^c56][^c57]
- The export records a completed high-priority modification campaign for gearbox oil conversion from [PWG 320](../product/pwg-320.md) to [PWG 220](../product/pwg-220.md) with a 60 L flush for WTG-01 through WTG-12 under reference MOC-2025-012; each row lists part [PWS-220-D208](../part/pws-220-d208.md) with quantity 3.[^c24][^c25][^c26][^c27][^c28][^c29][^c30][^c31][^c32][^c33][^c34][^c35]
- Gearbox oil sampling work orders WO-26-0341 through WO-26-0352 cover WTG-01 through WTG-12 and are all marked Completed.[^c36][^c37][^c38][^c39][^c40][^c41][^c42][^c43][^c44][^c45][^c46][^c47]
- [Pitch bearing](../component/pitch-bearing.md) bolt re-torque work for [WTG-07](wtg-07.md) through WTG-12 is planned for September 2026, with each title stating 1,450 Nm and 100 % of bolts and reference [SB-LWS-2025-11](../bulletin/sb-lws-2025-11.md) Rev. A.[^c124][^c125][^c126][^c127][^c128][^c129]
- WTG-12 in 2026-02 recorded availability_pct 99.2, energy_mwh 811.8, downtime_h 5.4, and alarm_count 26.[^c130]
- WTG-12 in 2026-04 recorded availability_pct 99.4, energy_mwh 688.1, downtime_h 4.3, and alarm_count 7.[^c131]
- The last listed record is for WTG-12 in 2026-06, with availability_pct 97.8, energy_mwh 496.4, downtime_h 15.8, and alarm_count 14.[^c132]
- Quellmoor Ridge has 12 Litware LT-32 turbines in CCV configuration, identified WTG-01 to WTG-12, with total capacity of 38.4 MW.[^c2]
- The turbine labels shown on the plan are WTG-01, WTG-02, WTG-03, [WTG-04](wtg-04.md), [WTG-05](wtg-05.md), WTG-06, WTG-07, [WTG-08](wtg-08.md), WTG-09, [WTG-10](wtg-10.md), [WTG-11](wtg-11.md), and WTG-12.[^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11][^c12][^c13][^c14]
- The configuration records checked for Quellmoor Ridge Wind Farm showed that all 12 turbines, WTG-01 through WTG-12, were delivered as LT-32 in CCV configuration with Fabrikam FGT-3200 gearboxes, so [SB-LWS-2025-07](../bulletin/sb-lws-2025-07.md) applies to all 12 turbines.[^c15]
- WTG-12 had its anti-pollution kit restocked.[^c133]
- The spill kit of WTG-12 needs a refill, identified with [AWI-20915](../part/awi-20915.md).[^c134]
- PWG 220 conversion status was: nine turbines completed, WTG-11 being converted that day, WTG-12 scheduled for the following Wednesday, and WTG-09 planned for the twenty-fourth if the access road remained open.[^c135][^c136]
- Superseded: The procedure applies to WTG-01 to WTG-12, specified as Litware LT-32 CCV turbines with Fabrikam FGT-3200 gearboxes.[^c48]
- Superseded: The scope covers all gearbox oil changes on WTG-01 to WTG-12, whether planned or decided after oil analysis.[^c49]

## Timeline

- 2025-05-06: The change was raised on 2025-05-06 by Dario Penwarden, O&M Supervisor, and is a technical lubricant change scoped to [WTG-01](wtg-01.md) through WTG-12.[^c16][^c17][^c18]
- 2025-07: The configuration records checked for [Quellmoor Ridge Wind Farm](quellmoor-ridge-wind-farm.md) showed that all 12 turbines, WTG-01 through WTG-12, were delivered as [LT-32](../product/lt-32.md) in CCV configuration with [Fabrikam FGT-3200](../product/fgt-3200.md) gearboxes, so [SB-LWS-2025-07](../bulletin/sb-lws-2025-07.md) applies to all 12 turbines.[^c15]
- 2025-09-01: Action 3 is the conversion campaign for WTG-01 to WTG-12, owned by Dario Penwarden and due from 2025-09-01 to 2025-11-28.[^c19]
- 2025-09-15: [WI-GEN-014](../procedure/wi-gen-014.md) is a Revision A work instruction applicable from 2025-09-15 to WTG-01 through WTG-12 with a 690 V double-fed asynchronous [generator](../component/generator.md).[^c58][^c59]
- 2026-02: WTG-12 in 2026-02 recorded availability_pct 99.2, energy_mwh 811.8, downtime_h 5.4, and alarm_count 26.[^c130]
- 2026-04: WTG-12 in 2026-04 recorded availability_pct 99.4, energy_mwh 688.1, downtime_h 4.3, and alarm_count 7.[^c131]
- 2026-04-01: On 2026-04-01, icing alarms [A7001](../alarm-code/a7001.md) led to [S600 Stopped - icing](../status-code/s600.md) status starts for WTG-12, [WTG-09](wtg-09.md), [WTG-03](wtg-03.md), and [WTG-02](wtg-02.md), with later clears and S600 ends recorded for each turbine in this part.[^c60][^c61][^c62][^c63][^c64][^c65][^c66][^c67]
- 2026-04-10: On 2026-04-10, [S200 Ready - low wind](../status-code/s200.md) started for WTG-01 through WTG-12 between 11:00:11 and 11:01:28 and ended between 16:00:13 and 16:01:30.[^c68][^c69][^c70][^c71]
- 2026-04-14: On 2026-04-14 and 2026-04-16, WTG-12 logged [A4105 Pitch system fault](../alarm-code/a4105.md) events with [S510 Stopped - fault](../status-code/s510.md) starts and ends; the first event had value 1 axis and the second had value 2 axis.[^c50][^c51][^c52][^c53]
- 2026-06: The last listed record is for WTG-12 in 2026-06, with availability_pct 97.8, energy_mwh 496.4, downtime_h 15.8, and alarm_count 14.[^c132]
- 2026-06-06: On 2026-06-06, [A6101 Grid voltage out of range](../alarm-code/a6101.md) alarms were raised across WTG-01 through WTG-12 with value 87.2 %, accompanied by S510 Stopped - fault START entries; later A6101 clear entries show value 99.6 % and S510 END entries.[^c72][^c73][^c74][^c75][^c76][^c77]
- 2026-06-18: On 2026-06-18 at about 14:10, A6101 Grid voltage out of range alarms were raised on WTG-01 through WTG-12 at 89.2 %, with S510 Stopped - fault status starts recorded for each turbine in the same sequence.[^c78][^c79][^c80][^c81][^c82][^c83][^c84][^c85][^c86][^c87][^c88][^c89]
- 2026-06-18: The 2026-06-18 grid-voltage alarms cleared at 99.6 %, and the S510 Stopped - fault statuses ended between [WTG-06](wtg-06.md) at 14:15:04 and WTG-12 at 14:20:10.[^c90][^c91][^c92][^c93]
- 2026-07-14: On 2026-07-14, WTG-01 through WTG-12 started [S430 Curtailed - grid operator setpoint](../status-code/s430.md) at 20.0 MW; END entries are shown through WTG-12 across the part boundary.[^c94][^c95][^c96][^c97]
- 2026-07-15: On 2026-07-15 and 2026-07-16, S430 Curtailed - grid operator setpoint at 20.0 MW started for WTG-01 through WTG-12 at about 08:00 and ended at about 18:00.[^c98][^c99][^c100][^c101]
- 2026-07-24: On 2026-07-24, WTG-01 through WTG-12 entered S200 Ready - low wind status around 07:00 at 2.2 wind_speed_ms and ended S200 around 12:00 at 3.6 wind_speed_ms.[^c102][^c103][^c104][^c105]
- 2026-08-02: On 2026-08-02, A6101 Grid voltage out of range was raised for WTG-01 through WTG-12 with value 89.3 %, S510 Stopped - fault started, then the A6101 alarms cleared at 99.6 % and S510 ended.[^c106][^c107][^c108][^c109][^c110][^c111]
- 2026-08-02: WTG-12 raised [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md) at 2.56 bar on 2026-08-02 and cleared it at 1.90 bar later the same day.[^c54][^c55]
- 2026-08-21: On 2026-08-21, WTG-01 through WTG-12 raised A6101 Grid voltage out of range at 87.8 %, entered S510 Stopped - fault, then cleared A6101 at 99.6 % and ended S510.[^c112][^c113][^c114][^c115][^c116][^c117][^c118][^c119]
- 2026-08-23: On 2026-08-23, WTG-01 through WTG-12 started S200 Ready - low wind at wind speed 2.4 m/s and later ended S200 at wind speed 3.3 m/s.[^c120][^c121][^c122][^c123]
- 2026-08-26: WTG-12 had [A3201 Generator winding temperature high](../alarm-code/a3201.md) raised at 147.3 °C and cleared at 139.5 °C on 2026-08-26.[^c56][^c57]
- 2026-09: [Pitch bearing](../component/pitch-bearing.md) bolt re-torque work for [WTG-07](wtg-07.md) through WTG-12 is planned for September 2026, with each title stating 1,450 Nm and 100 % of bolts and reference [SB-LWS-2025-11](../bulletin/sb-lws-2025-11.md) Rev. A.[^c124][^c125][^c126][^c127][^c128][^c129]

## Documents

- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../../sources/wbs-2026-031-blade-inspection-report.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines](../../sources/sop-loto-001-revc-lockout-tagout.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [KPI Export 2026-H1](../../sources/kpi-export-2026-h1.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../../sources/site-layout-plan.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../../sources/2026-07-18-note-de-releve.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../../sources/2026-07-15-shift-handover.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md) (superseded)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md)
- [A3201 Generator winding temperature high](../alarm-code/a3201.md)
- [A4105 Pitch system fault](../alarm-code/a4105.md)
- [A6101 Grid voltage out of range](../alarm-code/a6101.md)
- [A7001 Ice detected on rotor blades](../alarm-code/a7001.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [AWI-20915](../part/awi-20915.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../../sources/wbs-2026-031-blade-inspection-report.md)
- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [Fabrikam FGT-3200](../product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../organisation/fabrikam-getriebetechnik.md)
- [gearbox](../component/gearbox.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [generator](../component/generator.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [KPI Export 2026-H1](../../sources/kpi-export-2026-h1.md)
- [Litware LT-32](../product/lt-32.md)
- [Litware Wind Systems](../organisation/litware-wind-systems.md)
- [LT-32 CCV](../product/lt-32-ccv.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [oil filter element](../component/oil-filter.md)
- [pitch bearing](../component/pitch-bearing.md)
- [Proseware PWG 220](../product/pwg-220.md)
- [Proseware PWG 320](../product/pwg-320.md)
- [PWS-220-D208](../part/pws-220-d208.md)
- [Quellmoor Ridge substation](quellmoor-ridge-substation.md)
- [Quellmoor Ridge Wind Farm](quellmoor-ridge-wind-farm.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../../sources/site-layout-plan.md)
- [S200 Ready - low wind](../status-code/s200.md)
- [S430 Curtailed - grid operator setpoint](../status-code/s430.md)
- [S510 Stopped - fault](../status-code/s510.md)
- [S600 Stopped - icing](../status-code/s600.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../bulletin/sb-lws-2025-11.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../../sources/2026-07-15-shift-handover.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../../sources/2026-07-18-note-de-releve.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines](../../sources/sop-loto-001-revc-lockout-tagout.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [WI-GEN-014 Generator brush replacement](../procedure/wi-gen-014.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [WTG-01](wtg-01.md)
- [WTG-02](wtg-02.md)
- [WTG-03](wtg-03.md)
- [WTG-04](wtg-04.md)
- [WTG-05](wtg-05.md)
- [WTG-06](wtg-06.md)
- [WTG-07](wtg-07.md)
- [WTG-08](wtg-08.md)
- [WTG-09](wtg-09.md)
- [WTG-10](wtg-10.md)
- [WTG-11](wtg-11.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2) — p. 1](../../evidence/src-a7e8d332dafd/p0001.md) · ✓ quote verified
[^c2]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 2](../../evidence/src-e7cd20fa7984/slide-02.md) · ✓ quote verified
[^c3]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 5](../../evidence/src-a14b304454ed/img-b05.md) · OCR
[^c4]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 6](../../evidence/src-a14b304454ed/img-b06.md) · OCR
[^c5]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 9](../../evidence/src-a14b304454ed/img-b09.md) · OCR
[^c6]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 10](../../evidence/src-a14b304454ed/img-b10.md) · OCR
[^c7]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 11](../../evidence/src-a14b304454ed/img-b11.md) · OCR
[^c8]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 13](../../evidence/src-a14b304454ed/img-b13.md) · OCR
[^c9]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 12](../../evidence/src-a14b304454ed/img-b12.md) · OCR
[^c10]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 14](../../evidence/src-a14b304454ed/img-b14.md) · OCR
[^c11]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 16](../../evidence/src-a14b304454ed/img-b16.md) · OCR
[^c12]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 18](../../evidence/src-a14b304454ed/img-b18.md) · OCR
[^c13]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 20](../../evidence/src-a14b304454ed/img-b20.md) · OCR
[^c14]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 21](../../evidence/src-a14b304454ed/img-b21.md) · OCR
[^c15]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 10–12](../../evidence/src-0df0d0598e76/msg-body-l0010-l0012.md) · paraphrase
[^c16]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 3](../../evidence/src-a20331a5431f/tbl-01-r0003-r0003.md) · table
[^c17]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 4](../../evidence/src-a20331a5431f/tbl-01-r0004-r0004.md) · table
[^c18]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 5](../../evidence/src-a20331a5431f/tbl-01-r0005-r0005.md) · table
[^c19]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 4](../../evidence/src-a20331a5431f/tbl-03-r0004-r0004.md) · table
[^c20]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 1, row 7](../../evidence/src-70224c3b9c9f/tbl-01-r0007-r0007.md) · table
[^c21]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 7](../../evidence/src-70224c3b9c9f/para-0007.md) · ✓ quote verified
[^c22]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 6](../../evidence/src-21bd4ddf2ed6/para-0006.md) · ✓ quote verified
[^c23]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 6](../../evidence/src-05b9ebcb4d58/para-0006.md) · ✓ quote verified
[^c24]: [Work Orders Export through 2026-08-31 — row 2](../../evidence/src-9fd435ef5956/r0002-r0002.md) · table
[^c25]: [Work Orders Export through 2026-08-31 — row 3](../../evidence/src-9fd435ef5956/r0003-r0003.md) · table
[^c26]: [Work Orders Export through 2026-08-31 — row 4](../../evidence/src-9fd435ef5956/r0004-r0004.md) · table
[^c27]: [Work Orders Export through 2026-08-31 — row 5](../../evidence/src-9fd435ef5956/r0005-r0005.md) · table
[^c28]: [Work Orders Export through 2026-08-31 — row 6](../../evidence/src-9fd435ef5956/r0006-r0006.md) · table
[^c29]: [Work Orders Export through 2026-08-31 — row 7](../../evidence/src-9fd435ef5956/r0007-r0007.md) · table
[^c30]: [Work Orders Export through 2026-08-31 — row 8](../../evidence/src-9fd435ef5956/r0008-r0008.md) · table
[^c31]: [Work Orders Export through 2026-08-31 — row 9](../../evidence/src-9fd435ef5956/r0009-r0009.md) · table
[^c32]: [Work Orders Export through 2026-08-31 — row 10](../../evidence/src-9fd435ef5956/r0010-r0010.md) · table
[^c33]: [Work Orders Export through 2026-08-31 — row 11](../../evidence/src-9fd435ef5956/r0011-r0011.md) · table
[^c34]: [Work Orders Export through 2026-08-31 — row 12](../../evidence/src-9fd435ef5956/r0012-r0012.md) · table
[^c35]: [Work Orders Export through 2026-08-31 — row 13](../../evidence/src-9fd435ef5956/r0013-r0013.md) · table
[^c36]: [Work Orders Export through 2026-08-31 — row 56](../../evidence/src-9fd435ef5956/r0056-r0056.md) · table
[^c37]: [Work Orders Export through 2026-08-31 — row 57](../../evidence/src-9fd435ef5956/r0057-r0057.md) · table
[^c38]: [Work Orders Export through 2026-08-31 — row 58](../../evidence/src-9fd435ef5956/r0058-r0058.md) · table
[^c39]: [Work Orders Export through 2026-08-31 — row 59](../../evidence/src-9fd435ef5956/r0059-r0059.md) · table
[^c40]: [Work Orders Export through 2026-08-31 — row 60](../../evidence/src-9fd435ef5956/r0060-r0060.md) · table
[^c41]: [Work Orders Export through 2026-08-31 — row 61](../../evidence/src-9fd435ef5956/r0061-r0061.md) · table
[^c42]: [Work Orders Export through 2026-08-31 — row 62](../../evidence/src-9fd435ef5956/r0062-r0062.md) · table
[^c43]: [Work Orders Export through 2026-08-31 — row 63](../../evidence/src-9fd435ef5956/r0063-r0063.md) · table
[^c44]: [Work Orders Export through 2026-08-31 — row 64](../../evidence/src-9fd435ef5956/r0064-r0064.md) · table
[^c45]: [Work Orders Export through 2026-08-31 — row 65](../../evidence/src-9fd435ef5956/r0065-r0065.md) · table
[^c46]: [Work Orders Export through 2026-08-31 — row 66](../../evidence/src-9fd435ef5956/r0066-r0066.md) · table
[^c47]: [Work Orders Export through 2026-08-31 — row 67](../../evidence/src-9fd435ef5956/r0067-r0067.md) · table
[^c48]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 7](../../evidence/src-90ea27f71f0f/tbl-01-r0007-r0007.md) · table
[^c49]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 6](../../evidence/src-90ea27f71f0f/para-0006.md) · ✓ quote verified
[^c50]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 140](../../evidence/src-36f5b999211a/r0140-r0140.md) · table
[^c51]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 143](../../evidence/src-36f5b999211a/r0143-r0143.md) · table
[^c52]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 154](../../evidence/src-36f5b999211a/r0154-r0154.md) · table
[^c53]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 157](../../evidence/src-36f5b999211a/r0157-r0157.md) · table
[^c54]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1436](../../evidence/src-36f5b999211a/r1436-r1436.md) · table
[^c55]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1485](../../evidence/src-36f5b999211a/r1485-r1485.md) · table
[^c56]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1878](../../evidence/src-36f5b999211a/r1878-r1878.md) · table
[^c57]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1879](../../evidence/src-36f5b999211a/r1879-r1879.md) · table
[^c58]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 2](../../evidence/src-824b788eefc0/para-0002.md) · ✓ quote verified
[^c59]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 7](../../evidence/src-824b788eefc0/tbl-01-r0007-r0007.md) · table
[^c60]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 4](../../evidence/src-36f5b999211a/r0004-r0004.md) · table
[^c61]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 5](../../evidence/src-36f5b999211a/r0005-r0005.md) · table
[^c62]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 6](../../evidence/src-36f5b999211a/r0006-r0006.md) · table
[^c63]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 7](../../evidence/src-36f5b999211a/r0007-r0007.md) · table
[^c64]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 8](../../evidence/src-36f5b999211a/r0008-r0008.md) · table
[^c65]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 9](../../evidence/src-36f5b999211a/r0009-r0009.md) · table
[^c66]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 12](../../evidence/src-36f5b999211a/r0012-r0012.md) · table
[^c67]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 13](../../evidence/src-36f5b999211a/r0013-r0013.md) · table
[^c68]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 106](../../evidence/src-36f5b999211a/r0106-r0106.md) · table
[^c69]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 117](../../evidence/src-36f5b999211a/r0117-r0117.md) · table
[^c70]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 118](../../evidence/src-36f5b999211a/r0118-r0118.md) · table
[^c71]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 129](../../evidence/src-36f5b999211a/r0129-r0129.md) · table
[^c72]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 690](../../evidence/src-36f5b999211a/r0690-r0690.md) · table
[^c73]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 691](../../evidence/src-36f5b999211a/r0691-r0691.md) · table
[^c74]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 712](../../evidence/src-36f5b999211a/r0712-r0712.md) · table
[^c75]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 713](../../evidence/src-36f5b999211a/r0713-r0713.md) · table
[^c76]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 714](../../evidence/src-36f5b999211a/r0714-r0714.md) · table
[^c77]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 737](../../evidence/src-36f5b999211a/r0737-r0737.md) · table
[^c78]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 864](../../evidence/src-36f5b999211a/r0864-r0864.md) · table
[^c79]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 866](../../evidence/src-36f5b999211a/r0866-r0866.md) · table
[^c80]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 868](../../evidence/src-36f5b999211a/r0868-r0868.md) · table
[^c81]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 870](../../evidence/src-36f5b999211a/r0870-r0870.md) · table
[^c82]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 872](../../evidence/src-36f5b999211a/r0872-r0872.md) · table
[^c83]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 874](../../evidence/src-36f5b999211a/r0874-r0874.md) · table
[^c84]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 876](../../evidence/src-36f5b999211a/r0876-r0876.md) · table
[^c85]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 878](../../evidence/src-36f5b999211a/r0878-r0878.md) · table
[^c86]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 880](../../evidence/src-36f5b999211a/r0880-r0880.md) · table
[^c87]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 882](../../evidence/src-36f5b999211a/r0882-r0882.md) · table
[^c88]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 884](../../evidence/src-36f5b999211a/r0884-r0884.md) · table
[^c89]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 886](../../evidence/src-36f5b999211a/r0886-r0886.md) · table
[^c90]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 888](../../evidence/src-36f5b999211a/r0888-r0888.md) · table
[^c91]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 889](../../evidence/src-36f5b999211a/r0889-r0889.md) · table
[^c92]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 909](../../evidence/src-36f5b999211a/r0909-r0909.md) · table
[^c93]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 911](../../evidence/src-36f5b999211a/r0911-r0911.md) · table
[^c94]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1202](../../evidence/src-36f5b999211a/r1202-r1202.md) · table
[^c95]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1213](../../evidence/src-36f5b999211a/r1213-r1213.md) · table
[^c96]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1214](../../evidence/src-36f5b999211a/r1214-r1214.md) · table
[^c97]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1225](../../evidence/src-36f5b999211a/r1225-r1225.md) · table
[^c98]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1230](../../evidence/src-36f5b999211a/r1230-r1230.md) · table
[^c99]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1257](../../evidence/src-36f5b999211a/r1257-r1257.md) · table
[^c100]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1267](../../evidence/src-36f5b999211a/r1267-r1267.md) · table
[^c101]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1296](../../evidence/src-36f5b999211a/r1296-r1296.md) · table
[^c102]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1376](../../evidence/src-36f5b999211a/r1376-r1376.md) · table
[^c103]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1387](../../evidence/src-36f5b999211a/r1387-r1387.md) · table
[^c104]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1393](../../evidence/src-36f5b999211a/r1393-r1393.md) · table
[^c105]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1404](../../evidence/src-36f5b999211a/r1404-r1404.md) · table
[^c106]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1437](../../evidence/src-36f5b999211a/r1437-r1437.md) · table
[^c107]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1459](../../evidence/src-36f5b999211a/r1459-r1459.md) · table
[^c108]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1461](../../evidence/src-36f5b999211a/r1461-r1461.md) · table
[^c109]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1482](../../evidence/src-36f5b999211a/r1482-r1482.md) · table
[^c110]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1466](../../evidence/src-36f5b999211a/r1466-r1466.md) · table
[^c111]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1484](../../evidence/src-36f5b999211a/r1484-r1484.md) · table
[^c112]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1714](../../evidence/src-36f5b999211a/r1714-r1714.md) · table
[^c113]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1736](../../evidence/src-36f5b999211a/r1736-r1736.md) · table
[^c114]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1715](../../evidence/src-36f5b999211a/r1715-r1715.md) · table
[^c115]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1737](../../evidence/src-36f5b999211a/r1737-r1737.md) · table
[^c116]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1738](../../evidence/src-36f5b999211a/r1738-r1738.md) · table
[^c117]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1758](../../evidence/src-36f5b999211a/r1758-r1758.md) · table
[^c118]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1740](../../evidence/src-36f5b999211a/r1740-r1740.md) · table
[^c119]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1761](../../evidence/src-36f5b999211a/r1761-r1761.md) · table
[^c120]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1788](../../evidence/src-36f5b999211a/r1788-r1788.md) · table
[^c121]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1799](../../evidence/src-36f5b999211a/r1799-r1799.md) · table
[^c122]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1808](../../evidence/src-36f5b999211a/r1808-r1808.md) · table
[^c123]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1819](../../evidence/src-36f5b999211a/r1819-r1819.md) · table
[^c124]: [Work Orders Export through 2026-08-31 — row 90](../../evidence/src-9fd435ef5956/r0090-r0090.md) · table
[^c125]: [Work Orders Export through 2026-08-31 — row 91](../../evidence/src-9fd435ef5956/r0091-r0091.md) · table
[^c126]: [Work Orders Export through 2026-08-31 — row 92](../../evidence/src-9fd435ef5956/r0092-r0092.md) · table
[^c127]: [Work Orders Export through 2026-08-31 — row 93](../../evidence/src-9fd435ef5956/r0093-r0093.md) · table
[^c128]: [Work Orders Export through 2026-08-31 — row 94](../../evidence/src-9fd435ef5956/r0094-r0094.md) · table
[^c129]: [Work Orders Export through 2026-08-31 — row 95](../../evidence/src-9fd435ef5956/r0095-r0095.md) · table
[^c130]: [KPI Export 2026-H1 — row 25](../../evidence/src-65680eb5afcc/r0025-r0025.md) · table
[^c131]: [KPI Export 2026-H1 — row 49](../../evidence/src-65680eb5afcc/r0049-r0049.md) · table
[^c132]: [KPI Export 2026-H1 — row 73](../../evidence/src-65680eb5afcc/r0073-r0073.md) · table
[^c133]: [Shift Handover Note - Day Shift - 18/07/2026 — lines 6–12](../../evidence/src-b7a218719725/l0006-l0012.md) · ✓ quote verified
[^c134]: [Shift handover - 2026-07-15 (day shift to night shift) — lines 24–25](../../evidence/src-1d8dff18b801/l0024-l0025.md) · ✓ quote verified
[^c135]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:11–00:19](../../evidence/src-ecc004b57dd5/cue-00-00-11.md) · ✓ quote verified
[^c136]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:19–00:27](../../evidence/src-ecc004b57dd5/cue-00-00-19.md) · ✓ quote verified
