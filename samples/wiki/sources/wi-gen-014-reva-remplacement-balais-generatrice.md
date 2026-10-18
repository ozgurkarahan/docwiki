---
id: src-824b788eefc0
type: source
title: WI-GEN-014 Rev. A - Generator Brush Replacement
summary: This French work instruction describes inspection and replacement of generator brushes on Litware LT-32 turbines at Quellmoor Ridge. It covers safety requirements, required materials, replacement criteria, the step-by-step procedure, run-in, recording, estimated duration, and revision history.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- procedures
- work-instruction
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-824b788eefc0
source_path: full/procedures/WI-GEN-014_RevA_remplacement-balais-generatrice.docx
source_hash: sha256:d3f1c8c7a67e70c9cd0d8b8778d73ddaf1112979c38939c6ab7602b9d1b08f5e
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: work-instruction
category: procedures
doc_number: WI-GEN-014
revision: A
status: current
supersedes: []
superseded_by: []
original_lang: fr
pages: null
entities:
- alarm-code:a3210
- asset:quellmoor-ridge-wind-farm
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
- component:generator
- component:generator-brushes
- component:slip-ring
- organisation:litware-wind-systems
- part:lws-p-51207
- part:lws-p-55031
- procedure:sop-loto-001
- procedure:wi-gen-014
- product:lt-32
topics:
- topic:generator-and-electrical
- topic:safety-and-access
authority: 7
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 31
    deterministic-table: 7
---

# WI-GEN-014 Rev. A - Generator Brush Replacement

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This French work instruction describes inspection and replacement of [generator brushes](../entities/component/generator-brushes.md) on [Litware LT-32](../entities/product/lt-32.md) turbines at [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md). It covers safety requirements, required materials, replacement criteria, the step-by-step procedure, run-in, recording, estimated duration, and revision history.

## Key facts

- [WI-GEN-014](../entities/procedure/wi-gen-014.md) is a Revision A work instruction applicable from 2025-09-15 to [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) with a 690 V double-fed asynchronous [generator](../entities/component/generator.md).[^c1][^c2]
- The document was prepared by Élise Ternaux, wind turbine technician, and approved by Dario Penwarden, O&M supervisor.[^c3][^c4]
- The instruction describes checking and replacing the [generator brushes](../entities/component/generator-brushes.md) of [Litware LT-32](../entities/product/lt-32.md) wind turbines at the [Quellmoor Ridge wind farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c5]
- A PTW is mandatory and at least two technicians are required.[^c6]
- The generator, including stator and rotor, must be locked out according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md).[^c7]
- Technicians must wear gloves, glasses, and a dust mask because carbon dust is conductive.[^c8]
- The required brush set is [LWS-P-51207](../entities/part/lws-p-51207.md) and contains 18 brushes.[^c9]
- The slip-ring cleaning kit required is [LWS-P-55031](../entities/part/lws-p-55031.md).[^c10]
- Required tools include a 5 to 25 N·m torque wrench, a caliper, and an industrial vacuum cleaner.[^c11]
- The complete brush set must be replaced when any brush has less than 18 mm remaining; a new brush is 40 mm long, and new and worn brushes must never be mixed on the same ring.[^c12]
- Alarm [A3210](../entities/alarm-code/a3210.md), Generator brush wear limit reached, appears when the remaining brush length reaches approximately 20 mm.[^c13]
- The operating procedure begins by obtaining the PTW, stopping the turbine, and locking out the generator.[^c14]
- Each brush length must be measured with a caliper and the values recorded.[^c15]
- The [slip ring](../entities/component/slip-ring.md) must be cleaned with kit LWS-P-55031, then new brushes must be installed and checked for free sliding.[^c16][^c17]
- The brush-holder screws must be tightened to 12 N·m.[^c18]
- For run-in, turbine power must be limited to 50 % for 8 hours before returning to rated power.[^c19]
- Measured lengths and the work order number must be recorded.[^c20]
- The estimated duration is 3 hours for two technicians, excluding run-in.[^c21]
- Revision A is the first issue of the document.[^c22]

## Contents

### Document control

The document is titled [WI-GEN-014](../entities/procedure/wi-gen-014.md) - Generator Brush Replacement.[^c23] It is a work instruction at Revision A, applicable from 2025-09-15.[^c24]

The document-control table includes the document number, revision, application date, preparer, approver, and applicability.[^c25][^c26][^c27][^c3][^c4][^c2]

**Table t01** · table 1, rows 1–7

| Row | Champ | Valeur |
| --- | --- | --- |
| 2 | Numéro | WI-GEN-014 |
| 3 | Révision | A |
| 4 | Date d'application | 2025-09-15 |
| 5 | Rédigé par | Élise Ternaux, technicienne éolienne |
| 6 | Approuvé par | Dario Penwarden, superviseur O&M |
| 7 | Applicable à | [WTG-01](../entities/asset/wtg-01.md) à [WTG-12](../entities/asset/wtg-12.md) ([génératrice](../entities/component/generator.md) asynchrone à double alimentation, 690 V) |

Agents can query this table as `t01` with the `query_table` tool.

### Purpose

This instruction describes checking and replacing the [generator brushes](../entities/component/generator-brushes.md) of [Litware LT-32](../entities/product/lt-32.md) wind turbines at the [Quellmoor Ridge wind farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c28]

### Safety

- A PTW is mandatory, with a minimum of two technicians.[^c29]
- The [generator](../entities/component/generator.md), including stator and rotor, must be locked out according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md).[^c30]
- Gloves, glasses, and a dust mask must be worn because carbon dust is conductive.[^c31]

### Materials

- The required brush set is [LWS-P-51207](../entities/part/lws-p-51207.md), containing 18 brushes.[^c32]
- The required slip-ring cleaning kit is [LWS-P-55031](../entities/part/lws-p-55031.md).[^c33]
- Required tools are a 5 to 25 N·m torque wrench, a caliper, and an industrial vacuum cleaner.[^c34]

### Replacement criteria

The complete brush set must be replaced when the remaining length of a brush is less than 18 mm.[^c35] A new brush is 40 mm long.[^c35] New and worn brushes must never be mixed on the same ring.[^c35]

Alarm [A3210](../entities/alarm-code/a3210.md), Generator brush wear limit reached, appears when remaining length reaches approximately 20 mm.[^c36]

### Operating procedure

- Obtain the PTW, stop the turbine, and lock out the [generator](../entities/component/generator.md).[^c37]
- Open the cover of the slip-ring compartment.[^c38]
- Vacuum carbon dust before any intervention.[^c39]
- Measure each brush length with a caliper and record the values.[^c40]
- Remove the brush holders one by one.[^c41]
- Clean the [slip ring](../entities/component/slip-ring.md) with kit [LWS-P-55031](../entities/part/lws-p-55031.md).[^c42]
- Install new brushes and check that they slide freely.[^c43]
- Tighten the brush-holder screws to 12 N·m.[^c44]
- Check spring pressure by confirming the green mark is visible.[^c45]
- Close the cover, remove tools, and remove the lockout.[^c46]
- For run-in, limit turbine power to 50 % for 8 hours, then return to rated power.[^c47]
- Record the measured lengths and the work order number.[^c48]

### Duration

The estimated duration is 3 hours for two technicians, excluding run-in.[^c49]

### Revision history

The revision history records Revision A as the first issue dated 2025-09-15.[^c22]

**Table t02** · table 2, rows 1–2

| Row | Révision | Date | Modification |
| --- | --- | --- | --- |
| 2 | A | 2025-09-15 | Première émission. |

Agents can query this table as `t02` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [slip ring](../entities/component/slip-ring.md)
- Spare parts: [LWS-P-51207](../entities/part/lws-p-51207.md), [LWS-P-55031](../entities/part/lws-p-55031.md)
- Product: [Litware LT-32](../entities/product/lt-32.md)
- Alarm code: [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- Procedures: [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Organisation: [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- Topics: [Generator brushes and electrical systems](../topics/generator-and-electrical.md), [Safety, isolation and work at height](../topics/safety-and-access.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [Generator brushes and electrical systems](../topics/generator-and-electrical.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LWS-P-51207](../entities/part/lws-p-51207.md)
- [LWS-P-55031](../entities/part/lws-p-55031.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
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

[^c1]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 2](../evidence/src-824b788eefc0/para-0002.md) · ✓ quote verified
[^c2]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 7](../evidence/src-824b788eefc0/tbl-01-r0007-r0007.md) · table
[^c3]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 5](../evidence/src-824b788eefc0/tbl-01-r0005-r0005.md) · table
[^c4]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 6](../evidence/src-824b788eefc0/tbl-01-r0006-r0006.md) · table
[^c5]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 4](../evidence/src-824b788eefc0/para-0004.md) · ✓ quote verified
[^c6]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 6](../evidence/src-824b788eefc0/para-0006.md) · ✓ quote verified
[^c7]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 7](../evidence/src-824b788eefc0/para-0007.md) · ✓ quote verified
[^c8]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 8](../evidence/src-824b788eefc0/para-0008.md) · ✓ quote verified
[^c9]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 10](../evidence/src-824b788eefc0/para-0010.md) · ✓ quote verified
[^c10]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 11](../evidence/src-824b788eefc0/para-0011.md) · ✓ quote verified
[^c11]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 12](../evidence/src-824b788eefc0/para-0012.md) · ✓ quote verified
[^c12]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 14](../evidence/src-824b788eefc0/para-0014.md) · ✓ quote verified
[^c13]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 15](../evidence/src-824b788eefc0/para-0015.md) · ✓ quote verified
[^c14]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 17](../evidence/src-824b788eefc0/para-0017.md) · ✓ quote verified
[^c15]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 20](../evidence/src-824b788eefc0/para-0020.md) · ✓ quote verified
[^c16]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 22](../evidence/src-824b788eefc0/para-0022.md) · ✓ quote verified
[^c17]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 23](../evidence/src-824b788eefc0/para-0023.md) · ✓ quote verified
[^c18]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 24](../evidence/src-824b788eefc0/para-0024.md) · ✓ quote verified
[^c19]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 27](../evidence/src-824b788eefc0/para-0027.md) · ✓ quote verified
[^c20]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 28](../evidence/src-824b788eefc0/para-0028.md) · ✓ quote verified
[^c21]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 30](../evidence/src-824b788eefc0/para-0030.md) · ✓ quote verified
[^c22]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 2, row 2](../evidence/src-824b788eefc0/tbl-02-r0002-r0002.md) · table
[^c23]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 1](../evidence/src-824b788eefc0/para-0001.md) · paraphrase
[^c24]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 2](../evidence/src-824b788eefc0/para-0002.md) · paraphrase
[^c25]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 2](../evidence/src-824b788eefc0/tbl-01-r0002-r0002.md) · table
[^c26]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 3](../evidence/src-824b788eefc0/tbl-01-r0003-r0003.md) · table
[^c27]: [WI-GEN-014 Rev. A - Generator Brush Replacement — table 1, row 4](../evidence/src-824b788eefc0/tbl-01-r0004-r0004.md) · table
[^c28]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 4](../evidence/src-824b788eefc0/para-0004.md) · paraphrase
[^c29]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 6](../evidence/src-824b788eefc0/para-0006.md) · paraphrase
[^c30]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 7](../evidence/src-824b788eefc0/para-0007.md) · paraphrase
[^c31]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 8](../evidence/src-824b788eefc0/para-0008.md) · paraphrase
[^c32]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 10](../evidence/src-824b788eefc0/para-0010.md) · paraphrase
[^c33]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 11](../evidence/src-824b788eefc0/para-0011.md) · paraphrase
[^c34]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 12](../evidence/src-824b788eefc0/para-0012.md) · paraphrase
[^c35]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 14](../evidence/src-824b788eefc0/para-0014.md) · paraphrase
[^c36]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 15](../evidence/src-824b788eefc0/para-0015.md) · paraphrase
[^c37]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 17](../evidence/src-824b788eefc0/para-0017.md) · paraphrase
[^c38]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 18](../evidence/src-824b788eefc0/para-0018.md) · paraphrase
[^c39]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 19](../evidence/src-824b788eefc0/para-0019.md) · paraphrase
[^c40]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 20](../evidence/src-824b788eefc0/para-0020.md) · paraphrase
[^c41]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 21](../evidence/src-824b788eefc0/para-0021.md) · paraphrase
[^c42]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 22](../evidence/src-824b788eefc0/para-0022.md) · paraphrase
[^c43]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 23](../evidence/src-824b788eefc0/para-0023.md) · paraphrase
[^c44]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 24](../evidence/src-824b788eefc0/para-0024.md) · paraphrase
[^c45]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 25](../evidence/src-824b788eefc0/para-0025.md) · paraphrase
[^c46]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 26](../evidence/src-824b788eefc0/para-0026.md) · paraphrase
[^c47]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 27](../evidence/src-824b788eefc0/para-0027.md) · paraphrase
[^c48]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 28](../evidence/src-824b788eefc0/para-0028.md) · paraphrase
[^c49]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 30](../evidence/src-824b788eefc0/para-0030.md) · paraphrase
