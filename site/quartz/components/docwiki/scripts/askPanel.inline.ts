// Client of the "Ask this wiki" drawer (AskPanel.tsx, ADR 0007).
//
// Quartz's page navigation morphs the whole body on every internal link, so the drawer is rebuilt
// on each `nav` event from sessionStorage (open, selected answer, scroll) and from answers.json,
// fetched once per page load. Answers are data: they are rendered with DOM nodes and textContent
// only, and their links are content slugs made relative to the current page.
import type { AskAnswer, AskCitation, AskState } from "../../../plugins/transformers/docwiki-text"
import {
  ASK_STATE_KEY,
  LIVE_ASK_PATH,
  LIVE_FAILED,
  LIVE_KEEP,
  LIVE_POLL_MS,
  LIVE_QUESTION_MAX,
  LIVE_STATUS_PATH,
  LIVE_STORE_KEY,
  NARROW_QUERY,
  PHONE_QUERY,
  badgeForText,
  citationText,
  exampleQuestions,
  fabLabel,
  filedAnswerFor,
  followLink,
  groupAnswers,
  isLiveNotice,
  liveQuestion,
  parseAnswers,
  parseAskState,
  parseJobId,
  parseLivePoll,
  parseLiveStatus,
  parseStoredLive,
  provenanceLine,
  refusalMessage,
  relativeHref,
  renumberCitations,
  restoredState,
  stepsLabel,
  waitingLabel,
} from "../../../plugins/transformers/docwiki-text"

const PANEL_ID = "docwiki-ask"
const INPUT_ID = "docwiki-ask-input"
const HINT_ID = "docwiki-ask-hint"
const ANSWERS_PATH = "static/docwiki/answers.json"
const SVG_NS = "http://www.w3.org/2000/svg"
/** Quartz overlays that close on Escape themselves (search, global graph). */
const OVERLAYS = ".search-container.active, .global-graph-outer.active"

let answers: AskAnswer[] | null = null
let loading: Promise<AskAnswer[]> | null = null
let failed = false
/** Filed answers of this build (`data-filed-answers`); a build without any has no answers.json. */
let filedCount = 0
/** Source id → [page slug, title] of this build (`data-source-pages`). */
let sourcePages: Record<string, [string, string]> = {}
/** Whether the portal answers live questions (`/api/ask/status`); `null` until it is known. */
let liveEnabled: boolean | null = null
let liveChecking: Promise<void> | null = null

interface LiveRun {
  question: string
  started: number
  /** `null` until the portal accepted the question. */
  jobId: string | null
  timer: number
  /** Polls that failed in a row. */
  failures: number
}

/** The question in flight (module state: the drawer is rebuilt on every page navigation). */
let liveRun: LiveRun | null = null
/** Why the last live question did not produce an answer, or what is wrong with the text. */
let liveMessage: string | null = null
let liveDraft = ""
/** Live answers of this session, oldest first: kept in sessionStorage across page navigation. */
const liveAnswers = new Map<string, AskAnswer>(
  (() => {
    try {
      return parseStoredLive(sessionStorage.getItem(LIVE_STORE_KEY))
    } catch {
      return []
    }
  })().map((item): [string, AskAnswer] => [item.id, item]),
)

function storeLive() {
  try {
    sessionStorage.setItem(LIVE_STORE_KEY, JSON.stringify(Array.from(liveAnswers.values())))
  } catch {
    // Storage disabled or full: the answers last until the next full page load.
  }
}
let memoryState: AskState = parseAskState(null)
/** Focus to restore in the rebuilt drawer after a page navigation started from inside it. */
let pendingFocus: string | null = null
/** Link followed from a collapsed drawer, focused again by "Back to the answer". */
let resumeFocus: string | null = null
/** Scroll position of the question list, restored by "Back to questions". */
let listScroll = 0
let scrollFrame = 0

function readState(): AskState {
  try {
    const raw = sessionStorage.getItem(ASK_STATE_KEY)
    return raw === null ? { ...memoryState } : parseAskState(raw)
  } catch {
    return { ...memoryState }
  }
}

function writeState(state: AskState) {
  memoryState = { ...state }
  try {
    sessionStorage.setItem(ASK_STATE_KEY, JSON.stringify(state))
  } catch {
    // Storage disabled: the state lasts until the next full page load.
  }
}

function currentSlug(): string {
  return document.body.dataset.slug ?? "index"
}

function loadAnswers(slug: string): Promise<AskAnswer[]> {
  if (answers) return Promise.resolve(answers)
  if (!loading) {
    loading = fetch(relativeHref(slug, ANSWERS_PATH), { credentials: "same-origin" })
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        return response.json() as Promise<unknown>
      })
      .then((payload) => {
        answers = parseAnswers(payload)
        return answers
      })
      .finally(() => {
        loading = null
      })
  }
  return loading
}

/** Asks the portal once per page load whether it answers live questions; failures mean "no". */
function checkLive(slug: string): Promise<void> {
  if (liveEnabled !== null) return Promise.resolve()
  if (!liveChecking) {
    liveChecking = fetch(relativeHref(slug, LIVE_STATUS_PATH), { credentials: "same-origin" })
      .then((response) => (response.ok ? (response.json() as Promise<unknown>) : null))
      .then(parseLiveStatus)
      .catch(() => false)
      .then((enabled) => {
        liveEnabled = enabled
      })
      .finally(() => {
        liveChecking = null
      })
  }
  return liveChecking
}

function findAnswer(id: string): AskAnswer | undefined {
  return liveAnswers.get(id) ?? answers?.find((item) => item.id === id)
}

function element<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  text?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag)
  if (className) node.className = className
  if (text !== undefined) node.textContent = text
  return node
}

function icon(...paths: string[]): SVGSVGElement {
  const svg = document.createElementNS(SVG_NS, "svg")
  svg.setAttribute("viewBox", "0 0 24 24")
  svg.setAttribute("aria-hidden", "true")
  svg.setAttribute("focusable", "false")
  for (const d of paths) {
    const path = document.createElementNS(SVG_NS, "path")
    path.setAttribute("d", d)
    svg.append(path)
  }
  return svg
}

function button(className: string, text: string, focusKey: string): HTMLButtonElement {
  const node = element("button", className, text)
  node.type = "button"
  node.dataset.focusKey = focusKey
  return node
}

function link(slug: string, target: string, text: string, focusKey: string): HTMLAnchorElement {
  const node = element("a", undefined, text)
  node.setAttribute("href", relativeHref(slug, target))
  node.dataset.focusKey = focusKey
  node.dataset.askLink = ""
  return node
}

function header(): HTMLElement {
  const head = element("div", "docwiki-ask-header")
  const titles = element("div", "docwiki-ask-titles")
  const title = element("h2", "docwiki-ask-title", "Ask this wiki")
  title.tabIndex = -1
  title.dataset.focusKey = "title"
  const subtitle = element(
    "p",
    "docwiki-ask-subtitle",
    liveEnabled
      ? "Ask the Researcher agent. Its citations are checked before they are shown."
      : "Answers by the Researcher agent, reviewed before publishing",
  )
  titles.append(title, subtitle)
  const close = button("docwiki-ask-close", "", "close")
  close.dataset.askAction = "close"
  close.setAttribute("aria-label", "Close Ask this wiki")
  close.title = "Close (Esc)"
  close.append(icon("M6 6l12 12", "M18 6L6 18"))
  head.append(titles, close)
  return head
}

function footer(repoUrl: string | undefined): HTMLElement {
  const foot = element("p", "docwiki-ask-footer", "You can also ")
  const text = "connect your coding agent to this wiki (MCP)"
  if (repoUrl && /^https?:\/\//.test(repoUrl)) {
    const anchor = element("a", undefined, text)
    anchor.setAttribute("href", repoUrl)
    anchor.dataset.focusKey = "repo"
    foot.append(anchor, ".")
  } else {
    foot.append(`${text}.`)
  }
  return foot
}

/** Example questions of the sample corpus, shown while no live answer of the session exists. */
function examples(body: HTMLElement, list: readonly AskAnswer[]) {
  if (liveAnswers.size > 0) return
  const questions = exampleQuestions(list, liveEnabled === true)
  if (questions.length === 0) return
  const section = element("section", "docwiki-ask-group docwiki-ask-examples")
  const items = element("ul", "docwiki-ask-questions")
  questions.forEach((question, index) => {
    const choice = button("docwiki-ask-question", question, `example:${index}`)
    choice.dataset.askExample = question
    const entry = element("li")
    entry.append(choice)
    items.append(entry)
  })
  section.append(element("h3", "docwiki-ask-group-title", "Try one of these"), items)
  body.append(section)
}

function questionList(body: HTMLElement, list: readonly AskAnswer[], slug: string) {
  examples(body, list)
  const groups = groupAnswers(list, slug)
  const live = Array.from(liveAnswers.values()).reverse()
  if (live.length > 0) groups.unshift({ title: "Your live questions", answers: live })
  if (groups.length === 0) {
    if (!liveEnabled) {
      body.append(element("p", "docwiki-ask-status", "No answers have been filed yet."))
    }
    return
  }
  for (const group of groups) {
    const section = element("section", "docwiki-ask-group")
    const items = element("ul", "docwiki-ask-questions")
    for (const item of group.answers) {
      const choice = button("docwiki-ask-question", item.question, `question:${item.id}`)
      choice.dataset.askAnswer = item.id
      const entry = element("li")
      entry.append(choice)
      items.append(entry)
    }
    section.append(element("h3", "docwiki-ask-group-title", group.title), items)
    body.append(section)
  }
}

/** The Ask form above the question list: a labelled textarea, a button and a status line. */
function liveForm(body: HTMLElement) {
  const form = element("form", "docwiki-ask-form")
  form.noValidate = true
  const label = element("label", "docwiki-ask-form-label", "Ask the Researcher")
  label.htmlFor = INPUT_ID
  const input = element("textarea", "docwiki-ask-input")
  input.id = INPUT_ID
  input.rows = 3
  input.maxLength = LIVE_QUESTION_MAX
  input.value = liveDraft
  input.disabled = liveRun !== null
  input.dataset.focusKey = "ask-input"
  input.setAttribute("aria-describedby", HINT_ID)
  input.addEventListener("input", () => {
    liveDraft = input.value
  })
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
      event.preventDefault()
      form.requestSubmit()
    }
  })
  const submit = button("docwiki-ask-submit", "Ask", "ask-submit")
  submit.type = "submit"
  submit.disabled = liveRun !== null
  const status = element("p", "docwiki-ask-live-status")
  status.setAttribute("role", "status")
  status.setAttribute("aria-live", "polite")
  status.tabIndex = -1
  status.dataset.focusKey = "live-status"
  if (liveRun) status.textContent = waitingLabel((Date.now() - liveRun.started) / 1000)
  form.append(label, input, submit, status)
  if (liveMessage) {
    const problem = element("p", "docwiki-ask-live-error", liveMessage)
    problem.setAttribute("role", "alert")
    form.append(problem)
  }
  const hint = element(
    "p",
    "docwiki-ask-hint",
    "Live answers are checked against the sources before they are shown. " +
      "The owner has not reviewed them.",
  )
  hint.id = HINT_ID
  form.append(hint)
  form.addEventListener("submit", (event) => {
    event.preventDefault()
    void startLive()
  })
  body.append(form)
}

/** An example question: asked live when the agent is enabled, else its filed answer is opened. */
function useExample(question: string) {
  if (liveEnabled) {
    liveDraft = question
    void startLive()
    return
  }
  const filed = answers ? filedAnswerFor(answers, question) : undefined
  if (filed) select(filed.id)
}

function waiting() {
  const status = document.querySelector<HTMLElement>(`#${PANEL_ID} .docwiki-ask-live-status`)
  if (status && liveRun) status.textContent = waitingLabel((Date.now() - liveRun.started) / 1000)
}

type LiveOutcome = { answer: AskAnswer } | { message: string }

/** The question is over: show its answer, or why there is none (the filed list stays). */
function endLive(run: LiveRun, outcome: LiveOutcome) {
  if (liveRun !== run) return
  window.clearTimeout(run.timer)
  liveRun = null
  if ("answer" in outcome) {
    const item = outcome.answer
    liveAnswers.set(item.id, item)
    while (liveAnswers.size > LIVE_KEEP) {
      const oldest = liveAnswers.keys().next()
      if (oldest.done) break
      liveAnswers.delete(oldest.value)
    }
    storeLive()
    liveDraft = ""
    liveMessage = null
    const state = readState()
    // Not while the visitor reads another answer: it stays in "Your live questions".
    if (!state.open) update({ answer: item.id, scroll: 0 }, null)
    else if (state.answer === null) update({ answer: item.id, scroll: 0 }, "answer")
    else paint(null)
  } else {
    liveMessage = outcome.message
    paint("ask-input")
  }
}

async function pollLive(run: LiveRun) {
  if (liveRun !== run || run.jobId === null) return
  try {
    const target = relativeHref(currentSlug(), `${LIVE_ASK_PATH}/${run.jobId}`)
    const response = await fetch(target, { credentials: "same-origin", cache: "no-store" })
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const result = parseLivePoll(await response.json())
    run.failures = 0
    if (result.state === "running") {
      waiting()
      run.timer = window.setTimeout(() => void pollLive(run), LIVE_POLL_MS)
    } else if (result.state === "answer") {
      endLive(run, { answer: result.answer })
    } else {
      endLive(run, { message: result.message })
    }
  } catch (error) {
    console.error("DocWiki: the live answer could not be read", error)
    run.failures += 1
    if (run.failures >= 3) endLive(run, { message: LIVE_FAILED })
    else run.timer = window.setTimeout(() => void pollLive(run), LIVE_POLL_MS)
  }
}

async function startLive() {
  if (liveRun) return
  const checked = liveQuestion(liveDraft)
  if ("error" in checked) {
    liveMessage = checked.error
    paint("ask-input")
    return
  }
  liveMessage = null
  const run: LiveRun = {
    question: checked.question,
    started: Date.now(),
    jobId: null,
    timer: 0,
    failures: 0,
  }
  liveRun = run
  paint("live-status")
  try {
    const response = await fetch(relativeHref(currentSlug(), LIVE_ASK_PATH), {
      method: "POST",
      headers: { "content-type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ question: run.question }),
    })
    const payload = await response.json().catch((): unknown => null)
    if (!response.ok) {
      endLive(run, { message: refusalMessage(payload) })
      return
    }
    run.jobId = parseJobId(payload)
  } catch (error) {
    console.error("DocWiki: the question could not be sent", error)
    endLive(run, { message: LIVE_FAILED })
    return
  }
  run.timer = window.setTimeout(() => void pollLive(run), LIVE_POLL_MS)
}

function citeMark(
  n: number,
  entry: AskCitation | undefined,
  slug: string,
  focusKey: string,
): HTMLElement {
  const mark = element("sup", "docwiki-ask-cite")
  if (!entry) {
    mark.textContent = `[${n}]`
    return mark
  }
  const anchor = link(slug, entry.href, `[${n}]`, focusKey)
  const label = `Source ${n}: ${entry.title} — ${entry.label}`
  anchor.setAttribute("aria-label", label)
  anchor.title = label
  mark.append(anchor)
  return mark
}

function sourceItem(entry: AskCitation, slug: string): HTMLLIElement {
  const item = element("li")
  item.append(link(slug, entry.href, citationText(entry), `source:${entry.n}`))
  if (entry.badge) {
    const badge = badgeForText(entry.badge)
    const chip = element(
      "span",
      badge ? `docwiki-badge docwiki-badge--${badge.kind}` : "docwiki-badge",
      entry.badge,
    )
    if (badge) chip.title = badge.meaning
    item.append(" ", chip)
  }
  return item
}

/**
 * The wiki pages of the sources an answer cites (citation hrefs are `evidence/<source_id>/...`),
 * once each and in citation order: the reader goes on from the answer into the wiki.
 */
function wikiPages(item: AskAnswer): [string, string][] {
  const pages = new Map<string, string>()
  for (const entry of item.citations) {
    const [root, sourceId] = entry.href.split("/")
    const found = root === "evidence" ? sourcePages[sourceId] : undefined
    if (found && typeof found[0] === "string" && !pages.has(found[0])) {
      pages.set(found[0], String(found[1]))
    }
  }
  return Array.from(pages.entries())
}

function answerView(body: HTMLElement, answer: AskAnswer, slug: string) {
  // Sources are numbered in the order the answer first cites them.
  const item = renumberCitations(answer)
  const back = button("docwiki-ask-back", "Back to questions", "back")
  back.dataset.askAction = "back"
  const article = element("article", "docwiki-ask-answer")
  const question = element("h3", "docwiki-ask-question-title", item.question)
  question.tabIndex = -1
  question.dataset.focusKey = "answer"
  article.append(question)
  for (const banner of item.banners) {
    const note = element(
      "p",
      item.live && isLiveNotice(banner)
        ? "docwiki-ask-banner docwiki-ask-banner--live"
        : "docwiki-ask-banner",
      banner,
    )
    note.setAttribute("role", "note")
    article.append(note)
  }
  const byNumber = new Map(item.citations.map((entry) => [entry.n, entry]))
  const text = element("div", "docwiki-ask-text")
  let marks = 0
  for (const paragraph of item.paragraphs) {
    const block = element("p")
    let previousCite = false
    for (const segment of paragraph) {
      if (segment.text !== undefined) {
        block.append(segment.text)
        previousCite = false
      } else if (segment.cite !== undefined) {
        // Neighbouring markers read as "[1] [3]", never "13".
        if (previousCite) block.append(" ")
        previousCite = true
        const entry = byNumber.get(segment.cite)
        block.append(citeMark(segment.cite, entry, slug, `cite:${marks++}`))
      }
    }
    text.append(block)
  }
  article.append(text)
  const pages = wikiPages(item)
  if (pages.length > 0) {
    article.append(element("h4", "docwiki-ask-sources-title", "Pages in the wiki"))
    const list = element("ul", "docwiki-ask-sources docwiki-ask-pages")
    for (const [page, title] of pages) {
      const entry = element("li")
      entry.append(link(slug, page, title, `page:${page}`))
      list.append(entry)
    }
    article.append(list)
  }
  if (item.citations.length > 0) {
    article.append(element("h4", "docwiki-ask-sources-title", "Sources"))
    const sources = element("ul", "docwiki-ask-sources")
    for (const entry of item.citations) sources.append(sourceItem(entry, slug))
    article.append(sources)
  }
  if (item.steps.length > 0) {
    const details = element("details", "docwiki-ask-steps")
    const summary = element("summary", undefined, stepsLabel(item.steps.length))
    summary.dataset.focusKey = "steps"
    const steps = element("ol")
    for (const step of item.steps) steps.append(element("li", undefined, step))
    details.append(summary, steps)
    article.append(details)
  }
  const meta = element("div", "docwiki-ask-meta")
  const line = provenanceLine(item)
  if (line) meta.append(element("p", "docwiki-ask-provenance", line))
  if (!item.live) {
    const open = element("p", "docwiki-ask-open")
    open.append(link(slug, item.slug, "Open as a page", "page"))
    meta.append(open)
  }
  article.append(meta)
  body.append(back, article)
}

function fill(body: HTMLElement, state: AskState) {
  body.replaceChildren()
  body.removeAttribute("aria-busy")
  const slug = currentSlug()
  const selected = state.answer ? findAnswer(state.answer) : undefined
  if (selected) {
    answerView(body, selected, slug)
    body.scrollTop = state.scroll
    return
  }
  if (liveEnabled) liveForm(body)
  // A build without filed answers has no answers.json: only the live questions are left.
  if (answers || filedCount === 0) {
    questionList(body, answers ?? [], slug)
    body.scrollTop = state.scroll
    return
  }
  if (failed) {
    const message = element("p", "docwiki-ask-status", "The answers could not be loaded.")
    message.setAttribute("role", "alert")
    const retry = button("docwiki-ask-retry", "Try again", "retry")
    retry.dataset.askAction = "retry"
    body.append(message, retry)
    return
  }
  body.setAttribute("aria-busy", "true")
  const status = element("p", "docwiki-ask-status", "Loading answers…")
  status.setAttribute("role", "status")
  body.append(status)
  loadAnswers(slug).then(
    () => {
      if (body.isConnected) fill(body, readState())
    },
    (error: unknown) => {
      console.error("DocWiki: the answers could not be loaded", error)
      failed = true
      if (body.isConnected) fill(body, readState())
    },
  )
}

function elements(): { fab: HTMLButtonElement; panel: HTMLElement } | null {
  const panel = document.getElementById(PANEL_ID)
  const fab = document.querySelector<HTMLButtonElement>(".docwiki-ask-fab")
  return panel && fab ? { fab, panel } : null
}

function focusOn(panel: HTMLElement, key: string) {
  const targets = Array.from(panel.querySelectorAll<HTMLElement>("[data-focus-key]"))
  const target =
    targets.find((node) => node.dataset.focusKey === key) ??
    panel.querySelector<HTMLElement>(".docwiki-ask-title")
  target?.focus()
}

/** The floating button's state and label ("Back to the answer" after the drawer collapsed). */
function syncFab(fab: HTMLButtonElement, state: AskState) {
  fab.setAttribute("aria-expanded", state.open ? "true" : "false")
  const label = fab.querySelector(".docwiki-ask-fab-label")
  if (label) label.textContent = fabLabel(state)
}

/** Show the drawer as the stored state says, then move the focus to `focusKey` (if any). */
function paint(focusKey: string | null) {
  const found = elements()
  if (!found) return
  const { fab, panel } = found
  const state = readState()
  syncFab(fab, state)
  if (!state.open) {
    panel.hidden = true
    panel.replaceChildren()
    return
  }
  const body = element("div", "docwiki-ask-body")
  panel.replaceChildren(header(), body, footer(panel.dataset.repoUrl))
  panel.hidden = false
  fill(body, state)
  if (focusKey) focusOn(panel, focusKey)
}

function update(change: Partial<AskState>, focusKey: string | null) {
  writeState({ ...readState(), ...change })
  paint(focusKey)
}

function close() {
  update({ open: false, resume: false }, null)
  elements()?.fab.focus()
}

function select(id: string) {
  const body = document.querySelector<HTMLElement>(`#${PANEL_ID} .docwiki-ask-body`)
  listScroll = body ? body.scrollTop : 0
  update({ answer: id, scroll: 0 }, "answer")
}

function back() {
  const previous = readState().answer
  update({ answer: null, scroll: listScroll }, previous ? `question:${previous}` : "title")
}

function onFabClick() {
  const focusKey = readState().resume && resumeFocus ? resumeFocus : "title"
  resumeFocus = null
  update({ open: true, resume: false }, focusKey)
}

/**
 * A link of the answer was followed (Quartz's router opens its page). Below the desktop breakpoint
 * the drawer would hide that page: the state says "collapsed" and the next `nav` leaves the drawer
 * closed, with "Back to the answer" on the button. Wide screens keep the drawer open beside the
 * page.
 */
function onLinkFollowed(followed: HTMLElement, event: MouseEvent) {
  if (event.button !== 0 || event.ctrlKey || event.metaKey) return // a new tab: nothing changes
  const body = document.querySelector<HTMLElement>(`#${PANEL_ID} .docwiki-ask-body`)
  const narrow = window.matchMedia(NARROW_QUERY).matches
  writeState(followLink(readState(), narrow, body ? Math.round(body.scrollTop) : 0))
  resumeFocus = narrow ? (followed.dataset.focusKey ?? null) : null
}

function onPanelClick(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof Element)) return
  const followed = target.closest<HTMLElement>("a[data-ask-link]")
  if (followed) {
    onLinkFollowed(followed, event)
    return
  }
  const control = target.closest<HTMLElement>(
    "[data-ask-action], [data-ask-answer], [data-ask-example]",
  )
  if (!control) return
  const action = control.dataset.askAction
  if (action === "close") {
    close()
  } else if (action === "back") {
    back()
  } else if (action === "retry") {
    failed = false
    paint("title")
  } else if (control.dataset.askExample) {
    useExample(control.dataset.askExample)
  } else if (control.dataset.askAnswer) {
    select(control.dataset.askAnswer)
  }
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== "Escape" && event.key !== "Esc") return
  const found = elements()
  if (!found || found.panel.hidden || document.querySelector(OVERLAYS)) return
  const active = document.activeElement
  const inPanel = active !== null && found.panel.contains(active)
  const nowhere = active === null || active === document.body || active === document.documentElement
  if (!inPanel && !nowhere) return
  // Captured before Quartz's own Escape handlers, which would move the focus to the search button.
  event.preventDefault()
  event.stopPropagation()
  close()
}

function onPanelScroll(event: Event) {
  const target = event.target
  if (!(target instanceof HTMLElement) || !target.classList.contains("docwiki-ask-body")) return
  if (scrollFrame) return
  scrollFrame = requestAnimationFrame(() => {
    scrollFrame = 0
    if (target.isConnected) writeState({ ...readState(), scroll: Math.round(target.scrollTop) })
  })
}

function onPrenav() {
  const found = elements()
  if (!found || found.panel.hidden) return
  const body = found.panel.querySelector<HTMLElement>(".docwiki-ask-body")
  if (body) writeState({ ...readState(), scroll: Math.round(body.scrollTop) })
  const active = document.activeElement
  pendingFocus =
    active instanceof HTMLElement && found.panel.contains(active)
      ? (active.dataset.focusKey ?? null)
      : null
}

document.addEventListener("nav", () => {
  const focusKey = pendingFocus
  pendingFocus = null
  const found = elements()
  if (!found) return
  const { fab, panel } = found
  filedCount = Number(panel.dataset.filedAnswers) || 0
  try {
    const parsed: unknown = JSON.parse(panel.dataset.sourcePages || "{}")
    sourcePages =
      parsed && typeof parsed === "object" ? (parsed as Record<string, [string, string]>) : {}
  } catch {
    sourcePages = {}
  }
  fab.addEventListener("click", onFabClick)
  panel.addEventListener("click", onPanelClick)
  panel.addEventListener("scroll", onPanelScroll, { capture: true, passive: true })
  document.addEventListener("keydown", onKeydown, true)
  document.addEventListener("prenav", onPrenav)
  window.addCleanup(() => {
    fab.removeEventListener("click", onFabClick)
    panel.removeEventListener("click", onPanelClick)
    panel.removeEventListener("scroll", onPanelScroll, { capture: true })
    document.removeEventListener("keydown", onKeydown, true)
    document.removeEventListener("prenav", onPrenav)
  })
  // The button shows when there are filed answers or a live agent; the portal says which (a
  // static host has no /api/ask/status, so a build without answers shows nothing there).
  const known = liveEnabled !== null
  const apply = () => {
    fab.hidden = filedCount === 0 && liveEnabled !== true
    syncFab(fab, readState())
  }
  // The drawer is a bottom sheet on phones: a page never starts with it open.
  const stored = readState()
  const restored = restoredState(stored, window.matchMedia(PHONE_QUERY).matches)
  if (restored !== stored) writeState(restored)
  apply()
  if (restored.open && !fab.hidden) paint(focusKey)
  if (!known) {
    void checkLive(currentSlug()).then(() => {
      if (!fab.isConnected) return // another page replaced this one meanwhile
      apply()
      if (liveEnabled && !fab.hidden && readState().open) {
        // The form joins a drawer that is already open: keep the focus where it was.
        const active = document.activeElement
        const inPanel = active instanceof HTMLElement && panel.contains(active)
        paint(inPanel ? (active.dataset.focusKey ?? null) : null)
      }
    })
  }
})
