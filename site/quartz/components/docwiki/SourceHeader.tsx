// The header card of a source page (ADR 0010, slice B): what the document is (type, n°, indice,
// date), whether it is current or replaced, and the way to the document itself (its pages and
// full text) and to the original file. Built from the page's frontmatter and docwiki-site.json.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { settings } from "./settings"

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null
}

export default (() => {
  const SourceHeader: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    const frontmatter = fileData.frontmatter
    if (frontmatter?.type !== "source") return null
    const slug = fileData.slug as FullSlug
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const sourceId = text(frontmatter.source_id) ?? ""
    const source = settings.sources[sourceId]
    const superseded = text(frontmatter.status) === "superseded"
    const kind = text(frontmatter.doc_type)?.replace(/-/g, " ")
    const facts = [
      kind ? kind.charAt(0).toUpperCase() + kind.slice(1) : null,
      text(frontmatter.doc_number) ? `n° ${text(frontmatter.doc_number)}` : null,
      text(frontmatter.revision) ? `indice ${text(frontmatter.revision)}` : null,
      source?.date ?? null,
    ].filter((item): item is string => item !== null)
    const status = superseded
      ? source?.supersededBy
        ? `Superseded by ${source.supersededBy}`
        : "Superseded"
      : "Current"
    return (
      <div class={classNames(displayClass, "docwiki-source-header")}>
        <span class={`docwiki-status docwiki-status--${superseded ? "superseded" : "in_wiki"}`}>
          <span class="docwiki-status-shape" aria-hidden="true">
            {superseded ? "◑" : "●"}
          </span>
          <span class="docwiki-status-word">{status}</span>
        </span>
        {facts.length > 0 && <span class="docwiki-source-facts">{facts.join(" · ")}</span>}
        <span class="docwiki-source-links">
          {source?.document && <a href={link(source.document)}>The document</a>}
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
        </span>
      </div>
    )
  }

  return SourceHeader
}) satisfies QuartzComponentConstructor
