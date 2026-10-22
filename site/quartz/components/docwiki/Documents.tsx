// "① Documents" (ADR 0010): the documents of the release, each with its original and the wiki
// page compiled from it. Built from docwiki-site.json, so it needs no portal. The register (n°,
// indice, date, issuer, status) and the viewer come in a later slice.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { settings } from "./settings"

/** Same slug as `DOCUMENTS_SLUG` in src/docwiki/site/process_page.py. */
const DOCUMENTS_SLUG = "documents"

export default (() => {
  const Documents: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (fileData.slug !== DOCUMENTS_SLUG) return null
    const slug = fileData.slug as FullSlug
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const sources = Object.values(settings.sources).sort((a, b) =>
      a.title.localeCompare(b.title, "fr"),
    )
    return (
      <section class={classNames(displayClass, "docwiki-documents")} aria-label="Documents">
        <p class="docwiki-documents-count">
          {sources.length} document{sources.length === 1 ? "" : "s"} in this release
        </p>
        <ul class="docwiki-documents-list">
          {sources.map((source) => (
            <li class="docwiki-documents-item">
              <span class="docwiki-documents-title">
                {source.title}
              </span>
              {source.status === "superseded" && (
                <span class="docwiki-status docwiki-status--superseded">
                  <span class="docwiki-status-shape" aria-hidden="true">
                    ◑
                  </span>
                  <span class="docwiki-status-word">Superseded</span>
                </span>
              )}
              <span class="docwiki-documents-links">
                {source.original && (
                  <a href={link(source.original)} target="_blank" rel="noopener">
                    Original ↗<span class="sr-only"> (opens in a new tab)</span>
                  </a>
                )}
                {source.page && <a href={link(source.page)}>Wiki page</a>}
              </span>
            </li>
          ))}
        </ul>
      </section>
    )
  }

  return Documents
}) satisfies QuartzComponentConstructor
