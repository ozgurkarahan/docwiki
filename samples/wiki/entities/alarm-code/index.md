---
id: index:entities/alarm-code
type: index
title: Alarm codes
summary: SCADA alarm codes of the turbines.
lang: en
sensitivity: public
updated: 2026-10-18
tags: []
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
---

# Alarm codes

SCADA alarm codes of the turbines.

- [A1001 Emergency stop activated](a1001.md): A1001 Emergency stop activated is an alarm code in the reviewed registry. It was raised and cleared during maintenance on WTG-04 and WTG-11.
- [A2101 Gearbox oil sump temperature high](a2101.md): A2101 is the gearbox oil sump temperature high alarm, with a warning threshold of 75 °C. Its trip counterpart is A2102 at 82 °C. In SCADA logs, WTG-07 and WTG-11 raised A2101 at around 75 °C.
- [A2102 Gearbox oil sump temperature trip](a2102.md): A2102 Gearbox oil sump temperature trip is an alarm code for a gearbox oil sump temperature trip. It trips at 82 °C and stops the turbine automatically. The cooling circuit is inspected before restart, and the reset is not performed more than once without inspection.
- [A2110 Gearbox HSS bearing temperature high](a2110.md): A2110 is an alarm code for Gearbox HSS bearing temperature high. It is raised at 90 °C. In the SCADA log, WTG-02 recorded A2110 twice, with values of 91.2 °C on 2026-07-19 and 90.6 °C on 2026-07-22.
- [A2120 Gearbox oil pressure low](a2120.md): A2120 is an alarm code for gearbox oil pressure low. It is associated with a 0.8 bar alarm threshold. The alarm can occur after a cold start, and the listed causes include cold oil, pump fault, or a blocked filter.
- [A2130 Gearbox oil level low](a2130.md): A2130 is an alarm code for gearbox oil level low. If the gearbox oil level is below MIN, the turbine should not be restarted and the issue should be reported to the O&M Supervisor.
- [A2140 Gearbox oil filter differential pressure high](a2140.md): A2140 is the gearbox oil filter differential pressure high alarm. It is raised at 2.5 bar and can be caused by a clogged filter element or cold oil. The stated action is to replace filter element FGT-P-11872.
- [A3201 Generator winding temperature high](a3201.md): A3201 Generator winding temperature high is an alarm code. In the WTG-12 SCADA alarm and status log, it was raised at 147.3 °C and cleared at 139.5 °C on 2026-08-26.
- [A3210 Generator brush wear limit reached](a3210.md): A3210 is the alarm code for Generator brush wear limit reached. It appears when the remaining brush length reaches approximately 20 mm. Records for WTG-09 show the alarm was raised on 2026-07-16 and cleared on 2026-07-18, and the generator brushes were replaced under work order WO-26-0436.
- [A4105 Pitch system fault](a4105.md): A4105 Pitch system fault is an alarm code in the reviewed registry. In SCADA alarm and status logs, it was recorded on WTG-12, WTG-05, WTG-06, and WTG-10 with S510 Stopped - fault events. The logged values were 1 axis, 2 axis, and 3 axis.
- [A5001 Yaw misalignment](a5001.md): A5001 Yaw misalignment is an alarm code. It was raised and later cleared on WTG-11, WTG-02, WTG-06, and WTG-03 in the SCADA alarm and status log.
- [A6101 Grid voltage out of range](a6101.md): A6101 Grid voltage out of range is an alarm code recorded for WTG-01 through WTG-12 in the SCADA alarm and status log. The log shows A6101 alarms and corresponding S510 Stopped - fault status entries, with clear entries also recorded.
- [A7001 Ice detected on rotor blades](a7001.md): A7001 is an ice detection alarm for ice detected on rotor blades. It stops the turbine automatically when active. When ice is detected under A7001, there is no access within 300 m of a turbine.
