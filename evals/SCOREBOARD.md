<!-- scoreboard:start -->
## Evaluation

Each cell gives the score and its denominator: 0/1 metrics show passed / applicable questions, share metrics (coverage, citation precision and recall) the mean over the n applicable questions. Definitions, systems and honesty rules: `evals/README.md`.

### Dev split (`evals/golden/dev.jsonl`, 32 questions)

| System | Answer accuracy | Must-include coverage | Numeric exactness | Citation precision | Citation recall | Abstention accuracy | Injection resistance | Restricted exclusion | Judge answer score | Tokens / question | Cost (USD) | Latency p50 / p95 | Run |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `docwiki-researcher` | 75.0 % (24/32) | 92.0 % (n=30) | 100.0 % (9/9) | 65.9 % (n=31) | 60.4 % (n=30) | 96.9 % (31/32) | 100.0 % (1/1) | 100.0 % (32/32) | – | 26.0k | $0.1636/q ($5.23)* | 32.3 s / 71.1 s | 2026-10-23 · `e8afd0e` |
| `baseline-rag` | 56.2 % (18/32) | 78.8 % (n=30) | 66.7 % (6/9) | 90.4 % (n=27) | 67.4 % (n=30) | 90.6 % (29/32) | 100.0 % (1/1) | 100.0 % (32/32) | – | 6.9k | $0.0445/q ($1.42)* | 8.2 s / 19.1 s | 2026-10-23 · `e8afd0e` |
| `baseline-long-context` | 62.5 % (20/32) | 89.3 % (n=30) | 88.9 % (8/9) | 74.3 % (n=30) | 73.9 % (n=30) | 93.8 % (30/32) | 100.0 % (1/1) | 100.0 % (32/32) | – | 36.0k | $0.0527/q ($1.69)* | 14.6 s / 49.0 s | 2026-10-23 · `e8afd0e` |

Failed question ids per metric and category:

- `docwiki-researcher` — answer accuracy: abstain q011; contradiction q007; multi-hop q018, q021, q022, q029; skill q016; supersession q032 · must-include coverage: contradiction q007; multi-hop q018, q021, q022, q029; skill q016; supersession q032 · citation precision: abstain q011; contradiction q007; multi-hop q005, q006, q018, q030; multilingual q009; numeric q002, q025, q026; skill q015, q016; supersession q031, q032; table q004, q023, q024 · citation recall: contradiction q007; injection q012; multi-hop q005, q006, q018, q021, q022, q027, q028, q029, q030; numeric q025, q026; skill q015, q016; supersession q031, q032; table q004, q019, q020 · abstention accuracy: abstain q011
- `baseline-rag` — answer accuracy: multi-hop q017, q018, q021, q022, q029, q030; ocr q010; skill q014, q015, q016; supersession q031; table q004, q023, q024 · must-include coverage: multi-hop q017, q018, q021, q022, q029, q030; ocr q010; skill q014, q015, q016; supersession q031; table q004, q023, q024 · numeric exactness: table q004, q023, q024 · citation precision: multi-hop q005; numeric q002, q026; skill q014, q015, q016 · citation recall: contradiction q007; multi-hop q005, q006, q017, q018, q021, q022, q027, q028, q029, q030; numeric q025; ocr q010; skill q014, q015, q016; table q004 · abstention accuracy: multi-hop q029; ocr q010; table q004
- `baseline-long-context` — answer accuracy: multi-hop q017, q018, q021, q022; ocr q010; restricted q013; skill q014, q015, q016; supersession q031, q032; table q024 · must-include coverage: multi-hop q017, q018, q021, q022; ocr q010; skill q014, q015, q016; supersession q031, q032; table q024 · numeric exactness: table q024 · citation precision: injection q012; multi-hop q005, q006, q017, q018, q021, q022, q030; numeric q025, q026; restricted q013; single-hop q001; skill q014, q015, q016; supersession q031; table q019, q020 · citation recall: contradiction q007; multi-hop q005, q017, q018, q021, q022, q027, q028, q029, q030; ocr q010; skill q014, q015, q016; supersession q031, q032 · abstention accuracy: ocr q010; restricted q013

\* Estimated with unverified prices (the packaged `prices.yaml` holds placeholders; see `src/docwiki/llm/README.md`).

Dev and holdout scores are reported separately and prompts are never tuned on holdout results. The baselines measure trade-offs; DocWiki is not presented as a replacement for retrieval systems.
<!-- scoreboard:end -->
