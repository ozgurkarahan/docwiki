// The one status vocabulary of the site (ADR 0010): always a shape, a word and a colour (the
// colour comes from the `docwiki-status--<state>` class). The portal computes the state
// (`document_state` in src/docwiki/portal/process.py); the browser only words it.

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

const WORDS: Record<State, string> = {
  received: "Received",
  queued: "Queued",
  processing: "Processing",
  in_wiki: "In the wiki",
  superseded: "Superseded",
  held_back: "Held back",
  failed: "Failed",
  removed: "Removed",
}

export function asState(value: unknown): State | null {
  return typeof value === "string" && (STATES as readonly string[]).includes(value)
    ? (value as State)
    : null
}

/** "Processing 4/13 compile", "In the wiki", … */
export function stateWords(
  state: State,
  step: number | null = null,
  steps: number | null = null,
  stage: string | null = null,
): string {
  if (state !== "processing" || step === null) return WORDS[state]
  const of = steps ? `${step}/${steps}` : String(step)
  return stage ? `${WORDS[state]} ${of} ${stage}` : `${WORDS[state]} ${of}`
}

/** A status pill: the shape (hidden from screen readers, the word says it) and the word. */
export function statusPill(
  state: State,
  words: string = WORDS[state],
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
