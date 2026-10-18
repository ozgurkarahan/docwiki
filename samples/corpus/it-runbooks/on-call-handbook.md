FICTIONAL - NOT FOR OPERATIONAL USE

# Relecloud on-call handbook

Owner: Oskar Vennholm, Site Reliability Engineering Lead. Last review: 2026-01-19.

## Rotations

- sre-primary and sre-secondary: weekly, handover on Monday at 10:00.
- dba-primary: weekly, handover on Tuesday at 10:00.
- business-hours: Monday to Friday, 08:00 to 18:00.

## Severity levels

| Severity | Definition | Acknowledge within | Incident commander |
|---|---|---|---|
| SEV1 | Tier 1 service down or data loss | 5 minutes | within 15 minutes |
| SEV2 | Tier 1 service degraded or tier 2 service down | 15 minutes | within 30 minutes |
| SEV3 | Minor degradation without customer impact | 1 hour | not required |
| SEV4 | Cosmetic or internal only | next business day | not required |

## During an incident

1. Acknowledge the page and open an incident channel.
2. For SEV1 and SEV2, name an incident commander; the commander decides on rollbacks and failovers (for orders-db see PRC-DB-007).
3. Post a status update every 30 minutes for SEV1 and every hour for SEV2.
4. Keep a timeline; it becomes the basis of the postmortem.

## After an incident

- A blameless postmortem is written within 5 working days for every SEV1 and SEV2.
- Action items get an owner and a due date and are reviewed weekly.

## Escalation

On-call SRE, then the database administrator on call (dba-primary), then the engineering manager (Jun Hallgarth) for SEV1.

FICTIONAL - NOT FOR OPERATIONAL USE
