// Client of "The process, live" (Process.tsx, ADR 0009, 0010) on the pipeline page.
//
// The portal says who is reading (/api/owner/me) and where every document is in the pipeline
// (/api/process). Both replies are data: paths, errors and names come from documents and
// storage, so they are rendered with DOM nodes and textContent only, and the only links are the
// platform's sign-in pages and site-absolute wiki pages. The owner adds a document with a PUT (the
// platform's sign-in refuses signed-in POSTs). Polling is fast while something is in the pipeline,
// slow otherwise, pauses on a hidden tab and stops when Quartz navigates away (window.addCleanup).
import { relativeHref } from "../../../plugins/transformers/docwiki-text"
import { STATES, State, asState, stateWords, statusPill } from "./status"

const SECTION = "section.docwiki-process"
/** Same stages, same order as `STAGES` in src/docwiki/site/process_page.py. */
const STAGES = [
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
  "verify",
  "site",
  "publish",
] as const
const ME_PATH = "api/owner/me"
const PROCESS_PATH = "api/process"
const UPLOAD_PATH = "api/owner/documents"
const OWNER_HEADER = "X-DocWiki-Owner"
const FAST_MS = 5_000
const SLOW_MS = 30_000
/** An upload keeps the fast polling this long, until its pages appear. */
const UPLOAD_FOLLOW_MS = 10 * 60_000
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
}

interface Doc {
  path: string
  title: string | null
  size: number | null
  modified: string | null
  status: string
  stage: string | null
  state: State
  step: number | null
  steps: number | null
  hidden: boolean
  pageUrl: string | null
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
let showAll = false

// ----- Parsing: every field is checked, anything else is dropped -----

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function text(value: unknown): string | null {
  return typeof value === "string" ? value : null
}

function number(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

function list(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

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

/** A site-absolute wiki page (`/sources/x`); hosts and schemes are not linked. */
function pageUrl(value: unknown): string | null {
  const url = text(value)
  return url && url.startsWith("/") && !url.startsWith("//") && !url.includes("\\") ? url : null
}

function parseMe(payload: unknown): Me | null {
  const data = record(payload)
  if (!data) return null
  const upload = record(data.upload)
  const maxMb = number(upload?.max_mb)
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
    step: number(data.step),
    steps: number(data.steps),
    hidden: data.hidden === true,
    pageUrl: pageUrl(data.page_url),
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

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`
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
  if (uploaded && Date.now() - uploaded.at < UPLOAD_FOLLOW_MS) return true
  if (!view) return false
  const latest = view.runs[0]
  return inPipeline(view) > 0 || (view.queued ?? 0) > 0 || (!!latest && !latest.finishedAt)
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

function anchor(href: string, content: string): HTMLAnchorElement {
  const node = element("a", undefined, content)
  node.setAttribute("href", href)
  return node
}

function badge(status: string): HTMLSpanElement {
  const known = /^[a-z-]+$/.test(status) ? ` docwiki-process-badge--${status}` : ""
  return element("span", `docwiki-process-badge${known}`, status)
}

function heading(content: string): HTMLHeadingElement {
  return element("h3", "docwiki-process-title", content)
}

function nowBlock(view: View): HTMLElement {
  const block = element("div", "docwiki-process-now")
  const facts: string[] = []
  const release = view.release
  if (release) {
    facts.push(`Release ${release.id}, published ${when(release.publishedAt)}`)
    const counts: string[] = []
    if (release.sources !== null) counts.push(plural(release.sources, "source"))
    if (release.pages !== null) counts.push(plural(release.pages, "page"))
    if (counts.length > 0) facts.push(counts.join(", "))
  } else {
    facts.push("No release published yet")
  }
  if (view.queued !== null) {
    const queued = view.queued >= QUEUE_PEEK_LIMIT ? `${QUEUE_PEEK_LIMIT}+` : String(view.queued)
    facts.push(`queue: ${queued}`)
  }
  block.append(element("p", "docwiki-process-facts", facts.join(" · ")))
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
  // While a run is unfinished, the first stage without a report is the one at work.
  const current = running ? STAGES.find((name) => !byStage.has(name)) : undefined
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

function documentRow(doc: Doc, owner: boolean): HTMLTableRowElement {
  const row = element("tr")
  const mine = uploaded !== null && doc.path === uploaded.path
  if (mine) row.className = "is-uploaded"
  const status = element("td", "docwiki-process-status")
  // A document whose stages are all done but whose release is not out yet is at "publish".
  const stage = doc.state === "processing" ? (doc.stage ?? "publish") : null
  status.append(statusPill(doc.state, stateWords(doc.state, doc.step, doc.steps, stage)))
  const name = element("td", "docwiki-process-name")
  if (doc.hidden) {
    name.append(element("span", "docwiki-process-hidden", doc.path))
  } else if (doc.title && doc.pageUrl) {
    const open = anchor(doc.pageUrl, doc.title)
    open.className = "docwiki-process-doc"
    open.dataset.focusKey = `page:${doc.path}`
    name.append(open)
    name.append(element("span", "docwiki-process-path", doc.path))
  } else {
    name.append(element("span", "docwiki-process-doc", doc.title ?? doc.path))
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
  const facts = element("td", "docwiki-process-when")
  facts.append(element("span", undefined, when(doc.modified)))
  if (doc.size !== null) facts.append(element("span", "docwiki-process-size", size(doc.size)))
  row.append(status, name, facts)
  return row
}

/** An upload the portal accepted that the document list does not show yet. */
function receivedRow(path: string): HTMLTableRowElement {
  const row = element("tr", "is-uploaded")
  const status = element("td", "docwiki-process-status")
  status.append(statusPill("received"))
  const name = element("td", "docwiki-process-name")
  name.append(element("span", "docwiki-process-doc", path))
  name.append(element("span", "docwiki-process-mine", "received — waiting for the pipeline"))
  row.append(status, name, element("td"))
  return row
}

function documentsTable(
  view: View,
  owner: boolean,
  rerender: (focusKey: string) => void,
): HTMLElement {
  const block = element("div", "docwiki-process-documents")
  block.append(heading(`Documents (${view.total})`))
  const breakdown = STATE_ORDER.filter((state) => (view.states[state] ?? 0) > 0).map(
    (state) => `${view.states[state]} ${stateWords(state).toLowerCase()}`,
  )
  if (breakdown.length > 0) {
    block.append(element("p", "docwiki-process-caption", breakdown.join(" · ")))
  }
  const docs = [...view.documents]
  const mine = uploaded ? docs.findIndex((doc) => doc.path === uploaded?.path) : -1
  if (mine > 0) docs.unshift(...docs.splice(mine, 1))
  const pseudo = uploaded !== null && mine < 0 ? uploaded.path : null
  if (docs.length === 0 && !pseudo) {
    block.append(element("p", "docwiki-process-caption", "No documents yet."))
    return block
  }
  // Focusable, so that a keyboard scrolls a table wider than the screen.
  const scroller = element("div", "docwiki-process-scroll")
  scroller.tabIndex = 0
  scroller.setAttribute("role", "region")
  scroller.setAttribute("aria-label", "Documents")
  scroller.dataset.focusKey = "documents"
  const table = element("table", "docwiki-process-table")
  const head = element("tr")
  for (const label of ["Status", "Document", "Received"]) {
    const cell = element("th", undefined, label)
    cell.scope = "col"
    head.append(cell)
  }
  const thead = element("thead")
  thead.append(head)
  const body = element("tbody")
  if (pseudo) body.append(receivedRow(pseudo))
  const shown = showAll ? docs : docs.slice(0, ROWS_COLLAPSED)
  for (const doc of shown) body.append(documentRow(doc, owner))
  table.append(thead, body)
  scroller.append(table)
  block.append(scroller)
  if (shown.length < docs.length) {
    const more = element("button", "docwiki-process-more", `Show all ${docs.length}`)
    more.type = "button"
    more.dataset.focusKey = "more"
    more.addEventListener("click", () => {
      showAll = true
      rerender("documents")
    })
    block.append(more)
  }
  return block
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

function runsList(view: View): HTMLElement {
  const block = element("div", "docwiki-process-runs")
  block.append(heading("Runs that published a release"))
  if (view.checks.count > 0) {
    const checks = plural(view.checks.count, "scheduled check")
    const last = view.checks.last ? `, the last ${when(view.checks.last)}` : ""
    block.append(element("p", "docwiki-process-caption", `${checks} found nothing to do${last}.`))
  }
  if (view.runs.length === 0) {
    block.append(element("p", "docwiki-process-caption", "No run recorded yet."))
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
    const facts = [`started ${when(run.startedAt)}`, duration(runDuration(run))]
    if (run.cost !== null) facts.push(`${run.currency ?? ""} ${run.cost.toFixed(2)}`.trim())
    const sources = runSources(run.counts)
    if (sources) facts.push(sources)
    const changed = ["new", "changed", "deleted"].some((key) => (run.counts[key] ?? 0) > 0)
    if (run.kind === "rebuild" && !changed) facts.push("no document changed: the site was rebuilt")
    const gates = Object.entries(run.gates)
      .filter(([, count]) => count > 0)
      .map(([status, count]) => `${count} ${status}`)
    if (gates.length > 0) facts.push(`gates: ${gates.join(", ")}`)
    item.append(title, element("p", "docwiki-process-run-facts", facts.join(" · ")))
    items.append(item)
  }
  block.append(items)
  return block
}

// ----- The owner: sign-in bar and upload form -----

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

function errorText(payload: unknown, status: number): string {
  const message = text(record(payload)?.error)
  return message ? `${message} (HTTP ${status})` : `The upload failed (HTTP ${status}).`
}

function uploadForm(
  upload: NonNullable<Me["upload"]>,
  done: () => void,
  titled: boolean,
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
  const status = element("p", "docwiki-process-upload-status")
  status.setAttribute("role", "status")
  status.setAttribute("aria-live", "polite")
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
  const state = element("p", "docwiki-process-state")
  state.setAttribute("role", "status")
  state.setAttribute("aria-live", "polite")
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

  // Every poll rebuilds the view: the focus and the table's sideways scroll are carried over.
  const render = (focusKey?: string) => {
    if (!alive || !view) return
    if (placeholder) placeholder.hidden = true
    const sentence = stateSentence(view)
    if (state.textContent !== sentence) state.textContent = sentence
    state.hidden = false
    const active = document.activeElement
    const key =
      focusKey ??
      (active instanceof HTMLElement && live.contains(active) ? active.dataset.focusKey : undefined)
    const scrollLeft = live.querySelector(".docwiki-process-scroll")?.scrollLeft ?? 0
    live.replaceChildren(
      nowBlock(view),
      stageStrip(view),
      documentsTable(view, isOwner, render),
      runsList(view),
    )
    const scroller = live.querySelector(".docwiki-process-scroll")
    if (scroller) scroller.scrollLeft = scrollLeft
    if (key) {
      const targets = Array.from(live.querySelectorAll<HTMLElement>("[data-focus-key]"))
      targets.find((node) => node.dataset.focusKey === key)?.focus({ preventScroll: true })
    }
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
      view = parsed
      note.hidden = true
      render()
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
      if (me.owner && me.upload) owner.append(uploadForm(me.upload, () => void poll(), !box))
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
