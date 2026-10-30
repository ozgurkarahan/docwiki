// English UI strings of the overlay (the mirror under `en/`, and every page of an English wiki).
// Typed by `Strings` (strings.ts); fr.ts has the same keys.
import type { Strings } from "./strings.ts"

function plural(count: number, word: string): string {
  return `${count} ${word}${count === 1 ? "" : "s"}`
}

function money(total: number, currency: string | null): string {
  const tiny = total > 0 && total < 0.005
  if (currency === null || currency === "USD") return tiny ? "<$0.01" : `$${total.toFixed(2)}`
  return `${currency} ${tiny ? "<0.01" : total.toFixed(2)}`
}

export const en: Strings = {
  lang: "en",
  locale: "en-US",
  dateLocale: "en-GB",
  decimal: ".",

  header: {
    tabs: { documents: "Documents", pipeline: "Pipeline", wiki: "Wiki" },
    chipIdle: "Pipeline idle",
    chipProcessing: (count) =>
      count > 0 ? `Processing ${plural(count, "document")}` : "Processing — a run is at work",
    chipInWiki: "In the wiki → new page",
    chipTitleInWiki: (title) => `In the wiki: ${title}`,
    chipTitleIdle: "The pipeline is idle; open it",
    chipLive: (words) => `Pipeline: ${words}`,
    signIn: "Sign in",
    signInTitle: "Owner sign-in: only the owner adds documents",
    owner: "Owner ✓",
    ownerTitle: "Signed in as the owner: add documents on the Pipeline page",
    languageNav: "Language",
    languageNames: { en: "English", fr: "Français" },
  },

  a11y: {
    skip: "Skip to content",
    wikiNav: "Wiki",
    aboutPage: "About this page",
    browseWiki: "Browse the wiki",
    newTab: " (opens in a new tab)",
    breadcrumbs: "Breadcrumbs",
  },

  wiki: {
    explorerTitle: "Browse",
    breadcrumbRoot: "Wiki",
    documents: "Documents",
    bannerLabel: "Fictional sample.",
    bannerText:
      "Every organisation, person, site and document in this wiki is invented. " +
      "Not for operational use.",
    builtWith: "Built with",
    and: "and",
    release: "release",
    audience: "audience",
    scrollSideways: "Scroll sideways →",
    table: "Table",
    tableNamed: (heading) => `Table: ${heading}`,
    openImage: "Open the full-size image",
    provenanceBadges: "Provenance badges",
    footnotes: "Footnotes",
    footnoteBack: (reference) => `Back to reference ${reference}`,
    untranslated: "Untranslated",
    globalGraph: "Global graph",
    rssFeed: "RSS feed",
  },

  badges: {
    citation: {
      verified: {
        text: "✓ quote verified",
        meaning: "the quoted words were found verbatim in the source text",
      },
      paraphrase: {
        text: "paraphrase",
        meaning: "reworded from the source text; numbers checked, no verbatim quote",
      },
      table: {
        text: "table",
        meaning: "values parsed deterministically from the cited table rows",
      },
      ocr: { text: "OCR", meaning: "text recognised from an image; compare it with the image" },
      generated: {
        text: "generated description",
        meaning: "written by a model to describe a figure; not a quote",
      },
    },
    provenance: {
      "native-text": {
        text: "native text",
        meaning: "taken from the document's own text layer",
      },
      "deterministic-table": {
        text: "table",
        meaning: "cell values parsed deterministically from the file",
      },
      ocr: { text: "OCR", meaning: "text recognised from pixels; check it against the image" },
      "model-description": {
        text: "generated description",
        meaning: "written by a model; never cite it as a quote",
      },
    },
  },

  status: {
    received: "Received",
    queued: "Queued",
    processing: "Processing",
    in_wiki: "In the wiki",
    superseded: "Superseded",
    held_back: "Held back",
    failed: "Failed",
    removed: "Removed",
  },

  words: {
    documents: (count) => plural(count, "document"),
    documentsPhrase: (current, superseded) => {
      const total = plural(current + superseded, "document")
      return superseded > 0 ? `${total} (${superseded} superseded)` : total
    },
    quality: (q) => {
      if (q.blockingFailed > 0) return `${plural(q.blockingFailed, "blocking gate")} failed`
      const parts = [`${q.passed} passed`]
      if (q.warned > 0) parts.push(plural(q.warned, "warning"))
      if (q.skipped > 0) parts.push(`${q.skipped} skipped`)
      return parts.join(", ")
    },
    andMore: (count) => `and ${count} more`,
    money,
    lastRun: (parts) => `last run ${parts}`,
  },

  story: {
    heading: "How this wiki is made",
    lede:
      "An LLM compiles ordinary business documents into a wiki where every fact is cited, and " +
      "an agent answers from it.",
    pocBefore:
      "A public proof of concept on Azure, run on the invented documents of a building " +
      "contractor. The code is ",
    pocLink: "open source",
    pocAfter: "; the three tabs above follow the same three steps.",
    current: (current, superseded) => `${current} current · ${superseded} superseded`,
    originals: "the originals",
    openDocuments: " — open the Documents tab",
    steps: (count) => `${count}-step pipeline`,
    stepsDetail: "read · write · check · publish",
    openPipeline: " — open the Pipeline tab",
    citedPages: (count) => plural(count, "cited page"),
    citedDetail: "every fact opens its source",
    goToWiki: " — go to the wiki below",
    tryLabel: "Try:",
    tryOpens: " (opens Ask this wiki)",
    aboutLabel: "About this wiki",
    compiledBy: "Compiled by",
    from: "from",
    release: "release",
    qualityGates: "quality gates:",
    runReceipt: "run receipt",
    qualityReport: "quality report",
    thePipeline: "the pipeline",
    aboutDocwiki: "About DocWiki",
    aboutIntro:
      "This site was generated by DocWiki, which compiles a folder of documents (PDF, Word, " +
      "Excel, CSV, PowerPoint, e-mail, scans and transcripts) into a Markdown wiki that people " +
      "can browse and agents can trust.",
    aboutFootnotes:
      "Every fact ends with a footnote that opens its evidence: the exact page, paragraph or " +
      "table rows it came from, with a provenance badge.",
    aboutContradictions:
      "Contradictions between documents and superseded revisions are shown side by side, never " +
      "silently resolved.",
    aboutAgentsBefore: "The same immutable release ships as plain Markdown for agents, with an ",
    aboutAgentsAfter: " index, an agent guide and skills.",
    sourceCode: "Source code and documentation",
    theWiki: "The wiki",
    tourButton: "Take the 2-minute tour",
    architectureLink: "How it is built: the architecture",
  },

  documents: {
    sectionLabel: "Documents",
    number: (value) => `n° ${value}`,
    revision: (value) => `indice ${value}`,
    lot: (value) => `lot ${value}`,
    dated: (date) => `dated ${date}`,
    pageCompiled: (date) => `Page compiled ${date}`,
    current: "Current",
    superseded: "Superseded",
    supersededBy: (by) => `Superseded by ${by}`,
    supersededByRevision: (revision) => `indice ${revision}`,
    original: "Original ↗",
    downloadEml: "Download .eml",
    notPublished: "Original not published",
    notPublishedTitle:
      "Originals are published only for the public fictional sample, and never for a document " +
      "the safety checks flagged (its full text is shown with the flagged passage withheld).",
    viewDocument: "View document",
    wikiPage: "Wiki page",
    inRelease: (count) => `${plural(count, "document")} in this release`,
    supersededLater: (count) => `${count} superseded by a later indice`,
    asOf: (date) => `as of ${date}`,
    formats: {
      pdf: "PDF",
      docx: "Word",
      xlsx: "Excel",
      csv: "CSV",
      pptx: "PowerPoint",
      eml: "E-mail",
      jpg: "Photo",
      jpeg: "Photo",
      png: "Image",
      txt: "Text",
      md: "Text",
      vtt: "Transcript",
    },
    provenance: "Provenance",
    sourcePage: (title) => `Source page: ${title}`,
    originalDocument: (page) => `Original document${page ? `, page ${page}` : ""}`,
  },

  pipeline: {
    ownerTitle: "Add a document to the wiki",
    ownerText:
      "Only the owner adds documents. Everyone can follow each one through the pipeline below, " +
      "then read it in the wiki.",
    liveLabel: "The process, live",
    placeholder: "Live status appears here on the deployed site.",
    stepsSummary: (count) => `The ${count} technical steps`,
    stepColumn: "Step",
    whatColumn: "What it does",
    unavailable: "Status unavailable, retrying…",
    phases: { read: "Read", file: "File", write: "Write", check: "Check and publish" },
    allPhasesDone: (count) => `All ${count} phases done`,
    failedAtPhase: (index, count, word) => `Failed at phase ${index} of ${count}: ${word}`,
    notStarted: (count) => `Not started: ${count} phases to go`,
    phaseOf: (index, count, word) => `Phase ${index} of ${count}: ${word}`,
    step: (of) => `step ${of}`,
    pages: (count) => plural(count, "page"),
    pagesAdded: "Pages added",
    pagesChanged: "Pages changed",
    pagesRemoved: "Pages removed",
    changedWords: { added: () => "added", changed: () => "changed", removed: () => "removed" },
    contradictionsOpened: (count) => `${plural(count, "contradiction")} opened`,
    contradictionsClosed: (count, first) =>
      `${first ? plural(count, "contradiction") : String(count)} closed`,
    noChangeRebuild: "This release rebuilt the site; no page changed.",
    noChange: "No page changed in this release.",
    runAtWork: "Run at work",
    runAtWorkStage: (stage) => `Run at work: ${stage}`,
    runAtWorkStep: (stage, step, count) => `Run at work: ${stage} (step ${step}/${count})`,
    runDocuments: (count, names) => `${plural(count, "document")}: ${names}`,
    moreChanges: (count) => `and ${plural(count, "more change")}`,
    docProcessing: (name, phase, step) => `${name}: ${phase}${step === null ? "" : ` (${step})`}`,
    docState: {
      received: (name) => `${name} received`,
      queued: (name) => `${name} is queued`,
      processing: (name) => `${name} is processing`,
      in_wiki: (name) => `${name} is in the wiki`,
      superseded: (name) => `${name} is superseded`,
      held_back: (name) => `${name} is held back`,
      failed: (name) => `${name} failed`,
      removed: (name) => `${name} was removed`,
    },
    releaseFacts: (id, when) => `Release ${id}, published ${when}`,
    sources: (count) => plural(count, "source"),
    pageCount: (count) => plural(count, "page"),
    noRelease: "No release published yet",
    queue: (count) => `queue: ${count}`,
    working: (count) => `Working — ${plural(count, "document")} in the pipeline`,
    workingQueued: "Working — a run is queued",
    workingRun: "Working — a run is in progress",
    idle: "Idle — the wiki is up to date",
    heading: "Pipeline",
    latestRun: (kind, when, state) => `Latest run: ${kind}, started ${when} — ${state}`,
    noRun: "No run recorded yet.",
    stageStatus: {},
    original: "Original",
    received: (when) => `received ${when}`,
    documentPage: "Document page",
    pagesAndText: "Pages and full text",
    notInWiki: "not in the wiki yet",
    statusLabel: "Status",
    wikiPages: (count) => plural(count, "wiki page"),
    documentChange: (change) => `document ${change}`,
    lastRun: "Its last run",
    noRecordedRun: "No recorded run changed it",
    wikiPage: "Wiki page",
    yourUpload: "your upload",
    notInAudience: "not in this site's audience",
    earlierFailed: "an earlier attempt failed",
    follow: "Follow this document",
    receivedWaiting: "received — waiting for the pipeline",
    documentsTitle: "Documents",
    documentsCount: (count) => `Documents (${count})`,
    noDocuments: "No documents yet.",
    columns: { status: "Status", document: "Document", received: "Received" },
    showAll: (count) => `Show all ${count}`,
    runSourcesHead: (total) => (total === null ? "sources" : plural(total, "source")),
    runCounts: {},
    whatChanged: "What changed in this release",
    contradictionsOpenedLabel: "Contradictions opened",
    contradictionsClosedLabel: "Contradictions closed",
    runsTitle: "Runs that published a release",
    checks: (count, last) =>
      `${plural(count, "scheduled check")} found nothing to do${last ? `, the last ${last}` : ""}.`,
    noRunYet: "No run yet — the owner adds a document to start one.",
    currentRelease: "current release",
    started: (when) => `started ${when}`,
    rebuiltOnly: "no document changed: the site was rebuilt",
    gates: (list) => `gates: ${list}`,
    gateWords: {},
    runKinds: {},
    runStatus: {},
    signedInAs: (name) => `Signed in as ${name ?? "the owner"}`,
    signOut: "sign out",
    signInToAdd: "Sign in to add a document",
    tooManyFolders: (count) => `Use at most ${count} folders.`,
    badName: (name) =>
      `“${name}” cannot be used: names use letters, digits, spaces and ._()+- only.`,
    pathTooLong: "The path is too long.",
    failed: (what, status) => `${what} failed (HTTP ${status}).`,
    theUpload: "The upload",
    theRebuild: "The rebuild",
    addDocument: "Add a document",
    documentLabel: "Document",
    folderLabel: "Folder (optional)",
    folderPlaceholder: "for example planning, devis or achats",
    replace: " Replace if it exists",
    addToWiki: "Add to the wiki",
    uploadHint: (maxMb, left, extensions) =>
      `Up to ${maxMb} MB · ${plural(left, "upload")} left today · ${extensions}`,
    chooseFirst: "Choose a document first.",
    badType: (extensions) => `This file type cannot be added; use ${extensions}.`,
    emptyFile: "The file is empty.",
    tooLarge: (maxMb) => `The file is larger than ${maxMb} MB.`,
    uploading: (path) => `Uploading ${path}…`,
    uploaded: (path) => `Uploaded ${path}. The pipeline starts within a minute: `,
    followLive: "follow it live",
    uploadUnreachable:
      "The upload did not reach the portal; check the connection and try again.",
    rebuild: "Rebuild the wiki",
    rebuildHint: (perDay, left) =>
      "Rebuilds every page and the site from the cache; about $0 when no document changed; " +
      `at most ${perDay} a day, ${left} left.`,
    askingRebuild: "Asking for a rebuild…",
    rebuildQueued: "Rebuild queued: it starts within a minute; follow it in the pipeline below.",
    rebuildUnreachable:
      "The rebuild request did not reach the portal; check the connection and try again.",
    sizeUnits: ["B", "KB", "MB"],
  },

  evals: {
    heading: "Wiki + agent vs RAG",
    intro:
      "The same golden questions asked three ways: the Researcher agent working in this wiki, " +
      "one model reading every document at once, and classic retrieval over chunks.",
    caption: "Evaluation of three ways to answer questions about the same documents",
    system: "System",
    systems: {
      "docwiki-researcher": "Wiki + Researcher agent",
      "baseline-long-context": "Long context (all documents)",
      "baseline-rag": "RAG (chunks)",
    },
    accuracy: "Answer accuracy",
    numeric: "Exact numbers",
    cost: "Cost / question",
    latency: "Median time",
    run: (questions, split, date) =>
      [questions === null ? null : `${questions} ${split} questions`, date && `run ${date}`]
        .filter(Boolean)
        .join(" · "),
    estimated: "Costs are estimates from list prices.",
    scoreboard: "Full scoreboard on GitHub",
    percent: (value) => `${Math.round(value * 100)} %`,
    seconds: (value) => `${value.toFixed(0)} s`,
    money: (value) => `$${value.toFixed(value < 0.1 ? 3 : 2)}`,
  },

  tour: {
    label: "Guided tour",
    stepOf: (step, count) => `Step ${step} of ${count}`,
    back: "Back",
    next: "Next",
    done: "Done",
    close: "Close the tour",
    steps: [
      {
        title: "The documents",
        body:
          "Everything starts from ordinary files: quotes, contracts, plans, e-mails, scans. " +
          "Each one keeps its original, exactly as it was received.",
      },
      {
        title: "A source page and its evidence",
        body:
          "A model compiled this page from one document. Every fact is cited, and the document " +
          "and its original are one click away.",
      },
      {
        title: "The pipeline",
        body:
          "Runs, stages, quality gates and cost: a blocking gate stops the release, and each " +
          "run shows how long it took and what it cost.",
      },
      {
        title: "A topic with citations",
        body:
          "Topic pages combine several documents. Each footnote opens the exact passage a fact " +
          "came from.",
      },
      {
        title: "Ask the Researcher",
        body:
          "The Researcher agent answers from the wiki, with its citations checked before they " +
          "are shown. An example question is ready: ask it, or write yours.",
      },
      {
        title: "Does it pay off?",
        body:
          "The same questions answered by the wiki and its agent, by a long-context model and by " +
          "RAG. The quality report shows the gates of this release.",
      },
    ],
    missing: "(This part is not shown on this copy of the site.)",
    qualityReport: "Quality report",
    architecture: "Architecture",
  },

  architecture: {
    figureLabel: "Architecture diagram",
    caption:
      "Documents → pipeline job → release with quality gates → this site and the MCP server → " +
      "Foundry agents.",
    openFull: "Open the diagram full size",
  },

  ask: {
    title: "Ask this wiki",
    subtitleLive: "Ask the Researcher agent. Its citations are checked before they are shown.",
    subtitleFiled: "Answers by the Researcher agent, reviewed before publishing",
    close: "Close Ask this wiki",
    closeTitle: "Close (Esc)",
    footerBefore: "You can also ",
    footerLink: "connect your coding agent to this wiki (MCP)",
    tryThese: "Try one of these",
    yourLive: "Your live questions",
    aboutPage: "About this page",
    moreQuestions: "More questions",
    questions: "Questions",
    noAnswers: "No answers have been filed yet.",
    askLabel: "Ask the Researcher",
    askButton: "Ask",
    hint:
      "Live answers are checked against the sources before they are shown. " +
      "The owner has not reviewed them.",
    source: (n, title, label) => `Source ${n}: ${title} — ${label}`,
    back: "Back to questions",
    pagesInWiki: "Pages in the wiki",
    sources: "Sources",
    steps: (count) => `How the agent worked (${plural(count, "step")})`,
    filedOn: (date) => `Filed on ${date}`,
    openAsPage: "Open as a page",
    loadFailed: "The answers could not be loaded.",
    tryAgain: "Try again",
    loading: "Loading answers…",
    backToAnswer: "Back to the answer",
    liveFailed: "The live agent could not be reached. Please try again later.",
    tooShort: "Please ask a complete question.",
    tooLong: (max) => `Please keep the question under ${max} characters.`,
    waiting: (seconds) => `The Researcher is reading the wiki… ${seconds} s`,
    liveSteps: {
      "tool:answer_context": "Finding the wiki pages for the question",
      "tool:search": "Searching the wiki",
      "tool:read_page": "Reading a wiki page",
      "tool:get_evidence": "Opening the evidence",
      "tool:query_table": "Querying a table",
      "tool:glossary": "Checking the glossary",
      "tool:get_links": "Following links",
      "tool:get_index": "Reading an index",
      "tool:list_skills": "Looking at the wiki's skills",
      "tool:get_skill": "Reading a skill",
      "tool:recent_changes": "Reading the latest changes",
      tool: "Using a wiki tool",
      writing: "Writing the answer",
    },
    examples: [
      "When are the windows of the extension delivered?",
      "Which architect designed the extension of the Moreau house?",
      "What is the current total contract price of the works, excluding and including VAT?",
    ],
  },
}
