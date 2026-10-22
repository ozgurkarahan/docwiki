// The header card of a source page (ADR 0010, slice B): what the document is (type, n°, indice,
// date), whether it is current or replaced, and the way to the document itself (its pages and
// full text) and to the original file. Built from the page's frontmatter and docwiki-site.json.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { humanDate, revisionStatus, settings } from "./settings"

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null
}

export default (() => {
  const SourceHeader: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    const frontmatter = fileData.frontmatter
    const onDocument = frontmatter?.type === "evidence-index"
    if (frontmatter?.type !== "source" && !onDocument) return null
    const slug = fileData.slug as FullSlug
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const sourceId = text(frontmatter.source_id) ?? ""
    const source = settings.sources[sourceId]
    const kind = (text(frontmatter.doc_type) ?? source?.docType ?? null)?.replace(/-/g, " ")
    const dated = humanDate(source?.date)
    const facts = [
      kind ? kind.charAt(0).toUpperCase() + kind.slice(1) : null,
      source?.docNumber ? `n° ${source.docNumber}` : null,
      source?.revision ? `indice ${source.revision}` : null,
      dated ? `dated ${dated}` : null,
    ].filter((item): item is string => item !== null)
    const status = revisionStatus(source)
    const updated = frontmatter.updated as unknown
    const added = humanDate(
      updated instanceof Date ? updated.toISOString() : (text(updated) ?? undefined),
    )
    return (
      <div class={classNames(displayClass, "docwiki-source-header")}>
        {status && (
          <span class={`docwiki-status docwiki-status--${status.state}`} title={status.title}>
            <span class="docwiki-status-shape" aria-hidden="true">
              {status.state === "superseded" ? "◑" : "●"}
            </span>
            <span class="docwiki-status-word">{status.words}</span>
          </span>
        )}
        {facts.length > 0 && <span class="docwiki-source-facts">{facts.join(" · ")}</span>}
        {added && !onDocument && (
          <span class="docwiki-source-added">Page compiled {added}</span>
        )}
        <span class="docwiki-source-links">
          {source?.original && (
            <a
              href={link(source.original)}
              target="_blank"
              rel="noopener"
              data-no-popover="true"
              data-router-ignore="true"
            >
              Original ↗<span class="sr-only"> (opens in a new tab)</span>
            </a>
          )}
          {onDocument
            ? source?.page && <a href={link(source.page)}>Wiki page</a>
            : source?.document && <a href={link(source.document)}>View document</a>}
        </span>
      </div>
    )
  }

  return SourceHeader
}) satisfies QuartzComponentConstructor
