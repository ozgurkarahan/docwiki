// The one status vocabulary of the site (ADR 0010): always a shape, a word and a colour (the
// colour comes from the `docwiki-status--<state>` class). The portal computes the state
// (`document_state` in src/docwiki/portal/process.py); the browser only words it, in the page's
// language (i18n/en.ts, i18n/fr.ts: "In the wiki", "Dans le wiki").
import { clientStrings } from "../i18n"
import type { Strings } from "../i18n"

export const STATES = [
  "received",
  "queued",
  "processing",
  "in_wiki",
  "superseded",
  "held_back",
  "failed",
  "removed",
] as const

export type State = (typeof STATES)[number]

const SHAPES: Record<State, string> = {
  received: "○",
  queued: "◌",
  processing: "◐",
  in_wiki: "●",
  superseded: "◑",
  held_back: "⊘",
  failed: "✕",
  removed: "○",
}

export function asState(value: unknown): State | null {
  return typeof value === "string" && (STATES as readonly string[]).includes(value)
    ? (value as State)
    : null
}

/** "Processing 4/13 compile", "In the wiki", "En cours 4/13 compile", … */
export function stateWords(
  state: State,
  step: number | null = null,
  steps: number | null = null,
  stage: string | null = null,
  t: Strings = clientStrings(),
): string {
  const word = t.status[state]
  if (state !== "processing" || step === null) return word
  const of = steps ? `${step}/${steps}` : String(step)
  return stage ? `${word} ${of} ${stage}` : `${word} ${of}`
}

/** A status pill: the shape (hidden from screen readers, the word says it) and the word. */
export function statusPill(
  state: State,
  words: string = clientStrings().status[state],
  tag: "span" | "a" = "span",
): HTMLElement {
  const pill = document.createElement(tag)
  pill.className = `docwiki-status docwiki-status--${state}`
  const shape = document.createElement("span")
  shape.className = "docwiki-status-shape"
  shape.setAttribute("aria-hidden", "true")
  shape.textContent = SHAPES[state]
  const word = document.createElement("span")
  word.className = "docwiki-status-word"
  word.textContent = words
  pill.append(shape, word)
  return pill
}
