# `docwiki.extract` and `docwiki.evidence`

Extraction turns one raw file into the **ExtractedDoc** evidence contract
(`docs/spec/evidence-contract.md` §1–§2, §6; `src/docwiki/contracts/CONTRACT.md` §5). The evidence
stage renders what citations point to: one **sidecar** per cited locator
(evidence-contract §5, CONTRACT.md §5 and §10–§11). Both follow the cross-lane signatures of
`docs/spec/engine-interfaces.md`.

```python
from docwiki.engine_types import CitedLocator, ExtractSettings
from docwiki.evidence import build_evidence
from docwiki.extract import extract_source

result = await extract_source(
    raw_file, rel_path="docs/sop-gbx-010.pdf", settings=ExtractSettings(), llm=llm_or_none
)
result.doc  # ExtractedDoc (blocks b0001…, tables t01…, figures f01…)
result.figures  # {"f01": png bytes}
result.page_images  # {1: png bytes} — PDF pages rendered at settings.page_render_dpi; images
result.warnings  # == result.doc.extraction.warnings, "<code>: <message>"

paths = build_evidence(
    doc=result.doc,
    raw_file=raw_file,
    cited=cited_locators,
    source_title="Gearbox oil change SOP rev A",
    source_page_path="sources/sop-gbx-010-rev-a.md",
    sensitivity="public",
    publish_original=True,
    writer=release_writer,
    page_images=result.page_images,
)
```

`extract_source` raises `ExtractionError(source_id, reason)` when a source cannot be extracted
(unsupported type, unreadable/damaged/encrypted file, Content Understanding failure — the
subclass `ContentUnderstandingError` adds `status_code`, `retryable` and `auth`; its `systemic`
property is true for throttling, outages, network errors and timeouts (`retryable`) and for HTTP
401/403 or a missing Entra ID token (`auth`): the orchestrator then fails the run so that it is
retried instead of quarantining the source). Recoverable issues are warnings. Invalid settings
raise `ValueError`. `extractor_versions()` returns the adapter and
parser versions for run reports and cache keys; `uses_content_understanding(rel_path, settings)`
tells whether a file goes to the service.

## Adapters

| Format | Library | Blocks (kind) | Locator | Provenance |
|---|---|---|---|---|
| PDF | pypdfium2 | heading / paragraph / list per paragraph, `ocr-line` placeholder for pages without text | `pdf-page` + bbox | native-text, ocr |
| DOCX | python-docx | heading (style `Heading N`, `Title`, outline level), paragraph, list; `table-ref` per table row | `docx-paragraph`, `docx-table` | native-text, deterministic-table |
| XLSX/XLSM | openpyxl (`data_only`) | `heading` per sheet (row 1), `table-ref` per data row | `xlsx-rows` | deterministic-table |
| CSV/TSV | `csv` | `table-ref` per data row | `csv-rows` | deterministic-table |
| PPTX | python-pptx | `heading` (title), `slide` (text shapes, tables as rows), `note` (speaker notes) | `pptx-slide` (+ shape) | native-text |
| EML | `email` | `email-header`, `email-body` per paragraph, one block per attachment | `eml-part` | native-text |
| VTT | built-in parser | `cue` | `vtt-cue` | native-text |
| MD/TXT | built-in | heading (Markdown ATX), paragraph, list | `text-lines` | native-text |
| PNG/JPEG/TIFF/BMP/GIF/WEBP | Pillow | `ocr-line` placeholder + whole-image figure | `image-region` | ocr |

**Content Understanding** (`settings.mode == "azure"`) replaces the PDF and image adapters only.
Every other format always uses the local adapter (stable, deterministic locators), and XLSX/CSV
are always parsed deterministically.

### Locator conventions (the golden set relies on them)

- **PDF**: 1-based page index; bbox normalised `[x0, y0, x1, y1]`, origin top-left of the
  displayed (rotated, cropped) page. Paragraphs come from PDFium's line order, split on vertical
  gaps, font-size changes and bullets; headings are lines ≥ 1.2 × the page's body size.
- **DOCX**: `para-NNNN` = 1-based index into python-docx `Document.paragraphs` (body paragraphs,
  **empty ones included**; table cells, headers and footers excluded). `tbl-TT-rAAAA-rBBBB`:
  `TT` is 1-based into `Document.tables`; rows are 1-based with the header as row 1. Merged
  cells are expanded. Inline pictures are figures located at their paragraph.
- **XLSX**: Excel row numbers, header in row 1; empty rows are skipped but keep their number.
  The sheet slug is `slugify_ascii(sheet name)`; `sheet_slug` is set in the locator only when a
  collision forces `assign_unique_slugs` (`plan`, `plan-2`). Cell text: cached values (never
  formulas; a formula without cached value is empty + warning), ISO dates, percentages as
  displayed, numbers with 15 significant digits. Merged ranges are expanded.
- **CSV**: records counted from 1 (header = row 1), blank records included, so numbers match a
  spreadsheet view (a quoted field spanning lines stays one row). UTF-8 with or without BOM,
  UTF-16 with BOM, cp1252 fallback (warning); dialect sniffed among `, ; TAB |`.
- **PPTX**: 1-based slide; `shape` holds the shape name (`notes` for speaker notes). Table rows
  are native text (a slide is one sidecar, which has one provenance).
- **EML**: `headers` part for From/To/Cc/Date/Subject; body lines are the 1-based lines of the
  decoded `text/plain` body (or of the text converted from HTML when there is no plain part,
  with a warning); attachments are listed as `attachment:<name>` parts.
- **VTT**: cue start/end `HH:MM:SS`, milliseconds truncated; `<v Speaker>` becomes `Speaker: `.
- **MD/TXT**: 1-based physical lines; a paragraph is a run of consecutive non-empty lines.
- **Images**: `page` 1; regions are numbered in OCR reading order (`img-bNN`). Local mode has a
  single region 1 (the whole image) shared by the OCR placeholder and the figure; with Content
  Understanding the OCR paragraphs are regions 1…N and the whole-image figure is region N+1.

Block ids are `b0001…` in reading order, table ids `t01…`, figure ids `f01…`, all stable for an
unchanged input, adapter version and configuration. Table rows have `row_id = r<row number>`
(data rows only; the header is `columns`); one `table-ref` block per data row carries
`"Column: value; …"` so that quotes and numbers can be verified.

### Figures and descriptions

PDF figures are embedded images between 0.4 % and 85 % of the page area (smaller ones are
icons, larger ones are scans or backgrounds; an image repeated on 3+ pages is decoration),
cropped from the page render. DOCX/PPTX pictures and whole images are figures too.

When `settings.describe_figures` and an `llm` are given, each figure (up to 64 per source) is
described by one `llm.structured(tier="fast", schema_name="figure_description",
prompt_version="figure-description-v1")` call with the figure image (≤ 1024 px) and the fixed
text "Describe this figure." — no document text. The system prompt declares the image untrusted
and forbids following instructions found in it. A described figure gets `description`,
`description_provenance: model-description` and a `figure-ref` block (provenance
`model-description`) at its reading-order position; `extraction.model` names the model.
Failures are warnings (`figure-description-failed`).

### Bounds

`settings.max_pages` (PDF pages, PPTX slides; Content Understanding gets `range=1-N`),
100,000 rows and 500 columns per table, 64 described figures, images and renders ≤ 4096 px.
Every truncation is a warning.

### Warning codes

`needs-ocr`, `max-pages`, `pdf-text-unmappable`, `pdf-metadata`, `figure-skipped`,
`table-truncated`, `xlsx-formula-no-value`, `encoding`, `csv-parse`, `empty`, `eml-body`,
`eml-html-body`, `vtt-header`, `vtt-cue`, `image-frames`, `figure-descriptions`,
`figure-description-failed`, `cu-warning`, `cu-contents`, `cu-no-layout`, `cu-malformed`.

## Azure Content Understanding adapter

GA REST API **`2025-11-01`** (verified on Microsoft Learn: *Content Analyzers – Analyze Binary*
and *Get Result*), Microsoft Entra ID only (`DefaultAzureCredential`, scope
`https://cognitiveservices.azure.com/.default`; the identity needs **Cognitive Services User**
on the resource). Analyzer: `settings.cu_analyzer` (default `prebuilt-layout`, which needs no
model deployment).

1. `POST {endpoint}/contentunderstanding/analyzers/{analyzer}:analyzeBinary?api-version=2025-11-01&stringEncoding=codePoint[&range=1-N]`
   with the file bytes (`Content-Type: application/octet-stream`) → `202` + `Operation-Location`.
2. `GET` the operation location (must be on the endpoint's host, otherwise refused) until
   `status` is `Succeeded` (`Failed`/`Canceled` raise). `Retry-After` is honoured; 408/429/5xx
   and network errors are retried with backoff; 401/403 are not retried.
3. `result.contents[0]`: `paragraphs` (role `title`/`sectionHeading` → headings, `footnote` →
   note), `tables` (cells expanded over spans; header = row 1; their paragraphs are not repeated),
   `figures` (crop of the local page render + caption; CU's own descriptions are not used),
   ordered by markdown span offset. `source` polygons `D(page,x1,y1,…)` or
   `D(page,left,top,width,height)` in the content `unit` (inch for PDF, pixel for images) are
   normalised by the page size. Without layout details, blocks fall back to the per-page
   markdown (warning `cu-no-layout`).

Provenance is `native-text` for PDF pages that have a text layer (checked locally with
pypdfium2) and `ocr` otherwise (images, scans), with the mean word confidence on OCR blocks.
Page renders, metadata and figure crops are always produced locally.

### Record and replay

| `cu_mode` | Behaviour |
|---|---|
| `live` | call the service (needs `cu_endpoint`) |
| `record` | call the service and write `<recordings_dir>/<request hash>.json` |
| `replay` | read the recording only — offline, used in CI; a missing recording is an `ExtractionError` |

The request hash is the SHA-256 of the canonical JSON of `{api_version, analyzer,
content_sha256, content_type, range, string_encoding}` (no endpoint, so recordings are portable).
A recording is `{"schema": 1, "request": {…}, "response": {…}}` with sorted keys; the operation
id is removed and neither the endpoint nor the file bytes are stored. Replay checks that the
recorded request matches. Record only public sample documents, then commit the JSON files:

```python
settings = ExtractSettings(
    mode="azure",
    cu_endpoint="https://<resource>.cognitiveservices.azure.com",
    cu_mode="record",
    recordings_dir=Path("tests/fixtures/extract/cu"),
)
```

## Evidence sidecars (`docwiki.evidence`)

`build_evidence(..., canaries=())` writes, through the `ReleaseWriter`, for one source:

- `evidence/<sid>/<locator_key>.md` for every distinct key of `cited` (several citations of one
  page share the page sidecar); frontmatter `EvidenceFrontmatter` with the canonical locator of
  the key (no bbox for pages, no shape for slides) and **one** provenance for the cited content
  (precedence `native-text` > `deterministic-table` > `ocr` > `model-description`, so a page
  that also cites a figure keeps `native-text` and its figure citations keep the honest
  `generated description` badge; row ranges always take their table's provenance);
- a heading `<source title> — <locator label>`, a link back to the source page, a link to
  `original.<ext>` (`#page=N` for PDFs) when `publish_original`, and the provenance badge
  (`badge_for`);
- the content: page image with highlight boxes for every cited bbox (`img/<key>.png`, 150 dpi;
  rendered from `raw_file` when `page_images` lacks the page), verbatim native text as quotes,
  OCR text with its crop (`img/<key>-<block>.png`) and confidence, table rows under
  `## Row N` headings (XLSX, CSV, DOCX tables: exactly the rows of the locator's range, so a
  single-row citation shows one row; at most 500 rows), cited PDF/PPTX tables under
  `## Table tNN`, and figures (`img/<key>-<figure>.png`) with the generated description clearly
  labelled;
- `evidence/<sid>/index.md` (`EvidenceIndexFrontmatter`) listing the locators with badges, and
  `evidence/<sid>/original.<ext>` when `publish_original`.

Citations are resolved one by one, as the compile lane emits them: `block_ids` may hold block
ids (`b0042`), table refs (`t03`, `t03:r0012`) and figure refs (`f02`); when they are empty
(table rows and figures), the locator decides — a row range narrowed to the cited rows renders
those rows, a figure locator (page + figure bbox) renders the figure, a PDF/PPTX table locator
renders the table, otherwise the blocks of the key with the citation's provenance are quoted.
Non-contiguous citations of one table are separate keys or one narrowed range; each sidecar
renders its own range.

Document text is untrusted: every document-derived string (block text, table cells, captions,
generated descriptions, titles) first goes through `TextGuard` — canaries are replaced by
`[redacted]` (case-insensitive; an original containing a canary is not published) and every
sentence flagged by `contracts.detect_injection` (checked per sentence and across wrapped lines)
is replaced by `[instruction addressed to AI assistants removed — see quality report]` — and is
then escaped (`escape_text`: Markdown punctuation escaped, `<`/`>` as entities, URLs and e-mail
addresses as code spans, line-start lists/headings/quotes neutralised; `plain_text` for
frontmatter); each body finally passes through `contracts.sanitize_markdown`. Names used in
locators (sheets, attachments, shapes) that are addressed to AI systems are replaced at
extraction (`sheet 2`, `attachment 1`…; the sheet slug still follows the real name). The
ExtractedDoc keeps the original text, so quote verification is unaffected. Tests assert
`find_violations == []`, no injection left, no canary, and a clean `validate_release` for the
evidence of every fixture format.

## Tests

`uv run pytest tests/extract tests/evidence` generates every fixture at test time (fpdf2 text
and image-only PDFs, DOCX, XLSX, CSV, PPTX, EML, VTT, MD/TXT, PNG) and covers locators, labels,
provenance, determinism, the Content Understanding REST flow with a mock transport, record and
replay, local/CU parity, figure descriptions with `FakeLlmClient`, sidecars for every locator
kind, highlight boxes and sanitisation of hostile text. No test touches the network.
