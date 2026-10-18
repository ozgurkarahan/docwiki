---
id: src-b342a2d5bfdf
type: source
title: Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12
summary: This is a fictional 2026 asset register for Quellmoor Ridge Wind Farm. It lists turbine asset details, other site assets, ownership, and notes on the coordinate system.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- asset-register
- records-and-data
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-b342a2d5bfdf
source_path: full/records/asset-register-2026.xlsx
source_hash: sha256:68297eed944642640f70abd4b22fb6dbeb26fdad08d7c26dd78471ebe7cdfe81
media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
doc_type: asset-register
category: records-and-data
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- asset:mm-01
- asset:om-building
- asset:quellmoor-ridge-substation
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
- organisation:city-power-and-light
- organisation:contoso-renewables
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- product:fgt-3200
- product:lt-32
- product:pwg-220
topics:
- topic:grid-operations
authority: 6
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    deterministic-table: 22
---

# Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This is a fictional 2026 asset register for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md). It lists turbine asset details, other site assets, ownership, and notes on the coordinate system.

## Key facts

- The document identifies itself as the Asset register 2026 of [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), revision 2026-01-12, and is marked fictional and not for operational use.[^c1]
- The register owner is Yusuf Arkwell, Reliability Engineer at [Contoso Renewables](../entities/organisation/contoso-renewables.md).[^c2]
- The coordinate values in the register are in metres on the local site grid used by the site layout plan.[^c3]
- All turbine entries are [Litware LT-32](../entities/product/lt-32.md) CCV turbines with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearboxes, Hub height (m) 92, and Rotor diameter (m) 118.[^c4][^c5][^c6][^c7][^c8][^c9][^c10][^c11][^c12][^c13][^c14][^c15]
- [WTG-09](../entities/asset/wtg-09.md) has [gearbox](../entities/component/gearbox.md) oil conversion to [PWG 220](../entities/product/pwg-220.md) pending and deferred under [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md).[^c12]
- The [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md) is a 33/132 kV substation with one 45 MVA transformer, located next to the O&M building, with connection to [City Power & Light](../entities/organisation/city-power-and-light.md), Skelvane 132 kV substation, circuit 2.[^c16]
- [MM-01 met mast](../entities/asset/mm-01.md) is a 92 m meteorological mast located north of [WTG-01](../entities/asset/wtg-01.md) and is the reference for power curve tests.[^c17]
- The [Quellmoor Ridge O&M building](../entities/asset/om-building.md) is the site office, workshop and stores at the site entrance, and its notes identify a bunded oil drum store.[^c18]

## Contents

### Turbines

The sheet heading is “Turbines.”[^c19]

The rendered table for this section contains the turbine asset rows from [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md).[^c4][^c15]

**Table t01** · sheet "Turbines", rows 1–13

| Row | Turbine | Serial number | Model | Variant | [Gearbox](../entities/component/gearbox.md) model | Gearbox serial | Commissioned | Hub height (m) | Rotor diameter (m) | Easting (m) | Northing (m) | Elevation (m) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | WTG-01 | LT32-19-0412 | [Litware LT-32](../entities/product/lt-32.md) | CCV | [Fabrikam FGT-3200](../entities/product/fgt-3200.md) | FGT-3200-18-07731 | 2019-08-26 | 92 | 118 | 1210 | 3480 | 452 | Gearbox oil [PWG 220](../entities/product/pwg-220.md) since 2025-09-03 |
| 3 | [WTG-02](../entities/asset/wtg-02.md) | LT32-19-0413 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-18-07734 | 2019-08-29 | 92 | 118 | 1640 | 3335 | 461 | Gearbox oil PWG 220 since 2025-09-10 |
| 4 | [WTG-03](../entities/asset/wtg-03.md) | LT32-19-0415 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-18-07738 | 2019-09-03 | 92 | 118 | 2075 | 3190 | 474 | Gearbox oil PWG 220 since 2025-09-17 |
| 5 | [WTG-04](../entities/asset/wtg-04.md) | LT32-19-0416 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-18-07740 | 2019-09-05 | 92 | 118 | 2510 | 3060 | 478 | Gearbox oil PWG 220 since 2025-09-24 |
| 6 | [WTG-05](../entities/asset/wtg-05.md) | LT32-19-0418 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-18-07745 | 2019-09-10 | 92 | 118 | 2950 | 2935 | 470 | Gearbox oil PWG 220 since 2025-10-01 |
| 7 | [WTG-06](../entities/asset/wtg-06.md) | LT32-19-0419 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-18-07747 | 2019-09-12 | 92 | 118 | 3390 | 2805 | 463 | Gearbox oil PWG 220 since 2025-10-08 |
| 8 | [WTG-07](../entities/asset/wtg-07.md) | LT32-19-0421 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-18-07752 | 2019-09-17 | 92 | 118 | 1385 | 2760 | 441 | Gearbox oil PWG 220 since 2025-10-15 |
| 9 | [WTG-08](../entities/asset/wtg-08.md) | LT32-19-0422 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-18-07755 | 2019-09-19 | 92 | 118 | 1815 | 2620 | 437 | Gearbox oil PWG 220 since 2025-10-22 |
| 10 | [WTG-09](../entities/asset/wtg-09.md) | LT32-19-0424 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-19-07760 | 2019-09-24 | 92 | 118 | 2250 | 2480 | 429 | Gearbox oil conversion to PWG 220 pending (deferred, [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md)) |
| 11 | [WTG-10](../entities/asset/wtg-10.md) | LT32-19-0425 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-19-07763 | 2019-09-26 | 92 | 118 | 2690 | 2345 | 424 | Gearbox oil PWG 220 since 2025-11-05 |
| 12 | [WTG-11](../entities/asset/wtg-11.md) | LT32-19-0427 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-19-07768 | 2019-10-01 | 92 | 118 | 3125 | 2210 | 418 | Gearbox oil PWG 220 since 2025-11-12 |
| 13 | WTG-12 | LT32-19-0428 | Litware LT-32 | CCV | Fabrikam FGT-3200 | FGT-3200-19-07771 | 2019-10-03 | 92 | 118 | 3560 | 2075 | 412 | Gearbox oil PWG 220 since 2025-11-19 |

Agents can query this table as `t01` with the `query_table` tool.

### Other assets

The sheet heading is “Other assets.”[^c20]

The rendered table for this section lists the [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md), [MM-01 met mast](../entities/asset/mm-01.md), and [Quellmoor Ridge O&M building](../entities/asset/om-building.md).[^c16][^c17][^c18]

**Table t02** · sheet "Other assets", rows 1–4

| Row | Asset | Description | Location | Notes |
| --- | --- | --- | --- | --- |
| 2 | Quellmoor Ridge substation | 33/132 kV substation, one 45 MVA transformer | next to the O&M building | Connection to [City Power & Light](../entities/organisation/city-power-and-light.md), Skelvane 132 kV substation, circuit 2 |
| 3 | MM-01 met mast | 92 m meteorological mast | north of [WTG-01](../entities/asset/wtg-01.md) | Reference for power curve tests |
| 4 | Quellmoor Ridge O&M building | Site office, workshop and stores | site entrance | Bunded oil drum store |

Agents can query this table as `t02` with the `query_table` tool.

### About

The About sheet identifies the register as “Asset register 2026 of [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md) (revision 2026-01-12).”[^c1]

It names the owner as “Yusuf Arkwell, Reliability Engineer, [Contoso Renewables](../entities/organisation/contoso-renewables.md).”[^c2]

It states that coordinates are in metres on the local site grid used by the site layout plan.[^c3]

The sheet includes the statement “FICTIONAL - NOT FOR OPERATIONAL USE.”[^c21]

**Table t03** · sheet "About", rows 1–5

| Row | FICTIONAL - NOT FOR OPERATIONAL USE |
| --- | --- |
| 2 | Asset register 2026 of Quellmoor Ridge Wind Farm (revision 2026-01-12). |
| 3 | Owner: Yusuf Arkwell, Reliability Engineer, Contoso Renewables. |
| 4 | Coordinates are in metres on the local site grid used by the site layout plan. |
| 5 | FICTIONAL - NOT FOR OPERATIONAL USE |

Agents can query this table as `t03` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [MM-01 met mast](../entities/asset/mm-01.md), [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Component: [gearbox](../entities/component/gearbox.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [Proseware PWG 220](../entities/product/pwg-220.md)
- Service bulletin: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- Topic: [Grid connection and grid operator instructions](../topics/grid-operations.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [gearbox](../entities/component/gearbox.md)
- [Grid connection and grid operator instructions](../topics/grid-operations.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [MM-01 met mast](../entities/asset/mm-01.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md)
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

[^c1]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "About", row 2](../evidence/src-b342a2d5bfdf/sheet-about-r0002-r0002.md) · table
[^c2]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "About", row 3](../evidence/src-b342a2d5bfdf/sheet-about-r0003-r0003.md) · table
[^c3]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "About", row 4](../evidence/src-b342a2d5bfdf/sheet-about-r0004-r0004.md) · table
[^c4]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 2](../evidence/src-b342a2d5bfdf/sheet-turbines-r0002-r0002.md) · table
[^c5]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 3](../evidence/src-b342a2d5bfdf/sheet-turbines-r0003-r0003.md) · table
[^c6]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 4](../evidence/src-b342a2d5bfdf/sheet-turbines-r0004-r0004.md) · table
[^c7]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 5](../evidence/src-b342a2d5bfdf/sheet-turbines-r0005-r0005.md) · table
[^c8]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 6](../evidence/src-b342a2d5bfdf/sheet-turbines-r0006-r0006.md) · table
[^c9]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 7](../evidence/src-b342a2d5bfdf/sheet-turbines-r0007-r0007.md) · table
[^c10]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 8](../evidence/src-b342a2d5bfdf/sheet-turbines-r0008-r0008.md) · table
[^c11]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 9](../evidence/src-b342a2d5bfdf/sheet-turbines-r0009-r0009.md) · table
[^c12]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 10](../evidence/src-b342a2d5bfdf/sheet-turbines-r0010-r0010.md) · table
[^c13]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 11](../evidence/src-b342a2d5bfdf/sheet-turbines-r0011-r0011.md) · table
[^c14]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 12](../evidence/src-b342a2d5bfdf/sheet-turbines-r0012-r0012.md) · table
[^c15]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 13](../evidence/src-b342a2d5bfdf/sheet-turbines-r0013-r0013.md) · table
[^c16]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Other assets", row 2](../evidence/src-b342a2d5bfdf/sheet-other-assets-r0002-r0002.md) · table
[^c17]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Other assets", row 3](../evidence/src-b342a2d5bfdf/sheet-other-assets-r0003-r0003.md) · table
[^c18]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Other assets", row 4](../evidence/src-b342a2d5bfdf/sheet-other-assets-r0004-r0004.md) · table
[^c19]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 1](../evidence/src-b342a2d5bfdf/sheet-turbines-r0001-r0001.md) · table
[^c20]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Other assets", row 1](../evidence/src-b342a2d5bfdf/sheet-other-assets-r0001-r0001.md) · table
[^c21]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "About", row 5](../evidence/src-b342a2d5bfdf/sheet-about-r0005-r0005.md) · table
