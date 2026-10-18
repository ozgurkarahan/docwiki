---
id: asset:wtg-06
type: entity
title: WTG-06
summary: WTG-06 is a turbine listed on the Quellmoor Ridge Wind Farm site layout plan. An internal safety audit recorded a rescue drill on WTG-06 and reported that the casualty was lowered to the ground in 9 minutes against a 15-minute target. The SCADA log for WTG-06 recorded yaw misalignment, a pitch…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- asset
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: asset
key: wtg-06
aliases:
- text: WTG-06
  lang: en
- text: WTG06
  lang: en
- text: WTG 06
  lang: en
- text: éolienne WTG-06
  lang: fr
- text: Anlage WTG-06
  lang: de
sources:
- src-05b9ebcb4d58
- src-0df0d0598e76
- src-36f5b999211a
- src-383540987d7a
- src-65680eb5afcc
- src-70224c3b9c9f
- src-824b788eefc0
- src-90ea27f71f0f
- src-9d075c6edcd5
- src-9fd435ef5956
- src-a14b304454ed
- src-a20331a5431f
- src-a7e8d332dafd
- src-aba30cb7207f
- src-b342a2d5bfdf
- src-e7cd20fa7984
- src-ecc004b57dd5
---

# WTG-06

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

WTG-06 is a turbine listed on the [Quellmoor Ridge Wind Farm](quellmoor-ridge-wind-farm.md) site layout plan.[^c1][^c2][^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11][^c12] An internal safety audit recorded a rescue drill on WTG-06 and reported that the casualty was lowered to the ground in 9 minutes against a 15-minute target.[^c13] The SCADA log for WTG-06 recorded [yaw misalignment](../alarm-code/a5001.md), a [pitch system fault](../alarm-code/a4105.md), and a [gearbox oil filter differential pressure high](../alarm-code/a2140.md) alarm in 2026.[^c14][^c15][^c16][^c17][^c18][^c19][^c20][^c21][^c22][^c23]

## Facts

- The audit method was document review, interviews, and observation of two jobs: a filter change on [WTG-02](wtg-02.md) and a rescue drill on WTG-06.[^c13]
- Finding F1 was a major finding: the [rescue kit](../component/rescue-kit.md) in the WTG-06 nacelle was past its 6-monthly inspection, with last inspection on 2025-06-12 and due date 2025-12-12; the action was to inspect all rescue kits and add the kit seal check to the daily checklist, owned by Greta Vollan and due 2026-03-31.[^c13]
- The WTG-06 rescue drill lowered the casualty to the ground in 9 minutes against a 15 minutes target.[^c13]
- The 2026-06-18 grid-voltage alarms cleared at 99.6 %, and the [S510 Stopped - fault](../status-code/s510.md) statuses ended between WTG-06 at 14:15:04 and [WTG-12](wtg-12.md) at 14:20:10.[^c24][^c25][^c26][^c27]
- WTG-06 had two [A5001 Yaw misalignment](../alarm-code/a5001.md) raised records on 2026-07-30, at 11.8 deg and 16.5 deg, followed by two cleared records at 4.2 deg.[^c14][^c15][^c16][^c17]
- WTG-06 raised [A4105 Pitch system fault](../alarm-code/a4105.md) with value 3 axis on 2026-08-05, started S510 Stopped - fault, then cleared A4105 and ended S510 shortly after midnight on 2026-08-06.[^c18][^c19][^c20][^c21]
- WTG-06 had [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md) raised at 2.89 bar and cleared at 1.90 bar on 2026-08-31.[^c22][^c23]
- [Pitch bearing](../component/pitch-bearing.md) bolt re-torque work for [WTG-01](wtg-01.md) through WTG-06 was completed with a stated torque of 1,450 Nm and coverage of 100 % of bolts, referenced to [SB-LWS-2025-11](../bulletin/sb-lws-2025-11.md) Rev. A.[^c28][^c29][^c30][^c31][^c32][^c33]
- The turbine labels shown on the plan are WTG-01, WTG-02, [WTG-03](wtg-03.md), [WTG-04](wtg-04.md), [WTG-05](wtg-05.md), WTG-06, [WTG-07](wtg-07.md), [WTG-08](wtg-08.md), [WTG-09](wtg-09.md), [WTG-10](wtg-10.md), [WTG-11](wtg-11.md), and WTG-12.[^c1][^c2][^c3][^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11][^c12]
- The [service lift](../component/service-lift.md) on WTG-06 stopped twice the previous winter because of cold, and such events should be reported every time for follow-up with [Litware](../organisation/litware-wind-systems.md).[^c34][^c35]

## Timeline

- 2025-06-12: Finding F1 was a major finding: the [rescue kit](../component/rescue-kit.md) in the WTG-06 nacelle was past its 6-monthly inspection, with last inspection on 2025-06-12 and due date 2025-12-12; the action was to inspect all rescue kits and add the kit seal check to the daily checklist, owned by Greta Vollan and due 2026-03-31.[^c13]
- 2025-11: [Pitch bearing](../component/pitch-bearing.md) bolt re-torque work for [WTG-01](wtg-01.md) through WTG-06 was completed with a stated torque of 1,450 Nm and coverage of 100 % of bolts, referenced to [SB-LWS-2025-11](../bulletin/sb-lws-2025-11.md) Rev. A.[^c28][^c29][^c30][^c31][^c32][^c33]
- 2026-06-18: The 2026-06-18 grid-voltage alarms cleared at 99.6 %, and the [S510 Stopped - fault](../status-code/s510.md) statuses ended between WTG-06 at 14:15:04 and [WTG-12](wtg-12.md) at 14:20:10.[^c24][^c25][^c26][^c27]
- 2026-07-30: WTG-06 had two [A5001 Yaw misalignment](../alarm-code/a5001.md) raised records on 2026-07-30, at 11.8 deg and 16.5 deg, followed by two cleared records at 4.2 deg.[^c14][^c15][^c16][^c17]
- 2026-08-05: WTG-06 raised [A4105 Pitch system fault](../alarm-code/a4105.md) with value 3 axis on 2026-08-05, started S510 Stopped - fault, then cleared A4105 and ended S510 shortly after midnight on 2026-08-06.[^c18][^c19][^c20][^c21]
- 2026-08-31: WTG-06 had [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md) raised at 2.89 bar and cleared at 1.90 bar on 2026-08-31.[^c22][^c23]

## Documents

- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../../sources/wbs-2026-031-blade-inspection-report.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [Internal safety audit report AUD-2026-02](../../sources/aud-2026-02-internal-safety-audit-report.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [KPI Export 2026-H1](../../sources/kpi-export-2026-h1.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../../sources/site-layout-plan.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md) (superseded)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md)
- [A4105 Pitch system fault](../alarm-code/a4105.md)
- [A5001 Yaw misalignment](../alarm-code/a5001.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../../sources/wbs-2026-031-blade-inspection-report.md)
- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [gearbox](../component/gearbox.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [Internal safety audit report AUD-2026-02](../../sources/aud-2026-02-internal-safety-audit-report.md)
- [KPI Export 2026-H1](../../sources/kpi-export-2026-h1.md)
- [Litware Wind Systems](../organisation/litware-wind-systems.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [oil filter element](../component/oil-filter.md)
- [pitch bearing](../component/pitch-bearing.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C](../../sources/site-layout-plan.md)
- [rescue kit](../component/rescue-kit.md)
- [S510 Stopped - fault](../status-code/s510.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../bulletin/sb-lws-2025-11.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [service lift](../component/service-lift.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [WTG-01](wtg-01.md)
- [WTG-02](wtg-02.md)
- [WTG-03](wtg-03.md)
- [WTG-04](wtg-04.md)
- [WTG-05](wtg-05.md)
- [WTG-07](wtg-07.md)
- [WTG-08](wtg-08.md)
- [WTG-09](wtg-09.md)
- [WTG-10](wtg-10.md)
- [WTG-11](wtg-11.md)
- [WTG-12](wtg-12.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 5](../../evidence/src-a14b304454ed/img-b05.md) · OCR
[^c2]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 6](../../evidence/src-a14b304454ed/img-b06.md) · OCR
[^c3]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 9](../../evidence/src-a14b304454ed/img-b09.md) · OCR
[^c4]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 10](../../evidence/src-a14b304454ed/img-b10.md) · OCR
[^c5]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 11](../../evidence/src-a14b304454ed/img-b11.md) · OCR
[^c6]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 13](../../evidence/src-a14b304454ed/img-b13.md) · OCR
[^c7]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 12](../../evidence/src-a14b304454ed/img-b12.md) · OCR
[^c8]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 14](../../evidence/src-a14b304454ed/img-b14.md) · OCR
[^c9]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 16](../../evidence/src-a14b304454ed/img-b16.md) · OCR
[^c10]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 18](../../evidence/src-a14b304454ed/img-b18.md) · OCR
[^c11]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 20](../../evidence/src-a14b304454ed/img-b20.md) · OCR
[^c12]: [Quellmoor Ridge Wind Farm Site Layout Plan - Rev. C — region 21](../../evidence/src-a14b304454ed/img-b21.md) · OCR
[^c13]: [Internal safety audit report AUD-2026-02 — p. 1](../../evidence/src-9d075c6edcd5/p0001.md) · ✓ quote verified
[^c14]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1426](../../evidence/src-36f5b999211a/r1426-r1426.md) · table
[^c15]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1427](../../evidence/src-36f5b999211a/r1427-r1427.md) · table
[^c16]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1428](../../evidence/src-36f5b999211a/r1428-r1428.md) · table
[^c17]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1429](../../evidence/src-36f5b999211a/r1429-r1429.md) · table
[^c18]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1534](../../evidence/src-36f5b999211a/r1534-r1534.md) · table
[^c19]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1535](../../evidence/src-36f5b999211a/r1535-r1535.md) · table
[^c20]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1536](../../evidence/src-36f5b999211a/r1536-r1536.md) · table
[^c21]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1537](../../evidence/src-36f5b999211a/r1537-r1537.md) · table
[^c22]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1896](../../evidence/src-36f5b999211a/r1896-r1896.md) · table
[^c23]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1897](../../evidence/src-36f5b999211a/r1897-r1897.md) · table
[^c24]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 888](../../evidence/src-36f5b999211a/r0888-r0888.md) · table
[^c25]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 889](../../evidence/src-36f5b999211a/r0889-r0889.md) · table
[^c26]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 909](../../evidence/src-36f5b999211a/r0909-r0909.md) · table
[^c27]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 911](../../evidence/src-36f5b999211a/r0911-r0911.md) · table
[^c28]: [Work Orders Export through 2026-08-31 — row 45](../../evidence/src-9fd435ef5956/r0045-r0045.md) · table
[^c29]: [Work Orders Export through 2026-08-31 — row 46](../../evidence/src-9fd435ef5956/r0046-r0046.md) · table
[^c30]: [Work Orders Export through 2026-08-31 — row 47](../../evidence/src-9fd435ef5956/r0047-r0047.md) · table
[^c31]: [Work Orders Export through 2026-08-31 — row 48](../../evidence/src-9fd435ef5956/r0048-r0048.md) · table
[^c32]: [Work Orders Export through 2026-08-31 — row 49](../../evidence/src-9fd435ef5956/r0049-r0049.md) · table
[^c33]: [Work Orders Export through 2026-08-31 — row 50](../../evidence/src-9fd435ef5956/r0050-r0050.md) · table
[^c34]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:29–02:37](../../evidence/src-ecc004b57dd5/cue-00-02-29.md) · ✓ quote verified
[^c35]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:37–02:45](../../evidence/src-ecc004b57dd5/cue-00-02-37.md) · ✓ quote verified
