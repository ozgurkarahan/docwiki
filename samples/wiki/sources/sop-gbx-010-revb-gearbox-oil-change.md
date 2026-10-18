---
id: src-70224c3b9c9f
type: source
title: SOP-GBX-010 Rev. B - Gearbox oil change
summary: This standard operating procedure describes the gearbox oil change process for Quellmoor Ridge turbines. It covers scope, references, safety, materials, procedural steps, waste handling, records, and revision history for the change to PWG 220 oil.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- procedures
- sop
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-70224c3b9c9f
source_path: full/procedures/SOP-GBX-010_RevB_gearbox-oil-change.docx
source_hash: sha256:1997d662d94389d615e4b8d6a6252e7811b7790702e7d38742555f5e4f295626
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: sop
category: procedures
doc_number: SOP-GBX-010
revision: B
status: current
supersedes:
- src-90ea27f71f0f
superseded_by: []
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
- bulletin:sb-lws-2025-07
- component:gearbox
- component:oil-filter
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- part:fgt-p-11872
- part:pws-220-d208
- procedure:sop-gbx-010
- procedure:sop-loto-001
- procedure:sop-wah-003
- procedure:spl-012
- product:fgt-3200
- product:lt-32
- product:lt-32-ccv
- product:pwg-220
- product:pwg-320
topics:
- topic:cold-climate-operation
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:safety-and-access
authority: 7
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 45
    deterministic-table: 8
---

# SOP-GBX-010 Rev. B - Gearbox oil change

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This standard operating procedure describes the [gearbox](../entities/component/gearbox.md) oil change process for [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) turbines. It covers scope, references, safety, materials, procedural steps, waste handling, records, and revision history for the change to [PWG 220](../entities/product/pwg-220.md) oil.

## Key facts

- [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) is Revision B and is effective from 2025-08-25.[^c1]
- The procedure applies to [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) with [Litware LT-32](../entities/product/lt-32.md) CCV turbines and [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.[^c2]
- Revision B supersedes SOP-GBX-010 Rev. A and implements MOC-2025-012 and [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A.[^c3]
- The procedure is intended to change [gearbox](../entities/component/gearbox.md) oil safely and avoid contaminating the new oil.[^c4]
- The scope covers all gearbox oil changes on WTG-01 to WTG-12, including planned changes and changes decided after oil analysis.[^c5]
- A PTW is required, and at least two technicians must be present; lone working in the nacelle is not allowed.[^c6]
- The turbine must be isolated according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) before the oil circuit is opened.[^c7]
- The job must not start if the 10-minute mean wind speed exceeds 15 m/s.[^c8]
- Hot oil controls require chemical gloves, a face shield, long sleeves, and draining only between 40 and 60 °C.[^c9]
- The spill kit must be ready at the gearbox, with absorbent pads under every connection.[^c10]
- Each turbine requires 470 L of [Proseware PWG 220](../entities/product/pwg-220.md), consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of [PWS-220-D208](../entities/part/pws-220-d208.md).[^c11]
- One [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) is required.[^c12]
- Required equipment includes a filter cart with a 10 micron element, a transfer pump, and 3 waste oil containers of 200 L.[^c13]
- Required tools include a torque wrench with a 20 to 300 Nm range, oil sample bottles, and a PWG 220 label kit.[^c14]
- Before draining, the PTW must be obtained, the turbine stopped, and lockout/tagout applied with the rotor locked and drivetrain isolated.[^c15]
- Oil temperature must be checked and oil drained between 40 and 60 °C; if colder, heaters and the electric oil pump are run before isolation.[^c16]
- The used oil sample is taken at the sampling valve for the laboratory.[^c17]
- The gearbox sump and the cooling and filter circuit are drained into waste containers, with an approximate drained volume of 410 L.[^c18]
- The filter element FGT-P-11872 is replaced and the filter housing cover screws are tightened to 85 Nm.[^c19]
- The drain plug is refitted with a new seal and tightened to 280 Nm.[^c20]
- The flush step uses 60 L of PWG 220, runs the electric oil pump for 30 minutes, and then drains the flush oil into waste containers.[^c21]
- The gearbox is filled with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c22]
- After filling, the electric oil pump is run for 15 minutes and all connections are checked for leaks.[^c23]
- After 20 minutes of standstill, the oil level is checked at the sight glass according to [SPL-012](../entities/procedure/spl-012.md) and topped up only with PWG 220.[^c24]
- Controller parameter GBX_TMIN_START must be set to 5 °C, and the gearbox filler must be labelled PWG 220.[^c25]
- On restart, oil temperature is watched during the first hour, and the turbine starts only once the oil sump has reached +5 °C.[^c26]
- A reference oil sample is taken after 24 hours of operation.[^c27]
- Quantities and batch numbers are recorded in the work order, and the completion form is sent to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) within 30 days.[^c28]
- A converted gearbox must never be topped up with [PWG 320](../entities/product/pwg-320.md), and residual PWG 320 must remain below 5 % of oil volume.[^c29]
- Waste oil is stored in the bunded store in the O&M building and collected by the licensed carrier; oil sample results are kept with the work order.[^c30]
- Revision B changed the oil to PWG 220 per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c31]

## Contents

### Document control

The document is [SOP-GBX-010](../entities/procedure/sop-gbx-010.md), “[Gearbox](../entities/component/gearbox.md) oil change.”[^c32] It is a standard operating procedure, Revision B, effective 2025-08-25.[^c33] The document-control table identifies the document number, revision, effective date, owner, approver, and applicability.[^c34] It applies to [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) with [Litware LT-32](../entities/product/lt-32.md) CCV turbines and [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.[^c2] Revision B supersedes SOP-GBX-010 Rev. A and implements MOC-2025-012 and [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A.[^c35]

**Table t01** · table 1, rows 1–7

| Row | Field | Value |
| --- | --- | --- |
| 2 | Document number | SOP-GBX-010 |
| 3 | Revision | B |
| 4 | Effective date | 2025-08-25 |
| 5 | Owner | Dario Penwarden, O&M Supervisor |
| 6 | Approved by | Maren Ellingsby, Site Manager |
| 7 | Applies to | WTG-01 to WTG-12 (Litware LT-32 CCV, Fabrikam FGT-3200 gearbox) |

Agents can query this table as `t01` with the `query_table` tool.

### Purpose

The procedure describes how to change the [gearbox](../entities/component/gearbox.md) oil of the [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) turbines safely and without contaminating the new oil.[^c36]

### Scope

The scope covers all [gearbox](../entities/component/gearbox.md) oil changes on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), whether planned or decided after an oil analysis.[^c37]

### References

- The referenced [Litware](../entities/organisation/litware-wind-systems.md) maintenance manual is LWS-MM-GBX-32 Rev. D, section 4.3, for the [gearbox](../entities/component/gearbox.md).[^c38]
- The referenced service bulletin is [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A for gear oil for CCV turbines.[^c39]
- The referenced management of change is MOC-2025-012 for changing the gearbox oil grade to [PWG 220](../entities/product/pwg-220.md).[^c40]
- The referenced [lockout/tagout procedure](../entities/procedure/sop-loto-001.md) is SOP-LOTO-001.[^c41]
- The referenced working-at-height and rescue procedure is [SOP-WAH-003](../entities/procedure/sop-wah-003.md).[^c42]
- The referenced single-point lesson is [SPL-012](../entities/procedure/spl-012.md) for gearbox oil level checks.[^c43]

### Safety

- A PTW is required, with two technicians minimum and no lone working in the nacelle.[^c44]
- The turbine must be isolated according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) before the oil circuit is opened.[^c45]
- The job must not start if the 10-minute mean wind speed exceeds 15 m/s.[^c46]
- For hot oil, technicians must wear chemical gloves, a face shield, and long sleeves, and drain only between 40 and 60 °C.[^c47]
- The spill kit must be kept ready at the [gearbox](../entities/component/gearbox.md), with absorbent pads under every connection.[^c48]

### Materials and tools

- The required gear oil is [Proseware PWG 220](../entities/product/pwg-220.md) (ISO VG 220), with 470 L per turbine made up of 60 L for flushing and 410 L for filling, supplied as 3 drums of [PWS-220-D208](../entities/part/pws-220-d208.md).[^c49]
- One [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) is required.[^c50]
- Required equipment includes a filter cart with a 10 micron element, a transfer pump, and 3 waste oil containers of 200 L.[^c51]
- Required tools and consumables include a 20 to 300 Nm torque wrench, oil sample bottles, and a PWG 220 label kit.[^c52]

### Procedure

- Obtain the PTW, stop the turbine, and apply lockout/tagout according to [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) with the rotor locked and drivetrain isolated.[^c53]
- Check the oil temperature and drain between 40 and 60 °C; if the oil is colder, run the heaters and electric oil pump before isolation.[^c54]
- Take a used-oil sample at the sampling valve for the laboratory.[^c55]
- Drain the [gearbox](../entities/component/gearbox.md) sump and the cooling and filter circuit into the waste containers, about 410 L.[^c56]
- Remove the magnetic plug, record the debris, and clean the plug.[^c57]
- Replace filter element [FGT-P-11872](../entities/part/fgt-p-11872.md) and tighten the filter housing cover screws to 85 Nm.[^c58]
- Refit the drain plug with a new seal and tighten it to 280 Nm.[^c59]
- Flush by filling 60 L of [PWG 220](../entities/product/pwg-220.md), [running](../entities/status-code/s100.md) the electric oil pump for 30 minutes, and draining the flush oil into the waste containers.[^c60]
- Fill 410 L of Proseware PWG 220 through the 10 micron filter cart.[^c61]
- Run the electric oil pump for 15 minutes and check all connections for leaks.[^c62]
- After 20 minutes of standstill, check the level at the sight glass according to [SPL-012](../entities/procedure/spl-012.md) and top up only with PWG 220.[^c63]
- Check that controller parameter GBX_TMIN_START is set to 5 °C and label the gearbox filler “PWG 220.”[^c64]
- Remove lockout, restart, and watch oil temperature during the first hour; the turbine starts only when the oil sump has reached +5 °C.[^c65]
- Take a reference oil sample after 24 hours of operation.[^c66]
- Record quantities and batch numbers in the work order and send the completion form to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) within 30 days.[^c67]
- Never top up a converted gearbox with [PWG 320](../entities/product/pwg-320.md), and keep residual PWG 320 below 5 % of oil volume.[^c68]

### Waste and records

Waste oil goes to the bunded store in the O&M building and is collected by the licensed carrier.[^c69] Oil sample results must be kept with the work order.[^c69]

### Revision history

Revision history records Revision A as the first issue using [PWG 320](../entities/product/pwg-320.md).[^c70] Revision B, dated 2025-08-25, changed the oil to [PWG 220](../entities/product/pwg-220.md) per MOC-2025-012 and [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md), added the flush step, and set the minimum start-up temperature to +5 °C.[^c31]

**Table t02** · table 2, rows 1–3

| Row | Revision | Date | Change |
| --- | --- | --- | --- |
| 2 | A | 2023-04-03 | First issue (PWG 320). |
| 3 | B | 2025-08-25 | Oil changed to PWG 220 per MOC-2025-012 and SB-LWS-2025-07; flush step added; minimum start-up temperature +5 °C. |

Agents can query this table as `t02` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [oil filter element](../entities/component/oil-filter.md)
- Spare parts: [FGT-P-11872](../entities/part/fgt-p-11872.md), [PWS-220-D208](../entities/part/pws-220-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Safety, isolation and work at height](../topics/safety-and-access.md)
- Supersedes: [SOP-GBX-010 - Gearbox oil change, Revision A](sop-gbx-010-reva-gearbox-oil-change.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Cold-climate operation and icing](../topics/cold-climate-operation.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md)
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

[^c1]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 2](../evidence/src-70224c3b9c9f/para-0002.md) · ✓ quote verified
[^c2]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 1, row 7](../evidence/src-70224c3b9c9f/tbl-01-r0007-r0007.md) · table
[^c3]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 3](../evidence/src-70224c3b9c9f/para-0003.md) · ✓ quote verified
[^c4]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 5](../evidence/src-70224c3b9c9f/para-0005.md) · ✓ quote verified
[^c5]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 7](../evidence/src-70224c3b9c9f/para-0007.md) · ✓ quote verified
[^c6]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 16](../evidence/src-70224c3b9c9f/para-0016.md) · ✓ quote verified
[^c7]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 17](../evidence/src-70224c3b9c9f/para-0017.md) · ✓ quote verified
[^c8]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 18](../evidence/src-70224c3b9c9f/para-0018.md) · ✓ quote verified
[^c9]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 19](../evidence/src-70224c3b9c9f/para-0019.md) · ✓ quote verified
[^c10]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 20](../evidence/src-70224c3b9c9f/para-0020.md) · ✓ quote verified
[^c11]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 22](../evidence/src-70224c3b9c9f/para-0022.md) · ✓ quote verified
[^c12]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 23](../evidence/src-70224c3b9c9f/para-0023.md) · ✓ quote verified
[^c13]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 24](../evidence/src-70224c3b9c9f/para-0024.md) · ✓ quote verified
[^c14]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 25](../evidence/src-70224c3b9c9f/para-0025.md) · ✓ quote verified
[^c15]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 27](../evidence/src-70224c3b9c9f/para-0027.md) · ✓ quote verified
[^c16]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 28](../evidence/src-70224c3b9c9f/para-0028.md) · ✓ quote verified
[^c17]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 29](../evidence/src-70224c3b9c9f/para-0029.md) · ✓ quote verified
[^c18]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 30](../evidence/src-70224c3b9c9f/para-0030.md) · ✓ quote verified
[^c19]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 32](../evidence/src-70224c3b9c9f/para-0032.md) · ✓ quote verified
[^c20]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 33](../evidence/src-70224c3b9c9f/para-0033.md) · ✓ quote verified
[^c21]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 34](../evidence/src-70224c3b9c9f/para-0034.md) · ✓ quote verified
[^c22]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 35](../evidence/src-70224c3b9c9f/para-0035.md) · ✓ quote verified
[^c23]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 36](../evidence/src-70224c3b9c9f/para-0036.md) · ✓ quote verified
[^c24]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 37](../evidence/src-70224c3b9c9f/para-0037.md) · ✓ quote verified
[^c25]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 38](../evidence/src-70224c3b9c9f/para-0038.md) · ✓ quote verified
[^c26]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 39](../evidence/src-70224c3b9c9f/para-0039.md) · ✓ quote verified
[^c27]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 40](../evidence/src-70224c3b9c9f/para-0040.md) · ✓ quote verified
[^c28]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 41](../evidence/src-70224c3b9c9f/para-0041.md) · ✓ quote verified
[^c29]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 42](../evidence/src-70224c3b9c9f/para-0042.md) · ✓ quote verified
[^c30]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 44](../evidence/src-70224c3b9c9f/para-0044.md) · ✓ quote verified
[^c31]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 2, row 3](../evidence/src-70224c3b9c9f/tbl-02-r0003-r0003.md) · table
[^c32]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 1](../evidence/src-70224c3b9c9f/para-0001.md) · paraphrase
[^c33]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 2](../evidence/src-70224c3b9c9f/para-0002.md) · paraphrase
[^c34]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 1, row 2](../evidence/src-70224c3b9c9f/tbl-01-r0002-r0002.md) · table
[^c35]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 3](../evidence/src-70224c3b9c9f/para-0003.md) · paraphrase
[^c36]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 5](../evidence/src-70224c3b9c9f/para-0005.md) · paraphrase
[^c37]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 7](../evidence/src-70224c3b9c9f/para-0007.md) · paraphrase
[^c38]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 9](../evidence/src-70224c3b9c9f/para-0009.md) · paraphrase
[^c39]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 10](../evidence/src-70224c3b9c9f/para-0010.md) · paraphrase
[^c40]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 11](../evidence/src-70224c3b9c9f/para-0011.md) · paraphrase
[^c41]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 12](../evidence/src-70224c3b9c9f/para-0012.md) · paraphrase
[^c42]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 13](../evidence/src-70224c3b9c9f/para-0013.md) · paraphrase
[^c43]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 14](../evidence/src-70224c3b9c9f/para-0014.md) · paraphrase
[^c44]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 16](../evidence/src-70224c3b9c9f/para-0016.md) · paraphrase
[^c45]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 17](../evidence/src-70224c3b9c9f/para-0017.md) · paraphrase
[^c46]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 18](../evidence/src-70224c3b9c9f/para-0018.md) · paraphrase
[^c47]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 19](../evidence/src-70224c3b9c9f/para-0019.md) · paraphrase
[^c48]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 20](../evidence/src-70224c3b9c9f/para-0020.md) · paraphrase
[^c49]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 22](../evidence/src-70224c3b9c9f/para-0022.md) · paraphrase
[^c50]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 23](../evidence/src-70224c3b9c9f/para-0023.md) · paraphrase
[^c51]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 24](../evidence/src-70224c3b9c9f/para-0024.md) · paraphrase
[^c52]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 25](../evidence/src-70224c3b9c9f/para-0025.md) · paraphrase
[^c53]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 27](../evidence/src-70224c3b9c9f/para-0027.md) · paraphrase
[^c54]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 28](../evidence/src-70224c3b9c9f/para-0028.md) · paraphrase
[^c55]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 29](../evidence/src-70224c3b9c9f/para-0029.md) · paraphrase
[^c56]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 30](../evidence/src-70224c3b9c9f/para-0030.md) · paraphrase
[^c57]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 31](../evidence/src-70224c3b9c9f/para-0031.md) · paraphrase
[^c58]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 32](../evidence/src-70224c3b9c9f/para-0032.md) · paraphrase
[^c59]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 33](../evidence/src-70224c3b9c9f/para-0033.md) · paraphrase
[^c60]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 34](../evidence/src-70224c3b9c9f/para-0034.md) · paraphrase
[^c61]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 35](../evidence/src-70224c3b9c9f/para-0035.md) · paraphrase
[^c62]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 36](../evidence/src-70224c3b9c9f/para-0036.md) · paraphrase
[^c63]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 37](../evidence/src-70224c3b9c9f/para-0037.md) · paraphrase
[^c64]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 38](../evidence/src-70224c3b9c9f/para-0038.md) · paraphrase
[^c65]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 39](../evidence/src-70224c3b9c9f/para-0039.md) · paraphrase
[^c66]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 40](../evidence/src-70224c3b9c9f/para-0040.md) · paraphrase
[^c67]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 41](../evidence/src-70224c3b9c9f/para-0041.md) · paraphrase
[^c68]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 42](../evidence/src-70224c3b9c9f/para-0042.md) · paraphrase
[^c69]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 44](../evidence/src-70224c3b9c9f/para-0044.md) · paraphrase
[^c70]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 2, row 2](../evidence/src-70224c3b9c9f/tbl-02-r0002-r0002.md) · table
