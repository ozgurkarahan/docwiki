// DocWiki layout (copied over the pinned Quartz checkout by docwiki.site.build_site).
import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"
import * as DocWiki from "./quartz/components/docwiki"

// No graph on the Documents and Pipeline tabs (ADR 0010): it has nothing to show there.
const graph = Component.ConditionalRender({
  component: Component.Graph({
    localGraph: { showTags: false, depth: 1 },
    globalGraph: { showTags: false },
  }),
  condition: ({ fileData }) => fileData.slug !== "documents" && fileData.slug !== "pipeline",
})

const explorer = Component.Explorer({
  title: "Browse",
  // Evidence sidecars are reached from footnotes; tag pages from the tag list; Documents and
  // Pipeline from the tabs.
  filterFn: (node) =>
    !["tags", "evidence", "documents", "pipeline"].includes(node.slugSegment ?? ""),
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
  // ① Documents · ② Pipeline · ③ Wiki, the pipeline's status chip and Sign in (ADR 0010).
  header: [DocWiki.Tabs(), DocWiki.Banner()],
  // The documents page only: the release's documents. The pipeline page only: documents, queue
  // and runs, live from the portal, after the text. "Ask this wiki": the drawer on every page.
  afterBody: [DocWiki.Documents(), DocWiki.Process(), DocWiki.AskPanel()],
  footer: DocWiki.Footer(),
}

// Dates and reading time mean nothing on the Documents and Pipeline tabs, and on a source or
// document page the compile date would read as the document's own date (its card has that).
const contentMeta = Component.ConditionalRender({
  component: Component.ContentMeta(),
  condition: ({ fileData }) =>
    fileData.slug !== "documents" &&
    fileData.slug !== "pipeline" &&
    fileData.frontmatter?.type !== "source" &&
    fileData.frontmatter?.type !== "evidence-index",
})

export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    DocWiki.Breadcrumbs({ rootName: "Wiki" }),
    Component.ArticleTitle(),
    contentMeta,
    // The pipeline page only: the owner's sign-in and upload form, before the text.
    DocWiki.OwnerBox(),
    // Home page only: the story (the pattern in one sentence, documents → pipeline → cited
    // wiki, a question to try), then how the release was built and a collapsible "About DocWiki".
    DocWiki.Story(),
    DocWiki.About(),
    DocWiki.EvidenceHeader(),
    // Source pages: type, n°, indice, date, current or replaced, the document and the original.
    DocWiki.SourceHeader(),
    Component.TagList(),
  ],
  left: [Component.PageTitle(), Component.MobileOnly(Component.Spacer()), toolbar, explorer],
  right: [graph, Component.DesktopOnly(Component.TableOfContents()), Component.Backlinks()],
}

export const defaultListPageLayout: PageLayout = {
  beforeBody: [
    DocWiki.Breadcrumbs({ rootName: "Wiki" }),
    Component.ArticleTitle(),
    contentMeta,
    // A document page (evidence/<source_id>/index) is a folder page for Quartz: same card.
    DocWiki.SourceHeader(),
  ],
  left: [Component.PageTitle(), Component.MobileOnly(Component.Spacer()), toolbar, explorer],
  right: [],
}
