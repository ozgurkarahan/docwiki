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
