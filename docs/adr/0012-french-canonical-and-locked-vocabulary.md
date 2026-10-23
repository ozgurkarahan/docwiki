# ADR 0012 — French canonical with an English mirror; a locked trade vocabulary

- Status: Accepted 2026-10-23 (the locked vocabulary ships first; the French compile and the
  English mirror follow in a later slice of the same plan)
- Amends: decision D10 ("wiki written in English") for packs that declare their languages;
  [0007](0007-answers-in-the-wiki.md)'s English-only filed answers
- Spec: v1.7

## Context

The sample is a French building contractor's documents. A building-trade expert reviewed the live
wiki (2026-10-22) and found two mistakes that would make a professional close the tab:

- the conductrice de travaux was rendered "site manager", which is the chef de chantier, another
  job;
- "réception des travaux" was rendered "handover". Réception is a legal act (article 1792-6 of
  the French civil code): it records the réserves and starts the one-year, two-year and ten-year
  guarantees. "Handover" does not say any of that.

Both came from the domain pack itself: its glossary defined "site manager" and "handover" as the
English terms, and its notes told the model to write them. Translating the vocabulary of a legal
and contractual trade loses meaning, and translating it back (French → English → French) loses it
again ("réception" came back as "remise des clés").

## Decision

1. **A locked trade vocabulary per domain pack.** An optional pack file `terms.yaml` lists the
   terms the wiki keeps in the documents' language, exactly as written, each with an English gloss
   given in brackets the first time it appears on a page, and the English renderings that are
   banned because they change its meaning. For the batiment pack: réception, retenue de garantie,
   avenant, situation, OS, PV, réserves, DOE, PPSPS, conducteur de travaux, chef de chantier,
   chef d'équipe, lot, DPGF, CCAP.
   - The compile, entity and topic prompts receive the list; the glossary uses the locked terms
     as its entries.
   - **A blocking verify gate (G16)** fails a release in which a wiki page renders a locked term
     with a banned equivalent ("site manager", "handover").
2. **Amounts are written the trade's way by code**, never by the model: `2 390,00 € HT`. The
   model copies amounts as printed (so citations can be checked); a deterministic pass groups the
   thousands and writes HT or TTC.
3. **French canonical, English mirror** (later slice): a pack declares `wiki_languages`, the first
   one canonical. The batiment pack compiles in French; a `translate` stage after `verify` writes
   the English mirror under `/en/` with the same slugs, translating prose only (markers, numbers,
   dates, document numbers and locked terms are preserved and checked), cached per page and
   language. Filed and live answers are in the question's language.

## Consequences

- The wiki speaks the trade's language: a conducteur de travaux reads "réception" and
  "retenue de garantie", with the English gloss once for other readers.
- Changing the pack recompiles every page once (the pack hash is part of every stage's key).
- A model that slips back to a banned word blocks the release instead of publishing it; the
  previous release stays served.
- The engine stays generic: the vocabulary, its glosses and its bans live in the pack.
