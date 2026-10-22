// Client of the header (Tabs.tsx, ADR 0010): the pipeline's status chip and the owner's Sign in.
//
// /api/status says whether the pipeline is idle, processing n documents, or has just put a
// document in the wiki (with its page); /api/owner/me says whether the site offers a sign-in and
// who is signed in. Both are read once per page load and the status is then polled (fast while
// processing, slow otherwise, paused on a hidden tab). Quartz replaces the header on every
// navigation, so each "nav" re-fills it from the last answers. Only site-absolute pages and the
// platform's /.auth/ pages are linked; everything is rendered with textContent.
import { relativeHref } from "../../../plugins/transformers/docwiki-text"
import { statusPill } from "./status"

const STATUS_PATH = "api/status"
const ME_PATH = "api/owner/me"
const FAST_MS = 5_000
const SLOW_MS = 30_000

interface Status {
  state: "idle" | "processing" | "published"
  processing: number
  document: { title: string; pageUrl: string } | null
}

interface Me {
  signIn: boolean
  owner: boolean
  signInUrl: string | null
}

let status: Status | null = null
let me: Me | null = null
/** The state last announced to screen readers ("" before the first answer: never announced). */
let announced = ""
let timer = 0
let polling = false
let unavailable = false

function record(value: unknown): Record<string, unknown> | null {
  return typeof value === "object" && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null
}

function sitePage(value: unknown): string | null {
  return typeof value === "string" &&
    value.startsWith("/") &&
    !value.startsWith("//") &&
    !value.includes("\\")
    ? value
    : null
}

function parseStatus(payload: unknown): Status | null {
  const data = record(payload)
  const state = data?.state
  if (state !== "idle" && state !== "processing" && state !== "published") return null
  const doc = record(data?.document)
  const title = typeof doc?.title === "string" ? doc.title : null
  const pageUrl = sitePage(doc?.page_url)
  const processing = typeof data?.processing === "number" ? data.processing : 0
  return {
    state,
    processing,
    document: title && pageUrl ? { title, pageUrl } : null,
  }
}

function parseMe(payload: unknown): Me | null {
  const data = record(payload)
  if (!data) return null
  const url = typeof data.sign_in_url === "string" ? data.sign_in_url : null
  return {
    signIn: data.sign_in === true,
    owner: data.owner === true,
    signInUrl: url && url.startsWith("/.auth/") ? url : null,
  }
}

function currentSlug(): string {
  return document.body.dataset.slug ?? "index"
}

/** A site-absolute page (`/sources/x`) as a link relative to the current page. */
function fromRoot(url: string): string {
  return relativeHref(currentSlug(), url.replace(/^\/+/, "") || "index")
}

function chipText(value: Status): { words: string; state: "processing" | "in_wiki" | "idle" } {
  if (value.state === "processing") {
    const n = value.processing
    const words =
      n > 0 ? `Processing ${n} document${n === 1 ? "" : "s"}` : "Processing — a run is at work"
    return { words, state: "processing" }
  }
  if (value.state === "published" && value.document) {
    return { words: "In the wiki → new page", state: "in_wiki" }
  }
  return { words: "Idle", state: "idle" }
}

function render(): void {
  const chip = document.querySelector<HTMLAnchorElement>(".docwiki-chip")
  const live = document.querySelector<HTMLElement>(".docwiki-chip-live")
  if (chip) {
    if (status && !unavailable) {
      const { words, state } = chipText(status)
      const pill = statusPill(state === "idle" ? "in_wiki" : state, words)
      if (state === "idle") pill.classList.add("docwiki-status--idle")
      chip.replaceChildren(...Array.from(pill.childNodes))
      chip.className = `docwiki-chip is-ready ${pill.className}`
      const published = status.state === "published" && status.document
      chip.setAttribute(
        "href",
        published && status.document ? fromRoot(status.document.pageUrl) : fromRoot("/pipeline"),
      )
      chip.title =
        published && status.document
          ? `In the wiki: ${status.document.title}`
          : state === "idle"
            ? "The pipeline is idle; open it"
            : words
      if (published && status.document) {
        chip.setAttribute("aria-label", `In the wiki: ${status.document.title}`)
      } else {
        chip.removeAttribute("aria-label")
      }
      if (live && announced !== "" && announced !== words) live.textContent = `Pipeline: ${words}`
      announced = words
    } else {
      chip.classList.remove("is-ready")
    }
  }
  const signIn = document.querySelector<HTMLAnchorElement>(".docwiki-sign-in")
  if (signIn) {
    if (me?.owner) {
      signIn.textContent = "Owner ✓"
      signIn.setAttribute("href", fromRoot("/pipeline"))
      signIn.title = "Signed in as the owner: add documents on the Pipeline page"
      signIn.classList.add("is-ready")
    } else if (me?.signIn && me.signInUrl) {
      signIn.textContent = "Sign in"
      signIn.setAttribute("href", me.signInUrl)
      signIn.title = "Owner sign-in: only the owner adds documents"
      signIn.classList.add("is-ready")
    } else {
      signIn.classList.remove("is-ready")
    }
  }
}

async function getJson(path: string): Promise<{ status: number; payload: unknown }> {
  const response = await fetch(relativeHref(currentSlug(), path), {
    credentials: "same-origin",
    cache: "no-store",
  })
  const payload = response.ok ? await response.json() : null
  return { status: response.status, payload }
}

function schedule(): void {
  window.clearTimeout(timer)
  if (document.hidden) return
  const ms = status?.state === "processing" ? FAST_MS : SLOW_MS
  timer = window.setTimeout(() => void poll(), ms)
}

async function poll(): Promise<void> {
  try {
    const { status: code, payload } = await getJson(STATUS_PATH)
    // A static host has no portal: the chip stays hidden and nothing is polled.
    if (code === 404 && status === null) {
      polling = false
      return
    }
    const parsed = code === 200 ? parseStatus(payload) : null
    if (!parsed) throw new Error(`HTTP ${code}`)
    status = parsed
    unavailable = false
  } catch (error) {
    console.warn("DocWiki: the pipeline status could not be read", error)
    unavailable = true
  }
  render()
  schedule()
}

document.addEventListener("visibilitychange", () => {
  if (!polling) return
  if (document.hidden) window.clearTimeout(timer)
  else void poll()
})

/** A table wider than the page scrolls in its own box: make that box reachable by keyboard. */
function scrollableTables(): void {
  for (const box of document.querySelectorAll<HTMLElement>("article .table-container")) {
    if (box.scrollWidth <= box.clientWidth + 1) continue
    box.tabIndex = 0
    box.setAttribute("role", "region")
    const heading = box.closest("article")
      ? (box.previousElementSibling?.textContent ?? "").trim().slice(0, 60)
      : ""
    box.setAttribute("aria-label", heading ? `Table: ${heading}` : "Table")
  }
}

document.addEventListener("nav", () => {
  render()
  scrollableTables()
  if (!polling) {
    polling = true
    void poll()
  }
  if (me === null) {
    getJson(ME_PATH)
      .then(({ payload }) => {
        me = parseMe(payload) ?? { signIn: false, owner: false, signInUrl: null }
        render()
      })
      .catch(() => {
        // No portal: no sign-in.
      })
  }
})
