// "Skip to content" (slice H): the first focusable element of every page, shown when it has the
// focus, leading to the page title (ArticleTitle.tsx). Its script also corrects the markup of
// Quartz's own components from the overlay (scripts/a11y.inline.ts): landmarks, the explorer's
// and the table of contents' ARIA attributes, the menu button's name, and smooth scrolling under
// `prefers-reduced-motion`.
import { classNames } from "../../util/lang"
import { SKIP_TARGET_ID } from "../../plugins/transformers/docwiki-a11y"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"
// @ts-ignore
import script from "./scripts/a11y.inline"

export default (() => {
  const SkipLink: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (!fileData.frontmatter?.title) return null
    return (
      <a
        class={classNames(displayClass, "docwiki-skip")}
        href={`#${SKIP_TARGET_ID}`}
        data-router-ignore="true"
        data-no-popover="true"
      >
        Skip to content
      </a>
    )
  }

  // Quartz scrolls its explorer to the current page smoothly; with reduced motion, it jumps.
  SkipLink.beforeDOMLoaded = `(function () {
  try {
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)")
    var scrollIntoView = Element.prototype.scrollIntoView
    Element.prototype.scrollIntoView = function (options) {
      if (reduce.matches && options && typeof options === "object" && options.behavior === "smooth") {
        options = Object.assign({}, options, { behavior: "auto" })
      }
      return scrollIntoView.call(this, options)
    }
  } catch (e) {}
})()`
  SkipLink.afterDOMLoaded = script

  return SkipLink
}) satisfies QuartzComponentConstructor
