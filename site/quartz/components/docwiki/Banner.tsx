import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
import { settings } from "./settings"

/** Site-wide "fictional sample" notice, shown when the release or domain pack asks for one. */
export default (() => {
  const Banner: QuartzComponent = ({ displayClass }: QuartzComponentProps) => {
    if (!settings.banner) return null
    return (
      <div class={classNames(displayClass, "docwiki-banner")} role="note">
        <span class="docwiki-banner-label">Fictional sample.</span>{" "}
        <span class="docwiki-banner-text">{settings.banner}</span>
      </div>
    )
  }

  return Banner
}) satisfies QuartzComponentConstructor
