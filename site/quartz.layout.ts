// DocWiki layout (copied over the pinned Quartz checkout by docwiki.site.build_site).
import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"
import * as DocWiki from "./quartz/components/docwiki"

const graph = Component.Graph({
  localGraph: { showTags: false, depth: 1 },
  globalGraph: { showTags: false },
})

const explorer = Component.Explorer({
  title: "Browse",
  // Evidence sidecars are reached from footnotes; tag pages from the tag list.
  filterFn: (node) => node.slugSegment !== "tags" && node.slugSegment !== "evidence",
  // Folders without an index page show their path segment: `_meta` → "Meta", `queries` → "Queries".
  mapFn: (node) => {
    if (node.isFolder && node.data === null) {
      const name = node.displayName.replace(/^_+/, "")
      node.displayName = name.charAt(0).toUpperCase() + name.slice(1)
    }
  },
})

const toolbar = Component.Flex({
  components: [
    { Component: Component.Search(), grow: true },
    { Component: Component.Darkmode() },
    { Component: Component.ReaderMode() },
  ],
})

export const sharedPageComponents: SharedLayout = {
  head: DocWiki.Head(),
  header: [DocWiki.Banner()],
  // The how-it-works page only: documents, queue and runs, live from the portal, after the text.
  // "Ask this wiki": filed research answers in a drawer on every page (none without answers).
  afterBody: [DocWiki.Process(), DocWiki.AskPanel()],
  footer: DocWiki.Footer(),
}

export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    DocWiki.Breadcrumbs(),
    Component.ArticleTitle(),
    Component.ContentMeta(),
    // Home page only: how the release was built, then a collapsible "About DocWiki".
    DocWiki.About(),
    DocWiki.EvidenceHeader(),
    Component.TagList(),
  ],
  left: [Component.PageTitle(), Component.MobileOnly(Component.Spacer()), toolbar, explorer],
  right: [graph, Component.DesktopOnly(Component.TableOfContents()), Component.Backlinks()],
}

export const defaultListPageLayout: PageLayout = {
  beforeBody: [DocWiki.Breadcrumbs(), Component.ArticleTitle(), Component.ContentMeta()],
  left: [Component.PageTitle(), Component.MobileOnly(Component.Spacer()), toolbar, explorer],
  right: [],
}
