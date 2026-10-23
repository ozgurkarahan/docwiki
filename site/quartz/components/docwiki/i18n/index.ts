// The site's languages (ADR 0012, slice G): French canonical pages at the root of the site, an
// English mirror under `en/` with the same slugs. Pure helpers, shared by the components (at
// build time) and the inline scripts (in the browser); tested with Node (tests/site).
import { en } from "./en.ts"
import { fr } from "./fr.ts"
import type { Lang, Strings } from "./strings.ts"

export type { Lang, Strings } from "./strings.ts"

const TABLES: Record<Lang, Strings> = { en, fr }

/** The UI strings of a language; English for a language without a table. */
export function stringsFor(lang: string | null | undefined): Strings {
  return (lang && TABLES[lang as Lang]) || en
}

/** The two-letter codes the overlay knows how to show. */
export const LANGS: readonly Lang[] = ["fr", "en"]

/**
 * The language tree of a content slug: a mirror's code when the slug is in its folder
 * (`en/sources/x`), else the canonical language (`languages[0]`). Evidence and other shared
 * pages are in the canonical tree.
 */
export function treeOf(slug: string, languages: readonly string[]): string {
  const first = slug.split("/", 1)[0]
  return languages.indexOf(first) > 0 ? first : (languages[0] ?? "en")
}

/** The slug without its mirror folder: `en/sources/x` → `sources/x`, `en/index` → `index`. */
export function baseSlug(slug: string, languages: readonly string[]): string {
  const tree = treeOf(slug, languages)
  return tree === languages[0] ? slug : slug.slice(tree.length + 1) || "index"
}

/** The slug of `base` in `lang`: the canonical language at the root, a mirror in its folder. */
export function slugIn(base: string, lang: string, languages: readonly string[]): string {
  return lang === (languages[0] ?? "en") ? base : `${lang}/${base}`
}

/** The language of a page: its frontmatter's `lang` when it is a wiki language, else its tree. */
export function pageLanguage(
  slug: string,
  frontmatterLang: unknown,
  languages: readonly string[],
): string {
  if (typeof frontmatterLang === "string" && languages.includes(frontmatterLang)) {
    return frontmatterLang
  }
  return treeOf(slug, languages)
}

/**
 * Where the language switch leads from the page `slug` to `lang`: the same page in that language
 * when it exists (`exists`), else that language's documents page for a document's own pages
 * (`evidence/…`, which are not translated), else its home page.
 */
export function switchTarget(
  slug: string,
  lang: string,
  languages: readonly string[],
  exists: (slug: string) => boolean,
): string {
  const base = baseSlug(slug, languages)
  const twin = slugIn(base, lang, languages)
  if (twin === slug || exists(twin)) return twin
  return slugIn(base.startsWith("evidence/") ? "documents" : "index", lang, languages)
}

/**
 * A site-absolute page of the portal's replies (`/sources/x`) in the reader's language: the
 * mirror's folder (`/en/sources/x`) is prepended for wiki pages; the documents' own pages
 * (`/evidence/…`), static files and files with an extension are shared and stay as they are.
 */
export function localUrl(url: string, root: string): string {
  if (!root || !url.startsWith("/") || url.startsWith("//")) return url
  const path = url.split(/[?#]/, 1)[0]
  const last = path.split("/").pop() ?? ""
  if (/^\/(evidence|static|api)(\/|$)/.test(path) || /\.[A-Za-z0-9]+$/.test(last)) return url
  const prefix = `/${root.replace(/\/+$/, "")}`
  return url === "/" ? `${prefix}/` : `${prefix}${url}`
}

/** The cookie the language switch sets; the portal sends the reader to that language. */
export const LANG_COOKIE = "docwiki_lang"

/** The `Set-Cookie`-style value the switch writes for `lang` (one year, the whole site). */
export function langCookie(lang: string, secure: boolean): string {
  const attributes = ["path=/", "max-age=31536000", "samesite=lax"]
  if (secure) attributes.push("secure")
  return `${LANG_COOKIE}=${encodeURIComponent(lang)}; ${attributes.join("; ")}`
}

/** In the browser: the language of the page on screen (the header says it), and its table. */
export function clientLang(): string {
  if (typeof document === "undefined") return "en"
  const bar = document.querySelector<HTMLElement>(".docwiki-tabbar")
  return bar?.dataset.lang || document.documentElement.lang || "en"
}

export function clientStrings(): Strings {
  return stringsFor(clientLang())
}

/** In the browser: the mirror folder of the page on screen (`en/`), or "" in the canonical tree. */
export function clientRoot(): string {
  if (typeof document === "undefined") return ""
  return document.querySelector<HTMLElement>(".docwiki-tabbar")?.dataset.root ?? ""
}
