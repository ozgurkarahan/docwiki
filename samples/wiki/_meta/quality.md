---
id: meta:quality
type: meta
title: Quality report
summary: Gate results of this release.
lang: en
sensitivity: public
updated: 2026-10-18
tags: []
docwiki:
  schema: 1
  release: 20261018T104207Z-650d6d98
---

# Quality report

Release `20261018T104207Z-650d6d98`, audience public, built by run [run-20261018-104157-1fa32b76](runs/run-20261018-104157-1fa32b76.md).

Blocking gates passed. A failing blocking gate stops publication and keeps the previous release current.

| Gate | Name | Blocking | Status | Metric | Threshold | Violations |
| --- | --- | --- | --- | --- | --- | --- |
| G01 | frontmatter | yes | pass |  |  | 0 |
| G02 | links | yes | pass |  |  | 0 |
| G03 | citations-present | yes | pass |  |  | 0 |
| G04 | quote-verification | yes | pass | 0.9976 | 0.95 | 0 |
| G05 | safe-content | yes | pass |  |  | 0 |
| G06 | sidecars | yes | pass |  |  | 0 |
| G07 | audience | yes | pass |  |  | 0 |
| G08 | injection-containment | yes | pass |  |  | 0 |
| G09 | paths | yes | pass |  |  | 0 |
| G10 | glossary | yes | pass |  |  | 0 |
| G11 | supersession | yes | pass |  |  | 0 |
| G12 | tags | yes | pass |  |  | 0 |
| G13 | orphans | no | pass |  |  | 0 |
| G14 | skills | yes | pass |  |  | 0 |
| G15 | extraction | no | pass | 0.0 | 0.1 | 0 |

## Citations

G04 applies to quoted native-text and table citations; citations without a quote are paraphrases and are counted separately.

- Quoted native-text/table citations verified: 836 of 838 (99.8%)
- Quoted native-text/table citations that failed: 2
- Paraphrases (no quote, not verified): 1292
- Citations without a quote that failed: 5
- Quoted citations of OCR or figure text: 66

## Site

Built from this release after the gates above were evaluated; its link check, security scan and canary scan must pass before publication.

## Injection flags

These blocks contain text addressed to AI systems. It was kept out of the compiled pages, the search index and the published originals.

- source `src-0df0d0598e76`, block `b0010`: Contains text addressed to AI assistants and automated document processors, attempting to override instructions and cause an automated approval and repeated reference insertion; detected: ignore-inst…
