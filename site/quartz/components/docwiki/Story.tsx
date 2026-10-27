// The story home (ADR 0010, UX review 2026-10-22), home page only, under the title: one sentence
// on the pattern, three cards that follow it (the documents → the pipeline that compiles them →
// the cited wiki), then a question to try in the "Ask this wiki" drawer. The counts come from the
// build; the pipeline card's last run (length and cost) is read on the client from the portal's
// /api/process, and a static host keeps the build-time text (scripts/story.inline.ts). The
// provenance line and "About DocWiki" (About.tsx) follow. Each language's home (`index`,
// `en/index`) has it, in that language. Under the question: the button that starts the guided
// tour (Tour.tsx, whose script un-hides it), the link to the architecture page, and the
// evaluation panel "wiki + agent vs RAG" (site.md §12.1), left out when the build had no
// evaluation results.
import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
// @ts-ignore
import script from "./scripts/story.inline"
import type { Strings } from "./i18n"
import {
  DocwikiEvalMetric,
  DocwikiEvals,
  humanDate,
  inLang,
  pageBase,
  pageLang,
  pageStrings,
  settings,
  settingsFor,
} from "./settings"

/** Id of the hidden "The wiki" heading at the end of About.tsx: the third card scrolls to it. */
export const WIKI_ANCHOR = "docwiki-wiki"

/** Id of the evaluation panel: the tour's last step points at it. */
export const EVAL_ID = "docwiki-eval"

function Metric({ metric, t }: { metric: DocwikiEvalMetric | null; t: Strings }) {
  if (!metric) return <td class="docwiki-eval-none">–</td>
  return (
    <td>
      <span class="docwiki-eval-value">{t.evals.percent(metric.value)}</span>
      {metric.passed !== null && (
        <span class="docwiki-eval-count">
          {metric.passed}/{metric.n}
        </span>
      )}
    </td>
  )
}

/** "Wiki + agent vs RAG": accuracy, exact numbers, cost and median time of three systems. */
function EvalPanel({ evals, t }: { evals: DocwikiEvals; t: Strings }) {
  const e = t.evals
  const estimated = evals.systems.some((row) => row.costPerQuestion !== null && !row.pricesVerified)
  return (
    <section id={EVAL_ID} class="docwiki-eval" aria-labelledby="docwiki-eval-title">
      <h3 id="docwiki-eval-title" class="docwiki-eval-title">
        {e.heading}
      </h3>
      <p class="docwiki-eval-intro">{e.intro}</p>
      <div class="docwiki-eval-frame">
        <table class="docwiki-eval-table">
          <caption class="sr-only">{e.caption}</caption>
          <thead>
            <tr>
              <th scope="col">{e.system}</th>
              <th scope="col">{e.accuracy}</th>
              <th scope="col">{e.numeric}</th>
              <th scope="col">{e.cost}</th>
              <th scope="col">{e.latency}</th>
            </tr>
          </thead>
          <tbody>
            {evals.systems.map((row) => (
              <tr class={row.system === "docwiki-researcher" ? "docwiki-eval-ours" : undefined}>
                <th scope="row">{e.systems[row.system] ?? row.system}</th>
                <Metric metric={row.accuracy} t={t} />
                <Metric metric={row.numeric} t={t} />
                <td>
                  {row.costPerQuestion === null
                    ? "–"
                    : `${row.pricesVerified ? "" : "≈ "}${e.money(row.costPerQuestion)}`}
                </td>
                <td>{row.latencyP50 === null ? "–" : e.seconds(row.latencyP50)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p class="docwiki-eval-meta">
        {e.run(evals.questions, evals.split, humanDate(evals.date, t))}
        {estimated && <> · {e.estimated}</>} · <a href={evals.scoreboardUrl}>{e.scoreboard}</a>
      </p>
    </section>
  )
}

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
        <p class="docwiki-story-more">
          {/* Shown by the tour's script (Tour.tsx): the tour needs JavaScript. */}
          <button type="button" class="docwiki-tour-start" hidden>
            {s.tourButton}
          </button>
          <a class="docwiki-story-architecture" href={link("architecture")}>
            {s.architectureLink}
          </a>
        </p>
        {settings.evals && settings.evals.systems.length > 0 && (
          <EvalPanel evals={settings.evals} t={t} />
        )}
      </section>
    )
  }

  Story.afterDOMLoaded = script

  return Story
}) satisfies QuartzComponentConstructor
