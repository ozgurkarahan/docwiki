// Quartz's own components (search, theme and reader-mode buttons, table of contents, backlinks,
// graph, dates and reading time, folder and tag listings) take their words and date format from
// `cfg.locale`, which is one value for the whole site. Wrapped in `Localized`, a component gets
// the locale of its page's language instead (ADR 0012: French at the root, English under `en/`).
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { pageStrings } from "./settings"

export default ((Inner: QuartzComponent) => {
  const Localized: QuartzComponent = (props: QuartzComponentProps) => {
    const locale = pageStrings(props.fileData).locale
    const cfg = locale === props.cfg.locale ? props.cfg : { ...props.cfg, locale }
    return <Inner {...props} cfg={cfg} />
  }

  Localized.css = Inner.css
  Localized.beforeDOMLoaded = Inner.beforeDOMLoaded
  Localized.afterDOMLoaded = Inner.afterDOMLoaded

  return Localized
}) satisfies QuartzComponentConstructor<QuartzComponent>
