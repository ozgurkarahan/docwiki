---
id: src-c4370c220559
type: source
title: SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines
summary: This Litware Wind Systems service bulletin changes the gearbox oil specification for affected LT-32 cold-climate turbines. It covers applicability, compliance timing, oil conversion instructions, parts and labour, and completion reporting.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- oem-documentation
- service-bulletin
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-c4370c220559
source_path: full/oem/SB-LWS-2025-07_RevA_gearbox-oil-cold-climate.pdf
source_hash: sha256:5450be16452af702cbaef92203a2cf5dfba5200c2889832259b62988cfe36fd3
media_type: application/pdf
doc_type: service-bulletin
category: oem-documentation
doc_number: SB-LWS-2025-07
revision: A
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: 2
entities:
- alarm-code:a2101
- alarm-code:a2102
- bulletin:sb-lws-2025-07
- component:gearbox
- component:oil-filter
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- part:fgt-p-11872
- procedure:sop-loto-001
- product:fgt-3200
- product:lt-32
- product:lt-32-ccv
- product:pwg-220
- product:pwg-320
topics:
- topic:cold-climate-operation
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
authority: 9
extraction:
  adapter: content-understanding
  version: 1.0.0+cu.2025-11-01
  provenance_mix:
    native-text: 52
---

# SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) service bulletin changes the [gearbox](../entities/component/gearbox.md) oil specification for affected [LT-32](../entities/product/lt-32.md) cold-climate turbines. It covers applicability, compliance timing, oil conversion instructions, parts and labour, and completion reporting.

## Key facts

- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) issued the service bulletin on 2025-03-14.[^c1]
- The bulletin is categorized as recommended, but mandatory to keep the [gearbox](../entities/component/gearbox.md) warranty.[^c1]
- The bulletin applies to [LT-32](../entities/product/lt-32.md) turbines delivered in CCV configuration with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes and to LT-32 standard turbines at sites where ambient temperature regularly falls below -20 °C.[^c1]
- The affected document is LWS-MM-GBX-32 Rev. D, section 4.2 on lubrication.[^c1]
- Compliance is required at the next scheduled oil change and no later than 2025-12-31.[^c1]
- The reason for the change is that cold-site reports showed start-up heating times of more than 6 hours at -25 °C ambient and filter bypass events with ISO VG 320 oil.[^c1]
- For affected turbines, the gear oil changes from [Proseware PWG 320](../entities/product/pwg-320.md) to [Proseware PWG 220](../entities/product/pwg-220.md).[^c1]
- For affected turbines, the viscosity grade changes from ISO VG 320 to ISO VG 220.[^c1]
- The total oil volume remains 410 L.[^c1]
- The minimum oil sump temperature before start-up changes from +10 °C to +5 °C.[^c1]
- Warning [A2101](../entities/alarm-code/a2101.md) and trip [A2102](../entities/alarm-code/a2102.md) temperature thresholds remain 75 °C and 82 °C.[^c1]
- The conversion instructions say to stop the turbine and isolate the drivetrain according to the site lockout procedure.[^c1]
- PWG 320 must be drained at an oil temperature between 40 and 60 °C.[^c1]
- The [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) must be replaced during the conversion.[^c1]
- The gearbox must be flushed with 60 L of PWG 220, the electric oil pump run for 30 minutes, and the flush oil then drained.[^c1]
- The gearbox must be filled with 410 L of PWG 220 through a filter cart with a 10 micron element.[^c1]
- After flushing, residual PWG 320 must not exceed 5 % of total oil volume.[^c1]
- The controller parameter GBX_TMIN_START must be changed from 10 to 5 °C.[^c1]
- The gearbox filler must be labelled 'PWG 220' using the supplied label kit.[^c1]
- A reference oil sample must be taken after 24 hours of operation.[^c1]
- Per turbine, parts and labour include 470 L of Proseware PWG 220, one FGT-P-11872 oil filter element, one PWG 220 label kit, and labour by 2 technicians for about 6 hours.[^c2]
- The completion form in annex B must be returned to Litware Wind Systems within 30 days of each conversion.[^c2]
- Conversions performed according to the bulletin keep the gearbox warranty valid.[^c2]

## Contents

### Bulletin identification and applicability

[Litware Wind Systems](../entities/organisation/litware-wind-systems.md) issued this service bulletin on 2025-03-14.[^c3]

The bulletin number is [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) and the revision is A.[^c3]

The category is recommended, but the bulletin is mandatory to keep the [gearbox](../entities/component/gearbox.md) warranty.[^c3]

The bulletin applies to [LT-32](../entities/product/lt-32.md) turbines delivered in CCV configuration with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes and to LT-32 standard turbines at sites where ambient temperature regularly falls below -20 °C.[^c3]

The affected document is LWS-MM-GBX-32 Rev. D, section 4.2 on lubrication.[^c3] Compliance is required at the next scheduled oil change and no later than 2025-12-31.[^c3]

**Table t01** · p. 1

| Row | Field | Value |
| --- | --- | --- |
| 2 | Bulletin number | SB-LWS-2025-07 |
| 3 | Revision | A |
| 4 | Issue date | 2025-03-14 |
| 5 | Category | Recommended; mandatory to keep the gearbox warranty |
| 6 | Applies to | LT-32 turbines delivered in CCV configuration with Fabrikam FGT-3200 gearboxes (all serial numbers), and LT-32 standard turbines at sites where the ambient temperature regularly falls below -20 °C |
| 7 | Affected document | LWS-MM-GBX-32 Rev. D, section 4.2 (lubrication) |
| 8 | Compliance | At the next scheduled oil change and no later than 2025-12-31 |

Agents can query this table as `t01` with the `query_table` tool.

### Reason

Cold-site field reports showed start-up heating times of more than 6 hours at -25 °C ambient and filter bypass events with ISO VG 320 oil.[^c3]

The bulletin states that a lower viscosity grade shortens start-up time and keeps the filter element in service.[^c3]

### Change

The bulletin amends the lubricant specification in section 4.2 of LWS-MM-GBX-32 Rev. D for the turbines listed under the applicability statement.[^c3]

The gear oil changes from [Proseware PWG 320](../entities/product/pwg-320.md) to [Proseware PWG 220](../entities/product/pwg-220.md).[^c3] The viscosity grade changes from ISO VG 320 to ISO VG 220.[^c3]

The total oil volume remains 410 L.[^c3] The minimum oil sump temperature before start-up changes from +10 °C to +5 °C.[^c3] Warning [A2101](../entities/alarm-code/a2101.md) and trip [A2102](../entities/alarm-code/a2102.md) remain at 75 °C and 82 °C.[^c3]

**Table t02** · p. 1

| Row | Item | LWS-MM-GBX-32 Rev. D | After this bulletin |
| --- | --- | --- | --- |
| 2 | Gear oil | Proseware PWG 320 | Proseware PWG 220 |
| 3 | Viscosity grade | ISO VG 320 | ISO VG 220 |
| 4 | Total oil volume | 410 L | 410 L (unchanged) |
| 5 | Minimum oil sump temperature before start-up | +10 °C | +5 °C |
| 6 | Warning A2101 / trip A2102 | 75 °C / 82 °C | 75 °C / 82 °C (unchanged) |

Agents can query this table as `t02` with the `query_table` tool.

### Instructions

- Stop the turbine and isolate the drivetrain according to the site lockout procedure.[^c3]
- Drain [PWG 320](../entities/product/pwg-320.md) at an oil temperature between 40 and 60 °C.[^c3]
- Replace the [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md).[^c3]
- Flush the [gearbox](../entities/component/gearbox.md) with 60 L of [PWG 220](../entities/product/pwg-220.md) by filling, [running](../entities/status-code/s100.md) the electric oil pump for 30 minutes, and draining.[^c3]
- Fill with 410 L of PWG 220 through a filter cart with a 10 micron element.[^c3]
- Keep residual PWG 320 after flushing at no more than 5 % of total oil volume.[^c3]
- Change controller parameter GBX_TMIN_START from 10 to 5 °C.[^c3]
- Label the gearbox filler 'PWG 220' with the supplied label kit.[^c3]
- Take a reference oil sample after 24 hours of operation.[^c3]

### Parts and labour

The parts and labour table gives per-turbine quantities for [Proseware PWG 220](../entities/product/pwg-220.md), [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md), the PWG 220 label kit, and labour.[^c4]

**Table t03** · p. 2

| Row | Item | Quantity per turbine |
| --- | --- | --- |
| 2 | Proseware PWG 220 (60 L flush + 410 L fill) | 470 L |
| 3 | Oil filter element FGT-P-11872 | 1 |
| 4 | Label kit 'PWG 220' | 1 |
| 5 | Labour | 2 technicians, about 6 hours |

Agents can query this table as `t03` with the `query_table` tool.

### Reporting and completion form

The completion form in annex B must be returned to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) within 30 days of each conversion.[^c4]

The bulletin states that conversions made according to it keep the [gearbox](../entities/component/gearbox.md) warranty valid.[^c4]

The completion form records the turbine serial number, gearbox serial number, conversion date, [PWG 220](../entities/product/pwg-220.md) batch number, estimated residual [PWG 320](../entities/product/pwg-320.md) percentage, and technician name and signature.[^c4]

**Table t04** · p. 2

| Row | Field | Entry |
| --- | --- | --- |
| 2 | Turbine serial number |  |
| 3 | Gearbox serial number |  |
| 4 | Conversion date |  |
| 5 | PWG 220 batch number |  |
| 6 | Estimated residual PWG 320 (%) |  |
| 7 | Technician name and signature |  |

Agents can query this table as `t04` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Components: [gearbox](../entities/component/gearbox.md), [oil filter element](../entities/component/oil-filter.md)
- Spare part: [FGT-P-11872](../entities/part/fgt-p-11872.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- Procedure: [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
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
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 1](../evidence/src-c4370c220559/p0001.md) · ✓ quote verified
[^c2]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 2](../evidence/src-c4370c220559/p0002.md) · ✓ quote verified
[^c3]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 1](../evidence/src-c4370c220559/p0001.md) · paraphrase
[^c4]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 2](../evidence/src-c4370c220559/p0002.md) · paraphrase
