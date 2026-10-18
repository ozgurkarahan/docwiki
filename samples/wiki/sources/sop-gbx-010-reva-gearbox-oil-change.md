---
id: src-90ea27f71f0f
type: source
title: SOP-GBX-010 - Gearbox oil change, Revision A
summary: This standard operating procedure describes the safe gearbox oil change process for Quellmoor Ridge turbines. It covers scope, references, safety requirements, materials and tools, step-by-step work instructions, waste handling, records, and revision history.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- procedures
- sop
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-90ea27f71f0f
source_path: full/procedures/SOP-GBX-010_RevA_gearbox-oil-change.docx
source_hash: sha256:020494b99830170beea34aa9dd99a7d2e4abc9bee318c245e9dd93fd3e835505
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: sop
category: procedures
doc_number: SOP-GBX-010
revision: A
status: superseded
supersedes: []
superseded_by:
- src-70224c3b9c9f
original_lang: en
pages: null
entities:
- asset:om-building
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
- component:gearbox
- component:gearbox-heater
- component:oil-filter
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- part:fgt-p-11872
- part:pws-320-d208
- procedure:sop-gbx-010
- procedure:sop-loto-001
- procedure:sop-wah-003
- product:fgt-3200
- product:lt-32
- product:lt-32-ccv
- product:pwg-320
topics:
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:safety-and-access
authority: 7
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 39
    deterministic-table: 7
---

# SOP-GBX-010 - Gearbox oil change, Revision A

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

> **Superseded** by [SOP-GBX-010 Rev. B - Gearbox oil change](sop-gbx-010-revb-gearbox-oil-change.md). Use the current revision.

This standard operating procedure describes the safe [gearbox](../entities/component/gearbox.md) oil change process for [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) turbines. It covers scope, references, safety requirements, materials and tools, step-by-step work instructions, waste handling, records, and revision history.

## Key facts

- [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) is a standard operating procedure, Revision A, effective 2023-04-03.[^c1][^c2][^c3][^c4]
- The procedure applies to [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), specified as [Litware LT-32](../entities/product/lt-32.md) CCV turbines with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.[^c5]
- The procedure describes how to change [gearbox](../entities/component/gearbox.md) oil on [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) turbines safely and without contaminating the new oil.[^c6]
- The scope covers all gearbox oil changes on WTG-01 to WTG-12, whether planned or decided after oil analysis.[^c7]
- Referenced documents include LWS-MM-GBX-32 Rev. D section 4.3, [SOP-LOTO-001](../entities/procedure/sop-loto-001.md), [SOP-WAH-003](../entities/procedure/sop-wah-003.md), and oil level check at the sight glass.[^c8]
- A PTW is required, and at least two technicians are required with no lone working in the nacelle.[^c9]
- The turbine must be isolated according to SOP-LOTO-001 before the oil circuit is opened.[^c10]
- The job must not start if the 10-minute mean wind speed exceeds 15 m/s.[^c11]
- For hot oil work, technicians must wear chemical gloves, face shield, and long sleeves, and draining is allowed only between 40 and 60 °C.[^c12]
- The spill kit must be kept ready at the gearbox, with absorbent pads under every connection.[^c13]
- The specified new oil is [Proseware PWG 320](../entities/product/pwg-320.md) (ISO VG 320), with 410 L per turbine supplied as 2 drums [PWS-320-D208](../entities/part/pws-320-d208.md).[^c14]
- One [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) is required.[^c15]
- Required tools and containers include a filter cart with 10 micron element, transfer pump, three 200 L waste oil containers, a torque wrench covering 20 to 300 Nm, and oil sample bottles.[^c16][^c17]
- The work starts by obtaining the PTW, stopping the turbine, and applying lockout/tagout according to SOP-LOTO-001 with the rotor locked and drivetrain isolated.[^c18]
- Oil temperature must be checked, draining must be between 40 and 60 °C, and if the oil is colder the heaters and electric oil pump are to be run before isolation.[^c19]
- A used-oil sample must be taken at the sampling valve for the laboratory.[^c20]
- The gearbox sump and cooling and filter circuit are drained into waste containers, with an approximate drained volume of 410 L.[^c21]
- The magnetic plug is removed, debris is recorded, and the plug is cleaned.[^c22]
- The FGT-P-11872 filter element is replaced, and the filter housing cover screws are tightened to 85 Nm.[^c23]
- The drain plug is refitted with a new seal and tightened to 280 Nm.[^c24]
- 410 L of Proseware PWG 320 is filled through a 10 micron filter cart.[^c25]
- The electric oil pump is run for 15 minutes, after which all connections are checked for leaks.[^c26]
- After 20 minutes of standstill, the oil level is checked at the sight glass and topped up if needed.[^c27]
- After lockout removal and restart, oil temperature is watched during the first hour, and the turbine starts only when the oil sump has reached +10 °C.[^c28]
- A reference oil sample is taken after 24 hours of operation.[^c29]
- Quantities and batch numbers must be recorded in the work order.[^c30]
- Waste oil is sent to the bunded store in the O&M building and collected by the licensed carrier, and oil sample results are kept with the work order.[^c31]
- Revision A is the first issue and is associated with PWG 320.[^c32]

## Contents

### Document control

The document is titled “[SOP-GBX-010](../entities/procedure/sop-gbx-010.md) - [Gearbox](../entities/component/gearbox.md) oil change.”[^c33] It is a standard operating procedure, Revision A, effective 2023-04-03.[^c34] The owner is Dario Penwarden, O&M Supervisor, and the approver is Maren Ellingsby, Site Manager.[^c35][^c36] It applies to [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), described as [Litware LT-32](../entities/product/lt-32.md) CCV turbines with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.[^c5]

**Table t01** · table 1, rows 1–7

| Row | Field | Value |
| --- | --- | --- |
| 2 | Document number | SOP-GBX-010 |
| 3 | Revision | A |
| 4 | Effective date | 2023-04-03 |
| 5 | Owner | Dario Penwarden, O&M Supervisor |
| 6 | Approved by | Maren Ellingsby, Site Manager |
| 7 | Applies to | WTG-01 to WTG-12 (Litware LT-32 CCV, Fabrikam FGT-3200 gearbox) |

Agents can query this table as `t01` with the `query_table` tool.

### Purpose

The procedure describes how to change the [gearbox](../entities/component/gearbox.md) oil of the [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) turbines safely and without contaminating the new oil.[^c37]

### Scope

The scope covers all [gearbox](../entities/component/gearbox.md) oil changes on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), whether the work is planned or decided after oil analysis.[^c38]

### References

The listed references are LWS-MM-GBX-32 Rev. D section 4.3, [SOP-LOTO-001](../entities/procedure/sop-loto-001.md), [SOP-WAH-003](../entities/procedure/sop-wah-003.md), and oil level check at the sight glass.[^c8][^c39][^c40][^c41]

### Safety

- A PTW is required, at least two technicians are required, and lone working in the nacelle is prohibited.[^c42]
- The turbine must be isolated according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) before the oil circuit is opened.[^c43]
- The job must not start if the 10-minute mean wind speed exceeds 15 m/s.[^c44]
- For hot oil, chemical gloves, face shield, and long sleeves are required, and draining is only between 40 and 60 °C.[^c45]
- The spill kit must be ready at the [gearbox](../entities/component/gearbox.md), and absorbent pads must be placed under every connection.[^c46]

### Materials and tools

- The specified oil is [Proseware PWG 320](../entities/product/pwg-320.md) (ISO VG 320), 410 L per turbine, supplied as 2 drums [PWS-320-D208](../entities/part/pws-320-d208.md).[^c47]
- One [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) is required.[^c48]
- Required equipment includes a filter cart with 10 micron element, transfer pump, and 3 waste oil containers of 200 L.[^c49]
- Required tools and sampling items include a torque wrench covering 20 to 300 Nm and oil sample bottles.[^c50]

### Procedure

- Obtain the PTW, stop the turbine, and apply lockout/tagout according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) with the rotor locked and drivetrain isolated.[^c51]
- Check oil temperature and drain only between 40 and 60 °C; if colder, run the heaters and electric oil pump before isolation.[^c52]
- Take a used-oil sample at the sampling valve for the laboratory.[^c53]
- Drain the [gearbox](../entities/component/gearbox.md) sump and cooling and filter circuit into waste containers, about 410 L.[^c54]
- Remove the magnetic plug, record debris, and clean the plug.[^c55]
- Replace filter element [FGT-P-11872](../entities/part/fgt-p-11872.md) and tighten filter housing cover screws to 85 Nm.[^c56]
- Refit the drain plug with a new seal and tighten it to 280 Nm.[^c57]
- Fill 410 L of [Proseware PWG 320](../entities/product/pwg-320.md) through the 10 micron filter cart.[^c58]
- Run the electric oil pump for 15 minutes and check all connections for leaks.[^c59]
- After 20 minutes of standstill, check the level at the sight glass and top up if needed.[^c60]
- Remove lockout, restart, and watch oil temperature during the first hour; the turbine starts only when the oil sump has reached +10 °C.[^c61]
- Take a reference oil sample after 24 hours of operation.[^c62]
- Record quantities and batch numbers in the work order.[^c63]

### Waste and records

Waste oil goes to the bunded store in the O&M building and is collected by the licensed carrier.[^c64] Oil sample results are kept with the work order.[^c64]

### Revision history

Revision A dated 2023-04-03 is the first issue and refers to [PWG 320](../entities/product/pwg-320.md).[^c32]

**Table t02** · table 2, rows 1–2

| Row | Revision | Date | Change |
| --- | --- | --- | --- |
| 2 | A | 2023-04-03 | First issue (PWG 320). |

Agents can query this table as `t02` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [oil filter element](../entities/component/oil-filter.md)
- Spare parts: [FGT-P-11872](../entities/part/fgt-p-11872.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- Organisations: [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Safety, isolation and work at height](../topics/safety-and-access.md)
- Superseded by: [SOP-GBX-010 Rev. B - Gearbox oil change](sop-gbx-010-revb-gearbox-oil-change.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-320-D208](../entities/part/pws-320-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
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

[^c1]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 2](../evidence/src-90ea27f71f0f/para-0002.md) · ✓ quote verified
[^c2]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 2](../evidence/src-90ea27f71f0f/tbl-01-r0002-r0002.md) · table
[^c3]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 3](../evidence/src-90ea27f71f0f/tbl-01-r0003-r0003.md) · table
[^c4]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 4](../evidence/src-90ea27f71f0f/tbl-01-r0004-r0004.md) · table
[^c5]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 7](../evidence/src-90ea27f71f0f/tbl-01-r0007-r0007.md) · table
[^c6]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 4](../evidence/src-90ea27f71f0f/para-0004.md) · ✓ quote verified
[^c7]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 6](../evidence/src-90ea27f71f0f/para-0006.md) · ✓ quote verified
[^c8]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 8](../evidence/src-90ea27f71f0f/para-0008.md) · paraphrase
[^c9]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 13](../evidence/src-90ea27f71f0f/para-0013.md) · ✓ quote verified
[^c10]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 14](../evidence/src-90ea27f71f0f/para-0014.md) · ✓ quote verified
[^c11]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 15](../evidence/src-90ea27f71f0f/para-0015.md) · ✓ quote verified
[^c12]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 16](../evidence/src-90ea27f71f0f/para-0016.md) · ✓ quote verified
[^c13]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 17](../evidence/src-90ea27f71f0f/para-0017.md) · ✓ quote verified
[^c14]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 19](../evidence/src-90ea27f71f0f/para-0019.md) · ✓ quote verified
[^c15]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 20](../evidence/src-90ea27f71f0f/para-0020.md) · ✓ quote verified
[^c16]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 21](../evidence/src-90ea27f71f0f/para-0021.md) · ✓ quote verified
[^c17]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 22](../evidence/src-90ea27f71f0f/para-0022.md) · ✓ quote verified
[^c18]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 24](../evidence/src-90ea27f71f0f/para-0024.md) · ✓ quote verified
[^c19]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 25](../evidence/src-90ea27f71f0f/para-0025.md) · ✓ quote verified
[^c20]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 26](../evidence/src-90ea27f71f0f/para-0026.md) · ✓ quote verified
[^c21]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 27](../evidence/src-90ea27f71f0f/para-0027.md) · ✓ quote verified
[^c22]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 28](../evidence/src-90ea27f71f0f/para-0028.md) · ✓ quote verified
[^c23]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 29](../evidence/src-90ea27f71f0f/para-0029.md) · ✓ quote verified
[^c24]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 30](../evidence/src-90ea27f71f0f/para-0030.md) · ✓ quote verified
[^c25]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 31](../evidence/src-90ea27f71f0f/para-0031.md) · ✓ quote verified
[^c26]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 32](../evidence/src-90ea27f71f0f/para-0032.md) · ✓ quote verified
[^c27]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 33](../evidence/src-90ea27f71f0f/para-0033.md) · ✓ quote verified
[^c28]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 34](../evidence/src-90ea27f71f0f/para-0034.md) · ✓ quote verified
[^c29]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 35](../evidence/src-90ea27f71f0f/para-0035.md) · ✓ quote verified
[^c30]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 36](../evidence/src-90ea27f71f0f/para-0036.md) · ✓ quote verified
[^c31]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 38](../evidence/src-90ea27f71f0f/para-0038.md) · ✓ quote verified
[^c32]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 2, row 2](../evidence/src-90ea27f71f0f/tbl-02-r0002-r0002.md) · table
[^c33]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 1](../evidence/src-90ea27f71f0f/para-0001.md) · paraphrase
[^c34]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 2](../evidence/src-90ea27f71f0f/para-0002.md) · paraphrase
[^c35]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 5](../evidence/src-90ea27f71f0f/tbl-01-r0005-r0005.md) · table
[^c36]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 1, row 6](../evidence/src-90ea27f71f0f/tbl-01-r0006-r0006.md) · table
[^c37]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 4](../evidence/src-90ea27f71f0f/para-0004.md) · paraphrase
[^c38]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 6](../evidence/src-90ea27f71f0f/para-0006.md) · paraphrase
[^c39]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 9](../evidence/src-90ea27f71f0f/para-0009.md) · paraphrase
[^c40]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 10](../evidence/src-90ea27f71f0f/para-0010.md) · paraphrase
[^c41]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 11](../evidence/src-90ea27f71f0f/para-0011.md) · paraphrase
[^c42]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 13](../evidence/src-90ea27f71f0f/para-0013.md) · paraphrase
[^c43]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 14](../evidence/src-90ea27f71f0f/para-0014.md) · paraphrase
[^c44]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 15](../evidence/src-90ea27f71f0f/para-0015.md) · paraphrase
[^c45]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 16](../evidence/src-90ea27f71f0f/para-0016.md) · paraphrase
[^c46]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 17](../evidence/src-90ea27f71f0f/para-0017.md) · paraphrase
[^c47]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 19](../evidence/src-90ea27f71f0f/para-0019.md) · paraphrase
[^c48]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 20](../evidence/src-90ea27f71f0f/para-0020.md) · paraphrase
[^c49]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 21](../evidence/src-90ea27f71f0f/para-0021.md) · paraphrase
[^c50]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 22](../evidence/src-90ea27f71f0f/para-0022.md) · paraphrase
[^c51]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 24](../evidence/src-90ea27f71f0f/para-0024.md) · paraphrase
[^c52]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 25](../evidence/src-90ea27f71f0f/para-0025.md) · paraphrase
[^c53]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 26](../evidence/src-90ea27f71f0f/para-0026.md) · paraphrase
[^c54]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 27](../evidence/src-90ea27f71f0f/para-0027.md) · paraphrase
[^c55]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 28](../evidence/src-90ea27f71f0f/para-0028.md) · paraphrase
[^c56]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 29](../evidence/src-90ea27f71f0f/para-0029.md) · paraphrase
[^c57]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 30](../evidence/src-90ea27f71f0f/para-0030.md) · paraphrase
[^c58]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 31](../evidence/src-90ea27f71f0f/para-0031.md) · paraphrase
[^c59]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 32](../evidence/src-90ea27f71f0f/para-0032.md) · paraphrase
[^c60]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 33](../evidence/src-90ea27f71f0f/para-0033.md) · paraphrase
[^c61]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 34](../evidence/src-90ea27f71f0f/para-0034.md) · paraphrase
[^c62]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 35](../evidence/src-90ea27f71f0f/para-0035.md) · paraphrase
[^c63]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 36](../evidence/src-90ea27f71f0f/para-0036.md) · paraphrase
[^c64]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 38](../evidence/src-90ea27f71f0f/para-0038.md) · paraphrase
