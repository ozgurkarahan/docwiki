// The story home (ADR 0010, UX review 2026-10-22), home page only, under the title: one sentence
// on the pattern, three cards that follow it (the documents → the pipeline that compiles them →
// the cited wiki), then a question to try in the "Ask this wiki" drawer. The counts come from the
// build; the pipeline card's last run (length and cost) is read on the client from the portal's
// /api/process, and a static host keeps the build-time text (scripts/story.inline.ts). The
// provenance line and "About DocWiki" (About.tsx) follow. Each language's home (`index`,
// `en/index`) has it, in that language.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
// @ts-ignore
import script from "./scripts/story.inline"
import { inLang, pageBase, pageLang, pageStrings, settings, settingsFor } from "./settings"

/** Id of the hidden "The wiki" heading at the end of About.tsx: the third card scrolls to it. */
export const WIKI_ANCHOR = "docwiki-wiki"

export default (() => {
  const Story: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (pageBase(fileData.slug) !== "index") return null
    const slug = fileData.slug as FullSlug
    const lang = pageLang(fileData)
    const t = pageStrings(fileData)
    const local = settingsFor(lang)
    const link = (target: string) => resolveRelative(slug, inLang(target, lang) as FullSlug)
    const { current, superseded } = settings.documents
    const steps = local.steps?.length || 13
    const question = t.ask.examples[0]
    const s = t.story
    return (
      <section
        class={classNames(displayClass, "docwiki-story")}
        aria-labelledby="docwiki-story-title"
      >
        <h2 id="docwiki-story-title" class="sr-only">
          {s.heading}
        </h2>
        <p class="docwiki-story-lede">{s.lede}</p>
        <p class="docwiki-story-poc">
          {s.pocBefore}
          <a href={settings.repoUrl}>{s.pocLink}</a>
          {s.pocAfter}
        </p>
        <ol class="docwiki-story-strip">
          <li class="docwiki-story-step">
            <a class="docwiki-story-card" href={link("documents")}>
              <span class="docwiki-story-number" aria-hidden="true">
                ①
              </span>
              <span class="docwiki-story-tab">{t.header.tabs.documents}</span>
              <span class="docwiki-story-value">{t.words.documents(current + superseded)}</span>
              <span class="docwiki-story-detail">
                {superseded > 0 ? s.current(current, superseded) : s.originals}
              </span>
              <span class="sr-only">{s.openDocuments}</span>
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
              <span class="docwiki-story-tab">{t.header.tabs.pipeline}</span>
              <span class="docwiki-story-value">{s.steps(steps)}</span>
              <span class="docwiki-story-detail docwiki-story-run">{s.stepsDetail}</span>
              <span class="sr-only">{s.openPipeline}</span>
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
              <span class="docwiki-story-tab">{t.header.tabs.wiki}</span>
              <span class="docwiki-story-value">{s.citedPages(local.citedPages ?? 0)}</span>
              <span class="docwiki-story-detail">{s.citedDetail}</span>
              <span class="sr-only">{s.goToWiki}</span>
            </a>
          </li>
        </ol>
        {/* Shown by the script when the "Ask this wiki" drawer is on the page and has something
            to show; it opens the drawer on the question (the ASK_EVENT hook). */}
        <button type="button" class="docwiki-story-try" data-question={question} hidden>
          <span class="docwiki-story-try-label">{s.tryLabel}</span> {question}{" "}
          <span aria-hidden="true">▶</span>
          <span class="sr-only">{s.tryOpens}</span>
        </button>
        {/* Slice F: the evaluation's headline ("RAG vs wiki: …") goes here, under the question. */}
      </section>
    )
  }

  Story.afterDOMLoaded = script

  return Story
}) satisfies QuartzComponentConstructor
