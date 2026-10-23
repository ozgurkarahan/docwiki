// The page title, as Quartz's ArticleTitle, with the id the "Skip to content" link targets
// (SkipLink.tsx, slice H). It takes the focus from that link, so it is focusable by script only.
import { classNames } from "../../util/lang"
import { SKIP_TARGET_ID } from "../../plugins/transformers/docwiki-a11y"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"

export default (() => {
  const ArticleTitle: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    const title = fileData.frontmatter?.title
    if (!title) return null
    return (
      <h1 id={SKIP_TARGET_ID} class={classNames(displayClass, "article-title")} tabIndex={-1}>
        {title}
      </h1>
    )
  }

  ArticleTitle.css = `
.article-title {
  margin: 2rem 0 0 0;
}
`

  return ArticleTitle
}) satisfies QuartzComponentConstructor
