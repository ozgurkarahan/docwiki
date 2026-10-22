// "The process, live" (ADR 0009): the live part of the how-it-works page, after its "## Live"
// heading. The page's text is static (docwiki.site.process_page); this section is filled on the
// client from the portal's /api/process and /api/owner/me, with DOM nodes and textContent only
// (scripts/process.inline.ts). On a static host those APIs do not exist and the placeholder stays.
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
// @ts-ignore
import script from "./scripts/process.inline"

/** Same slug as `PROCESS_SLUG` in src/docwiki/site/process_page.py. */
const PROCESS_SLUG = "how-it-works"

export default (() => {
  const Process: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (fileData.slug !== PROCESS_SLUG) return null
    return (
      <section class={classNames(displayClass, "docwiki-process")} aria-label="The process, live">
        <p class="docwiki-process-placeholder">Live status appears here on the deployed site.</p>
      </section>
    )
  }

  Process.afterDOMLoaded = script

  return Process
}) satisfies QuartzComponentConstructor
