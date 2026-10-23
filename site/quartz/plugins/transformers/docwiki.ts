import path from "path"
import { Element, ElementContent, Root as HtmlRoot, Text as HtmlText } from "hast"
import { toString as hastToString } from "hast-util-to-string"
import { Heading, Html, Root as MdRoot } from "mdast"
import { toString as mdastToString } from "mdast-util-to-string"
import { SKIP, visit } from "unist-util-visit"
import { QuartzTransformerPlugin } from "../types"
import {
  Badge,
  BadgeKind,
  BadgeSplit,
  CITATION_BADGES,
  dropsSiteNotice,
  isDocumentHref,
  isIsoDay,
  noticeKind,
  shownBadge,
  splitProvenanceBadge,
  splitTrailingBadge,
  stripBacklinksBlock,
} from "./docwiki-text"
import { pageLanguage, stringsFor } from "../../components/docwiki/i18n"
import type { Strings } from "../../components/docwiki/i18n"
import {
  cellLabels,
  foreignLang,
  loneElementIndex,
  splitIsoDates,
  splitQuoted,
  stacksTables,
  tableCaption,
} from "./docwiki-a11y"

export interface Options {
  /** Release date (YYYY-MM-DD) used for pages without an `updated` date (evidence sidecars). */
  releaseDate: string | null
  /** The site banner shows the fictional-sample notice on every page. */
  siteBanner: boolean
  /** Source id → the document's own language (`original_lang`), for the `lang` marks. */
  sourceLangs: Record<string, string | null>
  /**
   * The wiki's languages, the canonical one first (ADR 0012): a page's language is its `lang`,
   * else its folder's (`en/…`), and the page's own words (badges, legends) are in it.
   */
  languages: string[]
  /**
   * The mirror pages kept untranslated, content slug (`en/sources/x`) → summary: their text is in
   * the canonical language, which the page marks (`lang`), except the notice that says so.
   */
  untranslated: Record<string, string>
}

const defaultOptions: Options = {
  releaseDate: null,
  siteBanner: false,
  sourceLangs: {},
  languages: ["en"],
  untranslated: {},
}

/** mdast parents whose children are blocks (a raw HTML node there becomes a paragraph). */
const FLOW_PARENTS = new Set(["root", "blockquote", "listItem", "footnoteDefinition"])
const COMMENT = /^<!--[\s\S]*?-->$/

function classList(element: Element): string[] {
  const value = element.properties?.className
  if (Array.isArray(value)) return value.map(String)
  if (typeof value === "string") return value.split(/\s+/).filter(Boolean)
  return []
}

function addClass(element: Element, ...names: string[]) {
  element.properties = element.properties ?? {}
  element.properties.className = [...new Set([...classList(element), ...names])]
}

function text(value: string): HtmlText {
  return { type: "text", value }
}

/** A badge in the page's language (the Markdown keeps the wiki's English marker). */
function badgeElement(marker: Badge, t: Strings): Element {
  const badge = shownBadge(marker, t)
  return {
    type: "element",
    tagName: "span",
    properties: {
      className: ["docwiki-badge", `docwiki-badge--${badge.kind}`],
      title: badge.meaning,
    },
    children: [text(badge.text)],
  }
}

function splitNodes(split: BadgeSplit, t: Strings): ElementContent[] {
  const nodes: ElementContent[] = []
  if (split.before) nodes.push(text(split.before))
  nodes.push(badgeElement(split.badge, t))
  if (split.after) nodes.push(text(split.after))
  return nodes
}

/** Markdown stage: raw HTML is rendered as text (comments dropped), never as markup. */
function disableRawHtml(tree: MdRoot) {
  visit(tree, "html", (node: Html, index, parent) => {
    if (!parent || index === undefined) return
    if (COMMENT.test(node.value.trim())) {
      parent.children.splice(index, 1)
      return [SKIP, index]
    }
    const literal = { type: "text" as const, value: node.value }
    const replacement = FLOW_PARENTS.has(parent.type)
      ? { type: "paragraph" as const, children: [literal] }
      : literal
    ;(parent.children as unknown[]).splice(index, 1, replacement)
    return [SKIP, index + 1]
  })
}

/** Quartz renders the frontmatter title; drop the identical `# Title` that opens the body. */
function dropTitleHeading(tree: MdRoot, title: string | undefined) {
  const index = tree.children.findIndex((node) => node.type === "heading")
  if (index < 0 || !title) return
  const heading = tree.children[index] as Heading
  if (heading.depth === 1 && mdastToString(heading).trim() === title.trim()) {
    tree.children.splice(index, 1)
  }
}

/** Defense in depth for the HTML stage: no raw node or comment reaches the page. */
function stripRawNodes(tree: HtmlRoot) {
  visit(tree, (node, index, parent) => {
    if (!parent || index === undefined) return
    if (node.type === "comment") {
      parent.children.splice(index, 1)
      return [SKIP, index]
    }
    if ((node.type as string) === "raw") {
      parent.children.splice(index, 1, text(String((node as { value?: unknown }).value ?? "")))
      return [SKIP, index + 1]
    }
  })
}

function isFootnotes(element: Element): boolean {
  return element.tagName === "section" && element.properties?.dataFootnotes !== undefined
}

function lastParagraph(element: Element): Element | undefined {
  for (let i = element.children.length - 1; i >= 0; i--) {
    const child = element.children[i]
    if (child.type === "element" && child.tagName === "p") return child
  }
  return undefined
}

const BACK_LABEL = /^Back to reference (\S+)$/

/**
 * The footnotes' words that remark-rehype writes in English: the section's (hidden) heading
 * "Footnotes" and each back link's name "Back to reference 1-2", in the page's language.
 */
function localizeFootnotes(section: Element, t: Strings) {
  visit(section, "element", (node: Element) => {
    if (node.tagName === "h2" && node.properties?.id === "footnote-label") {
      const index = node.children.findIndex((child) => child.type === "text")
      if (index >= 0) node.children.splice(index, 1, text(t.wiki.footnotes))
      return SKIP
    }
    const label = node.properties?.ariaLabel
    if (node.tagName === "a" && node.properties?.dataFootnoteBackref !== undefined) {
      const found = typeof label === "string" ? BACK_LABEL.exec(label) : null
      if (found) node.properties.ariaLabel = t.wiki.footnoteBack(found[1])
    }
  })
}

/** Wrap the provenance badge that ends each footnote definition in a styled span. */
function decorateFootnotes(section: Element, t: Strings): Set<BadgeKind> {
  localizeFootnotes(section, t)
  const used = new Set<BadgeKind>()
  visit(section, "element", (item: Element) => {
    if (item.tagName !== "li") return
    const container = lastParagraph(item) ?? item
    for (let i = container.children.length - 1; i >= 0; i--) {
      const child = container.children[i]
      if (child.type !== "text") continue
      if (!child.value.trim()) continue
      const split = splitTrailingBadge(child.value)
      if (split) {
        container.children.splice(i, 1, ...splitNodes(split, t))
        used.add(split.badge.kind)
      }
      break
    }
    return SKIP
  })
  if (used.size > 0) section.children.push(badgeLegend(used, t))
  return used
}

function badgeLegend(used: Set<BadgeKind>, t: Strings): Element {
  const children: ElementContent[] = [
    {
      type: "element",
      tagName: "span",
      properties: { className: ["docwiki-badge-legend-title"] },
      children: [text(t.wiki.provenanceBadges)],
    },
  ]
  for (const badge of CITATION_BADGES) {
    if (!used.has(badge.kind)) continue
    children.push({
      type: "element",
      tagName: "span",
      properties: { className: ["docwiki-badge-legend-item"] },
      children: [badgeElement(badge, t), text(` ${shownBadge(badge, t).meaning}`)],
    })
  }
  return {
    type: "element",
    tagName: "p",
    properties: { className: ["docwiki-badge-legend"] },
    children,
  }
}

/**
 * Notices before the first section (`> FICTIONAL …`, `> **Superseded** by …`). A fictional notice
 * that only repeats the site banner (the home page) is removed.
 */
function decorateNotices(
  tree: HtmlRoot,
  evidence: boolean,
  slug: string | undefined,
  banner: boolean,
) {
  let beforeFirstSection = true
  for (let index = 0; index < tree.children.length; index++) {
    const node = tree.children[index]
    if (node.type !== "element") continue
    if (node.tagName === "h2") beforeFirstSection = false
    if (node.tagName !== "blockquote") continue
    const kind = beforeFirstSection ? noticeKind(hastToString(node)) : undefined
    if (dropsSiteNotice(slug, banner, kind)) {
      tree.children.splice(index, 1)
      index--
    } else if (kind) {
      addClass(node, "docwiki-notice", `docwiki-notice--${kind}`)
    } else if (evidence) {
      addClass(node, "docwiki-verbatim")
    }
  }
}

/** Evidence sidecars: badge in the `Provenance:` line, navigation line, zoomable specimen. */
function decorateEvidence(tree: HtmlRoot, t: Strings) {
  for (const node of tree.children) {
    if (node.type !== "element" || node.tagName !== "p") continue
    const content = hastToString(node)
    if (!content.includes("Source page:") && !content.includes("Provenance:")) continue
    addClass(node, "docwiki-evidence-nav")
    visit(node, "text", (child: HtmlText, index, parent) => {
      if (!parent || index === undefined) return
      const split = splitProvenanceBadge(child.value)
      if (!split) return
      const nodes = splitNodes(split, t)
      parent.children.splice(index, 1, ...nodes)
      return [SKIP, index + nodes.length]
    })
  }
  visit(tree, "element", (node: Element, index, parent) => {
    if (node.tagName !== "img" || !parent || index === undefined) return
    addClass(node, "docwiki-specimen")
    const src = node.properties?.src
    if (typeof src !== "string" || parent.type !== "element" || parent.tagName === "a") return
    parent.children.splice(index, 1, {
      type: "element",
      tagName: "a",
      properties: {
        href: src,
        className: ["docwiki-zoom"],
        dataNoPopover: "true",
        dataRouterIgnore: "true",
        title: t.wiki.openImage,
      },
      children: [node],
    })
    return SKIP
  })
}

function decorateDocumentLinks(tree: HtmlRoot) {
  visit(tree, "element", (node: Element) => {
    const href = node.properties?.href
    if (node.tagName !== "a" || typeof href !== "string" || !isDocumentHref(href)) return
    addClass(node, "docwiki-original")
    node.properties.dataNoPopover = "true"
    node.properties.dataRouterIgnore = "true"
  })
}

/** Elements whose content is page chrome or code: no language marks inside them. */
const NO_QUOTE_MARKS = new Set(["code", "pre", "script", "style", "svg"])

/**
 * The document's own words in an English page (slice H, WCAG 3.1.2): verbatim blockquotes and
 * table rows of an evidence sidecar, the quoted passages and blockquotes of a source page. Notices
 * (the fictional stamp, superseded) are English and stay unmarked.
 */
function markLanguage(tree: HtmlRoot, type: string | undefined, lang: string) {
  if (type === "evidence") {
    visit(tree, "element", (node: Element) => {
      const quote = node.tagName === "blockquote" && classList(node).includes("docwiki-verbatim")
      if (quote || node.tagName === "table") {
        node.properties = { ...node.properties, lang }
        return SKIP
      }
    })
    return
  }
  if (type !== "source") return
  visit(tree, "element", (node: Element) => {
    if (node.tagName === "blockquote") {
      if (!classList(node).includes("docwiki-notice")) node.properties = { ...node.properties, lang }
      return SKIP
    }
    if (NO_QUOTE_MARKS.has(node.tagName) || isFootnotes(node)) return SKIP
    for (let index = 0; index < node.children.length; index++) {
      const child = node.children[index]
      if (child.type !== "text") continue
      const parts = splitQuoted(child.value)
      if (!parts.some((part) => part.quoted)) continue
      const nodes: ElementContent[] = parts.map((part) =>
        part.quoted
          ? { type: "element", tagName: "span", properties: { lang }, children: [text(part.text)] }
          : text(part.text),
      )
      node.children.splice(index, 1, ...nodes)
      index += nodes.length - 1
    }
  })
}

function hasClass(node: ElementContent | HtmlRoot["children"][number], name: string): boolean {
  return node.type === "element" && classList(node).includes(name)
}

/**
 * A mirror page kept untranslated (WCAG 3.1.2): its text is in the canonical language `lang`, so
 * every block of the body is marked with it, except the notice that says so (in the page's
 * language) and the footnotes' heading and badges (the page's words); the footnotes' citations are
 * marked too.
 */
function markUntranslated(tree: HtmlRoot, lang: string, pageLang: string) {
  for (const node of tree.children) {
    if (node.type !== "element" || hasClass(node, "docwiki-notice--untranslated")) continue
    if (isFootnotes(node)) {
      for (const child of node.children) {
        if (child.type !== "element" || child.tagName !== "ol") continue
        child.properties = { ...child.properties, lang }
        visit(child, "element", (badge: Element) => {
          if (!classList(badge).includes("docwiki-badge")) return
          badge.properties = { ...badge.properties, lang: pageLang }
          return SKIP
        })
      }
      continue
    }
    node.properties = { ...node.properties, lang }
  }
}

/** The content slug a Markdown link of the page `slug` leads to (`en/sources/x`), else null. */
function linkSlug(slug: string, href: string): string | null {
  if (/^[a-z][a-z0-9+.-]*:|^\/\/|^#/i.test(href)) return null
  let target = href.split(/[?#]/, 1)[0]
  try {
    target = decodeURIComponent(target)
  } catch {
    return null
  }
  if (!target) return null
  const folder = path.posix.dirname(slug)
  const resolved = path.posix.normalize(path.posix.join(folder === "." ? "" : folder, target))
  return resolved.replace(/\.md$/, "").replace(/\/$/, "/index")
}

/** Elements that end the inline run after a listed link (a nested list, a paragraph). */
const BLOCKS = new Set(["ul", "ol", "p", "div", "table", "blockquote", "pre"])

/**
 * Lists of a mirror page (its home, a hub): a link to an untranslated page shows that page's
 * title in the canonical language `lang`, and its list item may go on with that page's summary
 * (`: …`); both are marked.
 */
function markUntranslatedLinks(
  tree: HtmlRoot,
  slug: string,
  untranslated: Record<string, string>,
  lang: string,
) {
  const summaries = new Map<Element, string>()
  visit(tree, "element", (node: Element) => {
    if (node.tagName !== "a") return
    const href = node.properties?.href
    const target = typeof href === "string" ? linkSlug(slug, href) : null
    if (!target || !Object.prototype.hasOwnProperty.call(untranslated, target)) return
    node.properties = { ...node.properties, lang }
    summaries.set(node, untranslated[target])
    return SKIP
  })
  visit(tree, "element", (item: Element) => {
    // A tight list item holds the link, a loose one its paragraph.
    if (item.tagName !== "li" && item.tagName !== "p") return
    const first = item.children.findIndex(
      (child) => child.type !== "text" || child.value.trim() !== "",
    )
    const link = item.children[first]
    const summary = link?.type === "element" ? summaries.get(link) : undefined
    if (!summary) return
    let end = first + 1
    while (end < item.children.length) {
      const child = item.children[end]
      if (child.type === "element" && BLOCKS.has(child.tagName)) break
      end++
    }
    const rest = item.children.slice(first + 1, end)
    const words = rest
      .map((child) => hastToString(child))
      .join("")
      .replace(/^\s*[:—–-]\s*/, "")
      .replace(/\s+/g, " ")
      .trim()
    if (words !== summary) return
    item.children.splice(first + 1, rest.length, {
      type: "element",
      tagName: "span",
      properties: { lang },
      children: rest,
    })
  })
}

/** Blocks where a link alone is a control rather than a link inside a sentence. */
const LONE_LINK_PARENTS = new Set(["li", "p", "td", "th", "dd"])

/** A link alone in its list item, paragraph or cell gets a target of at least 24 px (CSS). */
function markLoneLinks(tree: HtmlRoot) {
  visit(tree, "element", (node: Element) => {
    if (!LONE_LINK_PARENTS.has(node.tagName)) return
    const index = loneElementIndex(node.children)
    const child = index === -1 ? undefined : node.children[index]
    if (child?.type === "element" && child.tagName === "a") addClass(child, "docwiki-target")
  })
}

function childElements(node: Element, tagName: string): Element[] {
  return node.children.filter(
    (child): child is Element => child.type === "element" && child.tagName === tagName,
  )
}

/** The ISO days written in a data table's cell (`(2026-04-21)`) never wrap at their hyphens. */
function keepDatesWhole(cell: Element) {
  for (let index = 0; index < cell.children.length; index++) {
    const child = cell.children[index]
    if (child.type !== "text") continue
    const parts = splitIsoDates(child.value)
    if (!parts.some((part) => part.date)) continue
    const nodes: ElementContent[] = parts.map((part) =>
      part.date
        ? {
            type: "element",
            tagName: "span",
            properties: { className: ["docwiki-nowrap"] },
            children: [text(part.text)],
          }
        : text(part.text),
    )
    cell.children.splice(index, 1, ...nodes)
    index += nodes.length - 1
  }
}

/**
 * The wiki's data tables: each body cell gets its column's header as `data-label`, which the
 * stacked cards show on narrow screens (`docwiki-cards`, not on evidence sidecars); a computed
 * view's tables get `data-caption` (the view's title), the name of their scroll box.
 */
function decorateTables(tree: HtmlRoot, type: string | undefined, title: unknown) {
  let heading = ""
  let index = 0
  for (const node of tree.children) {
    if (node.type !== "element") continue
    if (/^h[1-6]$/.test(node.tagName)) {
      heading = hastToString(node)
      continue
    }
    if (node.tagName !== "table") continue
    const head = childElements(node, "thead")[0]
    const headerRow = head ? childElements(head, "tr")[0] : undefined
    const headers = headerRow ? childElements(headerRow, "th").map((th) => hastToString(th)) : []
    for (const body of childElements(node, "tbody")) {
      for (const row of childElements(body, "tr")) {
        const cells = childElements(row, "td")
        cellLabels(headers, cells.length).forEach((label, position) => {
          if (label) cells[position].properties = { ...cells[position].properties, dataLabel: label }
        })
        if (stacksTables(type)) cells.forEach(keepDatesWhole)
      }
    }
    if (headers.length > 0 && stacksTables(type)) addClass(node, "docwiki-cards")
    const caption = tableCaption(type, title, heading, index)
    if (caption) node.properties = { ...node.properties, dataCaption: caption }
    index += 1
  }
}

export const DocWiki: QuartzTransformerPlugin<Partial<Options>> = (userOpts) => {
  const opts = { ...defaultOptions, ...userOpts }
  return {
    name: "DocWiki",
    textTransform(_ctx, src) {
      return stripBacklinksBlock(src)
    },
    markdownPlugins() {
      return [
        () => {
          return (tree: MdRoot, file) => {
            disableRawHtml(tree)
            const frontmatter = file.data.frontmatter
            if (!frontmatter) return
            // A page without `lang` in a wiki with a mirror takes its folder's language, so that
            // Quartz writes the right `<html lang>`.
            if (opts.languages.length > 1 && typeof frontmatter.lang !== "string") {
              frontmatter.lang = pageLanguage(file.data.slug ?? "index", null, opts.languages)
            }
            dropTitleHeading(tree, frontmatter.title)
            const type = typeof frontmatter.type === "string" ? frontmatter.type : undefined
            if (!frontmatter.description && typeof frontmatter.summary === "string") {
              frontmatter.description = frontmatter.summary
            }
            const classes = new Set([...(frontmatter.cssclasses ?? []), "docwiki"])
            if (type) classes.add(`docwiki-${type}`)
            frontmatter.cssclasses = [...classes]
            const day = isIsoDay(frontmatter.updated) ? frontmatter.updated : opts.releaseDate
            if (isIsoDay(day)) {
              const date = new Date(`${day}T00:00:00`)
              file.data.dates = { created: date, modified: date, published: date }
            }
          }
        },
      ]
    },
    htmlPlugins() {
      return [
        () => {
          return (tree: HtmlRoot, file) => {
            stripRawNodes(tree)
            const pageLang = pageLanguage(
              file.data.slug ?? "index",
              file.data.frontmatter?.lang,
              opts.languages,
            )
            const t = stringsFor(pageLang)
            const evidence = file.data.frontmatter?.type === "evidence"
            visit(tree, "element", (node: Element) => {
              if (!isFootnotes(node)) return
              decorateFootnotes(node, t)
              return SKIP
            })
            decorateNotices(tree, evidence, file.data.slug, opts.siteBanner)
            if (evidence) decorateEvidence(tree, t)
            decorateDocumentLinks(tree)
            markLoneLinks(tree)
            const frontmatter = file.data.frontmatter
            const type = typeof frontmatter?.type === "string" ? frontmatter.type : undefined
            decorateTables(tree, type, frontmatter?.title)
            const sourceId = frontmatter?.source_id
            const lang = foreignLang(
              type === "source"
                ? frontmatter?.original_lang
                : typeof sourceId === "string"
                  ? opts.sourceLangs[sourceId]
                  : null,
              pageLang,
            )
            // A mirror page kept untranslated is in the canonical language (gate G17 warns).
            const canonical = opts.languages[0] ?? pageLang
            const slug = file.data.slug ?? "index"
            const untranslated =
              pageLang !== canonical &&
              (Object.prototype.hasOwnProperty.call(opts.untranslated, slug) ||
                tree.children.some((node) => hasClass(node, "docwiki-notice--untranslated")))
            if (untranslated) {
              markUntranslated(tree, canonical, pageLang)
              file.data.docwikiTextLang = canonical
            } else if (lang) {
              markLanguage(tree, type, lang)
            }
            if (pageLang !== canonical && Object.keys(opts.untranslated).length > 0) {
              markUntranslatedLinks(tree, slug, opts.untranslated, canonical)
            }
          }
        },
      ]
    },
  }
}

declare module "vfile" {
  interface DataMap {
    /** The language of a page's text when it differs from the page's (an untranslated mirror). */
    docwikiTextLang: string
  }
}
