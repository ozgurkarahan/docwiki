import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { en } from "./i18n/en.ts"
import { pageStrings, settings } from "./settings"

/**
 * Site-wide "fictional sample" notice, shown when the release or domain pack asks for one. The
 * default notice is said in the page's language; a custom one is shown as written.
 */
export default (() => {
  const Banner: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (!settings.banner) return null
    const t = pageStrings(fileData)
    const text = settings.banner === en.wiki.bannerText ? t.wiki.bannerText : settings.banner
    return (
      <div class={classNames(displayClass, "docwiki-banner")} role="note">
        <span class="docwiki-banner-label">{t.wiki.bannerLabel}</span>{" "}
        <span class="docwiki-banner-text">{text}</span>
      </div>
    )
  }

  return Banner
}) satisfies QuartzComponentConstructor
