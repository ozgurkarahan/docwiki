// The body of Quartz's folder pages. Quartz renders every `<folder>/index` as a folder page: a
// mirror's home (`en/index`, ADR 0012) is one too, but it must read like the canonical home page
// (`index`, a content page): its text only, without the listing of the folder's pages. Other
// folder pages keep Quartz's listing, in their page's language (DocWiki.Localized).
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { pageBase } from "./settings"

export default ((parts: { home: QuartzComponent; folder: QuartzComponent }) => {
  const { home: Home, folder: Folder } = parts
  const FolderBody: QuartzComponent = (props: QuartzComponentProps) => {
    const slug = props.fileData.slug ?? "index"
    return slug !== "index" && pageBase(slug) === "index" ? <Home {...props} /> : <Folder {...props} />
  }

  const both = (key: "css" | "beforeDOMLoaded" | "afterDOMLoaded") => {
    const found = [Home[key], Folder[key]].flat().filter((item): item is string => !!item)
    return found.length > 0 ? found : undefined
  }
  FolderBody.css = both("css")
  FolderBody.beforeDOMLoaded = both("beforeDOMLoaded")
  FolderBody.afterDOMLoaded = both("afterDOMLoaded")

  return FolderBody
}) satisfies QuartzComponentConstructor<{ home: QuartzComponent; folder: QuartzComponent }>
