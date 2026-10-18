---
id: src-e7cd20fa7984
type: source
title: Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)
summary: This training deck is an induction for new staff and contractors at Quellmoor Ridge Wind Farm. It covers site layout facts, key contacts, site rules, permits and isolation, work-at-height and rescue rules, weather and ice controls, emergency arrangements, acronyms, and environmental requirements.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- training
- training-deck
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-e7cd20fa7984
source_path: full/training/onboarding-and-site-rules.pptx
source_hash: sha256:5800c512d3feb19c5e832debeff3d39e482859871efb0ac707d9853e97493372
media_type: application/vnd.openxmlformats-officedocument.presentationml.presentation
doc_type: training-deck
category: training
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: 11
entities:
- alarm-code:a7001
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
- component:generator
- component:rescue-kit
- component:rotor-blade
- organisation:city-power-and-light
- organisation:contoso-renewables
- organisation:litware-wind-systems
- procedure:sop-loto-001
- procedure:sop-wah-003
- product:lt-32
- product:lt-32-ccv
topics:
- topic:cold-climate-operation
- topic:environmental-compliance
- topic:grid-operations
- topic:safety-and-access
- topic:training-and-onboarding
authority: 4
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 49
---

# Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This training deck is an induction for new staff and contractors at [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md). It covers site layout facts, key contacts, site rules, permits and isolation, work-at-height and rescue rules, weather and ice controls, emergency arrangements, acronyms, and environmental requirements.

## Key facts

- The deck is an induction for new staff and contractors by [Contoso Renewables](../entities/organisation/contoso-renewables.md) dated February 2025.[^c1]
- The deck is labelled fictional and not for operational use.[^c1]
- [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) has 12 [Litware LT-32](../entities/product/lt-32.md) turbines in CCV configuration, identified [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), with total capacity of 38.4 MW.[^c2]
- Commercial operation at the site began on 15 October 2019.[^c2]
- The turbines have a hub height of 92 m and a rotor diameter of 118 m.[^c2]
- The site connects to [City Power & Light](../entities/organisation/city-power-and-light.md) at the Skelvane 132 kV substation.[^c2]
- The O&M building with workshop and stores is at the site entrance.[^c2]
- The speed limit on all site roads is 20 km/h.[^c3]
- Everyone must sign in and out at the O&M building.[^c3]
- Any turbine access requires a minimum of two persons; lone working is not allowed.[^c3]
- Helmet, safety boots and high-visibility vest are required outside vehicles.[^c3]
- Every incident and near miss must be reported on the same day.[^c3]
- Every turbine job needs a permit to work signed by the issuer.[^c4]
- Isolation follows [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) and requires a personal padlock and name tag.[^c4]
- High-voltage switching is only for authorised persons, and the control room must always know who is in which turbine.[^c5]
- All work at height must follow [SOP-WAH-003](../entities/procedure/sop-wah-003.md).[^c6]
- Climbing is allowed up to a 10-minute mean wind speed of 15 m/s, and hub entry is allowed up to 12 m/s.[^c6]
- A sealed [rescue kit](../entities/component/rescue-kit.md) is kept in every nacelle and its seal must be checked every day.[^c6]
- The rescue target is to have a casualty on the ground within 15 minutes.[^c6]
- Ice detection alarm [A7001](../entities/alarm-code/a7001.md) stops the turbine automatically.[^c7]
- Personnel must keep 300 m away from a turbine with ice on the blades.[^c7]
- Climbing is not allowed when lightning is detected within 15 km.[^c7]
- In an emergency, the alarm is raised to the control room first, the muster point is the O&M building car park, and the site ERP is followed.[^c8]
- The site has an environmental permit with conditions on noise, shadow flicker, ice and wildlife.[^c9]
- Automatic turbine stops for permit reasons must never be overridden.[^c9]
- A spill kit is kept in every turbine, and any spill must be reported immediately to the HSE Coordinator.[^c10]
- The HSE Coordinator contact named on the final slide is Greta Vollan, with e-mail `greta.vollan@contoso-renewables.example`.[^c11]

## Contents

### Title and induction scope

The deck is titled “[Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md) - onboarding and site rules.”[^c12] It is a [Contoso Renewables](../entities/organisation/contoso-renewables.md) induction for new staff and contractors dated February 2025.[^c12] The deck states that it is fictional and not for operational use.[^c12]

### Welcome to Quellmoor Ridge

[Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md) has 12 [Litware LT-32](../entities/product/lt-32.md) turbines in CCV configuration, [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md), with 38.4 MW capacity.[^c13] Commercial operation began on 15 October 2019.[^c13] The turbines have 92 m hub height and 118 m rotor diameter.[^c13] The grid connection is to [City Power & Light](../entities/organisation/city-power-and-light.md) at the Skelvane 132 kV substation.[^c13] The O&M building with workshop and stores is at the site entrance.[^c13]

### Who is who

The personnel table lists the site roles and named contacts for Site Manager, O&M Supervisor, HSE Coordinator, Reliability Engineer, Stores and spare parts, and Lead Wind Technician.[^c14]

**Table t01** · slide 3

| Row | Role | Name |
| --- | --- | --- |
| 2 | Site Manager | Maren Ellingsby |
| 3 | O&M Supervisor | Dario Penwarden |
| 4 | HSE Coordinator | Greta Vollan |
| 5 | Reliability Engineer | Yusuf Arkwell |
| 6 | Stores and spare parts | Tomasz Lebrecht |
| 7 | Lead Wind Technician | Callum Rydings |

Agents can query this table as `t01` with the `query_table` tool.

### Site rules

- The site road speed limit is 20 km/h.[^c15]
- Personnel sign in and out at the O&M building.[^c15]
- Turbine access requires at least two persons, and lone working is not allowed.[^c15]
- Helmet, safety boots and high-visibility vest are required outside vehicles.[^c15]
- Every incident and near miss is reported on the same day.[^c15]

### Permits and isolation

- Every turbine job needs a PTW signed by the issuer.[^c5]
- Isolation follows [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) with a personal padlock and name tag.[^c5]
- High-voltage switching is only by authorised persons.[^c5]
- The control room must always know who is in which turbine.[^c5]

### Climbing and rescue

- All work at height follows [SOP-WAH-003](../entities/procedure/sop-wah-003.md).[^c16]
- Climbing is allowed up to a 10-minute mean wind speed of 15 m/s, and hub entry is allowed up to 12 m/s.[^c16]
- A sealed [rescue kit](../entities/component/rescue-kit.md) is kept in every nacelle, and the seal is checked every day.[^c16]
- The rescue target is a casualty on the ground within 15 minutes.[^c16]

### Weather and ice

- Ice detection alarm [A7001](../entities/alarm-code/a7001.md) stops the turbine automatically.[^c17]
- Personnel keep 300 m away from a turbine with ice on the blades.[^c17]
- Climbing is not allowed when lightning is detected within 15 km.[^c17]
- In cold weather, work is done in pairs and warm breaks are taken in the vehicle.[^c17]

### Emergency

- In an emergency, the alarm is raised to the control room first.[^c8]
- The muster point is the O&M building car park.[^c8]
- First aiders are on every shift, and defibrillators are in the O&M building and each service vehicle.[^c8]
- The site ERP is followed.[^c8]

### Acronyms used on site

The acronym table defines the site meanings for CCV, PTW, LOTO, MOC, TBT, SPL, WTG, ERP, CMS, and SB.[^c18]

**Table t02** · slide 9

| Row | Acronym | Meaning |
| --- | --- | --- |
| 2 | CCV | Cold Climate Version - [LT-32](../entities/product/lt-32.md) variant with [gearbox](../entities/component/gearbox.md) oil heaters, low-temperature steel and heated sensors |
| 3 | PTW | Permit to work |
| 4 | LOTO | Lockout/tagout |
| 5 | MOC | Management of change |
| 6 | TBT | Toolbox talk |
| 7 | SPL | Single-point lesson |
| 8 | WTG | Wind turbine [generator](../entities/component/generator.md) (our turbine numbers [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md)) |
| 9 | ERP | Emergency response plan |
| 10 | CMS | Condition monitoring system |
| 11 | SB | Service bulletin (issued by the turbine manufacturer) |

Agents can query this table as `t02` with the `query_table` tool.

### Environment

The site has an environmental permit with conditions on noise, shadow flicker, ice and wildlife.[^c10] Some turbines stop automatically for permit reasons, and these stops must never be overridden.[^c10] A spill kit is kept in every turbine.[^c10] Any spill is reported immediately to the HSE Coordinator.[^c10]

### Questions and training record

The final slide names Greta Vollan as HSE Coordinator and gives `greta.vollan@contoso-renewables.example` as the e-mail contact.[^c19] The induction record is kept with the training file.[^c19]

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md)
- Products: [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md)
- Alarm code: [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Procedures: [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../topics/environmental-compliance.md), [Grid connection and grid operator instructions](../topics/grid-operations.md), [Safety, isolation and work at height](../topics/safety-and-access.md), [Training, site rules and acronyms](../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Cold-climate operation and icing](../topics/cold-climate-operation.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Environmental permit and night curtailment](../topics/environmental-compliance.md)
- [gearbox](../entities/component/gearbox.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [generator](../entities/component/generator.md)
- [Grid connection and grid operator instructions](../topics/grid-operations.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
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

[^c1]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 1](../evidence/src-e7cd20fa7984/slide-01.md) · ✓ quote verified
[^c2]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 2](../evidence/src-e7cd20fa7984/slide-02.md) · ✓ quote verified
[^c3]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 4](../evidence/src-e7cd20fa7984/slide-04.md) · ✓ quote verified
[^c4]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 5](../evidence/src-e7cd20fa7984/slide-05.md) · ✓ quote verified
[^c5]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 5](../evidence/src-e7cd20fa7984/slide-05.md) · paraphrase
[^c6]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 6](../evidence/src-e7cd20fa7984/slide-06.md) · ✓ quote verified
[^c7]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 7](../evidence/src-e7cd20fa7984/slide-07.md) · ✓ quote verified
[^c8]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 8](../evidence/src-e7cd20fa7984/slide-08.md) · paraphrase
[^c9]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 10](../evidence/src-e7cd20fa7984/slide-10.md) · ✓ quote verified
[^c10]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 10](../evidence/src-e7cd20fa7984/slide-10.md) · paraphrase
[^c11]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 11](../evidence/src-e7cd20fa7984/slide-11.md) · ✓ quote verified
[^c12]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 1](../evidence/src-e7cd20fa7984/slide-01.md) · paraphrase
[^c13]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 2](../evidence/src-e7cd20fa7984/slide-02.md) · paraphrase
[^c14]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 3](../evidence/src-e7cd20fa7984/slide-03.md) · paraphrase
[^c15]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 4](../evidence/src-e7cd20fa7984/slide-04.md) · paraphrase
[^c16]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 6](../evidence/src-e7cd20fa7984/slide-06.md) · paraphrase
[^c17]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 7](../evidence/src-e7cd20fa7984/slide-07.md) · paraphrase
[^c18]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 9](../evidence/src-e7cd20fa7984/slide-09.md) · paraphrase
[^c19]: [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025) — slide 11](../evidence/src-e7cd20fa7984/slide-11.md) · paraphrase
