// The site's three tabs (ADR 0010): ① Documents · ② Pipeline · ③ Wiki, in the header of every
// page, with the pipeline's status chip, the owner's Sign in and, when the wiki has a mirror
// (ADR 0012), the language switch "FR · EN". The chip and the sign-in come from the portal
// (/api/status, /api/owner/me) and stay hidden on a static host (scripts/tabs.inline.ts). The
// tabs, the chip and the switch speak the page's language and lead to pages in that language.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { switchTarget } from "./i18n"
// @ts-ignore
import script from "./scripts/tabs.inline"
import {
  builtSlugs,
  canonicalLang,
  inLang,
  languages,
  pageBase,
  pageLang,
  pageStrings,
} from "./settings"

/** Same slugs as `DOCUMENTS_SLUG` and `PROCESS_SLUG` in src/docwiki/site/process_page.py. */
const TABS = [
  { slug: "documents", number: "①", key: "documents" },
  { slug: "pipeline", number: "②", key: "pipeline" },
  { slug: "index", number: "③", key: "wiki" },
] as const

export default (() => {
  const Tabs: QuartzComponent = ({ fileData, allFiles, displayClass }: QuartzComponentProps) => {
    const slug = (fileData.slug ?? "index") as FullSlug
    const lang = pageLang(fileData)
    const t = pageStrings(fileData)
    const base = pageBase(slug)
    // A document's own pages (evidence/<source_id>/…) belong to the Documents tab.
    const active =
      base === "documents" || base.startsWith("evidence/")
        ? "documents"
        : base === "pipeline"
          ? "pipeline"
          : "index"
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const local = (target: string) => link(inLang(target, lang))
    const root = lang === canonicalLang ? "" : `${lang}/`
    const built = builtSlugs(allFiles)
    return (
      <div
        class={classNames(displayClass, "docwiki-tabbar")}
        data-lang={lang}
        data-root={root}
      >
        <nav class="docwiki-tabs" aria-label="DocWiki">
          <ol>
            {TABS.map((tab) => (
              <li>
                <a
                  href={local(tab.slug)}
                  class="docwiki-tab"
                  aria-current={tab.slug === active ? "page" : undefined}
                >
                  <span class="docwiki-tab-number" aria-hidden="true">
                    {tab.number}
                  </span>{" "}
                  {t.header.tabs[tab.key]}
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <a class="docwiki-chip docwiki-status docwiki-status--idle" href={local("pipeline")}>
          <span class="docwiki-status-shape" aria-hidden="true">
            ●
          </span>
          <span class="docwiki-status-word">{t.header.chipIdle}</span>
        </a>
        {/* The pipeline page has the owner's box with its own sign-in. */}
        {base !== "pipeline" && (
          <a class="docwiki-sign-in" href={local("pipeline")}>
            {t.header.signIn}
          </a>
        )}
        {/* The 404 page is served at any path, where its relative links would not resolve. */}
        {languages.length > 1 && slug !== "404" && (
          <nav class="docwiki-lang" aria-label={t.header.languageNav}>
            {languages.map((code, index) => {
              const target = switchTarget(slug, code, languages, (other) => built.has(other))
              const names = t.header.languageNames as Record<string, string>
              const current = code === lang
              return (
                <>
                  {index > 0 && (
                    <span class="docwiki-lang-sep" aria-hidden="true">
                      ·
                    </span>
                  )}
                  <a
                    class="docwiki-lang-link"
                    href={link(target)}
                    hreflang={code}
                    lang={code}
                    data-lang-switch={code}
                    data-router-ignore="true"
                    data-no-popover="true"
                    aria-current={current ? "true" : undefined}
                  >
                    {code.toUpperCase()}
                    <span class="sr-only"> – {names[code] ?? code}</span>
                  </a>
                </>
              )
            })}
          </nav>
        )}
        <span class="sr-only docwiki-chip-live" role="status" aria-live="polite"></span>
      </div>
    )
  }

  // Quartz's explorer scrolls its active entry into view on a first visit, which scrolled the
  // whole page down past the tabs; a saved explorer position (here: the top) skips that.
  Tabs.beforeDOMLoaded = `try {
  if (!sessionStorage.getItem("explorerScrollTop")) sessionStorage.setItem("explorerScrollTop", "0")
} catch (e) {}`
  Tabs.afterDOMLoaded = script

  return Tabs
}) satisfies QuartzComponentConstructor
