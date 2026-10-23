// Client of the story home (Story.tsx, ADR 0010).
//
// - The pipeline card: on each visit of the home page, the portal's GET /api/process gives the
//   length and cost of the run that built the published release; the card shows them as
//   "last run 4 min · $1.37" (textContent only). A static host (no /api) or an error keeps the
//   build-time text.
// - "Try: …": shown while the "Ask this wiki" button is shown (the drawer has filed answers or a
//   live agent), it opens the drawer on its question through the drawer's ASK_EVENT hook.
// - The third card scrolls to the wiki below (Quartz's router) and moves the focus there.
import { ASK_EVENT, lastRunLine, relativeHref } from "../../../plugins/transformers/docwiki-text"
import { clientStrings } from "../i18n"

const PROCESS_PATH = "api/process"
const WIKI_ANCHOR = "docwiki-wiki"

/** The last reply read this page load, shown at once on a later visit of the home page. */
let runReply: unknown = null

function showRun(slot: HTMLElement) {
  // Worded in the language of the page on screen (the reply is the same in every language).
  const runLine = runReply === null ? null : lastRunLine(runReply, clientStrings())
  if (runLine && slot.isConnected) slot.textContent = runLine
}

async function readRun(slot: HTMLElement) {
  showRun(slot)
  try {
    const slug = document.body.dataset.slug ?? "index"
    const response = await fetch(relativeHref(slug, PROCESS_PATH), {
      credentials: "same-origin",
      cache: "no-store",
    })
    if (!response.ok) return // a static host: the build-time text stays
    const reply: unknown = await response.json()
    if (lastRunLine(reply)) runReply = reply
    showRun(slot)
  } catch {
    // No portal or no JSON: the build-time text stays.
  }
}

document.addEventListener("nav", () => {
  const story = document.querySelector<HTMLElement>(".docwiki-story")
  if (!story) return

  const slot = story.querySelector<HTMLElement>(".docwiki-story-run")
  if (slot) void readRun(slot)

  const wiki = story.querySelector<HTMLAnchorElement>(".docwiki-story-wiki")
  const onWiki = (event: MouseEvent) => {
    if (event.button !== 0 || event.ctrlKey || event.metaKey) return
    const target = document.getElementById(WIKI_ANCHOR)
    // After Quartz's router scrolled to it: keyboard users continue from there.
    if (target) requestAnimationFrame(() => target.focus({ preventScroll: true }))
  }
  wiki?.addEventListener("click", onWiki)

  const tryButton = story.querySelector<HTMLButtonElement>(".docwiki-story-try")
  const fab = document.querySelector<HTMLButtonElement>(".docwiki-ask-fab")
  if (!tryButton || !fab) {
    window.addCleanup(() => wiki?.removeEventListener("click", onWiki))
    return
  }
  const sync = () => {
    tryButton.hidden = fab.hidden
  }
  sync()
  // The drawer's script shows its button once it knows there is something to show.
  const observer = new MutationObserver(sync)
  observer.observe(fab, { attributes: true, attributeFilter: ["hidden"] })
  const onTry = () => {
    const question = tryButton.dataset.question
    document.dispatchEvent(new CustomEvent(ASK_EVENT, { detail: { question } }))
  }
  tryButton.addEventListener("click", onTry)
  // On a phone the floating "Ask this wiki" button would cover the question to try, which opens
  // the same drawer: it steps aside while the question is on screen (custom.scss).
  const seen = new IntersectionObserver((entries) => {
    document.body.classList.toggle("docwiki-try-visible", entries.some((e) => e.isIntersecting))
  })
  seen.observe(tryButton)
  window.addCleanup(() => {
    seen.disconnect()
    document.body.classList.remove("docwiki-try-visible")
    observer.disconnect()
    tryButton.removeEventListener("click", onTry)
    wiki?.removeEventListener("click", onWiki)
  })
})
