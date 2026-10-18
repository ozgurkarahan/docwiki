---
id: component:gearbox
type: entity
title: gearbox
summary: A gearbox is a component used in LT-32 turbines and in the Fabrikam FGT-3200 three-stage gearbox. The LT-32 gearbox has an overall ratio of 1:118.4, a rated input torque of 2,410 kNm, and a dry mass of 21.6 t. Its lubrication system uses splash and forced lubrication, and the total oil volume is…
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- component
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
entity_type: component
key: gearbox
aliases:
- text: gearbox
  lang: en
- text: multiplicateur
  lang: fr
- text: Getriebe
  lang: de
sources:
- src-0df0d0598e76
- src-15df96905f07
- src-1abc5aef1a40
- src-1b5b5135881d
- src-1c261d5b87b5
- src-36f5b999211a
- src-42566abae6ef
- src-4e79f89ff183
- src-70224c3b9c9f
- src-86cb00fd2f6b
- src-90ea27f71f0f
- src-990a047180b7
- src-9a6703e054dc
- src-9fd435ef5956
- src-a20331a5431f
- src-aba30cb7207f
- src-b342a2d5bfdf
- src-c4370c220559
- src-e7cd20fa7984
- src-ecc004b57dd5
---

# gearbox

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

A gearbox is a component used in [LT-32](../product/lt-32.md) turbines and in the [Fabrikam FGT-3200](../product/fgt-3200.md) three-stage gearbox.[^c1][^c2] The LT-32 gearbox has an overall ratio of 1:118.4, a rated input torque of 2,410 kNm, and a dry mass of 21.6 t.[^c2] Its lubrication system uses splash and forced lubrication, and the total oil volume is 410 L.[^c2][^c3]

## Facts

- The bulletin is categorized as recommended, but mandatory to keep the gearbox warranty.[^c4]
- The gearbox must be flushed with 60 L of [PWG 220](../product/pwg-220.md), the electric oil pump run for 30 minutes, and the flush oil then drained.[^c4]
- The gearbox must be filled with 410 L of PWG 220 through a filter cart with a 10 micron element.[^c4]
- The gearbox filler must be labelled 'PWG 220' using the supplied label kit.[^c4]
- Conversions performed according to the bulletin keep the gearbox warranty valid.[^c5]
- The excerpt is Chapter 4, Gearbox, of document LWS-MM-GBX-32 Rev. D, issued by [Litware Wind Systems](../organisation/litware-wind-systems.md) on 2024-03-15.[^c1]
- The document applies to [LT-32](../product/lt-32.md) turbines of all variants with the [Fabrikam FGT-3200](../product/fgt-3200.md) gearbox.[^c1]
- Gearbox work requires the turbine to be stopped, the rotor locked, and the drivetrain isolated according to the operator's lockout procedure; hot oil up to 80 °C can cause burns.[^c1]
- Litware Wind Systems publishes changes to the gearbox chapter as service bulletins, and the bulletin register must be checked before planning gearbox work.[^c1]
- The LT-32 uses a Fabrikam FGT-3200 three-stage gearbox with one [planetary stage](planetary-stage.md) followed by two parallel helical stages.[^c2]
- The gearbox overall ratio is 1:118.4; at a rated rotor speed of 12.7 rpm, the output pinion shaft drives the [generator](generator.md) at 1,500 rpm.[^c2]
- The FGT-3200 gearbox rated input torque is 2,410 kNm and its dry mass is 21.6 t.[^c2]
- The gearbox lubrication system uses splash and forced lubrication, with a shaft-driven pump for operation and an electric pump for start-up and flushing.[^c2]
- Only the lubricant listed in Table 4-2 is approved for the FGT-3200 gearbox, and lubricants of different brands or viscosity grades must not be mixed.[^c3]
- The total oil volume is 410 L, made up of 330 L in the gearbox sump and 80 L in the cooling and filter circuit.[^c3]
- Alarm [A2101](../alarm-code/a2101.md), Gearbox oil sump temperature high at 75 °C, can be caused by cooling, oil level, load/ambient-temperature, or bearing issues; actions include checking fan rotation and motor current, cleaning the radiator, checking valve insert [LWS-P-30422](../part/lws-p-30422.md), checking oil level, reviewing vibration trend, and taking an oil sample.[^c6]
- Alarm [A2102](../alarm-code/a2102.md), Gearbox oil sump temperature trip at 82 °C, stops the turbine automatically; the cooling circuit is inspected before restart, and reset is not performed more than once without inspection.[^c6]
- Alarm [A2110](../alarm-code/a2110.md), Gearbox HSS bearing temperature high at 90 °C, can be caused by bearing damage or lubrication starvation; checks are vibration trend review and endoscope inspection of the bearing.[^c6]
- Alarm [A2120](../alarm-code/a2120.md), Gearbox oil pressure low at 0.8 bar, can be caused by cold oil at start-up, pump fault, or blocked filter; actions are to allow heater time at cold start and check the pump and filter.[^c6]
- Alarm [A2140](../alarm-code/a2140.md), Gearbox oil filter differential pressure high at 2.5 bar, can be caused by a clogged filter element or cold oil; the action is to replace filter element [FGT-P-11872](../part/fgt-p-11872.md).[^c6]
- The bulletin makes the oil-grade change a condition of the gearbox warranty.[^c7]
- The report is oil analysis report TR-OA-2026-0614 for gearbox oil from [WTG-07](../asset/wtg-07.md) at [Quellmoor Ridge](../asset/quellmoor-ridge-wind-farm.md).[^c8]
- The asset is the WTG-07 main gearbox, a Fabrikam FGT-3200 with serial FGT-3200-18-07752.[^c8]
- The procedure is intended to change gearbox oil safely and avoid contaminating the new oil.[^c9]
- The scope covers all gearbox oil changes on [WTG-01](../asset/wtg-01.md) to [WTG-12](../asset/wtg-12.md), including planned changes and changes decided after oil analysis.[^c10]
- The spill kit must be ready at the gearbox, with absorbent pads under every connection.[^c11]
- The gearbox sump and the cooling and filter circuit are drained into waste containers, with an approximate drained volume of 410 L.[^c12]
- The gearbox is filled with 410 L of Proseware PWG 220 through a 10 micron filter cart.[^c13]
- Controller parameter GBX_TMIN_START must be set to 5 °C, and the gearbox filler must be labelled PWG 220.[^c14]
- A converted gearbox must never be topped up with [PWG 320](../product/pwg-320.md), and residual PWG 320 must remain below 5 % of oil volume.[^c15]
- The incident concerns WTG-07, serial LT32-19-0421, with gearbox FGT-3200-18-07752.[^c16]
- [WTG-09](../asset/wtg-09.md) has gearbox oil conversion to PWG 220 pending and deferred under [SB-LWS-2025-07](../bulletin/sb-lws-2025-07.md).[^c17]
- Gearbox oil sampling and laboratory analysis task MP-GBX-01 is scheduled every 6 months, with a duration field of 1 h and crew field of 1.[^c18]
- Gearbox [oil filter element](oil-filter.md) replacement task MP-GBX-02 uses part FGT-P-11872, is scheduled every 12 months, and references [SOP-GBX-010](../procedure/sop-gbx-010.md).[^c19]
- Gearbox oil change task MP-GBX-03 for PWG 220 is scheduled every 5 years or on condition, references SOP-GBX-010 Rev. B, has a duration field of 6 h, and notes that the next planned changes start from 2030.[^c20]
- In the Plan 2026 sheet, [WTG-02](../asset/wtg-02.md) gearbox endoscope inspection task MP-GBX-04 is planned for 2026-07 and has status done at 2026-07-01.[^c21]
- [SPL-012](../procedure/spl-012.md) is titled "Gearbox oil level check."[^c22]
- To check the gearbox oil level, stop the turbine and wait 20 minutes so the oil settles.[^c23]
- Read the sight glass on the generator side of the gearbox.[^c23]
- The gearbox oil level must be between MIN and MAX.[^c23]
- Record the gearbox oil level check result on item 4 of the daily checklist.[^c23]
- On 2026-04-02, [WTG-08](../asset/wtg-08.md) and WTG-09 raised A2120 Gearbox oil pressure low at 0.59 bar and later cleared at 1.35 bar.[^c24][^c25][^c26][^c27]
- On 2026-05-30, WTG-07 raised A2101 Gearbox oil sump temperature high at 75.3 °C, then raised A2102 Gearbox oil sump temperature trip at 82.6 °C and entered [S510 Stopped - fault](../status-code/s510.md).[^c28][^c29][^c30]
- On 2026-06-19, WTG-07 first raised A2101 Gearbox oil sump temperature high at 75.6 °C, then raised A2102 Gearbox oil sump temperature trip at 83.4 °C and entered S510 Stopped - fault.[^c31][^c32][^c33]
- WTG-02 recorded A2110 Gearbox HSS bearing temperature high twice in this part, with raised values of 91.2 °C on 2026-07-19 and 90.6 °C on 2026-07-22.[^c34][^c35]
- WTG-12 raised A2140 Gearbox oil filter differential pressure high at 2.56 bar on 2026-08-02 and cleared it at 1.90 bar later the same day.[^c36][^c37]
- [WTG-04](../asset/wtg-04.md) raised A2140 Gearbox oil filter differential pressure high at 2.89 bar on 2026-08-11 17:18:08 and cleared it at 1.90 bar on 2026-08-11 18:22:08.[^c38][^c39]
- [WTG-11](../asset/wtg-11.md) raised A2101 Gearbox oil sump temperature high at 75.1 °C on 2026-08-12 16:05:02 and cleared it at 72.7 °C on 2026-08-12 16:14:40.[^c40][^c41]
- [WTG-06](../asset/wtg-06.md) had A2140 Gearbox oil filter differential pressure high raised at 2.89 bar and cleared at 1.90 bar on 2026-08-31.[^c42][^c43]
- The export records a completed high-priority modification campaign for gearbox oil conversion from PWG 320 to PWG 220 with a 60 L flush for WTG-01 through WTG-12 under reference MOC-2025-012; each row lists part [PWS-220-D208](../part/pws-220-d208.md) with quantity 3.[^c44][^c45][^c46][^c47][^c48][^c49][^c50][^c51][^c52][^c53][^c54][^c55]
- The WTG-09 gearbox oil conversion work order WO-25-0309 was deferred because the access road was closed by snow on 2025-11-24 and was completed on 2026-01-20.[^c52]
- Gearbox oil sampling work orders WO-26-0341 through WO-26-0352 cover WTG-01 through WTG-12 and are all marked Completed.[^c56][^c57][^c58][^c59][^c60][^c61][^c62][^c63][^c64][^c65][^c66][^c67]
- The deck is titled “Gearbox fundamentals for wind technicians.”[^c68]
- The gearbox raises rotor speed from 12.7 rpm to 1,500 rpm at the generator.[^c69]
- The gearbox stages described are a planetary stage with a planet carrier, three planet gears, a ring gear and a sun pinion, followed by two parallel helical stages.[^c70]
- The overall gearbox ratio is 1:118.4, with rotor speed 12.7 rpm and generator speed 1,500 rpm.[^c70]
- Each gearbox uses 410 L of oil, with a 60 L flush during the conversion.[^c71]
- Typical gearbox-related failure modes listed are [HSS bearing](hss-bearing.md) damage, micropitting on gear teeth, cooler fouling and fan motor failures, and oil leaks at seals and hoses.[^c72]
- WTG-07 availability was 95.2 % because of gearbox trips.[^c73]
- 8D INC-2026-006 was opened on 2026-05-30 for the WTG-07 gearbox over-temperature issue.[^c74]
- Litware’s response addresses a 29 April 2025 question about SB-LWS-2025-07 Rev. A, described as covering gearbox oil viscosity grade for CCV turbines.[^c75]
- Each gearbox is to be flushed with 60 L of PWG 220 before the final fill of 410 L.[^c76]
- Conversions made according to the bulletin keep the gearbox warranty valid.[^c77]
- For A2120 gearbox oil pressure low immediately after a cold start, technicians should give the heaters more time before escalating, because it is usually cold oil rather than a pump fault.[^c78]
- After conversion, a gearbox must never be topped up with PWG 320; old PWG 320 drums are marked do not use.[^c79]
- Superseded: The procedure describes how to change gearbox oil on Quellmoor Ridge turbines safely and without contaminating the new oil.[^c80]
- Superseded: The scope covers all gearbox oil changes on WTG-01 to WTG-12, whether planned or decided after oil analysis.[^c81]
- Superseded: The spill kit must be kept ready at the gearbox, with absorbent pads under every connection.[^c82]
- Superseded: The gearbox sump and cooling and filter circuit are drained into waste containers, with an approximate drained volume of 410 L.[^c83]

## Timeline

- 2024-03-15: The excerpt is Chapter 4, Gearbox, of document LWS-MM-GBX-32 Rev. D, issued by [Litware Wind Systems](../organisation/litware-wind-systems.md) on 2024-03-15.[^c1]
- 2025-04-29: Litware’s response addresses a 29 April 2025 question about [SB-LWS-2025-07](../bulletin/sb-lws-2025-07.md) Rev. A, described as covering gearbox oil viscosity grade for CCV turbines.[^c75]
- 2025-07: [WTG-09](../asset/wtg-09.md) has gearbox oil conversion to [PWG 220](../product/pwg-220.md) pending and deferred under SB-LWS-2025-07.[^c17]
- 2025-11-24: The WTG-09 gearbox oil conversion work order WO-25-0309 was deferred because the access road was closed by snow on 2025-11-24 and was completed on 2026-01-20.[^c52]
- 2026-04-02: On 2026-04-02, [WTG-08](../asset/wtg-08.md) and WTG-09 raised [A2120 Gearbox oil pressure low](../alarm-code/a2120.md) at 0.59 bar and later cleared at 1.35 bar.[^c24][^c25][^c26][^c27]
- 2026-05-30: 8D INC-2026-006 was opened on 2026-05-30 for the [WTG-07](../asset/wtg-07.md) gearbox over-temperature issue.[^c74]
- 2026-05-30: On 2026-05-30, WTG-07 raised [A2101 Gearbox oil sump temperature high](../alarm-code/a2101.md) at 75.3 °C, then raised [A2102 Gearbox oil sump temperature trip](../alarm-code/a2102.md) at 82.6 °C and entered [S510 Stopped - fault](../status-code/s510.md).[^c28][^c29][^c30]
- 2026-06-19: On 2026-06-19, WTG-07 first raised A2101 Gearbox oil sump temperature high at 75.6 °C, then raised A2102 Gearbox oil sump temperature trip at 83.4 °C and entered S510 Stopped - fault.[^c31][^c32][^c33]
- 2026-07: In the Plan 2026 sheet, [WTG-02](../asset/wtg-02.md) gearbox endoscope inspection task MP-GBX-04 is planned for 2026-07 and has status done at 2026-07-01.[^c21]
- 2026-07-19: WTG-02 recorded [A2110 Gearbox HSS bearing temperature high](../alarm-code/a2110.md) twice in this part, with raised values of 91.2 °C on 2026-07-19 and 90.6 °C on 2026-07-22.[^c34][^c35]
- 2026-08-02: [WTG-12](../asset/wtg-12.md) raised [A2140 Gearbox oil filter differential pressure high](../alarm-code/a2140.md) at 2.56 bar on 2026-08-02 and cleared it at 1.90 bar later the same day.[^c36][^c37]
- 2026-08-11: [WTG-04](../asset/wtg-04.md) raised A2140 Gearbox oil filter differential pressure high at 2.89 bar on 2026-08-11 17:18:08 and cleared it at 1.90 bar on 2026-08-11 18:22:08.[^c38][^c39]
- 2026-08-12: [WTG-11](../asset/wtg-11.md) raised A2101 Gearbox oil sump temperature high at 75.1 °C on 2026-08-12 16:05:02 and cleared it at 72.7 °C on 2026-08-12 16:14:40.[^c40][^c41]
- 2026-08-31: [WTG-06](../asset/wtg-06.md) had A2140 Gearbox oil filter differential pressure high raised at 2.89 bar and cleared at 1.90 bar on 2026-08-31.[^c42][^c43]

## Documents

- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [SPL-012 Gearbox Oil Level Check](../../sources/spl-012-gearbox-oil-level-check.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [Daily Turbine Checklist Form CHK-05 for WTG-05, 14/07/2026](../../sources/chk-05-daily-checklist-wtg-05-2026-07-14.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md) (superseded)

## Related

- Topics: [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md), [Cold-climate operation and icing](../../topics/cold-climate-operation.md), [Environmental permit and night curtailment](../../topics/environmental-compliance.md), [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../../topics/generator-and-electrical.md), [Grid connection and grid operator instructions](../../topics/grid-operations.md), [Safety, isolation and work at height](../../topics/safety-and-access.md), [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md), [Training, site rules and acronyms](../../topics/training-and-onboarding.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10)](../../sources/inc-2026-006-8d-report-wtg-07-gearbox-over-temperature.md)
- [A2130 Gearbox oil level low](../alarm-code/a2130.md)
- [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12](../../sources/asset-register-2026.md)
- [Blades, pitch bearings and main-component lifts](../../topics/blades-and-rotor.md)
- [Cold-climate operation and icing](../../topics/cold-climate-operation.md)
- [Daily Turbine Checklist Form CHK-05 for WTG-05, 14/07/2026](../../sources/chk-05-daily-checklist-wtg-05-2026-07-14.md)
- [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge](../../sources/2025-05-20-re-lws-ts-48213-sb-lws-2025-07-applicability.md)
- [Environmental permit and night curtailment](../../topics/environmental-compliance.md)
- [Fabrikam FGT-3200](../product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../organisation/fabrikam-getriebetechnik.md)
- [Fabrikam Supplier Note on PO-76994 HSS Bearings and PWG 220 Follow-up](../../sources/2026-08-03-lieferantenhinweis-fabrikam.md)
- [FGT-P-11872](../part/fgt-p-11872.md)
- [Gearbox Fundamentals for Wind Technicians](../../sources/gearbox-fundamentals.md)
- [Gearbox lubrication and oil changes](../../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../../topics/gearbox-condition-monitoring.md)
- [generator](generator.md)
- [Generator brushes and electrical systems](../../topics/generator-and-electrical.md)
- [Grid connection and grid operator instructions](../../topics/grid-operations.md)
- [HSS bearing](hss-bearing.md)
- [Litware LT-32](../product/lt-32.md)
- [Litware Wind Systems](../organisation/litware-wind-systems.md)
- [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt](../../sources/lws-mm-gbx-32-revd-gearbox-maintenance-manual-excerpt.md)
- [LWS-P-30422](../part/lws-p-30422.md)
- [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm](../../sources/maintenance-plan-2026.md)
- [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220](../../sources/moc-2025-012-gearbox-oil-grade-change.md)
- [Monthly O&M Review Minutes – 2026-06-18](../../sources/2026-06-18-monthly-om-review-minutes.md)
- [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil](../../sources/tr-oa-2026-0614-oil-analysis-wtg-07.md)
- [oil filter element](oil-filter.md)
- [planetary stage](planetary-stage.md)
- [Proseware Lubricants](../organisation/proseware-lubricants.md)
- [Proseware PWG 220](../product/pwg-220.md)
- [Proseware PWG 320](../product/pwg-320.md)
- [PWS-220-D208](../part/pws-220-d208.md)
- [PWS-320-D208](../part/pws-320-d208.md)
- [Quellmoor Ridge Wind Farm](../asset/quellmoor-ridge-wind-farm.md)
- [Quellmoor Ridge Wind Farm Onboarding and Site Rules (February 2025)](../../sources/onboarding-and-site-rules.md)
- [S510 Stopped - fault](../status-code/s510.md)
- [Safety, isolation and work at height](../../topics/safety-and-access.md)
- [SB-LWS-2025-07 Gearbox oil viscosity grade change for LT-32 CCV turbines](../bulletin/sb-lws-2025-07.md)
- [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines](../../sources/sb-lws-2025-07-reva-gearbox-oil-cold-climate.md)
- [SCADA alarm and status log, 2026-04-01 to 2026-08-31](../../sources/scada-alarm-log-2026-04-01-2026-08-31.md)
- [SOP-GBX-010 - Gearbox oil change, Revision A](../../sources/sop-gbx-010-reva-gearbox-oil-change.md)
- [SOP-GBX-010 Gearbox oil change](../procedure/sop-gbx-010.md)
- [SOP-GBX-010 Rev. B - Gearbox oil change](../../sources/sop-gbx-010-revb-gearbox-oil-change.md)
- [Spare Parts Stock Snapshot 2026-07-21 for Quellmoor Ridge O&M Building](../../sources/spare-parts-stock-2026-07-21.md)
- [Spare parts, stock levels and supply](../../topics/spare-parts-and-supply.md)
- [SPL-012 Gearbox oil level check](../procedure/spl-012.md)
- [SPL-012 Gearbox Oil Level Check](../../sources/spl-012-gearbox-oil-level-check.md)
- [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion](../../sources/2025-11-12-toolbox-talk-cold-weather-start-up.md)
- [Training, site rules and acronyms](../../topics/training-and-onboarding.md)
- [Trey Research Laboratories](../organisation/trey-research-laboratories.md)
- [Work Orders Export through 2026-08-31](../../sources/work-orders-export-2026-08-31.md)
- [WTG-01](../asset/wtg-01.md)
- [WTG-02](../asset/wtg-02.md)
- [WTG-07](../asset/wtg-07.md)
- [WTG-09](../asset/wtg-09.md)
- [WTG-12](../asset/wtg-12.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 1](../../evidence/src-1c261d5b87b5/p0001.md) · ✓ quote verified
[^c2]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../../evidence/src-1c261d5b87b5/p0002.md) · ✓ quote verified
[^c3]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 3](../../evidence/src-1c261d5b87b5/p0003.md) · ✓ quote verified
[^c4]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 1](../../evidence/src-c4370c220559/p0001.md) · ✓ quote verified
[^c5]: [SB-LWS-2025-07 Rev. A - Gearbox oil viscosity grade change for LT-32 CCV turbines — p. 2](../../evidence/src-c4370c220559/p0002.md) · ✓ quote verified
[^c6]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../../evidence/src-1c261d5b87b5/p0005.md) · ✓ quote verified
[^c7]: [MOC-2025-012 - Gearbox Oil Grade Change to PWG 220 — ¶ 6](../../evidence/src-a20331a5431f/para-0006.md) · ✓ quote verified
[^c8]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 1](../../evidence/src-990a047180b7/p0001.md) · ✓ quote verified
[^c9]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 5](../../evidence/src-70224c3b9c9f/para-0005.md) · ✓ quote verified
[^c10]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 7](../../evidence/src-70224c3b9c9f/para-0007.md) · ✓ quote verified
[^c11]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 20](../../evidence/src-70224c3b9c9f/para-0020.md) · ✓ quote verified
[^c12]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 30](../../evidence/src-70224c3b9c9f/para-0030.md) · ✓ quote verified
[^c13]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 35](../../evidence/src-70224c3b9c9f/para-0035.md) · ✓ quote verified
[^c14]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 38](../../evidence/src-70224c3b9c9f/para-0038.md) · ✓ quote verified
[^c15]: [SOP-GBX-010 Rev. B - Gearbox oil change — ¶ 42](../../evidence/src-70224c3b9c9f/para-0042.md) · ✓ quote verified
[^c16]: [8D report INC-2026-006 - Repeated gearbox oil over-temperature on WTG-07 (revision 2026-07-10) — table 1, row 3](../../evidence/src-86cb00fd2f6b/tbl-01-r0003-r0003.md) · table
[^c17]: [Asset Register 2026 of Quellmoor Ridge Wind Farm, revision 2026-01-12 — sheet "Turbines", row 10](../../evidence/src-b342a2d5bfdf/sheet-turbines-r0010-r0010.md) · table
[^c18]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 2](../../evidence/src-aba30cb7207f/sheet-tasks-r0002-r0002.md) · table
[^c19]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 3](../../evidence/src-aba30cb7207f/sheet-tasks-r0003-r0003.md) · table
[^c20]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Tasks", row 4](../../evidence/src-aba30cb7207f/sheet-tasks-r0004-r0004.md) · table
[^c21]: [Maintenance Plan 2026, Issue 2 — Quellmoor Ridge Wind Farm — sheet "Plan 2026", row 19](../../evidence/src-aba30cb7207f/sheet-plan-2026-r0019-r0019.md) · table
[^c22]: [SPL-012 Gearbox Oil Level Check — slide 1](../../evidence/src-9a6703e054dc/slide-01.md) · ✓ quote verified
[^c23]: [SPL-012 Gearbox Oil Level Check — slide 2](../../evidence/src-9a6703e054dc/slide-02.md) · ✓ quote verified
[^c24]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 32](../../evidence/src-36f5b999211a/r0032-r0032.md) · table
[^c25]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 33](../../evidence/src-36f5b999211a/r0033-r0033.md) · table
[^c26]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 34](../../evidence/src-36f5b999211a/r0034-r0034.md) · table
[^c27]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 35](../../evidence/src-36f5b999211a/r0035-r0035.md) · table
[^c28]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 550](../../evidence/src-36f5b999211a/r0550-r0550.md) · table
[^c29]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 551](../../evidence/src-36f5b999211a/r0551-r0551.md) · table
[^c30]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 552](../../evidence/src-36f5b999211a/r0552-r0552.md) · table
[^c31]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 946](../../evidence/src-36f5b999211a/r0946-r0946.md) · table
[^c32]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 947](../../evidence/src-36f5b999211a/r0947-r0947.md) · table
[^c33]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 948](../../evidence/src-36f5b999211a/r0948-r0948.md) · table
[^c34]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1330](../../evidence/src-36f5b999211a/r1330-r1330.md) · table
[^c35]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1366](../../evidence/src-36f5b999211a/r1366-r1366.md) · table
[^c36]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1436](../../evidence/src-36f5b999211a/r1436-r1436.md) · table
[^c37]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1485](../../evidence/src-36f5b999211a/r1485-r1485.md) · table
[^c38]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1654](../../evidence/src-36f5b999211a/r1654-r1654.md) · table
[^c39]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1655](../../evidence/src-36f5b999211a/r1655-r1655.md) · table
[^c40]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1660](../../evidence/src-36f5b999211a/r1660-r1660.md) · table
[^c41]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1661](../../evidence/src-36f5b999211a/r1661-r1661.md) · table
[^c42]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1896](../../evidence/src-36f5b999211a/r1896-r1896.md) · table
[^c43]: [SCADA alarm and status log, 2026-04-01 to 2026-08-31 — row 1897](../../evidence/src-36f5b999211a/r1897-r1897.md) · table
[^c44]: [Work Orders Export through 2026-08-31 — row 2](../../evidence/src-9fd435ef5956/r0002-r0002.md) · table
[^c45]: [Work Orders Export through 2026-08-31 — row 3](../../evidence/src-9fd435ef5956/r0003-r0003.md) · table
[^c46]: [Work Orders Export through 2026-08-31 — row 4](../../evidence/src-9fd435ef5956/r0004-r0004.md) · table
[^c47]: [Work Orders Export through 2026-08-31 — row 5](../../evidence/src-9fd435ef5956/r0005-r0005.md) · table
[^c48]: [Work Orders Export through 2026-08-31 — row 6](../../evidence/src-9fd435ef5956/r0006-r0006.md) · table
[^c49]: [Work Orders Export through 2026-08-31 — row 7](../../evidence/src-9fd435ef5956/r0007-r0007.md) · table
[^c50]: [Work Orders Export through 2026-08-31 — row 8](../../evidence/src-9fd435ef5956/r0008-r0008.md) · table
[^c51]: [Work Orders Export through 2026-08-31 — row 9](../../evidence/src-9fd435ef5956/r0009-r0009.md) · table
[^c52]: [Work Orders Export through 2026-08-31 — row 10](../../evidence/src-9fd435ef5956/r0010-r0010.md) · table
[^c53]: [Work Orders Export through 2026-08-31 — row 11](../../evidence/src-9fd435ef5956/r0011-r0011.md) · table
[^c54]: [Work Orders Export through 2026-08-31 — row 12](../../evidence/src-9fd435ef5956/r0012-r0012.md) · table
[^c55]: [Work Orders Export through 2026-08-31 — row 13](../../evidence/src-9fd435ef5956/r0013-r0013.md) · table
[^c56]: [Work Orders Export through 2026-08-31 — row 56](../../evidence/src-9fd435ef5956/r0056-r0056.md) · table
[^c57]: [Work Orders Export through 2026-08-31 — row 57](../../evidence/src-9fd435ef5956/r0057-r0057.md) · table
[^c58]: [Work Orders Export through 2026-08-31 — row 58](../../evidence/src-9fd435ef5956/r0058-r0058.md) · table
[^c59]: [Work Orders Export through 2026-08-31 — row 59](../../evidence/src-9fd435ef5956/r0059-r0059.md) · table
[^c60]: [Work Orders Export through 2026-08-31 — row 60](../../evidence/src-9fd435ef5956/r0060-r0060.md) · table
[^c61]: [Work Orders Export through 2026-08-31 — row 61](../../evidence/src-9fd435ef5956/r0061-r0061.md) · table
[^c62]: [Work Orders Export through 2026-08-31 — row 62](../../evidence/src-9fd435ef5956/r0062-r0062.md) · table
[^c63]: [Work Orders Export through 2026-08-31 — row 63](../../evidence/src-9fd435ef5956/r0063-r0063.md) · table
[^c64]: [Work Orders Export through 2026-08-31 — row 64](../../evidence/src-9fd435ef5956/r0064-r0064.md) · table
[^c65]: [Work Orders Export through 2026-08-31 — row 65](../../evidence/src-9fd435ef5956/r0065-r0065.md) · table
[^c66]: [Work Orders Export through 2026-08-31 — row 66](../../evidence/src-9fd435ef5956/r0066-r0066.md) · table
[^c67]: [Work Orders Export through 2026-08-31 — row 67](../../evidence/src-9fd435ef5956/r0067-r0067.md) · table
[^c68]: [Gearbox Fundamentals for Wind Technicians — slide 1](../../evidence/src-1b5b5135881d/slide-01.md) · ✓ quote verified
[^c69]: [Gearbox Fundamentals for Wind Technicians — slide 2](../../evidence/src-1b5b5135881d/slide-02.md) · ✓ quote verified
[^c70]: [Gearbox Fundamentals for Wind Technicians — slide 3](../../evidence/src-1b5b5135881d/slide-03.md) · ✓ quote verified
[^c71]: [Gearbox Fundamentals for Wind Technicians — slide 5](../../evidence/src-1b5b5135881d/slide-05.md) · ✓ quote verified
[^c72]: [Gearbox Fundamentals for Wind Technicians — slide 8](../../evidence/src-1b5b5135881d/slide-08.md) · ✓ quote verified
[^c73]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 8](../../evidence/src-15df96905f07/para-0008.md) · ✓ quote verified
[^c74]: [Monthly O&M Review Minutes – 2026-06-18 — ¶ 10](../../evidence/src-15df96905f07/para-0010.md) · ✓ quote verified
[^c75]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 5–6](../../evidence/src-0df0d0598e76/msg-body-l0005-l0006.md) · ✓ quote verified
[^c76]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 16–23](../../evidence/src-0df0d0598e76/msg-body-l0016-l0023.md) · ✓ quote verified
[^c77]: [Email RE: LWS-TS-48213 Applicability of SB-LWS-2025-07 Rev. A to Quellmoor Ridge — message body, lines 25–26](../../evidence/src-0df0d0598e76/msg-body-l0025-l0026.md) · ✓ quote verified
[^c78]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 01:23–01:34](../../evidence/src-ecc004b57dd5/cue-00-01-23.md) · ✓ quote verified
[^c79]: [Toolbox Talk: Cold-Weather Start-Up After PWG 220 Conversion — 02:45–02:55](../../evidence/src-ecc004b57dd5/cue-00-02-45.md) · ✓ quote verified
[^c80]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 4](../../evidence/src-90ea27f71f0f/para-0004.md) · ✓ quote verified
[^c81]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 6](../../evidence/src-90ea27f71f0f/para-0006.md) · ✓ quote verified
[^c82]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 17](../../evidence/src-90ea27f71f0f/para-0017.md) · ✓ quote verified
[^c83]: [SOP-GBX-010 - Gearbox oil change, Revision A — ¶ 27](../../evidence/src-90ea27f71f0f/para-0027.md) · ✓ quote verified
