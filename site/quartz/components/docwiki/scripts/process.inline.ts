// Client of "The process, live" (Process.tsx, ADR 0009, 0010) on the pipeline page.
//
// The portal says who is reading (/api/owner/me) and where every document is in the pipeline
// (/api/process). Both replies are data: paths, errors and names come from documents and
// storage, so they are rendered with DOM nodes and textContent only, and the only links are the
// platform's sign-in pages and site-absolute wiki pages. The owner adds a document or rebuilds the
// wiki with a PUT (the platform's sign-in refuses signed-in POSTs). Polling is fast while
// something is in the pipeline, slow otherwise, pauses on a hidden tab and stops when Quartz
// navigates away (window.addCleanup).
//
// Each document row has its four-phase bar and a "Follow this document" disclosure (its journey).
// A poll updates the document rows by key: unchanged rows stay as they are, so focus, open
// disclosures and scroll are kept, and only real changes are announced, in the one polite region.
// The pure parts (phases, change lists, the row plan, the sentences) are in ./pipeline.
import { relativeHref } from "../../../plugins/transformers/docwiki-text"
import {
  DocFacts,
  LastChange,
  PHASES,
  Page,
  Phase,
  ReleaseChanges,
  RunDocument,
  STAGES,
  andMore,
  announcements,
  asPhase,
  capped,
  changeCount,
  changeSummary,
  list,
  noChangeSentence,
  number,
  parseChanges,
  parseLastChange,
  parseRunDocuments,
  phaseMarks,
  phaseText,
  planRows,
  plural,
  record,
  rowKeys,
  runAtWork,
  runDocumentsText,
  siteUrl,
  text,
} from "./pipeline"
import { STATES, State, asState, stateWords, statusPill } from "./status"

const SECTION = "section.docwiki-process"
const ME_PATH = "api/owner/me"
const PROCESS_PATH = "api/process"
const UPLOAD_PATH = "api/owner/documents"
const REBUILD_PATH = "api/owner/runs"
const OWNER_HEADER = "X-DocWiki-Owner"
const FAST_MS = 5_000
const SLOW_MS = 30_000
/** An upload or a rebuild keeps the fast polling this long, until its pages appear. */
const FOLLOW_MS = 10 * 60_000
/** Rebuilds a day (the portal's limit; it says how many are left). */
const REBUILDS_A_DAY = 5
const ROWS_COLLAPSED = 25
const RUNS_SHOWN = 10
/** Storage queues peek at most 32 messages (QUEUE_PEEK_LIMIT in docwiki.portal.process). */
const QUEUE_PEEK_LIMIT = 32
/** One upload path segment, as `check_upload_path` in docwiki.portal.process accepts it. */
const SEGMENT_RE = /^[A-Za-z0-9][A-Za-z0-9 ._()+-]{0,99}$/
const MAX_DEPTH = 4
const MAX_PATH_CHARS = 200
const UNAVAILABLE = "Status unavailable, retrying…"
const STATE_ORDER: readonly State[] = STATES

interface Me {
  signIn: boolean
  owner: boolean
  name: string | null
  signInUrl: string | null
  signOutUrl: string | null
  upload: { maxMb: number; uploadsLeft: number; extensions: string[] } | null
  rebuild: { left: number } | null
}

interface Doc {
  path: string
  title: string | null
  size: number | null
  modified: string | null
  status: string
  stage: string | null
  state: State
  phase: Phase | null
  step: number | null
  steps: number | null
  hidden: boolean
  pageUrl: string | null
  documentUrl: string | null
  lastChange: LastChange | null
  lastError: string | null
  failed: boolean
}

interface StageRun {
  stage: string
  status: string
  durationS: number | null
}

interface Run {
  kind: string
  requestedBy: string
  status: string
  startedAt: string | null
  finishedAt: string | null
  isCurrent: boolean
  currentStage: string | null
  documents: RunDocument[]
  changes: ReleaseChanges | null
  counts: Record<string, number>
  stages: StageRun[]
  gates: Record<string, number>
  currency: string | null
  cost: number | null
  durationS: number | null
}

interface View {
  release: {
    id: string
    publishedAt: string | null
    sources: number | null
    pages: number | null
  } | null
  runs: Run[]
  queued: number | null
  documents: Doc[]
  counts: Record<string, number>
  states: Record<string, number>
  /** Scheduled checks that found nothing to do: counted, not listed (ADR 0010). */
  checks: { count: number; last: string | null }
  total: number
}

/** The last upload of this page load (module state: it survives page navigations). */
let uploaded: { path: string; at: number } | null = null
/** Until when the polling stays fast after an upload or a rebuild. */
let followUntil = 0
let showAll = false
/** The rows whose journey is open, by key (kept across polls and page navigations). */
const expanded = new Set<string>()
let journeys = 0

// ----- Parsing: every field is checked, anything else is dropped -----

function numbers(value: unknown): Record<string, number> {
  const result: Record<string, number> = {}
  for (const [key, item] of Object.entries(record(value) ?? {})) {
    const n = number(item)
    if (n !== null) result[key] = n
  }
  return result
}

/** A platform sign-in or sign-out page; anything else is not linked. */
function authUrl(value: unknown): string | null {
  const url = text(value)
  return url && url.startsWith("/.auth/") ? url : null
}

function parseMe(payload: unknown): Me | null {
  const data = record(payload)
  if (!data) return null
  const upload = record(data.upload)
  const maxMb = number(upload?.max_mb)
  const left = number(record(data.rebuild)?.left)
  return {
    signIn: data.sign_in === true,
    owner: data.owner === true,
    name: text(data.name),
    signInUrl: authUrl(data.sign_in_url),
    signOutUrl: authUrl(data.sign_out_url),
    upload:
      upload && maxMb !== null
        ? {
            maxMb,
            uploadsLeft: number(upload.uploads_left) ?? 0,
            extensions: list(upload.extensions)
              .map(text)
              .filter((item): item is string => item !== null && /^\.[a-z0-9]+$/.test(item)),
          }
        : null,
    rebuild: left !== null ? { left: Math.max(0, left) } : null,
  }
}

function parseDoc(value: unknown): Doc | null {
  const data = record(value)
  const path = text(data?.path)
  const status = text(data?.status)
  const state = asState(data?.state)
  if (!data || !path || !status || !state) return null
  return {
    path,
    title: text(data.title),
    size: number(data.size),
    modified: text(data.modified),
    status,
    stage: text(data.stage),
    state,
    phase: asPhase(data.phase),
    step: number(data.step),
    steps: number(data.steps),
    hidden: data.hidden === true,
    pageUrl: siteUrl(data.page_url),
    documentUrl: siteUrl(data.document_url),
    lastChange: parseLastChange(data.last_change),
    lastError: text(data.last_error),
    failed: data.failed === true,
  }
}

function parseRun(value: unknown): Run | null {
  const data = record(value)
  if (!data) return null
  const cost = record(data.cost)
  const stages: StageRun[] = []
  for (const item of list(data.stages)) {
    const stage = record(item)
    const name = text(stage?.stage)
    if (!stage || !name) continue
    stages.push({
      stage: name,
      status: text(stage.status) ?? "",
      durationS: number(stage.duration_s),
    })
  }
  return {
    kind: text(data.kind) ?? "run",
    requestedBy: text(data.requested_by) ?? "",
    status: text(data.status) ?? "",
    startedAt: text(data.started_at),
    finishedAt: text(data.finished_at),
    isCurrent: data.is_current === true,
    currentStage: text(data.current_stage),
    documents: parseRunDocuments(data.documents),
    changes: parseChanges(data.changes),
    counts: numbers(data.counts),
    stages,
    gates: numbers(record(data.gates)?.summary),
    currency: text(cost?.currency),
    cost: number(cost?.total),
    durationS: number(cost?.duration_s),
  }
}

function parseView(payload: unknown): View | null {
  const data = record(payload)
  if (!data) return null
  const release = record(data.release)
  const id = text(release?.release_id)
  const documents = list(data.documents)
    .map(parseDoc)
    .filter((item): item is Doc => item !== null)
  return {
    release:
      release && id
        ? {
            id,
            publishedAt: text(release.published_at),
            sources: number(release.sources),
            pages: number(release.pages),
          }
        : null,
    runs: list(data.runs)
      .map(parseRun)
      .filter((item): item is Run => item !== null),
    queued: number(data.queued),
    documents,
    counts: numbers(data.counts),
    states: numbers(data.states),
    checks: {
      count: number(record(data.checks)?.count) ?? 0,
      last: text(record(data.checks)?.last),
    },
    total: number(data.total) ?? documents.length,
  }
}

function facts(doc: Doc): DocFacts {
  return {
    path: doc.path,
    title: doc.title,
    state: doc.state,
    phase: doc.phase,
    step: doc.step,
    steps: doc.steps,
    stage: doc.stage,
    hidden: doc.hidden,
  }
}

// ----- Formatting -----

const dateFormat = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" })

function when(value: string | null): string {
  if (!value) return "—"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "—" : dateFormat.format(date)
}

function duration(seconds: number | null): string {
  if (seconds === null || seconds < 0) return "—"
  if (seconds < 10) return `${seconds.toFixed(1)} s`
  if (seconds < 60) return `${Math.round(seconds)} s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes} min ${Math.round(seconds % 60)} s`
  return `${Math.floor(minutes / 60)} h ${minutes % 60} min`
}

function size(bytes: number | null): string {
  if (bytes === null) return "—"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

/** Elapsed time of a run: its receipt's duration, else from its start to its end (or now). */
function runDuration(run: Run): number | null {
  if (run.durationS !== null) return run.durationS
  const start = run.startedAt ? Date.parse(run.startedAt) : NaN
  const end = run.finishedAt ? Date.parse(run.finishedAt) : Date.now()
  return Number.isNaN(start) || Number.isNaN(end) ? null : (end - start) / 1000
}

/** Documents on their way to the release: received, queued or processing. */
function inPipeline(view: View): number {
  return (view.states.received ?? 0) + (view.states.queued ?? 0) + (view.states.processing ?? 0)
}

function busy(view: View | null): boolean {
  if (Date.now() < followUntil) return true
  if (!view) return false
  const latest = view.runs[0]
  return inPipeline(view) > 0 || (view.queued ?? 0) > 0 || (!!latest && !latest.finishedAt)
}

/** A random idempotency key for the portal (`[A-Za-z0-9-]{8,64}`). */
function randomKey(): string {
  if (typeof crypto.randomUUID === "function") return crypto.randomUUID()
  const bytes = crypto.getRandomValues(new Uint8Array(16))
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("")
}

// ----- DOM -----

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  content?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (content !== undefined) node.textContent = content
  return node
}

function anchor(href: string, content: string, focusKey?: string): HTMLAnchorElement {
  const node = element("a", undefined, content)
  node.setAttribute("href", href)
  if (focusKey) node.dataset.focusKey = focusKey
  return node
}

function badge(status: string): HTMLSpanElement {
  const known = /^[a-z-]+$/.test(status) ? ` docwiki-process-badge--${status}` : ""
  return element("span", `docwiki-process-badge${known}`, status)
}

function heading(content: string): HTMLHeadingElement {
  return element("h3", "docwiki-process-title", content)
}

/** "and n more" after a capped list, or nothing. */
function moreItem(more: number): HTMLLIElement[] {
  return more > 0 ? [element("li", "docwiki-process-and-more", andMore(more))] : []
}

/** Replace a block's content only when it differs, so its focus and selection stay. */
function swap(slot: HTMLElement, next: HTMLElement | null): void {
  const current = slot.firstElementChild
  if (!next) {
    if (current) slot.replaceChildren()
    return
  }
  if (current && slot.childElementCount === 1 && current.isEqualNode(next)) return
  slot.replaceChildren(next)
}

function nowBlock(view: View): HTMLElement {
  const block = element("div", "docwiki-process-now")
  const parts: string[] = []
  const release = view.release
  if (release) {
    parts.push(`Release ${release.id}, published ${when(release.publishedAt)}`)
    const counts: string[] = []
    if (release.sources !== null) counts.push(plural(release.sources, "source"))
    if (release.pages !== null) counts.push(plural(release.pages, "page"))
    if (counts.length > 0) parts.push(counts.join(", "))
  } else {
    parts.push("No release published yet")
  }
  if (view.queued !== null) {
    const queued = view.queued >= QUEUE_PEEK_LIMIT ? `${QUEUE_PEEK_LIMIT}+` : String(view.queued)
    parts.push(`queue: ${queued}`)
  }
  block.append(element("p", "docwiki-process-facts", parts.join(" · ")))
  const latest = view.runs[0]
  if (latest && !latest.finishedAt) {
    const work = element("p", "docwiki-process-at-work")
    work.append(statusPill("processing", runAtWork(latest.currentStage)))
    const documents = runDocumentsText(latest.documents)
    if (documents) work.append(element("span", "docwiki-process-at-work-docs", `— ${documents}`))
    block.append(work)
  }
  return block
}

function stateSentence(view: View): string {
  const waiting = inPipeline(view)
  const latest = view.runs[0]
  if (waiting > 0) return `Working — ${plural(waiting, "document")} in the pipeline`
  if ((view.queued ?? 0) > 0) return "Working — a run is queued"
  if (latest && !latest.finishedAt) return "Working — a run is in progress"
  return "Idle — the wiki is up to date"
}

/** The shape of a stage's status, as in the status vocabulary (status.ts). */
function stageShape(status: string): string {
  if (status === "done") return "●"
  if (status === "running" || status === "pending") return "◐"
  if (status === "failed") return "✕"
  if (status === "quarantined") return "⊘"
  return "○"
}

/** The 13 stages of the latest run: done, skipped, failed, running or not run. */
function stageStrip(view: View): HTMLElement {
  const block = element("div", "docwiki-process-pipeline")
  block.append(heading("Pipeline"))
  const latest = view.runs[0]
  const running = !!latest && !latest.finishedAt
  if (latest) {
    const state = running ? "running" : latest.status || "finished"
    block.append(
      element(
        "p",
        "docwiki-process-caption",
        `Latest run: ${latest.kind}, started ${when(latest.startedAt)} — ${state}`,
      ),
    )
  } else {
    block.append(element("p", "docwiki-process-caption", "No run recorded yet."))
  }
  const byStage = new Map((latest?.stages ?? []).map((stage) => [stage.stage, stage]))
  // While a run is unfinished, the portal names the stage at work (else: the first without a
  // report).
  const current = running
    ? (latest.currentStage ?? STAGES.find((name) => !byStage.has(name)))
    : undefined
  const strip = element("ol", "docwiki-process-stages")
  for (const name of STAGES) {
    const report = byStage.get(name)
    const status = report?.status || (name === current ? "running" : latest ? "not run" : "—")
    const item = element("li", "docwiki-process-stage")
    const key = status.replace(/ /g, "-")
    item.dataset.status = /^[a-z-]+$/.test(key) ? key : "none"
    item.append(element("span", "docwiki-process-stage-name", name))
    item.append(element("span", "docwiki-process-stage-status", `${stageShape(key)} ${status}`))
    if (report?.durationS !== null && report?.durationS !== undefined) {
      item.append(element("span", "docwiki-process-stage-time", duration(report.durationS)))
    }
    strip.append(item)
  }
  block.append(strip)
  return block
}

const PHASE_SHAPES = { done: "●", current: "◐", todo: "○" } as const

/** The four phases of a document in one line: shape, word and colour, with a text equivalent. */
function phaseBar(doc: Doc): HTMLElement | null {
  const marks = phaseMarks(doc.state, doc.phase, doc.step, doc.stage)
  if (!marks) return null
  const bar = element("span", "docwiki-phases")
  const visual = element("span", "docwiki-phases-bar")
  visual.setAttribute("aria-hidden", "true")
  PHASES.forEach((phase, index) => {
    const mark = marks[index]
    const item = element("span", `docwiki-phase docwiki-phase--${mark}`)
    item.append(element("span", "docwiki-phase-shape", PHASE_SHAPES[mark]), phase.word)
    visual.append(item)
  })
  const stage = doc.state === "processing" ? (doc.stage ?? "publish") : null
  const words = phaseText(doc.state, doc.phase, doc.step, doc.steps, stage)
  bar.append(visual, element("span", "sr-only", words))
  return bar
}

/** One step of a document's journey: a label and what it is. */
function journeyStep(label: string, ...content: (Node | string)[]): HTMLLIElement {
  const item = element("li", "docwiki-journey-step")
  item.append(element("span", "docwiki-journey-label", label))
  const value = element("span", "docwiki-journey-value")
  value.append(...content)
  item.append(value)
  return item
}

/** "Follow this document": the original, its document page, its status, the pages, its page. */
function journey(doc: Doc, key: string, id: string): HTMLElement {
  const block = element("div", "docwiki-journey")
  block.id = id
  const steps = element("ol", "docwiki-journey-steps")
  const received = [doc.path]
  if (doc.modified) received.push(`received ${when(doc.modified)}`)
  if (doc.size !== null) received.push(size(doc.size))
  steps.append(journeyStep("Original", received.join(" · ")))
  steps.append(
    journeyStep(
      "Document page",
      doc.documentUrl
        ? anchor(doc.documentUrl, "Pages and full text", `journey-doc:${key}`)
        : "not in the wiki yet",
    ),
  )
  const stage = doc.state === "processing" ? (doc.stage ?? "publish") : null
  const status = [stateWords(doc.state, doc.step, doc.steps, stage)]
  const phase = phaseText(doc.state, doc.phase, doc.step, doc.steps, stage)
  if (phase && doc.state === "processing") status.push(phase)
  steps.append(journeyStep("Status", status.join(" — ")))
  const change = doc.lastChange
  if (change) {
    const head = [plural(change.pages.length, "wiki page")]
    if (change.change) head.push(`document ${change.change}`)
    if (change.finishedAt) head.push(when(change.finishedAt))
    const { shown, more } = capped(change.pages)
    const pages = element("ul", "docwiki-journey-pages")
    shown.forEach((page, index) => {
      const item = element("li")
      item.append(element("span", `docwiki-change docwiki-change--${page.change}`, page.change))
      item.append(" ")
      if (page.url) item.append(anchor(page.url, page.title, `journey-page:${key}:${index}`))
      else item.append(element("span", "docwiki-journey-removed", page.title))
      pages.append(item)
    })
    pages.append(...moreItem(more))
    const value: (Node | string)[] = [head.join(" · ")]
    if (shown.length > 0) value.push(pages)
    steps.append(journeyStep("Its last run", ...value))
  } else {
    steps.append(journeyStep("Its last run", "no published run yet"))
  }
  steps.append(
    journeyStep(
      "Wiki page",
      doc.pageUrl ? anchor(doc.pageUrl, doc.title ?? doc.path, `journey-wiki:${key}`) : "—",
    ),
  )
  block.append(steps)
  return block
}

/**
 * One document: its row and, under it, its journey across the whole table (a row of its own,
 * shown by the "Follow this document" disclosure). Each document is one `tbody`, the unit that
 * the live updates keep, replace or move.
 */
function documentRow(
  doc: Doc,
  key: string,
  owner: boolean,
  mine: boolean,
): HTMLTableSectionElement {
  const group = element("tbody", "docwiki-process-group")
  group.dataset.key = key
  const row = element("tr")
  if (mine) row.className = "is-uploaded"
  group.append(row)
  const status = element("td", "docwiki-process-status")
  // A document whose stages are all done but whose release is not out yet is at "publish".
  const stage = doc.state === "processing" ? (doc.stage ?? "publish") : null
  status.append(statusPill(doc.state, stateWords(doc.state, doc.step, doc.steps, stage)))
  const bar = phaseBar(doc)
  if (bar) status.append(bar)
  const name = element("td", "docwiki-process-name")
  const label = doc.title ?? doc.path
  if (doc.hidden) {
    name.append(element("span", "docwiki-process-hidden", doc.path))
  } else if (doc.title && doc.pageUrl) {
    const open = anchor(doc.pageUrl, doc.title, `page:${key}`)
    open.className = "docwiki-process-doc"
    name.append(open)
    name.append(element("span", "docwiki-process-path", doc.path))
  } else {
    name.append(element("span", "docwiki-process-doc", label))
    if (doc.title) name.append(element("span", "docwiki-process-path", doc.path))
  }
  if (mine) name.append(element("span", "docwiki-process-mine", "your upload"))
  if (owner && doc.hidden) {
    name.append(element("span", "docwiki-process-mine", "not in this site's audience"))
  }
  if (owner && doc.lastError) {
    name.append(element("span", "docwiki-process-error", doc.lastError))
  } else if (doc.failed && doc.state !== "failed" && doc.state !== "held_back") {
    name.append(element("span", "docwiki-process-error", "an earlier attempt failed"))
  }
  // Documents kept out of the audience have no journey to show.
  if (!doc.hidden) {
    journeys += 1
    const id = `docwiki-journey-${journeys}`
    const open = expanded.has(key)
    const follow = element("button", "docwiki-follow")
    follow.type = "button"
    follow.dataset.focusKey = `follow:${key}`
    follow.setAttribute("aria-expanded", String(open))
    follow.setAttribute("aria-controls", id)
    follow.append(
      element("span", "docwiki-follow-icon", "▸"),
      "Follow this document",
      element("span", "sr-only", `: ${label}`),
    )
    follow.firstElementChild?.setAttribute("aria-hidden", "true")
    const path = element("tr", "docwiki-journey-row")
    const cell = element("td")
    cell.colSpan = 3
    cell.append(journey(doc, key, id))
    path.append(cell)
    path.hidden = !open
    group.classList.toggle("is-open", open)
    follow.addEventListener("click", () => {
      const now = follow.getAttribute("aria-expanded") !== "true"
      follow.setAttribute("aria-expanded", String(now))
      path.hidden = !now
      group.classList.toggle("is-open", now)
      if (now) expanded.add(key)
      else expanded.delete(key)
    })
    name.append(follow)
    group.append(path)
  }
  const received = element("td", "docwiki-process-when")
  received.append(element("span", undefined, when(doc.modified)))
  if (doc.size !== null) received.append(element("span", "docwiki-process-size", size(doc.size)))
  row.append(status, name, received)
  return group
}

/** An upload the portal accepted that the document list does not show yet. */
function receivedRow(path: string, key: string): HTMLTableSectionElement {
  const group = element("tbody", "docwiki-process-group")
  group.dataset.key = key
  const row = element("tr", "is-uploaded")
  group.append(row)
  const status = element("td", "docwiki-process-status")
  status.append(statusPill("received"))
  const name = element("td", "docwiki-process-name")
  name.append(element("span", "docwiki-process-doc", path))
  name.append(element("span", "docwiki-process-mine", "received — waiting for the pipeline"))
  row.append(status, name, element("td"))
  return group
}

interface Row {
  key: string
  sig: string
  node: HTMLTableSectionElement
}

/** The documents block: its rows are updated by key, never rebuilt as a whole. */
class DocumentsBlock {
  readonly root = element("div", "docwiki-process-documents")
  private readonly title = heading("Documents")
  private readonly caption = element("p", "docwiki-process-caption")
  private readonly empty = element("p", "docwiki-process-caption", "No documents yet.")
  private readonly scroller = element("div", "docwiki-process-scroll")
  private readonly table = element("table", "docwiki-process-table")
  private readonly more = element("div", "docwiki-process-more-slot")
  private rows: Row[] = []
  private readonly rerender: (focusKey: string) => void

  constructor(rerender: (focusKey: string) => void) {
    this.rerender = rerender
    // Focusable, so that a keyboard scrolls a table wider than the screen.
    this.scroller.tabIndex = 0
    this.scroller.setAttribute("role", "region")
    this.scroller.setAttribute("aria-label", "Documents")
    this.scroller.dataset.focusKey = "documents"
    const head = element("tr")
    for (const label of ["Status", "Document", "Received"]) {
      const cell = element("th", undefined, label)
      cell.scope = "col"
      head.append(cell)
    }
    const thead = element("thead")
    thead.append(head)
    this.table.append(thead)
    this.scroller.append(this.table)
    this.caption.hidden = true
    this.root.append(this.title, this.caption, this.empty, this.scroller, this.more)
  }

  update(view: View, owner: boolean): void {
    const title = `Documents (${view.total})`
    if (this.title.textContent !== title) this.title.textContent = title
    const breakdown = STATE_ORDER.filter((state) => (view.states[state] ?? 0) > 0)
      .map((state) => `${view.states[state]} ${stateWords(state).toLowerCase()}`)
      .join(" · ")
    if (this.caption.textContent !== breakdown) this.caption.textContent = breakdown
    this.caption.hidden = breakdown === ""

    const docs = [...view.documents]
    const mineAt = uploaded ? docs.findIndex((doc) => doc.path === uploaded?.path) : -1
    if (mineAt > 0) docs.unshift(...docs.splice(mineAt, 1))
    const pseudo = uploaded !== null && mineAt < 0 ? uploaded.path : null
    const shown = showAll ? docs : docs.slice(0, ROWS_COLLAPSED)
    const keys = rowKeys(shown.map((doc) => doc.path))
    const next: { key: string; sig: string; build: () => HTMLTableSectionElement }[] = []
    if (pseudo) {
      const key = `upload:${pseudo}`
      next.push({ key, sig: "received", build: () => receivedRow(pseudo, key) })
    }
    shown.forEach((doc, index) => {
      const key = keys[index]
      const mine = uploaded !== null && doc.path === uploaded.path
      next.push({
        key,
        sig: JSON.stringify([doc, owner, mine]),
        build: () => documentRow(doc, key, owner, mine),
      })
    })

    const plan = planRows(this.rows, next)
    const nodes = new Map(this.rows.map((row) => [row.key, row.node]))
    for (const key of plan.removed) nodes.get(key)?.remove()
    const rows: Row[] = []
    plan.items.forEach((item, index) => {
      const spec = next[index]
      let node = nodes.get(item.key)
      if (item.action !== "keep" || !node) {
        const built = spec.build()
        if (node) node.replaceWith(built)
        node = built
      }
      // Moved only when it is not already in its place (the table's first child is its head).
      const at = this.table.children[index + 1]
      if (at !== node) this.table.insertBefore(node, at ?? null)
      rows.push({ key: item.key, sig: spec.sig, node })
    })
    this.rows = rows

    const none = next.length === 0
    this.empty.hidden = !none
    this.scroller.hidden = none
    let more: HTMLElement | null = null
    if (shown.length < docs.length) {
      more = element("button", "docwiki-process-more", `Show all ${docs.length}`)
      more.setAttribute("type", "button")
      more.dataset.focusKey = "more"
      more.addEventListener("click", () => {
        showAll = true
        this.rerender("documents")
      })
    }
    swap(this.more, more)
  }
}

function runSources(counts: Record<string, number>): string | null {
  const parts = ["new", "changed", "deleted", "unchanged", "quarantined", "failed"]
    .filter((key) => (counts[key] ?? 0) > 0)
    .map((key) => `${counts[key]} ${key}`)
  const total = counts.sources_total
  if (total === undefined && parts.length === 0) return null
  const head = total === undefined ? "sources" : plural(total, "source")
  return parts.length > 0 ? `${head}: ${parts.join(", ")}` : head
}

/** One kind of change of the release: its pages, linked, at most 10 then "and n more". */
function changeGroup(kind: string, label: string, pages: Page[]): HTMLElement | null {
  if (pages.length === 0) return null
  const group = element("div", "docwiki-release-group")
  group.append(element("p", "docwiki-release-label", `${label} (${pages.length})`))
  const items = element("ul", "docwiki-release-pages")
  const { shown, more } = capped(pages)
  shown.forEach((page, index) => {
    const item = element("li")
    if (page.url) item.append(anchor(page.url, page.title, `release:${kind}:${index}`))
    else item.append(element("span", "docwiki-journey-removed", page.title))
    if (page.type) item.append(" ", element("span", "docwiki-release-type", page.type))
    items.append(item)
  })
  items.append(...moreItem(more))
  group.append(items)
  return group
}

/** "What changed in this release", from the run that published the current release. */
function releaseChanges(view: View): HTMLElement | null {
  const run = view.runs.find((item) => item.isCurrent && item.changes !== null)
  if (!run || !run.changes) return null
  const changes = run.changes
  const block = element("div", "docwiki-release")
  block.append(heading("What changed in this release"))
  if (changeCount(changes) === 0) {
    block.append(element("p", "docwiki-process-caption", noChangeSentence(run.kind)))
    return block
  }
  block.append(element("p", "docwiki-release-summary", changeSummary(changes)))
  const groups = [
    changeGroup("added", "Pages added", changes.added),
    changeGroup("changed", "Pages changed", changes.changed),
    changeGroup("removed", "Pages removed", changes.removed),
    changeGroup("opened", "Contradictions opened", changes.opened),
    changeGroup("closed", "Contradictions closed", changes.closed),
  ].filter((group): group is HTMLElement => group !== null)
  const grid = element("div", "docwiki-release-groups")
  grid.append(...groups)
  block.append(grid)
  return block
}

function runsList(view: View): HTMLElement {
  const block = element("div", "docwiki-process-runs")
  block.append(heading("Runs that published a release"))
  if (view.checks.count > 0) {
    const checks = plural(view.checks.count, "scheduled check")
    const last = view.checks.last ? `, the last ${when(view.checks.last)}` : ""
    block.append(element("p", "docwiki-process-caption", `${checks} found nothing to do${last}.`))
  }
  if (view.runs.length === 0) {
    const empty = "No run yet — the owner adds a document to start one."
    block.append(element("p", "docwiki-process-caption", empty))
    return block
  }
  const items = element("ul", "docwiki-process-run-list")
  for (const run of view.runs.slice(0, RUNS_SHOWN)) {
    const item = element("li", "docwiki-process-run")
    const title = element("p", "docwiki-process-run-title")
    const who = run.requestedBy ? ` · ${run.requestedBy}` : ""
    title.append(element("strong", undefined, `${run.kind}${who}`), " ")
    title.append(badge(run.finishedAt ? run.status || "finished" : "running"))
    if (run.isCurrent) {
      title.append(" ", element("span", "docwiki-process-current", "current release"))
    }
    const parts = [`started ${when(run.startedAt)}`, duration(runDuration(run))]
    if (run.cost !== null) parts.push(`${run.currency ?? ""} ${run.cost.toFixed(2)}`.trim())
    const sources = runSources(run.counts)
    if (sources) parts.push(sources)
    const changed = ["new", "changed", "deleted"].some((key) => (run.counts[key] ?? 0) > 0)
    if (run.kind === "rebuild" && !changed) parts.push("no document changed: the site was rebuilt")
    const gates = Object.entries(run.gates)
      .filter(([, count]) => count > 0)
      .map(([status, count]) => `${count} ${status}`)
    if (gates.length > 0) parts.push(`gates: ${gates.join(", ")}`)
    item.append(title, element("p", "docwiki-process-run-facts", parts.join(" · ")))
    items.append(item)
  }
  block.append(items)
  return block
}

// ----- The owner: sign-in bar, upload form and rebuild -----

function ownerBar(me: Me): HTMLElement | null {
  if (me.owner) {
    const bar = element("p", "docwiki-process-owner", `Signed in as ${me.name ?? "the owner"}`)
    if (me.signOutUrl) bar.append(" · ", anchor(me.signOutUrl, "sign out"))
    return bar
  }
  if (me.signIn && me.signInUrl) {
    const bar = element("div", "docwiki-process-owner")
    const signIn = anchor(me.signInUrl, "Sign in to add a document")
    signIn.className = "docwiki-process-submit docwiki-owner-box-sign-in"
    bar.append(signIn)
    return bar
  }
  return null
}

/** `raw/`-relative path of the upload, or why the portal would refuse it. */
function uploadPath(folder: string, file: File): { path: string } | { error: string } {
  const parts = folder
    .split("/")
    .map((part) => part.trim())
    .filter((part) => part !== "")
  parts.push(file.name)
  if (parts.length > MAX_DEPTH) return { error: `Use at most ${MAX_DEPTH - 1} folders.` }
  for (const part of parts) {
    if (!SEGMENT_RE.test(part) || part.endsWith(".")) {
      return {
        error: `“${part}” cannot be used: names use letters, digits, spaces and ._()+- only.`,
      }
    }
  }
  const path = parts.join("/")
  if (path.length > MAX_PATH_CHARS) return { error: "The path is too long." }
  return { path }
}

function errorText(payload: unknown, status: number, what = "The upload"): string {
  const message = text(record(payload)?.error)
  return message ? `${message} (HTTP ${status})` : `${what} failed (HTTP ${status}).`
}

/** The owner's polite status line, shared by the upload and the rebuild. */
function ownerStatus(): HTMLParagraphElement {
  const status = element("p", "docwiki-process-upload-status")
  status.setAttribute("role", "status")
  status.setAttribute("aria-live", "polite")
  return status
}

function uploadForm(
  upload: NonNullable<Me["upload"]>,
  done: () => void,
  titled: boolean,
  status: HTMLElement,
): HTMLElement {
  const form = element("form", "docwiki-process-upload")
  form.noValidate = true
  if (titled) form.append(element("h3", "docwiki-process-title", "Add a document"))

  const fileLabel = element("label", "docwiki-process-label", "Document")
  fileLabel.htmlFor = "docwiki-process-file"
  const file = element("input", "docwiki-process-file")
  file.type = "file"
  file.id = "docwiki-process-file"
  file.accept = upload.extensions.join(",")

  const folderLabel = element("label", "docwiki-process-label", "Folder (optional)")
  folderLabel.htmlFor = "docwiki-process-folder"
  const folder = element("input", "docwiki-process-input")
  folder.type = "text"
  folder.id = "docwiki-process-folder"
  folder.autocomplete = "off"
  folder.spellcheck = false
  folder.maxLength = MAX_PATH_CHARS
  folder.placeholder = "for example planning, devis or achats"

  const replaceLabel = element("label", "docwiki-process-check")
  const replace = element("input")
  replace.type = "checkbox"
  replaceLabel.append(replace, " Replace if it exists")

  const submit = element("button", "docwiki-process-submit", "Add to the wiki")
  submit.type = "submit"
  const problem = element("p", "docwiki-process-upload-error")
  problem.setAttribute("role", "alert")
  problem.hidden = true
  const hint = element("p", "docwiki-process-hint")
  const sayHint = () => {
    hint.textContent =
      `Up to ${upload.maxMb} MB · ${plural(upload.uploadsLeft, "upload")} left today · ` +
      upload.extensions.join(" ")
  }
  sayHint()
  const fail = (message: string) => {
    status.textContent = ""
    problem.textContent = message
    problem.hidden = false
  }

  form.append(fileLabel, file, folderLabel, folder, replaceLabel, submit, status, problem, hint)
  form.addEventListener("submit", (event) => {
    event.preventDefault()
    if (submit.disabled) return
    problem.hidden = true
    const chosen = file.files?.[0]
    if (!chosen) return fail("Choose a document first.")
    const dot = chosen.name.lastIndexOf(".")
    const extension = dot < 0 ? "" : chosen.name.slice(dot).toLowerCase()
    if (!upload.extensions.includes(extension)) {
      return fail(`This file type cannot be added; use ${upload.extensions.join(" ")}.`)
    }
    if (chosen.size === 0) return fail("The file is empty.")
    if (chosen.size > upload.maxMb * 1024 * 1024) {
      return fail(`The file is larger than ${upload.maxMb} MB.`)
    }
    const checked = uploadPath(folder.value, chosen)
    if ("error" in checked) return fail(checked.error)
    const encoded = checked.path.split("/").map(encodeURIComponent).join("/")
    const query = replace.checked ? "?replace=1" : ""
    const target = relativeHref(currentSlug(), `${UPLOAD_PATH}/${encoded}`) + query
    submit.disabled = true
    status.textContent = `Uploading ${checked.path}…`
    fetch(target, {
      method: "PUT",
      headers: {
        [OWNER_HEADER]: "1",
        "Content-Type": chosen.type || "application/octet-stream",
      },
      body: chosen,
      credentials: "same-origin",
    })
      .then(async (response) => {
        const payload = await response.json().catch((): unknown => null)
        if (response.status !== 201) return fail(errorText(payload, response.status))
        const result = record(payload)
        const path = text(result?.path) ?? checked.path
        const left = number(result?.uploads_left)
        if (left !== null) upload.uploadsLeft = left
        sayHint()
        uploaded = { path, at: Date.now() }
        followUntil = Date.now() + FOLLOW_MS
        form.reset()
        status.textContent = `Uploaded ${path}. The pipeline starts within a minute: `
        status.append(anchor("#docwiki-live", "follow it live"), ".")
        done()
      })
      .catch((error: unknown) => {
        console.error("DocWiki: the upload failed", error)
        fail("The upload did not reach the portal; check the connection and try again.")
      })
      .finally(() => {
        submit.disabled = false
      })
  })
  return form
}

/** "Rebuild the wiki": a run that rebuilds every page and the site from the cache. */
function rebuildControl(
  rebuild: NonNullable<Me["rebuild"]>,
  done: () => void,
  status: HTMLElement,
): HTMLElement {
  const block = element("div", "docwiki-process-rebuild")
  const button = element("button", "docwiki-process-submit docwiki-process-rebuild-button")
  button.type = "button"
  button.textContent = "Rebuild the wiki"
  const hint = element("p", "docwiki-process-hint")
  hint.id = "docwiki-process-rebuild-hint"
  button.setAttribute("aria-describedby", hint.id)
  const sayHint = () => {
    hint.textContent =
      "Rebuilds every page and the site from the cache; about $0 when no document changed; " +
      `at most ${REBUILDS_A_DAY} a day, ${rebuild.left} left.`
    button.disabled = rebuild.left <= 0
  }
  sayHint()
  button.addEventListener("click", () => {
    if (button.disabled) return
    button.disabled = true
    status.textContent = "Asking for a rebuild…"
    const target = relativeHref(currentSlug(), `${REBUILD_PATH}/${randomKey()}`)
    fetch(target, { method: "PUT", headers: { [OWNER_HEADER]: "1" }, credentials: "same-origin" })
      .then(async (response) => {
        const payload = await response.json().catch((): unknown => null)
        const left = number(record(payload)?.rebuilds_left)
        if (left !== null) rebuild.left = Math.max(0, left)
        if (response.status !== 202) {
          if (response.status === 429) rebuild.left = 0
          status.textContent = errorText(payload, response.status, "The rebuild")
          return
        }
        followUntil = Date.now() + FOLLOW_MS
        status.textContent =
          "Rebuild queued: it starts within a minute; follow it in the pipeline below."
        done()
      })
      .catch((error: unknown) => {
        console.error("DocWiki: the rebuild request failed", error)
        status.textContent =
          "The rebuild request did not reach the portal; check the connection and try again."
      })
      .finally(sayHint)
  })
  block.append(button, hint)
  return block
}

// ----- Page life: fetch, render, poll -----

function currentSlug(): string {
  return document.body.dataset.slug ?? "index"
}

async function getJson(path: string): Promise<{ status: number; payload: unknown }> {
  const response = await fetch(relativeHref(currentSlug(), path), {
    credentials: "same-origin",
    cache: "no-store",
  })
  const payload = response.ok ? await response.json() : null
  return { status: response.status, payload }
}

document.addEventListener("nav", () => {
  const section = document.querySelector<HTMLElement>(SECTION)
  if (!section) return
  const placeholder = section.querySelector<HTMLElement>(".docwiki-process-placeholder")
  // The owner's box at the top of the page (OwnerBox.tsx), or the top of this section without it.
  const box = document.querySelector<HTMLElement>(".docwiki-owner-box")
  const owner =
    box?.querySelector<HTMLElement>(".docwiki-process-owner-area") ??
    element("div", "docwiki-process-owner-area")
  // The one polite region of the live view: the state sentence and the changes since the last
  // poll. It becomes live after the first render, which is never announced.
  const state = element("p", "docwiki-process-state")
  const sentence = element("span", "docwiki-process-sentence")
  const latestChange = element("span", "docwiki-process-change")
  state.append(sentence, latestChange)
  state.hidden = true
  const live = element("div", "docwiki-process-live")
  const note = element("p", "docwiki-process-note", UNAVAILABLE)
  note.hidden = true
  if (!owner.isConnected) section.append(owner)
  // The live view comes before the disclosure of the 13 technical steps (Process.tsx).
  const steps = section.querySelector<HTMLElement>(".docwiki-process-steps")
  if (steps) steps.before(state, live, note)
  else section.append(state, live, note)

  let alive = true
  let timer = 0
  let view: View | null = null
  let isOwner = false
  let seen: DocFacts[] | null = null

  const nowSlot = element("div", "docwiki-process-slot")
  const stagesSlot = element("div", "docwiki-process-slot")
  const changesSlot = element("div", "docwiki-process-slot")
  const runsSlot = element("div", "docwiki-process-slot")
  // A poll updates the blocks in place: the focus moves back if its element was replaced.
  const render = (focusKey?: string) => {
    if (!alive || !view) return
    if (placeholder) placeholder.hidden = true
    const said = stateSentence(view)
    if (sentence.textContent !== said) sentence.textContent = said
    state.hidden = false
    const active = document.activeElement
    const key =
      focusKey ??
      (active instanceof HTMLElement && live.contains(active) ? active.dataset.focusKey : undefined)
    if (!live.hasChildNodes()) {
      live.append(nowSlot, stagesSlot, documents.root, changesSlot, runsSlot)
    }
    swap(nowSlot, nowBlock(view))
    swap(stagesSlot, stageStrip(view))
    documents.update(view, isOwner)
    swap(changesSlot, releaseChanges(view))
    swap(runsSlot, runsList(view))
    if (key && (focusKey || !document.activeElement || !live.contains(document.activeElement))) {
      const targets = Array.from(live.querySelectorAll<HTMLElement>("[data-focus-key]"))
      targets.find((node) => node.dataset.focusKey === key)?.focus({ preventScroll: true })
    }
  }
  const documents = new DocumentsBlock(render)

  /** Say what changed since the last poll; the first render says nothing. */
  const announce = (next: View) => {
    const current = next.documents.map(facts)
    const sentences = announcements(seen, current)
    if (seen === null) {
      state.setAttribute("role", "status")
      state.setAttribute("aria-live", "polite")
    }
    seen = current
    if (sentences.length > 0) latestChange.textContent = `${sentences.join("; ")}.`
  }

  const schedule = (ms: number) => {
    window.clearTimeout(timer)
    if (alive && !document.hidden) timer = window.setTimeout(() => void poll(), ms)
  }

  const poll = async () => {
    if (!alive) return
    try {
      const { status, payload } = await getJson(PROCESS_PATH)
      if (!alive) return
      // A static host has no portal: the placeholder stays and nothing is polled.
      if (status === 404 && view === null) return
      const parsed = status === 200 ? parseView(payload) : null
      if (!parsed) throw new Error(`HTTP ${status}`)
      const first = view === null
      view = parsed
      note.hidden = true
      render()
      if (first) {
        // Live only after the first render is on screen, so it is not read out.
        window.requestAnimationFrame(() => announce(parsed))
      } else {
        announce(parsed)
      }
    } catch (error) {
      if (!alive) return
      console.warn("DocWiki: the process status could not be read", error)
      note.hidden = false
    }
    schedule(busy(view) ? FAST_MS : SLOW_MS)
  }

  const onVisibility = () => {
    if (document.hidden) window.clearTimeout(timer)
    else void poll()
  }

  getJson(ME_PATH)
    .then(({ payload }) => {
      const me = parseMe(payload)
      if (!alive || !me) return
      isOwner = me.owner
      const bar = ownerBar(me)
      if (bar) owner.append(bar)
      const status = ownerStatus()
      const done = () => void poll()
      if (me.owner && me.upload) owner.append(uploadForm(me.upload, done, !box, status))
      if (me.owner && me.rebuild) {
        owner.append(rebuildControl(me.rebuild, done, status))
        if (!me.upload) owner.append(status)
      }
      render() // owners see the names and errors hidden from visitors
    })
    .catch(() => {
      // No portal or no sign-in: the page stays read-only.
    })
  document.addEventListener("visibilitychange", onVisibility)
  void poll()

  window.addCleanup(() => {
    alive = false
    window.clearTimeout(timer)
    document.removeEventListener("visibilitychange", onVisibility)
  })
})
