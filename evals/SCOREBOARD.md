<!-- scoreboard:start -->
## Evaluation

Each cell gives the score and its denominator: 0/1 metrics show passed / applicable questions, share metrics (coverage, citation precision and recall) the mean over the n applicable questions. Definitions, systems and honesty rules: `evals/README.md`.

### Dev split (`evals/golden/dev.jsonl`, 33 questions)

| System | Answer accuracy | Must-include coverage | Numeric exactness | Citation precision | Citation recall | Abstention accuracy | Injection resistance | Restricted exclusion | Judge answer score | Tokens / question | Cost (USD) | Latency p50 / p95 | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `docwiki-researcher` | 90.6 % (29/32) | 94.2 % (n=29) | 80.0 % (4/5) | 79.5 % (n=30) | 77.3 % (n=30) | 100.0 % (33/33) | 100.0 % (2/2) | 100.0 % (33/33) | – | 20.0k | $0.1184/q ($3.91)* | 22.6 s / 75.1 s | 2026-10-18 · `8e237f0` · release `20261018T092417Z-d2186573` |
| `baseline-rag` | 75.0 % (24/32) | 84.5 % (n=29) | 100.0 % (5/5) | 91.8 % (n=27) | 75.8 % (n=30) | 90.9 % (30/33) | 100.0 % (2/2) | 100.0 % (33/33) | – | 7.2k | $0.0462/q ($1.53)* | 7.0 s / 19.7 s | 2026-10-18 · `adf51bf` |
| `baseline-long-context` | 50.0 % (16/32) | 58.9 % (n=29) | 40.0 % (2/5) | 75.2 % (n=22) | 44.5 % (n=30) | 72.7 % (24/33) | 100.0 % (2/2) | 93.9 % (31/33) | – | 154.7k | $0.1454/q ($4.51)* | 120.6 s / 189.0 s | 2026-10-18 · `8bd838c` |

Failed question ids per metric and category:

- `docwiki-researcher` — answer accuracy: multi-hop q012; supersession q019; table q007 · must-include coverage: multi-hop q012; supersession q019; table q007 · numeric exactness: table q007 · citation precision: injection q028, q029; multi-hop q011, q012, q015; skill q031, q032, q033; supersession q019, q020; table q007, q010 · citation recall: contradiction q017, q018; injection q029; multi-hop q011, q012, q013; skill q031, q032, q033; supersession q019, q020; table q007, q010
- `baseline-rag` — answer accuracy: multi-hop q011, q012, q014; multilingual q021, q022; skill q031, q033; table q007 · must-include coverage: multi-hop q011, q012, q014; multilingual q021, q022; skill q031, q033; table q007 · citation precision: multi-hop q012, q015; skill q033; table q008, q010 · citation recall: contradiction q018; injection q029; multi-hop q011, q012, q013, q014; multilingual q021, q022; skill q031, q032, q033; supersession q020 · abstention accuracy: injection q029; multi-hop q014; multilingual q021
- `baseline-long-context` — answer accuracy: contradiction q018; multi-hop q011, q012, q014, q016; multilingual q022; numeric q006; single-hop q002, q004; skill q032, q033; supersession q019; table q007, q008, q009, q010 · must-include coverage: contradiction q018; multi-hop q011, q012, q014, q016; multilingual q022; numeric q006; single-hop q002, q004; skill q032, q033; supersession q019; table q007, q008, q009, q010 · numeric exactness: numeric q006; table q008, q009 · citation precision: contradiction q017; injection q028; multi-hop q011, q012, q014; multilingual q023; numeric q006; single-hop q003; skill q031, q033; supersession q019, q020 · citation recall: contradiction q017, q018; injection q028, q029; multi-hop q011, q012, q013, q014, q016; multilingual q022; numeric q005, q006; single-hop q002, q003, q004; skill q031, q032, q033; supersession q019, q020; table q008, q009, q010 · abstention accuracy: injection q029; multi-hop q016; multilingual q022; numeric q006; single-hop q002, q004; skill q032; table q008, q009 · restricted exclusion: skill q032; table q009 · errors: q009, q032

### Holdout split (private questions, aggregates only, 15 questions)

| System | Answer accuracy | Must-include coverage | Numeric exactness | Citation precision | Citation recall | Abstention accuracy | Injection resistance | Restricted exclusion | Judge answer score | Tokens / question | Cost (USD) | Latency p50 / p95 | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `docwiki-researcher` | 93.3 % (14/15) | 98.1 % (n=13) | 100.0 % (2/2) | 86.5 % (n=13) | 84.3 % (n=13) | 100.0 % (15/15) | 100.0 % (1/1) | 100.0 % (15/15) | – | 25.7k | $0.1649/q ($2.47)* | 44.7 s / 77.4 s | 2026-10-18 · `8e237f0` · release `20261018T092417Z-d2186573` |
| `baseline-rag` | 66.7 % (10/15) | 87.2 % (n=13) | 50.0 % (1/2) | 96.9 % (n=13) | 86.5 % (n=13) | 100.0 % (15/15) | 100.0 % (1/1) | 100.0 % (15/15) | – | 7.4k | $0.0510/q ($0.76)* | 6.3 s / 9.4 s | 2026-10-18 · `adf51bf` |
| `baseline-long-context` | 46.7 % (7/15) | 53.2 % (n=13) | 0.0 % (0/2) | 71.7 % (n=9) | 37.8 % (n=13) | 66.7 % (10/15) | 100.0 % (1/1) | 80.0 % (12/15) | – | 132.0k | $0.1692/q ($2.03)* | 117.5 s / 135.6 s | 2026-10-18 · `8e237f0` |

\* Estimated with unverified prices (the packaged `prices.yaml` holds placeholders; see `src/docwiki/llm/README.md`).

Dev and holdout scores are reported separately and prompts are never tuned on holdout results. The baselines measure trade-offs; DocWiki is not presented as a replacement for retrieval systems.
<!-- scoreboard:end -->
