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
  runId: string | null
  /** Content slugs of the run receipt and the quality report, when the release has them. */
  runPage: string | null
  qualityPage: string | null
  /** Gate counts from the release manifest, or from the run for a staged release. */
  quality: DocwikiQuality | null
  sources: Record<string, DocwikiSource>
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

