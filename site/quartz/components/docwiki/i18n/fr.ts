// Chaînes françaises de l'interface (les pages canoniques, à la racine du site). Typées par
// `Strings` (strings.ts) ; en.ts a les mêmes clés. Le singulier vaut pour 0 et 1.
import type { Strings } from "./strings.ts"

/** "1 document", "0 document", "3 documents"; `many` when the plural is not word + s. */
function plural(count: number, one: string, many: string = `${one}s`): string {
  return `${count} ${count > 1 ? many : one}`
}

/** "ajoutée" / "ajoutées": a past participle agreed with its count (feminine nouns). */
function agreed(count: number, word: string): string {
  return count > 1 ? `${word}s` : word
}

function decimal(value: number, digits: number): string {
  return value.toFixed(digits).replace(".", ",")
}

function money(total: number, currency: string | null): string {
  const tiny = total > 0 && total < 0.005
  const amount = tiny ? "< 0,01" : decimal(total, 2)
  return `${amount} ${currency === null || currency === "USD" ? "$" : currency}`
}

export const fr: Strings = {
  lang: "fr",
  locale: "fr-FR",
  dateLocale: "fr-FR",
  decimal: ",",

  header: {
    tabs: { documents: "Documents", pipeline: "Traitement", wiki: "Wiki" },
    chipIdle: "Au repos",
    chipProcessing: (count) =>
      count > 0 ? `En cours (${count})` : "En cours",
    chipInWiki: "Dans le wiki → nouvelle page",
    chipTitleInWiki: (title) => `Dans le wiki : ${title}`,
    chipTitleIdle: "Le traitement est au repos ; l'ouvrir",
    chipLive: (words) => `Traitement : ${words}`,
    signIn: "Connexion",
    signInTitle: "Connexion du propriétaire : seul le propriétaire ajoute des documents",
    owner: "Propriétaire ✓",
    ownerTitle: "Connecté comme propriétaire : ajoutez des documents sur la page Traitement",
    languageNav: "Langue",
    languageNames: { en: "English", fr: "Français" },
  },

  a11y: {
    skip: "Aller au contenu",
    wikiNav: "Wiki",
    aboutPage: "À propos de cette page",
    browseWiki: "Parcourir le wiki",
    newTab: " (s'ouvre dans un nouvel onglet)",
    breadcrumbs: "Fil d'Ariane",
  },

  wiki: {
    explorerTitle: "Parcourir",
    breadcrumbRoot: "Wiki",
    documents: "Documents",
    bannerLabel: "Exemple fictif.",
    bannerText:
      "Les entreprises, personnes, chantiers et documents de ce wiki sont tous inventés. " +
      "Ne pas utiliser en situation réelle.",
    builtWith: "Réalisé avec",
    and: "et",
    release: "version",
    audience: "diffusion",
    scrollSideways: "Faire défiler vers la droite →",
    table: "Tableau",
    tableNamed: (heading) => `Tableau : ${heading}`,
    openImage: "Ouvrir l'image en taille réelle",
    provenanceBadges: "Badges de provenance",
    footnotes: "Notes",
    footnoteBack: (reference) => `Retour à l'appel de note ${reference}`,
    untranslated: "Non traduit",
    globalGraph: "Graphe global",
    rssFeed: "Flux RSS",
  },

  badges: {
    citation: {
      verified: {
        text: "✓ citation vérifiée",
        meaning: "les mots cités figurent mot pour mot dans le texte du document",
      },
      paraphrase: {
        text: "reformulation",
        meaning: "reformulé à partir du texte du document ; chiffres vérifiés, pas de citation exacte",
      },
      table: {
        text: "tableau",
        meaning: "valeurs lues par le code dans les lignes citées du tableau",
      },
      ocr: {
        text: "OCR",
        meaning: "texte reconnu sur une image ; à comparer avec l'image",
      },
      generated: {
        text: "description générée",
        meaning: "rédigée par un modèle pour décrire une figure ; ce n'est pas une citation",
      },
    },
    provenance: {
      "native-text": {
        text: "texte natif",
        meaning: "repris de la couche texte du document lui-même",
      },
      "deterministic-table": {
        text: "tableau",
        meaning: "valeurs des cellules lues par le code dans le fichier",
      },
      ocr: {
        text: "OCR",
        meaning: "texte reconnu sur les pixels ; à vérifier sur l'image",
      },
      "model-description": {
        text: "description générée",
        meaning: "rédigée par un modèle ; ne jamais la citer comme une citation",
      },
    },
  },

  status: {
    received: "Reçu",
    queued: "En file",
    processing: "En cours",
    in_wiki: "Dans le wiki",
    superseded: "Remplacé",
    held_back: "Retenu",
    failed: "Échec",
    removed: "Retiré",
  },

  words: {
    documents: (count) => plural(count, "document"),
    documentsPhrase: (current, superseded) => {
      const total = plural(current + superseded, "document")
      return superseded > 0 ? `${total} (${plural(superseded, "remplacé")})` : total
    },
    quality: (q) => {
      if (q.blockingFailed > 0) {
        return `${plural(q.blockingFailed, "contrôle bloquant", "contrôles bloquants")} en échec`
      }
      const parts = [plural(q.passed, "réussi")]
      if (q.warned > 0) parts.push(plural(q.warned, "avertissement"))
      if (q.skipped > 0) parts.push(plural(q.skipped, "non exécuté", "non exécutés"))
      return parts.join(", ")
    },
    andMore: (count) => `et ${count} de plus`,
    money,
    lastRun: (parts) => `dernière exécution ${parts}`,
  },

  story: {
    heading: "Comment ce wiki est fait",
    lede:
      "Un LLM compile des documents d'entreprise ordinaires en un wiki où chaque fait est " +
      "cité, et un agent répond à partir de ce wiki.",
    pocBefore:
      "Une preuve de concept publique sur Azure, menée sur les documents inventés d'une " +
      "entreprise du bâtiment. Le code est ",
    pocLink: "open source",
    pocAfter: " ; les trois onglets ci-dessus suivent les trois mêmes étapes.",
    current: (current, superseded) =>
      `${plural(current, "en vigueur", "en vigueur")} · ${plural(superseded, "remplacé")}`,
    originals: "les originaux",
    openDocuments: " — ouvrir l'onglet Documents",
    steps: (count) => `Traitement en ${count} étapes`,
    stepsDetail: "lire · rédiger · vérifier · publier",
    openPipeline: " — ouvrir l'onglet Traitement",
    citedPages: (count) => plural(count, "page citée", "pages citées"),
    citedDetail: "chaque fait ouvre sa source",
    goToWiki: " — aller au wiki ci-dessous",
    tryLabel: "Essayez :",
    tryOpens: " (ouvre Interroger ce wiki)",
    aboutLabel: "À propos de ce wiki",
    compiledBy: "Compilé par",
    from: "à partir de",
    release: "version du",
    qualityGates: "contrôles qualité :",
    runReceipt: "reçu d'exécution",
    qualityReport: "rapport qualité",
    thePipeline: "le traitement",
    aboutDocwiki: "À propos de DocWiki",
    aboutIntro:
      "Ce site a été produit par DocWiki, qui compile un dossier de documents (PDF, Word, " +
      "Excel, CSV, PowerPoint, e-mails, scans et transcriptions) en un wiki Markdown que les " +
      "personnes peuvent parcourir et auquel les agents peuvent se fier.",
    aboutFootnotes:
      "Chaque fait se termine par une note qui ouvre sa preuve : la page, le paragraphe ou les " +
      "lignes de tableau exacts dont il provient, avec un badge de provenance.",
    aboutContradictions:
      "Les contradictions entre documents et les indices remplacés sont montrés côte à côte, " +
      "jamais tranchés en silence.",
    aboutAgentsBefore:
      "La même version, figée, est livrée en Markdown brut pour les agents, avec un index ",
    aboutAgentsAfter: ", un guide pour les agents et des compétences.",
    sourceCode: "Code source et documentation",
    theWiki: "Le wiki",
    tourButton: "Faire la visite en 2 minutes",
    architectureLink: "Comment c'est construit : l'architecture",
  },

  documents: {
    sectionLabel: "Documents",
    number: (value) => `n° ${value}`,
    revision: (value) => `indice ${value}`,
    lot: (value) => `lot ${value}`,
    dated: (date) => `du ${date}`,
    pageCompiled: (date) => `Page compilée le ${date}`,
    current: "En vigueur",
    superseded: "Remplacé",
    supersededBy: (by) => `Remplacé par ${by}`,
    supersededByRevision: (revision) => `l'indice ${revision}`,
    original: "Original ↗",
    downloadEml: "Télécharger le .eml",
    notPublished: "Original non publié",
    notPublishedTitle:
      "Les originaux ne sont publiés que pour l'exemple fictif public, et jamais pour un " +
      "document signalé par les contrôles de sécurité (son texte intégral est affiché sans le " +
      "passage signalé).",
    viewDocument: "Voir le document",
    wikiPage: "Page du wiki",
    inRelease: (count) => `${plural(count, "document")} dans cette version`,
    supersededLater: (count) =>
      `${plural(count, "remplacé", "remplacés")} par un indice plus récent`,
    asOf: (date) => `au ${date}`,
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
      txt: "Texte",
      md: "Texte",
      vtt: "Transcription",
    },
    provenance: "Provenance",
    sourcePage: (title) => `Page du document : ${title}`,
    originalDocument: (page) => `Document original${page ? `, page ${page}` : ""}`,
  },

  pipeline: {
    ownerTitle: "Ajouter un document au wiki",
    ownerText:
      "Seul le propriétaire ajoute des documents. Chacun peut suivre chaque document dans le " +
      "traitement ci-dessous, puis le lire dans le wiki.",
    liveLabel: "Le traitement, en direct",
    placeholder: "L'état en direct s'affiche ici sur le site déployé.",
    stepsSummary: (count) => `Les ${count} étapes techniques`,
    stepColumn: "Étape",
    whatColumn: "Ce qu'elle fait",
    unavailable: "État indisponible, nouvel essai…",
    phases: { read: "Lire", file: "Classer", write: "Rédiger", check: "Vérifier et publier" },
    allPhasesDone: (count) => `Les ${count} phases sont faites`,
    failedAtPhase: (index, count, word) => `Échec à la phase ${index} sur ${count} : ${word}`,
    notStarted: (count) => `Pas commencé : ${count} phases à faire`,
    phaseOf: (index, count, word) => `Phase ${index} sur ${count} : ${word}`,
    step: (of) => `étape ${of}`,
    pages: (count) => plural(count, "page"),
    pagesAdded: "Pages ajoutées",
    pagesChanged: "Pages modifiées",
    pagesRemoved: "Pages supprimées",
    changedWords: {
      added: (count) => agreed(count, "ajoutée"),
      changed: (count) => agreed(count, "modifiée"),
      removed: (count) => agreed(count, "supprimée"),
    },
    contradictionsOpened: (count) =>
      `${plural(count, "contradiction")} ${agreed(count, "ouverte")}`,
    contradictionsClosed: (count, first) =>
      `${first ? plural(count, "contradiction") : String(count)} ${agreed(count, "résolue")}`,
    noChangeRebuild: "Cette version a reconstruit le site ; aucune page n'a changé.",
    noChange: "Aucune page n'a changé dans cette version.",
    runAtWork: "Exécution en cours",
    runAtWorkStage: (stage) => `Exécution en cours : ${stage}`,
    runAtWorkStep: (stage, step, count) =>
      `Exécution en cours : ${stage} (étape ${step}/${count})`,
    runDocuments: (count, names) => `${plural(count, "document")} : ${names}`,
    moreChanges: (count) =>
      `et ${plural(count, "autre changement", "autres changements")}`,
    docProcessing: (name, phase, step) =>
      `${name} : ${phase}${step === null ? "" : ` (${step})`}`,
    docState: {
      received: (name) => `${name} reçu`,
      queued: (name) => `${name} est en file`,
      processing: (name) => `${name} est en cours`,
      in_wiki: (name) => `${name} est dans le wiki`,
      superseded: (name) => `${name} est remplacé`,
      held_back: (name) => `${name} est retenu`,
      failed: (name) => `${name} : échec`,
      removed: (name) => `${name} a été retiré`,
    },
    releaseFacts: (id, when) => `Version ${id}, publiée le ${when}`,
    sources: (count) => plural(count, "source"),
    pageCount: (count) => plural(count, "page"),
    noRelease: "Aucune version publiée pour l'instant",
    queue: (count) => `file d'attente : ${count}`,
    working: (count) => `En cours — ${plural(count, "document")} dans le traitement`,
    workingQueued: "En cours — une exécution est en file",
    workingRun: "En cours — une exécution est en cours",
    idle: "Au repos — le wiki est à jour",
    heading: "Traitement",
    latestRun: (kind, when, state) => `Dernière exécution : ${kind}, lancée le ${when} — ${state}`,
    noRun: "Aucune exécution enregistrée pour l'instant.",
    stageStatus: {
      done: "fait",
      running: "en cours",
      pending: "en cours",
      failed: "échec",
      quarantined: "en quarantaine",
      skipped: "sauté",
      "not run": "non exécuté",
      finished: "terminée",
    },
    original: "Original",
    received: (when) => `reçu le ${when}`,
    documentPage: "Page du document",
    pagesAndText: "Pages et texte intégral",
    notInWiki: "pas encore dans le wiki",
    statusLabel: "État",
    wikiPages: (count) => plural(count, "page du wiki", "pages du wiki"),
    documentChange: (change) =>
      `document ${{ new: "nouveau", changed: "modifié", deleted: "supprimé", rebuilt: "reconstruit" }[change] ?? change}`,
    lastRun: "Sa dernière exécution",
    noRecordedRun: "Aucune exécution enregistrée ne l'a modifié",
    wikiPage: "Page du wiki",
    yourUpload: "votre dépôt",
    notInAudience: "hors de la diffusion de ce site",
    earlierFailed: "une tentative précédente a échoué",
    follow: "Suivre ce document",
    receivedWaiting: "reçu — en attente du traitement",
    documentsTitle: "Documents",
    documentsCount: (count) => `Documents (${count})`,
    noDocuments: "Aucun document pour l'instant.",
    columns: { status: "État", document: "Document", received: "Reçu le" },
    showAll: (count) => `Tout afficher (${count})`,
    runSourcesHead: (total) => (total === null ? "sources" : plural(total, "source")),
    runCounts: {
      new: (count) => plural(count, "nouvelle", "nouvelles"),
      changed: (count) => plural(count, "modifiée", "modifiées"),
      deleted: (count) => plural(count, "supprimée", "supprimées"),
      unchanged: (count) => plural(count, "inchangée", "inchangées"),
      quarantined: (count) => `${count} en quarantaine`,
      failed: (count) => plural(count, "en échec", "en échec"),
    },
    whatChanged: "Ce qui a changé dans cette version",
    contradictionsOpenedLabel: "Contradictions ouvertes",
    contradictionsClosedLabel: "Contradictions résolues",
    runsTitle: "Exécutions qui ont publié une version",
    checks: (count, last) =>
      `${plural(count, "vérification planifiée", "vérifications planifiées")} : rien à faire` +
      `${last ? `, la dernière le ${last}` : ""}.`,
    noRunYet: "Aucune exécution pour l'instant — le propriétaire ajoute un document pour en lancer une.",
    currentRelease: "version en ligne",
    started: (when) => `lancée le ${when}`,
    rebuiltOnly: "aucun document modifié : le site a été reconstruit",
    gates: (list) => `contrôles : ${list}`,
    gateWords: { pass: "réussis", warn: "avertissements", fail: "en échec", skipped: "non exécutés" },
    runKinds: {
      ingest: "intégration",
      recompile: "recompilation",
      rebuild: "reconstruction",
      reconcile: "rapprochement",
      run: "exécution",
      // Who asked for the run.
      librarian: "Librarian",
      event: "événement",
      cli: "ligne de commande",
      schedule: "planifiée",
      owner: "propriétaire",
    },
    runStatus: {
      running: "en cours",
      succeeded: "réussie",
      failed: "échec",
      "no-op": "rien à faire",
      finished: "terminée",
    },
    signedInAs: (name) => `Connecté comme ${name ?? "propriétaire"}`,
    signOut: "se déconnecter",
    signInToAdd: "Se connecter pour ajouter un document",
    tooManyFolders: (count) => `Utilisez au plus ${count} dossiers.`,
    badName: (name) =>
      `« ${name} » ne peut pas être utilisé : seuls les lettres, chiffres, espaces et ._()+- ` +
      "sont acceptés.",
    pathTooLong: "Le chemin est trop long.",
    failed: (what, status) => `${what} a échoué (HTTP ${status}).`,
    theUpload: "Le dépôt",
    theRebuild: "La reconstruction",
    addDocument: "Ajouter un document",
    documentLabel: "Document",
    folderLabel: "Dossier (facultatif)",
    folderPlaceholder: "par exemple planning, devis ou achats",
    replace: " Remplacer s'il existe",
    addToWiki: "Ajouter au wiki",
    uploadHint: (maxMb, left, extensions) =>
      `Jusqu'à ${maxMb} Mo · ${plural(left, "dépôt")} ${left > 1 ? "restants" : "restant"} ` +
      `aujourd'hui · ${extensions}`,
    chooseFirst: "Choisissez d'abord un document.",
    badType: (extensions) => `Ce type de fichier ne peut pas être ajouté ; utilisez ${extensions}.`,
    emptyFile: "Le fichier est vide.",
    tooLarge: (maxMb) => `Le fichier dépasse ${maxMb} Mo.`,
    uploading: (path) => `Envoi de ${path}…`,
    uploaded: (path) => `${path} est déposé. Le traitement démarre dans la minute : `,
    followLive: "suivez-le en direct",
    uploadUnreachable:
      "Le dépôt n'a pas atteint le portail ; vérifiez la connexion et réessayez.",
    rebuild: "Reconstruire le wiki",
    rebuildHint: (perDay, left) =>
      "Reconstruit chaque page et le site à partir du cache ; environ 0 $ si aucun document " +
      `n'a changé ; au plus ${perDay} par jour, ${left} ${left > 1 ? "restantes" : "restante"}.`,
    askingRebuild: "Demande de reconstruction…",
    rebuildQueued:
      "Reconstruction en file : elle démarre dans la minute ; suivez-la dans le traitement " +
      "ci-dessous.",
    rebuildUnreachable:
      "La demande de reconstruction n'a pas atteint le portail ; vérifiez la connexion et " +
      "réessayez.",
    sizeUnits: ["o", "Ko", "Mo"],
  },

  evals: {
    heading: "Wiki + agent face au RAG",
    intro:
      "Les mêmes questions de référence posées de trois façons : l'agent Researcher qui " +
      "travaille dans ce wiki, un modèle qui lit tous les documents d'un coup, et une recherche " +
      "classique par extraits.",
    caption: "Évaluation de trois façons de répondre aux questions sur les mêmes documents",
    system: "Système",
    systems: {
      "docwiki-researcher": "Wiki + agent Researcher",
      "baseline-long-context": "Contexte long (tous les documents)",
      "baseline-rag": "RAG (extraits)",
    },
    accuracy: "Réponses justes",
    numeric: "Chiffres exacts",
    cost: "Coût / question",
    latency: "Temps médian",
    run: (questions, split, date) =>
      [
        questions === null ? null : `${questions} questions (${split})`,
        date && `exécution du ${date}`,
      ]
        .filter(Boolean)
        .join(" · "),
    estimated: "Coûts estimés d'après les prix publics.",
    scoreboard: "Tableau complet sur GitHub",
    percent: (value) => `${Math.round(value * 100)} %`,
    seconds: (value) => `${value.toFixed(0)} s`,
    money: (value) => `${value.toFixed(value < 0.1 ? 3 : 2).replace(".", ",")} $`,
  },

  tour: {
    label: "Visite guidée",
    stepOf: (step, count) => `Étape ${step} sur ${count}`,
    back: "Précédent",
    next: "Suivant",
    done: "Terminer",
    close: "Fermer la visite",
    steps: [
      {
        title: "Les documents",
        body:
          "Tout part de fichiers ordinaires : devis, marchés, plans, e-mails, scans. Chacun garde " +
          "son original, tel qu'il a été reçu.",
      },
      {
        title: "Une page de document et ses preuves",
        body:
          "Un modèle a rédigé cette page à partir d'un seul document. Chaque fait est cité, et le " +
          "document comme son original sont à un clic.",
      },
      {
        title: "Le traitement",
        body:
          "Exécutions, étapes, contrôles qualité et coût : un contrôle bloquant arrête la " +
          "publication, et chaque exécution affiche sa durée et son coût.",
      },
      {
        title: "Une synthèse citée",
        body:
          "Les pages de synthèse croisent plusieurs documents. Chaque note de bas de page ouvre " +
          "le passage exact d'où vient le fait.",
      },
      {
        title: "Interroger le Researcher",
        body:
          "L'agent Researcher répond à partir du wiki, et ses citations sont vérifiées avant " +
          "d'être affichées. Une question d'exemple est prête : posez-la, ou écrivez la vôtre.",
      },
      {
        title: "Est-ce que ça vaut le coup ?",
        body:
          "Les mêmes questions traitées par le wiki et son agent, par un modèle à contexte long " +
          "et par du RAG. Le rapport qualité montre les contrôles de cette version.",
      },
    ],
    missing: "(Cette partie n'est pas affichée sur cette copie du site.)",
    qualityReport: "Rapport qualité",
    architecture: "Architecture",
  },

  architecture: {
    figureLabel: "Schéma d'architecture",
    caption:
      "Documents → job de traitement → version contrôlée → ce site et le serveur MCP → " +
      "agents Foundry.",
    openFull: "Ouvrir le schéma en grand",
  },

  ask: {
    title: "Interroger ce wiki",
    subtitleLive:
      "Posez votre question à l'agent Researcher. Ses citations sont vérifiées avant d'être " +
      "affichées.",
    subtitleFiled: "Réponses de l'agent Researcher, relues avant publication",
    close: "Fermer Interroger ce wiki",
    closeTitle: "Fermer (Échap)",
    footerBefore: "Vous pouvez aussi ",
    footerLink: "connecter votre agent de code à ce wiki (MCP)",
    tryThese: "Essayez l'une de ces questions",
    yourLive: "Vos questions en direct",
    aboutPage: "Sur cette page",
    moreQuestions: "Autres questions",
    questions: "Questions",
    noAnswers: "Aucune réponse n'a encore été classée.",
    askLabel: "Poser une question au Researcher",
    askButton: "Demander",
    hint:
      "Les réponses en direct sont vérifiées par rapport aux sources avant d'être affichées. " +
      "Le propriétaire ne les a pas relues.",
    source: (n, title, label) => `Source ${n} : ${title} — ${label}`,
    back: "Retour aux questions",
    pagesInWiki: "Pages du wiki",
    sources: "Sources",
    steps: (count) => `Comment l'agent a travaillé (${plural(count, "étape")})`,
    filedOn: (date) => `Classée le ${date}`,
    openAsPage: "Ouvrir comme une page",
    loadFailed: "Les réponses n'ont pas pu être chargées.",
    tryAgain: "Réessayer",
    loading: "Chargement des réponses…",
    backToAnswer: "Retour à la réponse",
    liveFailed: "L'agent en direct est injoignable. Réessayez plus tard.",
    tooShort: "Posez une question complète.",
    tooLong: (max) => `La question doit faire moins de ${max} caractères.`,
    waiting: (seconds) => `Le Researcher lit le wiki… ${seconds} s`,
    liveSteps: {
      "tool:answer_context": "Recherche des pages du wiki pour la question",
      "tool:search": "Recherche dans le wiki",
      "tool:read_page": "Lecture d'une page du wiki",
      "tool:get_evidence": "Ouverture de la preuve",
      "tool:query_table": "Interrogation d'un tableau",
      "tool:glossary": "Consultation du glossaire",
      "tool:get_links": "Suivi des liens",
      "tool:get_index": "Lecture d'un index",
      "tool:list_skills": "Consultation des skills du wiki",
      "tool:get_skill": "Lecture d'un skill",
      "tool:recent_changes": "Lecture des derniers changements",
      tool: "Utilisation d'un outil du wiki",
      writing: "Rédaction de la réponse",
    },
    examples: [
      "Quand les fenêtres de l'extension sont-elles livrées ?",
      "Quel architecte a conçu l'extension de la maison Moreau ?",
      "Quel est le montant actuel du marché de travaux, HT et TTC ?",
    ],
  },
}
