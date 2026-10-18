---
id: src-15df96905f07
type: source
title: Monthly O&M Review Minutes – 2026-06-18
summary: Minutes of the 18 June 2026 monthly O&M review held at the Quellmoor Ridge O&M building. The meeting covered safety, May performance, the WTG-07 gearbox over-temperature issue, WTG-04 blade replacement planning, environmental curtailment, spare parts, network works, and action tracking.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- meeting-minutes
- meetings
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-15df96905f07
source_path: full/meetings/2026-06-18_monthly-om-review-minutes.docx
source_hash: sha256:015c2f167f3d2068b0e35401d6d596e042bb5f6e9e0229819402e3e290b5505b
media_type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
doc_type: meeting-minutes
category: meetings
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- asset:om-building
- asset:quellmoor-ridge-wind-farm
- asset:wtg-03
- asset:wtg-04
- asset:wtg-05
- asset:wtg-07
- asset:wtg-10
- component:gearbox
- component:hss-bearing
- component:oil-cooler
- component:rescue-kit
- component:rotor-blade
- organisation:city-power-and-light
- organisation:litware-wind-systems
- organisation:tailspin-heavy-lift
- part:fgt-p-22328
topics:
- topic:blades-and-rotor
- topic:environmental-compliance
- topic:gearbox-condition-monitoring
- topic:grid-operations
- topic:safety-and-access
- topic:spare-parts-and-supply
authority: 4
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    native-text: 20
    deterministic-table: 5
---

# Monthly O&M Review Minutes – 2026-06-18

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

Minutes of the 18 June 2026 monthly O&M review held at the [Quellmoor Ridge O&M building](../entities/asset/om-building.md). The meeting covered safety, May performance, the [WTG-07](../entities/asset/wtg-07.md) [gearbox](../entities/component/gearbox.md) over-temperature issue, [WTG-04](../entities/asset/wtg-04.md) blade replacement planning, environmental curtailment, spare parts, network works, and action tracking.

## Key facts

- The monthly O&M review was held on 2026-06-18 from 10:00 to 11:30 at the [Quellmoor Ridge O&M building](../entities/asset/om-building.md).[^c1]
- Maren Ellingsby chaired the meeting as Site Manager; Dario Penwarden, Yusuf Arkwell, Greta Vollan, Tomasz Lebrecht, and Callum Rydings were present, and Élise Ternaux sent apologies.[^c2]
- There was no lost-time injury in May.[^c3]
- The actions from near miss INC-2026-003 were closed.[^c3]
- For audit AUD-2026-02, findings F1, F2, and F5 were closed, while F3 remained open with its due date moved to 2026-07-31.[^c4]
- Audit finding F4 concerning the oil drum bund remained open and was due on 2026-06-30.[^c4]
- May 2026 park availability was 98.0 %, and energy was 6,942 MWh.[^c5]
- [WTG-07](../entities/asset/wtg-07.md) availability was 95.2 % because of [gearbox](../entities/component/gearbox.md) trips.[^c5]
- 8D INC-2026-006 was opened on 2026-05-30 for the WTG-07 gearbox over-temperature issue.[^c6]
- WTG-07 had been limited to 2.6 MW since 2026-06-01.[^c6]
- Oil analysis TR-OA-2026-0614 arrived on 2026-06-17 with condition ALERT and iron at 64 ppm.[^c6]
- Callum Rydings was assigned to inspect the WTG-07 cooler fan and radiator, with the inspection planned for 2026-06-24.[^c6]
- Report WBS-2026-031 arrived on 2026-06-03.[^c7]
- [WTG-04](../entities/asset/wtg-04.md) blade B had a category 4 trailing-edge crack and had to be replaced before 2026-09-30 under WO-26-0355.[^c7]
- A new blade was ordered from [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) for delivery at the end of August.[^c7]
- The crane lift for the WTG-04 blade replacement was to be planned with [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md) for early September.[^c7]
- Monthly drone checks continued, with the next check scheduled for 2026-07-02.[^c7]
- The bat protection curtailment season started on 1 June for [WTG-03](../entities/asset/wtg-03.md), WTG-04, and [WTG-05](../entities/asset/wtg-05.md) under permit condition 7.3.[^c8]
- Yusuf Arkwell checked the curtailment settings in the turbine controllers on 2026-05-28.[^c8]
- There had been no [HSS bearing](../entities/component/hss-bearing.md) [FGT-P-22328](../entities/part/fgt-p-22328.md) in stock since the [WTG-10](../entities/asset/wtg-10.md) repair in March.[^c9]
- Tomasz Lebrecht was to raise a purchase order for two HSS bearings, and the supplier lead time was about 10 weeks.[^c9]
- [City Power & Light](../entities/organisation/city-power-and-light.md) announced July network works on the Skelvane 132 kV circuits, with the formal curtailment instruction expected in early July.[^c10]
- The action list assigned Callum Rydings to inspect the WTG-07 [oil cooler](../entities/component/oil-cooler.md) fan and radiator by 2026-06-24.[^c11]
- The action list assigned Tomasz Lebrecht to raise the purchase order for two HSS bearings FGT-P-22328 by 2026-06-22.[^c12]
- The next review was scheduled for 2026-07-16.[^c13]

## Contents

### Monthly O&M review - minutes

The review took place on 2026-06-18 from 10:00 to 11:30 at the [Quellmoor Ridge O&M building](../entities/asset/om-building.md).[^c14] Maren Ellingsby chaired the meeting as Site Manager; Dario Penwarden, Yusuf Arkwell, Greta Vollan, Tomasz Lebrecht, and Callum Rydings were present, and Élise Ternaux sent apologies.[^c15]

### Safety

No lost-time injury occurred in May.[^c16] The actions from near miss INC-2026-003 were closed.[^c16]

For audit AUD-2026-02, findings F1, F2, and F5 were closed.[^c17] Finding F3 was still open because toolbox talk records were being reconstructed, and its due date moved to 2026-07-31.[^c17] Finding F4 for the oil drum bund remained open and was due on 2026-06-30.[^c17]

### Performance in May 2026

Park availability in May 2026 was 98.0 %, and energy was 6,942 MWh.[^c18] [WTG-07](../entities/asset/wtg-07.md) availability was 95.2 % because of [gearbox](../entities/component/gearbox.md) trips.[^c18]

### WTG-07 gearbox over-temperature

8D INC-2026-006 was opened on 2026-05-30.[^c19] [WTG-07](../entities/asset/wtg-07.md) had been limited to 2.6 MW since 2026-06-01.[^c19] Oil analysis TR-OA-2026-0614 arrived on 2026-06-17 with condition ALERT and iron at 64 ppm.[^c19] Callum Rydings was to inspect the cooler fan and radiator, with the inspection planned for 2026-06-24.[^c19]

### Blade inspection

Report WBS-2026-031 arrived on 2026-06-03.[^c20] [WTG-04](../entities/asset/wtg-04.md) blade B had a category 4 trailing-edge crack and had to be replaced before 2026-09-30 under WO-26-0355.[^c20] A new blade was ordered from [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) for delivery at the end of August.[^c20] The crane lift was to be planned with [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md) for early September.[^c20] Monthly drone checks continued, with the next check scheduled for 2026-07-02.[^c20]

### Environment

The bat protection curtailment season started on 1 June for [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), and [WTG-05](../entities/asset/wtg-05.md) under permit condition 7.3.[^c21] Yusuf Arkwell checked the curtailment settings in the turbine controllers on 2026-05-28.[^c21]

### Spare parts

There had been no [HSS bearing](../entities/component/hss-bearing.md) [FGT-P-22328](../entities/part/fgt-p-22328.md) in stock since the [WTG-10](../entities/asset/wtg-10.md) repair in March.[^c22] Tomasz Lebrecht was to raise a purchase order for two bearings, and the supplier lead time was about 10 weeks.[^c22]

### Any other business

[City Power & Light](../entities/organisation/city-power-and-light.md) announced network works on the Skelvane 132 kV circuits in July.[^c23] The formal curtailment instruction was expected in early July.[^c23]

### Actions

The actions section is captured in the associated action table.[^c24]

**Table t01** · table 1, rows 1–6

| Row | No. | Action | Owner | Due |
| --- | --- | --- | --- | --- |
| 2 | 1 | Inspect [WTG-07](../entities/asset/wtg-07.md) [oil cooler](../entities/component/oil-cooler.md) fan and radiator | Callum Rydings | 2026-06-24 |
| 3 | 2 | Purchase order for two HSS bearings [FGT-P-22328](../entities/part/fgt-p-22328.md) | Tomasz Lebrecht | 2026-06-22 |
| 4 | 3 | Plan the [WTG-04](../entities/asset/wtg-04.md) blade lift with [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md) | Dario Penwarden | 2026-07-31 |
| 5 | 4 | Close audit finding F3 | Greta Vollan | 2026-07-31 |
| 6 | 5 | Bund capacity for oil drums (finding F4) | Tomasz Lebrecht | 2026-06-30 |

Agents can query this table as `t01` with the `query_table` tool.

### Next review

The next review was scheduled for 2026-07-16.[^c25]

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-10](../entities/asset/wtg-10.md)
- Components: [gearbox](../entities/component/gearbox.md), [HSS bearing](../entities/component/hss-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md)
- Spare part: [FGT-P-22328](../entities/part/fgt-p-22328.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)
- Topics: [Blades, pitch bearings and main-component lifts](../topics/blades-and-rotor.md), [Environmental permit and night curtailment](../topics/environmental-compliance.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Grid connection and grid operator instructions](../topics/grid-operations.md), [Safety, isolation and work at height](../topics/safety-and-access.md), [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Blades, pitch bearings and main-component lifts](../topics/blades-and-rotor.md)
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Environmental permit and night curtailment](../topics/environmental-compliance.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [Grid connection and grid operator instructions](../topics/grid-operations.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)
- [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)
- [WTG-03](../entities/asset/wtg-03.md)
- [WTG-04](../entities/asset/wtg-04.md)
- [WTG-05](../entities/asset/wtg-05.md)
- [WTG-07](../entities/asset/wtg-07.md)
- [WTG-10](../entities/asset/wtg-10.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 2](../evidence/src-15df96905f07/para-0002.md) · ✓ quote verified
[^c2]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 3](../evidence/src-15df96905f07/para-0003.md) · ✓ quote verified
[^c3]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 5](../evidence/src-15df96905f07/para-0005.md) · ✓ quote verified
[^c4]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 6](../evidence/src-15df96905f07/para-0006.md) · ✓ quote verified
[^c5]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 8](../evidence/src-15df96905f07/para-0008.md) · ✓ quote verified
[^c6]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 10](../evidence/src-15df96905f07/para-0010.md) · ✓ quote verified
[^c7]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 12](../evidence/src-15df96905f07/para-0012.md) · ✓ quote verified
[^c8]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 14](../evidence/src-15df96905f07/para-0014.md) · ✓ quote verified
[^c9]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 16](../evidence/src-15df96905f07/para-0016.md) · ✓ quote verified
[^c10]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 18](../evidence/src-15df96905f07/para-0018.md) · ✓ quote verified
[^c11]: [Monthly O&M Review Minutes – 2026-06-18 — table 1, row 2](../evidence/src-15df96905f07/tbl-01-r0002-r0002.md) · table
[^c12]: [Monthly O&M Review Minutes – 2026-06-18 — table 1, row 3](../evidence/src-15df96905f07/tbl-01-r0003-r0003.md) · table
[^c13]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 20](../evidence/src-15df96905f07/para-0020.md) · ✓ quote verified
[^c14]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 2](../evidence/src-15df96905f07/para-0002.md) · paraphrase
[^c15]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 3](../evidence/src-15df96905f07/para-0003.md) · paraphrase
[^c16]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 5](../evidence/src-15df96905f07/para-0005.md) · paraphrase
[^c17]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 6](../evidence/src-15df96905f07/para-0006.md) · paraphrase
[^c18]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 8](../evidence/src-15df96905f07/para-0008.md) · paraphrase
[^c19]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 10](../evidence/src-15df96905f07/para-0010.md) · paraphrase
[^c20]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 12](../evidence/src-15df96905f07/para-0012.md) · paraphrase
[^c21]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 14](../evidence/src-15df96905f07/para-0014.md) · paraphrase
[^c22]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 16](../evidence/src-15df96905f07/para-0016.md) · paraphrase
[^c23]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 18](../evidence/src-15df96905f07/para-0018.md) · paraphrase
[^c24]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 19](../evidence/src-15df96905f07/para-0019.md) · paraphrase
[^c25]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 20](../evidence/src-15df96905f07/para-0020.md) · paraphrase
