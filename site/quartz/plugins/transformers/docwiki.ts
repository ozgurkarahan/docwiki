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
}

const defaultOptions: Options = {
  releaseDate: null,
  siteBanner: false,
  sourceLangs: {},
  languages: ["en"],
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

/** Wrap the provenance badge that ends each footnote definition in a styled span. */
function decorateFootnotes(section: Element, t: Strings): Set<BadgeKind> {
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
            if (lang) markLanguage(tree, type, lang)
          }
        },
      ]
    },
  }
}
