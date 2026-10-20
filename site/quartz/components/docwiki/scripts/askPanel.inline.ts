// Client of the "Ask this wiki" drawer (AskPanel.tsx, ADR 0007).
//
// Quartz's page navigation morphs the whole body on every internal link, so the drawer is rebuilt
// on each `nav` event from sessionStorage (open, selected answer, scroll) and from answers.json,
// fetched once per page load. Answers are data: they are rendered with DOM nodes and textContent
// only, and their links are content slugs made relative to the current page.
import type { AskAnswer, AskCitation, AskState } from "../../../plugins/transformers/docwiki-text"
import {
  ASK_STATE_KEY,
  NARROW_QUERY,
  badgeForText,
  citationText,
  fabLabel,
  followLink,
  groupAnswers,
  parseAnswers,
  parseAskState,
  provenanceLine,
  relativeHref,
  stepsLabel,
} from "../../../plugins/transformers/docwiki-text"

const PANEL_ID = "docwiki-ask"
const ANSWERS_PATH = "static/docwiki/answers.json"
const SVG_NS = "http://www.w3.org/2000/svg"
/** Quartz overlays that close on Escape themselves (search, global graph). */
const OVERLAYS = ".search-container.active, .global-graph-outer.active"

let answers: AskAnswer[] | null = null
let loading: Promise<AskAnswer[]> | null = null
let failed = false
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
    "Answers by the Researcher agent, reviewed before publishing",
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
  const foot = element("p", "docwiki-ask-footer", "To ask your own questions, ")
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

function questionList(body: HTMLElement, list: readonly AskAnswer[], slug: string) {
  const groups = groupAnswers(list, slug)
  if (groups.length === 0) {
    body.append(element("p", "docwiki-ask-status", "No answers have been filed yet."))
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

function citeMark(
  n: number,
  entry: AskCitation | undefined,
  slug: string,
  focusKey: string,
): HTMLElement {
  const mark = element("sup", "docwiki-ask-cite")
  if (!entry) {
    mark.textContent = String(n)
    return mark
  }
  const anchor = link(slug, entry.href, String(n), focusKey)
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

function answerView(body: HTMLElement, item: AskAnswer, slug: string) {
  const back = button("docwiki-ask-back", "Back to questions", "back")
  back.dataset.askAction = "back"
  const article = element("article", "docwiki-ask-answer")
  const question = element("h3", "docwiki-ask-question-title", item.question)
  question.tabIndex = -1
  question.dataset.focusKey = "answer"
  article.append(question)
  for (const banner of item.banners) {
    const note = element("p", "docwiki-ask-banner", banner)
    note.setAttribute("role", "note")
    article.append(note)
  }
  const byNumber = new Map(item.citations.map((entry) => [entry.n, entry]))
  const text = element("div", "docwiki-ask-text")
  let marks = 0
  for (const paragraph of item.paragraphs) {
    const block = element("p")
    for (const segment of paragraph) {
      if (segment.text !== undefined) {
        block.append(segment.text)
      } else if (segment.cite !== undefined) {
        const entry = byNumber.get(segment.cite)
        block.append(citeMark(segment.cite, entry, slug, `cite:${marks++}`))
      }
    }
    text.append(block)
  }
  article.append(text)
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
  const open = element("p", "docwiki-ask-open")
  open.append(link(slug, item.slug, "Open as a page", "page"))
  meta.append(open)
  article.append(meta)
  body.append(back, article)
}

function fill(body: HTMLElement, state: AskState) {
  body.replaceChildren()
  body.removeAttribute("aria-busy")
  const slug = currentSlug()
  if (answers) {
    const selected = state.answer ? answers.find((item) => item.id === state.answer) : undefined
    if (selected) answerView(body, selected, slug)
    else questionList(body, answers, slug)
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
  const control = target.closest<HTMLElement>("[data-ask-action], [data-ask-answer]")
  if (!control) return
  const action = control.dataset.askAction
  if (action === "close") {
    close()
  } else if (action === "back") {
    back()
  } else if (action === "retry") {
    failed = false
    paint("title")
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
  const state = readState()
  if (state.open) paint(focusKey)
  else syncFab(fab, state)
})
