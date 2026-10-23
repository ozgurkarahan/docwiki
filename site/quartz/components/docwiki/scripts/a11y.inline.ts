// Client of the skip link (SkipLink.tsx, slice H) and corrections to the markup of Quartz's own
// components, which are not vendored: attributes are corrected after each page navigation (Quartz
// morphs the whole body, so they are set again on every `nav`).
import { SKIP_TARGET_ID } from "../../../plugins/transformers/docwiki-a11y"

/**
 * The skip link moves the focus itself: following `#docwiki-main` natively would fire `popstate`,
 * on which Quartz's router reloads the page and the focus is lost.
 */
function onSkip(event: MouseEvent) {
  const target = document.getElementById(SKIP_TARGET_ID)
  if (!target) return
  event.preventDefault()
  target.focus()
}

/** One `main` landmark (the page column) and the two side panels, so no content is outside one. */
function landmarks() {
  const center = document.querySelector<HTMLElement>("#quartz-body > .center")
  if (center && !document.querySelector("main, [role='main']")) center.setAttribute("role", "main")
  // The page column's <header> (tabs, banner) is inside that landmark: not a second banner. Its
  // tabs keep their own navigation landmark.
  for (const header of document.querySelectorAll<HTMLElement>("[role='main'] header")) {
    if (!header.hasAttribute("role")) header.setAttribute("role", "none")
  }
  const left = document.querySelector<HTMLElement>("#quartz-body > .sidebar.left")
  if (left && !left.hasAttribute("role")) {
    left.setAttribute("role", "navigation")
    left.setAttribute("aria-label", "Wiki")
  }
  const right = document.querySelector<HTMLElement>("#quartz-body > .sidebar.right")
  if (right && !right.hasAttribute("role") && right.childElementCount > 0) {
    right.setAttribute("role", "complementary")
    right.setAttribute("aria-label", "About this page")
  }
}

/**
 * Quartz's explorer keeps `aria-expanded` on its `div` (not allowed there) and never updates it on
 * its buttons; the phone's menu button has no name. The state moves to the buttons that toggle it.
 */
function syncExplorer(explorer: HTMLElement) {
  explorer.removeAttribute("aria-expanded")
  const open = !explorer.classList.contains("collapsed")
  for (const toggle of explorer.querySelectorAll<HTMLElement>(".explorer-toggle")) {
    if (toggle.getAttribute("aria-expanded") !== String(open)) {
      toggle.setAttribute("aria-expanded", String(open))
    }
  }
}

function explorers() {
  for (const explorer of document.querySelectorAll<HTMLElement>(".explorer")) {
    const menu = explorer.querySelector<HTMLElement>(".mobile-explorer")
    if (menu) {
      menu.setAttribute("aria-label", "Browse the wiki")
      menu.querySelector("svg")?.setAttribute("aria-hidden", "true")
    }
    // A group whose state is said by the buttons that control it.
    explorer.querySelector(".explorer-content")?.removeAttribute("aria-expanded")
    syncExplorer(explorer)
    const observer = new MutationObserver(() => syncExplorer(explorer))
    observer.observe(explorer, { attributes: true, attributeFilter: ["class", "aria-expanded"] })
    window.addCleanup(() => observer.disconnect())
  }
}

/** The table of contents' button names a list id that Quartz's OverflowList replaces. */
function tableOfContents() {
  for (const toc of document.querySelectorAll<HTMLElement>(".toc")) {
    const button = toc.querySelector(".toc-header")
    const content = toc.querySelector(".toc-content")
    if (button && content?.id) button.setAttribute("aria-controls", content.id)
  }
}

document.addEventListener("nav", () => {
  for (const link of document.querySelectorAll<HTMLAnchorElement>("a.docwiki-skip")) {
    link.addEventListener("click", onSkip)
    window.addCleanup(() => link.removeEventListener("click", onSkip))
  }
  landmarks()
  explorers()
  tableOfContents()
})
