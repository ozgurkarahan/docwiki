// The guided tour (site.md §12.2): six steps across the site, started by "Take the 2-minute tour"
// on the home page (Story.tsx). Each step is a small callout anchored to a real element of a real
// page: ① an original on the Documents tab, ② a source page and its evidence links, ③ the live
// pipeline, ④ a topic page's first citation, ⑤ the "Ask this wiki" drawer with the example
// question in its form, ⑥ the evaluation panel of the home page, with links to the quality report
// and the architecture page. The pages are chosen here, at build time, in the page's language (a
// mirror's tour stays in its folder): the first document of the register that has a wiki page,
// and the first topic page by slug; nothing names a sample document. The callout is rendered
// hidden on every page; scripts/tour.inline.ts moves it from step to step.
import { FullSlug, resolveRelative } from "../../util/path"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
// @ts-ignore
import script from "./scripts/tour.inline"
import { ARCHITECTURE_SLUG } from "./Architecture"
import { builtSlugs, inLang, pageBase, pageLang, pageStrings, settingsFor } from "./settings"

/** The first document of the register (its display order) that has a wiki page. */
function firstSourcePage(lang: string): string | null {
  const local = settingsFor(lang)
  const order =
    local.register?.flatMap((group) =>
      group.phases.flatMap((phase) => phase.types.flatMap((type) => type.sources)),
    ) ?? []
  for (const id of [...order, ...Object.keys(local.sources)]) {
    const page = local.sources[id]?.page
    if (page) return page
  }
  return null
}

export default (() => {
  const Tour: QuartzComponent = ({ fileData, allFiles }: QuartzComponentProps) => {
    const slug = fileData.slug as FullSlug
    const lang = pageLang(fileData)
    const t = pageStrings(fileData)
    const local = settingsFor(lang)
    const built = builtSlugs(allFiles)
    const topic =
      allFiles
        .filter(
          (file) =>
            file.frontmatter?.type === "topic" &&
            pageLang(file) === lang &&
            pageBase(file.slug).startsWith("topics/"),
        )
        .map((file) => file.slug as string)
        .sort()[0] ?? null
    const source = firstSourcePage(lang)
    const quality = local.qualityPage
      ? built.has(inLang(local.qualityPage, lang))
        ? inLang(local.qualityPage, lang)
        : local.qualityPage
      : null
    // One page per step, as full content slugs (the client makes them relative).
    const pages = [
      inLang("documents", lang),
      source,
      inLang("pipeline", lang),
      topic,
      topic,
      inLang("index", lang),
    ]
    const href = (target: string) => resolveRelative(slug, target as FullSlug)
    return (
      <>
        <div
          class="docwiki-tour"
          role="dialog"
          aria-modal="false"
          aria-labelledby="docwiki-tour-title"
          aria-describedby="docwiki-tour-body"
          data-pages={JSON.stringify(pages)}
          data-question={t.ask.examples[0] ?? ""}
          hidden
        >
          <p class="docwiki-tour-count" aria-hidden="true"></p>
          <h2 id="docwiki-tour-title" class="docwiki-tour-title" tabIndex={-1}></h2>
          <p id="docwiki-tour-body" class="docwiki-tour-body"></p>
          <p class="docwiki-tour-links" hidden>
            {quality && <a href={href(quality)}>{t.tour.qualityReport}</a>}
            <a href={href(inLang(ARCHITECTURE_SLUG, lang))}>{t.tour.architecture}</a>
          </p>
          <div class="docwiki-tour-actions">
            <button type="button" class="docwiki-tour-back">
              {t.tour.back}
            </button>
            <button type="button" class="docwiki-tour-next">
              {t.tour.next}
            </button>
          </div>
          <button type="button" class="docwiki-tour-close" aria-label={t.tour.close}>
            <span aria-hidden="true">×</span>
          </button>
        </div>
        <p class="docwiki-tour-live sr-only" role="status" aria-live="polite"></p>
      </>
    )
  }

  Tour.afterDOMLoaded = script

  return Tour
}) satisfies QuartzComponentConstructor
