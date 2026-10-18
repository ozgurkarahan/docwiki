---
id: src-1b5b5135881d
type: source
title: Gearbox Fundamentals for Wind Technicians
summary: This training deck covers gearbox fundamentals for wind technicians, focused on the Fabrikam FGT-3200 in the Litware LT-32. It explains drivetrain stages, shaft acronyms, lubrication after the PWG 220 change, temperature and condition-monitoring thresholds, typical failure modes, and quiz answers.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- training
- training-deck
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-1b5b5135881d
source_path: full/training/gearbox-fundamentals.pptx
source_hash: sha256:b0a9262bc91391a4c0894c9d46141a5214c4fdd5bb5e31098aaf1ff74a3acd1e
media_type: application/vnd.openxmlformats-officedocument.presentationml.presentation
doc_type: training-deck
category: training
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: 10
entities:
- alarm-code:a2101
- alarm-code:a2102
- bulletin:sb-lws-2025-07
- component:cooler-fan-motor
- component:gearbox
- component:generator
- component:hss-bearing
- component:oil-cooler
- component:planetary-stage
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- product:fgt-3200
- product:lt-32
- product:pwg-220
- product:pwg-320
topics:
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:generator-and-electrical
- topic:training-and-onboarding
authority: 4
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 36
    model-description: 2
---

# Gearbox Fundamentals for Wind Technicians

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This training deck covers [gearbox](../entities/component/gearbox.md) fundamentals for wind technicians, focused on the [Fabrikam FGT-3200](../entities/product/fgt-3200.md) in the [Litware LT-32](../entities/product/lt-32.md). It explains drivetrain stages, shaft acronyms, lubrication after the [PWG 220](../entities/product/pwg-220.md) change, temperature and condition-monitoring thresholds, typical failure modes, and quiz answers.

## Key facts

- The deck is titled “[Gearbox](../entities/component/gearbox.md) fundamentals for wind technicians.”[^c1]
- The deck is about the [Fabrikam FGT-3200](../entities/product/fgt-3200.md) in the [Litware LT-32](../entities/product/lt-32.md) and is dated October 2025.[^c1]
- The deck is marked fictional and not for operational use.[^c1]
- The gearbox raises rotor speed from 12.7 rpm to 1,500 rpm at the [generator](../entities/component/generator.md).[^c2]
- The gearbox stages described are a [planetary stage](../entities/component/planetary-stage.md) with a planet carrier, three planet gears, a ring gear and a sun pinion, followed by two parallel helical stages.[^c3]
- The overall gearbox ratio is 1:118.4, with rotor speed 12.7 rpm and generator speed 1,500 rpm.[^c3]
- LSS means low-speed shaft, the main shaft on the rotor side.[^c4]
- IMS means intermediate-speed shaft, located between the two helical stages.[^c4]
- HSS means high-speed shaft, the output shaft to the generator coupling.[^c4]
- PQ index means particle quantifier index, the amount of ferrous debris in an oil sample.[^c4]
- RMS means root mean square, a value used for vibration velocity.[^c4]
- Since [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md), the gearboxes use [Proseware PWG 220](../entities/product/pwg-220.md) with ISO VG 220 instead of [PWG 320](../entities/product/pwg-320.md).[^c5]
- Each gearbox uses 410 L of oil, with a 60 L flush during the conversion.[^c5]
- The minimum oil temperature for start-up is +5 °C, compared with +10 °C when using PWG 320.[^c5]
- Oils must not be mixed; top-up is with PWG 220 only.[^c5]
- The conversion campaign runs from September to November 2025 under MOC-2025-012.[^c5]
- Normal oil sump temperature is 50 to 65 °C.[^c6]
- [A2101](../entities/alarm-code/a2101.md) gives a warning at 75 °C, and [A2102](../entities/alarm-code/a2102.md) trips at 82 °C.[^c6]
- The thermostatic valve opens the cooler circuit at 45 °C.[^c6]
- The cooler fan and radiator are to be kept clean.[^c6]
- Vibration velocity RMS on the HSS bearings has an alert threshold of 3.5 mm/s and an alarm threshold of 4.5 mm/s.[^c7]
- Oil analysis is performed every 6 months, with an iron alert at 50 ppm and a PQ index alert at 60.[^c7]
- For condition monitoring, the trend matters more than a single value.[^c7]
- Typical gearbox-related failure modes listed are [HSS bearing](../entities/component/hss-bearing.md) damage, micropitting on gear teeth, cooler fouling and fan motor failures, and oil leaks at seals and hoses.[^c8]
- The exploded view item numbers follow maintenance manual LWS-MM-GBX-32, figure 4-1.[^c9]
- The quiz answers state that the HSS drives the generator, A2102 trips at 82 °C, the oil used is Proseware PWG 220, and a rising PQ index means more ferrous wear debris, often from a bearing.[^c10]

## Contents

### Overview (document section)

This training deck is titled “[Gearbox](../entities/component/gearbox.md) fundamentals for wind technicians” and focuses on the [Fabrikam FGT-3200](../entities/product/fgt-3200.md) in the [Litware LT-32](../entities/product/lt-32.md).[^c11]

The deck is marked fictional and not for operational use.[^c11]

### From rotor to generator

The [gearbox](../entities/component/gearbox.md) raises 12.7 rpm at the rotor to 1,500 rpm at the [generator](../entities/component/generator.md).[^c12]

### Three stages

The [gearbox](../entities/component/gearbox.md) has a [planetary stage](../entities/component/planetary-stage.md) made up of a planet carrier, three planet gears, a ring gear and a sun pinion, followed by two parallel helical stages.[^c13]

The overall ratio is 1:118.4, with 12.7 rpm at the rotor and 1,500 rpm at the [generator](../entities/component/generator.md).[^c13]

### Shaft names and acronyms

The slide provides shaft-name and monitoring acronyms in a table.[^c14]

**Table t01** · slide 4

| Row | Acronym | Meaning |
| --- | --- | --- |
| 2 | LSS | Low-speed shaft - main shaft on the rotor side |
| 3 | IMS | Intermediate-speed shaft - between the two helical stages |
| 4 | HSS | High-speed shaft - output shaft to the [generator](../entities/component/generator.md) coupling |
| 5 | PQ index | Particle quantifier index - amount of ferrous debris in an oil sample |
| 6 | RMS | Root mean square - value used for vibration velocity |

Agents can query this table as `t01` with the `query_table` tool.

### Lubrication: the change to PWG 220

Since [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md), the gearboxes use [Proseware PWG 220](../entities/product/pwg-220.md) with ISO VG 220 instead of [PWG 320](../entities/product/pwg-320.md).[^c15]

Each [gearbox](../entities/component/gearbox.md) uses 410 L, and the conversion includes a 60 L flush.[^c15]

The minimum oil temperature for start-up is +5 °C, compared with +10 °C when PWG 320 was used.[^c15]

Oils are not to be mixed, and top-up is with PWG 220 only.[^c15]

The conversion campaign runs from September to November 2025 under MOC-2025-012.[^c15]

### Temperatures and alarms

Normal oil sump temperature is 50 to 65 °C.[^c16]

[A2101](../entities/alarm-code/a2101.md) warns at 75 °C, and [A2102](../entities/alarm-code/a2102.md) trips at 82 °C.[^c16]

The thermostatic valve opens the cooler circuit at 45 °C.[^c16]

The cooler fan and radiator are to be kept clean.[^c16]

### Condition monitoring

Vibration velocity RMS on the HSS bearings has an alert threshold of 3.5 mm/s and an alarm threshold of 4.5 mm/s.[^c17]

Oil analysis is performed every 6 months, with an iron alert at 50 ppm and a PQ index alert at 60.[^c17]

The deck states that the trend matters more than a single value.[^c17]

### Typical failure modes

The listed typical failure modes are [HSS bearing](../entities/component/hss-bearing.md) damage with spalling and axial cracks, micropitting on gear teeth, cooler fouling and fan motor failures, and oil leaks at seals and hoses.[^c18]

### Exploded view and quiz

The deck includes an exploded view of the [FGT-3200](../entities/product/fgt-3200.md).[^c19]

The item numbers are as in maintenance manual LWS-MM-GBX-32, figure 4-1.[^c19]

The quiz asks about the generator-driving shaft, the oil temperature for [A2102](../entities/alarm-code/a2102.md) trip, the oil used since conversion, and the meaning of a rising PQ index.[^c20]

The speaker notes answer that the HSS drives the [generator](../entities/component/generator.md), A2102 trips at 82 °C, the oil is [Proseware PWG 220](../entities/product/pwg-220.md), and a rising PQ index means more ferrous wear debris, often from a bearing.[^c20]

## Figures

- **Figure f01** (slide 2): Generated description: A horizontal block diagram shows a wind turbine drivetrain from left to right: Rotor hub (3 blades), Main bearing, LSS, [Planetary stage](../entities/component/planetary-stage.md), IMS, HSS, and [Generator](../entities/component/generator.md) 1,500 rpm, with arrows connecting each block. A dashed bracket labeled [Gearbox](../entities/component/gearbox.md) 1:118.4 spans the Planetary stage, IMS, and HSS, and small labels below indicate 12.7 rpm near the LSS and 1,500 rpm near the gearbox output/generator. The LSS, IMS, and HSS blocks are shaded light blue while the others are white with blue outlines.[^c21]
- **Figure f02** (slide 9): Generated description: A schematic technical diagram of a machine assembly with multiple numbered parts labeled 1 through 16. It shows several rectangular and cylindrical components, dashed centerlines, and arrows indicating “rotor side” on the left and “generator side” on the right, with the numbered callouts pointing to individual elements such as plates, shafts, blocks, and a circular disc.[^c22]

## Related

- Components: [gearbox](../entities/component/gearbox.md), [generator](../entities/component/generator.md), [HSS bearing](../entities/component/hss-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [planetary stage](../entities/component/planetary-stage.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../topics/generator-and-electrical.md), [Training, site rules and acronyms](../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [generator](../entities/component/generator.md)
- [Generator brushes and electrical systems](../topics/generator-and-electrical.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [planetary stage](../entities/component/planetary-stage.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [Training, site rules and acronyms](../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Gearbox Fundamentals for Wind Technicians — slide 1](../evidence/src-1b5b5135881d/slide-01.md) · ✓ quote verified
[^c2]: [Gearbox Fundamentals for Wind Technicians — slide 2](../evidence/src-1b5b5135881d/slide-02.md) · ✓ quote verified
[^c3]: [Gearbox Fundamentals for Wind Technicians — slide 3](../evidence/src-1b5b5135881d/slide-03.md) · ✓ quote verified
[^c4]: [Gearbox Fundamentals for Wind Technicians — slide 4](../evidence/src-1b5b5135881d/slide-04.md) · ✓ quote verified
[^c5]: [Gearbox Fundamentals for Wind Technicians — slide 5](../evidence/src-1b5b5135881d/slide-05.md) · ✓ quote verified
[^c6]: [Gearbox Fundamentals for Wind Technicians — slide 6](../evidence/src-1b5b5135881d/slide-06.md) · ✓ quote verified
[^c7]: [Gearbox Fundamentals for Wind Technicians — slide 7](../evidence/src-1b5b5135881d/slide-07.md) · ✓ quote verified
[^c8]: [Gearbox Fundamentals for Wind Technicians — slide 8](../evidence/src-1b5b5135881d/slide-08.md) · ✓ quote verified
[^c9]: [Gearbox Fundamentals for Wind Technicians — slide 9](../evidence/src-1b5b5135881d/slide-09.md) · ✓ quote verified
[^c10]: [Gearbox Fundamentals for Wind Technicians — slide 10](../evidence/src-1b5b5135881d/slide-10.md) · ✓ quote verified
[^c11]: [Gearbox Fundamentals for Wind Technicians — slide 1](../evidence/src-1b5b5135881d/slide-01.md) · paraphrase
[^c12]: [Gearbox Fundamentals for Wind Technicians — slide 2](../evidence/src-1b5b5135881d/slide-02.md) · paraphrase
[^c13]: [Gearbox Fundamentals for Wind Technicians — slide 3](../evidence/src-1b5b5135881d/slide-03.md) · paraphrase
[^c14]: [Gearbox Fundamentals for Wind Technicians — slide 4](../evidence/src-1b5b5135881d/slide-04.md) · paraphrase
[^c15]: [Gearbox Fundamentals for Wind Technicians — slide 5](../evidence/src-1b5b5135881d/slide-05.md) · paraphrase
[^c16]: [Gearbox Fundamentals for Wind Technicians — slide 6](../evidence/src-1b5b5135881d/slide-06.md) · paraphrase
[^c17]: [Gearbox Fundamentals for Wind Technicians — slide 7](../evidence/src-1b5b5135881d/slide-07.md) · paraphrase
[^c18]: [Gearbox Fundamentals for Wind Technicians — slide 8](../evidence/src-1b5b5135881d/slide-08.md) · paraphrase
[^c19]: [Gearbox Fundamentals for Wind Technicians — slide 9](../evidence/src-1b5b5135881d/slide-09.md) · paraphrase
[^c20]: [Gearbox Fundamentals for Wind Technicians — slide 10](../evidence/src-1b5b5135881d/slide-10.md) · paraphrase
[^c21]: [Gearbox Fundamentals for Wind Technicians — slide 2](../evidence/src-1b5b5135881d/slide-02.md) · generated description
[^c22]: [Gearbox Fundamentals for Wind Technicians — slide 9](../evidence/src-1b5b5135881d/slide-09.md) · generated description
