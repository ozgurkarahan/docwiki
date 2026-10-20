# ADR 0004 — Evidence sidecars and provenance types

- Status: Accepted (spec v1)

## Context

A citation is only useful if a reader can check it quickly. Page numbers alone do not work for
spreadsheets, e-mails or transcripts, and private deployments cannot link to protected storage.
Text recognised from pixels and model-written figure descriptions are not quotes.

## Decision

- Every cited locator gets an **evidence sidecar** page (rendered PDF page with highlight boxes,
  spreadsheet rows with row anchors, slide, e-mail lines, transcript cue, OCR crop) published with
  the release, linking back to the source page and, for the public sample, to the original file.
- Every citation records a **provenance type**: `native-text`, `deterministic-table`, `ocr` or
  `model-description`. Only the first two can earn "✓ quote verified", checked deterministically.
- Spreadsheet and CSV values are always parsed by code, never retyped by a model.

## Consequences

- One click from any claim to the evidence, on the public demo and in private deployments.
- Honest badges; OCR and generated descriptions are visibly weaker evidence.
- Builds produce more files; the link checker validates every citation.
