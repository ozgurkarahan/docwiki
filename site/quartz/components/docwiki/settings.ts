// Typed view of docwiki-site.json, written into the Quartz checkout by docwiki.site.build_site.
import raw from "../../../docwiki-site.json"

export interface DocwikiSource {
  /** Content slug of the source page (`sources/<slug>`), when the release has one. */
  page: string | null
  title: string
  /** Content path of the published original (`evidence/<source_id>/original.<ext>`). */
  original: string | null
  /** `current`, `superseded` or `withdrawn` (catalog page status). */
  status?: string | null
  /** Content slug of the document page (`evidence/<source_id>/index`): pages, full text. */
  document?: string | null
  docType?: string | null
  docNumber?: string | null
  revision?: string | null
  /** The document's own date (its extraction, else its file name), ISO. */
  date?: string | null
  /** File extension of the original (`pdf`, `docx`, …). */
  format?: string | null
  /** Title and indice of the revision that replaces this one. */
  supersededBy?: string | null
  supersededByRevision?: string | null
  /** Scope value (a chantier code, or the default scope), phase key and lot (v1.7, ADR 0011). */
  scope?: string | null
  phase?: string | null
  lot?: string | null
}

/** One scope of the Documents register: its phases, each with its document types. */
export interface DocwikiRegisterGroup {
  scope: string | null
  title: string
  /** Content slug of the scope's hub page (`chantiers/moreau`), when it has one. */
  hub: string | null
  count: number
  phases: {
    phase: string | null
    title: string
    types: { type: string | null; title: string; sources: string[] }[]
  }[]
}

export interface DocwikiQuality {
  gates: number
  passed: number
  warned: number
  failed: number
  skipped: number
  blockingFailed: number
}

export interface DocwikiSettings {
  schema: 1
  pageTitle: string
  baseUrl: string | null
  repoUrl: string
  banner: string | null
  releaseId: string | null
  releaseDate: string | null
  audience: string | null
  quartzVersion: string
  /** Sources of this build by status (withdrawn sources have no page). */
  documents: { current: number; superseded: number }
  /** Wiki pages that cite at least one source (the story home's third card). */
  citedPages?: number
  runId: string | null
  /** Content slugs of the run receipt and the quality report, when the release has them. */
  runPage: string | null
  qualityPage: string | null
  /** Gate counts from the release manifest, or from the run for a staged release. */
  quality: DocwikiQuality | null
  sources: Record<string, DocwikiSource>
  /** Every scope value with its title and hub page (empty when the pack declares no scopes). */
  scopes?: Record<string, { title: string; hub: string | null }>
  /** The register grouped by scope, phase and type; null when no source has a scope. */
  register?: DocwikiRegisterGroup[] | null
  /** Explorer order: hub folders first; the `entities` folder's name when the wiki has scopes. */
  explorer?: { hubFolders: string[]; entitiesTitle: string | null }
  /**
   * Filed research answers published in `static/docwiki/answers.json` (ADR 0007); the "Ask this
   * wiki" drawer is rendered only when there is at least one.
   */
  answers: number
  /** The 13 pipeline stages and what each does (`STAGES` in src/docwiki/site/process_page.py). */
  steps?: { name: string; text: string }[]
}

export const settings = raw as DocwikiSettings

/**
 * Current or replaced: only for documents that have revisions (a number or an indice); a photo, a
 * delivery note or an e-mail is neither. `null` when there is nothing to say.
 */
export function revisionStatus(
  source: DocwikiSource | undefined,
): { state: "in_wiki" | "superseded"; words: string; title?: string } | null {
  if (!source) return null
  if (source.status === "superseded") {
    const by = source.supersededByRevision
      ? `indice ${source.supersededByRevision}`
      : source.supersededBy
    return by
      ? { state: "superseded", words: `Superseded by ${by}`, title: source.supersededBy ?? undefined }
      : { state: "superseded", words: "Superseded" }
  }
  if (source.docNumber || source.revision) return { state: "in_wiki", words: "Current" }
  return null
}

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" })

/** "20 Jan 2026" from an ISO date. */
export function humanDate(iso: string | null | undefined): string | null {
  if (!iso) return null
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? null : dateFormat.format(date)
}

