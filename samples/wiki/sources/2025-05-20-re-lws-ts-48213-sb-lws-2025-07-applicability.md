---
id: src-0df0d0598e76
type: source
title: 'Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge'
summary: This email from Litware Wind Systems technical support answers Contoso Renewables’ question about whether service bulletin SB-LWS-2025-07 Rev. A applies to Quellmoor Ridge. It states that the bulletin applies to all 12 LT-32 turbines in CCV configuration and lists conversion requirements for gearbox oil, flushing, filters, start-up temperature, and completion reporting.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- correspondence
- email
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-0df0d0598e76
source_path: full/correspondence/2025-05-20_RE-LWS-TS-48213_SB-LWS-2025-07-applicability.eml
source_hash: sha256:f89724485fab8e34de3950793b5a113f0c4189ff1065339a9b716334f7856638
media_type: message/rfc822
doc_type: email
category: correspondence
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
- component:oil-filter
- organisation:contoso-renewables
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- part:fgt-p-11872
- product:fgt-3200
- product:lt-32
- product:lt-32-ccv
- product:pwg-220
- product:pwg-320
topics:
- topic:cold-climate-operation
- topic:gearbox-lubrication
authority: 3
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 17
---

# Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This email from [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) technical support answers [Contoso Renewables](../entities/organisation/contoso-renewables.md)’ question about whether service bulletin [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A applies to [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md). It states that the bulletin applies to all 12 [LT-32](../entities/product/lt-32.md) turbines in CCV configuration and lists conversion requirements for [gearbox](../entities/component/gearbox.md) oil, flushing, filters, start-up temperature, and completion reporting.

## Key facts

- The email body is marked “FICTIONAL - NOT FOR OPERATIONAL USE.”[^c1]
- The email was sent on 20 May 2025 with the subject “RE: [LWS-TS-48213] Applicability of [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) to [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).”[^c2]
- [Litware](../entities/organisation/litware-wind-systems.md)’s response addresses a 29 April 2025 question about SB-LWS-2025-07 Rev. A, described as covering [gearbox](../entities/component/gearbox.md) oil viscosity grade for CCV turbines.[^c3]
- The configuration records checked for Quellmoor Ridge Wind Farm showed that all 12 turbines, [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md), were delivered as [LT-32](../entities/product/lt-32.md) in CCV configuration with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes, so SB-LWS-2025-07 applies to all 12 turbines.[^c4]
- For the conversion, the oil is to be changed from [Proseware PWG 320](../entities/product/pwg-320.md) to [Proseware PWG 220](../entities/product/pwg-220.md) at the next scheduled oil change, and no later than 31 December 2025.[^c5]
- Each gearbox is to be flushed with 60 L of PWG 220 before the final fill of 410 L.[^c6]
- The [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) is to be replaced during the conversion.[^c6]
- The minimum oil sump temperature for start-up is to be set to +5 degrees C using controller parameter GBX_TMIN_START.[^c6]
- The completion form in annex B of the bulletin is to be returned within 30 days of each conversion.[^c6]
- Conversions made according to the bulletin keep the gearbox warranty valid.[^c7]
- Residual PWG 320 above 5 % after flushing is not permitted.[^c7]
- The original requester stated that [Contoso](../entities/organisation/contoso-renewables.md) operates 12 LT-32 turbines at Quellmoor Ridge and reported that on 21 January two turbines needed more than 6 hours of heating before start-up at -24.6 degrees C.[^c8]
- The original requester asked whether SB-LWS-2025-07 applies to all Quellmoor Ridge turbines and whether the conversion could be done during the autumn maintenance campaign.[^c9]

## Contents

### Email context

The message is an email reply dated 20 May 2025 about the applicability of [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) to [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c10]

The sender is Henrik Saltvedt, and the message is addressed to Dario Penwarden with Yusuf Arkwell copied.[^c10]

The body contains a “FICTIONAL - NOT FOR OPERATIONAL USE” banner at both the beginning and the end of the email chain.[^c11][^c12]

### Litware response on applicability

Henrik Saltvedt thanks Dario for the 29 April 2025 question about [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) Rev. A, described as the service bulletin for [gearbox](../entities/component/gearbox.md) oil viscosity grade for CCV turbines.[^c13]

Henrik states that he checked the configuration records of [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c14]

The records show that all 12 turbines, [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), were delivered as [LT-32](../entities/product/lt-32.md) in CCV configuration with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes.[^c4]

On that basis, the email states that SB-LWS-2025-07 applies to all 12 turbines.[^c4]

### Conversion points

For the conversion, the email lists these required points:[^c15]

- Change from [Proseware PWG 320](../entities/product/pwg-320.md) to [Proseware PWG 220](../entities/product/pwg-220.md) at the next scheduled oil change, and no later than 31 December 2025.[^c5]
- Flush each [gearbox](../entities/component/gearbox.md) with 60 L of PWG 220 before the final fill of 410 L.[^c5]
- Replace [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) during the conversion.[^c5]
- Set the minimum oil sump temperature for start-up to +5 degrees C using controller parameter GBX_TMIN_START.[^c5]
- Return the completion form from annex B of the bulletin within 30 days of each conversion.[^c5]

### Warranty and residual oil condition

The email states that conversions made according to the bulletin keep the [gearbox](../entities/component/gearbox.md) warranty valid.[^c16]

It also states that residual [PWG 320](../entities/product/pwg-320.md) above 5 % after flushing is not permitted.[^c16]

### Original request

The original email came from Dario Penwarden of [Contoso Renewables](../entities/organisation/contoso-renewables.md), O&M Supervisor, and asked [Litware](../entities/organisation/litware-wind-systems.md) technical support about ticket LWS-TS-48213 and the applicability of [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md) to [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c17][^c18]

Dario stated that Contoso operates 12 [LT-32](../entities/product/lt-32.md) turbines at Quellmoor Ridge.[^c8]

He reported that on 21 January two turbines needed more than 6 hours of heating before start-up at -24.6 degrees C.[^c8]

He asked whether SB-LWS-2025-07 applies to all of the turbines and whether the conversion could be done during the autumn maintenance campaign.[^c8]

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [oil filter element](../entities/component/oil-filter.md)
- Spare part: [FGT-P-11872](../entities/part/fgt-p-11872.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Cold-climate operation and icing](../topics/cold-climate-operation.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
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

[^c1]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, line 1](../evidence/src-0df0d0598e76/msg-body-l0001-l0001.md) · ✓ quote verified
[^c2]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message headers](../evidence/src-0df0d0598e76/msg-headers.md) · ✓ quote verified
[^c3]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 5–6](../evidence/src-0df0d0598e76/msg-body-l0005-l0006.md) · ✓ quote verified
[^c4]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 10–12](../evidence/src-0df0d0598e76/msg-body-l0010-l0012.md) · paraphrase
[^c5]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 16–23](../evidence/src-0df0d0598e76/msg-body-l0016-l0023.md) · paraphrase
[^c6]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 16–23](../evidence/src-0df0d0598e76/msg-body-l0016-l0023.md) · ✓ quote verified
[^c7]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 25–26](../evidence/src-0df0d0598e76/msg-body-l0025-l0026.md) · ✓ quote verified
[^c8]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 48–51](../evidence/src-0df0d0598e76/msg-body-l0048-l0051.md) · paraphrase
[^c9]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 48–51](../evidence/src-0df0d0598e76/msg-body-l0048-l0051.md) · ✓ quote verified
[^c10]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message headers](../evidence/src-0df0d0598e76/msg-headers.md) · paraphrase
[^c11]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, line 1](../evidence/src-0df0d0598e76/msg-body-l0001-l0001.md) · paraphrase
[^c12]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, line 57](../evidence/src-0df0d0598e76/msg-body-l0057-l0057.md) · paraphrase
[^c13]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 5–6](../evidence/src-0df0d0598e76/msg-body-l0005-l0006.md) · paraphrase
[^c14]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, line 8](../evidence/src-0df0d0598e76/msg-body-l0008-l0008.md) · paraphrase
[^c15]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, line 14](../evidence/src-0df0d0598e76/msg-body-l0014-l0014.md) · paraphrase
[^c16]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 25–26](../evidence/src-0df0d0598e76/msg-body-l0025-l0026.md) · paraphrase
[^c17]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 40–44](../evidence/src-0df0d0598e76/msg-body-l0040-l0044.md) · paraphrase
[^c18]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 53–55](../evidence/src-0df0d0598e76/msg-body-l0053-l0055.md) · paraphrase
