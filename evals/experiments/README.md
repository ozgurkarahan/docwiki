# Retrieval experiments

Decision records of the words and meaning search plan (spec CHANGELOG v1.10). Each gate's
criteria are committed here **before** the run they judge; results are published even when a gate
fails.

## Blind decision set

`retrieval-blind.sha256` is the SHA-256 of `retrieval-blind.jsonl`, the blind decision set of the
retrieval probes (`evals/golden/README.md`, "Retrieval probe sets"), committed before any retrieval
change is built.

- Written on 2026-11-01 by an independent agent session from the public fictional documents only
  (`probes.py --list` and `--dump`, `samples/fiction/bible.yaml`, the domain glossary and the golden
  README), with no access to the retrieval code, the dev or tune sets, results or experiments.
- 30 probes, verified with `probes.py --check` (30 passed): 8 `paraphrase-fr`, 8 `en-to-fr`,
  8 `lexical-control`, 6 `multi-chantier`; 17 in French, 13 in English; 24 with a `within`.
- The builder has seen only those aggregates and the fingerprint, never a question. The file stays
  outside the repository during development and is published here after the last gate; check it
  with `sha256sum -c retrieval-blind.sha256` (or `Get-FileHash`).
- Blind by process, not cryptographically. Optional confirmation: the owner may run the private
  holdout on the final configuration (aggregates only).
