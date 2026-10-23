// The site's title above the explorer, as Quartz's PageTitle, in the page's language: a mirror
// page (`en/…`) shows the mirror's home title and links to its home (ADR 0012).
import { FullSlug, pathToRoot, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { canonicalLang, inLang, pageLang, settingsFor } from "./settings"

export default (() => {
  const PageTitle: QuartzComponent = ({ fileData, cfg, displayClass }: QuartzComponentProps) => {
    const lang = pageLang(fileData)
    const slug = (fileData.slug ?? "index") as FullSlug
    const canonical = lang === canonicalLang
    const title = canonical ? cfg.pageTitle : settingsFor(lang).pageTitle
    const home = canonical
      ? pathToRoot(slug)
      : resolveRelative(slug, inLang("index", lang) as FullSlug)
    return (
      <h2 class={classNames(displayClass, "page-title")}>
        <a href={home}>{title}</a>
      </h2>
    )
  }

  PageTitle.css = `
.page-title {
  font-size: 1.75rem;
  margin: 0;
  font-family: var(--titleFont);
}
`

  return PageTitle
}) satisfies QuartzComponentConstructor
