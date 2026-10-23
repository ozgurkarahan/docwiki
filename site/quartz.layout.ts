// DocWiki layout (copied over the pinned Quartz checkout by docwiki.site.build_site).
import { PageLayout, SharedLayout } from "./quartz/cfg"
import * as Component from "./quartz/components"
import * as DocWiki from "./quartz/components/docwiki"
import { stringsFor } from "./quartz/components/docwiki/i18n"
import {
  canonicalLang,
  languages,
  mirrorLangs,
  pageBase,
  pageLang,
  settingsFor,
} from "./quartz/components/docwiki/settings"

// Every page is in one language (ADR 0012): French at the root, English under `en/`. Quartz's own
// components take that language's words through DocWiki.Localized.
const L = DocWiki.Localized

// No graph on the Documents and Pipeline tabs (ADR 0010), nor on the home page: it has nothing
// useful to show there (newcomers read it as broken).
const graph = Component.ConditionalRender({
  component: L(
    Component.Graph({
      localGraph: { showTags: false, depth: 1 },
      globalGraph: { showTags: false },
    }),
  ),
  condition: ({ fileData }) => !["documents", "pipeline", "index"].includes(pageBase(fileData.slug)),
})

type ExplorerOptions = NonNullable<Parameters<typeof Component.Explorer>[0]>

/**
 * The explorer of one language. Quartz runs the explorer's functions in the browser from their
 * source text (toString()), so a value they need is written into that text: the hub folders
 * (v1.7, ADR 0011), the name of the `entities` folder when the wiki has scopes ("Entreprise"),
 * the per-scope topic folders' titles, and the language's folder. The canonical explorer never
 * lists a mirror's folder; a mirror's explorer lists only its folder, with the same grouping.
 */
function explorerFor(lang: string) {
  const local = settingsFor(lang)
  const prefix = lang === canonicalLang ? "" : `${lang}/`
  const hubFolders = JSON.stringify(local.explorer?.hubFolders ?? [])
  const entitiesTitle = JSON.stringify(local.explorer?.entitiesTitle ?? null)
  const folderTitles = JSON.stringify(local.explorer?.folderTitles ?? {})
  const mirrors = JSON.stringify(prefix ? [] : mirrorLangs)
  const root = JSON.stringify(prefix ? lang : null)
  const at = JSON.stringify(prefix)
  return Component.Explorer({
    title: stringsFor(lang).wiki.explorerTitle,
    // Evidence sidecars are reached from footnotes; tag pages from the tag list; Documents and
    // Pipeline from the tabs; the other languages from the switch.
    filterFn: new Function(
      "node",
      `const mirrors = ${mirrors}
      if (mirrors.includes(node.slugSegment) && node.slug.split("/").length === 2) return false
      return !["tags", "evidence", "documents", "pipeline"].includes(node.slugSegment ?? "")`,
    ) as ExplorerOptions["filterFn"],
    // A mirror's folder becomes the explorer's root. Folders without an index page show their
    // path segment: `_meta` → "Meta", `queries` → "Queries". With scopes, `entities` shows as the
    // default scope ("Entreprise"); its pages keep their paths. Per-scope topic folders show
    // their scope's name ("topics/moreau" → "Chantier Moreau").
    mapFn: new Function(
      "node",
      `const root = ${root}
      if (root && node.isFolder && node.slug === "index") {
        const mirror = node.children.find((child) => child.slugSegment === root)
        node.children = mirror ? mirror.children : []
      }
      if (node.isFolder && node.data === null) {
        const name = node.displayName.replace(/^_+/, "")
        node.displayName = name.charAt(0).toUpperCase() + name.slice(1)
      }
      const at = ${at}
      const entitiesTitle = ${entitiesTitle}
      if (entitiesTitle && node.isFolder && node.slug === at + "entities/index") {
        node.displayName = entitiesTitle
      }
      const folderTitles = ${folderTitles}
      const folder = node.isFolder ? node.slug.replace(/\\/index$/, "").slice(at.length) : null
      if (folder && Object.prototype.hasOwnProperty.call(folderTitles, folder)) {
        node.displayName = folderTitles[folder]
      }`,
    ) as ExplorerOptions["mapFn"],
    // Top level: the hub folders ("Chantiers"), entities, sources, topics, then the rest (folders
    // before files, by name).
    sortFn: new Function(
      "a",
      "b",
      `const hubs = ${hubFolders}
      const at = ${at}
      const rank = (node) => {
        const rel = node.slug.startsWith(at) ? node.slug.slice(at.length) : node.slug
        if (!node.isFolder || rel.split("/").length !== 2) return 4
        if (hubs.includes(node.slugSegment)) return 0
        const fixed = ["entities", "sources", "topics"].indexOf(node.slugSegment)
        return fixed === -1 ? 4 : fixed + 1
      }
      const order = rank(a) - rank(b)
      if (order !== 0) return order
      if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1
      return a.displayName.localeCompare(b.displayName, undefined, {
        numeric: true,
        sensitivity: "base",
      })`,
    ) as ExplorerOptions["sortFn"],
  })
}

// One explorer per language; a page shows the one of its language.
const explorers = languages.map((lang) => {
  const explorer = explorerFor(lang)
  return languages.length === 1
    ? explorer
    : Component.ConditionalRender({
        component: explorer,
        condition: ({ fileData }) => pageLang(fileData) === lang,
      })
})

const toolbar = L(
  Component.Flex({
    components: [
      // Each one wrapped as well: Localized corrects what a component renders itself.
      { Component: L(Component.Search()), grow: true },
      { Component: L(Component.Darkmode()) },
      { Component: L(Component.ReaderMode()) },
    ],
  }),
)

// "Skip to content", the first focusable element of every page; it leads to the page title
// (DocWiki.ArticleTitle carries its target) and its script corrects Quartz's own markup (slice H).
const skipLink = DocWiki.SkipLink()

export const sharedPageComponents: SharedLayout = {
  head: DocWiki.Head(),
  // ① Documents · ② Pipeline · ③ Wiki, the pipeline's status chip, Sign in and the language
  // switch (ADR 0010, 0012).
  header: [DocWiki.Tabs(), DocWiki.Banner()],
  // The documents page only: the release's documents. The pipeline page only: documents, queue
  // and runs, live from the portal, after the text. "Ask this wiki": the drawer on every page.
  afterBody: [DocWiki.Documents(), DocWiki.Process(), DocWiki.AskPanel()],
  footer: DocWiki.Footer(),
}

// Dates and reading time mean nothing on the Documents and Pipeline tabs, and on a source or
// document page the compile date would read as the document's own date (its card has that).
const contentMeta = Component.ConditionalRender({
  component: L(Component.ContentMeta()),
  condition: ({ fileData }) =>
    pageBase(fileData.slug) !== "documents" &&
    pageBase(fileData.slug) !== "pipeline" &&
    fileData.frontmatter?.type !== "source" &&
    fileData.frontmatter?.type !== "evidence-index",
})

const left = [
  skipLink,
  DocWiki.PageTitle(),
  Component.MobileOnly(Component.Spacer()),
  toolbar,
  ...explorers,
]

export const defaultContentPageLayout: PageLayout = {
  beforeBody: [
    DocWiki.Breadcrumbs(),
    DocWiki.ArticleTitle(),
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
    L(Component.TagList()),
  ],
  left,
  right: [
    graph,
    Component.DesktopOnly(L(Component.TableOfContents())),
    L(Component.Backlinks()),
  ],
}

// A mirror's home (`en/index`) is a folder page for Quartz: it gets what the home page has (the
// story, "About this wiki", the table of contents and backlinks); other folder pages do not.
const mirrorHome = ({ fileData }: { fileData: { slug?: string } }) =>
  fileData.slug !== "index" && pageBase(fileData.slug) === "index"

export const defaultListPageLayout: PageLayout = {
  beforeBody: [
    DocWiki.Breadcrumbs(),
    DocWiki.ArticleTitle(),
    contentMeta,
    DocWiki.Story(),
    DocWiki.About(),
    // A document page (evidence/<source_id>/index) is a folder page for Quartz: same card.
    DocWiki.SourceHeader(),
  ],
  left,
  right: [
    Component.ConditionalRender({
      component: Component.DesktopOnly(L(Component.TableOfContents())),
      condition: mirrorHome,
    }),
    Component.ConditionalRender({ component: L(Component.Backlinks()), condition: mirrorHome }),
  ],
}
