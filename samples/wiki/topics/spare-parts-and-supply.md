---
id: topic:spare-parts-and-supply
type: topic
title: Spare parts, stock levels and supply
summary: This page covers spare-parts stock, purchase orders, expected deliveries, and work orders waiting for parts.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- spare-parts-and-supply
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: spare-parts-and-supply
sources:
- src-15df96905f07
- src-1abc5aef1a40
- src-42566abae6ef
- src-86cb00fd2f6b
- src-9107d71821bf
- src-9fd435ef5956
- src-a20331a5431f
confidence: medium
contradictions: 3
superseded_claims: 0
---

# Spare parts, stock levels and supply

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers spare-parts stock, purchase orders, expected deliveries, and work orders waiting for parts.

## Overview

[HSS bearing](../entities/component/hss-bearing.md) [FGT-P-22328](../entities/part/fgt-p-22328.md) is a critical item below minimum stock, and [WTG-07](../entities/asset/wtg-07.md) and [WTG-02](../entities/asset/wtg-02.md) work orders are waiting for that part.[^c1][^c2][^c3][^c4] [Oil cooler fan motor](../entities/component/cooler-fan-motor.md) [LWS-P-30418](../entities/part/lws-p-30418.md) is also below minimum stock, with two units on order and no work order waiting for that motor.[^c1][^c5][^c6] Current sources disagree on PO-76994 delivery timing for FGT-P-22328: the stock snapshot lists expected delivery on 2026-09-25, the shortage email says week 39 from 21 to 25 September 2026, and the supplier note says the bearings cannot be delivered in week 39 and gives a confirmed window of 28.09.2026 to 02.10.2026.[^c1][^c2][^c7][^c8] The [gearbox](../entities/component/gearbox.md) oil conversion campaign from [PWG 320](../entities/product/pwg-320.md) to [PWG 220](../entities/product/pwg-220.md) is recorded as completed for [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md), while the stock entry for PWG 320 shows one do-not-use drum on hand with no reorder quantity and none on order.[^c9][^c10][^c11][^c12][^c13][^c14][^c15][^c16][^c17][^c18][^c19][^c20][^c21]

## HSS bearing shortage

- [FGT-P-22328](../entities/part/fgt-p-22328.md), the generator-side [HSS bearing](../entities/component/hss-bearing.md) for [FGT-3200](../entities/product/fgt-3200.md), is listed with 0 pc on hand, a minimum of 1 pc, a reorder quantity of 2 pc, and 2 pc on order under PO-76994.[^c1][^c2]
- WO-26-0412 for [WTG-07](../entities/asset/wtg-07.md) is waiting for parts to replace the generator-side HSS bearing, lists FGT-P-22328 quantity 1, and notes vibration above the 4.5 mm/s alarm level.[^c3]
- WO-26-0439 for [WTG-02](../entities/asset/wtg-02.md) is waiting for parts for a generator-side HSS bearing replacement after spalling was found at endoscopy on 2026-07-23, and it lists FGT-P-22328 quantity 1.[^c4]
- The WTG-07 8D report says the generator-side HSS bearing replacement under WO-26-0412 is waiting for parts and is planned on delivery of the bearing.[^c22]
- The last spare FGT-P-22328 bearing was used for the completed [WTG-10](../entities/asset/wtg-10.md) repair under WO-26-0187.[^c23]
- The stock snapshot lists a typical supplier lead time of 10 weeks for [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md).[^c24][^c25][^c26][^c27]

## PO-76994 delivery information

- The stock snapshot lists PO-76994 for 2 pc of [FGT-P-22328](../entities/part/fgt-p-22328.md) with expected delivery on 2026-09-25.[^c1][^c2]
- The shortage email says [Fabrikam](../entities/organisation/fabrikam-getriebetechnik.md) confirmed delivery of two FGT-P-22328 bearings in week 39, from 21 to 25 September 2026.[^c7]
- The supplier note says the two FGT-P-22328 bearings from PO-76994 cannot be delivered in calendar week 39 and gives a new confirmed delivery window of calendar week 40, from 28.09.2026 to 02.10.2026.[^c8]
- The shortage email says Fabrikam offered air freight for an extra EUR 2,300 that would bring the bearings forward by about two weeks, while the supplier note says air freight would no longer shorten the delivery time.[^c28][^c8]

## Oil cooler fan motor stock

- [LWS-P-30418](../entities/part/lws-p-30418.md), the 1.5 kW [oil cooler fan motor](../entities/component/cooler-fan-motor.md), is a critical item below minimum stock with 1 pc on hand, a minimum of 2 pc, a reorder quantity of 2 pc, and 2 pc on order under PO-77102 for expected delivery on 2026-08-14.[^c1][^c5]
- Minimum stock for fan motor LWS-P-30418 was raised from 1 to 2.[^c29]
- The stock movement records a 2026-06-24 issue of quantity -1 for LWS-P-30418 against WO-26-0398 for [WTG-07](../entities/asset/wtg-07.md).[^c30]
- The shortage email says two [oil cooler](../entities/component/oil-cooler.md) fan motors are on order under PO-77102 with an expected date of 14 August and that no work order is waiting for that motor.[^c6]

## Other work orders and supplied parts

- WO-26-0450 for [WTG-11](../entities/asset/wtg-11.md) is waiting for parts for a leaking hydraulic hose in the yaw brake circuit and lists part [AWI-10442](../entities/part/awi-10442.md) quantity 1.[^c31][^c32][^c33]
- WO-26-0355 for [WTG-04](../entities/asset/wtg-04.md) is planned high-priority corrective maintenance to replace [rotor blade](../entities/component/rotor-blade.md) B for a trailing-edge crack, with planned date 2026-09-08.[^c34]
- A new blade for WTG-04 was ordered from [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) for delivery at the end of August.[^c35]
- WO-26-0436 for [WTG-09](../entities/asset/wtg-09.md) replaced [generator brushes](../entities/component/generator-brushes.md), used part [LWS-P-51207](../entities/part/lws-p-51207.md) quantity 1, and the stock movements sheet records a 2026-07-18 issue of quantity -1 for LWS-P-51207 against that work order.[^c36][^c37]

## Gearbox oil and related stock

- MOC-2025-012 action 2 was to order 36 drums of [PWG 220](../entities/product/pwg-220.md) and set the minimum stock of [PWS-220-D208](../entities/part/pws-220-d208.md) to 8 drums.[^c38]
- The work-order export records the completed [gearbox](../entities/component/gearbox.md) oil conversion campaign from [PWG 320](../entities/product/pwg-320.md) to PWG 220 with a 60 L flush for [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md), with each row listing part PWS-220-D208 quantity 3.[^c9][^c10][^c11][^c12][^c13][^c14][^c15][^c16][^c17][^c18][^c19][^c20]
- [PWS-320-D208](../entities/part/pws-320-d208.md) is listed as Proseware PWG 320 gear oil in a 208 L drum with a do-not-use note tied to MOC-2025-012, 1 drum on hand, minimum 0, reorder quantity 0, and 0 on order.[^c21]
- The supplier note says that after switching from PWG 320 to PWG 220, [oil filter element](../entities/component/oil-filter.md) [FGT-P-11872](../entities/part/fgt-p-11872.md) is to be changed a second time after 500 operating hours, with an oil sample recommended at the same time.[^c39]

## Contradictions

- **PO-76994 delivery timing for [HSS bearing](../entities/component/hss-bearing.md) [FGT-P-22328](../entities/part/fgt-p-22328.md): stock snapshot versus supplier note.** [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md) states: FGT-P-22328, the HSS bearing on the [generator](../entities/component/generator.md) side for [FGT-3200](../entities/product/fgt-3200.md), is a critical item below minimum stock: 0 pc on hand, minimum 1 pc, reorder quantity 2 pc, and 2 pc on order under PO-76994 for expected delivery on 2026-09-25.[^c1][^c2] (authority 5, dated 2026-07-21). [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md) states: The two HSS bearings FGT-P-22328 from PO-76994 cannot be delivered in calendar week 39.[^c8] The new confirmed delivery window is calendar week 40, from 28.09.2026 to 02.10.2026.[^c8] (authority 3, date unknown). Resolution rule (authority, then recency): Spare Parts Stock Snapshot 2026-07-21 for [Quellmoor Ridge O&M Building](../entities/asset/om-building.md) prevails (authority 5 vs 3).
- **PO-76994 delivery timing for HSS bearing FGT-P-22328: shortage email versus supplier note.** [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../sources/2026-07-22-parts-shortage-hss-bearing.md) states: The last HSS bearing was used on [WTG-10](../entities/asset/wtg-10.md) in March under WO-26-0187, and [Fabrikam](../entities/organisation/fabrikam-getriebetechnik.md) confirmed delivery of two bearings in week 39, from 21 to 25 September 2026.[^c7] (authority 3, dated 2026-07-22). [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md) states: The two HSS bearings FGT-P-22328 from PO-76994 cannot be delivered in calendar week 39.[^c8] The new confirmed delivery window is calendar week 40, from 28.09.2026 to 02.10.2026.[^c8] (authority 3, date unknown). Resolution rule (authority, then recency): the rule does not decide between them (same authority and no usable dates); review both sources.
- **Whether air freight can shorten PO-76994 delivery time.** [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../sources/2026-07-22-parts-shortage-hss-bearing.md) states: Fabrikam offered air freight for an extra EUR 2,300, which would bring the bearings forward by about two weeks, and Tomasz asked whether to accept it.[^c28] (authority 3, dated 2026-07-22). [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md) states: The stated delivery-delay reason is a delay in heat treatment of the outer rings, and air freight would no longer shorten the delivery time.[^c8] (authority 3, date unknown). Resolution rule (authority, then recency): the rule does not decide between them (same authority and no usable dates); review both sources.

Resolution policy: When two current sources disagree, the source with the higher document-type authority wins (environmental permit 10; service bulletin and grid instruction 9; maintenance manual and management of change 8; procedures, laboratory and inspection reports 7). With equal authority the more recent source wins. A service bulletin that amends a manual section for some turbines is shown next to the manual value, with the turbines it applies to.

## Superseded information

No superseded information.

## Sources consulted

- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md): current, authority 8, dated 2025-06-18
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md): current, authority 6, dated 2026-07-10
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md): current, authority 5, dated 2026-07-21
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md): current, authority 5, date unknown
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md): current, authority 4, dated 2026-06-18
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md): current, authority 3, date unknown
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../sources/2026-07-22-parts-shortage-hss-bearing.md): current, authority 3, dated 2026-07-22

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [IMS bearing](../entities/component/ims-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [slip ring](../entities/component/slip-ring.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-20915](../entities/part/awi-20915.md), [AWI-31007](../entities/part/awi-31007.md), [AWI-40210](../entities/part/awi-40210.md), [AWI-40388](../entities/part/awi-40388.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-11880](../entities/part/fgt-p-11880.md), [FGT-P-13010](../entities/part/fgt-p-13010.md), [FGT-P-14002](../entities/part/fgt-p-14002.md), [FGT-P-21904](../entities/part/fgt-p-21904.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [FGT-P-22331](../entities/part/fgt-p-22331.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-30422](../entities/part/lws-p-30422.md), [LWS-P-41120](../entities/part/lws-p-41120.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [LWS-P-55031](../entities/part/lws-p-55031.md), [LWS-P-60455](../entities/part/lws-p-60455.md), [LWS-P-72210](../entities/part/lws-p-72210.md), [LWS-P-80031](../entities/part/lws-p-80031.md), [LWS-P-90012](../entities/part/lws-p-90012.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- Status code: [S100 Running](../entities/status-code/s100.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletins: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md), [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Organisations: [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md), [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md), [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- [Adventure Works Industrial Supply](../entities/organisation/adventure-works-industrial-supply.md)
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-20915](../entities/part/awi-20915.md)
- [AWI-31007](../entities/part/awi-31007.md)
- [AWI-40210](../entities/part/awi-40210.md)
- [AWI-40388](../entities/part/awi-40388.md)
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-11880](../entities/part/fgt-p-11880.md)
- [FGT-P-13010](../entities/part/fgt-p-13010.md)
- [FGT-P-14002](../entities/part/fgt-p-14002.md)
- [FGT-P-21904](../entities/part/fgt-p-21904.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [FGT-P-22331](../entities/part/fgt-p-22331.md)
- [gearbox](../entities/component/gearbox.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
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
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Parts shortage - HSS bearing FGT-P-22328 below minimum stock](../sources/2026-07-22-parts-shortage-hss-bearing.md)
- [pitch bearing](../entities/component/pitch-bearing.md)
- [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [PWS-320-D208](../entities/part/pws-320-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [S100 Running](../entities/status-code/s100.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../sources/spare-parts-stock-2026-07-21.md)
- [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)
- [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)
- [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md)
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

[^c1]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "About", row 3](../evidence/src-42566abae6ef/sheet-about-r0003-r0003.md) · table
[^c2]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 2](../evidence/src-42566abae6ef/sheet-stock-r0002-r0002.md) · table
[^c3]: [Work Orders Export through 2026-08-31 — row 73](../evidence/src-9fd435ef5956/r0073-r0073.md) · table
[^c4]: [Work Orders Export through 2026-08-31 — row 80](../evidence/src-9fd435ef5956/r0080-r0080.md) · table
[^c5]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 9](../evidence/src-42566abae6ef/sheet-stock-r0009-r0009.md) · table
[^c6]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 18–20](../evidence/src-9107d71821bf/msg-body-l0018-l0020.md) · ✓ quote verified
[^c7]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 10–12](../evidence/src-9107d71821bf/msg-body-l0010-l0012.md) · ✓ quote verified
[^c8]: [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up — lines 8–11](../evidence/src-1abc5aef1a40/l0008-l0011.md) · ✓ quote verified
[^c9]: [Work Orders Export through 2026-08-31 — row 2](../evidence/src-9fd435ef5956/r0002-r0002.md) · table
[^c10]: [Work Orders Export through 2026-08-31 — row 3](../evidence/src-9fd435ef5956/r0003-r0003.md) · table
[^c11]: [Work Orders Export through 2026-08-31 — row 4](../evidence/src-9fd435ef5956/r0004-r0004.md) · table
[^c12]: [Work Orders Export through 2026-08-31 — row 5](../evidence/src-9fd435ef5956/r0005-r0005.md) · table
[^c13]: [Work Orders Export through 2026-08-31 — row 6](../evidence/src-9fd435ef5956/r0006-r0006.md) · table
[^c14]: [Work Orders Export through 2026-08-31 — row 7](../evidence/src-9fd435ef5956/r0007-r0007.md) · table
[^c15]: [Work Orders Export through 2026-08-31 — row 8](../evidence/src-9fd435ef5956/r0008-r0008.md) · table
[^c16]: [Work Orders Export through 2026-08-31 — row 9](../evidence/src-9fd435ef5956/r0009-r0009.md) · table
[^c17]: [Work Orders Export through 2026-08-31 — row 10](../evidence/src-9fd435ef5956/r0010-r0010.md) · table
[^c18]: [Work Orders Export through 2026-08-31 — row 11](../evidence/src-9fd435ef5956/r0011-r0011.md) · table
[^c19]: [Work Orders Export through 2026-08-31 — row 12](../evidence/src-9fd435ef5956/r0012-r0012.md) · table
[^c20]: [Work Orders Export through 2026-08-31 — row 13](../evidence/src-9fd435ef5956/r0013-r0013.md) · table
[^c21]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Stock", row 19](../evidence/src-42566abae6ef/sheet-stock-r0019-r0019.md) · table
[^c22]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 2, row 5](../evidence/src-86cb00fd2f6b/tbl-02-r0005-r0005.md) · table
[^c23]: [Work Orders Export through 2026-08-31 — row 38](../evidence/src-9fd435ef5956/r0038-r0038.md) · table
[^c24]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 2](../evidence/src-42566abae6ef/sheet-suppliers-r0002-r0002.md) · table
[^c25]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 3](../evidence/src-42566abae6ef/sheet-suppliers-r0003-r0003.md) · table
[^c26]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 4](../evidence/src-42566abae6ef/sheet-suppliers-r0004-r0004.md) · table
[^c27]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Suppliers", row 5](../evidence/src-42566abae6ef/sheet-suppliers-r0005-r0005.md) · table
[^c28]: [Parts shortage - HSS bearing FGT-P-22328 below minimum stock — message body, lines 22–23](../evidence/src-9107d71821bf/msg-body-l0022-l0023.md) · ✓ quote verified
[^c29]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — ¶ 22](../evidence/src-86cb00fd2f6b/para-0022.md) · ✓ quote verified
[^c30]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Movements", row 7](../evidence/src-42566abae6ef/sheet-movements-r0007-r0007.md) · table
[^c31]: [Work Orders Export through 2026-08-31 — row 82](../evidence/src-9fd435ef5956/r0082-r0082.md) · table
[^c32]: [Work Orders Export through 2026-08-31 — row 83](../evidence/src-9fd435ef5956/r0083-r0083.md) · table
[^c33]: [Work Orders Export through 2026-08-31 — row 86](../evidence/src-9fd435ef5956/r0086-r0086.md) · table
[^c34]: [Work Orders Export through 2026-08-31 — row 68](../evidence/src-9fd435ef5956/r0068-r0068.md) · table
[^c35]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 12](../evidence/src-15df96905f07/para-0012.md) · ✓ quote verified
[^c36]: [Work Orders Export through 2026-08-31 — row 78](../evidence/src-9fd435ef5956/r0078-r0078.md) · table
[^c37]: [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building — sheet "Movements", row 10](../evidence/src-42566abae6ef/sheet-movements-r0010-r0010.md) · table
[^c38]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — table 3, row 3](../evidence/src-a20331a5431f/tbl-03-r0003-r0003.md) · table
[^c39]: [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up — lines 13–15](../evidence/src-1abc5aef1a40/l0013-l0015.md) · ✓ quote verified
