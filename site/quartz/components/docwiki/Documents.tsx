// "① Documents" (ADR 0010): the register of the release's documents. Each entry gives the type,
// the document number, the revision (indice), the date and whether it is current or replaced,
// and leads to the document itself (its pages and full text, `evidence/<source_id>/`), to the
// original file and to the wiki page compiled from it. Built from docwiki-site.json, so it needs
// no portal. Restricted documents are not in a public release, so they are never listed.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { DocwikiSource, settings } from "./settings"

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

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "medium", timeZone: "UTC" })

function humanDate(iso: string | null | undefined): string | null {
  if (!iso) return null
  const date = new Date(`${iso}T00:00:00Z`)
  return Number.isNaN(date.getTime()) ? null : dateFormat.format(date)
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
    humanDate(source.date),
  ].filter((item): item is string => item !== null)
}

export default (() => {
  const Documents: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (fileData.slug !== DOCUMENTS_SLUG) return null
    const slug = fileData.slug as FullSlug
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const sources = Object.values(settings.sources).sort(
      (a, b) =>
        (a.date ?? "9999").localeCompare(b.date ?? "9999") || a.title.localeCompare(b.title, "fr"),
    )
    const current = sources.filter((source) => source.status !== "superseded").length
    return (
      <section class={classNames(displayClass, "docwiki-documents")} aria-label="Documents">
        <p class="docwiki-documents-count">
          {sources.length} document{sources.length === 1 ? "" : "s"} in this release ·{" "}
          {current} current
          {sources.length > current ? ` · ${sources.length - current} superseded` : ""}
        </p>
        <ol class="docwiki-documents-list">
          {sources.map((source) => {
            const superseded = source.status === "superseded"
            return (
              <li class="docwiki-documents-item">
                <div class="docwiki-documents-main">
                  {source.document ? (
                    <a class="docwiki-documents-title" href={link(source.document)}>
                      {source.title}
                    </a>
                  ) : (
                    <span class="docwiki-documents-title">{source.title}</span>
                  )}
                  <span class="docwiki-documents-facts">{facts(source).join(" · ")}</span>
                </div>
                <span
                  class={`docwiki-status docwiki-status--${superseded ? "superseded" : "in_wiki"}`}
                >
                  <span class="docwiki-status-shape" aria-hidden="true">
                    {superseded ? "◑" : "●"}
                  </span>
                  <span class="docwiki-status-word">
                    {superseded
                      ? source.supersededBy
                        ? `Superseded by ${source.supersededBy}`
                        : "Superseded"
                      : "Current"}
                  </span>
                </span>
                <span class="docwiki-documents-links">
                  {source.document && <a href={link(source.document)}>View</a>}
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
                    <span class="docwiki-documents-none">Original not published</span>
                  )}
                  {source.page && <a href={link(source.page)}>Wiki page</a>}
                </span>
              </li>
            )
          })}
        </ol>
      </section>
    )
  }

  return Documents
}) satisfies QuartzComponentConstructor
