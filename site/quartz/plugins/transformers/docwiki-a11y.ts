// Pure accessibility helpers of the DocWiki overlay (slice H): the transformer's language marks and
// lone-link targets, the skip link's target and the drawer's focus cycling.
// No imports: unit-tested directly with Node (tests/site/test_a11y_text.py).

/** Id of the page title (DocWiki's ArticleTitle): the target of the "Skip to content" link. */
export const SKIP_TARGET_ID = "docwiki-main"

const LANG_TAG = /^([a-z]{2,3})(-[a-z0-9]{2,8})*$/i

/**
 * The `lang` attribute for content in a document's own language, or `null` when there is nothing
 * to mark: the pages are English, so English (or an unknown or malformed tag) needs no mark.
 */
export function foreignLang(lang: unknown): string | null {
  if (typeof lang !== "string") return null
  const tag = lang.trim()
  const match = LANG_TAG.exec(tag)
  if (!match || match[1].toLowerCase() === "en") return null
  return tag.toLowerCase()
}

export interface QuotedPart {
  text: string
  quoted: boolean
}

/** Opening mark → closing mark of the quotations that `splitQuoted` recognises. */
const QUOTES: Record<string, string> = { '"': '"', "“": "”", "«": "»" }
const QUOTED_MAX = 200

/**
 * Split a text into plain parts and the inside of its quotations ("…", “…”, « … »), the quotation
 * marks staying in the plain parts. In a source page the quotations are the document's own words
 * (in its language); the caller marks them with `lang`. A quotation without letters, longer than
 * 200 characters or not closed is left as plain text.
 */
export function splitQuoted(text: string): QuotedPart[] {
  const parts: QuotedPart[] = []
  let plain = ""
  let index = 0
  while (index < text.length) {
    const open = text[index]
    const close = QUOTES[open]
    const end = close === undefined ? -1 : text.indexOf(close, index + 1)
    if (end === -1) {
      plain += open
      index += 1
      continue
    }
    const raw = text.slice(index + 1, end)
    // Guillemets are spaced in French (« texte »): the spaces stay outside the mark.
    const lead = raw.length - raw.trimStart().length
    const trail = raw.length - raw.trimEnd().length
    const inner = raw.trim()
    if (!inner || inner.length > QUOTED_MAX || !/\p{L}/u.test(inner)) {
      // The whole quotation stays plain: its closing mark must not open another one.
      plain += text.slice(index, end + 1)
      index = end + 1
      continue
    }
    plain += open + raw.slice(0, lead)
    parts.push({ text: plain, quoted: false })
    parts.push({ text: inner, quoted: true })
    plain = raw.slice(raw.length - trail) + close
    index = end + 1
  }
  if (plain) parts.push({ text: plain, quoted: false })
  return parts.filter((part) => part.quoted || part.text !== "")
}

/** A hast-like node: enough of `hast` for `loneElementIndex`. */
export interface NodeLike {
  type: string
  value?: string
  tagName?: string
}

/**
 * Index of the only element among `children` when every other child is blank text, else -1. A
 * link alone in its list item, paragraph or table cell is a control, not a link inside a sentence:
 * it gets a target of at least 24 px (WCAG 2.5.8).
 */
export function loneElementIndex(children: readonly NodeLike[]): number {
  let found = -1
  for (let index = 0; index < children.length; index++) {
    const child = children[index]
    if (child.type === "text" && !(child.value ?? "").trim()) continue
    if (child.type !== "element" || found !== -1) return -1
    found = index
  }
  return found
}

/**
 * Where Tab goes from the focusable element at `index` of `count` when the focus cycles inside a
 * panel: the first element after the last one, the last one before the first; -1 when the browser's
 * own order stays inside (or the focus is not on one of them: then the first, or the last with
 * Shift).
 */
export function cycleFocus(count: number, index: number, backwards: boolean): number {
  if (count <= 0) return -1
  if (index < 0 || index >= count) return backwards ? count - 1 : 0
  if (backwards) return index === 0 ? count - 1 : -1
  return index === count - 1 ? 0 : -1
}
