import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { pageStrings, settings } from "./settings"

const QUARTZ_REPOSITORY = "https://github.com/jackyzha0/quartz"

/** Footer without build-time dates or third-party hosts (only the repository host). */
export default (() => {
  const Footer: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    const t = pageStrings(fileData).wiki
    return (
      <footer class={classNames(displayClass, "docwiki-footer")}>
        <p>
          {t.builtWith} <a href={settings.repoUrl}>DocWiki</a> {t.and}{" "}
          <a href={QUARTZ_REPOSITORY}>Quartz {settings.quartzVersion}</a>
          {settings.releaseId && (
            <>
              {" · "}
              {t.release} <code>{settings.releaseId}</code>
            </>
          )}
          {settings.audience && (
            <>
              {" · "}
              {t.audience} {settings.audience}
            </>
          )}
        </p>
      </footer>
    )
  }

  return Footer
}) satisfies QuartzComponentConstructor
