// "Ask this wiki" (ADR 0007, 0008): a floating button and a non-modal drawer. It lists the research
// answers filed as queries/ pages (static/docwiki/answers.json) and, where the portal enables it,
// lets a visitor ask the Researcher agent (/api/ask). Both are filled on the client with DOM nodes
// and textContent only (scripts/askPanel.inline.ts). The button is part of every page and stays
// hidden until the client knows there is something to show: filed answers, or a live agent.
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
// @ts-ignore
import script from "./scripts/askPanel.inline"
import { settings } from "./settings"

const PANEL_ID = "docwiki-ask"

/** Source id → [source page slug, title]: the wiki pages an answer's citations come from. */
const sourcePages = JSON.stringify(
  Object.fromEntries(
    Object.entries(settings.sources)
      .filter(([, source]) => source.page)
      .map(([id, source]) => [id, [source.page, source.title]]),
  ),
)

export default (() => {
  const AskPanel: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    // The 404 page is served at any path, where its relative links would not resolve.
    if (fileData.slug === "404") return null
    return (
      <div class={classNames(displayClass, "docwiki-ask-root")}>
        <button
          type="button"
          class="docwiki-ask-fab"
          aria-expanded="false"
          aria-controls={PANEL_ID}
          hidden={settings.answers === 0}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
            <path d="M20.5 11.6a8.4 8.4 0 0 1-12.3 7.4L3.5 20.5l1.5-4.4a8.4 8.4 0 1 1 15.5-4.5z" />
            <path d="M9.7 9.4a2.4 2.4 0 0 1 4.6 1c0 1.6-2.3 2-2.3 3.4" />
            <path d="M12 16.7h.01" />
          </svg>
          <span class="docwiki-ask-fab-label">Ask this wiki</span>
        </button>
        <aside
          id={PANEL_ID}
          class="docwiki-ask"
          aria-label="Ask this wiki"
          data-repo-url={settings.repoUrl}
          data-filed-answers={String(settings.answers)}
          data-source-pages={sourcePages}
          hidden
        ></aside>
      </div>
    )
  }

  AskPanel.afterDOMLoaded = script

  return AskPanel
}) satisfies QuartzComponentConstructor
