// Pure helpers of the DocWiki transformer. No imports: unit-tested directly with Node
// (tests/site/test_overlay_text.py) and mirrored by docwiki.contracts.markdown in Python.

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
