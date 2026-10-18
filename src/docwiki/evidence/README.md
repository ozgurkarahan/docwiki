# `docwiki.evidence`

`build_evidence(...)` renders the evidence sidecars of one source (evidence-contract §5): one
`evidence/<source_id>/<locator_key>.md` per cited locator key with highlighted page images,
verbatim text, table rows under `## Row N` headings, OCR crops with confidence and clearly
labelled generated figure descriptions, plus `evidence/<source_id>/index.md` and, for public
sample builds, `original.<ext>` (a Markdown original is published as `original.txt`: every `.md`
file under `evidence/` is read as a page). Citations are resolved as the compile lane emits
them (block ids, `t03:r0012` / `f02` refs, narrowed row ranges, figure locators). A citation of
several blocks (a quote running across paragraphs, carried by its first block's locator) shows
every cited block, each labelled with its locator, and the other blocks' locator keys get
sidecars too.
All document text is guarded (`TextGuard`: canaries redacted, sentences addressed to AI systems
replaced by a visible placeholder), escaped (`escape_text`, `plain_text`) and passed through
`contracts.sanitize_markdown`.

See [`../extract/README.md`](../extract/README.md#evidence-sidecars-docwikievidence) for the
layout, provenance rules and sanitisation details.
