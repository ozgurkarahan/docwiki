// Page <head> without third-party requests: no web-font CDN, no preconnects, no analytics,
// no external social images. Quartz's inline content-index loader is replaced by a same-origin
// script so the site also works under `Content-Security-Policy: script-src 'self'`; it is told the
// wiki's languages, so that search and the explorer list the pages of the reader's language.
import { i18n } from "../../i18n"
import { FullSlug, joinSegments, pathToRoot, resolveRelative } from "../../util/path"
import {
  CSSResourceToStyleElement,
  JSResource,
  JSResourceToScriptElement,
} from "../../util/resources"
import { unescapeHTML } from "../../util/escape"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { languages, twins } from "./settings"

const CONTENT_INDEX_LOADER = /^const fetchData = fetch\("[^"]*static\/contentIndex\.json"\)/

function isContentIndexLoader(resource: JSResource): boolean {
  return resource.contentType === "inline" && CONTENT_INDEX_LOADER.test(resource.script.trim())
}

/** A page's URL: absolute on the site's host when the build knows it, else relative. */
function pageHref(base: string | undefined, from: FullSlug, slug: string): string {
  const path = slug === "index" ? "" : slug.endsWith("/index") ? slug.slice(0, -5) : slug
  return base ? `https://${base}/${path}` : resolveRelative(from, slug as FullSlug)
}

export default (() => {
  const Head: QuartzComponent = ({
    cfg,
    fileData,
    allFiles,
    externalResources,
  }: QuartzComponentProps) => {
    const titleSuffix = cfg.pageTitleSuffix ?? ""
    const title =
      (fileData.frontmatter?.title ?? i18n(cfg.locale).propertyDefaults.title) + titleSuffix
    const description =
      fileData.frontmatter?.socialDescription ??
      fileData.frontmatter?.description ??
      unescapeHTML(fileData.description?.trim() ?? i18n(cfg.locale).propertyDefaults.description)

    const { css, js, additionalHead } = externalResources
    const url = new URL(`https://${cfg.baseUrl ?? "example.com"}`)
    const baseDir =
      fileData.slug === "404" ? (url.pathname as FullSlug) : pathToRoot(fileData.slug!)
    const iconPath = joinSegments(baseDir, "static/docwiki/icon.svg")
    const loaderPath = joinSegments(baseDir, "static/docwiki/content-index.js")
    const socialUrl =
      fileData.slug === "404" ? url.toString() : joinSegments(url.toString(), fileData.slug!)
    // The same page in the other languages (ADR 0012): `hreflang` alternates, the canonical
    // language also as `x-default`.
    const slug = (fileData.slug ?? "index") as FullSlug
    const alternates = twins(slug, allFiles).map(([lang, twin]) => ({
      lang,
      href: pageHref(cfg.baseUrl, slug, twin),
    }))

    return (
      <head>
        <title>{title}</title>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
        <meta name="referrer" content="no-referrer" />
        <meta name="color-scheme" content="light dark" />
        <meta name="og:site_name" content={cfg.pageTitle}></meta>
        <meta property="og:title" content={title} />
        <meta property="og:type" content="website" />
        <meta property="og:description" content={description} />
        {cfg.baseUrl && <meta property="og:url" content={socialUrl}></meta>}
        <link rel="icon" href={iconPath} type="image/svg+xml" />
        {alternates.map((item) => (
          <link rel="alternate" hreflang={item.lang} href={item.href} />
        ))}
        {alternates.length > 0 && (
          <link rel="alternate" hreflang="x-default" href={alternates[0].href} />
        )}
        <meta name="description" content={description} />
        <meta name="generator" content="Quartz" />
        {css.map((resource) => CSSResourceToStyleElement(resource, true))}
        {js
          .filter((resource) => resource.loadTime === "beforeDOMReady")
          .map((resource) =>
            isContentIndexLoader(resource) ? (
              <script
                src={loaderPath}
                type="application/javascript"
                data-languages={languages.length > 1 ? languages.join(" ") : undefined}
                spa-preserve
              />
            ) : (
              JSResourceToScriptElement(resource, true)
            ),
          )}
        {additionalHead.map((resource) =>
          typeof resource === "function" ? resource(fileData) : resource,
        )}
      </head>
    )
  }

  return Head
}) satisfies QuartzComponentConstructor
