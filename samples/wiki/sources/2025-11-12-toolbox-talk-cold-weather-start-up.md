---
id: src-ecc004b57dd5
type: source
title: 'Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion'
summary: This is a transcript of a toolbox talk on cold-weather turbine start-up after gearbox oil conversion to PWG 220. It covers conversion status, start-up temperature thresholds, cold-start alarms, ice and personnel safety, service lift issues, and post-conversion oil handling.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- meeting-transcript
- meetings
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-ecc004b57dd5
source_path: full/meetings/2025-11-12_toolbox-talk-cold-weather-start-up.vtt
source_hash: sha256:45c24c95ee75aa6fa2935ecb61e4f06ebaf0d73b2c7cb6ee97d629772ed6c70d
media_type: text/vtt
doc_type: meeting-transcript
category: meetings
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- alarm-code:a2120
- alarm-code:a2140
- alarm-code:a7001
- asset:wtg-02
- asset:wtg-05
- asset:wtg-06
- asset:wtg-09
- asset:wtg-11
- asset:wtg-12
- component:gearbox
- component:gearbox-heater
- component:oil-filter
- component:rotor-blade
- component:service-lift
- organisation:litware-wind-systems
- product:pwg-220
- product:pwg-320
topics:
- topic:cold-climate-operation
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:training-and-onboarding
authority: 2
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 24
---

# Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This is a transcript of a toolbox talk on cold-weather turbine start-up after [gearbox](../entities/component/gearbox.md) oil conversion to [PWG 220](../entities/product/pwg-220.md). It covers conversion status, start-up temperature thresholds, cold-start alarms, ice and personnel safety, [service lift](../entities/component/service-lift.md) issues, and post-conversion oil handling.

## Key facts

- The transcript is marked as fictional and not for operational use.[^c1][^c2]
- The toolbox talk is about cold-weather start-up now that most gearboxes run on the new oil.[^c3]
- [PWG 220](../entities/product/pwg-220.md) conversion status was: nine turbines completed, [WTG-11](../entities/asset/wtg-11.md) being converted that day, [WTG-12](../entities/asset/wtg-12.md) scheduled for the following Wednesday, and [WTG-09](../entities/asset/wtg-09.md) planned for the twenty-fourth if the access road remained open.[^c4][^c5]
- With PWG 220, the minimum oil temperature for start-up is plus five degrees; with the old [PWG 320](../entities/product/pwg-320.md), it was plus ten.[^c6]
- From minus twenty, heaters need about four hours to bring the sump to plus five; the previous January, [WTG-02](../entities/asset/wtg-02.md) and WTG-09 needed more than six hours.[^c7]
- The start inhibit must not be bypassed because the controller waits for the oil temperature for a reason.[^c8]
- If WTG-09 still has PWG 320 in January, its start temperature remains plus ten until conversion is complete; the parameter is changed only with the new oil.[^c9]
- For [A2120 gearbox oil pressure low](../entities/alarm-code/a2120.md) immediately after a cold start, technicians should give the heaters more time before escalating, because it is usually cold oil rather than a pump fault.[^c10]
- For [A2140](../entities/alarm-code/a2140.md) filter alarm in cold conditions, thick oil can cause a high pressure drop across the filter; wait for the oil to warm up and then check again.[^c11][^c12]
- When [A7001](../entities/alarm-code/a7001.md) ice detection is active, the turbine stops by itself.[^c13]
- Personnel must keep at least 300 metres away from a turbine with ice on the blades, and there must be no climbing until the ice has gone.[^c14]
- Cold-weather personal precautions include wearing layers, taking spare gloves and hand warmers, and doing a buddy check every thirty minutes.[^c15]
- Ladder rungs can be frozen at the tower base; the [service lift](../entities/component/service-lift.md) should be used when it works, and the lift battery should be checked on cold mornings.[^c16]
- The service lift on [WTG-06](../entities/asset/wtg-06.md) stopped twice the previous winter because of cold, and such events should be reported every time for follow-up with [Litware](../entities/organisation/litware-wind-systems.md).[^c17][^c18]
- After conversion, a [gearbox](../entities/component/gearbox.md) must never be topped up with PWG 320; old PWG 320 drums are marked do not use.[^c19]
- One drum of PWG 320 remained in the store and was to stay there until the waste carrier collected it; it was not to be used.[^c20][^c21]
- Attendees were asked to sign the attendance sheet before leaving.[^c22]

## Contents

### Opening and conversion status

- The transcript is marked fictional and not for operational use.[^c23]
- The toolbox talk was about cold-weather start-up now that most gearboxes run on the new oil.[^c24]
- [PWG 220](../entities/product/pwg-220.md) conversion status was nine turbines completed, [WTG-11](../entities/asset/wtg-11.md) being converted that day, [WTG-12](../entities/asset/wtg-12.md) scheduled for the following Wednesday, and [WTG-09](../entities/asset/wtg-09.md) planned for the twenty-fourth if the access road stayed open.[^c25][^c26]

### Cold-weather start-up thresholds and alarms

- With [PWG 220](../entities/product/pwg-220.md), the minimum oil temperature for start-up is plus five degrees; with old [PWG 320](../entities/product/pwg-320.md), it was plus ten.[^c27]
- From minus twenty, heaters need about four hours to bring the sump to plus five, while [WTG-02](../entities/asset/wtg-02.md) and [WTG-09](../entities/asset/wtg-09.md) needed more than six hours the previous January.[^c28]
- The start inhibit must not be bypassed because the controller waits for the oil temperature.[^c29]
- If WTG-09 still has PWG 320 in January, its start temperature remains plus ten until the conversion is done, and the parameter is changed only with the new oil.[^c30][^c31]
- For [A2120 gearbox oil pressure low](../entities/alarm-code/a2120.md) right after a cold start, the talk advises giving the heaters more time before escalating because it is usually cold oil rather than a pump fault.[^c32]
- For [A2140](../entities/alarm-code/a2140.md) filter alarm, thick oil can cause a high pressure drop across the filter; wait for the oil to warm up and then check again.[^c33][^c34]

### Ice, cold exposure, and access safety

- When [A7001](../entities/alarm-code/a7001.md) ice detection is active, the turbine stops by itself.[^c35]
- Personnel should keep at least 300 metres away from a turbine with ice on the blades, and climbing is not allowed until the ice has gone.[^c36]
- Cold-weather personal precautions include wearing layers, taking spare gloves and hand warmers, and doing a buddy check every thirty minutes.[^c37]
- Ladder rungs can be frozen at the tower base, so the [service lift](../entities/component/service-lift.md) should be used when it works and the lift battery should be checked on cold mornings.[^c38]
- The service lift on [WTG-06](../entities/asset/wtg-06.md) stopped twice last winter because of cold, and these events should be reported every time for follow-up with [Litware](../entities/organisation/litware-wind-systems.md).[^c39][^c40]

### Oil handling after conversion and close-out

- After conversion, gearboxes must not be topped up with [PWG 320](../entities/product/pwg-320.md), and old drums are marked do not use.[^c41]
- One PWG 320 drum remained in the store and was to stay there until the waste carrier collected it; it was not to be used.[^c42][^c43]
- Attendees were asked to sign the attendance sheet before leaving.[^c44]
- The transcript closes with the same fictional, not-for-operational-use marking.[^c45]

## Figures

No figures were extracted from this document.

## Related

- Assets: [WTG-02](../entities/asset/wtg-02.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [oil filter element](../entities/component/oil-filter.md), [rotor blade](../entities/component/rotor-blade.md), [service lift](../entities/component/service-lift.md)
- Products: [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Organisation: [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Training, site rules and acronyms](../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md)
- [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md)
- [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- [Cold-climate operation and icing](../topics/cold-climate-operation.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [service lift](../entities/component/service-lift.md)
- [Training, site rules and acronyms](../topics/training-and-onboarding.md)
- [WTG-02](../entities/asset/wtg-02.md)
- [WTG-05](../entities/asset/wtg-05.md)
- [WTG-06](../entities/asset/wtg-06.md)
- [WTG-09](../entities/asset/wtg-09.md)
- [WTG-11](../entities/asset/wtg-11.md)
- [WTG-12](../entities/asset/wtg-12.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:00–00:04](../evidence/src-ecc004b57dd5/cue-00-00-00.md) · ✓ quote verified
[^c2]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 03:19–03:23](../evidence/src-ecc004b57dd5/cue-00-03-19.md) · ✓ quote verified
[^c3]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:04–00:11](../evidence/src-ecc004b57dd5/cue-00-00-04.md) · ✓ quote verified
[^c4]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:11–00:19](../evidence/src-ecc004b57dd5/cue-00-00-11.md) · ✓ quote verified
[^c5]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:19–00:27](../evidence/src-ecc004b57dd5/cue-00-00-19.md) · ✓ quote verified
[^c6]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:27–00:37](../evidence/src-ecc004b57dd5/cue-00-00-27.md) · ✓ quote verified
[^c7]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:45–00:56](../evidence/src-ecc004b57dd5/cue-00-00-45.md) · ✓ quote verified
[^c8]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:56–01:05](../evidence/src-ecc004b57dd5/cue-00-00-56.md) · ✓ quote verified
[^c9]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:15–01:23](../evidence/src-ecc004b57dd5/cue-00-01-15.md) · ✓ quote verified
[^c10]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:23–01:34](../evidence/src-ecc004b57dd5/cue-00-01-23.md) · ✓ quote verified
[^c11]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:34–01:43](../evidence/src-ecc004b57dd5/cue-00-01-34.md) · ✓ quote verified
[^c12]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:43–01:52](../evidence/src-ecc004b57dd5/cue-00-01-43.md) · ✓ quote verified
[^c13]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:52–02:01](../evidence/src-ecc004b57dd5/cue-00-01-52.md) · ✓ quote verified
[^c14]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:01–02:10](../evidence/src-ecc004b57dd5/cue-00-02-01.md) · ✓ quote verified
[^c15]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:10–02:20](../evidence/src-ecc004b57dd5/cue-00-02-10.md) · ✓ quote verified
[^c16]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:20–02:29](../evidence/src-ecc004b57dd5/cue-00-02-20.md) · ✓ quote verified
[^c17]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:29–02:37](../evidence/src-ecc004b57dd5/cue-00-02-29.md) · ✓ quote verified
[^c18]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:37–02:45](../evidence/src-ecc004b57dd5/cue-00-02-37.md) · ✓ quote verified
[^c19]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:45–02:55](../evidence/src-ecc004b57dd5/cue-00-02-45.md) · ✓ quote verified
[^c20]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:55–03:03](../evidence/src-ecc004b57dd5/cue-00-02-55.md) · ✓ quote verified
[^c21]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 03:03–03:11](../evidence/src-ecc004b57dd5/cue-00-03-03.md) · ✓ quote verified
[^c22]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 03:11–03:19](../evidence/src-ecc004b57dd5/cue-00-03-11.md) · ✓ quote verified
[^c23]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:00–00:04](../evidence/src-ecc004b57dd5/cue-00-00-00.md) · paraphrase
[^c24]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:04–00:11](../evidence/src-ecc004b57dd5/cue-00-00-04.md) · paraphrase
[^c25]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:11–00:19](../evidence/src-ecc004b57dd5/cue-00-00-11.md) · paraphrase
[^c26]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:19–00:27](../evidence/src-ecc004b57dd5/cue-00-00-19.md) · paraphrase
[^c27]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:27–00:37](../evidence/src-ecc004b57dd5/cue-00-00-27.md) · paraphrase
[^c28]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:45–00:56](../evidence/src-ecc004b57dd5/cue-00-00-45.md) · paraphrase
[^c29]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 00:56–01:05](../evidence/src-ecc004b57dd5/cue-00-00-56.md) · paraphrase
[^c30]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:05–01:15](../evidence/src-ecc004b57dd5/cue-00-01-05.md) · paraphrase
[^c31]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:15–01:23](../evidence/src-ecc004b57dd5/cue-00-01-15.md) · paraphrase
[^c32]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:23–01:34](../evidence/src-ecc004b57dd5/cue-00-01-23.md) · paraphrase
[^c33]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:34–01:43](../evidence/src-ecc004b57dd5/cue-00-01-34.md) · paraphrase
[^c34]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:43–01:52](../evidence/src-ecc004b57dd5/cue-00-01-43.md) · paraphrase
[^c35]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:52–02:01](../evidence/src-ecc004b57dd5/cue-00-01-52.md) · paraphrase
[^c36]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:01–02:10](../evidence/src-ecc004b57dd5/cue-00-02-01.md) · paraphrase
[^c37]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:10–02:20](../evidence/src-ecc004b57dd5/cue-00-02-10.md) · paraphrase
[^c38]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:20–02:29](../evidence/src-ecc004b57dd5/cue-00-02-20.md) · paraphrase
[^c39]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:29–02:37](../evidence/src-ecc004b57dd5/cue-00-02-29.md) · paraphrase
[^c40]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:37–02:45](../evidence/src-ecc004b57dd5/cue-00-02-37.md) · paraphrase
[^c41]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:45–02:55](../evidence/src-ecc004b57dd5/cue-00-02-45.md) · paraphrase
[^c42]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:55–03:03](../evidence/src-ecc004b57dd5/cue-00-02-55.md) · paraphrase
[^c43]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 03:03–03:11](../evidence/src-ecc004b57dd5/cue-00-03-03.md) · paraphrase
[^c44]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 03:11–03:19](../evidence/src-ecc004b57dd5/cue-00-03-11.md) · paraphrase
[^c45]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 03:19–03:23](../evidence/src-ecc004b57dd5/cue-00-03-19.md) · paraphrase
