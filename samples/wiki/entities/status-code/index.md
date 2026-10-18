---
id: index:entities/status-code
type: index
title: Status codes
summary: SCADA status codes of the turbines.
lang: en
sensitivity: public
updated: 2026-10-18
tags: []
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
---

# Status codes

SCADA status codes of the turbines.

- [S100 Running](s100.md): S100 Running is a status code for WTG-07, which continues running with vibration above the alarm level. Yusuf requested weekly vibration reviews.
- [S200 Ready - low wind](s200.md): S200 Ready - low wind is a status code used for WTG-01 through WTG-12. The status was recorded on 2026-04-10, 2026-07-24, and 2026-08-23. It started when wind speed was low and ended later at higher wind speeds.
- [S310 Maintenance mode](s310.md): S310 is the status code for Maintenance mode. It is used in wind turbine lockout/tagout and SCADA status logs.
- [S420 Curtailed - environmental condition](s420.md): S420 Curtailed - environmental condition is a status code used by WTG-03, WTG-04, and WTG-05. In the SCADA alarm and status log, these turbines were in S420 Curtailed - environmental condition from around 22:00 on 2026-06-01 to around 05:00 on 2026-06-02, and again from 22:00 on 2026-08-25 to…
- [S430 Curtailed - grid operator setpoint](s430.md): S430 Curtailed - grid operator setpoint is a status code used in SCADA alarm and status logs. In the current log, WTG-01 through WTG-12 entered S430 Curtailed - grid operator setpoint at 20.0 MW on 2026-07-14. On 2026-07-15 and 2026-07-16, the same status started at about 08:00 and ended at about…
- [S510 Stopped - fault](s510.md): S510 Stopped - fault is a status code used in SCADA alarm and status logs. It appears with pitch system fault events, gearbox oil sump temperature alarms and trips, and grid voltage out of range alarms across multiple wind turbines. The logs show S510 starting and ending when those alarms are…
- [S600 Stopped - icing](s600.md): S600 Stopped - icing is a status code used for WTG-12, WTG-09, WTG-03, and WTG-02 in SCADA alarm and status logs. In the cited log, icing alarms A7001 led to S600 status starts for those turbines, with later clears and S600 ends recorded.
