---
id: src-86cb00fd2f6b
type: source
title: 8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)
summary: This is an 8D incident report for repeated gearbox oil over-temperature on WTG-07. It covers the team, problem description, containment, root-cause analysis, corrective and preventive actions, verification status, and open closure condition.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- incident-report
- incidents
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-86cb00fd2f6b
source_path: full/incidents/INC-2026-006_8D-report-WTG-07-gearbox-over-temperature.docx
source_hash: sha256:245ddafaddd19cb17c8666a66135cf64fba7578493b9250cffa4f182fc940239
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: incident-report
category: incidents
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- alarm-code:a2101
- alarm-code:a2102
- asset:wtg-07
- component:cooler-fan-motor
- component:gearbox
- component:generator
- component:hss-bearing
- component:oil-cooler
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:trey-research-laboratories
- part:fgt-p-22328
- part:lws-p-30418
- product:fgt-3200
topics:
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:generator-and-electrical
- topic:spare-parts-and-supply
authority: 6
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 26
    deterministic-table: 8
    model-description: 1
---

# 8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This is an 8D incident report for repeated [gearbox](../entities/component/gearbox.md) oil over-temperature on [WTG-07](../entities/asset/wtg-07.md). It covers the team, problem description, containment, root-cause analysis, corrective and preventive actions, verification status, and open closure condition.

## Key facts

- The 2026-07-10 revision has D1 to D7 complete and D8 open until the bearing replacement.[^c1]
- The report number is INC-2026-006.[^c2]
- The incident concerns [WTG-07](../entities/asset/wtg-07.md), serial LT32-19-0421, with [gearbox](../entities/component/gearbox.md) FGT-3200-18-07752.[^c3]
- The report was opened on 2026-05-30 after the first [A2102](../entities/alarm-code/a2102.md) trip.[^c4]
- Yusuf Arkwell, Reliability Engineer, is the 8D lead.[^c5]
- Between 2026-04-09 and 2026-06-21, WTG-07 logged 27 [A2101](../entities/alarm-code/a2101.md) warnings at 75 °C and two A2102 trips at 82 °C, while no other turbine logged an A2101 warning in that period.[^c6]
- The [HSS bearing](../entities/component/hss-bearing.md) vibration on the [generator](../entities/component/generator.md) side rose from 2.1 mm/s RMS to 5.2 mm/s RMS and exceeded the 4.5 mm/s alarm level.[^c7]
- From 2026-06-01, WTG-07 was limited to 2.6 MW by the park controller with daily oil-temperature checks, and the limit was removed on 2026-06-25 after the D6 corrective actions.[^c8]
- The root-cause analysis says the oil overheated because the [oil cooler](../entities/component/oil-cooler.md) did not reject enough heat at high load.[^c9]
- The cooler fan ran at reduced speed and the radiator fins were about 40 % blocked by insects and pollen.[^c10]
- The fan motor [LWS-P-30418](../entities/part/lws-p-30418.md) bearing had failed and the motor current was 35 % above nominal.[^c11]
- The report identifies the root cause as missing preventive maintenance of the oil cooler, allowing fan motor bearing failure and radiator fouling to reduce cooling capacity.[^c12]
- A contributing factor was generator-side HSS bearing wear, supported by oil analysis TR-OA-2026-0614 with iron at 64 ppm, PQ index 112, and the vibration trend.[^c13]
- Corrective actions completed on 2026-06-24 included replacing [oil cooler fan motor](../entities/component/cooler-fan-motor.md) LWS-P-30418 under WO-26-0398 and cleaning the oil cooler radiator under WO-26-0399.[^c14][^c15]
- The 2.6 MW limit was removed after verification on 2026-06-25.[^c16]
- Replacing the generator-side HSS bearing [FGT-P-22328](../entities/part/fgt-p-22328.md) under WO-26-0412 is waiting for parts and is planned on delivery of the bearing.[^c17]
- Preventive task MP-GBX-07 for oil cooler radiator cleaning and fan current check was added to the maintenance plan for all turbines every 6 months.[^c18]
- Minimum stock of fan motor LWS-P-30418 was raised from 1 to 2.[^c19]
- A request to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) to add fan motor current to SCADA signals is open under ticket LWS-TS-51877.[^c20]
- Verification reports no A2101 warning on WTG-07 since 2026-06-24, but vibration remains above the alarm level until the bearing is replaced.[^c21]
- The 8D remains open and will be closed after WO-26-0412 and an oil sample 500 operating hours after the bearing replacement.[^c22]

## Contents

### Report status and metadata

The report is titled as an 8D report for repeated [gearbox](../entities/component/gearbox.md) oil over-temperature on [WTG-07](../entities/asset/wtg-07.md).[^c23]

The revision dated 2026-07-10 records D1 to D7 as complete and D8 as open until the bearing replacement.[^c24]

**Table t01** · table 1, rows 1–5

| Row | Field | Value |
| --- | --- | --- |
| 2 | Report number | INC-2026-006 |
| 3 | Turbine | WTG-07 (serial LT32-19-0421, gearbox FGT-3200-18-07752) |
| 4 | Opened | 2026-05-30 after the first [A2102](../entities/alarm-code/a2102.md) trip |
| 5 | 8D lead | Yusuf Arkwell, Reliability Engineer |

Agents can query this table as `t01` with the `query_table` tool.

### D1 - Team

The team consisted of Yusuf Arkwell as lead, Dario Penwarden, Callum Rydings, Élise Ternaux, Katrin Ostermeier from [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md) for remote support, and Imogen Thackwray from [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md) for oil analysis.[^c25]

### D2 - Problem description

Between 2026-04-09 and 2026-06-21, [WTG-07](../entities/asset/wtg-07.md) logged 27 [A2101](../entities/alarm-code/a2101.md) warnings and two [A2102](../entities/alarm-code/a2102.md) trips, with no other turbine logging an A2101 warning in the same period.[^c26]

The generator-side [HSS bearing](../entities/component/hss-bearing.md) vibration rose from 2.1 mm/s RMS on 2026-01-05 to 5.2 mm/s RMS on 2026-06-15, above the alarm level of 4.5 mm/s.[^c27]

Figure 1 is identified as showing WTG-07 weekly A2101 warnings and HSS bearing vibration for 2026.[^c28]

### D3 - Containment

From 2026-06-01, [WTG-07](../entities/asset/wtg-07.md) was limited to 2.6 MW by the park controller and oil temperature was checked daily; the limit was removed on 2026-06-25 after the D6 corrective actions.[^c29]

### D4 - Root cause analysis (5 Whys)

The analysis states that the oil overheated because the [oil cooler](../entities/component/oil-cooler.md) did not reject enough heat at high load.[^c30]

The cooler fan ran at reduced speed and the radiator fins were about 40 % blocked by insects and pollen.[^c31]

The fan ran slowly because the bearing of fan motor [LWS-P-30418](../entities/part/lws-p-30418.md) had failed, and the motor current was 35 % above nominal.[^c32]

The issue was not detected earlier because fan motor current was not monitored by SCADA and the radiator was cleaned only when found dirty.[^c33]

The maintenance plan followed a manual that gave no radiator cleaning interval and specified cleaning only as required.[^c34]

The stated root cause was missing preventive maintenance of the oil cooler, allowing fan motor bearing failure and radiator fouling to reduce cooling capacity.[^c35]

A contributing factor was generator-side [HSS bearing](../entities/component/hss-bearing.md) wear confirmed by oil analysis TR-OA-2026-0614 and the vibration trend, which increased [gearbox](../entities/component/gearbox.md) friction losses.[^c36]

### D5 and D6 - Corrective actions

**Table t02** · table 2, rows 1–5

| Row | Action | Work order | Owner | Date | Status |
| --- | --- | --- | --- | --- | --- |
| 2 | Replace [oil cooler fan motor](../entities/component/cooler-fan-motor.md) [LWS-P-30418](../entities/part/lws-p-30418.md) | WO-26-0398 | Callum Rydings | 2026-06-24 | done |
| 3 | Clean [oil cooler](../entities/component/oil-cooler.md) radiator | WO-26-0399 | Élise Ternaux | 2026-06-24 | done |
| 4 | Remove the 2.6 MW limit after verification | - | Dario Penwarden | 2026-06-25 | done |
| 5 | Replace [HSS bearing](../entities/component/hss-bearing.md), [generator](../entities/component/generator.md) side ([FGT-P-22328](../entities/part/fgt-p-22328.md)) | WO-26-0412 | Callum Rydings | on delivery of the bearing | waiting for parts |

Agents can query this table as `t02` with the `query_table` tool.

### D7 - Prevent recurrence

Task MP-GBX-07, for [oil cooler](../entities/component/oil-cooler.md) radiator cleaning and fan current check, was added to the maintenance plan for all turbines every 6 months.[^c37]

The minimum stock of fan motor [LWS-P-30418](../entities/part/lws-p-30418.md) was raised from 1 to 2.[^c38]

A request to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) to add fan motor current to SCADA signals is open under ticket LWS-TS-51877.[^c39]

Verification found no [A2101](../entities/alarm-code/a2101.md) warning on [WTG-07](../entities/asset/wtg-07.md) since 2026-06-24, while vibration remains above the alarm level until the bearing is replaced.[^c40]

### D8 - Closure

The report remains open and will be closed after WO-26-0412 and an oil sample 500 operating hours after the bearing replacement.[^c41]

## Figures

- **Figure f01** (¶ 8): Generated description: A dual-axis time series chart shows [A2101](../entities/alarm-code/a2101.md) warnings per week as orange bars and Velocity RMS (mm/s) as a blue line with circular markers. The left y-axis is labeled A2101 per week from 0 to 6, and the right y-axis is labeled mm/s RMS from 0 to 7; two horizontal dashed reference lines appear at about 3 and 3.9. The blue line rises steadily from about 2.1 mm/s in early January to a peak near 5.4 mm/s in late June, while the orange bars begin in late March and increase to around 4 warnings per week by late May and June.[^c42]

## Related

- Asset: [WTG-07](../entities/asset/wtg-07.md)
- Components: [gearbox](../entities/component/gearbox.md), [generator](../entities/component/generator.md), [HSS bearing](../entities/component/hss-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- Spare parts: [FGT-P-22328](../entities/part/fgt-p-22328.md), [LWS-P-30418](../entities/part/lws-p-30418.md)
- Product: [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- Alarm codes: [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- Organisations: [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)
- Topics: [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../topics/generator-and-electrical.md), [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [generator](../entities/component/generator.md)
- [Generator brushes and electrical systems](../topics/generator-and-electrical.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)
- [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)
- [WTG-07](../entities/asset/wtg-07.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 2](../evidence/src-86cb00fd2f6b/para-0002.md) · ✓ quote verified
[^c2]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 1, row 2](../evidence/src-86cb00fd2f6b/tbl-01-r0002-r0002.md) · table
[^c3]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 1, row 3](../evidence/src-86cb00fd2f6b/tbl-01-r0003-r0003.md) · table
[^c4]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 1, row 4](../evidence/src-86cb00fd2f6b/tbl-01-r0004-r0004.md) · table
[^c5]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 1, row 5](../evidence/src-86cb00fd2f6b/tbl-01-r0005-r0005.md) · table
[^c6]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 6](../evidence/src-86cb00fd2f6b/para-0006.md) · ✓ quote verified
[^c7]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 7](../evidence/src-86cb00fd2f6b/para-0007.md) · ✓ quote verified
[^c8]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 10](../evidence/src-86cb00fd2f6b/para-0010.md) · ✓ quote verified
[^c9]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 12](../evidence/src-86cb00fd2f6b/para-0012.md) · ✓ quote verified
[^c10]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 13](../evidence/src-86cb00fd2f6b/para-0013.md) · ✓ quote verified
[^c11]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 14](../evidence/src-86cb00fd2f6b/para-0014.md) · ✓ quote verified
[^c12]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 17](../evidence/src-86cb00fd2f6b/para-0017.md) · ✓ quote verified
[^c13]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 18](../evidence/src-86cb00fd2f6b/para-0018.md) · ✓ quote verified
[^c14]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 2](../evidence/src-86cb00fd2f6b/tbl-02-r0002-r0002.md) · table
[^c15]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 3](../evidence/src-86cb00fd2f6b/tbl-02-r0003-r0003.md) · table
[^c16]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 4](../evidence/src-86cb00fd2f6b/tbl-02-r0004-r0004.md) · table
[^c17]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 5](../evidence/src-86cb00fd2f6b/tbl-02-r0005-r0005.md) · table
[^c18]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 21](../evidence/src-86cb00fd2f6b/para-0021.md) · ✓ quote verified
[^c19]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 22](../evidence/src-86cb00fd2f6b/para-0022.md) · ✓ quote verified
[^c20]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 23](../evidence/src-86cb00fd2f6b/para-0023.md) · ✓ quote verified
[^c21]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 24](../evidence/src-86cb00fd2f6b/para-0024.md) · ✓ quote verified
[^c22]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 26](../evidence/src-86cb00fd2f6b/para-0026.md) · ✓ quote verified
[^c23]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 1](../evidence/src-86cb00fd2f6b/para-0001.md) · paraphrase
[^c24]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 2](../evidence/src-86cb00fd2f6b/para-0002.md) · paraphrase
[^c25]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 4](../evidence/src-86cb00fd2f6b/para-0004.md) · paraphrase
[^c26]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 6](../evidence/src-86cb00fd2f6b/para-0006.md) · paraphrase
[^c27]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 7](../evidence/src-86cb00fd2f6b/para-0007.md) · paraphrase
[^c28]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 8](../evidence/src-86cb00fd2f6b/para-0008.md) · paraphrase
[^c29]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 10](../evidence/src-86cb00fd2f6b/para-0010.md) · paraphrase
[^c30]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 12](../evidence/src-86cb00fd2f6b/para-0012.md) · paraphrase
[^c31]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 13](../evidence/src-86cb00fd2f6b/para-0013.md) · paraphrase
[^c32]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 14](../evidence/src-86cb00fd2f6b/para-0014.md) · paraphrase
[^c33]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 15](../evidence/src-86cb00fd2f6b/para-0015.md) · paraphrase
[^c34]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 16](../evidence/src-86cb00fd2f6b/para-0016.md) · paraphrase
[^c35]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 17](../evidence/src-86cb00fd2f6b/para-0017.md) · paraphrase
[^c36]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 18](../evidence/src-86cb00fd2f6b/para-0018.md) · paraphrase
[^c37]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 21](../evidence/src-86cb00fd2f6b/para-0021.md) · paraphrase
[^c38]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 22](../evidence/src-86cb00fd2f6b/para-0022.md) · paraphrase
[^c39]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 23](../evidence/src-86cb00fd2f6b/para-0023.md) · paraphrase
[^c40]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 24](../evidence/src-86cb00fd2f6b/para-0024.md) · paraphrase
[^c41]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 26](../evidence/src-86cb00fd2f6b/para-0026.md) · paraphrase
[^c42]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 8](../evidence/src-86cb00fd2f6b/para-0008.md) · generated description
