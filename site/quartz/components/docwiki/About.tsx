import { FullSlug, resolveRelative } from "../../util/path"
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { documentsPhrase, qualityPhrase } from "../../plugins/transformers/docwiki-text"
import { inLang, pageBase, pageLang, pageStrings, settings } from "./settings"
import { WIKI_ANCHOR } from "./Story"

/**
 * "About this wiki" block of the home page, under the story strip (Story.tsx): how the release was
 * built (documents, release date, quality gates, run receipt, quality report) and a collapsible
 * "About DocWiki". A visually hidden "The wiki" heading follows: the wiki's own home page starts
 * there, and the strip's third card leads to it. The run receipt, the quality report and
 * `llms.txt` are the canonical wiki's (they are not translated).
 */
export default (() => {
  const About: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (pageBase(fileData.slug) !== "index") return null
    const slug = fileData.slug as FullSlug
    const lang = pageLang(fileData)
    const t = pageStrings(fileData)
    const s = t.story
    const link = (target: string) => resolveRelative(slug, target as FullSlug)
    const llms = link("llms.txt")
    const { documents, quality } = settings
    return (
      <>
        <section class={classNames(displayClass, "docwiki-about")} aria-label={s.aboutLabel}>
          <p class="docwiki-provenance">
            {s.compiledBy} <a href={settings.repoUrl}>DocWiki</a> {s.from}{" "}
            {documentsPhrase(documents.current, documents.superseded, t)}
            {settings.releaseDate && (
              <>
                {" · "}
                {s.release} {settings.releaseDate}
              </>
            )}
            {quality && (
              <>
                {" · "}
                {s.qualityGates} {qualityPhrase(quality, t)}
              </>
            )}
            {settings.runPage && (
              <>
                {" · "}
                <a href={link(settings.runPage)}>{s.runReceipt}</a>
              </>
            )}
            {settings.qualityPage && (
              <>
                {" · "}
                <a href={link(settings.qualityPage)}>{s.qualityReport}</a>
              </>
            )}
            {" · "}
            <a href={link(inLang("pipeline", lang))}>{s.thePipeline}</a>
          </p>
          <details class="docwiki-about-more">
            <summary>{s.aboutDocwiki}</summary>
            <p>{s.aboutIntro}</p>
            <ul>
              <li>{s.aboutFootnotes}</li>
              <li>{s.aboutContradictions}</li>
              <li>
                {s.aboutAgentsBefore}
                <a href={llms}>llms.txt</a>
                {s.aboutAgentsAfter}
              </li>
            </ul>
            <p>
              <a class="docwiki-target" href={settings.repoUrl}>
                {s.sourceCode}
              </a>
            </p>
          </details>
        </section>
        <h2 id={WIKI_ANCHOR} class="sr-only" tabIndex={-1}>
          {s.theWiki}
        </h2>
      </>
    )
  }

  return About
}) satisfies QuartzComponentConstructor
