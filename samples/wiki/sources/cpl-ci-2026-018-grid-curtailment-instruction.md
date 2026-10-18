---
id: src-867a6c78f5b5
type: source
title: Curtailment instruction CPL-CI-2026-018
summary: This City Power & Light Network Control instruction orders a planned curtailment for Quellmoor Ridge Wind Farm during a network outage. It gives the export limit schedule, ramp-rate condition, acknowledgement requirement, reporting threshold, and acknowledgement details.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- compliance
- grid-instruction
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-867a6c78f5b5
source_path: full/compliance/CPL-CI-2026-018_grid-curtailment-instruction.pdf
source_hash: sha256:98ec3e4b716e043f95d2793237906f16a632f66c9d8af4f8bad5aafda3bc0ec2
media_type: application/pdf
doc_type: grid-instruction
category: compliance
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: 1
entities:
- asset:quellmoor-ridge-wind-farm
- organisation:city-power-and-light
- organisation:contoso-renewables
topics:
- topic:environmental-compliance
- topic:grid-operations
authority: 9
extraction:
  adapter: content-understanding
  version: 1.0.0+cu.2025-11-01
  provenance_mix:
    native-text: 23
---

# Curtailment instruction CPL-CI-2026-018

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This [City Power & Light](../entities/organisation/city-power-and-light.md) Network Control instruction orders a planned curtailment for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md) during a network outage. It gives the export limit schedule, ramp-rate condition, acknowledgement requirement, reporting threshold, and acknowledgement details.

## Key facts

- The document is a [City Power & Light](../entities/organisation/city-power-and-light.md) Network Control curtailment instruction for a planned network outage, numbered CPL-CI-2026-018.[^c1]
- The document is marked fictional and not for operational use.[^c1]
- The instruction was issued on 2026-07-02 at 10:15.[^c1]
- The instruction is addressed to [Contoso Renewables](../entities/organisation/contoso-renewables.md) for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c1]
- The connection point is Skelvane 132 kV substation, circuit 2.[^c1]
- The reason for the instruction is planned maintenance of Skelvane 132 kV circuit 1 while the network runs on a single circuit.[^c1]
- Active power export at the connection point must be limited to 20 MW on 14, 15 and 16 July 2026, each day from 08:00 to 18:00 local time.[^c1]
- The export-limit schedule lists 20 MW from 08:00 to 18:00 on 2026-07-14.[^c1]
- The export-limit schedule lists 20 MW from 08:00 to 18:00 on 2026-07-15.[^c1]
- The export-limit schedule lists 20 MW from 08:00 to 18:00 on 2026-07-16.[^c1]
- When the limit ends, export must be restored with a ramp rate of at most 5 MW per minute.[^c1]
- The instruction must be acknowledged within 48 hours.[^c1]
- Export above the limit by more than 1 MW for more than 5 minutes will be reported.[^c1]
- Network Control may extend the outage, and any extension is confirmed by phone and in writing.[^c1]
- Dario Penwarden, O&M Supervisor, acknowledged the instruction for Contoso Renewables on 2026-07-02 at 14:40.[^c1]
- The Network Control duty engineer at City Power & Light is available 24/7.[^c1]

## Contents

### Document status

[City Power & Light](../entities/organisation/city-power-and-light.md) Network Control issued this document as curtailment instruction CPL-CI-2026-018 for a planned network outage.[^c2]

The document is marked fictional and not for operational use.[^c2]

### Outage context

The instruction was issued to [Contoso Renewables](../entities/organisation/contoso-renewables.md) for [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).[^c2]

The connection point is Skelvane 132 kV substation, circuit 2.[^c2]

The stated reason is planned maintenance of Skelvane 132 kV circuit 1, with the network [running](../entities/status-code/s100.md) on a single circuit.[^c2]

The source table contains the issued time, addressee, connection point, and reason.[^c2]

**Table t01** · p. 1

| Row | Field | Value |
| --- | --- | --- |
| 2 | Issued | 2026-07-02 10:15 |
| 3 | To | Contoso Renewables, Quellmoor Ridge Wind Farm |
| 4 | Connection point | Skelvane 132 kV substation, circuit 2 |
| 5 | Reason | Planned maintenance of Skelvane 132 kV circuit 1; the network runs on a single circuit |

Agents can query this table as `t01` with the `query_table` tool.

### Curtailment instruction

Active power export at the connection point must be limited to 20 MW on 14, 15 and 16 July 2026, each day from 08:00 to 18:00 local time.[^c2]

The export-limit table gives the daily entries for 2026-07-14, 2026-07-15, and 2026-07-16.[^c2]

When the limit ends, export must be restored with a ramp rate of at most 5 MW per minute.[^c2]

The instruction must be acknowledged within 48 hours.[^c2]

Export above the limit by more than 1 MW for more than 5 minutes will be reported.[^c2]

Network Control may extend the outage, and any extension is confirmed by phone and in writing.[^c2]

**Table t02** · p. 1

| Row | Date | From | To | Export limit |
| --- | --- | --- | --- | --- |
| 2 | 2026-07-14 | 08:00 | 18:00 | 20 MW |
| 3 | 2026-07-15 | 08:00 | 18:00 | 20 MW |
| 4 | 2026-07-16 | 08:00 | 18:00 | 20 MW |

Agents can query this table as `t02` with the `query_table` tool.

### Acknowledgement and contact

Dario Penwarden, O&M Supervisor, acknowledged the instruction for [Contoso Renewables](../entities/organisation/contoso-renewables.md) on 2026-07-02 at 14:40.[^c2]

The Network Control duty engineer at [City Power & Light](../entities/organisation/city-power-and-light.md) is available 24/7.[^c2]

## Figures

No figures were extracted from this document.

## Related

- Asset: [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- Topics: [Environmental permit and night curtailment](../topics/environmental-compliance.md), [Grid connection and grid operator instructions](../topics/grid-operations.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Environmental permit and night curtailment](../topics/environmental-compliance.md)
- [Grid connection and grid operator instructions](../topics/grid-operations.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Curtailment instruction CPL-CI-2026-018 — p. 1](../evidence/src-867a6c78f5b5/p0001.md) · ✓ quote verified
[^c2]: [Curtailment instruction CPL-CI-2026-018 — p. 1](../evidence/src-867a6c78f5b5/p0001.md) · paraphrase
