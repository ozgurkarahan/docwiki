// The header card of a source page (ADR 0010, slice B): what the document is (type, n°, indice,
// date), whether it is current or replaced, and the way to the document itself (its pages and
// full text) and to the original file. Built from the page's frontmatter and docwiki-site.json,
// in the page's language (a mirror's source page links its own wiki page; documents are shared).
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import {
  docTypeName,
  humanDate,
  pageLang,
  pageStrings,
  revisionStatus,
  settingsFor,
} from "./settings"

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null
}

export default (() => {
  const SourceHeader: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    const frontmatter = fileData.frontmatter
    const onDocument = frontmatter?.type === "evidence-index"
    if (frontmatter?.type !== "source" && !onDocument) return null
    const slug = fileData.slug as FullSlug
    const t = pageStrings(fileData)
    const words = t.documents
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const sourceId = text(frontmatter.source_id) ?? ""
    const source = settingsFor(pageLang(fileData)).sources[sourceId]
    const kind = docTypeName(
      text(frontmatter.doc_type) ?? source?.docType,
      text(frontmatter.doc_type_label) ?? source?.docTypeLabel,
    )
    const dated = humanDate(source?.date, t)
    const facts = [
      kind,
      source?.docNumber ? words.number(source.docNumber) : null,
      source?.revision ? words.revision(source.revision) : null,
      dated ? words.dated(dated) : null,
    ].filter((item): item is string => item !== null)
    const status = revisionStatus(source, t)
    const updated = frontmatter.updated as unknown
    const added = humanDate(
      updated instanceof Date ? updated.toISOString() : (text(updated) ?? undefined),
      t,
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
          <span class="docwiki-source-added">{words.pageCompiled(added)}</span>
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
              {words.original}
              <span class="sr-only">{t.a11y.newTab}</span>
            </a>
          )}
          {onDocument
            ? source?.page && <a href={link(source.page)}>{words.wikiPage}</a>
            : source?.document && <a href={link(source.document)}>{words.viewDocument}</a>}
        </span>
      </div>
    )
  }

  return SourceHeader
}) satisfies QuartzComponentConstructor
