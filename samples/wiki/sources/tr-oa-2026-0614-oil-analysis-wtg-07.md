---
id: src-990a047180b7
type: source
title: Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil
summary: Trey Research Laboratories issued an oil analysis report for the WTG-07 main gearbox at Quellmoor Ridge. The report records sample details, laboratory results, an alert overall condition, comments on ferrous wear, recommendations, and a recent trend table.
lang: en
sensitivity: public
updated: 2026-10-18
tags:
- lab-and-inspection
- oil-analysis-report
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
source_id: src-990a047180b7
source_path: full/lab-inspection/TR-OA-2026-0614_oil-analysis-WTG-07.pdf
source_hash: sha256:875982f903f41e2994ecf50b149d9e4c2dcc3d1a27d77b8f5a3527053c292ea6
media_type: application/pdf
doc_type: oil-analysis-report
category: lab-and-inspection
doc_number: null
revision: null
status: current
supersedes: []
superseded_by: []
original_lang: en
pages: 2
entities:
- asset:quellmoor-ridge-wind-farm
- asset:wtg-07
- component:gearbox
- component:hss-bearing
- component:oil-filter
- organisation:contoso-renewables
- organisation:fabrikam-getriebetechnik
- organisation:proseware-lubricants
- organisation:trey-research-laboratories
- product:fgt-3200
- product:pwg-220
- product:pwg-320
topics:
- topic:gearbox-condition-monitoring
- topic:gearbox-lubrication
authority: 7
extraction:
  adapter: content-understanding
  version: 1.0.0+cu.2025-11-01
  provenance_mix:
    native-text: 61
    model-description: 1
---

# Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil

> FICTIONAL SAMPLE - Contoso Renewables, Quellmoor Ridge Wind Farm and every organisation, person, product and value in this wiki are invented. Not for operational use.

[Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md) issued an oil analysis report for the [WTG-07](../entities/asset/wtg-07.md) main [gearbox](../entities/component/gearbox.md) at [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md). The report records sample details, laboratory results, an alert overall condition, comments on ferrous wear, recommendations, and a recent trend table.

## Key facts

- The report is oil analysis report TR-OA-2026-0614 for [gearbox](../entities/component/gearbox.md) oil from [WTG-07](../entities/asset/wtg-07.md) at [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c1]
- The customer is [Contoso Renewables](../entities/organisation/contoso-renewables.md), Quellmoor Ridge Wind Farm.[^c1]
- The asset is the WTG-07 main gearbox, a [Fabrikam FGT-3200](../entities/product/fgt-3200.md) with serial FGT-3200-18-07752.[^c1]
- The lubricant is [Proseware PWG 220](../entities/product/pwg-220.md), ISO VG 220, in service since 2025-10-15.[^c1]
- The sample ID is TR-26-11873, sampled on 2026-06-10 by Callum Rydings from the sampling valve with oil at operating temperature.[^c1]
- The sample was received on 2026-06-12 and reported on 2026-06-17, and the analyst was Imogen Thackwray, Senior Lubrication Analyst.[^c1]
- The overall condition is ALERT and action is required.[^c1]
- Viscosity at 40 °C was 229 mm2/s, within the alert-limit range of 198 to 242, with normal status.[^c1]
- Water was 180 ppm against an alert limit of 300 ppm, with normal status.[^c1]
- Total acid number was 0.9 mg KOH/g against an alert limit of 1.5 mg KOH/g, with normal status.[^c1]
- Iron was 64 ppm against an alert limit of 50 ppm and was reported with ALERT status.[^c1]
- The PQ index was 112 against an alert limit of 60 and was reported with ALERT status.[^c1]
- Particle count was 20/18/15 code against an alert limit of 19/17/14 and was reported with ALERT status.[^c1]
- The report states that ferrous wear increased sharply since the previous sample, TR-OA-2026-0241 of 2026-03-17, when Fe was 31 ppm and PQ index was 44.[^c1]
- The report interprets large ferrous particles with normal copper as indicating rolling-element bearing distress rather than gear wear.[^c1]
- The report states that viscosity and water content are normal for PWG 220.[^c1]
- The recommendations are to review vibration trends for output stage bearings, inspect the HSS bearings by endoscope, replace the filter element, and resample within 30 days.[^c1]
- The trend table shows the 2026-06-10 sample as PWG 220 oil with Fe 64 ppm, PQ index 112, viscosity at 40 °C of 229, and ALERT status.[^c2]
- The results relate only to the sample received, and the report was approved by Imogen Thackwray of [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md).[^c2]

## Contents

### Report identification

[Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md) issued oil analysis report TR-OA-2026-0614.[^c3]

The report covers [gearbox](../entities/component/gearbox.md) oil for [WTG-07](../entities/asset/wtg-07.md) at [Quellmoor Ridge](../entities/asset/quellmoor-ridge-wind-farm.md).[^c3]

The customer is [Contoso Renewables](../entities/organisation/contoso-renewables.md), Quellmoor Ridge Wind Farm.[^c3]

The asset is the WTG-07 main gearbox, [Fabrikam FGT-3200](../entities/product/fgt-3200.md), serial FGT-3200-18-07752.[^c3]

**Table t01** · p. 1

| Row | Field | Value |
| --- | --- | --- |
| 2 | Customer | Contoso Renewables, Quellmoor Ridge Wind Farm |
| 3 | Asset | WTG-07 main gearbox, Fabrikam FGT-3200, serial FGT-3200-18-07752 |
| 4 | Lubricant | [Proseware PWG 220](../entities/product/pwg-220.md) (ISO VG 220), in service since 2025-10-15 |
| 5 | Sample ID | TR-26-11873 |
| 6 | Sampled | 2026-06-10 by Callum Rydings (sampling valve, oil at operating temperature) |
| 7 | Received / reported | 2026-06-12 / 2026-06-17 |
| 8 | Analyst | Imogen Thackwray, Senior Lubrication Analyst |

Agents can query this table as `t01` with the `query_table` tool.

### Sample and lubricant details

The lubricant is [Proseware PWG 220](../entities/product/pwg-220.md), ISO VG 220, in service since 2025-10-15.[^c3]

The sample ID is TR-26-11873.[^c3]

The sample was taken on 2026-06-10 by Callum Rydings from the sampling valve with oil at operating temperature.[^c3]

The sample was received on 2026-06-12 and reported on 2026-06-17.[^c3]

The analyst was Imogen Thackwray, Senior Lubrication Analyst.[^c3]

See table t01 above.

### Overall condition and laboratory results

The overall condition is ALERT, with action required.[^c3]

The laboratory results table reports viscosity, water, total acid number, elemental metals, PQ index, and particle count.[^c3]

Viscosity at 40 °C, viscosity at 100 °C, water, total acid number, copper, chromium, and silicon were reported as normal.[^c3]

Iron, PQ index, and particle count were reported with ALERT status.[^c3]

**Table t02** · p. 1

| Row | Test | Method | Result | Unit | Alert limit | Status |
| --- | --- | --- | --- | --- | --- | --- |
| 2 | Viscosity at 40 °C | kinematic | 229 | mm2/s | 198 to 242 | normal |
| 3 | Viscosity at 100 °C | kinematic | 26.1 | mm2/s | - | normal |
| 4 | Water | coulometric titration | 180 | ppm | 300 | normal |
| 5 | Total acid number | titration | 0.9 | mg KOH/g | 1.5 | normal |
| 6 | Iron (Fe) | ICP | 64 | ppm | 50 | ALERT |
| 7 | Copper (Cu) | ICP | 7 | ppm | 25 | normal |
| 8 | Chromium (Cr) | ICP | 2 | ppm | 10 | normal |
| 9 | Silicon (Si) | ICP | 9 | ppm | 15 | normal |
| 10 | PQ index | ferrous debris | 112 | - | 60 | ALERT |
| 11 | Particle count | ISO 4406 | 20/18/15 | code | 19/17/14 | ALERT |

Agents can query this table as `t02` with the `query_table` tool.

### Comments and interpretation

Ferrous wear has increased sharply since the previous sample, which the report identifies as TR-OA-2026-0241 of 2026-03-17 with Fe 31 ppm and PQ index 44.[^c3]

The report states that large ferrous particles with normal copper indicate rolling-element bearing distress rather than gear wear.[^c3]

Viscosity and water content are normal for [PWG 220](../entities/product/pwg-220.md).[^c3]

### Recommendations

The report recommends reviewing the vibration trend of the output stage bearings.[^c3]

It recommends inspecting the HSS bearings by endoscope.[^c3]

It recommends replacing the filter element and resampling within 30 days.[^c3]

### Trend and approval

The trend section contains Figure 1, described as iron and PQ index of the [WTG-07](../entities/asset/wtg-07.md) [gearbox](../entities/component/gearbox.md) oil.[^c4]

The trend table lists samples from 2025-06-11, 2025-12-09, 2026-03-17, and 2026-06-10.[^c4]

The latest trend-table entry is report TR-OA-2026-0614 for 2026-06-10, with [PWG 220](../entities/product/pwg-220.md) oil and ALERT status.[^c4]

The report states that results relate only to the sample received and that the report was approved by Imogen Thackwray, Senior Lubrication Analyst, [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md).[^c4]

**Table t03** · p. 2

| Row | Sample date | Report | Oil | Fe (ppm) | PQ index | Viscosity 40 °C | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2 | 2025-06-11 | TR-OA-2025-0388 | [PWG 320](../entities/product/pwg-320.md) | 22 | 19 | 318 | NORMAL |
| 3 | 2025-12-09 | TR-OA-2025-0951 | PWG 220 | 18 | 21 | 221 | NORMAL |
| 4 | 2026-03-17 | TR-OA-2026-0241 | PWG 220 | 31 | 44 | 224 | NORMAL |
| 5 | 2026-06-10 | TR-OA-2026-0614 | PWG 220 | 64 | 112 | 229 | ALERT |

Agents can query this table as `t03` with the `query_table` tool.

## Figures

- **Figure f01** (p. 2): Figure 1 - Iron and PQ index of the [WTG-07](../entities/asset/wtg-07.md) [gearbox](../entities/component/gearbox.md) oil. Generated description: A two-line time series chart compares Fe (ppm) in blue circles and PQ index in orange squares across four dates: 2025-06-11, 2025-12-09, 2026-03-17, and 2026-06-10. Fe is about 22, 18, 31, and 64 ppm, while PQ index is about 19, 21, 44, and 112. Two dashed horizontal reference lines are labeled Fe alert 50 and PQ alert 60.[^c5]

## Related

- Assets: [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md), [WTG-07](../entities/asset/wtg-07.md)
- Components: [gearbox](../entities/component/gearbox.md), [HSS bearing](../entities/component/hss-bearing.md), [oil filter element](../entities/component/oil-filter.md)
- Products: [Fabrikam FGT-3200](../entities/product/fgt-3200.md), [Proseware PWG 220](../entities/product/pwg-220.md), [Proseware PWG 320](../entities/product/pwg-320.md)
- Organisations: [Contoso Renewables](../entities/organisation/contoso-renewables.md), [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md), [Proseware Lubricants](../entities/organisation/proseware-lubricants.md), [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)
- Topics: [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md), [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)

<!-- docwiki:backlinks:start -->
## Referenced by

- [Contoso Renewables](../entities/organisation/contoso-renewables.md)
- [Fabrikam FGT-3200](../entities/product/fgt-3200.md)
- [Fabrikam Getriebetechnik GmbH](../entities/organisation/fabrikam-getriebetechnik.md)
- [gearbox](../entities/component/gearbox.md)
- [Gearbox lubrication and oil changes](../topics/gearbox-lubrication.md)
- [Gearbox temperature, vibration and oil analysis](../topics/gearbox-condition-monitoring.md)
- [HSS bearing](../entities/component/hss-bearing.md)
- [oil filter element](../entities/component/oil-filter.md)
- [Proseware Lubricants](../entities/organisation/proseware-lubricants.md)
- [Proseware PWG 220](../entities/product/pwg-220.md)
- [Proseware PWG 320](../entities/product/pwg-320.md)
- [Quellmoor Ridge Wind Farm](../entities/asset/quellmoor-ridge-wind-farm.md)
- [Trey Research Laboratories](../entities/organisation/trey-research-laboratories.md)
- [WTG-07](../entities/asset/wtg-07.md)

<!-- docwiki:backlinks:end -->

## Sources

[^c1]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 1](../evidence/src-990a047180b7/p0001.md) · ✓ quote verified
[^c2]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 2](../evidence/src-990a047180b7/p0002.md) · ✓ quote verified
[^c3]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 1](../evidence/src-990a047180b7/p0001.md) · paraphrase
[^c4]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 2](../evidence/src-990a047180b7/p0002.md) · paraphrase
[^c5]: [Oil analysis report TR-OA-2026-0614 - WTG-07 gearbox oil — p. 2](../evidence/src-990a047180b7/p0002.md) · generated description
