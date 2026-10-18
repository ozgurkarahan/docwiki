import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { settings } from "./settings"

const QUARTZ_REPOSITORY = "https://github.com/jackyzha0/quartz"

/** Footer without build-time dates or third-party hosts (only the repository host). */
export default (() => {
  const Footer: QuartzComponent = ({ displayClass }: QuartzComponentProps) => (
    <footer class={classNames(displayClass, "docwiki-footer")}>
      <p>
        Built with <a href={settings.repoUrl}>DocWiki</a> and{" "}
        <a href={QUARTZ_REPOSITORY}>Quartz {settings.quartzVersion}</a>
        {settings.releaseId && (
          <>
            {" · "}release <code>{settings.releaseId}</code>
          </>
        )}
        {settings.audience && <> · audience {settings.audience}</>}
      </p>
    </footer>
  )

  return Footer
}) satisfies QuartzComponentConstructor
