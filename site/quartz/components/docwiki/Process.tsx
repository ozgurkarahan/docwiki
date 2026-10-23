// "The process, live" (ADR 0009, 0010): the live part of the pipeline page, after its "## Live"
// heading. The page's text is static (docwiki.site.process_page); this section is filled on the
// client from the portal's /api/process and /api/owner/me, with DOM nodes and textContent only
// (scripts/process.inline.ts). On a static host those APIs do not exist and the placeholder stays.
// The 14 technical steps follow in a disclosure. Every language's pipeline page has it.
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { pageBase, pageLang, pageStrings, settingsFor } from "./settings"
// @ts-ignore
import script from "./scripts/process.inline"

/** Same slug as `PROCESS_SLUG` in src/docwiki/site/process_page.py. */
const PROCESS_SLUG = "pipeline"

export default (() => {
  const Process: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (pageBase(fileData.slug) !== PROCESS_SLUG) return null
    const t = pageStrings(fileData).pipeline
    const steps = settingsFor(pageLang(fileData)).steps
    return (
      <section
        id="docwiki-live"
        class={classNames(displayClass, "docwiki-process")}
        aria-label={t.liveLabel}
      >
        <p class="docwiki-process-placeholder">{t.placeholder}</p>
        {steps && steps.length > 0 && (
          <details class="docwiki-process-steps">
            <summary>{t.stepsSummary(steps.length)}</summary>
            <table class="docwiki-process-steps-table">
              <thead>
                <tr>
                  <th scope="col">#</th>
                  <th scope="col">{t.stepColumn}</th>
                  <th scope="col">{t.whatColumn}</th>
                </tr>
              </thead>
              <tbody>
                {steps.map((step, index) => (
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
