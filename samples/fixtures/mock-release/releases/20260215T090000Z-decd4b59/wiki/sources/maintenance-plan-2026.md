---
id: src-43c97f7dfcde
type: source
title: Maintenance plan 2026
summary: Fictional 2026 maintenance plan listing planned tasks per turbine.
lang: en
sensitivity: public
updated: 2026-02-15
tags:
- maintenance
- plan
docwiki:
  schema: 1
  release: 20260215T090000Z-decd4b59
source_id: src-43c97f7dfcde
source_path: records/maintenance-plan-2026.xlsx
source_hash: sha256:547eeaad80cc9f73e634445f7b5744579739b8423dd2dbf30ecea3acf9b0b46f
media_type: application/vnd.openxmlformats-officedocument.spreadsheetml.sheet
doc_type: maintenance-plan
category: records
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: null
entities:
- asset:wtg-07
- asset:wtg-12
topics:
- topic:gearbox-oil
authority: 5
extraction:
  adapter: local
  version: mock-1
  provenance_mix:
    deterministic-table: 4
---

# Maintenance plan 2026

> FICTIONAL - NOT FOR OPERATIONAL USE. Sample content about the fictional operator Contoso Renewables.

The 2026 maintenance plan lists the planned tasks per turbine in the sheet "Plan".

## Key facts

- WTG-07 has a gearbox oil change planned for 2026-03 with ISO VG 320 oil (6 hours).[^c1]
- WTG-12 has a gearbox oil change planned for 2026-05 with ISO VG 220 oil (6 hours).[^c1]

## Contents

### Sheet "Plan"

| Row | Asset | Task | Oil grade | Due | Hours |
| --- | --- | --- | --- | --- | --- |
| 2 | WTG-07 | Gearbox oil change | ISO VG 320 | 2026-03 | 6 |
| 3 | WTG-07 | Vibration check |  | 2026-04 | 2 |
| 4 | WTG-12 | Gearbox oil change | ISO VG 220 | 2026-05 | 6 |

Agents can query this table as `t01` with the `query_table` tool.

## Figures

No figures were extracted from this document.

## Related

- Assets: [WTG-07](../entities/asset/wtg-07.md), [WTG-12](../entities/asset/wtg-12.md)
- Topic: [Gearbox oil](../topics/gearbox-oil.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Gearbox oil](../topics/gearbox-oil.md)
- [Which gearbox oil grade applies to WTG-07 in winter?](../queries/2026-02-12-cold-site-gearbox-oil.md)
- [WTG-07](../entities/asset/wtg-07.md)
- [WTG-12](../entities/asset/wtg-12.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Maintenance plan 2026 — sheet "Plan", rows 2–4](../evidence/src-43c97f7dfcde/sheet-plan-r0002-r0004.md) · table
