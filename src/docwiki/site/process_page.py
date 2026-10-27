"""The ``pipeline`` and ``documents`` pages (ADR 0009, 0010): the first two of the site's three
tabs, ① Documents · ② Pipeline · ③ Wiki.

The site build writes them next to the release's content, so they carry the wiki's navigation,
search and drawer. Their text is static. On ``pipeline`` the live part (the owner's box, each
document's status, the queue and the runs) is filled on the client from the portal's
``/api/process`` by the ``Process`` and ``OwnerBox`` components, which also show the 14 technical
steps of :data:`STAGES` in a disclosure. On ``documents`` the ``Documents`` component lists the
release's documents.

Both pages exist in each language of the wiki (ADR 0012): in the canonical language at the root
(``/pipeline``) and in each mirror under its folder (``/en/pipeline``), with the same slugs.
Languages other than French and English get the English text.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "ARCHITECTURE_SLUG",
    "DOCUMENTS_SLUG",
    "PROCESS_SLUG",
    "STAGES",
    "architecture_markdown",
    "documents_markdown",
    "process_markdown",
    "stages",
    "write_architecture_page",
    "write_documents_page",
    "write_process_page",
]

PROCESS_SLUG = "pipeline"
DOCUMENTS_SLUG = "documents"
ARCHITECTURE_SLUG = "architecture"

STAGES: tuple[tuple[str, str], ...] = (
    ("discover", "Lists the documents, spots what is new, changed or deleted, groups revisions."),
    ("extract", "Reads the text, tables and figures of each file, page by page and row by row."),
    ("classify", "Gives each document its type, revision and sensitivity (rules first)."),
    ("compile", "A model writes the source page: summary, key facts and sections, each cited."),
    ("entities", "Builds a page for each known thing (equipment, site, party) from the facts."),
    ("topics", "Writes topic pages across documents, with contradictions and superseded parts."),
    ("links", "Links pages to each other and adds the backlinks, by rule, not by a model."),
    ("indexes", "Writes the home page, indexes, glossary, change log and search index."),
    ("agentkit", "Writes the agent guide and skills from reviewed templates."),
    ("evidence", "Saves the exact passage behind every citation, with the original page image."),
    (
        "translate",
        "Writes the wiki in its other languages; numbers, citations and trade terms are checked.",
    ),
    ("verify", "Runs the quality gates: a blocking failure stops the release."),
    ("site", "Builds this website from the candidate release."),
    ("publish", "Publishes the release atomically: the site switches to it within a minute."),
)

_STAGES_FR: tuple[tuple[str, str], ...] = (
    (
        "discover",
        "Liste les documents, repère ce qui est nouveau, modifié ou supprimé, regroupe "
        "les indices d'un même document.",
    ),
    (
        "extract",
        "Lit le texte, les tableaux et les figures de chaque fichier, page par page et "
        "ligne par ligne.",
    ),
    (
        "classify",
        "Donne à chaque document son type, son indice et sa sensibilité (les règles d'abord).",
    ),
    (
        "compile",
        "Un modèle rédige la page du document : résumé, faits clés et sections, chacun cité.",
    ),
    (
        "entities",
        "Crée une page pour chaque élément connu (équipement, chantier, intervenant) à "
        "partir des faits.",
    ),
    (
        "topics",
        "Rédige les pages de synthèse entre documents, avec les contradictions et les "
        "parties remplacées.",
    ),
    (
        "links",
        "Relie les pages entre elles et ajoute les renvois, par des règles, pas par un modèle.",
    ),
    (
        "indexes",
        "Rédige la page d'accueil, les index, le glossaire, le journal des modifications "
        "et l'index de recherche.",
    ),
    ("agentkit", "Rédige le guide des agents et leurs compétences à partir de modèles relus."),
    (
        "evidence",
        "Conserve le passage exact derrière chaque citation, avec l'image de la page d'origine.",
    ),
    (
        "translate",
        "Écrit le wiki dans ses autres langues ; chiffres, citations et termes du métier "
        "sont contrôlés.",
    ),
    ("verify", "Passe les contrôles qualité : un échec bloquant arrête la publication."),
    ("site", "Construit ce site à partir de la version candidate du wiki."),
    (
        "publish",
        "Publie la version d'un seul tenant : le site bascule dessus en moins d'une minute.",
    ),
)


def stages(lang: str = "en") -> tuple[tuple[str, str], ...]:
    """The 13 stages and what each does, in ``lang`` (French or English)."""
    return _STAGES_FR if lang == "fr" else STAGES


_PROCESS_TEXT = {
    "en": """title: Pipeline
---

This wiki was not written by hand. Ordinary documents (PDF, Word, Excel, e-mail, scans) are
compiled into the pages you read, and every fact keeps a footnote that opens the exact passage it
came from. When a document is added, the pipeline runs again and a new release of the whole wiki
replaces the old one.

Below, live: every document and where it is in the pipeline, and the runs that changed the wiki,
with their timings and cost. Models are used only where judgement is needed; everything derivable
from structure is computed by code, and a run reuses what did not change.

## Live
""",
    "fr": """title: Traitement
---

Ce wiki n'a pas été écrit à la main. Des documents ordinaires (PDF, Word, Excel, e-mails, scans)
sont compilés en pages, et chaque fait garde une note de bas de page qui ouvre le passage exact
dont il provient. Quand un document est ajouté, le traitement repart et une nouvelle version de
tout le wiki remplace l'ancienne.

Ci-dessous, en direct : chaque document et son avancement dans le traitement, et les exécutions
qui ont modifié le wiki, avec leur durée et leur coût. Les modèles ne servent que là où il faut
du jugement ; tout ce qui se déduit de la structure est calculé par le code, et une exécution
réutilise ce qui n'a pas changé.

## En direct
""",
}

_DOCUMENTS_TEXT = {
    "en": """title: Documents
---

The raw documents this wiki is compiled from, as they were received: quotes, contracts, plans,
invoices, e-mails, photos and scans. Open the original, or the wiki page compiled from it.
""",
    "fr": """title: Documents
---

Les documents bruts à partir desquels ce wiki est compilé, tels qu'ils ont été reçus : devis,
marchés, plans, factures, e-mails, photos et scans. Ouvrez l'original, ou la page du wiki rédigée
à partir de lui.
""",
}


_ARCHITECTURE_TEXT = {
    "en": """title: Architecture
---

How a folder of ordinary documents becomes this site, and where the agents fit. Everything runs
on Azure; the code is open source.

## How it works

1. **Documents.** PDF, Word, Excel, CSV, PowerPoint, e-mail and scans are kept exactly as they
   were received: every one has its original on the [Documents](documents) tab.
2. **A 14-step pipeline.** An Azure Container Apps job reads, classifies and compiles them with
   Microsoft Foundry models, then links, indexes and saves the evidence behind every citation.
   Models are used only where judgement is needed; whatever the structure gives is computed by
   code. Follow it on the [Pipeline](pipeline) tab.
3. **A release with quality gates.** Each run produces a complete, immutable release of the wiki.
   Quality gates check citations, numbers and links, and leak gates keep restricted content and
   private identifiers out; a blocking failure stops the release. Publishing switches the site
   to the new release in one step.
4. **A static site and an MCP server.** This site is built from the release with Quartz. The same
   release is served to agents by an MCP server with read-only tools (search, read a page, open
   the evidence, query a table). The MCP server is private: visitors ask through the "Ask this
   wiki" drawer.
5. **Two Microsoft Foundry agents.** The Researcher reads: it starts from the wiki's indexes and
   search in one call, reads the pages, confirms decisive facts in the evidence and answers with
   citations. The Librarian maintains: it queues new documents and follows the runs. Public
   questions go through Azure API Management limits (requests per address, a token budget and a
   daily cost cut-off, after which the filed answers are shown), and live answers pass the same
   quote verification and leak checks before they are shown.
6. **Hosting.** Azure Container Apps run the site, the MCP server and the pipeline jobs, with
   managed identities and no keys. Only the owner, signed in with the platform's built-in
   authentication (Easy Auth), uploads documents. The whole stack deploys with `azd up`.
""",
    "fr": """title: Architecture
---

Comment un dossier de documents ordinaires devient ce site, et où interviennent les agents. Tout
tourne sur Azure ; le code est open source.

## Comment ça marche

1. **Les documents.** PDF, Word, Excel, CSV, PowerPoint, e-mails et scans sont conservés tels
   qu'ils ont été reçus : chacun a son original dans l'onglet [Documents](documents).
2. **Un traitement en 14 étapes.** Un job Azure Container Apps les lit, les classe et les compile
   avec des modèles Microsoft Foundry, puis relie les pages, rédige les index et conserve la
   preuve derrière chaque citation. Les modèles ne servent que là où il faut du jugement ; tout
   ce que donne la structure est calculé par le code. Suivez-le dans l'onglet
   [Traitement](pipeline).
3. **Une version contrôlée.** Chaque exécution produit une version complète et immuable du wiki.
   Les contrôles qualité vérifient citations, chiffres et liens, et les contrôles de fuite
   écartent les contenus restreints et les identifiants privés ; un échec bloquant arrête la
   publication. La publication bascule le site sur la nouvelle version d'un seul tenant.
4. **Un site statique et un serveur MCP.** Ce site est construit à partir de la version avec
   Quartz. La même version est servie aux agents par un serveur MCP aux outils en lecture seule
   (rechercher, lire une page, ouvrir la preuve, interroger un tableau). Le serveur MCP est
   privé : les visiteurs posent leurs questions dans le panneau « Interroger ce wiki ».
5. **Deux agents Microsoft Foundry.** Le Researcher lit : il part des index du wiki et de la
   recherche en un seul appel, lit les pages, confirme les faits décisifs dans les preuves et
   répond avec ses citations. Le Librarian entretient : il met les nouveaux documents en file et
   suit les exécutions. Les questions du public passent par les limites d'Azure API Management
   (requêtes par adresse, budget de jetons et plafond de coût quotidien, au-delà duquel les
   réponses classées sont affichées), et les réponses en direct passent les mêmes vérifications
   de citations et de fuite avant d'être affichées.
6. **L'hébergement.** Azure Container Apps fait tourner le site, le serveur MCP et les jobs du
   traitement, avec des identités managées et sans clés. Seul le propriétaire, connecté par
   l'authentification intégrée de la plateforme (Easy Auth), dépose des documents. L'ensemble se
   déploie avec `azd up`.
""",
}


def _page(texts: dict[str, str], lang: str) -> str:
    return f"---\nlang: {lang}\n" + texts.get(lang, texts["en"])


def process_markdown(lang: str = "en") -> str:
    return _page(_PROCESS_TEXT, lang)


def documents_markdown(lang: str = "en") -> str:
    return _page(_DOCUMENTS_TEXT, lang)


def _write_once(target: Path, text: str) -> bool:
    if target.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8", newline="\n")
    return True


def write_process_page(content_dir: Path, lang: str = "en") -> bool:
    """Write ``pipeline.md`` in ``lang`` into the Quartz content folder of that language (the
    content root, or a mirror's folder) unless the release has its own."""
    return _write_once(content_dir / f"{PROCESS_SLUG}.md", process_markdown(lang))


def write_documents_page(content_dir: Path, lang: str = "en") -> bool:
    """Write ``documents.md`` in ``lang`` into the Quartz content folder of that language unless
    the release has its own."""
    return _write_once(content_dir / f"{DOCUMENTS_SLUG}.md", documents_markdown(lang))


def architecture_markdown(lang: str = "en") -> str:
    return _page(_ARCHITECTURE_TEXT, lang)


def write_architecture_page(content_dir: Path, lang: str = "en") -> bool:
    """Write ``architecture.md`` in ``lang`` into the Quartz content folder of that language
    unless the release has its own."""
    return _write_once(content_dir / f"{ARCHITECTURE_SLUG}.md", architecture_markdown(lang))
