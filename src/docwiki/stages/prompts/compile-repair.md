---
name: compile-repair
version: compile-repair-v1
---
# Repairing facts that failed verification
In this step you do not compile the whole document again. The task section lists numbered facts
from your earlier answer that deterministic verification rejected, each with its citations and
the reasons. The document data contains the parts of the document needed to fix them.
- For each listed fact that the document supports, return it with fact_number set to its number,
  its English text, corrected citations (existing ids and exact quotes copied character for
  character from the cited block or table row) and its numbers written exactly as in the cited
  text.
- If the document does not support a fact, or only part of it, leave the fact out or narrow its
  text to what the document states. Never add new facts.
- Return {"facts": []} when nothing can be repaired.
