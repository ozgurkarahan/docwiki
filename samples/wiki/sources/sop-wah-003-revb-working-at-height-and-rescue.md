---
id: src-05b9ebcb4d58
type: source
title: SOP-WAH-003 Revision B - Working at height and rescue
summary: This standard operating procedure defines working-at-height and rescue requirements for turbine climbing, nacelle and hub work, dropped-object controls, weather limits, rescue equipment, rescue response, training, and revision history. It applies to WTG-01 through WTG-12 and is effective from 2026-04-07.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- procedures
- sop
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-05b9ebcb4d58
source_path: full/procedures/SOP-WAH-003_RevB_working-at-height-and-rescue.docx
source_hash: sha256:883a2d0549279ee0a4408df925af604358f9c227febc065eac6260427c689ac9
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: sop
category: procedures
doc_number: SOP-WAH-003
revision: B
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- alarm-code:a7001
- asset:wtg-01
- asset:wtg-02
- asset:wtg-03
- asset:wtg-04
- asset:wtg-05
- asset:wtg-06
- asset:wtg-07
- asset:wtg-08
- asset:wtg-09
- asset:wtg-10
- asset:wtg-11
- asset:wtg-12
- component:rescue-kit
- component:service-lift
- procedure:sop-wah-003
topics:
- topic:cold-climate-operation
- topic:safety-and-access
- topic:training-and-onboarding
authority: 7
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 27
    deterministic-table: 12
---

# SOP-WAH-003 Revision B - Working at height and rescue

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This standard operating procedure defines working-at-height and rescue requirements for turbine climbing, nacelle and hub work, dropped-object controls, weather limits, rescue equipment, rescue response, training, and revision history. It applies to [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) and is effective from 2026-04-07.

## Key facts

- [SOP-WAH-003](../entities/procedure/sop-wah-003.md) is Revision B and is effective 2026-04-07.[^c1]
- The document owner is Greta Vollan, HSE Coordinator, and it was approved by Maren Ellingsby, Site Manager.[^c2][^c3]
- The purpose is to prevent falls of people and objects during work in towers and nacelles and to ensure a casualty can be rescued quickly.[^c4]
- The scope covers all climbing, work in the nacelle and hub, and rescue on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md).[^c5]
- The O&M Supervisor plans work at height and checks the weather limits.[^c6]
- Each technician must check his or her harness and lanyards before use.[^c7]
- The HSE Coordinator organises rescue drills twice a year.[^c8]
- Tool tethering is mandatory above 2 m.[^c9]
- Hatches must stay closed while tools or parts are passed.[^c9]
- During nacelle work, an exclusion zone with signage is set up at the tower base and nobody enters it without the nacelle team's agreement.[^c9]
- Climbing requires a minimum of two persons, with only one ladder section climbed at a time.[^c10]
- Climbers must use the fall arrest rail and rest platforms, and use the [service lift](../entities/component/service-lift.md) when available.[^c11]
- Any damaged ladder rung or fall arrest component must be reported immediately.[^c12]
- Climbing and nacelle work are limited to 10-minute mean wind speed up to 15 m/s.[^c13]
- Hub entry is limited to 10-minute mean wind speed up to 12 m/s.[^c14]
- Work on the nacelle roof is limited to 10-minute mean wind speed up to 10 m/s.[^c15]
- Climbing is not allowed during a thunderstorm when lightning is detected within 15 km.[^c16]
- For ice, there is no access within 300 m of a turbine with ice detected under alarm [A7001](../entities/alarm-code/a7001.md).[^c17]
- Each nacelle has a sealed [rescue kit](../entities/component/rescue-kit.md) with a descent device.[^c18]
- Rescue kits are inspected every 6 months, and the seal is checked on the daily checklist.[^c18]
- A broken rescue kit seal means the kit must be inspected before the next climb.[^c18]
- The rescue procedure begins by raising the alarm to the control room and emergency services.[^c19]
- The turbine is then made safe by stopping it and applying the rotor lock.[^c20]
- The casualty is attached to the descent device and lowered to the ground or through the tower.[^c21]
- The target is to have the casualty on the ground within 15 minutes of the alarm.[^c22]
- Working at height and rescue training is refreshed every 2 years, and rescue drills take place twice a year on site.[^c23]
- Revision B added mandatory tool tethering above 2 m after near miss INC-2026-003 and the requirement to close hatches when passing tools.[^c24]

## Contents

### Document control

[SOP-WAH-003](../entities/procedure/sop-wah-003.md) is a standard operating procedure for working at height and rescue, Revision B, effective 2026-04-07.[^c25][^c26]

The metadata identifies Greta Vollan, HSE Coordinator, as owner and Maren Ellingsby, Site Manager, as approver.[^c2][^c3]

**Table t01** · table 1, rows 1–6

| Row | Field | Value |
| --- | --- | --- |
| 2 | Document number | SOP-WAH-003 |
| 3 | Revision | B |
| 4 | Effective date | 2026-04-07 |
| 5 | Owner | Greta Vollan, HSE Coordinator |
| 6 | Approved by | Maren Ellingsby, Site Manager |

Agents can query this table as `t01` with the `query_table` tool.

### Purpose

The procedure aims to prevent falls of people and objects during work in towers and nacelles and to make sure that a casualty can be rescued quickly.[^c27]

### Scope

The procedure applies to all climbing, nacelle and hub work, and rescue on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md).[^c28]

### Responsibilities

- The O&M Supervisor plans work at height and checks weather limits.[^c29]
- Each technician checks his or her own harness and lanyards before use.[^c30]
- The HSE Coordinator organises rescue drills twice a year.[^c31]

### Dropped objects and exclusion zones

Tool tethering is mandatory above 2 m.[^c32] Hatches stay closed while tools or parts are passed.[^c32] During nacelle work, an exclusion zone with signage is set up at the tower base, and nobody enters it without the nacelle team's agreement.[^c32]

### Climbing

- Climbing requires at least two persons, and teams climb one ladder section at a time.[^c33]
- Climbers use the fall arrest rail and rest platforms, and use the [service lift](../entities/component/service-lift.md) when it is available.[^c34]
- Any damaged ladder rung or fall arrest component is reported immediately.[^c35]

### Weather limits

Weather limits are specified for climbing and nacelle work, hub entry, work on the nacelle roof, thunderstorms, and ice conditions.[^c13][^c14][^c15][^c16][^c17]

**Table t02** · table 2, rows 1–6

| Row | Activity | Limit |
| --- | --- | --- |
| 2 | Climbing and nacelle work | 10-minute mean wind speed up to 15 m/s |
| 3 | Hub entry | 10-minute mean wind speed up to 12 m/s |
| 4 | Work on the nacelle roof | 10-minute mean wind speed up to 10 m/s |
| 5 | Thunderstorm | no climbing when lightning is detected within 15 km |
| 6 | Ice | no access within 300 m of a turbine with ice detected ([A7001](../entities/alarm-code/a7001.md)) |

Agents can query this table as `t02` with the `query_table` tool.

### Rescue equipment and inspection

Each nacelle holds a sealed [rescue kit](../entities/component/rescue-kit.md) with a descent device.[^c36] The kits are inspected every 6 months, and the seal is checked on the daily checklist.[^c36] A broken seal means the kit must be inspected before the next climb.[^c36]

### Rescue procedure

- Raise the alarm to the control room and emergency services.[^c37]
- Make the turbine safe by stopping it and applying the rotor lock.[^c38]
- Attach the casualty to the descent device and lower him or her to the ground or through the tower.[^c39]
- The target is casualty on the ground within 15 minutes of the alarm.[^c40]

### Training

Working at height and rescue training is refreshed every 2 years, and rescue drills take place twice a year on site.[^c41]

### Revision history

Revision A was the first issue.[^c42] Revision B recorded mandatory tool tethering above 2 m after near miss INC-2026-003 and closed hatches when passing tools.[^c24]

**Table t03** · table 3, rows 1–3

| Row | Revision | Date | Change |
| --- | --- | --- | --- |
| 2 | A | 2019-10-01 | First issue. |
| 3 | B | 2026-04-07 | Tool tethering mandatory above 2 m after near miss INC-2026-003; hatches closed when passing tools. |

Agents can query this table as `t03` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [rescue kit](../entities/component/rescue-kit.md), [service lift](../entities/component/service-lift.md)
- Alarm code: [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Procedure: [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Safety, isolation and work at height](../topics/safety-and-access.md), [Training, site rules and acronyms](../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- [Cold-climate operation and icing](../topics/cold-climate-operation.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [service lift](../entities/component/service-lift.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [Training, site rules and acronyms](../topics/training-and-onboarding.md)
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

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 2](../evidence/src-05b9ebcb4d58/para-0002.md) · ✓ quote verified
[^c2]: [SOP-WAH-003 Revision B - Working at height and rescue — table 1, row 5](../evidence/src-05b9ebcb4d58/tbl-01-r0005-r0005.md) · table
[^c3]: [SOP-WAH-003 Revision B - Working at height and rescue — table 1, row 6](../evidence/src-05b9ebcb4d58/tbl-01-r0006-r0006.md) · table
[^c4]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 4](../evidence/src-05b9ebcb4d58/para-0004.md) · ✓ quote verified
[^c5]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 6](../evidence/src-05b9ebcb4d58/para-0006.md) · ✓ quote verified
[^c6]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 8](../evidence/src-05b9ebcb4d58/para-0008.md) · ✓ quote verified
[^c7]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 9](../evidence/src-05b9ebcb4d58/para-0009.md) · ✓ quote verified
[^c8]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 10](../evidence/src-05b9ebcb4d58/para-0010.md) · ✓ quote verified
[^c9]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 12](../evidence/src-05b9ebcb4d58/para-0012.md) · ✓ quote verified
[^c10]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 14](../evidence/src-05b9ebcb4d58/para-0014.md) · ✓ quote verified
[^c11]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 15](../evidence/src-05b9ebcb4d58/para-0015.md) · ✓ quote verified
[^c12]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 16](../evidence/src-05b9ebcb4d58/para-0016.md) · ✓ quote verified
[^c13]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 2](../evidence/src-05b9ebcb4d58/tbl-02-r0002-r0002.md) · table
[^c14]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 3](../evidence/src-05b9ebcb4d58/tbl-02-r0003-r0003.md) · table
[^c15]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 4](../evidence/src-05b9ebcb4d58/tbl-02-r0004-r0004.md) · table
[^c16]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 5](../evidence/src-05b9ebcb4d58/tbl-02-r0005-r0005.md) · table
[^c17]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 6](../evidence/src-05b9ebcb4d58/tbl-02-r0006-r0006.md) · table
[^c18]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 19](../evidence/src-05b9ebcb4d58/para-0019.md) · ✓ quote verified
[^c19]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 21](../evidence/src-05b9ebcb4d58/para-0021.md) · ✓ quote verified
[^c20]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 22](../evidence/src-05b9ebcb4d58/para-0022.md) · ✓ quote verified
[^c21]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 23](../evidence/src-05b9ebcb4d58/para-0023.md) · ✓ quote verified
[^c22]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 24](../evidence/src-05b9ebcb4d58/para-0024.md) · ✓ quote verified
[^c23]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 26](../evidence/src-05b9ebcb4d58/para-0026.md) · ✓ quote verified
[^c24]: [SOP-WAH-003 Revision B - Working at height and rescue — table 3, row 3](../evidence/src-05b9ebcb4d58/tbl-03-r0003-r0003.md) · table
[^c25]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 1](../evidence/src-05b9ebcb4d58/para-0001.md) · paraphrase
[^c26]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 2](../evidence/src-05b9ebcb4d58/para-0002.md) · paraphrase
[^c27]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 4](../evidence/src-05b9ebcb4d58/para-0004.md) · paraphrase
[^c28]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 6](../evidence/src-05b9ebcb4d58/para-0006.md) · paraphrase
[^c29]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 8](../evidence/src-05b9ebcb4d58/para-0008.md) · paraphrase
[^c30]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 9](../evidence/src-05b9ebcb4d58/para-0009.md) · paraphrase
[^c31]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 10](../evidence/src-05b9ebcb4d58/para-0010.md) · paraphrase
[^c32]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 12](../evidence/src-05b9ebcb4d58/para-0012.md) · paraphrase
[^c33]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 14](../evidence/src-05b9ebcb4d58/para-0014.md) · paraphrase
[^c34]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 15](../evidence/src-05b9ebcb4d58/para-0015.md) · paraphrase
[^c35]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 16](../evidence/src-05b9ebcb4d58/para-0016.md) · paraphrase
[^c36]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 19](../evidence/src-05b9ebcb4d58/para-0019.md) · paraphrase
[^c37]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 21](../evidence/src-05b9ebcb4d58/para-0021.md) · paraphrase
[^c38]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 22](../evidence/src-05b9ebcb4d58/para-0022.md) · paraphrase
[^c39]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 23](../evidence/src-05b9ebcb4d58/para-0023.md) · paraphrase
[^c40]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 24](../evidence/src-05b9ebcb4d58/para-0024.md) · paraphrase
[^c41]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 26](../evidence/src-05b9ebcb4d58/para-0026.md) · paraphrase
[^c42]: [SOP-WAH-003 Revision B - Working at height and rescue — table 3, row 2](../evidence/src-05b9ebcb4d58/tbl-03-r0002-r0002.md) · table
