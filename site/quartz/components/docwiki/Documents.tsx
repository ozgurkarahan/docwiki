// "① Documents" (ADR 0010): the register of the release's documents. Each entry gives the type,
// the document number, the revision (indice), the date and whether it is current or replaced,
// and leads to the document itself (its pages and full text, `evidence/<source_id>/`), to the
// original file and to the wiki page compiled from it. Built from docwiki-site.json, so it needs
// no portal. Restricted documents are not in a public release, so they are never listed.
// When the documents have scopes (chantiers, v1.7, ADR 0011), the register is grouped by scope
// (the hub's title), then phase, then type, as computed by src/docwiki/site/register.py. Every
// language has the page (`documents`, `en/documents`), in its words and with its wiki pages.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import type { Strings } from "./i18n"
import {
  DocwikiRegisterGroup,
  DocwikiSource,
  docTypeName,
  humanDate,
  pageBase,
  pageLang,
  pageStrings,
  revisionStatus,
  settings,
  settingsFor,
} from "./settings"

/** Same slug as `DOCUMENTS_SLUG` in src/docwiki/site/process_page.py. */
const DOCUMENTS_SLUG = "documents"

function typeLabel(source: DocwikiSource, t: Strings): string | null {
  const kind = docTypeName(source.docType, source.docTypeLabel)
  const formats = t.documents.formats
  const format = source.format ? (formats[source.format] ?? source.format.toUpperCase()) : null
  if (kind && format) return `${kind} · ${format}`
  return kind ?? format
}

function facts(source: DocwikiSource, t: Strings): string[] {
  const words = t.documents
  return [
    typeLabel(source, t),
    source.docNumber ? words.number(source.docNumber) : null,
    source.revision ? words.revision(source.revision) : null,
    source.lot ? words.lot(source.lot) : null,
    humanDate(source.date, t),
  ].filter((item): item is string => item !== null)
}

export default (() => {
  const Documents: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (pageBase(fileData.slug) !== DOCUMENTS_SLUG) return null
    const slug = fileData.slug as FullSlug
    const t = pageStrings(fileData)
    const words = t.documents
    const local = settingsFor(pageLang(fileData))
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    // By type, then n° and indice (so revisions sit together), then date.
    const key = (source: DocwikiSource) =>
      [source.docType ?? "~", source.docNumber ?? "~", source.revision ?? "", source.date ?? ""]
    const sources = Object.values(local.sources).sort((a, b) => {
      const [x, y] = [key(a), key(b)]
      for (let i = 0; i < x.length; i++) {
        const order = x[i].localeCompare(y[i])
        if (order !== 0) return order
      }
      return a.title.localeCompare(b.title, "fr")
    })
    const superseded = sources.filter((source) => source.status === "superseded").length
    const asOf = humanDate(settings.releaseDate, t)
    const register: DocwikiRegisterGroup[] = local.register ?? []

    const item = (source: DocwikiSource) => {
      const status = revisionStatus(source, t)
      return (
        <li class="docwiki-documents-item">
          <div class="docwiki-documents-main">
            <span class="docwiki-documents-title">{source.title}</span>
            <span class="docwiki-documents-facts">{facts(source, t).join(" · ")}</span>
          </div>
          {status && (
            <span class={`docwiki-status docwiki-status--${status.state}`} title={status.title}>
              <span class="docwiki-status-shape" aria-hidden="true">
                {status.state === "superseded" ? "◑" : "●"}
              </span>
              <span class="docwiki-status-word">{status.words}</span>
            </span>
          )}
          <span class="docwiki-documents-links">
            {source.original ? (
              source.format === "eml" ? (
                <a
                  href={link(source.original)}
                  download
                  data-no-popover="true"
                  data-router-ignore="true"
                >
                  {words.downloadEml}
                </a>
              ) : (
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
              )
            ) : (
              <span class="docwiki-documents-none" title={words.notPublishedTitle}>
                {words.notPublished}
              </span>
            )}
            {source.document && <a href={link(source.document)}>{words.viewDocument}</a>}
            {source.page && <a href={link(source.page)}>{words.wikiPage}</a>}
          </span>
        </li>
      )
    }

    const listed = (ids: string[]) =>
      ids
        .map((id) => local.sources[id])
        .filter((source): source is DocwikiSource => source !== undefined)

    return (
      <section
        class={classNames(displayClass, "docwiki-documents")}
        aria-label={words.sectionLabel}
      >
        <p class="docwiki-documents-count">
          {words.inRelease(sources.length)}
          {superseded > 0 ? ` · ${words.supersededLater(superseded)}` : ""}
          {asOf ? ` · ${words.asOf(asOf)}` : ""}
        </p>
        {register.length > 0 ? (
          register.map((group) => (
            <section class="docwiki-documents-scope" aria-label={group.title}>
              <h2 class="docwiki-documents-scope-title">
                {group.hub ? <a href={link(group.hub)}>{group.title}</a> : group.title}
                <span class="docwiki-documents-scope-count">
                  {` · ${t.words.documents(group.count)}`}
                </span>
              </h2>
              {group.phases.map((phase) => (
                <div class="docwiki-documents-phase">
                  <h3 class="docwiki-documents-phase-title">{phase.title}</h3>
                  {phase.types.map((type) => (
                    <div class="docwiki-documents-type">
                      <h4 class="docwiki-documents-type-title">{type.title}</h4>
                      <ol class="docwiki-documents-list">{listed(type.sources).map(item)}</ol>
                    </div>
                  ))}
                </div>
              ))}
            </section>
          ))
        ) : (
          <ol class="docwiki-documents-list">{sources.map(item)}</ol>
        )}
      </section>
    )
  }

  return Documents
}) satisfies QuartzComponentConstructor
