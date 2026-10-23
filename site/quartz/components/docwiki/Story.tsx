// The story home (ADR 0010, UX review 2026-10-22), home page only, under the title: one sentence
// on the pattern, three cards that follow it (the documents → the pipeline that compiles them →
// the cited wiki), then a question to try in the "Ask this wiki" drawer. The counts come from the
// build; the pipeline card's last run (length and cost) is read on the client from the portal's
// /api/process, and a static host keeps the build-time text (scripts/story.inline.ts). The
// provenance line and "About DocWiki" (About.tsx) follow.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { EXAMPLE_QUESTIONS, plural } from "../../plugins/transformers/docwiki-text"
// @ts-ignore
import script from "./scripts/story.inline"
import { settings } from "./settings"

/** Id of the hidden "The wiki" heading at the end of About.tsx: the third card scrolls to it. */
export const WIKI_ANCHOR = "docwiki-wiki"

export default (() => {
  const Story: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (fileData.slug !== "index") return null
    const slug = fileData.slug as FullSlug
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const { current, superseded } = settings.documents
    const steps = settings.steps?.length || 13
    const question = EXAMPLE_QUESTIONS[0]
    return (
      <section
        class={classNames(displayClass, "docwiki-story")}
        aria-labelledby="docwiki-story-title"
      >
        <h2 id="docwiki-story-title" class="sr-only">
          How this wiki is made
        </h2>
        <p class="docwiki-story-lede">
          An LLM compiles ordinary business documents into a wiki where every fact is cited, and an
          agent answers from it.
        </p>
        <ol class="docwiki-story-strip">
          <li class="docwiki-story-step">
            <a class="docwiki-story-card" href={link("documents")}>
              <span class="docwiki-story-number" aria-hidden="true">
                ①
              </span>
              <span class="docwiki-story-value">{plural(current + superseded, "document")}</span>
              <span class="docwiki-story-detail">
                {superseded > 0 ? `${current} current · ${superseded} superseded` : "the originals"}
              </span>
              <span class="sr-only"> — open the Documents tab</span>
            </a>
          </li>
          <li class="docwiki-story-step">
            <span class="docwiki-story-arrow" aria-hidden="true">
              →
            </span>
            <a class="docwiki-story-card" href={link("pipeline")}>
              <span class="docwiki-story-number" aria-hidden="true">
                ②
              </span>
              <span class="docwiki-story-value">{steps}-step pipeline</span>
              <span class="docwiki-story-detail docwiki-story-run">
                read · write · check · publish
              </span>
              <span class="sr-only"> — open the Pipeline tab</span>
            </a>
          </li>
          <li class="docwiki-story-step">
            <span class="docwiki-story-arrow" aria-hidden="true">
              →
            </span>
            <a class="docwiki-story-card docwiki-story-wiki" href={`#${WIKI_ANCHOR}`}>
              <span class="docwiki-story-number" aria-hidden="true">
                ③
              </span>
              <span class="docwiki-story-value">
                {plural(settings.citedPages ?? 0, "cited page")}
              </span>
              <span class="docwiki-story-detail">every fact opens its source</span>
              <span class="sr-only"> — go to the wiki below</span>
            </a>
          </li>
        </ol>
        {/* Shown by the script when the "Ask this wiki" drawer is on the page and has something
            to show; it opens the drawer on the question (the ASK_EVENT hook). */}
        <button type="button" class="docwiki-story-try" data-question={question} hidden>
          <span class="docwiki-story-try-label">Try:</span> {question}{" "}
          <span aria-hidden="true">▶</span>
          <span class="sr-only"> (opens Ask this wiki)</span>
        </button>
        {/* Slice F: the evaluation's headline ("RAG vs wiki: …") goes here, under the question. */}
      </section>
    )
  }

  Story.afterDOMLoaded = script

  return Story
}) satisfies QuartzComponentConstructor
