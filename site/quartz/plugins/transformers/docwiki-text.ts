// Pure helpers of the DocWiki overlay (transformer, components and the "Ask this wiki" drawer).
// Unit-tested directly with Node (tests/site/test_overlay_text.py) and mirrored by
// docwiki.contracts.markdown and docwiki.site.answers in Python. Their only imports are the UI
// string tables (import-free modules): the words come in the page's language (`t`, English by
// default).
import { en } from "../../components/docwiki/i18n/en.ts"
import type { BadgeWords, Strings } from "../../components/docwiki/i18n/strings.ts"

/** The table passed in, else English (an `Array.map` callback gets an index there). */
function table(t: unknown): Strings {
  return typeof t === "object" && t !== null && "ask" in t ? (t as Strings) : en
}

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

/**
 * A badge as shown on a page in the language of `t`: the wiki's markers stay English in the
 * Markdown (`✓ quote verified`), the reader sees its words and meaning in the page's language.
 */
export function shownBadge(badge: Badge, t: Strings = en): Badge {
  const words = (table(t).badges.citation as Record<string, BadgeWords | undefined>)[badge.kind]
  return words ? { kind: badge.kind, text: words.text, meaning: words.meaning } : badge
}

/** The provenance badge of an evidence sidecar (`native-text`, `ocr`…) in the language of `t`. */
export function provenanceBadge(provenance: string, t: Strings = en): Badge | undefined {
  const badge = PROVENANCE_BADGES[provenance]
  const words = (table(t).badges.provenance as Record<string, BadgeWords | undefined>)[provenance]
  return badge && words ? { kind: badge.kind, text: words.text, meaning: words.meaning } : badge
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

export function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`
}

/** "37 documents (1 superseded)" for the home page's provenance line. */
export function documentsPhrase(current: number, superseded: number, t: Strings = en): string {
  return table(t).words.documentsPhrase(current, superseded)
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
export function qualityPhrase(quality: QualityCounts, t: Strings = en): string {
  return table(t).words.quality(quality)
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
export function groupAnswers(
  answers: readonly AskAnswer[],
  slug: string,
  t: Strings = en,
): AnswerGroup[] {
  const here = answers.filter((item) => item.pages.includes(slug))
  const more = answers.filter((item) => !item.pages.includes(slug))
  const groups: AnswerGroup[] = []
  if (here.length > 0) groups.push({ title: table(t).ask.aboutPage, answers: here })
  if (more.length > 0) {
    groups.push({ title: here.length > 0 ? table(t).ask.moreQuestions : table(t).ask.questions, answers: more })
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
export function stepsLabel(count: number, t: Strings = en): string {
  return table(t).ask.steps(count)
}

/**
 * The answer's provenance line: the note of "How this answer was produced" (its closing colon,
 * which introduces the tool steps on the page, becomes a full stop), else "Filed on <date>".
 */
export function provenanceLine(
  item: Pick<AskAnswer, "provenance" | "date">,
  t: Strings = en,
): string {
  const note = item.provenance.trim()
  if (note) return note.replace(/:$/, ".")
  return item.date ? table(t).ask.filedOn(item.date) : ""
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

/** Quartz's phone layout (its `mobile` breakpoint): the drawer is a bottom sheet (custom.scss). */
export const PHONE_QUERY = "(max-width: 800px)"

/**
 * The state to restore on a page load. On a phone the drawer never comes back open (a sheet over
 * the page that was just opened would hide it); the answer stays selected for the next opening.
 */
export function restoredState(state: AskState, phone: boolean): AskState {
  return phone && state.open ? { ...state, open: false } : state
}

/**
 * State after following a link of an answer (a citation, a source, the answer's page). On a narrow
 * screen the drawer collapses so that the page shows, keeping the answer to come back to; on wide
 * screens the drawer stays open beside the page.
 */
export function followLink(state: AskState, narrow: boolean, scroll: number): AskState {
  return narrow ? { ...state, open: false, resume: true, scroll } : { ...state, scroll }
}

/** Label of the floating button: "Back to the answer" after the drawer collapsed for a link. */
export function fabLabel(state: AskState, t: Strings = en): string {
  return state.resume && state.answer ? table(t).ask.backToAnswer : table(t).ask.title
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
export const LIVE_FAILED = en.ask.liveFailed

const JOB_ID = /^[0-9a-f]{32}$/

/** `{"enabled": true}` of `GET /api/ask/status`; anything else means "no live ask". */
export function parseLiveStatus(payload: unknown): boolean {
  return isRecord(payload) && payload.enabled === true
}

/** The visitor's text as a question (trimmed, 3 to 500 characters), or what to tell them. */
export function liveQuestion(
  raw: string,
  t: Strings = en,
): { question: string } | { error: string } {
  const question = raw.trim()
  if (question.length < LIVE_QUESTION_MIN) return { error: table(t).ask.tooShort }
  if (question.length > LIVE_QUESTION_MAX) return { error: table(t).ask.tooLong(LIVE_QUESTION_MAX) }
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
export function refusalMessage(payload: unknown, t: Strings = en): string {
  if (isRecord(payload) && typeof payload.message === "string" && payload.message.trim()) {
    return payload.message.trim().slice(0, 300)
  }
  return table(t).ask.liveFailed
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
export function parseLivePoll(payload: unknown, t: Strings = en): LivePoll {
  if (!isRecord(payload)) throw new Error("the live ask returned an unexpected reply")
  const message = typeof payload.message === "string" ? payload.message.trim().slice(0, 300) : ""
  const elapsed =
    typeof payload.elapsed_s === "number" && payload.elapsed_s >= 0 ? payload.elapsed_s : 0
  switch (payload.status) {
    case "running":
      return { state: "running", elapsed }
    case "error":
    case "busy":
      return { state: "failed", status: payload.status, message: message || table(t).ask.liveFailed }
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
export function waitingLabel(elapsedSeconds: number, t: Strings = en): string {
  return table(t).ask.waiting(Math.max(Math.floor(elapsedSeconds), 0))
}

// ----- Drawer details: numbering, examples, the last live answers -----

/**
 * The answer with its sources numbered 1..n in the order the answer first cites them, and the
 * inline markers renumbered to match. A marker citing a source the answer does not list is
 * numbered too (it stays unlinked); listed sources the text never cites follow, in their order.
 * Pure: the input is not changed.
 */
export function renumberCitations(item: AskAnswer): AskAnswer {
  const order = new Map<number, number>()
  const assign = (old: number) => {
    if (!order.has(old)) order.set(old, order.size + 1)
    return order.get(old) as number
  }
  const seen = new Set<number>()
  const listed = item.citations.filter((entry) => {
    if (seen.has(entry.n)) return false
    seen.add(entry.n)
    return true
  })
  // Listed sources first (cited ones in order of appearance), so the list has no gaps.
  for (const paragraph of item.paragraphs) {
    for (const segment of paragraph) {
      if (segment.cite !== undefined && seen.has(segment.cite)) assign(segment.cite)
    }
  }
  for (const entry of listed) assign(entry.n)
  const paragraphs = item.paragraphs.map((paragraph) =>
    paragraph.map((segment) =>
      segment.cite !== undefined ? { cite: assign(segment.cite) } : { ...segment },
    ),
  )
  const citations = listed
    .map((entry) => ({ ...entry, n: order.get(entry.n) as number }))
    .sort((a, b) => a.n - b.n)
  return { ...item, paragraphs, citations }
}

/** Opening of the notice every live answer carries (the portal's `LIVE_BANNER`). */
export function isLiveNotice(banner: string): boolean {
  return banner.startsWith("Live answer from the Researcher agent")
}

/** Questions the sample corpus answers, offered when the drawer has no answer to show. */
export const EXAMPLE_QUESTIONS: readonly string[] = en.ask.examples

function sameQuestion(a: string, b: string): boolean {
  const clean = (text: string) => text.trim().replace(/\s+/g, " ").toLowerCase()
  return clean(a) === clean(b)
}

/** The filed answer to exactly this question, if the build has one. */
export function filedAnswerFor(
  answers: readonly AskAnswer[],
  question: string,
): AskAnswer | undefined {
  return answers.find((item) => !item.live && sameQuestion(item.question, question))
}

/**
 * The examples to offer: all of them when the portal answers live questions, else those that have
 * a filed answer in this build.
 */
export function exampleQuestions(
  answers: readonly AskAnswer[] | null,
  live: boolean,
  examples: readonly string[] = EXAMPLE_QUESTIONS,
): string[] {
  if (live) return [...examples]
  return examples.filter((question) => filedAnswerFor(answers ?? [], question))
}

/** sessionStorage key of the live answers of the session (they survive page navigation). */
export const LIVE_STORE_KEY = "docwiki-ask-live"

/**
 * Live answers read back from sessionStorage: the same validation as the live JSON, always marked
 * live, at most `LIVE_KEEP` of them, oldest first. Anything of the wrong shape is dropped.
 */
export function parseStoredLive(raw: string | null | undefined): AskAnswer[] {
  if (!raw) return []
  let value: unknown
  try {
    value = JSON.parse(raw)
  } catch {
    return []
  }
  if (!Array.isArray(value)) return []
  const kept = value
    .map(answer)
    .filter((item): item is AskAnswer => item !== undefined)
    .map((item) => ({ ...item, live: true }))
  return kept.slice(-LIVE_KEEP)
}

// ----- The story home (Story.tsx, ADR 0010): the three cards and the question to try -----

/**
 * Page-level hook of the "Ask this wiki" drawer: any part of a page opens the drawer on a question
 * with `document.dispatchEvent(new CustomEvent(ASK_EVENT, { detail: { question } }))`. The drawer
 * treats it like its own example buttons: asked live when the agent is enabled, else the filed
 * answer to that question is opened (the question list when there is none). The event is ignored
 * while the drawer has nothing to show (its button is hidden) or is not on the page.
 */
export const ASK_EVENT = "docwiki:ask"

/** The question of an `ASK_EVENT` detail (`{ question }`), whitespace collapsed, or `null`. */
export function askEventQuestion(detail: unknown): string | null {
  const value = record(detail)?.question
  if (typeof value !== "string") return null
  const question = value.trim().replace(/\s+/g, " ")
  return question.length > 0 && question.length <= LIVE_QUESTION_MAX ? question : null
}

/** "42 s", "4 min", "1 h 5 min": a run's length on the story strip, in whole units. */
export function shortDuration(seconds: number): string | null {
  if (!Number.isFinite(seconds) || seconds < 0) return null
  if (seconds < 59.5) return `${Math.max(1, Math.round(seconds))} s`
  const minutes = Math.round(seconds / 60)
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  return minutes % 60 === 0 ? `${hours} h` : `${hours} h ${minutes % 60} min`
}

/** "$1.37": cost receipts are in USD (a missing currency reads as USD); else "EUR 1.37". */
export function money(total: number, currency: string | null, t: Strings = en): string | null {
  if (!Number.isFinite(total) || total < 0) return null
  return table(t).words.money(total, currency)
}

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function finite(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null
}

/**
 * The pipeline card's live line from the portal's `GET /api/process`: the length and cost of the
 * run that built the published release (the first `runs` entry with `is_current`), as
 * "last run 4 min · $1.37". `null` when the reply has no such run or says neither, so the card
 * keeps its build-time text. The reply is data: only numbers, dates and a currency code are read.
 */
export function lastRunLine(payload: unknown, t: Strings = en): string | null {
  const runs = record(payload)?.runs
  const run = (Array.isArray(runs) ? runs : [])
    .map(record)
    .find((item) => item !== null && item.is_current === true)
  if (!run) return null
  const cost = record(run.cost) ?? {}
  const { started_at: started, finished_at: finished } = run
  let seconds = finite(cost.duration_s)
  if (seconds === null && typeof started === "string" && typeof finished === "string") {
    seconds = finite((Date.parse(finished) - Date.parse(started)) / 1000)
  }
  const code = cost.currency
  const currency = typeof code === "string" && /^[A-Z]{3}$/.test(code) ? code : null
  const total = finite(cost.total)
  const parts = [
    seconds === null ? null : shortDuration(seconds),
    total === null ? null : money(total, currency, t),
  ].filter((part): part is string => part !== null)
  return parts.length > 0 ? table(t).words.lastRun(parts.join(" · ")) : null
}
