---
id: asset:wtg-07
type: entity
title: WTG-07
summary: WTG-07 is a turbine at Quellmoor Ridge with a main gearbox, a Fabrikam FGT-3200 serial FGT-3200-18-07752. In 2026, WTG-07 logged repeated gearbox oil over-temperature alarms and trips, and it was limited to 2.6 MW before the limit was removed on 2026-06-25. WTG-07's oil sampling report recorded…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- asset
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: asset
key: wtg-07
aliases:
- text: WTG-07
  lang: en
- text: WTG07
  lang: en
- text: WTG 07
  lang: en
- text: éolienne WTG-07
  lang: fr
- text: Anlage WTG-07
  lang: de
sources:
- src-05b9ebcb4d58
- src-0df0d0598e76
- src-15df96905f07
- src-1d8dff18b801
- src-32ed1eb40d24
- src-36f5b999211a
- src-383540987d7a
- src-42566abae6ef
- src-65680eb5afcc
- src-70224c3b9c9f
- src-824b788eefc0
- src-86cb00fd2f6b
- src-90ea27f71f0f
- src-9107d71821bf
- src-990a047180b7
- src-9fd435ef5956
- src-a011da5de982
- src-a14b304454ed
- src-a20331a5431f
- src-a7e8d332dafd
- src-aba30cb7207f
- src-b342a2d5bfdf
- src-b7a218719725
- src-e7cd20fa7984
---

# WTG-07

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

WTG-07 is a turbine at [Quellmoor Ridge](quellmoor-ridge-wind-farm.md) with a main [gearbox](../component/gearbox.md), a [Fabrikam FGT-3200](../product/fgt-3200.md) serial FGT-3200-18-07752.[^c1] In 2026, WTG-07 logged repeated gearbox oil over-temperature alarms and trips, and it was limited to 2.6 MW before the limit was removed on 2026-06-25.[^c2][^c3][^c4][^c5][^c6][^c7][^c8][^c9] WTG-07's oil sampling report recorded condition ALERT, and the turbine still has elevated vibration while waiting for a bearing replacement.[^c10][^c11][^c12][^c13][^c14]

## Facts

- The report is oil analysis report TR-OA-2026-0614 for [gearbox](../component/gearbox.md) oil from WTG-07 at [Quellmoor Ridge](quellmoor-ridge-wind-farm.md).[^c1]
- The asset is the WTG-07 main gearbox, a [Fabrikam FGT-3200](../product/fgt-3200.md) with serial FGT-3200-18-07752.[^c1]
- The incident concerns WTG-07, serial LT32-19-0421, with gearbox FGT-3200-18-07752.[^c15]
- Between 2026-04-09 and 2026-06-21, WTG-07 logged 27 [A2101](../alarm-code/a2101.md) warnings at 75 °C and two [A2102](../alarm-code/a2102.md) trips at 82 °C, while no other turbine logged an A2101 warning in that period.[^c2]
- From 2026-06-01, WTG-07 was limited to 2.6 MW by the park controller with daily oil-temperature checks, and the limit was removed on 2026-06-25 after the D6 corrective actions.[^c3]
- Verification reports no A2101 warning on WTG-07 since 2026-06-24, but vibration remains above the alarm level until the bearing is replaced.[^c11]
- WTG-07 oil sampling report TR-OA-2026-0614 recorded [PWG 220](../product/pwg-220.md) oil, Fe of 64 ppm, PQ index of 112, condition ALERT, and next sample due 2026-07-10 with resampling within 30 days.[^c10]
- On 2026-05-30, WTG-07 raised A2101 Gearbox oil sump temperature high at 75.3 °C, then raised A2102 Gearbox oil sump temperature trip at 82.6 °C and entered [S510 Stopped - fault](../status-code/s510.md).[^c4][^c5][^c6]
- WTG-07 cleared the 2026-05-30 A2102 trip at 79.4 °C, cleared the A2101 high-temperature alarm at 72.8 °C, and ended S510 Stopped - fault.[^c16][^c17][^c18]
- On 2026-06-19, WTG-07 first raised A2101 Gearbox oil sump temperature high at 75.6 °C, then raised A2102 Gearbox oil sump temperature trip at 83.4 °C and entered S510 Stopped - fault.[^c7][^c8][^c9]
- The movements sheet records a 2026-06-24 issue of quantity -1 for [LWS-P-30418](../part/lws-p-30418.md) against WO-26-0398 for WTG-07.[^c19]
- The first recorded row is dated 2026-01-05 for WTG-07 and sensor GBX HSS GS radial, with velocity_rms_mm_s 2.1, envelope_ge 0.30, oil_temp_avg_c 53.4 and power_avg_kw 1126.[^c20]
- On 2026-02-23, WTG-07 recorded velocity_rms_mm_s 2.6, envelope_ge 0.63, oil_temp_avg_c 55.2 and power_avg_kw 1229.[^c21]
- On 2026-03-30, WTG-07 recorded velocity_rms_mm_s 3.2, envelope_ge 0.94, oil_temp_avg_c 52.9 and power_avg_kw 1172.[^c22]
- On 2026-04-06, WTG-07 recorded velocity_rms_mm_s 3.4, envelope_ge 1.12, oil_temp_avg_c 69.9 and power_avg_kw 747.[^c23]
- On 2026-05-25, WTG-07 recorded velocity_rms_mm_s 4.7, envelope_ge 1.72, oil_temp_avg_c 66.1 and power_avg_kw 780.[^c24]
- On 2026-06-15, WTG-07 recorded velocity_rms_mm_s 5.2, envelope_ge 2.14, oil_temp_avg_c 66.6 and power_avg_kw 929.[^c25]
- On 2026-06-22, WTG-07 recorded velocity_rms_mm_s 5.4, envelope_ge 2.12, oil_temp_avg_c 70.5 and power_avg_kw 849.[^c26]
- On 2026-07-20, WTG-07 recorded velocity_rms_mm_s 5.3, envelope_ge 2.17, oil_temp_avg_c 60.2 and power_avg_kw 1055.[^c27]
- On 2026-08-24, WTG-07 recorded velocity_rms_mm_s 5.6, envelope_ge 2.36, oil_temp_avg_c 59.4 and power_avg_kw 774.[^c28]
- The final recorded row is dated 2026-08-31 for WTG-07 and sensor GBX HSS GS radial, with velocity_rms_mm_s 5.7, envelope_ge 2.26, oil_temp_avg_c 57.7 and power_avg_kw 946.[^c29]
- For WTG-07 under INC-2026-006, WO-26-0398 replaced the [oil cooler fan motor](../component/cooler-fan-motor.md) with part LWS-P-30418 quantity 1, and WO-26-0399 cleaned the [oil cooler](../component/oil-cooler.md) radiator with remarks that fins were about 40 % blocked by insects and pollen.[^c30][^c31]
- WO-26-0412 for WTG-07 is a high-priority corrective-maintenance work order to replace the generator-side [HSS bearing](../component/hss-bearing.md), is waiting for parts, lists part [FGT-P-22328](../part/fgt-p-22328.md) quantity 1, and remarks that vibration is above the alarm level of 4.5 mm/s.[^c12]
- [Pitch bearing](../component/pitch-bearing.md) bolt re-torque work for WTG-07 through [WTG-12](wtg-12.md) is planned for September 2026, with each title stating 1,450 Nm and 100 % of bolts and reference [SB-LWS-2025-11](../bulletin/sb-lws-2025-11.md) Rev. A.[^c32][^c33][^c34][^c35][^c36][^c37]
- WTG-07 in 2026-05 recorded availability_pct 95.2, energy_mwh 555.7, downtime_h 35.7, and alarm_count 31.[^c38]
- WTG-07 in 2026-06 recorded availability_pct 90.4, energy_mwh 386.5, downtime_h 69.1, and alarm_count 38.[^c39]
- For WTG-07, availability_pct changed from 95.2 in 2026-05 to 90.4 in 2026-06, while downtime_h changed from 35.7 to 69.1 and alarm_count changed from 31 to 38.[^c38][^c39]
- WTG-07 availability was 95.2 % because of gearbox trips.[^c40]
- 8D INC-2026-006 was opened on 2026-05-30 for the WTG-07 gearbox over-temperature issue.[^c41]
- WTG-07 had been limited to 2.6 MW since 2026-06-01.[^c41]
- Callum Rydings was assigned to inspect the WTG-07 cooler fan and radiator, with the inspection planned for 2026-06-24.[^c41]
- The action list assigned Callum Rydings to inspect the WTG-07 oil cooler fan and radiator by 2026-06-24.[^c42]
- The turbine labels shown on the plan are [WTG-01](wtg-01.md), [WTG-02](wtg-02.md), [WTG-03](wtg-03.md), [WTG-04](wtg-04.md), [WTG-05](wtg-05.md), [WTG-06](wtg-06.md), WTG-07, [WTG-08](wtg-08.md), [WTG-09](wtg-09.md), [WTG-10](wtg-10.md), [WTG-11](wtg-11.md), and WTG-12.[^c43][^c44][^c45][^c46][^c47][^c48][^c49][^c50][^c51][^c52][^c53][^c54]
- WO-26-0412 for WTG-07 HSS bearing replacement cannot start until the bearings arrive.[^c13]
- WTG-07 continues [running](../status-code/s100.md) with vibration above the alarm level, so Yusuf requested weekly vibration reviews.[^c13]
- Oil cooler fan motor LWS-P-30418 is also below minimum after the WTG-07 repair, with 1 on hand and a minimum of 2.[^c55]
- WTG-07 reached a maximum oil temperature of 66 °C that day, had no alarm, and still had high vibration while awaiting the bearing.[^c56]
- WO-26-0439 for WTG-02 was raised on 24/07 and is waiting for the same bearing as WTG-07, part FGT-P-22328.[^c57]
- WTG-07 has had no oil temperature alarm since 24/06.[^c57]
- WTG-07 still has HSS bearing vibration around 5.3 mm/s; oil temperature has been normal since the fan motor replacement, and WO-26-0412 is waiting for the bearing.[^c14]
- The next shift should watch WTG-07 oil temperature in the afternoon.[^c58]

## Timeline

- 2026-01-05: The first recorded row is dated 2026-01-05 for WTG-07 and sensor GBX HSS GS radial, with velocity_rms_mm_s 2.1, envelope_ge 0.30, oil_temp_avg_c 53.4 and power_avg_kw 1126.[^c20]
- 2026-02-23: On 2026-02-23, WTG-07 recorded velocity_rms_mm_s 2.6, envelope_ge 0.63, oil_temp_avg_c 55.2 and power_avg_kw 1229.[^c21]
- 2026-03-30: On 2026-03-30, WTG-07 recorded velocity_rms_mm_s 3.2, envelope_ge 0.94, oil_temp_avg_c 52.9 and power_avg_kw 1172.[^c22]
- 2026-04-06: On 2026-04-06, WTG-07 recorded velocity_rms_mm_s 3.4, envelope_ge 1.12, oil_temp_avg_c 69.9 and power_avg_kw 747.[^c23]
- 2026-04-09: Between 2026-04-09 and 2026-06-21, WTG-07 logged 27 [A2101](../alarm-code/a2101.md) warnings at 75 °C and two [A2102](../alarm-code/a2102.md) trips at 82 °C, while no other turbine logged an A2101 warning in that period.[^c2]
- 2026-05: For WTG-07, availability_pct changed from 95.2 in 2026-05 to 90.4 in 2026-06, while downtime_h changed from 35.7 to 69.1 and alarm_count changed from 31 to 38.[^c38][^c39]
- 2026-05: WTG-07 in 2026-05 recorded availability_pct 95.2, energy_mwh 555.7, downtime_h 35.7, and alarm_count 31.[^c38]
- 2026-05-25: On 2026-05-25, WTG-07 recorded velocity_rms_mm_s 4.7, envelope_ge 1.72, oil_temp_avg_c 66.1 and power_avg_kw 780.[^c24]
- 2026-05-30: 8D INC-2026-006 was opened on 2026-05-30 for the WTG-07 [gearbox](../component/gearbox.md) over-temperature issue.[^c41]
- 2026-05-30: On 2026-05-30, WTG-07 raised A2101 Gearbox oil sump temperature high at 75.3 °C, then raised A2102 Gearbox oil sump temperature trip at 82.6 °C and entered [S510 Stopped - fault](../status-code/s510.md).[^c4][^c5][^c6]
- 2026-05-30: WTG-07 cleared the 2026-05-30 A2102 trip at 79.4 °C, cleared the A2101 high-temperature alarm at 72.8 °C, and ended S510 Stopped - fault.[^c16][^c17][^c18]
- 2026-06: WTG-07 in 2026-06 recorded availability_pct 90.4, energy_mwh 386.5, downtime_h 69.1, and alarm_count 38.[^c39]
- 2026-06-01: From 2026-06-01, WTG-07 was limited to 2.6 MW by the park controller with daily oil-temperature checks, and the limit was removed on 2026-06-25 after the D6 corrective actions.[^c3]
- 2026-06-01: WTG-07 had been limited to 2.6 MW since 2026-06-01.[^c41]
- 2026-06-15: On 2026-06-15, WTG-07 recorded velocity_rms_mm_s 5.2, envelope_ge 2.14, oil_temp_avg_c 66.6 and power_avg_kw 929.[^c25]
- 2026-06-19: On 2026-06-19, WTG-07 first raised A2101 Gearbox oil sump temperature high at 75.6 °C, then raised A2102 Gearbox oil sump temperature trip at 83.4 °C and entered S510 Stopped - fault.[^c7][^c8][^c9]
- 2026-06-22: On 2026-06-22, WTG-07 recorded velocity_rms_mm_s 5.4, envelope_ge 2.12, oil_temp_avg_c 70.5 and power_avg_kw 849.[^c26]
- 2026-06-24: Callum Rydings was assigned to inspect the WTG-07 cooler fan and radiator, with the inspection planned for 2026-06-24.[^c41]
- 2026-06-24: The action list assigned Callum Rydings to inspect the WTG-07 [oil cooler](../component/oil-cooler.md) fan and radiator by 2026-06-24.[^c42]
- 2026-06-24: The movements sheet records a 2026-06-24 issue of quantity -1 for [LWS-P-30418](../part/lws-p-30418.md) against WO-26-0398 for WTG-07.[^c19]
- 2026-06-24: Verification reports no A2101 warning on WTG-07 since 2026-06-24, but vibration remains above the alarm level until the bearing is replaced.[^c11]
- 2026-07-10: WTG-07 oil sampling report TR-OA-2026-0614 recorded [PWG 220](../product/pwg-220.md) oil, Fe of 64 ppm, PQ index of 112, condition ALERT, and next sample due 2026-07-10 with resampling within 30 days.[^c10]
- 2026-07-20: On 2026-07-20, WTG-07 recorded velocity_rms_mm_s 5.3, envelope_ge 2.17, oil_temp_avg_c 60.2 and power_avg_kw 1055.[^c27]
- 2026-08-24: On 2026-08-24, WTG-07 recorded velocity_rms_mm_s 5.6, envelope_ge 2.36, oil_temp_avg_c 59.4 and power_avg_kw 774.[^c28]
- 2026-08-31: The final recorded row is dated 2026-08-31 for WTG-07 and sensor GBX HSS GS radial, with velocity_rms_mm_s 5.7, envelope_ge 2.26, oil_temp_avg_c 57.7 and power_avg_kw 946.[^c29]
- 2026-09: [Pitch bearing](../component/pitch-bearing.md) bolt re-torque work for WTG-07 through [WTG-12](wtg-12.md) is planned for September 2026, with each title stating 1,450 Nm and 100 % of bolts and reference [SB-LWS-2025-11](../bulletin/sb-lws-2025-11.md) Rev. A.[^c32][^c33][^c34][^c35][^c36][^c37]

## Documents

- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../../sources/wbs-2026-031-blade-inspection-report.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026](../../sources/vibration-trend-wtg-07-gearbox-2026.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [KPI Export 2026-H1](../../sources/kpi-export-2026-h1.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../../sources/site-layout-plan.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../../sources/2026-07-18-note-de-releve.md)
- [Shift Handover for 2026-07-29 Day Shift](../../sources/2026-07-29-shift-handover.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../../sources/2026-07-15-shift-handover.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md) (superseded)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [A2101 Gearbox oil sump temperature high](../alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../alarm-code/a2102.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../../sources/wbs-2026-031-blade-inspection-report.md)
- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [Fabrikam FGT-3200](../product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../organisation/fabrikam-getriebetechnik.md)
- [FGT-P-22328](../part/fgt-p-22328.md)
- [gearbox](../component/gearbox.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [generator](../component/generator.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [HSS bearing](../component/hss-bearing.md)
- [KPI Export 2026-H1](../../sources/kpi-export-2026-h1.md)
- [LWS-P-30418](../part/lws-p-30418.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [oil cooler](../component/oil-cooler.md)
- [oil cooler fan motor](../component/cooler-fan-motor.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [pitch bearing](../component/pitch-bearing.md)
- [Proseware PWG 220](../product/pwg-220.md)
- [Quellmoor Ridge Wind Farm](quellmoor-ridge-wind-farm.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../../sources/site-layout-plan.md)
- [S100 Running](../status-code/s100.md)
- [S510 Stopped - fault](../status-code/s510.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../bulletin/sb-lws-2025-11.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../../sources/2026-07-15-shift-handover.md)
- [Shift Handover for 2026-07-29 Day Shift](../../sources/2026-07-29-shift-handover.md)
- [Shift Handover Note - Day Shift - 18/07/2026](../../sources/2026-07-18-note-de-releve.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [Trey Research Laboratories](../organisation/trey-research-laboratories.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [WTG-01](wtg-01.md)
- [WTG-02](wtg-02.md)
- [WTG-03](wtg-03.md)
- [WTG-04](wtg-04.md)
- [WTG-05](wtg-05.md)
- [WTG-06](wtg-06.md)
- [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026](../../sources/vibration-trend-wtg-07-gearbox-2026.md)
- [WTG-08](wtg-08.md)
- [WTG-09](wtg-09.md)
- [WTG-10](wtg-10.md)
- [WTG-11](wtg-11.md)
- [WTG-12](wtg-12.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 1](../../evidence/src-990a047180b7/p0001.md) · ✓ quote verified
[^c2]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 6](../../evidence/src-86cb00fd2f6b/para-0006.md) · ✓ quote verified
[^c3]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 10](../../evidence/src-86cb00fd2f6b/para-0010.md) · ✓ quote verified
[^c4]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 550](../../evidence/src-36f5b999211a/r0550-r0550.md) · table
[^c5]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 551](../../evidence/src-36f5b999211a/r0551-r0551.md) · table
[^c6]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 552](../../evidence/src-36f5b999211a/r0552-r0552.md) · table
[^c7]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 946](../../evidence/src-36f5b999211a/r0946-r0946.md) · table
[^c8]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 947](../../evidence/src-36f5b999211a/r0947-r0947.md) · table
[^c9]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 948](../../evidence/src-36f5b999211a/r0948-r0948.md) · table
[^c10]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Oil sampling", row 8](../../evidence/src-aba30cb7207f/sheet-oil-sampling-r0008-r0008.md) · table
[^c11]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 24](../../evidence/src-86cb00fd2f6b/para-0024.md) · ✓ quote verified
[^c12]: [Work Orders Export through 2026-08-31 — row 73](../../evidence/src-9fd435ef5956/r0073-r0073.md) · table
[^c13]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 14–16](../../evidence/src-9107d71821bf/msg-body-l0014-l0016.md) · ✓ quote verified
[^c14]: [Shift handover - 2026-07-15 (day shift to night shift) — lines 11–14](../../evidence/src-1d8dff18b801/l0011-l0014.md) · ✓ quote verified
[^c15]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 1, row 3](../../evidence/src-86cb00fd2f6b/tbl-01-r0003-r0003.md) · table
[^c16]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 555](../../evidence/src-36f5b999211a/r0555-r0555.md) · table
[^c17]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 558](../../evidence/src-36f5b999211a/r0558-r0558.md) · table
[^c18]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 559](../../evidence/src-36f5b999211a/r0559-r0559.md) · table
[^c19]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Movements", row 7](../../evidence/src-42566abae6ef/sheet-movements-r0007-r0007.md) · table
[^c20]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 2](../../evidence/src-32ed1eb40d24/r0002-r0002.md) · table
[^c21]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 9](../../evidence/src-32ed1eb40d24/r0009-r0009.md) · table
[^c22]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 14](../../evidence/src-32ed1eb40d24/r0014-r0014.md) · table
[^c23]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 15](../../evidence/src-32ed1eb40d24/r0015-r0015.md) · table
[^c24]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 22](../../evidence/src-32ed1eb40d24/r0022-r0022.md) · table
[^c25]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 25](../../evidence/src-32ed1eb40d24/r0025-r0025.md) · table
[^c26]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 26](../../evidence/src-32ed1eb40d24/r0026-r0026.md) · table
[^c27]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 30](../../evidence/src-32ed1eb40d24/r0030-r0030.md) · table
[^c28]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 35](../../evidence/src-32ed1eb40d24/r0035-r0035.md) · table
[^c29]: [WTG-07 GBX HSS GS Radial Vibration Trend Data, 2026 — row 36](../../evidence/src-32ed1eb40d24/r0036-r0036.md) · table
[^c30]: [Work Orders Export through 2026-08-31 — row 70](../../evidence/src-9fd435ef5956/r0070-r0070.md) · table
[^c31]: [Work Orders Export through 2026-08-31 — row 71](../../evidence/src-9fd435ef5956/r0071-r0071.md) · table
[^c32]: [Work Orders Export through 2026-08-31 — row 90](../../evidence/src-9fd435ef5956/r0090-r0090.md) · table
[^c33]: [Work Orders Export through 2026-08-31 — row 91](../../evidence/src-9fd435ef5956/r0091-r0091.md) · table
[^c34]: [Work Orders Export through 2026-08-31 — row 92](../../evidence/src-9fd435ef5956/r0092-r0092.md) · table
[^c35]: [Work Orders Export through 2026-08-31 — row 93](../../evidence/src-9fd435ef5956/r0093-r0093.md) · table
[^c36]: [Work Orders Export through 2026-08-31 — row 94](../../evidence/src-9fd435ef5956/r0094-r0094.md) · table
[^c37]: [Work Orders Export through 2026-08-31 — row 95](../../evidence/src-9fd435ef5956/r0095-r0095.md) · table
[^c38]: [KPI Export 2026-H1 — row 56](../../evidence/src-65680eb5afcc/r0056-r0056.md) · table
[^c39]: [KPI Export 2026-H1 — row 68](../../evidence/src-65680eb5afcc/r0068-r0068.md) · table
[^c40]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 8](../../evidence/src-15df96905f07/para-0008.md) · ✓ quote verified
[^c41]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 10](../../evidence/src-15df96905f07/para-0010.md) · ✓ quote verified
[^c42]: [Monthly O&M Review Minutes – 2026-06-18 — table 1, row 2](../../evidence/src-15df96905f07/tbl-01-r0002-r0002.md) · table
[^c43]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 5](../../evidence/src-a14b304454ed/img-b05.md) · OCR
[^c44]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 6](../../evidence/src-a14b304454ed/img-b06.md) · OCR
[^c45]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 9](../../evidence/src-a14b304454ed/img-b09.md) · OCR
[^c46]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 10](../../evidence/src-a14b304454ed/img-b10.md) · OCR
[^c47]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 11](../../evidence/src-a14b304454ed/img-b11.md) · OCR
[^c48]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 13](../../evidence/src-a14b304454ed/img-b13.md) · OCR
[^c49]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 12](../../evidence/src-a14b304454ed/img-b12.md) · OCR
[^c50]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 14](../../evidence/src-a14b304454ed/img-b14.md) · OCR
[^c51]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 16](../../evidence/src-a14b304454ed/img-b16.md) · OCR
[^c52]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 18](../../evidence/src-a14b304454ed/img-b18.md) · OCR
[^c53]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 20](../../evidence/src-a14b304454ed/img-b20.md) · OCR
[^c54]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 21](../../evidence/src-a14b304454ed/img-b21.md) · OCR
[^c55]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 18–20](../../evidence/src-9107d71821bf/msg-body-l0018-l0020.md) · ✓ quote verified
[^c56]: [Shift Handover Note - Day Shift - 18/07/2026 — lines 6–12](../../evidence/src-b7a218719725/l0006-l0012.md) · ✓ quote verified
[^c57]: [Shift Handover for 2026-07-29 Day Shift — lines 5–14](../../evidence/src-a011da5de982/l0005-l0014.md) · ✓ quote verified
[^c58]: [Shift handover - 2026-07-15 (day shift to night shift) — lines 24–25](../../evidence/src-1d8dff18b801/l0024-l0025.md) · ✓ quote verified
