---
id: src-65680eb5afcc
type: source
title: KPI Export 2026-H1
summary: This CSV KPI export lists monthly turbine performance records for the first half of 2026. It covers WTG-01 through WTG-12 and includes availability, energy, downtime, and alarm-count fields.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- kpi-export
- records-and-data
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-65680eb5afcc
source_path: full/records/kpi-export-2026-H1.csv
source_hash: sha256:76d30f6cdf4038ecdea1e2bb1edb65ddac93ece8d5ea01e7d072b329284a4191
media_type: text/csv
doc_type: kpi-export
category: records-and-data
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
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
topics: []
authority: 4
extraction:
  adapter: local
  version: 1.0.0
  provenance_mix:
    deterministic-table: 72
---

# KPI Export 2026-H1

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This CSV KPI export lists monthly turbine performance records for the first half of 2026. It covers [WTG-01](../entities/asset/wtg-01.md) through [WTG-12](../entities/asset/wtg-12.md) and includes availability, energy, downtime, and alarm-count fields.

## Key facts

- The first listed record is for [WTG-01](../entities/asset/wtg-01.md) in 2026-01, with availability_pct 98.6, energy_mwh 952.7, downtime_h 10.4, and alarm_count 24.[^c1]
- [WTG-09](../entities/asset/wtg-09.md) in 2026-01 recorded availability_pct 96.1, energy_mwh 955.9, downtime_h 29.0, and alarm_count 15.[^c2]
- [WTG-12](../entities/asset/wtg-12.md) in 2026-02 recorded availability_pct 99.2, energy_mwh 811.8, downtime_h 5.4, and alarm_count 26.[^c3]
- [WTG-10](../entities/asset/wtg-10.md) in 2026-03 recorded availability_pct 93.8, energy_mwh 807.4, downtime_h 46.1, and alarm_count 24.[^c4]
- WTG-12 in 2026-04 recorded availability_pct 99.4, energy_mwh 688.1, downtime_h 4.3, and alarm_count 7.[^c5]
- [WTG-07](../entities/asset/wtg-07.md) in 2026-05 recorded availability_pct 95.2, energy_mwh 555.7, downtime_h 35.7, and alarm_count 31.[^c6]
- WTG-07 in 2026-06 recorded availability_pct 90.4, energy_mwh 386.5, downtime_h 69.1, and alarm_count 38.[^c7]
- For WTG-07, availability_pct changed from 95.2 in 2026-05 to 90.4 in 2026-06, while downtime_h changed from 35.7 to 69.1 and alarm_count changed from 31 to 38.[^c6][^c7]
- The last listed record is for WTG-12 in 2026-06, with availability_pct 97.8, energy_mwh 496.4, downtime_h 15.8, and alarm_count 14.[^c8]

## Contents

### Data set and fields

The KPI export is a table with the columns month, turbine, availability_pct, energy_mwh, downtime_h, and alarm_count.[^c9]

The records run from a 2026-01 entry for [WTG-01](../entities/asset/wtg-01.md) to a 2026-06 entry for [WTG-12](../entities/asset/wtg-12.md).[^c1][^c8]

**Table t01** · rows 1–73

| Row | month | turbine | availability_pct | energy_mwh | downtime_h | alarm_count |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | 2026-01 | WTG-01 | 98.6 | 952.7 | 10.4 | 24 |
| 3 | 2026-01 | [WTG-02](../entities/asset/wtg-02.md) | 98.6 | 976.3 | 10.4 | 12 |
| 4 | 2026-01 | [WTG-03](../entities/asset/wtg-03.md) | 97.5 | 910.4 | 18.6 | 22 |
| 5 | 2026-01 | [WTG-04](../entities/asset/wtg-04.md) | 98.1 | 948.8 | 14.1 | 6 |
| 6 | 2026-01 | [WTG-05](../entities/asset/wtg-05.md) | 98.7 | 936.6 | 9.7 | 6 |
| 7 | 2026-01 | [WTG-06](../entities/asset/wtg-06.md) | 99.3 | 928.0 | 5.2 | 6 |
| 8 | 2026-01 | [WTG-07](../entities/asset/wtg-07.md) | 97.5 | 933.3 | 18.6 | 20 |
| 9 | 2026-01 | [WTG-08](../entities/asset/wtg-08.md) | 97.9 | 911.6 | 15.6 | 12 |
| 10 | 2026-01 | [WTG-09](../entities/asset/wtg-09.md) | 96.1 | 955.9 | 29.0 | 15 |
| 11 | 2026-01 | [WTG-10](../entities/asset/wtg-10.md) | 98.4 | 992.2 | 11.9 | 19 |
| 12 | 2026-01 | [WTG-11](../entities/asset/wtg-11.md) | 97.8 | 986.6 | 16.4 | 15 |
| 13 | 2026-01 | WTG-12 | 97.9 | 957.0 | 15.6 | 17 |
| 14 | 2026-02 | WTG-01 | 97.9 | 791.8 | 14.1 | 18 |
| 15 | 2026-02 | WTG-02 | 98.4 | 815.6 | 10.8 | 17 |
| 16 | 2026-02 | WTG-03 | 99.1 | 774.7 | 6.0 | 26 |
| 17 | 2026-02 | WTG-04 | 97.7 | 791.1 | 15.5 | 25 |
| 18 | 2026-02 | WTG-05 | 97.7 | 776.1 | 15.5 | 19 |
| 19 | 2026-02 | WTG-06 | 98.6 | 771.4 | 9.4 | 14 |
| 20 | 2026-02 | WTG-07 | 99.3 | 795.8 | 4.7 | 11 |
| 21 | 2026-02 | WTG-08 | 98.4 | 767.0 | 10.8 | 23 |
| 22 | 2026-02 | WTG-09 | 97.7 | 813.5 | 15.5 | 20 |
| 23 | 2026-02 | WTG-10 | 98.3 | 829.8 | 11.4 | 15 |
| 24 | 2026-02 | WTG-11 | 98.8 | 834.4 | 8.1 | 25 |
| 25 | 2026-02 | WTG-12 | 99.2 | 811.8 | 5.4 | 26 |
| 26 | 2026-03 | WTG-01 | 98.4 | 811.6 | 11.9 | 26 |
| 27 | 2026-03 | WTG-02 | 99.1 | 837.6 | 6.7 | 22 |
| 28 | 2026-03 | WTG-03 | 97.6 | 778.0 | 17.9 | 15 |
| 29 | 2026-03 | WTG-04 | 98.0 | 809.2 | 14.9 | 13 |
| 30 | 2026-03 | WTG-05 | 98.1 | 794.7 | 14.1 | 14 |
| 31 | 2026-03 | WTG-06 | 99.1 | 790.6 | 6.7 | 14 |
| 32 | 2026-03 | WTG-07 | 99.1 | 809.8 | 6.7 | 16 |
| 33 | 2026-03 | WTG-08 | 98.8 | 785.4 | 8.9 | 21 |
| 34 | 2026-03 | WTG-09 | 98.7 | 838.1 | 9.7 | 22 |
| 35 | 2026-03 | WTG-10 | 93.8 | 807.4 | 46.1 | 24 |
| 36 | 2026-03 | WTG-11 | 99.3 | 855.2 | 5.2 | 18 |
| 37 | 2026-03 | WTG-12 | 98.1 | 818.6 | 14.1 | 11 |
| 38 | 2026-04 | WTG-01 | 98.8 | 676.0 | 8.6 | 24 |
| 39 | 2026-04 | WTG-02 | 98.3 | 689.2 | 12.2 | 23 |
| 40 | 2026-04 | WTG-03 | 98.4 | 650.6 | 11.5 | 26 |
| 41 | 2026-04 | WTG-04 | 97.7 | 669.1 | 16.6 | 26 |
| 42 | 2026-04 | WTG-05 | 98.2 | 659.8 | 13.0 | 22 |
| 43 | 2026-04 | WTG-06 | 97.6 | 645.9 | 17.3 | 24 |
| 44 | 2026-04 | WTG-07 | 97.6 | 661.6 | 17.3 | 21 |
| 45 | 2026-04 | WTG-08 | 98.3 | 648.2 | 12.2 | 23 |
| 46 | 2026-04 | WTG-09 | 99.3 | 699.4 | 5.0 | 17 |
| 47 | 2026-04 | WTG-10 | 99.2 | 708.3 | 5.8 | 11 |
| 48 | 2026-04 | WTG-11 | 99.1 | 707.9 | 6.5 | 25 |
| 49 | 2026-04 | WTG-12 | 99.4 | 688.1 | 4.3 | 7 |
| 50 | 2026-05 | WTG-01 | 98.2 | 578.5 | 13.4 | 25 |
| 51 | 2026-05 | WTG-02 | 97.8 | 590.5 | 16.4 | 16 |
| 52 | 2026-05 | WTG-03 | 99.2 | 564.8 | 6.0 | 8 |
| 53 | 2026-05 | WTG-04 | 99.2 | 585.0 | 6.0 | 16 |
| 54 | 2026-05 | WTG-05 | 97.5 | 564.1 | 18.6 | 8 |
| 55 | 2026-05 | WTG-06 | 97.9 | 557.9 | 15.6 | 19 |
| 56 | 2026-05 | WTG-07 | 95.2 | 555.7 | 35.7 | 31 |
| 57 | 2026-05 | WTG-08 | 97.6 | 554.2 | 17.9 | 9 |
| 58 | 2026-05 | WTG-09 | 99.0 | 600.4 | 7.4 | 13 |
| 59 | 2026-05 | WTG-10 | 98.3 | 604.4 | 12.6 | 10 |
| 60 | 2026-05 | WTG-11 | 98.3 | 604.7 | 12.6 | 15 |
| 61 | 2026-05 | WTG-12 | 97.6 | 581.8 | 17.9 | 8 |
| 62 | 2026-06 | WTG-01 | 98.1 | 492.2 | 13.7 | 11 |
| 63 | 2026-06 | WTG-02 | 98.2 | 504.9 | 13.0 | 23 |
| 64 | 2026-06 | WTG-03 | 99.1 | 480.5 | 6.5 | 6 |
| 65 | 2026-06 | WTG-04 | 98.2 | 493.2 | 13.0 | 6 |
| 66 | 2026-06 | WTG-05 | 98.6 | 485.8 | 10.1 | 11 |
| 67 | 2026-06 | WTG-06 | 98.7 | 479.0 | 9.4 | 19 |
| 68 | 2026-06 | WTG-07 | 90.4 | 386.5 | 69.1 | 38 |
| 69 | 2026-06 | WTG-08 | 98.2 | 474.8 | 13.0 | 6 |
| 70 | 2026-06 | WTG-09 | 97.6 | 504.1 | 17.3 | 14 |
| 71 | 2026-06 | WTG-10 | 99.1 | 518.9 | 6.5 | 16 |
| 72 | 2026-06 | WTG-11 | 97.5 | 510.8 | 18.0 | 18 |
| 73 | 2026-06 | WTG-12 | 97.8 | 496.4 | 15.8 | 14 |

Agents can query this table as `t01` with the `query_table` tool.

### Selected KPI records

- [WTG-09](../entities/asset/wtg-09.md) in 2026-01 recorded availability_pct 96.1, energy_mwh 955.9, downtime_h 29.0, and alarm_count 15.[^c2]
- [WTG-10](../entities/asset/wtg-10.md) in 2026-03 recorded availability_pct 93.8, energy_mwh 807.4, downtime_h 46.1, and alarm_count 24.[^c4]
- [WTG-12](../entities/asset/wtg-12.md) in 2026-04 recorded availability_pct 99.4, energy_mwh 688.1, downtime_h 4.3, and alarm_count 7.[^c5]
- [WTG-07](../entities/asset/wtg-07.md) in 2026-05 recorded availability_pct 95.2, energy_mwh 555.7, downtime_h 35.7, and alarm_count 31.[^c6]
- WTG-07 in 2026-06 recorded availability_pct 90.4, energy_mwh 386.5, downtime_h 69.1, and alarm_count 38.[^c7]

### WTG-07 May-to-June change

[WTG-07](../entities/asset/wtg-07.md) changed from availability_pct 95.2, downtime_h 35.7, and alarm_count 31 in 2026-05 to availability_pct 90.4, downtime_h 69.1, and alarm_count 38 in 2026-06.[^c6][^c7]

## Figures

No figures were extracted from this document.

## Related

- Assets: [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)

<!-- docwiki:backlinks:start -->
## Referenced by

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

[^c1]: [KPI Export 2026-H1 — row 2](../evidence/src-65680eb5afcc/r0002-r0002.md) · table
[^c2]: [KPI Export 2026-H1 — row 10](../evidence/src-65680eb5afcc/r0010-r0010.md) · table
[^c3]: [KPI Export 2026-H1 — row 25](../evidence/src-65680eb5afcc/r0025-r0025.md) · table
[^c4]: [KPI Export 2026-H1 — row 35](../evidence/src-65680eb5afcc/r0035-r0035.md) · table
[^c5]: [KPI Export 2026-H1 — row 49](../evidence/src-65680eb5afcc/r0049-r0049.md) · table
[^c6]: [KPI Export 2026-H1 — row 56](../evidence/src-65680eb5afcc/r0056-r0056.md) · table
[^c7]: [KPI Export 2026-H1 — row 68](../evidence/src-65680eb5afcc/r0068-r0068.md) · table
[^c8]: [KPI Export 2026-H1 — row 73](../evidence/src-65680eb5afcc/r0073-r0073.md) · table
[^c9]: [KPI Export 2026-H1 — rows 1–73](../evidence/src-65680eb5afcc/r0001-r0073.md) · table
