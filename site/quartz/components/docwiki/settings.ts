// Typed view of docwiki-site.json, written into the Quartz checkout by docwiki.site.build_site.
import raw from "../../../docwiki-site.json"
import { baseSlug, pageLanguage, slugIn, stringsFor } from "./i18n"
import type { Strings } from "./i18n"
import { en } from "./i18n/en.ts"

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
  /** The domain pack's label of the type (`PV de réception`): shown instead of the key. */
  docTypeLabel?: string | null
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
  /** The document's own language (`original_lang`, e.g. `fr`): its quotations are marked. */
  lang?: string | null
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

/** What differs in a mirror language (`en/…`, ADR 0012): slugs are full content slugs. */
export interface DocwikiMirror {
  pageTitle: string
  sources: Record<string, DocwikiSource>
  citedPages?: number
  scopes?: Record<string, { title: string; hub: string | null }>
  register?: DocwikiRegisterGroup[] | null
  explorer?: DocwikiSettings["explorer"]
  steps?: { name: string; text: string }[]
  /** Its pages kept untranslated, content slug (`en/sources/x`) → summary (canonical text). */
  untranslated?: Record<string, string>
}

export interface DocwikiSettings {
  schema: 1
  /** The wiki's languages, the canonical one first (`["fr", "en"]`); `["en"]` before slice G. */
  languages?: string[]
  /** One entry per mirror language (`en`): its title, sources, register and explorer. */
  mirrors?: Record<string, DocwikiMirror>
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
  explorer?: {
    hubFolders: string[]
    entitiesTitle: string | null
    /** Folder → title, e.g. `topics/moreau` → `Chantier Moreau` (per-scope topics). */
    folderTitles?: Record<string, string>
  }
  /**
   * Filed research answers published in `static/docwiki/answers.json` (ADR 0007); the "Ask this
   * wiki" drawer is rendered only when there is at least one.
   */
  answers: number
  /** The 13 pipeline stages and what each does (`STAGES` in src/docwiki/site/process_page.py). */
  steps?: { name: string; text: string }[]
  /** The home page's evaluation panel (src/docwiki/site/evals.py); null leaves it out. */
  evals?: DocwikiEvals | null
  /** Path of the architecture diagram under the site's root (`static/docwiki/architecture.svg`). */
  architecture?: string | null
}

/** A headline metric of the evaluation: share, denominator and passes. */
export interface DocwikiEvalMetric {
  value: number
  n: number
  passed: number | null
}

/** "Wiki + agent vs RAG": the scoreboard's headline cells for three systems (site.md §12.1). */
export interface DocwikiEvals {
  split: string
  questions: number | null
  date: string | null
  scoreboardUrl: string
  systems: {
    system: string
    accuracy: DocwikiEvalMetric | null
    numeric: DocwikiEvalMetric | null
    costPerQuestion: number | null
    pricesVerified: boolean
    latencyP50: number | null
  }[]
}

export const settings = raw as DocwikiSettings

/** The wiki's languages, the canonical one first. */
export const languages: readonly string[] =
  settings.languages && settings.languages.length > 0 ? settings.languages : ["en"]

/** The canonical language: the pages at the root of the site. */
export const canonicalLang = languages[0]

/** The mirror languages (each under its own folder: `en/`). */
export const mirrorLangs: readonly string[] = languages.slice(1)

/** The language of a page (its frontmatter's `lang`, else the folder it is in). */
export function pageLang(fileData: {
  slug?: string
  frontmatter?: { lang?: unknown } | null
}): string {
  return pageLanguage(fileData.slug ?? "index", fileData.frontmatter?.lang, languages)
}

/** The UI strings of a page's language. */
export function pageStrings(fileData: Parameters<typeof pageLang>[0]): Strings {
  return stringsFor(pageLang(fileData))
}

/** The page's slug without its mirror folder (`en/sources/x` → `sources/x`). */
export function pageBase(slug: string | undefined): string {
  return baseSlug(slug ?? "index", languages)
}

/** The slug of `base` in `lang` (`documents` → `en/documents`). */
export function inLang(base: string, lang: string): string {
  return slugIn(base, lang, languages)
}

const slugSets = new WeakMap<object, Set<string>>()

/** The slugs of the built pages (to know whether a page has a twin in another language). */
export function builtSlugs(files: readonly { slug?: string }[]): Set<string> {
  let found = slugSets.get(files)
  if (!found) {
    found = new Set(files.map((file) => file.slug ?? "").filter((slug) => slug !== ""))
    slugSets.set(files, found)
  }
  return found
}

/**
 * The same page in each language that has it (`[["fr", "sources/x"], ["en", "en/sources/x"]]`),
 * for the `hreflang` alternates; empty for a wiki without a mirror or a page without a twin.
 */
export function twins(slug: string, files: readonly { slug?: string }[]): [string, string][] {
  if (languages.length < 2 || slug === "404") return []
  const built = builtSlugs(files)
  const base = pageBase(slug)
  const found = languages
    .map((lang): [string, string] => [lang, inLang(base, lang)])
    .filter(([, twin]) => twin === slug || built.has(twin))
  return found.length > 1 ? found : []
}

/** The settings as seen from a page in `lang`: a mirror's title, page links and register. */
export function settingsFor(lang: string): DocwikiSettings {
  const mirror = settings.mirrors?.[lang]
  if (!mirror || lang === canonicalLang) return settings
  return {
    ...settings,
    pageTitle: mirror.pageTitle,
    sources: mirror.sources,
    citedPages: mirror.citedPages ?? settings.citedPages,
    scopes: mirror.scopes ?? settings.scopes,
    register: mirror.register ?? settings.register,
    explorer: mirror.explorer ?? settings.explorer,
    steps: mirror.steps ?? settings.steps,
  }
}

/**
 * The display name of a document type: the domain pack's label (`PV de réception`); a release
 * built before the labels shows its key in words (`Site meeting minutes`).
 */
export function docTypeName(
  docType: string | null | undefined,
  label: string | null | undefined,
): string | null {
  if (label && label.trim()) return label.trim()
  if (!docType) return null
  const words = docType.replace(/-/g, " ")
  return words.charAt(0).toUpperCase() + words.slice(1)
}

/**
 * Current or replaced: only for documents that have revisions (a number or an indice); a photo, a
 * delivery note or an e-mail is neither. `null` when there is nothing to say.
 */
export function revisionStatus(
  source: DocwikiSource | undefined,
  t: Strings = en,
): { state: "in_wiki" | "superseded"; words: string; title?: string } | null {
  if (!source) return null
  const words = t.documents
  if (source.status === "superseded") {
    const by = source.supersededByRevision
      ? words.supersededByRevision(source.supersededByRevision)
      : source.supersededBy
    return by
      ? {
          state: "superseded",
          words: words.supersededBy(by),
          title: source.supersededBy ?? undefined,
        }
      : { state: "superseded", words: words.superseded }
  }
  if (source.docNumber || source.revision) return { state: "in_wiki", words: words.current }
  return null
}

const dateFormats = new Map<string, Intl.DateTimeFormat>()

/** "20 Jan 2026" (or "20 janv. 2026") from an ISO date. */
export function humanDate(iso: string | null | undefined, t: Strings = en): string | null {
  if (!iso) return null
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`)
  if (Number.isNaN(date.getTime())) return null
  let format = dateFormats.get(t.dateLocale)
  if (!format) {
    format = new Intl.DateTimeFormat(t.dateLocale, { dateStyle: "medium", timeZone: "UTC" })
    dateFormats.set(t.dateLocale, format)
  }
  return format.format(date)
}

