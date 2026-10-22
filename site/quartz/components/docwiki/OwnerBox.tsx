// "Add a document" (ADR 0009, 0010): the owner's sign-in and upload form at the top of the pipeline
// page, before its text, so the owner finds them without scrolling. Hidden until the portal says
// sign-in exists; scripts/process.inline.ts (Process.tsx) fills it from /api/owner/me.
import { classNames } from "../../util/lang"
import { QuartzComponent, QuartzComponentConstructor, QuartzComponentProps } from "../types"

/** Same slug as `PROCESS_SLUG` in src/docwiki/site/process_page.py. */
const PROCESS_SLUG = "pipeline"

export default (() => {
  const OwnerBox: QuartzComponent = ({ fileData, displayClass }: QuartzComponentProps) => {
    if (fileData.slug !== PROCESS_SLUG) return null
    return (
      <section
        class={classNames(displayClass, "docwiki-owner-box")}
        aria-labelledby="docwiki-owner-box-title"
        hidden
      >
        <h2 id="docwiki-owner-box-title" class="docwiki-owner-box-title">
          Add a document to the wiki
        </h2>
      </section>
    )
  }

  return OwnerBox
}) satisfies QuartzComponentConstructor
