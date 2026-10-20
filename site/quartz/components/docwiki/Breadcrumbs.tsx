import breadcrumbsStyle from "../styles/breadcrumbs.scss"
import { FullSlug, resolveRelative, simplifySlug } from "../../util/path"
import { classNames } from "../../util/lang"
import { trieFromAllFiles } from "../../util/ctx"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"

interface Options {
  rootName: string
  spacerSymbol: string
}

const defaultOptions: Options = { rootName: "Home", spacerSymbol: "/" }

/** Folders without an index page show their path segment: capitalise it (`evidence`). */
function folderName(name: string, untitled: boolean): string {
  return untitled ? name.charAt(0).toUpperCase() + name.slice(1) : name
}

/**
 * Breadcrumbs that keep titles verbatim (Quartz's own component turns `DEV-2026-014` into
 * `DEV 2026 014`), with the current page as plain text marked `aria-current`.
 */
export default ((userOpts?: Partial<Options>) => {
  const opts = { ...defaultOptions, ...userOpts }
  const Breadcrumbs: QuartzComponent = ({
    fileData,
    allFiles,
    displayClass,
    ctx,
  }: QuartzComponentProps) => {
    const slug = fileData.slug as FullSlug
    const trie = (ctx.trie ??= trieFromAllFiles(allFiles))
    const nodes = trie.ancestryChain(slug.split("/"))
    if (!nodes || nodes.length < 2) return null
    const crumbs = nodes.map((node, index) => ({
      name: index === 0 ? opts.rootName : folderName(node.displayName, node.data === null),
      href: resolveRelative(slug, simplifySlug(node.slug)),
    }))
    const current = crumbs.pop()!

    return (
      <nav class={classNames(displayClass, "breadcrumb-container")} aria-label="Breadcrumbs">
        {crumbs.map((crumb) => (
          <div class="breadcrumb-element">
            <a href={crumb.href}>{crumb.name}</a>
            <p aria-hidden="true">{` ${opts.spacerSymbol} `}</p>
          </div>
        ))}
        <div class="breadcrumb-element">
          <span aria-current="page">{current.name}</span>
        </div>
      </nav>
    )
  }
  Breadcrumbs.css = breadcrumbsStyle

  return Breadcrumbs
}) satisfies QuartzComponentConstructor
