// "The process, live" (ADR 0009, 0010): the live part of the pipeline page, after its "## Live"
// heading. The page's text is static (docwiki.site.process_page); this section is filled on the
// client from the portal's /api/process and /api/owner/me, with DOM nodes and textContent only
// (scripts/process.inline.ts). On a static host those APIs do not exist and the placeholder stays.
// The 13 technical steps follow in a disclosure.
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { settings } from "./settings"
// @ts-ignore
import script from "./scripts/process.inline"

/** Same slug as `PROCESS_SLUG` in src/docwiki/site/process_page.py. */
const PROCESS_SLUG = "pipeline"

export default (() => {
  const Process: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (fileData.slug !== PROCESS_SLUG) return null
    return (
      <section
        id="docwiki-live"
        class={classNames(displayClass, "docwiki-process")}
        aria-label="The process, live"
      >
        <p class="docwiki-process-placeholder">Live status appears here on the deployed site.</p>
        {settings.steps && settings.steps.length > 0 && (
          <details class="docwiki-process-steps">
            <summary>The {settings.steps.length} technical steps</summary>
            <table class="docwiki-process-steps-table">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">Step</th>
                  <th scope="col">What it does</th>
                </tr>
              </thead>
              <tbody>
                {settings.steps.map((step, index) => (
                  <tr>
                    <td>{index + 1}</td>
                    <td>
                      <code>{step.name}</code>
                    </td>
                    <td>{step.text}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        )}
      </section>
    )
  }

  Process.afterDOMLoaded = script

  return Process
}) satisfies QuartzComponentConstructor
