// "① Documents" (ADR 0010): the register of the release's documents. Each entry gives the type,
// the document number, the revision (indice), the date and whether it is current or replaced,
// and leads to the document itself (its pages and full text, `evidence/<source_id>/`), to the
// original file and to the wiki page compiled from it. Built from docwiki-site.json, so it needs
// no portal. Restricted documents are not in a public release, so they are never listed.
// When the documents have scopes (chantiers, v1.7, ADR 0011), the register is grouped by scope
// (the hub's title), then phase, then type, as computed by src/docwiki/site/register.py.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import {
  DocwikiRegisterGroup,
  DocwikiSource,
  humanDate,
  revisionStatus,
  settings,
} from "./settings"

/** Same slug as `DOCUMENTS_SLUG` in src/docwiki/site/process_page.py. */
const DOCUMENTS_SLUG = "documents"

const FORMATS: Record<string, string> = {
  pdf: "PDF",
  docx: "Word",
  xlsx: "Excel",
  csv: "CSV",
  pptx: "PowerPoint",
  eml: "E-mail",
  jpg: "Photo",
  jpeg: "Photo",
  png: "Image",
  txt: "Text",
  md: "Text",
  vtt: "Transcript",
}

function typeLabel(source: DocwikiSource): string | null {
  const kind = source.docType ? source.docType.replace(/-/g, " ") : null
  const format = source.format ? (FORMATS[source.format] ?? source.format.toUpperCase()) : null
  if (kind && format) return `${kind.charAt(0).toUpperCase()}${kind.slice(1)} · ${format}`
  return kind ?? format
}

function facts(source: DocwikiSource): string[] {
  return [
    typeLabel(source),
    source.docNumber ? `n° ${source.docNumber}` : null,
    source.revision ? `indice ${source.revision}` : null,
    source.lot ? `lot ${source.lot}` : null,
    humanDate(source.date),
  ].filter((item): item is string => item !== null)
}

export default (() => {
  const Documents: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (fileData.slug !== DOCUMENTS_SLUG) return null
    const slug = fileData.slug as FullSlug
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    // By type, then n° and indice (so revisions sit together), then date.
    const key = (source: DocwikiSource) =>
      [source.docType ?? "~", source.docNumber ?? "~", source.revision ?? "", source.date ?? ""]
    const sources = Object.values(settings.sources).sort((a, b) => {
      const [x, y] = [key(a), key(b)]
      for (let i = 0; i < x.length; i++) {
        const order = x[i].localeCompare(y[i])
        if (order !== 0) return order
      }
      return a.title.localeCompare(b.title, "fr")
    })
    const superseded = sources.filter((source) => source.status === "superseded").length
    const asOf = humanDate(settings.releaseDate)
    const register: DocwikiRegisterGroup[] = settings.register ?? []

    const item = (source: DocwikiSource) => {
      const status = revisionStatus(source)
      return (
        <li class="docwiki-documents-item">
          <div class="docwiki-documents-main">
            <span class="docwiki-documents-title">{source.title}</span>
            <span class="docwiki-documents-facts">{facts(source).join(" · ")}</span>
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
                  Download .eml
                </a>
              ) : (
                <a
                  href={link(source.original)}
                  target="_blank"
                  rel="noopener"
                  data-no-popover="true"
                  data-router-ignore="true"
                >
                  Original ↗<span class="sr-only"> (opens in a new tab)</span>
                </a>
              )
            ) : (
              <span
                class="docwiki-documents-none"
                title="Originals are published only for the public fictional sample, and never for a document the safety checks flagged (its full text is shown with the flagged passage withheld)."
              >
                Original not published
              </span>
            )}
            {source.document && <a href={link(source.document)}>View document</a>}
            {source.page && <a href={link(source.page)}>Wiki page</a>}
          </span>
        </li>
      )
    }

    const listed = (ids: string[]) =>
      ids
        .map((id) => settings.sources[id])
        .filter((source): source is DocwikiSource => source !== undefined)

    return (
      <section class={classNames(displayClass, "docwiki-documents")} aria-label="Documents">
        <p class="docwiki-documents-count">
          {sources.length} document{sources.length === 1 ? "" : "s"} in this release
          {superseded > 0 ? ` · ${superseded} superseded by a later indice` : ""}
          {asOf ? ` · as of ${asOf}` : ""}
        </p>
        {register.length > 0 ? (
          register.map((group) => (
            <section class="docwiki-documents-scope" aria-label={group.title}>
              <h2 class="docwiki-documents-scope-title">
                {group.hub ? <a href={link(group.hub)}>{group.title}</a> : group.title}
                <span class="docwiki-documents-scope-count">
                  {` · ${group.count} document${group.count === 1 ? "" : "s"}`}
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
