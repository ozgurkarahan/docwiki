import { Root } from "hast"
import { visit } from "unist-util-visit"
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { provenanceBadge } from "../../plugins/transformers/docwiki-text"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { pageLang, pageStrings, settingsFor } from "./settings"

function pdfPage(locator: unknown): number | undefined {
  if (typeof locator !== "object" || locator === null) return undefined
  const { kind, page } = locator as { kind?: unknown; page?: unknown }
  return kind === "pdf-page" && typeof page === "number" ? page : undefined
}

function pathOf(slug: FullSlug, href: string): string {
  return new URL(href, `https://docwiki.invalid/${slug}`).pathname
}

/** Pathnames already linked from the page body (the sidecar usually links its source page). */
function bodyTargets(slug: FullSlug, tree: unknown): { links: Set<string>; badge: boolean } {
  const links = new Set<string>()
  let badge = false
  visit(tree as Root, "element", (node) => {
    const href = node.properties?.href
    if (node.tagName === "a" && typeof href === "string") links.add(pathOf(slug, href))
    const classes = node.properties?.className
    if (Array.isArray(classes) && classes.includes("docwiki-badge")) badge = true
  })
  return { links, badge }
}

/**
 * Evidence microscope toolbar: provenance, way back to the source page, original document.
 * Items the sidecar body already shows (its `Source page: … · Provenance: …` line) are omitted.
 */
export default (() => {
  const EvidenceHeader: QuartzComponent = ({
    fileData,
    tree,
    displayClass,
  }: QuartzComponentProps) => {
    const frontmatter = fileData.frontmatter
    if (frontmatter?.type !== "evidence" && frontmatter?.type !== "evidence-index") return null
    const slug = fileData.slug as FullSlug
    const t = pageStrings(fileData)
    const sourceId = typeof frontmatter.source_id === "string" ? frontmatter.source_id : ""
    const source = settingsFor(pageLang(fileData)).sources[sourceId]
    const body = bodyTargets(slug, tree)
    const badge =
      typeof frontmatter.provenance === "string" && !body.badge
        ? provenanceBadge(frontmatter.provenance, t)
        : undefined
    const page = pdfPage(frontmatter.locator)
    let sourceHref = source?.page ? resolveRelative(slug, source.page as FullSlug) : undefined
    if (sourceHref && body.links.has(pathOf(slug, sourceHref))) sourceHref = undefined
    let originalHref = source?.original
      ? resolveRelative(slug, source.original as FullSlug)
      : undefined
    if (originalHref && body.links.has(pathOf(slug, originalHref))) originalHref = undefined
    if (!badge && !sourceHref && !originalHref) return null

    return (
      <div class={classNames(displayClass, "docwiki-evidence-header")}>
        {badge && (
          <span class="docwiki-evidence-provenance">
            {t.documents.provenance}{" "}
            <span class={`docwiki-badge docwiki-badge--${badge.kind}`} title={badge.meaning}>
              {badge.text}
            </span>
          </span>
        )}
        {sourceHref && (
          <a class="internal" href={sourceHref}>
            {t.documents.sourcePage(source?.title ?? "")}
          </a>
        )}
        {originalHref && (
          <a
            class="docwiki-original"
            href={originalHref + (page ? `#page=${page}` : "")}
            data-no-popover="true"
            data-router-ignore="true"
          >
            {t.documents.originalDocument(page ?? null)}
          </a>
        )}
      </div>
    )
  }

  return EvidenceHeader
}) satisfies QuartzComponentConstructor
