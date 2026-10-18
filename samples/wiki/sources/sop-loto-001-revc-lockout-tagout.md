---
id: src-21bd4ddf2ed6
type: source
title: SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines
summary: This standard operating procedure defines lockout/tagout for wind turbines and related low-voltage substation boards at Quellmoor Ridge. It covers responsibilities, LT-32 energy sources, personal padlocks and tags, isolation, verification, removal, and revision history.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- procedures
- sop
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-21bd4ddf2ed6
source_path: full/procedures/SOP-LOTO-001_RevC_lockout-tagout.docx
source_hash: sha256:829fe0651fc73d2a622e4733afbf8ae9371f30dcff150ed9e099972bd7dbed7b
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: sop
category: procedures
doc_number: SOP-LOTO-001
revision: C
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- asset:quellmoor-ridge-substation
- asset:quellmoor-ridge-wind-farm
- asset:wtg-01
- asset:wtg-12
- component:generator
- procedure:sop-loto-001
- product:lt-32
- status-code:s310
topics:
- topic:safety-and-access
authority: 7
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 25
    deterministic-table: 14
---

# SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This standard operating procedure defines lockout/tagout for wind turbines and related low-voltage substation boards at [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md). It covers responsibilities, [LT-32](../entities/product/lt-32.md) energy sources, personal padlocks and tags, isolation, verification, removal, and revision history.

## Key facts

- [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) is Revision C and was effective on 2024-09-02.[^c1][^c2]
- The procedure owner is Greta Vollan, HSE Coordinator, and it was approved by Maren Ellingsby, Site Manager.[^c3][^c4]
- The purpose is to protect people working on a turbine against unexpected release of electrical, hydraulic, mechanical, rotational, and thermal energy.[^c5]
- The procedure applies to all work on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) and on the [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md) low-voltage boards.[^c6]
- High-voltage switching is outside this procedure and is performed only by authorised persons under the switching programme.[^c6]
- The PTW issuer checks the isolation list before signing the PTW.[^c7]
- Each worker must apply a personal padlock and keep the key.[^c8]
- Any deviation requires written approval by the O&M Supervisor.[^c9]
- For [LT-32](../entities/product/lt-32.md) electrical 690 V energy from the [generator](../entities/component/generator.md), converter, and auxiliaries is isolated at the main circuit breaker in the tower base.[^c10]
- For LT-32 electrical 33 kV energy from the transformer feeder is isolated at the ring main unit, which is for authorised persons only.[^c11]
- For LT-32 controller uninterruptible power, the source is the UPS of the controller and the isolation point is the UPS output breaker.[^c12]
- For LT-32 hydraulic energy from pitch and yaw brake accumulators, the isolation point is relief valves to 0 bar.[^c13]
- For LT-32 rotational energy from the rotor and drivetrain, the isolation point is the rotor lock pins.[^c14]
- For LT-32 thermal energy from hot gear oil and heaters, the isolation point is cool-down and the heater breaker.[^c15]
- Every worker uses a personal padlock with a name tag, and padlocks without a name tag must not be used.[^c16]
- Spare padlocks are issued by the HSE Coordinator.[^c16]
- The isolation sequence starts by informing the control room and setting the turbine to [maintenance mode](../entities/status-code/s310.md), status S310.[^c17]
- The turbine is stopped from the controller and the rotor speed must be below 1 rpm before continuing.[^c18]
- Rotor lock pins are engaged, but they must not be engaged above a 10-minute mean wind speed of 15 m/s.[^c19]
- The main circuit breaker and UPS output breaker are opened, then padlocks and tags are applied.[^c20]
- Hydraulic pressure of the pitch and yaw brake accumulators is released to 0 bar.[^c21]
- A group lock box is applied when more than two people work on the turbine.[^c22]
- Before work starts, verification requires trying to start the turbine from the local panel, testing for absence of voltage at the converter, and reading 0 bar on accumulator gauges.[^c23]
- During removal, each worker removes only his or her own padlock.[^c24]
- The last person checks that tools are removed and guards are fitted before the turbine leaves maintenance mode.[^c24]
- Revision C updated the energy table and added the wind limit for rotor lock pins.[^c25]

## Contents

### Document control

This document is a standard operating procedure, Revision C, effective 2024-09-02.[^c26]

The document control table gives the document number, revision, effective date, owner, and approver.[^c2][^c27][^c28][^c3][^c4]

**Table t01** · table 1, rows 1–6

| Row | Field | Value |
| --- | --- | --- |
| 2 | Document number | [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) |
| 3 | Revision | C |
| 4 | Effective date | 2024-09-02 |
| 5 | Owner | Greta Vollan, HSE Coordinator |
| 6 | Approved by | Maren Ellingsby, Site Manager |

Agents can query this table as `t01` with the `query_table` tool.

### Purpose

The procedure is intended to protect people working on a turbine against unexpected release of electrical, hydraulic, mechanical, rotational, and thermal energy.[^c29]

### Scope

The scope covers all work on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) and on the [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md) low-voltage boards.[^c30]

High-voltage switching is done only by authorised persons under the switching programme and is outside this procedure.[^c30]

### Responsibilities

- The PTW issuer checks the isolation list before signing the PTW.[^c31]
- Each worker applies a personal padlock and keeps the key.[^c32]
- The O&M Supervisor approves any deviation in writing.[^c33]

### Energy sources of the LT-32

The procedure includes an energy-source and isolation-point table for the [LT-32](../entities/product/lt-32.md).[^c34]

**Table t02** · table 2, rows 1–7

| Row | Energy | Source | Isolation point |
| --- | --- | --- | --- |
| 2 | Electrical 690 V | [Generator](../entities/component/generator.md), converter, auxiliaries | Main circuit breaker in the tower base |
| 3 | Electrical 33 kV | Transformer feeder | Ring main unit (authorised persons only) |
| 4 | Uninterruptible power | UPS of the controller | UPS output breaker |
| 5 | Hydraulic | Pitch and yaw brake accumulators | Relief valves to 0 bar |
| 6 | Rotational | Rotor and drivetrain | Rotor lock pins |
| 7 | Thermal | Hot gear oil, heaters | Cool-down and heater breaker |

Agents can query this table as `t02` with the `query_table` tool.

### Personal padlocks and tags

Every worker uses a personal padlock with a name tag.[^c35] Padlocks without a name tag must not be used.[^c35] Spare padlocks are issued by the HSE Coordinator.[^c35]

### Isolation sequence

- Inform the control room and set the turbine to [maintenance mode](../entities/status-code/s310.md), status S310.[^c36]
- Stop the turbine from the controller and wait until the rotor speed is below 1 rpm.[^c37]
- Engage the rotor lock pins, but do not engage them above a 10-minute mean wind speed of 15 m/s.[^c38]
- Open the main circuit breaker and the UPS output breaker, then apply padlocks and tags.[^c39]
- Release the hydraulic pressure of the pitch and yaw brake accumulators to 0 bar.[^c40]
- Apply the group lock box when more than two people work on the turbine.[^c41]

### Verification

Before work starts, try to start the turbine from the local panel, test for absence of voltage at the converter, and read 0 bar on the accumulator gauges.[^c42]

### Removal

Each worker removes only his or her own padlock.[^c43] The last person checks that tools are removed and guards are fitted before the turbine leaves [maintenance mode](../entities/status-code/s310.md).[^c43]

### Revision history

The revision history records first issue at commercial operation, addition of the group lock box, and Revision C updates to the energy table and the wind limit for rotor lock pins.[^c44][^c45][^c25]

**Table t03** · table 3, rows 1–4

| Row | Revision | Date | Change |
| --- | --- | --- | --- |
| 2 | A | 2019-10-01 | First issue at commercial operation. |
| 3 | B | 2021-05-17 | Group lock box added. |
| 4 | C | 2024-09-02 | Energy table updated; wind limit for rotor lock pins. |

Agents can query this table as `t03` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-12](../entities/asset/wtg-12.md)
- Component: [generator](../entities/component/generator.md)
- Product: [Litware LT-32](../entities/product/lt-32.md)
- Status code: [S310 Maintenance mode](../entities/status-code/s310.md)
- Procedure: [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- Topic: [Safety, isolation and work at height](../topics/safety-and-access.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [generator](../entities/component/generator.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [S310 Maintenance mode](../entities/status-code/s310.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [WTG-01](../entities/asset/wtg-01.md)
- [WTG-12](../entities/asset/wtg-12.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 2](../evidence/src-21bd4ddf2ed6/para-0002.md) · ✓ quote verified
[^c2]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 1, row 2](../evidence/src-21bd4ddf2ed6/tbl-01-r0002-r0002.md) · table
[^c3]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 1, row 5](../evidence/src-21bd4ddf2ed6/tbl-01-r0005-r0005.md) · table
[^c4]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 1, row 6](../evidence/src-21bd4ddf2ed6/tbl-01-r0006-r0006.md) · table
[^c5]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 4](../evidence/src-21bd4ddf2ed6/para-0004.md) · ✓ quote verified
[^c6]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 6](../evidence/src-21bd4ddf2ed6/para-0006.md) · ✓ quote verified
[^c7]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 8](../evidence/src-21bd4ddf2ed6/para-0008.md) · ✓ quote verified
[^c8]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 9](../evidence/src-21bd4ddf2ed6/para-0009.md) · ✓ quote verified
[^c9]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 10](../evidence/src-21bd4ddf2ed6/para-0010.md) · ✓ quote verified
[^c10]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 2](../evidence/src-21bd4ddf2ed6/tbl-02-r0002-r0002.md) · table
[^c11]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 3](../evidence/src-21bd4ddf2ed6/tbl-02-r0003-r0003.md) · table
[^c12]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 4](../evidence/src-21bd4ddf2ed6/tbl-02-r0004-r0004.md) · table
[^c13]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 5](../evidence/src-21bd4ddf2ed6/tbl-02-r0005-r0005.md) · table
[^c14]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 6](../evidence/src-21bd4ddf2ed6/tbl-02-r0006-r0006.md) · table
[^c15]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 7](../evidence/src-21bd4ddf2ed6/tbl-02-r0007-r0007.md) · table
[^c16]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 13](../evidence/src-21bd4ddf2ed6/para-0013.md) · ✓ quote verified
[^c17]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 15](../evidence/src-21bd4ddf2ed6/para-0015.md) · ✓ quote verified
[^c18]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 16](../evidence/src-21bd4ddf2ed6/para-0016.md) · ✓ quote verified
[^c19]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 17](../evidence/src-21bd4ddf2ed6/para-0017.md) · ✓ quote verified
[^c20]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 18](../evidence/src-21bd4ddf2ed6/para-0018.md) · ✓ quote verified
[^c21]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 19](../evidence/src-21bd4ddf2ed6/para-0019.md) · ✓ quote verified
[^c22]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 20](../evidence/src-21bd4ddf2ed6/para-0020.md) · ✓ quote verified
[^c23]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 22](../evidence/src-21bd4ddf2ed6/para-0022.md) · ✓ quote verified
[^c24]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 24](../evidence/src-21bd4ddf2ed6/para-0024.md) · ✓ quote verified
[^c25]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 3, row 4](../evidence/src-21bd4ddf2ed6/tbl-03-r0004-r0004.md) · table
[^c26]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 2](../evidence/src-21bd4ddf2ed6/para-0002.md) · paraphrase
[^c27]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 1, row 3](../evidence/src-21bd4ddf2ed6/tbl-01-r0003-r0003.md) · table
[^c28]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 1, row 4](../evidence/src-21bd4ddf2ed6/tbl-01-r0004-r0004.md) · table
[^c29]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 4](../evidence/src-21bd4ddf2ed6/para-0004.md) · paraphrase
[^c30]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 6](../evidence/src-21bd4ddf2ed6/para-0006.md) · paraphrase
[^c31]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 8](../evidence/src-21bd4ddf2ed6/para-0008.md) · paraphrase
[^c32]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 9](../evidence/src-21bd4ddf2ed6/para-0009.md) · paraphrase
[^c33]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 10](../evidence/src-21bd4ddf2ed6/para-0010.md) · paraphrase
[^c34]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 11](../evidence/src-21bd4ddf2ed6/para-0011.md) · paraphrase
[^c35]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 13](../evidence/src-21bd4ddf2ed6/para-0013.md) · paraphrase
[^c36]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 15](../evidence/src-21bd4ddf2ed6/para-0015.md) · paraphrase
[^c37]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 16](../evidence/src-21bd4ddf2ed6/para-0016.md) · paraphrase
[^c38]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 17](../evidence/src-21bd4ddf2ed6/para-0017.md) · paraphrase
[^c39]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 18](../evidence/src-21bd4ddf2ed6/para-0018.md) · paraphrase
[^c40]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 19](../evidence/src-21bd4ddf2ed6/para-0019.md) · paraphrase
[^c41]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 20](../evidence/src-21bd4ddf2ed6/para-0020.md) · paraphrase
[^c42]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 22](../evidence/src-21bd4ddf2ed6/para-0022.md) · paraphrase
[^c43]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 24](../evidence/src-21bd4ddf2ed6/para-0024.md) · paraphrase
[^c44]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 3, row 2](../evidence/src-21bd4ddf2ed6/tbl-03-r0002-r0002.md) · table
[^c45]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 3, row 3](../evidence/src-21bd4ddf2ed6/tbl-03-r0003-r0003.md) · table
