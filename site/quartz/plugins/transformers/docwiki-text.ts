// Pure helpers of the DocWiki overlay (transformer, components and the "Ask this wiki" drawer).
// No imports: unit-tested directly with Node (tests/site/test_overlay_text.py) and mirrored by
// docwiki.contracts.markdown and docwiki.site.answers in Python.

export const BACKLINKS_START = "<!-- docwiki:backlinks:start -->"
export const BACKLINKS_END = "<!-- docwiki:backlinks:end -->"

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
}

const BACKLINKS_BLOCK = new RegExp(
  escapeRegExp(BACKLINKS_START) + "[\\s\\S]*?" + escapeRegExp(BACKLINKS_END),
  "g",
)

/** Remove every generated backlinks block, markers included (Quartz renders its own panel). */
export function stripBacklinksBlock(markdown: string): string {
  return markdown.replace(BACKLINKS_BLOCK, "")
}

export type BadgeKind = "verified" | "paraphrase" | "table" | "ocr" | "generated" | "native"

export interface Badge {
  kind: BadgeKind
  text: string
  meaning: string
}

/** Citation badges of wiki-contract §5 (plus `paraphrase`, CONTRACT.md decision 4). */
export const CITATION_BADGES: readonly Badge[] = [
  {
    kind: "verified",
    text: "✓ quote verified",
    meaning: "the quoted words were found verbatim in the source text",
  },
  {
    kind: "paraphrase",
    text: "paraphrase",
    meaning: "reworded from the source text; numbers checked, no verbatim quote",
  },
  {
    kind: "table",
    text: "table",
    meaning: "values parsed deterministically from the cited table rows",
  },
  {
    kind: "ocr",
    text: "OCR",
    meaning: "text recognised from an image; compare it with the image",
  },
  {
    kind: "generated",
    text: "generated description",
    meaning: "written by a model to describe a figure; not a quote",
  },
]

/** Provenance of an evidence sidecar (evidence-contract §3) shown in its header. */
export const PROVENANCE_BADGES: Readonly<Record<string, Badge>> = {
  "native-text": {
    kind: "native",
    text: "native text",
    meaning: "taken from the document's own text layer",
  },
  "deterministic-table": {
    kind: "table",
    text: "table",
    meaning: "cell values parsed deterministically from the file",
  },
  ocr: {
    kind: "ocr",
    text: "OCR",
    meaning: "text recognised from pixels; check it against the image",
  },
  "model-description": {
    kind: "generated",
    text: "generated description",
    meaning: "written by a model; never cite it as a quote",
  },
}

const BADGE_ALTERNATION = CITATION_BADGES.map((badge) => escapeRegExp(badge.text)).join("|")
const TRAILING_BADGE = new RegExp(`^([\\s\\S]*?·\\s*)(${BADGE_ALTERNATION})(\\s*)$`)
const PROVENANCE_LABEL = new RegExp(`(Provenance:\\s*)(${BADGE_ALTERNATION})`)

export function badgeForText(text: string): Badge | undefined {
  return CITATION_BADGES.find((badge) => badge.text === text)
}

export interface BadgeSplit {
  before: string
  badge: Badge
  after: string
}

/** Split the text that ends a footnote definition (`… · ✓ quote verified`) around its badge. */
export function splitTrailingBadge(text: string): BadgeSplit | undefined {
  const match = TRAILING_BADGE.exec(text)
  if (!match) return undefined
  const badge = badgeForText(match[2])
  return badge ? { before: match[1], badge, after: match[3] } : undefined
}

/** Split `… Provenance: <badge> …` (evidence sidecar body) around its badge. */
export function splitProvenanceBadge(text: string): BadgeSplit | undefined {
  const match = PROVENANCE_LABEL.exec(text)
  if (!match) return undefined
  const badge = badgeForText(match[2])
  if (!badge) return undefined
  const start = match.index + match[1].length
  return {
    before: text.slice(0, start),
    badge,
    after: text.slice(start + match[2].length),
  }
}

export type NoticeKind = "fictional" | "superseded" | "warning"

/** Kind of a leading notice blockquote (`> FICTIONAL …`, `> **Superseded** by …`). */
export function noticeKind(text: string): NoticeKind | undefined {
  const head = text.trimStart()
  if (/^FICTIONAL\b/.test(head)) return "fictional"
  if (/^superseded\b/i.test(head)) return "superseded"
  if (/^(warning|withdrawn)\b/i.test(head)) return "warning"
  return undefined
}

/**
 * The home page repeats the domain pack's fictional notice that the site banner already shows on
 * every page: drop that copy. Document stamps on other pages stay.
 */
export function dropsSiteNotice(
  slug: string | undefined,
  siteBanner: boolean,
  kind: NoticeKind | undefined,
): boolean {
  return siteBanner && slug === "index" && kind === "fictional"
}

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`
}

/** "37 documents (1 superseded)" for the home page's provenance line. */
export function documentsPhrase(current: number, superseded: number): string {
  const total = plural(current + superseded, "document")
  return superseded > 0 ? `${total} (${superseded} superseded)` : total
}

export interface QualityCounts {
  gates: number
  passed: number
  warned: number
  failed: number
  skipped: number
  blockingFailed: number
}

/** "15 passed", "12 passed, 3 skipped", "14 passed, 1 warning" or "1 blocking gate failed". */
export function qualityPhrase(quality: QualityCounts): string {
  if (quality.blockingFailed > 0) {
    return `${plural(quality.blockingFailed, "blocking gate")} failed`
  }
  const parts = [`${quality.passed} passed`]
  if (quality.warned > 0) parts.push(plural(quality.warned, "warning"))
  if (quality.skipped > 0) parts.push(`${quality.skipped} skipped`)
  return parts.join(", ")
}

const DOCUMENT_EXTENSION = /\.(pdf|docx?|xlsx?|pptx?|csv|eml|vtt|txt|zip)$/i

/** Links to original files: no popover (PDF popovers would embed an iframe). */
export function isDocumentHref(href: string): boolean {
  const path = href.split("#", 1)[0].split("?", 1)[0]
  return DOCUMENT_EXTENSION.test(path)
}

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/

export function isIsoDay(value: unknown): value is string {
  return typeof value === "string" && ISO_DAY.test(value)
}

// ----- "Ask this wiki" drawer (ADR 0007): static/docwiki/answers.json -----
// Written by docwiki.site.answers; the drawer renders it with DOM nodes and textContent only.

/** `{"text": …}` or `{"cite": n}` (the number of one of the answer's citations). */
export interface AskSegment {
  text?: string
  cite?: number
}

export interface AskCitation {
  n: number
  title: string
  label: string
  /** Content slug of the evidence sidecar (`evidence/<source_id>/<locator_key>`). */
  href: string
  badge: string
}

export interface AskAnswer {
  id: string
  /** Content slug of the query page (`queries/<yyyy-mm-dd>-<slug>`). */
  slug: string
  question: string
  date: string
  banners: string[]
  paragraphs: AskSegment[][]
  citations: AskCitation[]
  steps: string[]
  /** "How this answer was produced": agent and version, dates, release, review ("" if none). */
  provenance: string
  /** Content slugs the answer is about: listed first on those pages. */
  pages: string[]
  /** A live answer of the Researcher (ADR 0008): not filed, so there is no page to open. */
  live?: boolean
}

const CONTENT_SLUG = /^[a-z0-9_][a-z0-9_.-]*(\/[a-z0-9_][a-z0-9_.-]*)*(#[A-Za-z0-9_-]+)?$/

/** A content slug of this site (`evidence/src-1/p0001`, optional `#anchor`); never a URL. */
export function isContentSlug(value: unknown): value is string {
  return typeof value === "string" && CONTENT_SLUG.test(value)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function isCount(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : []
}

function segments(value: unknown): AskSegment[] {
  if (!Array.isArray(value)) return []
  const result: AskSegment[] = []
  for (const item of value) {
    if (!isRecord(item)) continue
    if (typeof item.text === "string") result.push({ text: item.text })
    else if (isCount(item.cite)) result.push({ cite: item.cite })
  }
  return result
}

function citation(value: unknown): AskCitation | undefined {
  if (!isRecord(value) || !isCount(value.n) || !isContentSlug(value.href)) return undefined
  const { title, label, badge } = value
  if (typeof title !== "string" || typeof label !== "string") return undefined
  return {
    n: value.n,
    title,
    label,
    href: value.href,
    badge: typeof badge === "string" ? badge : "",
  }
}

function answer(value: unknown): AskAnswer | undefined {
  if (!isRecord(value)) return undefined
  const { id, slug, question, date } = value
  if (typeof id !== "string" || !id || !isContentSlug(slug)) return undefined
  if (typeof question !== "string" || !question.trim()) return undefined
  const paragraphs = Array.isArray(value.paragraphs) ? value.paragraphs.map(segments) : []
  const citations = Array.isArray(value.citations) ? value.citations.map(citation) : []
  const parsed: AskAnswer = {
    id,
    slug,
    question,
    date: typeof date === "string" ? date : "",
    banners: strings(value.banners),
    paragraphs: paragraphs.filter((paragraph) => paragraph.length > 0),
    citations: citations.filter((item): item is AskCitation => item !== undefined),
    steps: strings(value.steps),
    provenance: typeof value.provenance === "string" ? value.provenance : "",
    pages: strings(value.pages),
  }
  if (value.live === true) parsed.live = true
  return parsed
}

/**
 * Answers of `answers.json` (schema 1). The file is data: entries or fields of the wrong shape
 * are left out and links are content slugs only. Throws when the file is not schema 1.
 */
export function parseAnswers(payload: unknown): AskAnswer[] {
  if (!isRecord(payload) || payload.schema !== 1 || !Array.isArray(payload.answers)) {
    throw new Error("answers.json is not a schema 1 answers file")
  }
  return payload.answers.map(answer).filter((item): item is AskAnswer => item !== undefined)
}

export interface AnswerGroup {
  title: string
  answers: AskAnswer[]
}

/**
 * The drawer's question list on the page `slug`: answers about this page first, then the others
 * ("More questions"; "Questions" when none is about this page). The file order (newest first) is
 * kept inside each group.
 */
export function groupAnswers(answers: readonly AskAnswer[], slug: string): AnswerGroup[] {
  const here = answers.filter((item) => item.pages.includes(slug))
  const more = answers.filter((item) => !item.pages.includes(slug))
  const groups: AnswerGroup[] = []
  if (here.length > 0) groups.push({ title: "About this page", answers: here })
  if (more.length > 0) {
    groups.push({ title: here.length > 0 ? "More questions" : "Questions", answers: more })
  }
  return groups
}

/**
 * Relative URL from the page `current` (a Quartz full slug: `topics/schedule-and-window-delivery`,
 * `index`, `sources/index`) to the content slug `target` (`evidence/src-1/p0001`, optional
 * `#anchor`), as Quartz's `resolveRelative` computes it.
 */
export function relativeHref(current: string, target: string): string {
  const depth = current.split("/").filter((segment) => segment !== "").length - 1
  const root = depth > 0 ? Array<string>(depth).fill("..").join("/") : "."
  const hash = target.indexOf("#")
  const path = hash < 0 ? target : target.slice(0, hash)
  const anchor = hash < 0 ? "" : target.slice(hash)
  const simple = path === "index" ? "" : path.endsWith("/index") ? path.slice(0, -5) : path
  return `${root}/${simple}${anchor}`
}

/** "[2] Maintenance plan 2026 — sheet "Plan", rows 2–4" */
export function citationText(item: AskCitation): string {
  return `[${item.n}] ${item.title} — ${item.label}`
}

/** "How the agent worked (3 steps)" */
export function stepsLabel(count: number): string {
  return `How the agent worked (${plural(count, "step")})`
}

/**
 * The answer's provenance line: the note of "How this answer was produced" (its closing colon,
 * which introduces the tool steps on the page, becomes a full stop), else "Filed on <date>".
 */
export function provenanceLine(item: Pick<AskAnswer, "provenance" | "date">): string {
  const note = item.provenance.trim()
  if (note) return note.replace(/:$/, ".")
  return item.date ? `Filed on ${item.date}` : ""
}

/** Drawer state kept in sessionStorage: Quartz's page navigation replaces the whole body. */
export interface AskState {
  open: boolean
  /** Id of the selected answer, `null` for the question list. */
  answer: string | null
  /** Scroll position of the drawer's content. */
  scroll: number
  /** The drawer was collapsed to show a page opened from the answer (narrow screens). */
  resume: boolean
}

export const ASK_STATE_KEY = "docwiki-ask"

/**
 * Quartz's phone and tablet layouts (up to its desktop breakpoint, 1200 px included), where the
 * drawer covers the page text (a full-screen sheet on phones): following a link collapses it. Wider,
 * the drawer replaces the right-hand panel and the page column narrows (custom.scss).
 */
export const NARROW_QUERY = "(max-width: 1200px)"

/**
 * State after following a link of an answer (a citation, a source, the answer's page). On a narrow
 * screen the drawer collapses so that the page shows, keeping the answer to come back to; on wide
 * screens the drawer stays open beside the page.
 */
export function followLink(state: AskState, narrow: boolean, scroll: number): AskState {
  return narrow ? { ...state, open: false, resume: true, scroll } : { ...state, scroll }
}

/** Label of the floating button: "Back to the answer" after the drawer collapsed for a link. */
export function fabLabel(state: AskState): string {
  return state.resume && state.answer ? "Back to the answer" : "Ask this wiki"
}

export function parseAskState(raw: string | null | undefined): AskState {
  const state: AskState = { open: false, answer: null, scroll: 0, resume: false }
  if (!raw) return state
  let value: unknown
  try {
    value = JSON.parse(raw)
  } catch {
    return state
  }
  if (!isRecord(value)) return state
  state.open = value.open === true
  state.answer = typeof value.answer === "string" && value.answer ? value.answer : null
  const scroll = value.scroll
  state.scroll =
    typeof scroll === "number" && Number.isFinite(scroll) && scroll > 0 ? Math.round(scroll) : 0
  state.resume = value.resume === true
  return state
}

// ----- Live questions to the Researcher (ADR 0008): /api/ask, served by the same portal -----

export const LIVE_STATUS_PATH = "api/ask/status"
export const LIVE_ASK_PATH = "api/ask"
export const LIVE_QUESTION_MIN = 3
export const LIVE_QUESTION_MAX = 500
/** Delay between two polls of a running question. */
export const LIVE_POLL_MS = 2000
/** Live answers kept in the drawer for this page load. */
export const LIVE_KEEP = 5
/** Shown when the portal cannot be reached or answers in an unexpected way. */
export const LIVE_FAILED = "The live agent could not be reached. Please try again later."

const JOB_ID = /^[0-9a-f]{32}$/

/** `{"enabled": true}` of `GET /api/ask/status`; anything else means "no live ask". */
export function parseLiveStatus(payload: unknown): boolean {
  return isRecord(payload) && payload.enabled === true
}

/** The visitor's text as a question (trimmed, 3 to 500 characters), or what to tell them. */
export function liveQuestion(raw: string): { question: string } | { error: string } {
  const question = raw.trim()
  if (question.length < LIVE_QUESTION_MIN) return { error: "Please ask a complete question." }
  if (question.length > LIVE_QUESTION_MAX) {
    return { error: `Please keep the question under ${LIVE_QUESTION_MAX} characters.` }
  }
  return { question }
}

/** Job id of a `202` reply; throws on anything but 32 hexadecimal characters. */
export function parseJobId(payload: unknown): string {
  if (isRecord(payload) && typeof payload.job_id === "string" && JOB_ID.test(payload.job_id)) {
    return payload.job_id
  }
  throw new Error("the live ask did not return a job id")
}

/** Message of a refused request (`{"message": …}`), else a generic one: never raw server text. */
export function refusalMessage(payload: unknown): string {
  if (isRecord(payload) && typeof payload.message === "string" && payload.message.trim()) {
    return payload.message.trim().slice(0, 300)
  }
  return LIVE_FAILED
}

export type LivePoll =
  | { state: "running"; elapsed: number }
  | { state: "answer"; status: "done" | "unverified"; answer: AskAnswer }
  | { state: "failed"; status: "error" | "busy"; message: string }

/**
 * A poll reply of `GET /api/ask/{job_id}`. The reply is data: the answer goes through the same
 * parser as `answers.json`, is always marked live, and an `unverified` answer loses its citation
 * links whatever the server sent, with the portal's message as an extra note. Throws when the
 * reply is not of this shape.
 */
export function parseLivePoll(payload: unknown): LivePoll {
  if (!isRecord(payload)) throw new Error("the live ask returned an unexpected reply")
  const message = typeof payload.message === "string" ? payload.message.trim().slice(0, 300) : ""
  const elapsed =
    typeof payload.elapsed_s === "number" && payload.elapsed_s >= 0 ? payload.elapsed_s : 0
  switch (payload.status) {
    case "running":
      return { state: "running", elapsed }
    case "error":
    case "busy":
      return { state: "failed", status: payload.status, message: message || LIVE_FAILED }
    case "done":
    case "unverified": {
      const parsed = answer(payload.answer)
      if (!parsed) throw new Error("the live ask returned no answer")
      const verified = payload.status === "done"
      const paragraphs = verified
        ? parsed.paragraphs
        : parsed.paragraphs
            .map((paragraph) => paragraph.filter((segment) => segment.cite === undefined))
            .filter((paragraph) => paragraph.length > 0)
      const banners = !verified && message ? [...parsed.banners, message] : parsed.banners
      return {
        state: "answer",
        status: payload.status,
        answer: {
          ...parsed,
          paragraphs,
          banners,
          citations: verified ? parsed.citations : [],
          live: true,
        },
      }
    }
    default:
      throw new Error("the live ask returned an unknown status")
  }
}

/** "The Researcher is reading the wiki… 12 s" */
export function waitingLabel(elapsedSeconds: number): string {
  return `The Researcher is reading the wiki… ${Math.max(Math.floor(elapsedSeconds), 0)} s`
}
