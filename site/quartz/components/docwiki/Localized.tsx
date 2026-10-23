// Quartz's own components (search, theme and reader-mode buttons, table of contents, backlinks,
// graph, dates and reading time, folder and tag listings) take their words and date format from
// `cfg.locale`, which is one value for the whole site. Wrapped in `Localized`, a component gets
// the locale of its page's language instead (ADR 0012: French at the root, English under `en/`),
// and the few words Quartz writes in English whatever the locale (the search icon's `<title>`, the
// global graph button's name) or capitalises in French are corrected in what it renders.
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import type { Strings } from "./i18n"
import { pageStrings } from "./settings"

/** Quartz's French locale capitalises like English titles. */
const TEXT_FIXES: Record<string, Record<string, string>> = {
  fr: { "Table des Matières": "Table des matières", "Vue Graphique": "Vue graphique" },
}

type VNodeLike = { type?: unknown; props?: Record<string, unknown> }

function isTitle(child: unknown, words: string): boolean {
  const node = child as VNodeLike
  return node?.type === "title" && [node.props?.children].flat().join("") === words
}

/** Corrects a rendered tree in place (elements only: nested components render themselves). */
function localize(node: unknown, t: Strings): unknown {
  if (Array.isArray(node)) return node.map((child) => localize(child, t))
  if (typeof node === "string") return TEXT_FIXES[t.lang]?.[node] ?? node
  const vnode = node as VNodeLike
  if (!vnode || typeof vnode !== "object" || !vnode.props) return node
  const props = vnode.props
  if (props["aria-label"] === "Global Graph") props["aria-label"] = t.wiki.globalGraph
  const children = props.children
  // The search button's icon is named "Search" beside the localized word: decorative instead.
  if (vnode.type === "svg" && [children].flat().some((child) => isTitle(child, "Search"))) {
    props.children = [children].flat().filter((child) => !isTitle(child, "Search"))
    delete props.role
    props["aria-hidden"] = "true"
    return node
  }
  if (children !== undefined) props.children = localize(children, t)
  return node
}

export default ((Inner: QuartzComponent) => {
  const Localized: QuartzComponent = (props: QuartzComponentProps) => {
    const t = pageStrings(props.fileData)
    const cfg = t.locale === props.cfg.locale ? props.cfg : { ...props.cfg, locale: t.locale }
    return localize(Inner({ ...props, cfg }), t) as ReturnType<QuartzComponent>
  }

  Localized.css = Inner.css
  Localized.beforeDOMLoaded = Inner.beforeDOMLoaded
  Localized.afterDOMLoaded = Inner.afterDOMLoaded

  return Localized
}) satisfies QuartzComponentConstructor<QuartzComponent>
