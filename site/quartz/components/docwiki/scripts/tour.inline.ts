// Client of the guided tour (Tour.tsx, site.md §12.2): six steps across the site's pages. The
// step is kept in localStorage (inside try/catch: without storage the tour still works within the
// page load) and the callout is shown again after each navigation (Quartz's "nav" event) when the
// page on screen is the step's page; on any other page it waits, and the start button restarts
// it. Every text is set with textContent. No library.
import {
  ASK_EVENT,
  TOUR_KEY,
  relativeHref,
  tourPlacement,
  tourStep,
} from "../../../plugins/transformers/docwiki-text"
import { clientStrings } from "../i18n"

/** The element each step points at, best first; the callout is centred when none is found. */
const TARGETS: readonly string[][] = [
  [".docwiki-documents-links a[target='_blank']", ".docwiki-documents-links a", ".docwiki-documents"],
  [".docwiki-source-links", ".docwiki-source-header", "article"],
  [".docwiki-process", "article"],
  ["article a[data-footnote-ref]", "article sup a", "article"],
  ["#docwiki-ask .docwiki-ask-form", "#docwiki-ask:not([hidden])"],
  ["#docwiki-eval", ".docwiki-about"],
]
const COUNT = TARGETS.length
const ASK_STEP = 4
const NARROW = "(max-width: 640px)"
const HIGHLIGHT = "docwiki-tour-target"

/** The step when storage is unavailable (private mode, blocked site data). */
let memoryStep: number | null = null

function readStep(): number | null {
  try {
    return tourStep(window.localStorage.getItem(TOUR_KEY), COUNT)
  } catch {
    return memoryStep
  }
}

function saveStep(step: number | null) {
  memoryStep = step
  try {
    if (step === null) window.localStorage.removeItem(TOUR_KEY)
    else window.localStorage.setItem(TOUR_KEY, JSON.stringify({ step }))
  } catch {
    // No storage: the step lives in memory for this page load.
  }
}

function currentSlug(): string {
  return document.body.dataset.slug ?? "index"
}

function callout(): HTMLElement | null {
  return document.querySelector<HTMLElement>(".docwiki-tour")
}

function pages(box: HTMLElement): (string | null)[] {
  try {
    const value: unknown = JSON.parse(box.dataset.pages ?? "[]")
    return Array.isArray(value) ? value.map((item) => (typeof item === "string" ? item : null)) : []
  } catch {
    return []
  }
}

function findTarget(step: number): HTMLElement | null {
  for (const selector of TARGETS[step]) {
    const found = document.querySelector<HTMLElement>(selector)
    if (found && found.checkVisibility()) return found
  }
  return null
}

function clearHighlight() {
  for (const node of document.querySelectorAll(`.${HIGHLIGHT}`)) node.classList.remove(HIGHLIGHT)
}

function closeDrawer() {
  const close = document.querySelector<HTMLButtonElement>(
    "#docwiki-ask:not([hidden]) [data-ask-action='close']",
  )
  close?.click()
}

let shownStep: number | null = null
let target: HTMLElement | null = null

function place(box: HTMLElement) {
  const fixed = target !== null && getComputedStyle(target).position === "fixed"
  const inDrawer = target !== null && target.closest("#docwiki-ask") !== null
  const dock = window.matchMedia(NARROW).matches || fixed || inDrawer
  const rect = target?.getBoundingClientRect() ?? null
  const where = tourPlacement(
    rect ? { top: rect.top, left: rect.left, width: rect.width, height: rect.height } : null,
    { width: window.innerWidth, height: window.innerHeight },
    { width: box.offsetWidth, height: box.offsetHeight },
    dock,
  )
  box.dataset.mode = where.mode === "anchor" ? (where.above ? "above" : "below") : where.mode
  if (where.mode === "anchor") {
    // In page coordinates: the callout scrolls with its element.
    box.style.top = `${Math.round(where.top + window.scrollY)}px`
    box.style.left = `${Math.round(where.left + window.scrollX)}px`
  } else {
    box.style.top = ""
    box.style.left = ""
  }
}

function render(box: HTMLElement, step: number, announce: boolean) {
  const t = clientStrings().tour
  const words = t.steps[step]
  clearHighlight()
  target = findTarget(step)
  const count = box.querySelector<HTMLElement>(".docwiki-tour-count")
  const title = box.querySelector<HTMLElement>(".docwiki-tour-title")
  const body = box.querySelector<HTMLElement>(".docwiki-tour-body")
  const links = box.querySelector<HTMLElement>(".docwiki-tour-links")
  const back = box.querySelector<HTMLButtonElement>(".docwiki-tour-back")
  const next = box.querySelector<HTMLButtonElement>(".docwiki-tour-next")
  if (count) count.textContent = t.stepOf(step + 1, COUNT)
  if (title) title.textContent = words.title
  if (body) body.textContent = target ? words.body : `${words.body} ${t.missing}`
  if (links) links.hidden = step !== COUNT - 1
  if (back) back.disabled = step === 0
  if (next) next.textContent = step === COUNT - 1 ? t.done : t.next
  box.hidden = false
  shownStep = step
  if (target) {
    target.classList.add(HIGHLIGHT)
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    if (getComputedStyle(target).position !== "fixed") {
      // A tall element (the evaluation panel on a phone) shows from its top.
      const tall = target.getBoundingClientRect().height > window.innerHeight / 2
      target.scrollIntoView({ block: tall ? "start" : "center", behavior: still ? "auto" : "smooth" })
    }
  }
  place(box)
  // Again once a smooth scroll or the drawer's opening has settled.
  window.setTimeout(() => {
    if (shownStep === step && box.isConnected) place(box)
  }, 450)
  if (announce) {
    const live = document.querySelector<HTMLElement>(".docwiki-tour-live")
    if (live) live.textContent = `${t.stepOf(step + 1, COUNT)}. ${words.title}`
    title?.focus({ preventScroll: true })
  }
}

function hide(box: HTMLElement | null) {
  clearHighlight()
  target = null
  shownStep = null
  if (box) box.hidden = true
}

function go(step: number) {
  const box = callout()
  if (!box) return
  if (shownStep === ASK_STEP && step !== ASK_STEP) closeDrawer()
  saveStep(step)
  const page = pages(box)[step]
  if (!page || page === currentSlug()) {
    show(box, step)
    return
  }
  hide(box)
  const href = relativeHref(currentSlug(), page)
  const url = new URL(href, window.location.href)
  if (typeof window.spaNavigate === "function") void window.spaNavigate(url)
  else window.location.assign(url)
}

function show(box: HTMLElement, step: number) {
  if (step === ASK_STEP) {
    const question = box.dataset.question
    if (question) {
      document.dispatchEvent(new CustomEvent(ASK_EVENT, { detail: { question, fill: true } }))
    }
    // The drawer opens after it checked the live agent: point at it then.
    window.setTimeout(() => {
      if (readStep() === ASK_STEP && box.isConnected) render(box, ASK_STEP, true)
    }, 600)
    render(box, step, false)
    return
  }
  render(box, step, true)
}

function end() {
  const box = callout()
  if (shownStep === ASK_STEP) closeDrawer()
  saveStep(null)
  hide(box)
  const start = document.querySelector<HTMLElement>(".docwiki-tour-start")
  const main = document.getElementById("docwiki-main")
  if (start && start.checkVisibility()) start.focus()
  else main?.focus()
}

document.addEventListener("nav", () => {
  const box = callout()
  shownStep = null
  target = null
  const starts = Array.from(document.querySelectorAll<HTMLButtonElement>(".docwiki-tour-start"))
  const onStart = () => go(0)
  for (const start of starts) {
    start.hidden = !box
    start.addEventListener("click", onStart)
  }
  if (!box) {
    window.addCleanup(() => starts.forEach((start) => start.removeEventListener("click", onStart)))
    return
  }

  const onBack = () => {
    if (shownStep !== null && shownStep > 0) go(shownStep - 1)
  }
  const onNext = () => {
    if (shownStep === null) return
    if (shownStep >= COUNT - 1) end()
    else go(shownStep + 1)
  }
  const back = box.querySelector<HTMLButtonElement>(".docwiki-tour-back")
  const next = box.querySelector<HTMLButtonElement>(".docwiki-tour-next")
  const close = box.querySelector<HTMLButtonElement>(".docwiki-tour-close")
  back?.addEventListener("click", onBack)
  next?.addEventListener("click", onNext)
  close?.addEventListener("click", end)

  const onKeydown = (event: KeyboardEvent) => {
    if ((event.key !== "Escape" && event.key !== "Esc") || box.hidden) return
    const active = document.activeElement
    const nowhere = active === null || active === document.body
    if (!nowhere && !box.contains(active)) return
    event.preventDefault()
    event.stopPropagation()
    end()
  }
  let frame = 0
  const onResize = () => {
    if (frame || box.hidden) return
    frame = requestAnimationFrame(() => {
      frame = 0
      if (!box.hidden) place(box)
    })
  }
  document.addEventListener("keydown", onKeydown, true)
  window.addEventListener("resize", onResize)

  const step = readStep()
  if (step !== null) {
    const page = pages(box)[step]
    if (!page || page === currentSlug()) show(box, step)
  }

  window.addCleanup(() => {
    starts.forEach((start) => start.removeEventListener("click", onStart))
    back?.removeEventListener("click", onBack)
    next?.removeEventListener("click", onNext)
    close?.removeEventListener("click", end)
    document.removeEventListener("keydown", onKeydown, true)
    window.removeEventListener("resize", onResize)
    if (frame) cancelAnimationFrame(frame)
    clearHighlight()
  })
})
