// The site's three tabs (ADR 0010): ① Documents · ② Pipeline · ③ Wiki, in the header of every
// page, with the pipeline's status chip and the owner's Sign in. The chip and the sign-in come
// from the portal (/api/status, /api/owner/me) and stay hidden on a static host
// (scripts/tabs.inline.ts).
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
// @ts-ignore
import script from "./scripts/tabs.inline"

/** Same slugs as `DOCUMENTS_SLUG` and `PROCESS_SLUG` in src/docwiki/site/process_page.py. */
const TABS = [
  { slug: "documents", number: "①", label: "Documents" },
  { slug: "pipeline", number: "②", label: "Pipeline" },
  { slug: "index", number: "③", label: "Wiki" },
] as const

export default (() => {
  const Tabs: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    const slug = (fileData.slug ?? "index") as FullSlug
    // A document's own pages (evidence/<source_id>/…) belong to the Documents tab.
    const active =
      slug === "documents" || slug.startsWith("evidence/")
        ? "documents"
        : slug === "pipeline"
          ? "pipeline"
          : "index"
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    return (
      <div class={classNames(displayClass, "docwiki-tabbar")}>
        <nav class="docwiki-tabs" aria-label="DocWiki">
          <ol>
            {TABS.map((tab) => (
              <li>
                <a
                  href={link(tab.slug)}
                  class="docwiki-tab"
                  aria-current={tab.slug === active ? "page" : undefined}
                >
                  <span class="docwiki-tab-number" aria-hidden="true">
                    {tab.number}
                  </span>{" "}
                  {tab.label}
                </a>
              </li>
            ))}
          </ol>
        </nav>
        <a class="docwiki-chip docwiki-status docwiki-status--idle" href={link("pipeline")}>
          <span class="docwiki-status-shape" aria-hidden="true">
            ●
          </span>
          <span class="docwiki-status-word">Idle</span>
        </a>
        {/* The pipeline page has the owner's box with its own sign-in. */}
        {slug !== "pipeline" && (
          <a class="docwiki-sign-in" href={link("pipeline")}>
            Sign in
          </a>
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
