---
id: src-42566abae6ef
type: source
title: Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building
summary: This spreadsheet is a fictional spare-parts stock snapshot for the Quellmoor Ridge O&M building as of 2026-07-21. It covers stock levels, movements, supplier lead times, and ownership information.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- records-and-data
- stock-list
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-42566abae6ef
source_path: full/records/spare-parts-stock-2026-07-21.xlsx
source_hash: sha256:9976d2934ef2ab31227cc1dd6b09b720ae76f246730756a242b0aebe319415d1
media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
doc_type: stock-list
category: records-and-data
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
- asset:wtg-01
- asset:wtg-07
- asset:wtg-09
- asset:wtg-10
- asset:wtg-11
- component:cooler-fan-motor
- component:gearbox
- component:generator
- component:generator-brushes
- component:hss-bearing
- component:ims-bearing
- component:oil-cooler
- component:oil-filter
- component:pitch-bearing
- component:pitch-bearing-bolts
- component:slip-ring
- organisation:adventure-works-industrial-supply
- organisation:contoso-renewables
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- part:awi-10442
- part:awi-20915
- part:awi-31007
- part:awi-40210
- part:awi-40388
- part:fgt-p-11872
- part:fgt-p-11880
- part:fgt-p-13010
- part:fgt-p-14002
- part:fgt-p-21904
- part:fgt-p-22328
- part:fgt-p-22331
- part:lws-p-30418
- part:lws-p-30422
- part:lws-p-41120
- part:lws-p-51207
- part:lws-p-55031
- part:lws-p-60455
- part:lws-p-72210
- part:lws-p-80031
- part:lws-p-90012
- part:pws-220-d208
- part:pws-320-d208
- product:fgt-3200
- product:pwg-220
- product:pwg-320
topics:
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:spare-parts-and-supply
authority: 5
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    deterministic-table: 44
---

# Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This spreadsheet is a fictional spare-parts stock snapshot for the [Quellmoor Ridge O&M building](../entities/asset/om-building.md) as of 2026-07-21. It covers stock levels, movements, supplier lead times, and ownership information.

## Key facts

- The workbook states that it is a fictional spare-parts stock snapshot for the [Quellmoor Ridge O&M building](../entities/asset/om-building.md) dated 2026-07-21.[^c1]
- A part is below its minimum level when its On hand quantity is lower than its Minimum quantity.[^c2]
- [FGT-P-22328](../entities/part/fgt-p-22328.md), the [HSS bearing](../entities/component/hss-bearing.md) on the [generator](../entities/component/generator.md) side for [FGT-3200](../entities/product/fgt-3200.md), is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c2][^c3]
- [LWS-P-30418](../entities/part/lws-p-30418.md), the 1.5 kW [oil cooler fan motor](../entities/component/cooler-fan-motor.md), is a critical item below minimum stock: 1 pc on hand, minimum 2 pc, reorder quantity 2 pc, and 2 pc on order under PO-77102 for expected delivery on 2026-08-14.[^c2][^c4]
- [PWS-320-D208](../entities/part/pws-320-d208.md) is listed as [Proseware PWG 320](../entities/product/pwg-320.md) gear oil in a 208 L drum with a do-not-use note tied to MOC-2025-012; the stock entry shows 1 drum on hand, minimum 0, reorder quantity 0, and 0 on order.[^c5]
- The movements sheet records a 2026-03-12 issue of quantity -1 for FGT-P-22328 against WO-26-0187 for [WTG-10](../entities/asset/wtg-10.md).[^c6]
- The movements sheet records a 2026-06-24 issue of quantity -1 for LWS-P-30418 against WO-26-0398 for [WTG-07](../entities/asset/wtg-07.md).[^c7]
- The movements sheet records a 2026-07-18 issue of quantity -1 for [LWS-P-51207](../entities/part/lws-p-51207.md) against WO-26-0436 for [WTG-09](../entities/asset/wtg-09.md).[^c8]
- Supplier typical lead times are 10 weeks for [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), 6 weeks for [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), 3 weeks for [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), and 2 weeks for [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md).[^c9][^c10][^c11][^c12]
- The owner is Tomasz Lebrecht, Stores and Spare Parts Coordinator at [Contoso Renewables](../entities/organisation/contoso-renewables.md).[^c13]

## Contents

### Stock

The stock sheet is headed “Stock.”[^c14]

The stock table includes entries such as [FGT-P-22328](../entities/part/fgt-p-22328.md), an [HSS bearing](../entities/component/hss-bearing.md) for [FGT-3200](../entities/product/fgt-3200.md) supplied by [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), and [AWI-40388](../entities/part/awi-40388.md), oil absorbent pads supplied by [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md).[^c3][^c15]

The workbook defines a below-minimum part as one whose On hand quantity is lower than its Minimum quantity.[^c2] Under that definition, FGT-P-22328 is below minimum with 0 on hand and a minimum of 1, and [LWS-P-30418](../entities/part/lws-p-30418.md) is below minimum with 1 on hand and a minimum of 2.[^c3][^c4]

[PWS-320-D208](../entities/part/pws-320-d208.md) is listed as [Proseware PWG 320](../entities/product/pwg-320.md) gear oil in a 208 L drum with the note “do not use (MOC-2025-012).”[^c5]

**Table t01** · sheet "Stock", rows 1–24

| Row | Part number | Description | Supplier | Category | Unit | On hand | Minimum | Reorder qty | On order | PO number | Expected delivery | Bin | Critical |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | FGT-P-22328 | HSS bearing, [generator](../entities/component/generator.md) side (FGT-3200) | Fabrikam Getriebetechnik GmbH | Bearings | pc | 0 | 1 | 2 | 2 | PO-76994 | 2026-09-25 | B-04-2 | Y |
| 3 | [FGT-P-22331](../entities/part/fgt-p-22331.md) | HSS bearing, rotor side (FGT-3200) | Fabrikam Getriebetechnik GmbH | Bearings | pc | 1 | 1 | 1 | 0 |  |  | B-04-3 | Y |
| 4 | [FGT-P-21904](../entities/part/fgt-p-21904.md) | [IMS bearing](../entities/component/ims-bearing.md) set (FGT-3200) | Fabrikam Getriebetechnik GmbH | Bearings | set | 1 | 1 | 1 | 0 |  |  | B-05-1 | Y |
| 5 | [FGT-P-11872](../entities/part/fgt-p-11872.md) | [Gearbox](../entities/component/gearbox.md) [oil filter element](../entities/component/oil-filter.md), 10 micron | Fabrikam Getriebetechnik GmbH | Filters | pc | 14 | 12 | 24 | 0 |  |  | F-01-1 | Y |
| 6 | [FGT-P-11880](../entities/part/fgt-p-11880.md) | Gearbox breather with desiccant | Fabrikam Getriebetechnik GmbH | Filters | pc | 9 | 6 | 12 | 0 |  |  | F-01-2 | N |
| 7 | [FGT-P-13010](../entities/part/fgt-p-13010.md) | Oil level sight glass with seal | Fabrikam Getriebetechnik GmbH | Gearbox | pc | 2 | 2 | 2 | 0 |  |  | G-02-1 | N |
| 8 | [FGT-P-14002](../entities/part/fgt-p-14002.md) | Oil sampling valve with dust cap | Fabrikam Getriebetechnik GmbH | Gearbox | pc | 6 | 4 | 6 | 0 |  |  | G-02-2 | N |
| 9 | LWS-P-30418 | [Oil cooler fan motor](../entities/component/cooler-fan-motor.md) 1.5 kW | [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) | Electrical | pc | 1 | 2 | 2 | 2 | PO-77102 | 2026-08-14 | E-02-1 | Y |
| 10 | [LWS-P-30422](../entities/part/lws-p-30422.md) | [Oil cooler](../entities/component/oil-cooler.md) thermostatic valve insert | Litware Wind Systems | Gearbox | pc | 3 | 2 | 2 | 0 |  |  | G-03-1 | N |
| 11 | [LWS-P-51207](../entities/part/lws-p-51207.md) | Generator brush set (18 brushes) | Litware Wind Systems | Electrical | set | 3 | 2 | 4 | 0 |  |  | E-03-2 | N |
| 12 | [LWS-P-55031](../entities/part/lws-p-55031.md) | [Slip ring](../entities/component/slip-ring.md) cleaning kit | Litware Wind Systems | Electrical | kit | 4 | 2 | 4 | 0 |  |  | E-03-3 | N |
| 13 | [LWS-P-60455](../entities/part/lws-p-60455.md) | [Pitch bearing](../entities/component/pitch-bearing.md) bolt kit M30 10.9 (72 bolts) | Litware Wind Systems | Fasteners | kit | 2 | 1 | 2 | 0 |  |  | P-01-1 | N |
| 14 | [LWS-P-41120](../entities/part/lws-p-41120.md) | Yaw brake pad set | Litware Wind Systems | Mechanical | set | 4 | 2 | 4 | 0 |  |  | M-02-4 | N |
| 15 | [LWS-P-72210](../entities/part/lws-p-72210.md) | Hydraulic accumulator 4 L | Litware Wind Systems | Hydraulics | pc | 2 | 1 | 2 | 0 |  |  | H-01-1 | N |
| 16 | [LWS-P-80031](../entities/part/lws-p-80031.md) | Ice detection sensor | Litware Wind Systems | Sensors | pc | 2 | 1 | 1 | 0 |  |  | S-01-2 | N |
| 17 | [LWS-P-90012](../entities/part/lws-p-90012.md) | Nacelle hatch gas strut | Litware Wind Systems | Mechanical | pc | 4 | 2 | 4 | 0 |  |  | M-03-1 | N |
| 18 | [PWS-220-D208](../entities/part/pws-220-d208.md) | [Proseware PWG 220](../entities/product/pwg-220.md) gear oil, 208 L drum | [Proseware Lubricants](../entities/organisation/proseware-lubricants.md) | Lubricants | drum | 11 | 8 | 6 | 0 |  |  | L-01 | Y |
| 19 | PWS-320-D208 | Proseware PWG 320 gear oil, 208 L drum - do not use (MOC-2025-012) | Proseware Lubricants | Lubricants | drum | 1 | 0 | 0 | 0 |  |  | L-02 | N |
| 20 | [AWI-10442](../entities/part/awi-10442.md) | Hydraulic hose assembly DN12, 1.6 m (not stocked) | Adventure Works Industrial Supply | Hydraulics | pc | 0 | 0 | 0 | 0 |  |  | H-02-3 | N |
| 21 | [AWI-20915](../entities/part/awi-20915.md) | Spill kit refill, 50 L | Adventure Works Industrial Supply | HSE | kit | 5 | 4 | 6 | 0 |  |  | HSE-01 | N |
| 22 | [AWI-31007](../entities/part/awi-31007.md) | Tool tether set (10 lanyards) | Adventure Works Industrial Supply | HSE | set | 6 | 4 | 4 | 0 |  |  | HSE-02 | N |
| 23 | [AWI-40210](../entities/part/awi-40210.md) | Nitrile gloves, box of 100 | Adventure Works Industrial Supply | HSE | box | 18 | 10 | 20 | 0 |  |  | HSE-03 | N |
| 24 | AWI-40388 | Oil absorbent pads, pack of 200 | Adventure Works Industrial Supply | HSE | pack | 7 | 4 | 6 | 0 |  |  | HSE-04 | N |

Agents can query this table as `t01` with the `query_table` tool.

### Movements

The movements sheet is headed “Movements.”[^c16]

Recorded movements include a 2026-03-12 quantity -1 movement of [FGT-P-22328](../entities/part/fgt-p-22328.md) for [WTG-10](../entities/asset/wtg-10.md), a 2026-06-24 quantity -1 movement of [LWS-P-30418](../entities/part/lws-p-30418.md) for [WTG-07](../entities/asset/wtg-07.md), and a 2026-07-18 quantity -1 movement of [LWS-P-51207](../entities/part/lws-p-51207.md) for [WTG-09](../entities/asset/wtg-09.md).[^c6][^c7][^c8]

**Table t02** · sheet "Movements", rows 1–10

| Row | Date | Part number | Quantity | Reference | Turbine | By |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 2026-03-12 | FGT-P-22328 | -1 | WO-26-0187 | WTG-10 | Tomasz Lebrecht |
| 3 | 2026-04-02 | [AWI-31007](../entities/part/awi-31007.md) | -1 | WO-26-0203 | [WTG-11](../entities/asset/wtg-11.md) | Tomasz Lebrecht |
| 4 | 2026-04-14 | AWI-31007 | 4 | PO-76410 |  | Tomasz Lebrecht |
| 5 | 2026-05-04 | [LWS-P-60455](../entities/part/lws-p-60455.md) | -1 | WO-26-0301 | [WTG-01](../entities/asset/wtg-01.md) | Tomasz Lebrecht |
| 6 | 2026-06-08 | [FGT-P-14002](../entities/part/fgt-p-14002.md) | -1 | WO-26-0341 | WTG-01 | Tomasz Lebrecht |
| 7 | 2026-06-24 | LWS-P-30418 | -1 | WO-26-0398 | WTG-07 | Tomasz Lebrecht |
| 8 | 2026-06-30 | [PWS-220-D208](../entities/part/pws-220-d208.md) | 2 | PO-76988 |  | Tomasz Lebrecht |
| 9 | 2026-07-07 | [AWI-40388](../entities/part/awi-40388.md) | -1 | WO-26-0430 | WTG-01 | Tomasz Lebrecht |
| 10 | 2026-07-18 | LWS-P-51207 | -1 | WO-26-0436 | WTG-09 | Tomasz Lebrecht |

Agents can query this table as `t02` with the `query_table` tool.

### Suppliers

The suppliers sheet is headed “Suppliers.”[^c17]

[Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md) supplies [gearbox](../entities/component/gearbox.md) bearings, filters, and gearbox parts with a typical lead time of 10 weeks.[^c9] [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) supplies turbine spare parts and electrical parts with a typical lead time of 6 weeks.[^c10] [Proseware Lubricants](../entities/organisation/proseware-lubricants.md) supplies gear oil with a typical lead time of 3 weeks.[^c11] [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md) supplies consumables, hydraulic hoses, and HSE items with a typical lead time of 2 weeks.[^c12]

**Table t03** · sheet "Suppliers", rows 1–5

| Row | Supplier | Supplies | Typical lead time (weeks) | Ordering e-mail |
| --- | --- | --- | --- | --- |
| 2 | Fabrikam Getriebetechnik GmbH | Gearbox bearings, filters, gearbox parts | 10 | `orders@fabrikam-getriebe.example` |
| 3 | Litware Wind Systems | Turbine spare parts, electrical parts | 6 | `spares@litware-wind.example` |
| 4 | Proseware Lubricants | Gear oil | 3 | `orders@contoso-renewables.example` |
| 5 | Adventure Works Industrial Supply | Consumables, hydraulic hoses, HSE items | 2 | `orders@contoso-renewables.example` |

Agents can query this table as `t03` with the `query_table` tool.

### About

The about sheet is headed “About.”[^c18]

The workbook states that the data is fictional and not for operational use, and identifies the file as a spare-parts stock snapshot for the [Quellmoor Ridge O&M building](../entities/asset/om-building.md).[^c1]

The workbook states that a part is below its minimum level when On hand is lower than Minimum.[^c2]

The owner is Tomasz Lebrecht, Stores and Spare Parts Coordinator, [Contoso Renewables](../entities/organisation/contoso-renewables.md).[^c13]

**Table t04** · sheet "About", rows 1–5

| Row | FICTIONAL - NOT FOR OPERATIONAL USE |
| --- | --- |
| 2 | Spare parts stock of the Quellmoor Ridge O&M building, snapshot of 2026-07-21. |
| 3 | A part is below its minimum level when 'On hand' is lower than 'Minimum'. |
| 4 | Owner: Tomasz Lebrecht, Stores and Spare Parts Coordinator, Contoso Renewables. |
| 5 | FICTIONAL - NOT FOR OPERATIONAL USE |

Agents can query this table as `t04` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md)
- Components: [gearbox](../entities/component/gearbox.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [IMS bearing](../entities/component/ims-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [slip ring](../entities/component/slip-ring.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-20915](../entities/part/awi-20915.md), [AWI-31007](../entities/part/awi-31007.md), [AWI-40210](../entities/part/awi-40210.md), [AWI-40388](../entities/part/awi-40388.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-11880](../entities/part/fgt-p-11880.md), [FGT-P-13010](../entities/part/fgt-p-13010.md), [FGT-P-14002](../entities/part/fgt-p-14002.md), [FGT-P-21904](../entities/part/fgt-p-21904.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [FGT-P-22331](../entities/part/fgt-p-22331.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-30422](../entities/part/lws-p-30422.md), [LWS-P-41120](../entities/part/lws-p-41120.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [LWS-P-55031](../entities/part/lws-p-55031.md), [LWS-P-60455](../entities/part/lws-p-60455.md), [LWS-P-72210](../entities/part/lws-p-72210.md), [LWS-P-80031](../entities/part/lws-p-80031.md), [LWS-P-90012](../entities/part/lws-p-90012.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Organisations: [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md)
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-20915](../entities/part/awi-20915.md)
- [AWI-31007](../entities/part/awi-31007.md)
- [AWI-40210](../entities/part/awi-40210.md)
- [AWI-40388](../entities/part/awi-40388.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-11880](../entities/part/fgt-p-11880.md)
- [FGT-P-13010](../entities/part/fgt-p-13010.md)
- [FGT-P-14002](../entities/part/fgt-p-14002.md)
- [FGT-P-21904](../entities/part/fgt-p-21904.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [FGT-P-22331](../entities/part/fgt-p-22331.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [IMS bearing](../entities/component/ims-bearing.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-30422](../entities/part/lws-p-30422.md)
- [LWS-P-41120](../entities/part/lws-p-41120.md)
- [LWS-P-51207](../entities/part/lws-p-51207.md)
- [LWS-P-55031](../entities/part/lws-p-55031.md)
- [LWS-P-60455](../entities/part/lws-p-60455.md)
- [LWS-P-72210](../entities/part/lws-p-72210.md)
- [LWS-P-80031](../entities/part/lws-p-80031.md)
- [LWS-P-90012](../entities/part/lws-p-90012.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [pitch bearing](../entities/component/pitch-bearing.md)
- [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [PWS-320-D208](../entities/part/pws-320-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [slip ring](../entities/component/slip-ring.md)
- [Spare parts, stock levels and supply](../topics/spare-parts-and-supply.md)
- [WTG-01](../entities/asset/wtg-01.md)
- [WTG-07](../entities/asset/wtg-07.md)
- [WTG-09](../entities/asset/wtg-09.md)
- [WTG-10](../entities/asset/wtg-10.md)
- [WTG-11](../entities/asset/wtg-11.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 2](../evidence/src-42566abae6ef/sheet-about-r0002-r0002.md) · table
[^c2]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 3](../evidence/src-42566abae6ef/sheet-about-r0003-r0003.md) · table
[^c3]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 2](../evidence/src-42566abae6ef/sheet-stock-r0002-r0002.md) · table
[^c4]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 9](../evidence/src-42566abae6ef/sheet-stock-r0009-r0009.md) · table
[^c5]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 19](../evidence/src-42566abae6ef/sheet-stock-r0019-r0019.md) · table
[^c6]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Movements", row 2](../evidence/src-42566abae6ef/sheet-movements-r0002-r0002.md) · table
[^c7]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Movements", row 7](../evidence/src-42566abae6ef/sheet-movements-r0007-r0007.md) · table
[^c8]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Movements", row 10](../evidence/src-42566abae6ef/sheet-movements-r0010-r0010.md) · table
[^c9]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 2](../evidence/src-42566abae6ef/sheet-suppliers-r0002-r0002.md) · table
[^c10]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 3](../evidence/src-42566abae6ef/sheet-suppliers-r0003-r0003.md) · table
[^c11]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 4](../evidence/src-42566abae6ef/sheet-suppliers-r0004-r0004.md) · table
[^c12]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 5](../evidence/src-42566abae6ef/sheet-suppliers-r0005-r0005.md) · table
[^c13]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 4](../evidence/src-42566abae6ef/sheet-about-r0004-r0004.md) · table
[^c14]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 1](../evidence/src-42566abae6ef/sheet-stock-r0001-r0001.md) · table
[^c15]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 24](../evidence/src-42566abae6ef/sheet-stock-r0024-r0024.md) · table
[^c16]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Movements", row 1](../evidence/src-42566abae6ef/sheet-movements-r0001-r0001.md) · table
[^c17]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 1](../evidence/src-42566abae6ef/sheet-suppliers-r0001-r0001.md) · table
[^c18]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 1](../evidence/src-42566abae6ef/sheet-about-r0001-r0001.md) · table
