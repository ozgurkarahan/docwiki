// DocWiki Quartz configuration (copied over the pinned Quartz checkout by docwiki.site.build_site).
// docwiki-site.json is generated per build from the release (title, base URL, banner, sources).
import { QuartzConfig } from "./quartz/cfg"
import * as Plugin from "./quartz/plugins"
import { DocWiki } from "./quartz/plugins/transformers/docwiki"
import { settings } from "./quartz/components/docwiki/settings"

const config: QuartzConfig = {
  configuration: {
    pageTitle: settings.pageTitle,
    pageTitleSuffix: "",
    enableSPA: true,
    enablePopovers: true,
    analytics: null,
    locale: "en-US",
    baseUrl: settings.baseUrl ?? undefined,
    ignorePatterns: [],
    defaultDateType: "modified",
    theme: {
      // No web fonts are downloaded: custom.scss sets system font stacks.
      fontOrigin: "local",
      cdnCaching: false,
      typography: {
        header: "system-ui",
        body: "system-ui",
        code: "ui-monospace",
      },
      colors: {
        lightMode: {
          light: "#f7f6f2",
          lightgray: "#e2e0d8",
          // 4.5:1 on the page, its surface and the highlight tint (slice H).
          gray: "#666560",
          darkgray: "#363732",
          dark: "#22231f",
          secondary: "#3c6250",
          tertiary: "#496955",
          highlight: "rgba(60, 98, 80, 0.10)",
          textHighlight: "#ecdf9c99",
        },
        darkMode: {
          light: "#181a17",
          lightgray: "#30332e",
          gray: "#9a9c92",
          darkgray: "#d6d6ce",
          dark: "#eeede6",
          secondary: "#9ec3ad",
          tertiary: "#b9cfa9",
          highlight: "rgba(158, 195, 173, 0.12)",
          textHighlight: "#7a6f3a88",
        },
      },
    },
  },
  plugins: {
    transformers: [
      Plugin.FrontMatter(),
      Plugin.CreatedModifiedDate({ priority: ["frontmatter"] }),
      DocWiki({
        releaseDate: settings.releaseDate,
        siteBanner: !!settings.banner,
        sourceLangs: Object.fromEntries(
          Object.entries(settings.sources).map(([id, source]) => [id, source.lang ?? null]),
        ),
      }),
      Plugin.SyntaxHighlighting({
        theme: { light: "github-light", dark: "github-dark" },
        keepBackground: false,
      }),
      // Evidence quotes must stay verbatim: no smart quotes.
      Plugin.GitHubFlavoredMarkdown({ enableSmartyPants: false, linkHeadings: true }),
      Plugin.TableOfContents(),
      // Wiki links are relative Markdown links; titles may contain "/" so no pretty links.
      Plugin.CrawlLinks({ markdownLinkResolution: "relative", prettyLinks: false }),
      Plugin.Description(),
    ],
    filters: [Plugin.RemoveDrafts()],
    emitters: [
      Plugin.ComponentResources(),
      Plugin.ContentPage(),
      Plugin.FolderPage(),
      Plugin.TagPage(),
      Plugin.ContentIndex({ enableSiteMap: !!settings.baseUrl, enableRSS: !!settings.baseUrl }),
      Plugin.Assets(),
      Plugin.Static(),
      Plugin.NotFoundPage(),
    ],
  },
}

export default config
