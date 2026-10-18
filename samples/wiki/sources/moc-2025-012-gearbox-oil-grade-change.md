---
id: src-a20331a5431f
type: source
title: MOC-2025-012 - Gearbox Oil Grade Change to PWG 220
summary: This approved management-of-change record covers replacing PWG 320 gearbox oil with PWG 220 in all 12 Quellmoor Ridge turbines. It records the reason, risk controls, implementation actions, estimated cost, and approval for the lubricant change.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- change-management
- moc-record
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-a20331a5431f
source_path: full/change/MOC-2025-012_gearbox-oil-grade-change.docx
source_hash: sha256:ebe7402257c6148a640c320e35e08ce21d21174400ed139e930410368803ceca
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: moc-record
category: change-management
doc_number: null
revision: A
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
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
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- part:pws-220-d208
- procedure:sop-gbx-010
- product:pwg-220
- product:pwg-320
topics:
- topic:cold-climate-operation
- topic:environmental-compliance
- topic:gearbox-lubrication
- topic:spare-parts-and-supply
- topic:training-and-onboarding
authority: 8
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 12
    deterministic-table: 17
---

# MOC-2025-012 - Gearbox Oil Grade Change to PWG 220

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This approved management-of-change record covers replacing [PWG 320](../entities/product/pwg-320.md) [gearbox](../entities/component/gearbox.md) oil with [PWG 220](../entities/product/pwg-220.md) in all 12 [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) turbines. It records the reason, risk controls, implementation actions, estimated cost, and approval for the lubricant change.

## Key facts

- The management-of-change record MOC-2025-012 was approved on 2025-06-18.[^c1][^c2]
- The change was raised on 2025-05-06 by Dario Penwarden, O&M Supervisor, and is a technical lubricant change scoped to [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md).[^c3][^c4][^c5]
- The record was reviewed by Greta Vollan, HSE Coordinator, and Yusuf Arkwell, Reliability Engineer.[^c6]
- The decision was approved on 2025-06-18 by Maren Ellingsby, Site Manager.[^c7]
- The change replaces [Proseware PWG 320](../entities/product/pwg-320.md) (ISO VG 320) with [Proseware PWG 220](../entities/product/pwg-220.md) (ISO VG 220) in the gearboxes of all 12 turbines, as required by [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A.[^c8]
- [Litware](../entities/organisation/litware-wind-systems.md) support confirmed on 2025-05-20 under ticket LWS-TS-48213 that SB-LWS-2025-07 applies to all 12 CCV turbines of [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c8]
- On 2025-01-21 at -24.6 °C, [WTG-02](../entities/asset/wtg-02.md) and [WTG-09](../entities/asset/wtg-09.md) needed more than 6 hours of heating before starting.[^c9]
- The bulletin makes the oil-grade change a condition of the [gearbox](../entities/component/gearbox.md) warranty.[^c9]
- For the oil-mixing hazard, the identified risk is residual PWG 320 above 5 %, controlled by a 60 L flush, labelling the filler, and removing PWG 320 drums from the shelf.[^c10]
- For the cold-start hazard, the control is to set GBX_TMIN_START to 5 °C and verify it in the conversion checklist.[^c11]
- For the hot-oil and spill hazard, controls include [SOP-GBX-010](../entities/procedure/sop-gbx-010.md), a spill kit, and draining between 40 and 60 °C.[^c12]
- The availability risk is about 6 hours downtime per turbine, controlled by planning the campaign in low-wind periods.[^c13]
- The waste-oil risk is 12 x 470 L of waste oil, controlled by using a licensed carrier and checking bund capacity.[^c14]
- Action 1 is to revise SOP-GBX-010 to Rev. B, owned by Dario Penwarden and due 2025-08-29.[^c15]
- Action 2 is to order 36 drums of PWG 220 and set the minimum stock of [PWS-220-D208](../entities/part/pws-220-d208.md) to 8 drums, owned by Tomasz Lebrecht and due 2025-08-15.[^c16]
- Action 3 is the conversion campaign for WTG-01 to WTG-12, owned by Dario Penwarden and due from 2025-09-01 to 2025-11-28.[^c17]
- Action 4 is a toolbox talk on cold-weather start-up with the new oil, owned by Dario Penwarden and due 2025-11-30.[^c18]
- Action 5 is to update the maintenance plan and oil sampling schedule, owned by Yusuf Arkwell and due 2025-12-15.[^c19]
- Action 6 is to send the Litware completion form within 30 days of each conversion, owned by Dario Penwarden and due per conversion.[^c20]
- The estimated cost is EUR 58,600 for 36 drums of PWG 220, 12 filter elements, labour, and waste-oil disposal, within the 2025 maintenance budget.[^c21]
- Implementation is reported at the monthly O&M review.[^c22]

## Contents

### Record summary

The document is titled “MOC-2025-012 - [Gearbox](../entities/component/gearbox.md) oil grade change to [PWG 220](../entities/product/pwg-220.md).”[^c23]

It is a management-of-change record approved on 2025-06-18.[^c24]

The MOC number is MOC-2025-012; it was raised on 2025-05-06 by Dario Penwarden, O&M Supervisor; its type is a technical lubricant change; and its scope is [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md).[^c2][^c3][^c4][^c5]

The record was reviewed by Greta Vollan, HSE Coordinator, and Yusuf Arkwell, Reliability Engineer.[^c6]

The decision was approved on 2025-06-18 by Maren Ellingsby, Site Manager.[^c7]

**Table t01** · table 1, rows 1–7

| Row | Field | Value |
| --- | --- | --- |
| 2 | MOC number | MOC-2025-012 |
| 3 | Raised | 2025-05-06 by Dario Penwarden, O&M Supervisor |
| 4 | Type | Technical change - lubricant |
| 5 | Scope | WTG-01 to WTG-12 |
| 6 | Reviewed by | Greta Vollan (HSE Coordinator), Yusuf Arkwell (Reliability Engineer) |
| 7 | Decision | Approved on 2025-06-18 by Maren Ellingsby, Site Manager |

Agents can query this table as `t01` with the `query_table` tool.

### Description of the change

The change replaces [Proseware PWG 320](../entities/product/pwg-320.md) (ISO VG 320) with [Proseware PWG 220](../entities/product/pwg-220.md) (ISO VG 220) in the gearboxes of all 12 turbines.[^c25]

The change is required by service bulletin [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A.[^c25]

[Litware](../entities/organisation/litware-wind-systems.md) support confirmed on 2025-05-20, under ticket LWS-TS-48213, that the bulletin applies to all 12 CCV turbines of [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c25]

### Reason

On 2025-01-21, at -24.6 °C, [WTG-02](../entities/asset/wtg-02.md) and [WTG-09](../entities/asset/wtg-09.md) needed more than 6 hours of heating before they could start.[^c26]

The bulletin also makes the change a condition of the [gearbox](../entities/component/gearbox.md) warranty.[^c26]

### Risk assessment

The risk assessment identifies hazards for mixing of oils, cold start, hot oil and spills, availability, and waste oil.[^c10][^c11][^c12][^c13][^c14]

For mixing of oils, the risk is residual [PWG 320](../entities/product/pwg-320.md) above 5 %, and the controls are a 60 L flush, labelling the filler, and removing PWG 320 drums from the shelf.[^c10]

For cold start, the risk is a wrong start parameter, and the control is to set GBX_TMIN_START to 5 °C and verify it in the conversion checklist.[^c11]

For hot oil and spills, the risks are burns and environmental spill, and the controls are [SOP-GBX-010](../entities/procedure/sop-gbx-010.md), a spill kit, and draining between 40 and 60 °C.[^c12]

For availability, the risk is about 6 hours downtime per turbine, and the control is to plan the campaign in low-wind periods.[^c13]

For waste oil, the risk is 12 x 470 L of waste oil, and the controls are a licensed carrier and checking bund capacity.[^c14]

**Table t02** · table 2, rows 1–6

| Row | Hazard | Risk | Control |
| --- | --- | --- | --- |
| 2 | Mixing of oils | Residual PWG 320 above 5 % | 60 L flush; label the filler; remove PWG 320 drums from the shelf |
| 3 | Cold start | Wrong start parameter | Set GBX_TMIN_START to 5 °C and verify it in the conversion checklist |
| 4 | Hot oil and spills | Burns, environmental spill | SOP-GBX-010; spill kit; drain between 40 and 60 °C |
| 5 | Availability | About 6 hours downtime per turbine | Plan the campaign in low-wind periods |
| 6 | Waste oil | 12 x 470 L of waste oil | Licensed carrier; check the bund capacity |

Agents can query this table as `t02` with the `query_table` tool.

### Actions

The action plan assigns six actions covering SOP revision, oil ordering and minimum stock, the conversion campaign, toolbox talk, maintenance-plan and oil-sampling updates, and completion-form submission.[^c15][^c16][^c17][^c18][^c19][^c20]

Action 1 is to revise [SOP-GBX-010](../entities/procedure/sop-gbx-010.md) to Rev. B, owned by Dario Penwarden and due 2025-08-29.[^c15]

Action 2 is to order 36 drums of [PWG 220](../entities/product/pwg-220.md) and set the minimum stock of [PWS-220-D208](../entities/part/pws-220-d208.md) to 8 drums, owned by Tomasz Lebrecht and due 2025-08-15.[^c16]

Action 3 is the conversion campaign for [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), owned by Dario Penwarden and due from 2025-09-01 to 2025-11-28.[^c17]

Action 4 is a toolbox talk on cold-weather start-up with the new oil, owned by Dario Penwarden and due 2025-11-30.[^c18]

Action 5 is to update the maintenance plan and the oil sampling schedule, owned by Yusuf Arkwell and due 2025-12-15.[^c19]

Action 6 is to send the [Litware](../entities/organisation/litware-wind-systems.md) completion form within 30 days of each conversion, owned by Dario Penwarden and due per conversion.[^c20]

**Table t03** · table 3, rows 1–7

| Row | No. | Action | Owner | Due |
| --- | --- | --- | --- | --- |
| 2 | 1 | Revise SOP-GBX-010 to Rev. B | Dario Penwarden | 2025-08-29 |
| 3 | 2 | Order 36 drums of PWG 220 and set the minimum stock of PWS-220-D208 to 8 drums | Tomasz Lebrecht | 2025-08-15 |
| 4 | 3 | Conversion campaign WTG-01 to WTG-12 | Dario Penwarden | 2025-09-01 to 2025-11-28 |
| 5 | 4 | Toolbox talk on cold-weather start-up with the new oil | Dario Penwarden | 2025-11-30 |
| 6 | 5 | Update the maintenance plan and the oil sampling schedule | Yusuf Arkwell | 2025-12-15 |
| 7 | 6 | Send the Litware completion form within 30 days of each conversion | Dario Penwarden | per conversion |

Agents can query this table as `t03` with the `query_table` tool.

### Cost

The estimated cost is EUR 58,600 for 36 drums of [PWG 220](../entities/product/pwg-220.md), 12 filter elements, labour, and waste-oil disposal.[^c27]

The estimated cost is within the 2025 maintenance budget.[^c27]

### Approval

The change was approved by Maren Ellingsby, Site Manager, on 2025-06-18.[^c28]

Implementation is reported at the monthly O&M review.[^c28]

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Component: [gearbox](../entities/component/gearbox.md)
- Spare part: [PWS-220-D208](../entities/part/pws-220-d208.md)
- Products: [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Procedure: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Cold-climate operation and icing](../topics/cold-climate-operation.md)
- [Environmental permit and night curtailment](../topics/environmental-compliance.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)
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

[^c1]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 2](../evidence/src-a20331a5431f/para-0002.md) · ✓ quote verified
[^c2]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 2](../evidence/src-a20331a5431f/tbl-01-r0002-r0002.md) · table
[^c3]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 3](../evidence/src-a20331a5431f/tbl-01-r0003-r0003.md) · table
[^c4]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 4](../evidence/src-a20331a5431f/tbl-01-r0004-r0004.md) · table
[^c5]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 5](../evidence/src-a20331a5431f/tbl-01-r0005-r0005.md) · table
[^c6]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 6](../evidence/src-a20331a5431f/tbl-01-r0006-r0006.md) · table
[^c7]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 1, row 7](../evidence/src-a20331a5431f/tbl-01-r0007-r0007.md) · table
[^c8]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 4](../evidence/src-a20331a5431f/para-0004.md) · ✓ quote verified
[^c9]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 6](../evidence/src-a20331a5431f/para-0006.md) · ✓ quote verified
[^c10]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 2](../evidence/src-a20331a5431f/tbl-02-r0002-r0002.md) · table
[^c11]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 3](../evidence/src-a20331a5431f/tbl-02-r0003-r0003.md) · table
[^c12]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 4](../evidence/src-a20331a5431f/tbl-02-r0004-r0004.md) · table
[^c13]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 5](../evidence/src-a20331a5431f/tbl-02-r0005-r0005.md) · table
[^c14]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 2, row 6](../evidence/src-a20331a5431f/tbl-02-r0006-r0006.md) · table
[^c15]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 2](../evidence/src-a20331a5431f/tbl-03-r0002-r0002.md) · table
[^c16]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 3](../evidence/src-a20331a5431f/tbl-03-r0003-r0003.md) · table
[^c17]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 4](../evidence/src-a20331a5431f/tbl-03-r0004-r0004.md) · table
[^c18]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 5](../evidence/src-a20331a5431f/tbl-03-r0005-r0005.md) · table
[^c19]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 6](../evidence/src-a20331a5431f/tbl-03-r0006-r0006.md) · table
[^c20]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 7](../evidence/src-a20331a5431f/tbl-03-r0007-r0007.md) · table
[^c21]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 10](../evidence/src-a20331a5431f/para-0010.md) · ✓ quote verified
[^c22]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 12](../evidence/src-a20331a5431f/para-0012.md) · ✓ quote verified
[^c23]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 1](../evidence/src-a20331a5431f/para-0001.md) · paraphrase
[^c24]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 2](../evidence/src-a20331a5431f/para-0002.md) · paraphrase
[^c25]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 4](../evidence/src-a20331a5431f/para-0004.md) · paraphrase
[^c26]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 6](../evidence/src-a20331a5431f/para-0006.md) · paraphrase
[^c27]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 10](../evidence/src-a20331a5431f/para-0010.md) · paraphrase
[^c28]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 12](../evidence/src-a20331a5431f/para-0012.md) · paraphrase
