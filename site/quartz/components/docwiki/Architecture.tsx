// The architecture page (site.md §12.3): its text is static (docwiki.site.process_page); this
// component shows the diagram above it, docs/assets/architecture.svg copied by the site build to
// quartz/static/docwiki/ (`settings.architecture`). Without the diagram the page keeps its text.
// Every language's architecture page has it.
import { FullSlug, joinSegments, pathToRoot } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { pageBase, pageStrings, settings } from "./settings"

/** Same slug as `ARCHITECTURE_SLUG` in src/docwiki/site/process_page.py. */
export const ARCHITECTURE_SLUG = "architecture"

export default (() => {
  const Architecture: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (pageBase(fileData.slug) !== ARCHITECTURE_SLUG || !settings.architecture) return null
    const t = pageStrings(fileData).architecture
    const src = joinSegments(pathToRoot(fileData.slug as FullSlug), settings.architecture)
    return (
      <figure
        class={classNames(displayClass, "docwiki-architecture")}
        aria-label={t.figureLabel}
      >
        <a
          href={src}
          target="_blank"
          rel="noopener"
          data-no-popover="true"
          data-router-ignore="true"
          class="docwiki-architecture-link"
        >
          {/* The SVG carries its own title and description (role="img"). */}
          <img src={src} alt={t.figureLabel} width={1280} height={690} loading="lazy" />
          <span class="sr-only">{t.openFull}</span>
        </a>
        <figcaption>{t.caption}</figcaption>
      </figure>
    )
  }

  return Architecture
}) satisfies QuartzComponentConstructor
