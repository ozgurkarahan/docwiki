# Engine interfaces (spec v1 addendum)

The engine is built by three parallel lanes. These signatures are the only cross-lane calls.
Shared types live in `src/docwiki/engine_types.py` (main-owned, frozen). Contracts are in
`src/docwiki/contracts/CONTRACT.md`.

## Extract lane — `docwiki.extract`, `docwiki.evidence`

```python
# docwiki.extract
async def extract_source(raw_file: Path, *, rel_path: str, settings: ExtractSettings,
                         llm: LlmClient | None = None) -> ExtractResult
# raises ExtractionError(source_id, reason) for unrecoverable failures

# docwiki.evidence
def build_evidence(*, doc: ExtractedDoc, raw_file: Path, cited: Sequence[CitedLocator],
                   source_title: str, source_page_path: str, sensitivity: Sensitivity,
                   publish_original: bool, writer: ReleaseWriter,
                   page_images: Mapping[int, bytes] | None = None) -> list[str]
# writes evidence/<sid>/index.md, one sidecar per distinct locator key, img/ assets with
# highlight boxes, original.<ext> when publish_original; returns written content paths
```

`llm` is used only for figure descriptions (tier `fast`, provenance `model-description`).
XLSX and CSV are always parsed locally and deterministically, in both modes.

## Compile lane — `docwiki.stages.classify|compile|render|entities|topics`

```python
async def classify_source(doc: ExtractedDoc, pack: DomainPack, llm: LlmClient) -> Classification

async def compile_source(doc: ExtractedDoc, classification: Classification, pack: DomainPack,
                         llm: LlmClient, *, hints: str | None = None) -> CompiledResult

def render_source_page(result: CompiledResult, doc: ExtractedDoc, classification: Classification,
                       state: SourceState, *, slug: str, stamp: DocwikiStamp, pack: DomainPack,
                       supersedes: Sequence[str] = (), superseded_by: Sequence[str] = ()
                       ) -> tuple[Page, list[CitedLocator]]

async def build_entity_pages(results: Sequence[CompiledResult], source_pages: Mapping[str, Page],
                             pack: DomainPack, llm: LlmClient, *, stamp: DocwikiStamp
                             ) -> tuple[list[Page], list[CitedLocator]]

async def build_topic_pages(results: Sequence[CompiledResult], source_pages: Mapping[str, Page],
                            states: Mapping[str, SourceState],
                            classifications: Mapping[str, Classification], pack: DomainPack,
                            llm: LlmClient, *, audience: Sensitivity, stamp: DocwikiStamp
                            ) -> tuple[list[Page], list[CitedLocator], list[TopicSkip]]
```

- Prompts live in `src/docwiki/stages/prompts/` with a `PROMPT_VERSION` per prompt.
- Pages contain footnotes whose targets are sidecar paths in the content namespace
  (`relative_link(page_path, f"evidence/{sid}/{key}.md")`); every footnote's locator is
  returned as a `CitedLocator` so that the evidence stage materialises it.
- Links section, backlinks block and indexes are NOT produced here (assemble lane).

## Assemble lane — everything else

- `docwiki.storage.blob.BlobStorage` implementing the `Storage` protocol on Azure Blob Storage
  (Entra auth, ETags, blob leases clamped to 15–60 s).
- Stages `discover`, `links`, `indexes`, `agentkit`, `verify`, `publish`, `site` (calls the site
  lane's `docwiki.site.build_site`), and the orchestration (Microsoft Agent Framework workflow with
  a plain-async fallback, cache keys, state shards, run reports and cost receipts, queue worker and
  reconcile loop).
- CLI commands of pipeline.md §8 (`serve` delegates to `docwiki.mcp.server.main`, `ask` delegates
  to `docwiki.agents_client.ask`).
- Until the other lanes are merged, tests use stubs with exactly the signatures above.

## Other lanes

- Site: `docwiki.site.build_site(release_root: Path, out_dir: Path, *, base_url: str | None = None) -> Path`.
- MCP: `docwiki.mcp.server.main(argv: list[str] | None = None) -> int`; `create_app(...)` for HTTP.
- Agents: `async docwiki.agents_client.ask(question: str, *, agent: str = "researcher") -> AgentAnswer`.
