---
id: component:oil-filter
type: entity
title: oil filter element
summary: The oil filter element is a component identified by part number FGT-P-11872. It is used in gearbox oil change and oil filter element replacement tasks, including the scheduled MP-GBX-02 task every 12 months. It is replaced during the LT-32 CCV turbine conversion and in response to gearbox oil…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- component
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: component
key: oil-filter
aliases:
- text: oil filter element
  lang: en
- text: élément filtrant d'huile
  lang: fr
- text: Ölfilterelement
  lang: de
sources:
- src-0df0d0598e76
- src-1abc5aef1a40
- src-1c261d5b87b5
- src-36f5b999211a
- src-42566abae6ef
- src-70224c3b9c9f
- src-90ea27f71f0f
- src-990a047180b7
- src-9fd435ef5956
- src-aba30cb7207f
- src-c4370c220559
- src-ecc004b57dd5
---

# oil filter element

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

The oil filter element is a component identified by part number [FGT-P-11872](../part/fgt-p-11872.md).[^c1][^c2][^c3] It is used in [gearbox](gearbox.md) oil change and oil filter element replacement tasks, including the scheduled MP-GBX-02 task every 12 months.[^c2][^c3][^c4] It is replaced during the [LT-32 CCV](../product/lt-32-ccv.md) turbine conversion and in response to [gearbox oil filter differential pressure high](../alarm-code/a2140.md) alarm A2140.[^c5][^c6][^c7]

## Facts

- The oil filter element [FGT-P-11872](../part/fgt-p-11872.md) must be replaced during the conversion.[^c5]
- Per turbine, parts and labour include 470 L of [Proseware PWG 220](../product/pwg-220.md), one FGT-P-11872 oil filter element, one PWG 220 label kit, and labour by 2 technicians for about 6 hours.[^c1]
- Alarm [A2140](../alarm-code/a2140.md), Gearbox oil filter differential pressure high at 2.5 bar, can be caused by a clogged filter element or cold oil; the action is to replace filter element FGT-P-11872.[^c6]
- One oil filter element FGT-P-11872 is required.[^c2][^c3]
- [Gearbox](gearbox.md) oil filter element replacement task MP-GBX-02 uses part FGT-P-11872, is scheduled every 12 months, and references [SOP-GBX-010](../procedure/sop-gbx-010.md).[^c4]
- [WTG-12](../asset/wtg-12.md) raised A2140 Gearbox oil filter differential pressure high at 2.56 bar on 2026-08-02 and cleared it at 1.90 bar later the same day.[^c8][^c9]
- [WTG-04](../asset/wtg-04.md) raised A2140 Gearbox oil filter differential pressure high at 2.89 bar on 2026-08-11 17:18:08 and cleared it at 1.90 bar on 2026-08-11 18:22:08.[^c10][^c11]
- [WTG-06](../asset/wtg-06.md) had A2140 Gearbox oil filter differential pressure high raised at 2.89 bar and cleared at 1.90 bar on 2026-08-31.[^c12][^c13]
- The oil filter element FGT-P-11872 is to be replaced during the conversion.[^c7]
- After switching from [PWG 320](../product/pwg-320.md) to PWG 220, oil filter element FGT-P-11872 is to be changed a second time after 500 operating hours because loosened deposits collect in the filter.[^c14]
- At the same time as the second oil filter element change, the supplier recommends an oil sample.[^c14]

## Timeline

- 2026-08-02: [WTG-12](../asset/wtg-12.md) raised [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md) at 2.56 bar on 2026-08-02 and cleared it at 1.90 bar later the same day.[^c8][^c9]
- 2026-08-11: [WTG-04](../asset/wtg-04.md) raised A2140 Gearbox oil filter differential pressure high at 2.89 bar on 2026-08-11 17:18:08 and cleared it at 1.90 bar on 2026-08-11 18:22:08.[^c10][^c11]
- 2026-08-31: [WTG-06](../asset/wtg-06.md) had A2140 Gearbox oil filter differential pressure high raised at 2.89 bar and cleared at 1.90 bar on 2026-08-31.[^c12][^c13]

## Documents

- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md) (superseded)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [FGT-P-11872](../part/fgt-p-11872.md)
- [gearbox](gearbox.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [Proseware Lubricants](../organisation/proseware-lubricants.md)
- [Proseware PWG 220](../product/pwg-220.md)
- [Proseware PWG 320](../product/pwg-320.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Gearbox oil change](../procedure/sop-gbx-010.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 2](../../evidence/src-c4370c220559/p0002.md) · ✓ quote verified
[^c2]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 23](../../evidence/src-70224c3b9c9f/para-0023.md) · ✓ quote verified
[^c3]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 20](../../evidence/src-90ea27f71f0f/para-0020.md) · ✓ quote verified
[^c4]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 3](../../evidence/src-aba30cb7207f/sheet-tasks-r0003-r0003.md) · table
[^c5]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 1](../../evidence/src-c4370c220559/p0001.md) · ✓ quote verified
[^c6]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../../evidence/src-1c261d5b87b5/p0005.md) · ✓ quote verified
[^c7]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 16–23](../../evidence/src-0df0d0598e76/msg-body-l0016-l0023.md) · ✓ quote verified
[^c8]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1436](../../evidence/src-36f5b999211a/r1436-r1436.md) · table
[^c9]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1485](../../evidence/src-36f5b999211a/r1485-r1485.md) · table
[^c10]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1654](../../evidence/src-36f5b999211a/r1654-r1654.md) · table
[^c11]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1655](../../evidence/src-36f5b999211a/r1655-r1655.md) · table
[^c12]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1896](../../evidence/src-36f5b999211a/r1896-r1896.md) · table
[^c13]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1897](../../evidence/src-36f5b999211a/r1897-r1897.md) · table
[^c14]: [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up — lines 13–15](../../evidence/src-1abc5aef1a40/l0013-l0015.md) · ✓ quote verified
