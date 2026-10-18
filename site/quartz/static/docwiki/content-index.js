// Same-origin replacement for Quartz's inline content-index loader (see Head.tsx).
// A top-level `const` in a classic script is a global binding, visible to Quartz's bundles.
const fetchData = fetch(new URL("../contentIndex.json", document.currentScript.src)).then(
  (response) => response.json(),
)
