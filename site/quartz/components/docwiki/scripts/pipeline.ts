// Pure helpers of the pipeline page (scripts/process.inline.ts, ADR 0010, slice C): the four
// phases of a document, the journey and release-change data of /api/process, the capped lists,
// the keyed row plan of the live updates and the sentences announced in the polite region.
// No DOM, and no imports but the UI string tables (import-free): unit-tested directly with Node
// (tests/site/test_pipeline_text.py). The words come in the page's language (`t`, English by
// default).
import { en } from "../i18n/en.ts"
import type { Strings } from "../i18n/strings.ts"

/** The table passed in, else English (an `Array.map` callback gets an index there). */
function table(t: unknown): Strings {
  return typeof t === "object" && t !== null && "pipeline" in t ? (t as Strings) : en
}

/** The 14 stages, in order: same as `STAGES` in src/docwiki/site/process_page.py. */
export const STAGES = [
  "discover",
  "extract",
  "classify",
  "compile",
  "entities",
  "topics",
  "links",
  "indexes",
  "agentkit",
  "evidence",
  "translate",
  "verify",
  "site",
  "publish",
] as const

export type Phase = "read" | "file" | "write" | "check"

/** The business view of the 14 stages (the portal's `phase` of a document). */
export const PHASES: readonly { key: Phase; word: string; stages: readonly string[] }[] = [
  { key: "read", word: "Read", stages: ["discover", "extract"] },
  { key: "file", word: "File", stages: ["classify"] },
  {
    key: "write",
    word: "Write",
    stages: ["compile", "entities", "topics", "links", "indexes", "agentkit"],
  },
  {
    key: "check",
    word: "Check and publish",
    stages: ["evidence", "translate", "verify", "site", "publish"],
  },
]

export type PhaseMark = "done" | "current" | "todo" | "failed"

/** The word of a phase in the language of `t` ("Write", "Rédiger"). */
export function phaseWord(key: Phase, t: Strings = en): string {
  return table(t).pipeline.phases[key]
}

/** At most this many items of a list are shown; the rest is "and n more". */
export const LIST_CAP = 10

// ----- Parsing: every field is checked, anything else is dropped -----

export function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

export function text(value: unknown): string | null {
  return typeof value === "string" ? value : null
}

export function number(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

export function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

/** A site-absolute page (`/sources/x`); hosts, schemes and backslashes are not linked. */
export function siteUrl(value: unknown): string | null {
  const url = text(value)
  return url && url.startsWith("/") && !url.startsWith("//") && !url.includes("\\") ? url : null
}

export function asPhase(value: unknown): Phase | null {
  return PHASES.some((phase) => phase.key === value) ? (value as Phase) : null
}

/** The phase of a stage name, or of a 1-based step out of the 14. */
export function phaseOfStage(stage: string | null, step: number | null = null): Phase | null {
  const name = stage ?? (step !== null && step >= 1 ? (STAGES[step - 1] ?? null) : null)
  if (!name) return null
  return PHASES.find((phase) => phase.stages.includes(name))?.key ?? null
}

/**
 * The four marks of a document's phase bar, or null when it has none.
 *
 * Processing: the phases before its phase are done, its phase is in progress, the later ones are
 * not started (the portal's `phase`; its step or stage when the portal gives none). In the
 * release (in the wiki or superseded): all done. Received or queued: none started. Failed: the
 * phase where it stopped is failed (its stage or step; Read when unknown). Held back and removed
 * documents have no bar: their status says it.
 */
export function phaseMarks(
  state: string,
  phase: Phase | null,
  step: number | null = null,
  stage: string | null = null,
): PhaseMark[] | null {
  if (state === "in_wiki" || state === "superseded") return PHASES.map(() => "done")
  if (state === "received" || state === "queued") return PHASES.map(() => "todo")
  if (state !== "processing" && state !== "failed") return null
  const fallback = state === "failed" ? "read" : "check"
  const at = phase ?? phaseOfStage(stage, step) ?? fallback
  const index = PHASES.findIndex((item) => item.key === at)
  const here: PhaseMark = state === "failed" ? "failed" : "current"
  return PHASES.map((_item, i) => (i < index ? "done" : i === index ? here : "todo"))
}

/** The text equivalent of a phase bar: "Phase 3 of 4: Write, step 4/13 compile". */
export function phaseText(
  state: string,
  phase: Phase | null,
  step: number | null = null,
  steps: number | null = null,
  stage: string | null = null,
  t: Strings = en,
): string {
  const words = table(t).pipeline
  const marks = phaseMarks(state, phase, step, stage)
  if (!marks) return ""
  const count = PHASES.length
  if (marks.every((mark) => mark === "done")) return words.allPhasesDone(count)
  const stopped = marks.indexOf("failed")
  if (stopped >= 0) {
    return words.failedAtPhase(stopped + 1, count, words.phases[PHASES[stopped].key])
  }
  const index = marks.indexOf("current")
  if (index < 0) return words.notStarted(count)
  let text = words.phaseOf(index + 1, count, words.phases[PHASES[index].key])
  if (step !== null) {
    text += `, ${words.step(steps ? `${step}/${steps}` : String(step))}`
    if (stage) text += ` ${stage}`
  }
  return text
}

export type PageChange = "added" | "changed" | "removed"
export type DocumentChange = "new" | "changed" | "deleted" | "rebuilt"

export interface ChangedPage {
  title: string
  url: string | null
  change: PageChange
  type: string | null
}

export interface LastChange {
  runId: string | null
  finishedAt: string | null
  change: DocumentChange | null
  pages: ChangedPage[]
}

export interface Page {
  title: string
  url: string | null
  type: string | null
}

export interface ReleaseChanges {
  added: Page[]
  changed: Page[]
  removed: Page[]
  opened: Page[]
  closed: Page[]
}

export interface RunDocument {
  path: string
  title: string | null
  change: string | null
}

const PAGE_CHANGES: readonly string[] = ["added", "changed", "removed"]
const DOCUMENT_CHANGES: readonly string[] = ["new", "changed", "deleted", "rebuilt"]

/** A page of a change list; a removed page is never linked. */
export function parsePage(value: unknown, removed = false): Page | null {
  const data = record(value)
  const title = text(data?.title)
  if (!data || !title) return null
  return { title, url: removed ? null : siteUrl(data.url), type: text(data.type) }
}

function pages(value: unknown, removed = false): Page[] {
  return list(value)
    .map((item) => parsePage(item, removed))
    .filter((item): item is Page => item !== null)
}

export function parseLastChange(value: unknown): LastChange | null {
  const data = record(value)
  if (!data) return null
  const change = text(data.change)
  const changed: ChangedPage[] = []
  for (const item of list(data.pages)) {
    const kind = text(record(item)?.change)
    if (!kind || !PAGE_CHANGES.includes(kind)) continue
    const page = parsePage(item, kind === "removed")
    if (page) changed.push({ ...page, change: kind as PageChange })
  }
  return {
    runId: text(data.run_id),
    finishedAt: text(data.finished_at),
    change: change && DOCUMENT_CHANGES.includes(change) ? (change as DocumentChange) : null,
    pages: changed,
  }
}

export function parseChanges(value: unknown): ReleaseChanges | null {
  const data = record(value)
  if (!data) return null
  const contradictions = record(data.contradictions)
  return {
    added: pages(data.added),
    changed: pages(data.changed),
    removed: pages(data.removed, true),
    opened: pages(contradictions?.opened),
    closed: pages(contradictions?.closed),
  }
}

export function parseRunDocuments(value: unknown): RunDocument[] {
  const result: RunDocument[] = []
  for (const item of list(value)) {
    const data = record(item)
    const path = text(data?.path)
    if (!data || !path) continue
    result.push({ path, title: text(data.title), change: text(data.change) })
  }
  return result
}

/** How the journey shows a page's change: a chip for added and removed pages only. */
export function changeChip(change: PageChange): boolean {
  return change !== "changed"
}

export type OriginalLink = "open" | "download" | "none"

/** The original of a document: opened in a new tab, downloaded (e-mail) or not published. */
export function originalLink(path: string, url: string | null): OriginalLink {
  if (!url) return "none"
  return /\.eml$/i.test(path) ? "download" : "open"
}

/** "and n more" of a journey links to the release's changes when its run made the release. */
export function moreGoesToRelease(change: LastChange | null, currentRunId: string | null): boolean {
  return !!change?.runId && change.runId === currentRunId
}

// ----- Words -----

export function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`
}

/** The first `cap` items and how many more there are ("and n more"). */
export function capped<T>(items: readonly T[], cap = LIST_CAP): { shown: T[]; more: number } {
  return { shown: items.slice(0, cap), more: Math.max(0, items.length - cap) }
}

export function andMore(more: number, t: Strings = en): string {
  return more > 0 ? table(t).words.andMore(more) : ""
}

export function changeCount(changes: ReleaseChanges): number {
  return (
    changes.added.length +
    changes.changed.length +
    changes.removed.length +
    changes.opened.length +
    changes.closed.length
  )
}

/** "4 pages added · 2 changed · 1 removed · 1 contradiction opened", or "" when none. */
export function changeSummary(changes: ReleaseChanges, t: Strings = en): string {
  const words = table(t).pipeline
  const parts: string[] = []
  const pageParts: [number, "added" | "changed" | "removed"][] = [
    [changes.added.length, "added"],
    [changes.changed.length, "changed"],
    [changes.removed.length, "removed"],
  ]
  for (const [count, key] of pageParts) {
    if (count === 0) continue
    const word = words.changedWords[key](count)
    parts.push(parts.length === 0 ? `${words.pages(count)} ${word}` : `${count} ${word}`)
  }
  if (changes.opened.length > 0) {
    parts.push(words.contradictionsOpened(changes.opened.length, true))
  }
  const closed = changes.closed.length
  if (closed > 0) parts.push(words.contradictionsClosed(closed, changes.opened.length === 0))
  return parts.join(" · ")
}

/** The sentence of a release whose run changed no page. */
export function noChangeSentence(kind: string, t: Strings = en): string {
  const words = table(t).pipeline
  return kind === "rebuild" ? words.noChangeRebuild : words.noChange
}

/** "Run at work: compile (step 4/13)", or "Run at work" when the stage is not known. */
export function runAtWork(stage: string | null, t: Strings = en): string {
  const words = table(t).pipeline
  const index = stage ? STAGES.indexOf(stage as (typeof STAGES)[number]) : -1
  if (!stage) return words.runAtWork
  return index < 0
    ? words.runAtWorkStage(stage)
    : words.runAtWorkStep(stage, index + 1, STAGES.length)
}

/** "1 document: PLN-2026-003 indice B" (names capped at `cap`, then "and n more"). */
export function runDocumentsText(
  documents: readonly RunDocument[],
  cap = 3,
  t: Strings = en,
): string {
  if (documents.length === 0) return ""
  const { shown, more } = capped(documents, cap)
  const names = shown.map((doc) => doc.title ?? doc.path)
  if (more > 0) names.push(andMore(more, t))
  return table(t).pipeline.runDocuments(documents.length, names.join(", "))
}

// ----- Live updates -----

/** Unique keys for rows keyed by path (hidden rows all share one placeholder path). */
export function rowKeys(paths: readonly string[]): string[] {
  const seen = new Map<string, number>()
  return paths.map((path) => {
    const count = seen.get(path) ?? 0
    seen.set(path, count + 1)
    return count === 0 ? path : `${path}#${count + 1}`
  })
}

export type RowAction = "keep" | "update" | "insert"

/**
 * How to go from the rows on screen to the next ones, by key: rows whose signature did not change
 * are kept as they are (focus, open disclosures and scroll stay), changed rows are updated in
 * place, new rows inserted, and the keys no longer listed removed. The order is the next one.
 */
export function planRows(
  previous: readonly { key: string; sig: string }[],
  next: readonly { key: string; sig: string }[],
): { items: { key: string; action: RowAction }[]; removed: string[] } {
  const before = new Map(previous.map((row) => [row.key, row.sig]))
  const keys = new Set(next.map((row) => row.key))
  return {
    items: next.map((row) => {
      const sig = before.get(row.key)
      const action: RowAction = sig === undefined ? "insert" : sig === row.sig ? "keep" : "update"
      return { key: row.key, action }
    }),
    removed: previous.filter((row) => !keys.has(row.key)).map((row) => row.key),
  }
}

export interface DocFacts {
  path: string
  title: string | null
  state: string
  phase: Phase | null
  step: number | null
  steps: number | null
  stage: string | null
  hidden: boolean
}

function docPhaseWord(doc: DocFacts, t: Strings): string {
  const at = doc.phase ?? phaseOfStage(doc.stage, doc.step)
  const found = PHASES.find((phase) => phase.key === at)
  return found ? t.pipeline.phases[found.key] : t.status.processing
}

/** The sentence that announces a document's new status. */
export function docSentence(doc: DocFacts, t: Strings = en): string {
  const words = table(t)
  const name = doc.title ?? doc.path
  if (doc.state === "processing") {
    const of = doc.steps ? `${doc.step}/${doc.steps}` : String(doc.step)
    const step = doc.step === null ? null : words.pipeline.step(of)
    return words.pipeline.docProcessing(name, docPhaseWord(doc, words), step)
  }
  const sentences = words.pipeline.docState
  const say = Object.prototype.hasOwnProperty.call(sentences, doc.state)
    ? sentences[doc.state as keyof typeof sentences]
    : sentences.received
  return say(name)
}

/**
 * The real changes between two polls, as sentences: a new document, a new state or a new phase.
 * Nothing on the first render (`previous` null), nothing for documents kept out of the audience,
 * and at most `cap` sentences then "and n more changes".
 */
export function announcements(
  previous: readonly DocFacts[] | null,
  next: readonly DocFacts[],
  cap = 3,
  t: Strings = en,
): string[] {
  if (previous === null) return []
  const before = new Map(previous.filter((doc) => !doc.hidden).map((doc) => [doc.path, doc]))
  const sentences: string[] = []
  for (const doc of next) {
    if (doc.hidden) continue
    const old = before.get(doc.path)
    const moved =
      !old ||
      old.state !== doc.state ||
      (doc.state === "processing" &&
        (old.phase ?? phaseOfStage(old.stage, old.step)) !==
          (doc.phase ?? phaseOfStage(doc.stage, doc.step)))
    if (moved) sentences.push(docSentence(doc, t))
  }
  const { shown, more } = capped(sentences, cap)
  if (more > 0) shown.push(table(t).pipeline.moreChanges(more))
  return shown
}
