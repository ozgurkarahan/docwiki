// The overlay's UI strings, one table per language (en.ts, fr.ts), typed by `Strings` (ADR 0012,
// slice G). Pages are French at the root and English under `en/`: every component and inline
// script picks the table of its page's language. Locked trade terms (réception, avenant,
// situation, PV, réserves, DPGF, CCAP, PPSPS, conducteur de travaux…) stay untranslated in
// English. No imports: the tables are loaded by Node in the tests (tests/site).

/** A language of the site's UI (the wiki's languages that have a table). */
export type Lang = "en" | "fr"

export type StatusKey =
  | "received"
  | "queued"
  | "processing"
  | "in_wiki"
  | "superseded"
  | "held_back"
  | "failed"
  | "removed"

export type PhaseKey = "read" | "file" | "write" | "check"

export interface BadgeWords {
  text: string
  meaning: string
}

export interface Strings {
  lang: Lang
  /** BCP 47 locale for dates and numbers, and Quartz's own strings. */
  locale: "en-US" | "fr-FR"
  /** Locale of the short dates ("20 Jan 2026", "20 janv. 2026"). */
  dateLocale: string
  /** Decimal separator of the numbers written by the overlay. */
  decimal: "." | ","

  /** Header: the three tabs, the status chip, Sign in and the language switch. */
  header: {
    tabs: { documents: string; pipeline: string; wiki: string }
    chipIdle: string
    chipProcessing: (count: number) => string
    chipInWiki: string
    chipTitleInWiki: (title: string) => string
    chipTitleIdle: string
    chipLive: (words: string) => string
    signIn: string
    signInTitle: string
    owner: string
    ownerTitle: string
    languageNav: string
    /** Each language's name, in that language ("Français", "English"). */
    languageNames: Record<Lang, string>
  }

  /** Accessibility helpers: the skip link and the names of Quartz's regions. */
  a11y: {
    skip: string
    wikiNav: string
    aboutPage: string
    browseWiki: string
    newTab: string
    breadcrumbs: string
  }

  /** The wiki's chrome: explorer, breadcrumbs, banner, footer, tables. */
  wiki: {
    explorerTitle: string
    breadcrumbRoot: string
    documents: string
    bannerLabel: string
    /** The default fictional-sample notice (`DEFAULT_BANNER` of src/docwiki/site/build.py). */
    bannerText: string
    builtWith: string
    and: string
    release: string
    audience: string
    scrollSideways: string
    table: string
    tableNamed: (heading: string) => string
    openImage: string
    provenanceBadges: string
    /** The footnotes section's (hidden) heading and each back link's name ("1", "1-2"). */
    footnotes: string
    footnoteBack: (reference: string) => string
    /**
     * The first words of the notice of a mirror page kept untranslated (the engine's
     * `mirror.untranslated`, src/docwiki/contracts/i18n.py), without the colon.
     */
    untranslated: string
    /** Names Quartz leaves in English: the global graph button and the RSS feed link. */
    globalGraph: string
    rssFeed: string
  }

  /** Citation and provenance badges: the words shown for the wiki's (English) markers. */
  badges: {
    citation: Record<"verified" | "paraphrase" | "table" | "ocr" | "generated", BadgeWords>
    provenance: Record<"native-text" | "deterministic-table" | "ocr" | "model-description", BadgeWords>
  }

  /** The status vocabulary (ADR 0010): one word per state. */
  status: Record<StatusKey, string>

  /** Counted words and phrases shared by several components. */
  words: {
    documents: (count: number) => string
    documentsPhrase: (current: number, superseded: number) => string
    quality: (q: {
      passed: number
      warned: number
      skipped: number
      blockingFailed: number
    }) => string
    andMore: (count: number) => string
    /** "$1.37", "1,37 $", "EUR 1.37". */
    money: (total: number, currency: string | null) => string
    lastRun: (parts: string) => string
  }

  /** The home page: the story strip and "About this wiki". */
  story: {
    heading: string
    lede: string
    pocBefore: string
    pocLink: string
    pocAfter: string
    current: (current: number, superseded: number) => string
    originals: string
    openDocuments: string
    steps: (count: number) => string
    stepsDetail: string
    openPipeline: string
    citedPages: (count: number) => string
    citedDetail: string
    goToWiki: string
    tryLabel: string
    tryOpens: string
    aboutLabel: string
    compiledBy: string
    from: string
    release: string
    qualityGates: string
    runReceipt: string
    qualityReport: string
    thePipeline: string
    aboutDocwiki: string
    aboutIntro: string
    aboutFootnotes: string
    aboutContradictions: string
    aboutAgentsBefore: string
    aboutAgentsAfter: string
    sourceCode: string
    theWiki: string
    /** The button that starts the guided tour (Tour.tsx). */
    tourButton: string
    /** The link to the architecture page. */
    architectureLink: string
  }

  /** The home page's evaluation panel: the wiki and its agent against two baselines. */
  evals: {
    heading: string
    intro: string
    caption: string
    system: string
    systems: Record<string, string>
    accuracy: string
    numeric: string
    cost: string
    latency: string
    /** "32 dev questions · run 23 Oct 2026" */
    run: (questions: number | null, split: string, date: string | null) => string
    estimated: string
    scoreboard: string
    percent: (value: number) => string
    seconds: (value: number) => string
    money: (value: number) => string
  }

  /** The guided tour (Tour.tsx): six steps across the site's pages. */
  tour: {
    label: string
    stepOf: (step: number, count: number) => string
    back: string
    next: string
    done: string
    close: string
    steps: readonly { title: string; body: string }[]
    /** Added when a step's element is not on the page (a static host, an empty register). */
    missing: string
    qualityReport: string
    architecture: string
  }

  /** The architecture page (site.md §12.3). */
  architecture: {
    figureLabel: string
    caption: string
    openFull: string
  }

  /** Source pages and the documents register. */
  documents: {
    sectionLabel: string
    number: (value: string) => string
    revision: (value: string) => string
    lot: (value: string) => string
    dated: (date: string) => string
    pageCompiled: (date: string) => string
    current: string
    superseded: string
    supersededBy: (by: string) => string
    supersededByRevision: (revision: string) => string
    original: string
    downloadEml: string
    notPublished: string
    notPublishedTitle: string
    viewDocument: string
    wikiPage: string
    inRelease: (count: number) => string
    supersededLater: (count: number) => string
    asOf: (date: string) => string
    formats: Record<string, string>
    provenance: string
    sourcePage: (title: string) => string
    originalDocument: (page: number | null) => string
  }

  /** The pipeline page: owner's box, live view, steps, uploads and rebuilds. */
  pipeline: {
    ownerTitle: string
    ownerText: string
    liveLabel: string
    placeholder: string
    stepsSummary: (count: number) => string
    stepColumn: string
    whatColumn: string
    unavailable: string
    phases: Record<PhaseKey, string>
    allPhasesDone: (count: number) => string
    failedAtPhase: (index: number, count: number, word: string) => string
    notStarted: (count: number) => string
    phaseOf: (index: number, count: number, word: string) => string
    step: (of: string) => string
    pages: (count: number) => string
    pagesAdded: string
    pagesChanged: string
    pagesRemoved: string
    changedWords: Record<"added" | "changed" | "removed", (count: number) => string>
    contradictionsOpened: (count: number, first: boolean) => string
    contradictionsClosed: (count: number, first: boolean) => string
    noChangeRebuild: string
    noChange: string
    runAtWork: string
    runAtWorkStage: (stage: string) => string
    runAtWorkStep: (stage: string, step: number, count: number) => string
    runDocuments: (count: number, names: string) => string
    moreChanges: (count: number) => string
    docProcessing: (name: string, phase: string, step: string | null) => string
    docState: Record<StatusKey, (name: string) => string>
    releaseFacts: (id: string, when: string) => string
    sources: (count: number) => string
    pageCount: (count: number) => string
    noRelease: string
    queue: (count: string) => string
    working: (count: number) => string
    workingQueued: string
    workingRun: string
    idle: string
    heading: string
    latestRun: (kind: string, when: string, state: string) => string
    noRun: string
    /** Words of the stage, run and gate statuses, run kinds and requesters; a missing key shows
     * the portal's own word. */
    stageStatus: Record<string, string>
    original: string
    received: (when: string) => string
    documentPage: string
    pagesAndText: string
    notInWiki: string
    statusLabel: string
    wikiPages: (count: number) => string
    documentChange: (change: string) => string
    lastRun: string
    noRecordedRun: string
    wikiPage: string
    yourUpload: string
    notInAudience: string
    earlierFailed: string
    follow: string
    receivedWaiting: string
    documentsTitle: string
    documentsCount: (count: number) => string
    noDocuments: string
    columns: { status: string; document: string; received: string }
    showAll: (count: number) => string
    runSourcesHead: (total: number | null) => string
    /** Run counts by key (`new`, `unchanged`…); a missing key reads "<n> <key>". */
    runCounts: Record<string, (count: number) => string>
    whatChanged: string
    contradictionsOpenedLabel: string
    contradictionsClosedLabel: string
    runsTitle: string
    checks: (count: number, last: string | null) => string
    noRunYet: string
    currentRelease: string
    started: (when: string) => string
    rebuiltOnly: string
    gates: (list: string) => string
    gateWords: Record<string, string>
    runKinds: Record<string, string>
    runStatus: Record<string, string>
    signedInAs: (name: string | null) => string
    signOut: string
    signInToAdd: string
    tooManyFolders: (count: number) => string
    badName: (name: string) => string
    pathTooLong: string
    failed: (what: string, status: number) => string
    theUpload: string
    theRebuild: string
    addDocument: string
    documentLabel: string
    folderLabel: string
    folderPlaceholder: string
    replace: string
    addToWiki: string
    uploadHint: (maxMb: number, left: number, extensions: string) => string
    chooseFirst: string
    badType: (extensions: string) => string
    emptyFile: string
    tooLarge: (maxMb: number) => string
    uploading: (path: string) => string
    uploaded: (path: string) => string
    followLive: string
    uploadUnreachable: string
    rebuild: string
    rebuildHint: (perDay: number, left: number) => string
    askingRebuild: string
    rebuildQueued: string
    rebuildUnreachable: string
    sizeUnits: readonly [string, string, string]
  }

  /** The "Ask this wiki" drawer. */
  ask: {
    title: string
    subtitleLive: string
    subtitleFiled: string
    close: string
    closeTitle: string
    footerBefore: string
    footerLink: string
    tryThese: string
    yourLive: string
    aboutPage: string
    moreQuestions: string
    questions: string
    noAnswers: string
    askLabel: string
    askButton: string
    hint: string
    source: (n: number, title: string, label: string) => string
    back: string
    pagesInWiki: string
    sources: string
    steps: (count: number) => string
    filedOn: (date: string) => string
    openAsPage: string
    loadFailed: string
    tryAgain: string
    loading: string
    backToAnswer: string
    liveFailed: string
    tooShort: string
    tooLong: (max: number) => string
    waiting: (seconds: number) => string
    /** What the live agent is doing, by step key of the portal (`tool:search`, `writing`…). */
    liveSteps: Readonly<Record<string, string>>
    examples: readonly string[]
  }
}
