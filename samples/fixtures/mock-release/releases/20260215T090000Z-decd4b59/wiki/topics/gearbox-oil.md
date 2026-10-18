---
id: topic:gearbox-oil
type: topic
title: Gearbox oil
summary: Gearbox oil grade requirements, the cold-site change and the open plan contradiction.
lang: en
sensitivity: public
updated: 2026-02-15
tags:
- gearbox
- oil
docwiki:
  schema: 1
  release: 20260215T090000Z-decd4b59
topic_slug: gearbox-oil
sources:
- src-43c97f7dfcde
- src-4d9c65e05302
- src-f2750f41f3fa
confidence: medium
contradictions: 1
superseded_claims: 1
---

# Gearbox oil

> FICTIONAL - NOT FOR OPERATIONAL USE. Sample content about the fictional operator Contoso Renewables.

Gearbox oil grade requirements for the Contoso Renewables fleet, compiled from three sources.

## Overview

The current procedure requires ISO VG 220 gearbox oil at cold sites, where the ambient temperature can fall below -20 °C.[^c1]

## Oil grade by site

- Cold sites: ISO VG 220, with WTG-07 switching first.[^c1]
- The 2026 plan schedules oil changes with ISO VG 320 on WTG-07 and ISO VG 220 on WTG-12.[^c2]

## Contradictions

- **Oil grade for WTG-07.** [Maintenance plan 2026](../sources/maintenance-plan-2026.md) lists ISO VG 320 for the 2026-03 oil change on WTG-07[^c2] (authority 5), while [Gearbox oil change SOP rev B](../sources/sop-gbx-010-rev-b.md) requires ISO VG 220 at cold sites and names WTG-07 first[^c1] (authority 7). Resolution rule (authority, then recency): the procedure has the higher authority; the plan should be reviewed.

## Superseded information

- **Oil grade for all turbines.** [Gearbox oil change SOP rev A](../sources/sop-gbx-010-rev-a.md) specified ISO VG 320 for all turbines[^c3]; replaced by rev B, which requires ISO VG 220 at cold sites.[^c1] Superseding source: [Gearbox oil change SOP rev B](../sources/sop-gbx-010-rev-b.md).

## Sources consulted

- [Gearbox oil change SOP rev B](../sources/sop-gbx-010-rev-b.md): current, authority 7
- [Maintenance plan 2026](../sources/maintenance-plan-2026.md): current, authority 5
- [Gearbox oil change SOP rev A](../sources/sop-gbx-010-rev-a.md): superseded, authority 7

## Related

- Assets: [WTG-07](../entities/asset/wtg-07.md), [WTG-12](../entities/asset/wtg-12.md)
- Organisation: [Litware](../entities/organisation/litware.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Which gearbox oil grade applies to WTG-07 in winter?](../queries/2026-02-12-cold-site-gearbox-oil.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Gearbox oil change SOP rev B — ¶ 4](../evidence/src-4d9c65e05302/para-0004.md) · ✓ quote verified
[^c2]: [Maintenance plan 2026 — sheet "Plan", rows 2–4](../evidence/src-43c97f7dfcde/sheet-plan-r0002-r0004.md) · table
[^c3]: [Gearbox oil change SOP rev A — p. 1](../evidence/src-f2750f41f3fa/p0001.md) · ✓ quote verified
