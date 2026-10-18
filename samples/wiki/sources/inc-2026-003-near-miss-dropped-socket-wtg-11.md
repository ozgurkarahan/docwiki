---
id: src-52a23aeb488e
type: source
title: 'Near-miss Report INC-2026-003: Dropped Socket at WTG-11'
summary: This is a Contoso Renewables near-miss report for a dropped socket incident at WTG-11. It covers the event description, immediate actions, causes, corrective actions, and lessons learned.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- incidents
- near-miss-report
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-52a23aeb488e
source_path: full/incidents/INC-2026-003_near-miss-dropped-socket-WTG-11.pdf
source_hash: sha256:8b2d55e9f3c9ff928dd4b8314ec1cf21d53428b518f0be8b1635661e644d5e26
media_type: application/pdf
doc_type: near-miss-report
category: incidents
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: 1
entities:
- asset:wtg-11
- organisation:contoso-renewables
- part:awi-31007
- procedure:sop-wah-003
topics:
- topic:safety-and-access
- topic:training-and-onboarding
authority: 6
extraction:
  adapter: content-understanding
  version: 1.0.0+cu.2025-11-01
  provenance_mix:
    native-text: 29
---

# Near-miss Report INC-2026-003: Dropped Socket at WTG-11

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This is a [Contoso Renewables](../entities/organisation/contoso-renewables.md) near-miss report for a dropped socket incident at [WTG-11](../entities/asset/wtg-11.md). It covers the event description, immediate actions, causes, corrective actions, and lessons learned.

## Key facts

- The document is a [Contoso Renewables](../entities/organisation/contoso-renewables.md) incident management near-miss report numbered INC-2026-003 and titled "Dropped socket at [WTG-11](../entities/asset/wtg-11.md)."[^c1]
- The incident was recorded as occurring on 2026-03-24 at 10:40 at WTG-11, yaw deck hatch, and was classified as a near miss involving a dropped object with high potential severity.[^c1]
- The report was made by Callum Rydings, Lead Wind Technician, investigated by Greta Vollan, HSE Coordinator, and dated 2026-03-27.[^c1]
- During a 12-month service, a 24 mm impact socket weighing 0.4 kg slipped from a technician's hand at the yaw deck while tools were being passed through an open hatch.[^c1]
- The socket fell about 85 m inside the tower to the tower base platform; nobody was at the tower base because the exclusion zone was respected, there was no injury, and a cable tray cover was dented.[^c1]
- Immediate actions were to stop work, check the area, and hold a dropped-objects toolbox talk on 2026-03-26.[^c1]
- The identified causes were that the socket was not tethered, the hatch stayed open while tools were passed, and there was no tool tether anchor point at the yaw deck hatch.[^c1]
- Corrective action A1 requires installing tool tether anchor points at the yaw deck hatches, first at WTG-11 under WO-26-0203 and then on all turbines; Callum Rydings owns the open action due 2026-04-30.[^c1]
- Corrective action A2 requires making tool tethering mandatory above 2 m and updating [SOP-WAH-003](../entities/procedure/sop-wah-003.md); Greta Vollan owns the open action due 2026-04-15.[^c1]
- Corrective action A3, a toolbox talk on dropped objects owned by Dario Penwarden and due 2026-03-26, was completed.[^c1]
- Corrective action A4 requires ordering [AWI-31007](../entities/part/awi-31007.md) tool tether sets; Tomasz Lebrecht owns the open action due 2026-03-31.[^c1]
- The lesson learned was that exclusion zones under work at height are effective, and that tethering every tool and keeping hatches closed removes the hazard at its source.[^c1]

## Contents

### Document control and incident metadata

This is a [Contoso Renewables](../entities/organisation/contoso-renewables.md) incident management document.[^c2] It is a near-miss report numbered INC-2026-003 and titled “Dropped socket at [WTG-11](../entities/asset/wtg-11.md).”[^c2] The document is marked as fictional and not for operational use.[^c2]

The metadata table records the event date and time, location, classification, reporter, investigator, and report date.[^c2]

**Table t01** · p. 1

| Row | Field | Value |
| --- | --- | --- |
| 2 | Date and time | 2026-03-24 10:40 |
| 3 | Location | WTG-11, yaw deck hatch |
| 4 | Classification | Near miss - dropped object - potential severity high |
| 5 | Reported by | Callum Rydings, Lead Wind Technician |
| 6 | Investigated by | Greta Vollan, HSE Coordinator |
| 7 | Report date | 2026-03-27 |

Agents can query this table as `t01` with the `query_table` tool.

### Description

During the 12-month service, a 24 mm impact socket weighing 0.4 kg slipped from a technician’s hand at the yaw deck while tools were being passed through the open hatch.[^c2] It fell about 85 m inside the tower to the tower base platform.[^c2] Nobody was at the tower base because the exclusion zone had been respected.[^c2] There was no injury, and a cable tray cover was dented.[^c2]

### Immediate actions

- Work stopped and the area was checked.[^c2]
- A toolbox talk on dropped objects was held on 2026-03-26.[^c2]

### Causes

- The socket was not tethered.[^c2]
- The hatch stayed open while tools were passed.[^c2]
- There was no tool tether anchor point at the yaw deck hatch.[^c2]

### Actions

The action table lists four corrective actions, covering installation of tool tether anchor points, mandatory tool tethering and an [SOP-WAH-003](../entities/procedure/sop-wah-003.md) update, a dropped-objects toolbox talk, and ordering [AWI-31007](../entities/part/awi-31007.md) tool tether sets.[^c2] The table also records each action owner, due date, and status.[^c2]

**Table t02** · p. 1

| Row | ID | Action | Owner | Due | Status |
| --- | --- | --- | --- | --- | --- |
| 2 | A1 | Install tool tether anchor points at the yaw deck hatches ([WTG-11](../entities/asset/wtg-11.md) under WO-26-0203, then all turbines) | Callum Rydings | 2026-04-30 | open |
| 3 | A2 | Make tool tethering mandatory above 2 m and update SOP-WAH-003 | Greta Vollan | 2026-04-15 | open |
| 4 | A3 | Toolbox talk on dropped objects | Dario Penwarden | 2026-03-26 | done |
| 5 | A4 | Order tool tether sets AWI-31007 | Tomasz Lebrecht | 2026-03-31 | open |

Agents can query this table as `t02` with the `query_table` tool.

### Lessons learned

The report states that exclusion zones under work at height work.[^c2] It also states that tethering every tool and keeping hatches closed removes the hazard at its source.[^c2]

## Figures

No figures were extracted from this document.

## Related

- Asset: [WTG-11](../entities/asset/wtg-11.md)
- Spare part: [AWI-31007](../entities/part/awi-31007.md)
- Procedure: [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- Organisation: [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- Topics: [Safety, isolation and work at height](../topics/safety-and-access.md), [Training, site rules and acronyms](../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [AWI-31007](../entities/part/awi-31007.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Safety, isolation and work at height](../topics/safety-and-access.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [Training, site rules and acronyms](../topics/training-and-onboarding.md)
- [WTG-11](../entities/asset/wtg-11.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Near-miss Report INC-2026-003: Dropped Socket at WTG-11 — p. 1](../evidence/src-52a23aeb488e/p0001.md) · ✓ quote verified
[^c2]: [Near-miss Report INC-2026-003: Dropped Socket at WTG-11 — p. 1](../evidence/src-52a23aeb488e/p0001.md) · paraphrase
