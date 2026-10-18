---
id: src-1c261d5b87b5
type: source
title: LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt
summary: This is a Litware Wind Systems maintenance manual excerpt for the Litware LT-32 gearbox chapter, issued as LWS-MM-GBX-32 Rev. D. It covers gearbox description, lubrication, oil change overview, inspection and condition monitoring, oil analysis and vibration limits, and troubleshooting of gearbox alarms.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- maintenance-manual
- oem-documentation
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-1c261d5b87b5
source_path: full/oem/LWS-MM-GBX-32_RevD_gearbox-maintenance-manual-excerpt.pdf
source_hash: sha256:76e7c62cdb5ac228eddc00e376c10e37dc1512c6cea2c16b5b76752abd7ead04
media_type: application/pdf
doc_type: maintenance-manual
category: oem-documentation
doc_number: LWS-MM-GBX-32
revision: D
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: 5
entities:
- alarm-code:a2101
- alarm-code:a2102
- alarm-code:a2110
- alarm-code:a2120
- alarm-code:a2130
- alarm-code:a2140
- component:cooler-fan-motor
- component:gearbox
- component:gearbox-heater
- component:generator
- component:hss-bearing
- component:ims-bearing
- component:oil-cooler
- component:oil-filter
- component:planetary-stage
- organisation:fabrikam-getriebetechnik
- organisation:litware-wind-systems
- organisation:proseware-lubricants
- part:fgt-p-11872
- part:fgt-p-11880
- part:fgt-p-13010
- part:fgt-p-14002
- part:fgt-p-21904
- part:fgt-p-22328
- part:fgt-p-22331
- part:lws-p-30418
- part:lws-p-30422
- product:fgt-3200
- product:lt-32
- product:pwg-320
topics:
- topic:cold-climate-operation
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
- topic:generator-and-electrical
authority: 8
extraction:
  adapter: content-understanding
  version: 1.0.0+cu.2025-11-01
  provenance_mix:
    native-text: 140
    model-description: 1
---

# LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

This is a [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) maintenance manual excerpt for the [Litware LT-32](../entities/product/lt-32.md) [gearbox](../entities/component/gearbox.md) chapter, issued as LWS-MM-GBX-32 Rev. D. It covers gearbox description, lubrication, oil change overview, inspection and condition monitoring, oil analysis and vibration limits, and troubleshooting of gearbox alarms.

## Key facts

- The excerpt is Chapter 4, [Gearbox](../entities/component/gearbox.md), of document LWS-MM-GBX-32 Rev. D, issued by [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) on 2024-03-15.[^c1]
- The document applies to [LT-32](../entities/product/lt-32.md) turbines of all variants with the [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearbox.[^c1]
- Gearbox work requires the turbine to be stopped, the rotor locked, and the drivetrain isolated according to the operator's lockout procedure; hot oil up to 80 °C can cause burns.[^c1]
- Litware Wind Systems publishes changes to the gearbox chapter as service bulletins, and the bulletin register must be checked before planning gearbox work.[^c1]
- The LT-32 uses a Fabrikam FGT-3200 three-stage gearbox with one [planetary stage](../entities/component/planetary-stage.md) followed by two parallel helical stages.[^c2]
- The gearbox overall ratio is 1:118.4; at a rated rotor speed of 12.7 rpm, the output pinion shaft drives the [generator](../entities/component/generator.md) at 1,500 rpm.[^c2]
- The FGT-3200 gearbox rated input torque is 2,410 kNm and its dry mass is 21.6 t.[^c2]
- The gearbox lubrication system uses splash and forced lubrication, with a shaft-driven pump for operation and an electric pump for start-up and flushing.[^c2]
- The oil passes through a 10 micron inline filter and an air/[oil cooler](../entities/component/oil-cooler.md) with an electric fan; a thermostatic valve sends oil through the cooler above 45 °C.[^c2]
- Three immersion heaters rated 3 x 1.5 kW warm the oil sump before a cold start.[^c2]
- Only the lubricant listed in Table 4-2 is approved for the FGT-3200 gearbox, and lubricants of different brands or viscosity grades must not be mixed.[^c3]
- The approved gear oil is [Proseware PWG 320](../entities/product/pwg-320.md) with viscosity grade ISO VG 320 and synthetic PAO base oil.[^c3]
- The total oil volume is 410 L, made up of 330 L in the gearbox sump and 80 L in the cooling and filter circuit.[^c3]
- The oil change interval is 5 years, or earlier if laboratory analysis requires it; the oil sampling interval is 6 months.[^c3]
- The filter element [FGT-P-11872](../entities/part/fgt-p-11872.md) must be replaced every 12 months or at alarm [A2140](../entities/alarm-code/a2140.md), and breather [FGT-P-11880](../entities/part/fgt-p-11880.md) must be replaced every 12 months.[^c3]
- Normal oil sump temperature in operation is 50 to 65 °C.[^c3]
- The cooler-circuit thermostatic valve opening temperature is 45°C.[^c3]
- Oil sump temperature warning [A2101](../entities/alarm-code/a2101.md) is set at 75°C, and oil sump temperature trip [A2102](../entities/alarm-code/a2102.md) is set at 82 °C.[^c3]
- Minimum oil sump temperature before start-up is +10 °C, with heaters on below +10 °C.[^c3]
- The turbine controller blocks drivetrain start until the oil sump reaches the minimum start-up temperature, and the start inhibit must not be bypassed.[^c3]
- During oil change, oil is to be drained at an oil temperature between 40 and 60 °C so deposits drain with the oil.[^c3]
- During oil change, the filter element FGT-P-11872 is replaced, the magnetic plug is inspected, and filling is only through a filter cart with a 10 micron element.[^c3]
- After an oil change, the oil level is checked at the sight glass after 20 minutes of standstill, and a reference oil sample is taken after 24 hours of operation.[^c3]
- Oil-change tightening torques are 280 Nm for the drain plug, 85 Nm for filter housing cover screws, 210 Nm for oil cooler hose flange screws, and 22 Nm for sight glass retaining screws.[^c3]
- Inspection intervals are 6 months for visual inspection and leak check, 6 months for oil sampling and laboratory analysis, 24 months for endoscope inspection, continuous for vibration monitoring, 12 months for filter element replacement, and as required for oil cooler radiator cleaning.[^c4]
- Oil analysis alert/alarm limits are 50 ppm/100 ppm for iron, 25 ppm/50 ppm for copper, 15 ppm/25 ppm for silicon, and 300 ppm/500 ppm for water.[^c4]
- Oil analysis alert/alarm limits are +/- 10 %/+/- 15 % for viscosity change at 40 ℃, 60/120 for PQ index, and 19/17/14 and 21/19/16 for cleanliness ISO 4406 against a target of 17/15/12.[^c4]
- For output stage HSS bearings, velocity RMS limits are 3.5 mm/s alert and 4.5 mm/s alarm; above alarm level, a bearing inspection is planned and load is reduced if the trend keeps rising.[^c4]
- Alarm A2101, Gearbox oil sump temperature high at 75 °C, can be caused by cooling, oil level, load/ambient-temperature, or bearing issues; actions include checking fan rotation and motor current, cleaning the radiator, checking valve insert [LWS-P-30422](../entities/part/lws-p-30422.md), checking oil level, reviewing vibration trend, and taking an oil sample.[^c5]
- Alarm A2102, Gearbox oil sump temperature trip at 82 °C, stops the turbine automatically; the cooling circuit is inspected before restart, and reset is not performed more than once without inspection.[^c5]
- Alarm [A2110](../entities/alarm-code/a2110.md), Gearbox HSS bearing temperature high at 90 °C, can be caused by bearing damage or lubrication starvation; checks are vibration trend review and endoscope inspection of the bearing.[^c5]
- Alarm [A2120](../entities/alarm-code/a2120.md), Gearbox oil pressure low at 0.8 bar, can be caused by cold oil at start-up, pump fault, or blocked filter; actions are to allow heater time at cold start and check the pump and filter.[^c5]
- Alarm A2140, Gearbox oil filter differential pressure high at 2.5 bar, can be caused by a clogged filter element or cold oil; the action is to replace filter element FGT-P-11872.[^c5]

## Contents

### Document control, safety, and contents

The excerpt is from the [Litware LT-32](../entities/product/lt-32.md) maintenance manual and is Chapter 4, [Gearbox](../entities/component/gearbox.md), of document LWS-MM-GBX-32 Rev. D, issued by [Litware Wind Systems](../entities/organisation/litware-wind-systems.md) on 2024-03-15.[^c6]

The document applies to LT-32 turbines of all variants with [Fabrikam FGT-3200](../entities/product/fgt-3200.md) gearbox, superseding Rev. C of 2021-06-30, which is marked withdrawn.[^c6]

The document is marked fictional and not for operational use.[^c6]

Gearbox work requires the turbine to be stopped, the rotor locked, and the drivetrain isolated according to the operator's lockout procedure; hot oil up to 80 °C can cause burns, and site-defined personal protective equipment is required.[^c6]

The excerpt contents are gearbox description, lubrication, oil change overview, inspection and condition monitoring, and troubleshooting of gearbox alarms.[^c6]

Changes to the chapter are published as Litware Wind Systems service bulletins, and the bulletin register is to be checked before planning gearbox work.[^c6]

**Table t01** · p. 1

| Row | Field | Value |
| --- | --- | --- |
| 2 | Document number | LWS-MM-GBX-32 |
| 3 | Revision | D |
| 4 | Issue date | 2024-03-15 |
| 5 | Applies to | LT-32 turbines (all variants) with Fabrikam FGT-3200 gearbox |
| 6 | Previous revision | Rev. C of 2021-06-30 (withdrawn) |
| 7 | Language | English (original) |

Agents can query this table as `t01` with the `query_table` tool.

### 4.1 Gearbox description

The [LT-32](../entities/product/lt-32.md) uses a [Fabrikam FGT-3200](../entities/product/fgt-3200.md) three-stage [gearbox](../entities/component/gearbox.md) with one [planetary stage](../entities/component/planetary-stage.md) followed by two parallel helical stages.[^c7]

The gearbox overall ratio is 1:118.4, and at 12.7 rpm rated rotor speed the output pinion shaft drives the [generator](../entities/component/generator.md) at 1,500 rpm.[^c7]

The gearbox rated input torque is 2,410 kNm and its dry mass is 21.6 t.[^c7]

The gearbox is lubricated by splash and forced lubrication; a shaft-driven pump supplies bearings and gear meshes during operation, while an electric pump runs during start-up and flushing.[^c7]

Oil passes an inline 10 micron filter and an air/[oil cooler](../entities/component/oil-cooler.md) with an electric fan, and a thermostatic valve sends oil through the cooler above 45 °C.[^c7]

Three immersion heaters rated 3 x 1.5 kW warm the oil sump before cold start.[^c7]

Figure 4-1 is an exploded view of the FGT-3200 gearbox with item numbers linked to Table 4-1.[^c8]

**Table t02** · p. 2

| Row | Item | Description | Spare part number |
| --- | --- | --- | --- |
| 2 | 1 | Housing cover, rotor side | - |
| 3 | 2 | Planet carrier with three planet gears | - |
| 4 | 3 | Ring gear | - |
| 5 | 4 | Sun pinion shaft | - |
| 6 | 5 | Second-stage gear wheel | - |
| 7 | 6 | Intermediate pinion shaft | - |
| 8 | 7 | [IMS bearing](../entities/component/ims-bearing.md) set | [FGT-P-21904](../entities/part/fgt-p-21904.md) |
| 9 | 8 | Output pinion shaft | - |
| 10 | 9 | [HSS bearing](../entities/component/hss-bearing.md), rotor side | [FGT-P-22331](../entities/part/fgt-p-22331.md) |
| 11 | 10 | HSS bearing, generator side | [FGT-P-22328](../entities/part/fgt-p-22328.md) |
| 12 | 11 | Oil cooler with fan motor 1.5 kW | [LWS-P-30418](../entities/part/lws-p-30418.md) (fan motor) |
| 13 | 12 | Thermostatic valve insert | [LWS-P-30422](../entities/part/lws-p-30422.md) |
| 14 | 13 | [Oil filter element](../entities/component/oil-filter.md), 10 micron | [FGT-P-11872](../entities/part/fgt-p-11872.md) |
| 15 | 14 | Breather with desiccant | [FGT-P-11880](../entities/part/fgt-p-11880.md) |
| 16 | 15 | Oil level sight glass | [FGT-P-13010](../entities/part/fgt-p-13010.md) |
| 17 | 16 | Oil sampling valve | [FGT-P-14002](../entities/part/fgt-p-14002.md) |

Agents can query this table as `t02` with the `query_table` tool.

### 4.2 Lubrication and operating temperatures

Only the lubricant listed in Table 4-2 is approved for the [FGT-3200](../entities/product/fgt-3200.md) [gearbox](../entities/component/gearbox.md), and lubricants of different brands or viscosity grades are not to be mixed.[^c9]

The approved lubricant specification table lists [Proseware PWG 320](../entities/product/pwg-320.md) gear oil, ISO VG 320 viscosity grade, synthetic PAO base oil, 410 L total oil volume, oil-change and oil-sampling intervals, and replacement intervals for the filter element and breather.[^c9]

The operating temperature table gives normal oil sump temperature, thermostatic-valve opening temperature, warning and trip thresholds, and minimum oil sump temperature before start-up.[^c9]

The turbine controller blocks drivetrain start until the oil sump reaches the minimum start-up temperature, and the start inhibit must not be bypassed.[^c9]

**Table t03** · p. 3

| Row | Item | Specification |
| --- | --- | --- |
| 2 | Gear oil | Proseware PWG 320 |
| 3 | Viscosity grade | ISO VG 320 |
| 4 | Base oil | synthetic PAO |
| 5 | Total oil volume | 410 L (gearbox sump 330 L + cooling and filter circuit 80 L) |
| 6 | Oil change interval | 5 years, or earlier when the laboratory analysis requires it |
| 7 | Oil sampling interval | 6 months |
| 8 | Filter element [FGT-P-11872](../entities/part/fgt-p-11872.md) | replace every 12 months or at alarm [A2140](../entities/alarm-code/a2140.md) |
| 9 | Breather [FGT-P-11880](../entities/part/fgt-p-11880.md) | replace every 12 months |

Agents can query this table as `t03` with the `query_table` tool.

**Table t04** · p. 3

| Row | Parameter | Value |
| --- | --- | --- |
| 2 | Normal oil sump temperature in operation | 50 to 65 °C |
| 3 | Thermostatic valve opening (cooler circuit) | 45°C |
| 4 | Warning [A2101](../entities/alarm-code/a2101.md) - oil sump temperature high | 75°C |
| 5 | Trip [A2102](../entities/alarm-code/a2102.md) - oil sump temperature trip | 82 °C |
| 6 | Minimum oil sump temperature before start-up | +10 °C (heaters on below +10 °C) |

Agents can query this table as `t04` with the `query_table` tool.

### 4.3 Oil change overview

The detailed oil change procedure is defined by the operator, while the manual gives OEM requirements.[^c9]

The OEM requirements include stopping the turbine, locking the rotor, isolating the drivetrain, draining oil between 40 and 60 °C, replacing filter element [FGT-P-11872](../entities/part/fgt-p-11872.md), inspecting the magnetic plug, filling only through a 10 micron filter cart, checking the sight glass after 20 minutes of standstill, and taking a reference oil sample after 24 hours of operation.[^c9]

Table 4-4 gives tightening torques for oil-change work, covering the drain plug, filter housing cover screws, [oil cooler](../entities/component/oil-cooler.md) hose flange screws, and sight glass retaining screws.[^c9]

**Table t05** · p. 3

| Row | Joint | Thread | Tightening torque |
| --- | --- | --- | --- |
| 2 | Drain plug | M48 x 2 | 280 Nm |
| 3 | Filter housing cover screws | M12 | 85 Nm |
| 4 | Oil cooler hose flange screws | M16 | 210 Nm |
| 5 | Sight glass retaining screws | M8 | 22 Nm |

Agents can query this table as `t05` with the `query_table` tool.

### 4.4 Inspection and condition monitoring

Table 4-5 defines inspection intervals for visual inspection and leak check, oil sampling and laboratory analysis, endoscope inspection of gear teeth and bearings, vibration monitoring, filter element replacement, and [oil cooler](../entities/component/oil-cooler.md) radiator cleaning.[^c10]

For output stage HSS bearings on the rotor side and [generator](../entities/component/generator.md) side, velocity RMS limits are 3.5 mm/s alert and 4.5 mm/s alarm.[^c10]

Above the vibration alarm level, bearing inspection is planned and load is reduced if the trend keeps rising.[^c10]

**Table t06** · p. 4

| Row | Task | Interval |
| --- | --- | --- |
| 2 | Visual inspection and leak check | 6 months |
| 3 | Oil sampling and laboratory analysis | 6 months |
| 4 | Endoscope inspection of gear teeth and bearings | 24 months |
| 5 | Vibration monitoring (condition monitoring system) | continuous |
| 6 | Filter element replacement | 12 months |
| 7 | Oil cooler radiator cleaning | as required |

Agents can query this table as `t06` with the `query_table` tool.

**Table t07** · p. 4

| Row | Parameter | Alert | Alarm |
| --- | --- | --- | --- |
| 2 | Iron (Fe) | 50 ppm | 100 ppm |
| 3 | Copper (Cu) | 25 ppm | 50 ppm |
| 4 | Silicon (Si) | 15 ppm | 25 ppm |
| 5 | Water | 300 ppm | 500 ppm |
| 6 | Viscosity change at 40 ℃ | +/- 10 % | +/- 15 % |
| 7 | PQ index | 60 | 120 |
| 8 | Cleanliness ISO 4406 (target 17/15/12) | 19/17/14 | 21/19/16 |

Agents can query this table as `t07` with the `query_table` tool.

### 4.5 Troubleshooting of gearbox alarms

Table 4-7 lists [gearbox](../entities/component/gearbox.md) alarms [A2101](../entities/alarm-code/a2101.md), [A2102](../entities/alarm-code/a2102.md), [A2110](../entities/alarm-code/a2110.md), [A2120](../entities/alarm-code/a2120.md), [A2130](../entities/alarm-code/a2130.md), and [A2140](../entities/alarm-code/a2140.md), with messages, possible causes, and checks or actions.[^c11]

A2101 covers high gearbox oil sump temperature at 75 °C, with possible causes including cooler fan motor fault, blocked radiator fins, stuck thermostatic valve insert, low oil level, high load and ambient temperature, and bearing damage.[^c11]

A2102 covers gearbox oil sump temperature trip at 82 °C and states that the turbine stops automatically; the cooling circuit is inspected before restart and the alarm is not reset more than once without inspection.[^c11]

A2110 covers gearbox HSS bearing temperature high at 90 °C, with bearing damage and lubrication starvation as possible causes.[^c11]

A2120 covers gearbox oil pressure low at 0.8 bar, with cold oil at start-up, pump fault, and blocked filter as possible causes.[^c11]

A2130 covers gearbox oil level low due to leaks at seals, hoses, or plugs, with actions to repair the leak and top up with approved oil.[^c11]

A2140 covers gearbox oil filter differential pressure high at 2.5 bar, with clogged filter element or cold oil as possible causes, and the action is to replace filter element [FGT-P-11872](../entities/part/fgt-p-11872.md).[^c11]

**Table t08** · p. 5

| Row | Code | Message | Possible causes | Checks and actions |
| --- | --- | --- | --- | --- |
| 2 | A2101 | Gearbox oil sump temperature high (75 °C) | Cooler fan motor fault or reduced fan speed; radiator fins blocked; thermostatic valve insert stuck; low oil level; full load at high ambient temperature; bearing damage | Check fan rotation and motor current; clean the radiator; check valve insert [LWS-P-30422](../entities/part/lws-p-30422.md); check the oil level; review the vibration trend; take an oil sample |
| 3 | A2102 | Gearbox oil sump temperature trip (82 °C) | As for A2101; the turbine stops automatically | Inspect the cooling circuit before restart; do not reset more than once without inspection |
| 4 | A2110 | Gearbox HSS bearing temperature high (90 °C) | Bearing damage; lubrication starvation | Check the vibration trend; endoscope inspection of the bearing |
| 5 | A2120 | Gearbox oil pressure low (0.8 bar) | Cold oil at start-up; pump fault; filter blocked | Allow heater time at cold start; check the pump and the filter |
| 6 | A2130 | Gearbox oil level low | Leak at seals, hoses or plugs | Find and repair the leak; top up with the approved oil |
| 7 | A2140 | Gearbox oil filter differential pressure high (2.5 bar) | Filter element clogged; cold oil | Replace filter element FGT-P-11872 |

Agents can query this table as `t08` with the `query_table` tool.

## Figures

- **Figure f01** (p. 2): Figure 4-1 - Exploded view of the [FGT-3200](../entities/product/fgt-3200.md) [gearbox](../entities/component/gearbox.md) (item numbers in table 4-1). Generated description: A black-and-white technical schematic shows multiple labeled parts in a machine layout, with numbered callouts from 1 to 16 and arrows indicating rotor side at the lower left and [generator](../entities/component/generator.md) side at the upper right. The drawing includes rectangular housings, shafts, a large striped block, vertical scale-like bars, and several crosshatched cylindrical or beam elements aligned along a dashed centerline. No legend or title is visible, and the figure appears to be an assembly or alignment diagram rather than a photograph.[^c8]

## Related

- Components: [gearbox](../entities/component/gearbox.md), [gearbox oil heater](../entities/component/gearbox-heater.md), [generator](../entities/component/generator.md), [HSS bearing](../entities/component/hss-bearing.md), [IMS bearing](../entities/component/ims-bearing.md), [oil cooler](../entities/component/oil-cooler.md), [oil cooler fan motor](../entities/component/cooler-fan-motor.md), [oil filter element](../entities/component/oil-filter.md), [planetary stage](../entities/component/planetary-stage.md)
- Spare parts: [FGT-P-11872](../entities/part/fgt-p-11872.md), [FGT-P-11880](../entities/part/fgt-p-11880.md), [FGT-P-13010](../entities/part/fgt-p-13010.md), [FGT-P-14002](../entities/part/fgt-p-14002.md), [FGT-P-21904](../entities/part/fgt-p-21904.md), [FGT-P-22328](../entities/part/fgt-p-22328.md), [FGT-P-22331](../entities/part/fgt-p-22331.md), [LWS-P-30418](../entities/part/lws-p-30418.md), [LWS-P-30422](../entities/part/lws-p-30422.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Litware LT-32](../entities/product/lt-32.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Alarm codes: [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md), [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md), [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md), [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md), [A2130 Gearbox oil level low](../entities/alarm-code/a2130.md), [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md)
- Organisations: [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Litware Wind Systems](../entities/organisation/litware-wind-systems.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- Topics: [Cold-climate operation and icing](../topics/cold-climate-operation.md), [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md), [Generator brushes and electrical systems](../topics/generator-and-electrical.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [A2101 Gearbox oil sump temperature high](../entities/alarm-code/a2101.md)
- [A2102 Gearbox oil sump temperature trip](../entities/alarm-code/a2102.md)
- [A2110 Gearbox HSS bearing temperature high](../entities/alarm-code/a2110.md)
- [A2120 Gearbox oil pressure low](../entities/alarm-code/a2120.md)
- [A2130 Gearbox oil level low](../entities/alarm-code/a2130.md)
- [A2140 Gearbox oil filter differential pressure high](../entities/alarm-code/a2140.md)
- [Cold-climate operation and icing](../topics/cold-climate-operation.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [FGT-P-11872](../entities/part/fgt-p-11872.md)
- [FGT-P-11880](../entities/part/fgt-p-11880.md)
- [FGT-P-13010](../entities/part/fgt-p-13010.md)
- [FGT-P-14002](../entities/part/fgt-p-14002.md)
- [FGT-P-21904](../entities/part/fgt-p-21904.md)
- [FGT-P-22328](../entities/part/fgt-p-22328.md)
- [FGT-P-22331](../entities/part/fgt-p-22331.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [gearbox oil heater](../entities/component/gearbox-heater.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [generator](../entities/component/generator.md)
- [Generator brushes and electrical systems](../topics/generator-and-electrical.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [IMS bearing](../entities/component/ims-bearing.md)
- [Litware LT-32](../entities/product/lt-32.md)
- [Litware Wind Systems](../entities/organisation/litware-wind-systems.md)
- [LWS-P-30418](../entities/part/lws-p-30418.md)
- [LWS-P-30422](../entities/part/lws-p-30422.md)
- [oil cooler](../entities/component/oil-cooler.md)
- [oil cooler fan motor](../entities/component/cooler-fan-motor.md)
- [oil filter element](../entities/component/oil-filter.md)
- [planetary stage](../entities/component/planetary-stage.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 1](../evidence/src-1c261d5b87b5/p0001.md) · ✓ quote verified
[^c2]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../evidence/src-1c261d5b87b5/p0002.md) · ✓ quote verified
[^c3]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 3](../evidence/src-1c261d5b87b5/p0003.md) · ✓ quote verified
[^c4]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 4](../evidence/src-1c261d5b87b5/p0004.md) · ✓ quote verified
[^c5]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../evidence/src-1c261d5b87b5/p0005.md) · ✓ quote verified
[^c6]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 1](../evidence/src-1c261d5b87b5/p0001.md) · paraphrase
[^c7]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../evidence/src-1c261d5b87b5/p0002.md) · paraphrase
[^c8]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 2](../evidence/src-1c261d5b87b5/p0002.md) · generated description
[^c9]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 3](../evidence/src-1c261d5b87b5/p0003.md) · paraphrase
[^c10]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 4](../evidence/src-1c261d5b87b5/p0004.md) · paraphrase
[^c11]: [LWS-MM-GBX-32 Rev. D — LT-32 Maintenance Manual Chapter 4 Gearbox Excerpt — p. 5](../evidence/src-1c261d5b87b5/p0005.md) · paraphrase
