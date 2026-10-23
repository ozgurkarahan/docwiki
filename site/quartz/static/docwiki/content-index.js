// Same-origin replacement for Quartz's inline content-index loader (see Head.tsx).
// Quartz's bundles read the global `fetchData` (search, explorer, graph). With a mirror language
// (ADR 0012: French at the root, English under `en/`), each read gives the pages of the language
// of the page on screen: the canonical language leaves the mirrors' folders out, a mirror keeps
// only its folder, and both keep the documents' own pages (`evidence/`), which are shared.
// `data-languages` lists the languages, the canonical one first; without it every page is kept.
;(function () {
  var script = document.currentScript
  var all = fetch(new URL("../contentIndex.json", script.src)).then(function (response) {
    return response.json()
  })
  var languages = ((script && script.getAttribute("data-languages")) || "")
    .split(" ")
    .filter(function (code) {
      return /^[a-z]{2}$/.test(code)
    })

  /** The language tree of a slug: a mirror's code for its folder, else the canonical one. */
  function treeOf(slug) {
    var first = String(slug || "").split("/")[0]
    return languages.indexOf(first) > 0 ? first : languages[0]
  }

  /** Whether a page belongs to the search and explorer of the language `lang`. */
  function keeps(slug, lang) {
    if (String(slug).indexOf("evidence/") === 0) return true
    return treeOf(slug) === lang
  }

  var byLang = {}
  function pagesOf(lang) {
    if (!byLang[lang]) {
      byLang[lang] = all.then(function (data) {
        var kept = {}
        Object.keys(data).forEach(function (slug) {
          if (keeps(slug, lang)) kept[slug] = data[slug]
        })
        return kept
      })
    }
    return byLang[lang]
  }

  var read =
    languages.length > 1
      ? function () {
          var body = document.body
          return pagesOf(treeOf(body ? body.getAttribute("data-slug") || "index" : "index"))
        }
      : function () {
          return all
        }
  // A global getter: Quartz's scripts read `fetchData` as a free variable on each navigation.
  Object.defineProperty(window, "fetchData", { configurable: true, get: read })
  window.docwikiContentIndex = { treeOf: treeOf, keeps: keeps }
})()
