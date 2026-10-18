---
id: topic:safety-and-access
type: topic
title: Safety, isolation and work at height
summary: This page covers safety controls for isolation, permits, access, working at height, rescue, lifting, dropped objects and related audit actions at Quellmoor Ridge Wind Farm.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- safety-and-access
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
topic_slug: safety-and-access
sources:
- src-05b9ebcb4d58
- src-15df96905f07
- src-1d8dff18b801
- src-21bd4ddf2ed6
- src-383540987d7a
- src-52a23aeb488e
- src-67f6c3ce9754
- src-70224c3b9c9f
- src-824b788eefc0
- src-90ea27f71f0f
- src-9d075c6edcd5
- src-9fd435ef5956
- src-a011da5de982
- src-a7e8d332dafd
- src-aba30cb7207f
- src-e7cd20fa7984
confidence: high
contradictions: 0
superseded_claims: 6
---

# Safety, isolation and work at height

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This page covers safety controls for isolation, permits, access, working at height, rescue, lifting, dropped objects and related audit actions at [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md).

## Overview

Current turbine work is controlled through permit-to-work and lockout/tagout requirements, including permit issuer checks of the isolation list and personal named padlocks kept under each worker's control.[^c1][^c2][^c3] Working at height controls cover climbing, nacelle and hub work, rescue arrangements, mandatory tool tethering above height, hatch control and tower-base exclusion zones during nacelle work.[^c4][^c5] Rescue readiness is based on sealed nacelle rescue kits with scheduled inspections, site rescue drills, and a target to get a casualty to the ground within the stated response time.[^c6][^c7][^c8] The [WTG-04](../entities/asset/wtg-04.md) blade B replacement lift has specific current controls for permit sign-off, rotor and pitch isolation, weather limits, tag lines and an exclusion zone released only by the appointed person.[^c9][^c10]

## Permit to work and lockout/tagout

- [SOP-LOTO-001](../entities/procedure/sop-loto-001.md) is intended to protect people working on a turbine against unexpected release of electrical, hydraulic, mechanical, rotational and thermal energy.[^c11]
- The lockout/tagout procedure applies to work on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md) and the [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md) low-voltage boards, while high-voltage switching is outside the procedure and is performed only by authorised persons under the switching programme.[^c12]
- The isolation sequence starts by informing the control room and setting the turbine to [maintenance mode](../entities/status-code/s310.md), then stopping the turbine and confirming rotor speed below the specified threshold before continuing.[^c13][^c14]
- Rotor lock pins are used for [LT-32](../entities/product/lt-32.md) rotational energy isolation and must not be engaged above the specified wind limit.[^c15][^c16]
- Electrical and controller energy isolation includes opening the main circuit breaker and UPS output breaker, then applying padlocks and tags.[^c17][^c18][^c19]
- Hydraulic energy from pitch and yaw brake accumulators is isolated by relief valves to zero pressure, and verification before work includes a local start attempt, absence-of-voltage testing at the converter and accumulator gauge checks.[^c20][^c21][^c22]
- When more than two people work on a turbine, a group lock box is applied.[^c23]
- During lockout removal, each worker removes only his or her own padlock, and the last person checks that tools are removed and guards are fitted before the turbine leaves maintenance mode.[^c24]
- [Gearbox](../entities/component/gearbox.md) oil changes and [generator](../entities/component/generator.md) brush work both require a permit to work, at least two technicians and lockout/tagout before the work proceeds.[^c25][^c26][^c27][^c28]

## Working at height, access limits and dropped objects

- [SOP-WAH-003](../entities/procedure/sop-wah-003.md) is intended to prevent falls of people and objects during tower and nacelle work and to ensure that a casualty can be rescued quickly.[^c29]
- The working-at-height scope covers all climbing, work in the nacelle and hub, and rescue on [WTG-01](../entities/asset/wtg-01.md) to [WTG-12](../entities/asset/wtg-12.md).[^c4]
- The O&M Supervisor plans work at height and checks weather limits, while each technician checks his or her harness and lanyards before use.[^c30][^c31]
- Climbing requires at least two persons, only one ladder section may be climbed at a time, and climbers must use the fall arrest rail and rest platforms and use the [service lift](../entities/component/service-lift.md) when available.[^c32][^c33]
- Climbing and nacelle work, hub entry and nacelle roof work each have separate wind-speed limits, and climbing is not allowed when lightning is detected within the stated distance.[^c34][^c35][^c36][^c37]
- Access is prohibited within the stated distance of a turbine with ice detected under alarm [A7001](../entities/alarm-code/a7001.md).[^c38]
- Tool tethering is mandatory above two metres, and hatches must stay closed while tools or parts are passed.[^c5]
- During nacelle work, an exclusion zone with signage is set up at the tower base, and nobody enters it without the nacelle team's agreement.[^c5]
- The [WTG-11](../entities/asset/wtg-11.md) near miss involved a dropped socket during a service while tools were being passed through an open hatch; the socket fell to the tower base platform, but nobody was there because the exclusion zone was respected.[^c39]
- The dropped-object investigation identified an untethered socket, an open hatch during tool passing and the absence of a tool tether anchor point at the yaw deck hatch as causes.[^c39]
- Revision B of the working-at-height procedure added mandatory tool tethering above two metres after the dropped-socket near miss and added the requirement to close hatches when passing tools.[^c40]

## Rescue arrangements

- Each nacelle has a sealed [rescue kit](../entities/component/rescue-kit.md) with a descent device.[^c7]
- Rescue kits are inspected every six months, and their seals are checked on the daily checklist.[^c7]
- A broken rescue kit seal means the kit must be inspected before the next climb.[^c7]
- The rescue procedure begins by raising the alarm to the control room and emergency services, then making the turbine safe by stopping it and applying the rotor lock.[^c41][^c42]
- The casualty is attached to the descent device and lowered to the ground or through the tower, with a target to have the casualty on the ground within the stated response time.[^c43][^c8]
- Working-at-height and rescue training is refreshed on a scheduled cycle, and rescue drills take place twice a year on site.[^c44]
- The internal audit recorded that the [WTG-06](../entities/asset/wtg-06.md) rescue drill lowered the casualty to the ground within the target time.[^c45]
- The internal audit found the WTG-06 nacelle rescue kit past its inspection date, and the later O&M review recorded that audit finding F1 was closed.[^c45][^c46]

## WTG-04 blade replacement lift controls

- The [WTG-04](../entities/asset/wtg-04.md) blade B replacement is planned as a single blade lift.[^c10]
- Before lifting, the sequence requires a pre-lift meeting and a permit to work signed by both parties.[^c9]
- The rotor is locked with blade B pointing down, and the pitch system is isolated.[^c9]
- The lift plan sets limits for mean wind speed and gusts and prohibits the lift in fog below the stated visibility, lightning within the stated distance or icing.[^c10]
- Wind for the lift is read at the WTG-04 nacelle anemometer and the boom tip anemometer.[^c10]
- The lift plan sets an exclusion zone around WTG-04 during the lift, and that exclusion zone may be released only by the appointed person.[^c10][^c9]
- Two tag lines are fitted to the blade, both tag lines are manned during lowering, and the banksman closes the site gate.[^c10][^c9]
- The blade yoke is fitted and load tested above the laydown area before the blade is unbolted and lowered.[^c9]
- The lift plan states the blade, yoke, rigging and total hook load, the crane capacity at radius and utilisation, and the allowable and calculated ground bearing pressures.[^c10]

## Environmental and spill-related access safeguards

- Turbines must stop automatically when ice is detected on rotor blades and may restart only when the ice has gone.[^c47]
- Warning signs about falling ice must be placed at all access points at the stated distance from the turbines during the stated seasonal period.[^c47]
- A spill kit must be kept in each turbine and in the O&M building.[^c47]
- Oil spills above the permit threshold outside a turbine must be reported to the Authority within the required period.[^c47]
- Oil drums must be stored in a bunded area sized against the largest container or the total stored volume, whichever gives the larger required capacity.[^c47]
- Waste oil must be collected by a licensed carrier.[^c47]
- During [gearbox](../entities/component/gearbox.md) oil changes, the spill kit must be ready at the gearbox and absorbent pads must be placed under every connection.[^c48]
- Gearbox waste oil is stored in the bunded store in the O&M building and collected by the licensed carrier, with oil sample results kept with the work order.[^c49]

## Audit findings and action status

- The internal safety audit covered the PTW system, lockout/tagout, working at height and rescue, lifting equipment, oil and chemical handling, training records and emergency arrangements.[^c45]
- The audit concluded that the site met the corporate standard and recorded an overall score against the target.[^c45]
- The audit recorded positive observations that the PTW system was well used, permits were closed correctly and lockout boards were clear and up to date.[^c45]
- The audit found two personal padlocks in use without name tags, and the later O&M review recorded that audit finding F2 was closed.[^c45][^c46]
- The audit found dropped-object exclusion signage absent at the [WTG-11](../entities/asset/wtg-11.md) tower base during nacelle work, and the later O&M review recorded that audit finding F5 was closed.[^c45][^c46]
- The audit found incomplete toolbox talk attendance records for November 2025, and the later O&M review recorded that audit finding F3 remained open with its due date moved.[^c45][^c46]
- The audit observed the oil drum storage bund at high capacity with twelve drums stored, and the later O&M review recorded that audit finding F4 remained open with its due date.[^c45][^c46]
- The monthly O&M review recorded that the actions from near miss INC-2026-003 were closed.[^c50]

## Contradictions

No contradictions were found between current sources.

## Superseded information

- **[Gearbox](../entities/component/gearbox.md) oil type and oil quantity for gearbox oil changes.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The specified new oil is [Proseware PWG 320](../entities/product/pwg-320.md) (ISO VG 320), with 410 L per turbine supplied as 2 drums [PWS-320-D208](../entities/part/pws-320-d208.md).[^c51] 410 L of Proseware PWG 320 is filled through a 10 micron filter cart.[^c52] Replacement: Each turbine requires 470 L of [Proseware PWG 220](../entities/product/pwg-220.md), consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of [PWS-220-D208](../entities/part/pws-220-d208.md).[^c53] The gearbox is filled with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c54] Revision B changed the oil to PWG 220 per MOC-2025-012 and [SB-LWS-2025-07](../entities/bulletin/sb-lws-2025-07.md), added the flush step, and set a minimum start-up temperature of +5 °C.[^c55] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Gearbox flushing step for the oil conversion procedure.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The specified new oil is Proseware PWG 320 (ISO VG 320), with 410 L per turbine supplied as 2 drums PWS-320-D208.[^c51] 410 L of Proseware PWG 320 is filled through a 10 micron filter cart.[^c52] Revision A is the first issue and is associated with PWG 320.[^c56] Replacement: Each turbine requires 470 L of Proseware PWG 220, consisting of 60 L for flushing and 410 L for filling, supplied as 3 drums of PWS-220-D208.[^c53] The flush step uses 60 L of PWG 220, runs the electric oil pump for 30 minutes, and then drains the flush oil into waste containers.[^c57] Revision B changed the oil to PWG 220 per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c55] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Minimum gearbox oil-sump temperature for turbine start after oil change.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: After lockout removal and restart, oil temperature is watched during the first hour, and the turbine starts only when the oil sump has reached +10 °C.[^c58] Replacement: Controller parameter GBX_TMIN_START must be set to 5 °C, and the gearbox filler must be labelled PWG 220.[^c59] On restart, oil temperature is watched during the first hour, and the turbine starts only once the oil sump has reached +5 °C.[^c60] Revision B changed the oil to PWG 220 per MOC-2025-012 and SB-LWS-2025-07, added the flush step, and set a minimum start-up temperature of +5 °C.[^c55] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Oil top-up after gearbox oil level check.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: After 20 minutes of standstill, the oil level is checked at the sight glass and topped up if needed.[^c61] Replacement: After 20 minutes of standstill, the oil level is checked at the sight glass according to [SPL-012](../entities/procedure/spl-012.md) and topped up only with PWG 220.[^c62] A converted gearbox must never be topped up with PWG 320, and residual PWG 320 must remain below 5 % of oil volume.[^c63] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Magnetic plug removal, debris recording and cleaning step in the [gearbox oil change procedure](../entities/procedure/sop-gbx-010.md).** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: The magnetic plug is removed, debris is recorded, and the plug is cleaned.[^c64] Replacement: no current source restates it. Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).
- **Gearbox oil change completion records.** [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md) stated: Quantities and batch numbers must be recorded in the work order.[^c65] Replacement: Quantities and batch numbers are recorded in the work order, and the completion form is sent to [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) within 30 days.[^c66] Superseding source: [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md).

## Sources consulted

- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../sources/ep-2018-0417-environmental-permit-consolidated.md): current, authority 10, dated 2024-12-10
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../sources/wbs-2026-031-blade-inspection-report.md): current, authority 7, dated 2026-06-03
- [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement](../sources/lp-2026-009-lift-plan-wtg-04-blade-scanned.md): current, authority 7, dated 2026-08-19
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md): current, authority 7, dated 2025-08-25
- [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines](../sources/sop-loto-001-revc-lockout-tagout.md): current, authority 7, dated 2024-09-02
- [SOP-WAH-003 Revision B - Working at height and rescue](../sources/sop-wah-003-revb-working-at-height-and-rescue.md): current, authority 7, dated 2026-04-07
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../sources/wi-gen-014-reva-remplacement-balais-generatrice.md): current, authority 7, dated 2025-09-15
- [Internal safety audit report AUD-2026-02](../sources/aud-2026-02-internal-safety-audit-report.md): current, authority 6, dated 2026-03-06
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md): current, authority 6, dated 2026-07-01
- [Near-miss Report INC-2026-003: Dropped Socket at WTG-11](../sources/inc-2026-003-near-miss-dropped-socket-wtg-11.md): current, authority 6, dated 2026-03-27
- [Work Orders Export through 2026-08-31](../sources/work-orders-export-2026-08-31.md): current, authority 5, date unknown
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md): current, authority 4, dated 2026-06-18
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../sources/onboarding-and-site-rules.md): current, authority 4, dated 2025-02-03
- [Shift Handover for 2026-07-29 Day Shift](../sources/2026-07-29-shift-handover.md): current, authority 2, date unknown
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md): current, authority 2, date unknown
- [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md): superseded, authority 7, dated 2023-04-03

## Related

- Assets: [Quellmoor Ridge O&M building](../entities/asset/om-building.md), [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md), [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-01](../entities/asset/wtg-01.md), [WTG-02](../entities/asset/wtg-02.md), [WTG-03](../entities/asset/wtg-03.md), [WTG-04](../entities/asset/wtg-04.md), [WTG-05](../entities/asset/wtg-05.md), [WTG-06](../entities/asset/wtg-06.md), [WTG-07](../entities/asset/wtg-07.md), [WTG-08](../entities/asset/wtg-08.md), [WTG-09](../entities/asset/wtg-09.md), [WTG-10](../entities/asset/wtg-10.md), [WTG-11](../entities/asset/wtg-11.md), [WTG-12](../entities/asset/wtg-12.md)
- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [generator brushes](../entities/component/generator-brushes.md), [HSS bearing](../entities/component/hss-bearing.md), [hydraulic system](../entities/component/hydraulic-system.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [pitch bearing](../entities/component/pitch-bearing.md), [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md), [rescue kit](../entities/component/rescue-kit.md), [rotor blade](../entities/component/rotor-blade.md), [service lift](../entities/component/service-lift.md), [slip ring](../entities/component/slip-ring.md), [yaw system](../entities/component/yaw-system.md)
- Spare parts: [AWI-10442](../entities/part/awi-10442.md), [AWI-20915](../entities/part/awi-20915.md), [AWI-31007](../entities/part/awi-31007.md), [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-51207](../entities/part/lws-p-51207.md), [LWS-P-55031](../entities/part/lws-p-55031.md), [PWS-220-D208](../entities/part/pws-220-d208.md), [PWS-320-D208](../entities/part/pws-320-d208.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [LT-32 CCV](../entities/product/lt-32-ccv.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md), [TS-600C](../entities/product/ts-600c.md)
- Alarm codes: [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md), [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- Status codes: [S100 Running](../entities/status-code/s100.md), [S310 Maintenance mode](../entities/status-code/s310.md)
- Procedures: [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md), [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md), [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md), [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md), [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- Service bulletins: [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md), [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- Organisations: [City Power & Light](../entities/organisation/city-power-and-light.md), [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md), [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md), [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A3210 Generator brush wear limit reached](../entities/alarm-code/a3210.md)
- [A7001 Ice detected on rotor blades](../entities/alarm-code/a7001.md)
- [AWI-10442](../entities/part/awi-10442.md)
- [AWI-20915](../entities/part/awi-20915.md)
- [AWI-31007](../entities/part/awi-31007.md)
- [Blade inspection report WBS-2026-031 - Quellmoor Ridge Wind Farm (May 2026)](../sources/wbs-2026-031-blade-inspection-report.md)
- [City Power & Light](../entities/organisation/city-power-and-light.md)
- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2)](../sources/ep-2018-0417-environmental-permit-consolidated.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [gearbox](../entities/component/gearbox.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [generator](../entities/component/generator.md)
- [generator brushes](../entities/component/generator-brushes.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [hydraulic system](../entities/component/hydraulic-system.md)
- [Internal safety audit report AUD-2026-02](../sources/aud-2026-02-internal-safety-audit-report.md)
- [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement](../sources/lp-2026-009-lift-plan-wtg-04-blade-scanned.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LT-32 CCV](../entities/product/lt-32-ccv.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-51207](../entities/part/lws-p-51207.md)
- [LWS-P-55031](../entities/part/lws-p-55031.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../sources/maintenance-plan-2026.md)
- [Monthly O&M Review Minutes – 2026-06-18](../sources/2026-06-18-monthly-om-review-minutes.md)
- [Near-miss Report INC-2026-003: Dropped Socket at WTG-11](../sources/inc-2026-003-near-miss-dropped-socket-wtg-11.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [pitch bearing](../entities/component/pitch-bearing.md)
- [pitch bearing bolts](../entities/component/pitch-bearing-bolts.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [PWS-220-D208](../entities/part/pws-220-d208.md)
- [PWS-320-D208](../entities/part/pws-320-d208.md)
- [Quellmoor Ridge O&M building](../entities/asset/om-building.md)
- [Quellmoor Ridge substation](../entities/asset/quellmoor-ridge-substation.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../sources/onboarding-and-site-rules.md)
- [rescue kit](../entities/component/rescue-kit.md)
- [rotor blade](../entities/component/rotor-blade.md)
- [S100 Running](../entities/status-code/s100.md)
- [S310 Maintenance mode](../entities/status-code/s310.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../entities/bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-11 Pitch bearing bolt re-torque](../entities/bulletin/sb-lws-2025-11.md)
- [service lift](../entities/component/service-lift.md)
- [Shift handover - 2026-07-15 (day shift to night shift)](../sources/2026-07-15-shift-handover.md)
- [Shift Handover for 2026-07-29 Day Shift](../sources/2026-07-29-shift-handover.md)
- [Skelvane District Environmental Authority](../entities/organisation/skelvane-district-environmental-authority.md)
- [slip ring](../entities/component/slip-ring.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Gearbox oil change](../entities/procedure/sop-gbx-010.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [SOP-LOTO-001 Lockout/tagout of wind turbines](../entities/procedure/sop-loto-001.md)
- [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines](../sources/sop-loto-001-revc-lockout-tagout.md)
- [SOP-WAH-003 Revision B - Working at height and rescue](../sources/sop-wah-003-revb-working-at-height-and-rescue.md)
- [SOP-WAH-003 Working at height and rescue](../entities/procedure/sop-wah-003.md)
- [SPL-012 Gearbox oil level check](../entities/procedure/spl-012.md)
- [Tailspin Heavy Lift](../entities/organisation/tailspin-heavy-lift.md)
- [TS-600C](../entities/product/ts-600c.md)
- [WI-GEN-014 Generator brush replacement](../entities/procedure/wi-gen-014.md)
- [WI-GEN-014 Rev. A - Generator Brush Replacement](../sources/wi-gen-014-reva-remplacement-balais-generatrice.md)
- [Wingtip Blade Services](../entities/organisation/wingtip-blade-services.md)
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
- [yaw system](../entities/component/yaw-system.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 8](../evidence/src-21bd4ddf2ed6/para-0008.md) · ✓ quote verified
[^c2]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 9](../evidence/src-21bd4ddf2ed6/para-0009.md) · ✓ quote verified
[^c3]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 13](../evidence/src-21bd4ddf2ed6/para-0013.md) · ✓ quote verified
[^c4]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 6](../evidence/src-05b9ebcb4d58/para-0006.md) · ✓ quote verified
[^c5]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 12](../evidence/src-05b9ebcb4d58/para-0012.md) · ✓ quote verified
[^c6]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 10](../evidence/src-05b9ebcb4d58/para-0010.md) · ✓ quote verified
[^c7]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 19](../evidence/src-05b9ebcb4d58/para-0019.md) · ✓ quote verified
[^c8]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 24](../evidence/src-05b9ebcb4d58/para-0024.md) · ✓ quote verified
[^c9]: [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement — p. 2](../evidence/src-67f6c3ce9754/p0002.md) · OCR
[^c10]: [Lift Plan LP-2026-009 - WTG-04 Blade B Replacement — p. 1](../evidence/src-67f6c3ce9754/p0001.md) · OCR
[^c11]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 4](../evidence/src-21bd4ddf2ed6/para-0004.md) · ✓ quote verified
[^c12]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 6](../evidence/src-21bd4ddf2ed6/para-0006.md) · ✓ quote verified
[^c13]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 15](../evidence/src-21bd4ddf2ed6/para-0015.md) · ✓ quote verified
[^c14]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 16](../evidence/src-21bd4ddf2ed6/para-0016.md) · ✓ quote verified
[^c15]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 6](../evidence/src-21bd4ddf2ed6/tbl-02-r0006-r0006.md) · table
[^c16]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 17](../evidence/src-21bd4ddf2ed6/para-0017.md) · ✓ quote verified
[^c17]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 2](../evidence/src-21bd4ddf2ed6/tbl-02-r0002-r0002.md) · table
[^c18]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 4](../evidence/src-21bd4ddf2ed6/tbl-02-r0004-r0004.md) · table
[^c19]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 18](../evidence/src-21bd4ddf2ed6/para-0018.md) · ✓ quote verified
[^c20]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — table 2, row 5](../evidence/src-21bd4ddf2ed6/tbl-02-r0005-r0005.md) · table
[^c21]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 19](../evidence/src-21bd4ddf2ed6/para-0019.md) · ✓ quote verified
[^c22]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 22](../evidence/src-21bd4ddf2ed6/para-0022.md) · ✓ quote verified
[^c23]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 20](../evidence/src-21bd4ddf2ed6/para-0020.md) · ✓ quote verified
[^c24]: [SOP-LOTO-001 Rev. C - Lockout/tagout of wind turbines — ¶ 24](../evidence/src-21bd4ddf2ed6/para-0024.md) · ✓ quote verified
[^c25]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 16](../evidence/src-70224c3b9c9f/para-0016.md) · ✓ quote verified
[^c26]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 17](../evidence/src-70224c3b9c9f/para-0017.md) · ✓ quote verified
[^c27]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 6](../evidence/src-824b788eefc0/para-0006.md) · ✓ quote verified
[^c28]: [WI-GEN-014 Rev. A - Generator Brush Replacement — ¶ 7](../evidence/src-824b788eefc0/para-0007.md) · ✓ quote verified
[^c29]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 4](../evidence/src-05b9ebcb4d58/para-0004.md) · ✓ quote verified
[^c30]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 8](../evidence/src-05b9ebcb4d58/para-0008.md) · ✓ quote verified
[^c31]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 9](../evidence/src-05b9ebcb4d58/para-0009.md) · ✓ quote verified
[^c32]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 14](../evidence/src-05b9ebcb4d58/para-0014.md) · ✓ quote verified
[^c33]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 15](../evidence/src-05b9ebcb4d58/para-0015.md) · ✓ quote verified
[^c34]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 2](../evidence/src-05b9ebcb4d58/tbl-02-r0002-r0002.md) · table
[^c35]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 3](../evidence/src-05b9ebcb4d58/tbl-02-r0003-r0003.md) · table
[^c36]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 4](../evidence/src-05b9ebcb4d58/tbl-02-r0004-r0004.md) · table
[^c37]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 5](../evidence/src-05b9ebcb4d58/tbl-02-r0005-r0005.md) · table
[^c38]: [SOP-WAH-003 Revision B - Working at height and rescue — table 2, row 6](../evidence/src-05b9ebcb4d58/tbl-02-r0006-r0006.md) · table
[^c39]: [Near-miss Report INC-2026-003: Dropped Socket at WTG-11 — p. 1](../evidence/src-52a23aeb488e/p0001.md) · ✓ quote verified
[^c40]: [SOP-WAH-003 Revision B - Working at height and rescue — table 3, row 3](../evidence/src-05b9ebcb4d58/tbl-03-r0003-r0003.md) · table
[^c41]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 21](../evidence/src-05b9ebcb4d58/para-0021.md) · ✓ quote verified
[^c42]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 22](../evidence/src-05b9ebcb4d58/para-0022.md) · ✓ quote verified
[^c43]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 23](../evidence/src-05b9ebcb4d58/para-0023.md) · ✓ quote verified
[^c44]: [SOP-WAH-003 Revision B - Working at height and rescue — ¶ 26](../evidence/src-05b9ebcb4d58/para-0026.md) · ✓ quote verified
[^c45]: [Internal safety audit report AUD-2026-02 — p. 1](../evidence/src-9d075c6edcd5/p0001.md) · ✓ quote verified
[^c46]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 6](../evidence/src-15df96905f07/para-0006.md) · ✓ quote verified
[^c47]: [Environmental Permit EP-2018-0417 - Quellmoor Ridge Wind Farm (consolidated with variation 2) — p. 2](../evidence/src-a7e8d332dafd/p0002.md) · ✓ quote verified
[^c48]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 20](../evidence/src-70224c3b9c9f/para-0020.md) · ✓ quote verified
[^c49]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 44](../evidence/src-70224c3b9c9f/para-0044.md) · ✓ quote verified
[^c50]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 5](../evidence/src-15df96905f07/para-0005.md) · ✓ quote verified
[^c51]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 19](../evidence/src-90ea27f71f0f/para-0019.md) · ✓ quote verified
[^c52]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 31](../evidence/src-90ea27f71f0f/para-0031.md) · ✓ quote verified
[^c53]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 22](../evidence/src-70224c3b9c9f/para-0022.md) · ✓ quote verified
[^c54]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 35](../evidence/src-70224c3b9c9f/para-0035.md) · ✓ quote verified
[^c55]: [SOP-GBX-010 Rev. B - Gearbox oil change — table 2, row 3](../evidence/src-70224c3b9c9f/tbl-02-r0003-r0003.md) · table
[^c56]: [SOP-GBX-010 - Gearbox oil change, Revision A — table 2, row 2](../evidence/src-90ea27f71f0f/tbl-02-r0002-r0002.md) · table
[^c57]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 34](../evidence/src-70224c3b9c9f/para-0034.md) · ✓ quote verified
[^c58]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 34](../evidence/src-90ea27f71f0f/para-0034.md) · ✓ quote verified
[^c59]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 38](../evidence/src-70224c3b9c9f/para-0038.md) · ✓ quote verified
[^c60]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 39](../evidence/src-70224c3b9c9f/para-0039.md) · ✓ quote verified
[^c61]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 33](../evidence/src-90ea27f71f0f/para-0033.md) · ✓ quote verified
[^c62]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 37](../evidence/src-70224c3b9c9f/para-0037.md) · ✓ quote verified
[^c63]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 42](../evidence/src-70224c3b9c9f/para-0042.md) · ✓ quote verified
[^c64]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 28](../evidence/src-90ea27f71f0f/para-0028.md) · ✓ quote verified
[^c65]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 36](../evidence/src-90ea27f71f0f/para-0036.md) · ✓ quote verified
[^c66]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 41](../evidence/src-70224c3b9c9f/para-0041.md) · ✓ quote verified
