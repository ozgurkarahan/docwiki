// Typed view of docwiki-site.json, written into the Quartz checkout by docwiki.site.build_site.
import raw from "../../../docwiki-site.json"

export interface DocwikiSource {
  /** Content slug of the source page (`sources/<slug>`), when the release has one. */
  page: string | null
  title: string
  /** Content path of the published original (`evidence/<source_id>/original.<ext>`). */
  original: string | null
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
  sources: Record<string, DocwikiSource>
}

export const settings = raw as DocwikiSettings
