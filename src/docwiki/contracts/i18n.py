"""String tables of the generated wiki text (v1.7, ADR 0012).

Every sentence, heading and label that code writes into a wiki page (headings such as
``Key facts`` or ``Open contradictions``, resolution-rule sentences, hub, dashboard and view
boilerplate) comes from these tables, in the language of the page: the canonical language of
the domain pack (``wiki_languages[0]``) for the canonical wiki, the target language for the
mirror pages that code rebuilds (hubs, indexes, views). A domain pack may override any key that
is not structural with ``domains/<pack>/i18n/<lang>.yaml``.

Structural keys (:data:`STRUCTURAL_KEYS`) are the headings that the release validator, the links
stage and the translate stage recognise: packs cannot override them, so that every heading of
every core language stays known (:func:`heading_variants`).

Templates use :meth:`str.format` fields (``{count}``, ``{title}`` …). A key with plural forms has
``.one`` and ``.other`` variants (:meth:`Strings.count`). French text uses a no-break space before
``:`` (typography kept light on purpose).
"""

from __future__ import annotations

from collections.abc import Mapping
from functools import cache
from typing import Any

__all__ = [
    "CORE_LANGUAGES",
    "CORE_STRINGS",
    "DEFAULT_LANGUAGE",
    "MIRRORED_PAGE_TYPES",
    "STRUCTURAL_KEYS",
    "Strings",
    "core_strings",
    "heading_key",
    "heading_variants",
    "language_name",
    "untranslated_marker",
]

DEFAULT_LANGUAGE = "en"
_NB = "\u00a0"
"""No-break space (French typography before ``:``)."""

_EN: dict[str, str] = {
    # headings (structural)
    "heading.key_facts": "Key facts",
    "heading.contents": "Contents",
    "heading.figures": "Figures",
    "heading.related": "Related",
    "heading.referenced_by": "Referenced by",
    "heading.sources": "Sources",
    "heading.facts": "Facts",
    "heading.timeline": "Timeline",
    "heading.documents": "Documents",
    "heading.overview": "Overview",
    "heading.contradictions": "Contradictions",
    "heading.superseded": "Superseded information",
    "heading.sources_consulted": "Sources consulted",
    "heading.details": "Details",
    "heading.topics": "Topics",
    "heading.entities": "Entities",
    "heading.computed_views": "Computed views",
    "heading.open_contradictions": "Open contradictions",
    "heading.last_document": "Last document received",
    "heading.rows": "Rows",
    "heading.totals": "Totals",
    "heading.how_to_navigate": "How to navigate",
    "heading.categories": "Categories",
    "heading.stats": "Stats",
    "heading.recent_changes": "Recent changes",
    "heading.quality": "Quality",
    "heading.not_synthesised": "Not synthesised yet",
    "heading.tables": "Tables",
    # page status words
    "status.current": "current",
    "status.superseded": "superseded",
    "status.withdrawn": "withdrawn",
    # source pages (render)
    "render.no_evidence": "No evidence is cited on this page.",
    "render.table_caption": "**Table {table_id}** · {label}",
    "render.column": "Column {number}",
    "render.row": "Row",
    "render.table_more": (
        "Showing the first {shown} of {total} rows. Agents can query the full table as "
        "`{table_id}` with the `query_table` tool."
    ),
    "render.table_query": (
        "Agents can query this table as `{table_id}` with the `query_table` tool."
    ),
    "render.generated_description": "Generated description: {text}.",
    "render.no_caption": "No caption or description was extracted.",
    "render.figure": "- **Figure {figure_id}** ({label}): ",
    "render.superseded_banner": "> **Superseded** by {links}. Use the current revision.",
    "render.no_key_facts": "No verified key facts were extracted from this document.",
    "render.see_table": "See table {table_id} above.",
    "render.no_sections": "No content sections were compiled from this document.",
    "render.no_figures": "No figures were extracted from this document.",
    # entity pages
    "entity.intro.one": (
        "{title} is an entity of type {type_title} in the domain registry, mentioned in "
        "{count} source document."
    ),
    "entity.intro.other": (
        "{title} is an entity of type {type_title} in the domain registry, mentioned in "
        "{count} source documents."
    ),
    "entity.superseded_fact": "Superseded: {text}",
    "entity.no_facts": "No verified facts name this entity yet.",
    "entity.no_dated": "No dated facts.",
    "entity.superseded_suffix": " (superseded)",
    # topic pages
    "topic.summary": "Synthesis of {count} sources about {title}.",
    "topic.no_overview": "No overview claim could be verified against current sources.",
    "topic.contradiction": (
        "- **{subject}.** {first} states: {first_facts} ({first_meta}). {second} states: "
        "{second_facts} ({second_meta}). {resolution}"
    ),
    "topic.no_contradictions": "No contradictions were found between current sources.",
    "topic.changes_intro": (
        "Changed by an amending document (changes of terms, not contradictions):"
    ),
    "topic.change": (
        "- **{subject}.** {amended} states: {amended_facts} ({amended_meta}). Changed by "
        "{amending}: {amending_facts} ({amending_meta})."
    ),
    "topic.policy": "Resolution policy: {notes}",
    "topic.superseded_item": (
        "- **{subject}.** {old} stated: {old_text} Replacement: {replacement} "
        "Superseding source: {superseding}."
    ),
    "topic.no_restatement": "no current source restates it.",
    "topic.no_superseded": "No superseded information.",
    "topic.meta_authority": "authority {authority}",
    "topic.meta_dated": "dated {date}",
    "topic.meta_undated": "date unknown",
    "topic.consulted": "- {link}: {meta}",
    # resolution statements (topics, wiki-contract §9)
    "resolution.authority": "authority",
    "resolution.recency": "recency",
    "resolution.then": ", then ",
    "resolution.head": "Resolution rule ({rule}): ",
    "resolution.arbitrate": (
        "{head}to arbitrate; the rule does not decide between {first} and {second}. {reason}"
    ),
    "resolution.why_authority": "authority {winner} vs {loser}",
    "resolution.why_dated": "dated {winner} vs {loser}",
    "resolution.review": "{head}to review; the rule would favour {winner} ({why}), but {review}",
    "resolution.amended_review": (
        "the terms of {winner} may have been changed by the amending documents{where}: "
        "{links}; check them before relying on either statement."
    ),
    "resolution.where": " of {label}",
    "resolution.prevails": "{head}{winner} prevails ({why}).",
    "resolution.undecided": (
        "{head}the rule does not decide between them (same authority and no usable dates); "
        "review both sources."
    ),
    # links stage
    "links.no_backlinks": "No other page links here yet.",
    "links.topic.one": "Topic",
    "links.topic.other": "Topics",
    "links.view.one": "Computed view",
    "links.view.other": "Computed views",
    "links.supersedes": "Supersedes",
    "links.superseded_by": "Superseded by",
    # hubs and dashboard
    "hub.no_phase": "No phase",
    "hub.phase": "Phase {phase}",
    "hub.superseded_by": "superseded by {links}",
    "hub.counts.one": "{count} document, last received {date}.",
    "hub.counts.other": "{count} documents, last received {date}.",
    "hub.built_by_code": (
        " Built by code from the documents' folders and the domain pack; the facts themselves "
        "are on the cited source and topic pages."
    ),
    "hub.registry": "From the domain pack's registry (reviewed, not read from the documents).",
    "hub.attribute_header": "| Attribute | Value |",
    "hub.no_registry": "The domain pack's registry has no entry for {label}.",
    "hub.no_topics": "No topic synthesises these documents yet.",
    "hub.no_entities": "No registry entity is mentioned by these documents yet.",
    "hub.view_rows.one": "{link}: {count} row for this {noun}",
    "hub.view_rows.other": "{link}: {count} rows for this {noun}",
    "hub.no_views": "No computed view has rows for this {noun}.",
    "hub.no_contradictions": "No open contradictions in the topics of this {noun}.",
    "hub.contradiction_count.one": "- {topics}: {count} contradiction",
    "hub.contradiction_count.other": "- {topics}: {count} contradictions",
    "hub.contradiction": "- {first} and {second}: {subjects} (in {topics}).",
    "hub.more_subjects": "; and {count} more",
    "hub.index_intro": (
        "One hub page per {noun}, built by code from the documents' folders and the domain pack."
    ),
    "hub.index_summary": "The hub page of every {noun}.",
    "dashboard.header": (
        "| {scope_title} | Phase | Open contradictions | Documents | Last document (dated) |"
    ),
    "dashboard.received": "{link} (received {date})",
    "dashboard.every": "Every {noun} has a hub page; see [all {plural}]({href}).",
    "dashboard.view.one": "{link} ({count} row)",
    "dashboard.view.other": "{link} ({count} rows)",
    "dashboard.views": (
        "Computed views, figures computed by code with every row cited: {views} "
        "([all computed views]({href}))."
    ),
    # indexes
    "index.skip.insufficient_evidence": "not enough sources yet",
    "index.skip.audience": "its sources are above the audience of this build",
    "index.skip.no_current_sources": "no current source covers it",
    "index.log.superseded": "{page} is superseded by {replacement}",
    "index.log.source_removed": "Source page removed: {reason}.",
    "index.log.query_removed": "Research answer removed: {reason}.",
    "index.log.raw_deleted": "the raw file was deleted",
    "index.log.reason.unprocessed": "the current version could not be processed",
    "index.log.reason.audience": "the source is above the audience of this build",
    "index.log.reason.query_checks": "it no longer passes the checks of this release",
    "index.log.title": "Log",
    "index.log.summary": "Append-only change log of this wiki.",
    "index.log.empty": "No changes recorded yet.",
    "index.glossary.title": "Glossary",
    "index.glossary.summary": "Terms with definitions, multilingual synonyms and links.",
    "index.glossary.empty": "No glossary terms are defined for this wiki yet.",
    "index.glossary.intro": (
        "Terms of the domain with definitions, synonyms in other languages and related pages."
    ),
    "index.glossary.synonyms": "- Synonyms: {synonyms}",
    "index.glossary.see_also": "- See also: {links}",
    "index.sources.title": "Sources",
    "index.sources.summary": "All sources grouped by category, with status and sensitivity.",
    "index.sources.empty": "No sources have been compiled yet.",
    "index.sources.intro.one": (
        "{count} source grouped by category, with their status and sensitivity."
    ),
    "index.sources.intro.other": (
        "{count} sources grouped by category, with their status and sensitivity."
    ),
    "index.sources.superseded_by": "superseded by {links}",
    "index.entities.title": "Entities",
    "index.entities.summary": "Entity types of this wiki and their pages.",
    "index.entities.empty": "No entity of the domain registry is mentioned by the sources yet.",
    "index.entities.pages.one": "{count} page",
    "index.entities.pages.other": "{count} pages",
    "index.entities.type_summary": "Entity pages of type {entity_type}.",
    "index.topics.title": "Topics",
    "index.topics.summary": "Curated multi-source syntheses.",
    "index.topics.empty": "No topic has enough evidence for a synthesis yet.",
    "index.queries.title": "Research answers",
    "index.queries.summary": "Research answers filed back into the wiki after approval.",
    "index.home.summary": (
        "Home: purpose, how to navigate, categories, topics, stats and recent changes."
    ),
    "index.home.cited": (
        "Every fact in this wiki is cited: footnotes link to evidence sidecars that show the "
        "exact page, paragraph, slide or table rows of the original document."
    ),
    "index.home.nav1": "1. Start with the [topics]({href}) for syntheses across documents.",
    "index.home.nav2": "2. Browse the [entities]({href}) of the domain registry.",
    "index.home.nav3": (
        "3. Read the [sources]({href}): one page per document, grouped by category, with its "
        "status and sensitivity."
    ),
    "index.home.nav4": "4. Use the [glossary]({href}) for acronyms and multilingual synonyms.",
    "index.home.nav5": (
        "5. Check the [log]({log}) for recent changes and the [quality report]({quality}) for "
        "gate results."
    ),
    "index.home.agents": (
        "Agents start with the [agent guide]({href}); `llms.txt` and `catalog.json` index every "
        "page."
    ),
    "index.home.category.one": "{count} source",
    "index.home.category.other": "{count} sources",
    "index.home.category_superseded": " ({count} superseded)",
    "index.home.no_topics": "No topics yet.",
    "index.home.stat_sources": "- Sources: {total} ({current} current, {superseded} superseded)",
    "index.home.stat_entities": "- Entities: {count}",
    "index.home.stat_topics": "- Topics: {count}",
    "index.home.stat_glossary": "- Glossary terms: {count}",
    "index.home.stat_queries": "- Filed research answers: [{count}]({href})",
    "index.home.quality_report": ("- [Quality report]({href}): gate results of this release"),
    "index.home.run_receipt": (
        "- [Run receipt]({href}): durations, tokens, costs and versions of the run that built it"
    ),
    # computed views
    "view.computed": (
        "These figures were computed by code, not by a language model, from {rows} cited table "
        "row(s) of {documents} document(s); every row links to the evidence of exactly that "
        "row, and the totals are sums of the cited rows."
    ),
    "view.document": "Document",
    "view.truncated": "Only the first {count} rows are shown and summed.",
    "view.no_rows": "No row of the documents matches this view.",
    "view.summary": "{count} rows computed by code from the documents' tables, cited row by row.",
    "view.scope": "Scope",
    "view.rows": "Rows",
    "view.totals_intro": "Sums computed by code from the cited rows above{per}.",
    "view.totals_per": ", per {scope}",
    "view.all": "**All**",
    "view.not_summed": "Not summed because they are not numbers: {parts}.",
    "view.not_summed_part": "{count} cell(s) of {column}",
    "view.yes": "yes",
    "view.no": "no",
    "views.title": "Computed views",
    "views.intro": (
        "Figures computed by code, not by a language model, from the tables of the documents; "
        "every row is cited to the row of the document it comes from."
    ),
    "views.summary": "Every computed view: figures computed by code, every row cited.",
    "views.rows.one": "{link}: {count} row",
    "views.rows.other": "{link}: {count} rows",
    # mirror pages (translate stage)
    "mirror.untranslated": (
        "> **Untranslated:** this page could not be translated reliably; it is shown in its "
        "original language ({lang})."
    ),
}

_FR: dict[str, str] = {
    "heading.key_facts": "Faits clés",
    "heading.contents": "Contenu",
    "heading.figures": "Figures",
    "heading.related": "Voir aussi",
    "heading.referenced_by": "Pages qui renvoient ici",
    "heading.sources": "Sources",
    "heading.facts": "Faits",
    "heading.timeline": "Chronologie",
    "heading.documents": "Documents",
    "heading.overview": "Vue d'ensemble",
    "heading.contradictions": "Contradictions",
    "heading.superseded": "Informations remplacées",
    "heading.sources_consulted": "Sources consultées",
    "heading.details": "Détails",
    "heading.topics": "Thèmes",
    "heading.entities": "Entités",
    "heading.computed_views": "Vues calculées",
    "heading.open_contradictions": "Contradictions ouvertes",
    "heading.last_document": "Dernier document reçu",
    "heading.rows": "Lignes",
    "heading.totals": "Totaux",
    "heading.how_to_navigate": "Comment naviguer",
    "heading.categories": "Catégories",
    "heading.stats": "Chiffres",
    "heading.recent_changes": "Changements récents",
    "heading.quality": "Qualité",
    "heading.not_synthesised": "Pas encore synthétisés",
    "heading.tables": "Tableaux",
    "status.current": "en vigueur",
    "status.superseded": "remplacé",
    "status.withdrawn": "retiré",
    "render.no_evidence": "Aucune preuve n'est citée sur cette page.",
    "render.table_caption": "**Tableau {table_id}** · {label}",
    "render.column": "Colonne {number}",
    "render.row": "Ligne",
    "render.table_more": (
        "Seules les {shown} premières lignes sur {total} sont affichées. Les agents peuvent "
        "interroger le tableau complet `{table_id}` avec l'outil `query_table`."
    ),
    "render.table_query": (
        "Les agents peuvent interroger ce tableau `{table_id}` avec l'outil `query_table`."
    ),
    "render.generated_description": f"Description générée{_NB}: {{text}}.",
    "render.no_caption": "Aucune légende ni description n'a été extraite.",
    "render.figure": f"- **Figure {{figure_id}}** ({{label}}){_NB}: ",
    "render.superseded_banner": "> **Remplacé** par {links}. Utilisez la révision en vigueur.",
    "render.no_key_facts": "Aucun fait clé vérifié n'a été extrait de ce document.",
    "render.see_table": "Voir le tableau {table_id} ci-dessus.",
    "render.no_sections": "Aucune section de contenu n'a été compilée à partir de ce document.",
    "render.no_figures": "Aucune figure n'a été extraite de ce document.",
    "entity.intro.one": (
        "{title} est une entité de type {type_title} du registre du domaine, citée dans "
        "{count} document source."
    ),
    "entity.intro.other": (
        "{title} est une entité de type {type_title} du registre du domaine, citée dans "
        "{count} documents sources."
    ),
    "entity.superseded_fact": f"Remplacé{_NB}: {{text}}",
    "entity.no_facts": "Aucun fait vérifié ne cite encore cette entité.",
    "entity.no_dated": "Aucun fait daté.",
    "entity.superseded_suffix": " (remplacé)",
    "topic.summary": "Synthèse de {count} sources sur {title}.",
    "topic.no_overview": (
        "Aucune affirmation de synthèse n'a pu être vérifiée dans les sources en vigueur."
    ),
    "topic.contradiction": (
        f"- **{{subject}}.** {{first}} indique{_NB}: {{first_facts}} ({{first_meta}}). "
        f"{{second}} indique{_NB}: {{second_facts}} ({{second_meta}}). {{resolution}}"
    ),
    "topic.no_contradictions": "Aucune contradiction n'a été trouvée entre les sources en vigueur.",
    "topic.changes_intro": (
        "Modifié par un document modificatif (changements de conditions, pas des "
        f"contradictions){_NB}:"
    ),
    "topic.change": (
        f"- **{{subject}}.** {{amended}} indique{_NB}: {{amended_facts}} ({{amended_meta}}). "
        f"Modifié par {{amending}}{_NB}: {{amending_facts}} ({{amending_meta}})."
    ),
    "topic.policy": f"Politique de résolution{_NB}: {{notes}}",
    "topic.superseded_item": (
        f"- **{{subject}}.** {{old}} indiquait{_NB}: {{old_text}} Remplacement{_NB}: "
        f"{{replacement}} Source qui le remplace{_NB}: {{superseding}}."
    ),
    "topic.no_restatement": "aucune source en vigueur ne le reprend.",
    "topic.no_superseded": "Aucune information remplacée.",
    "topic.meta_authority": "autorité {authority}",
    "topic.meta_dated": "daté du {date}",
    "topic.meta_undated": "date inconnue",
    "topic.consulted": f"- {{link}}{_NB}: {{meta}}",
    "resolution.authority": "autorité",
    "resolution.recency": "date",
    "resolution.then": ", puis ",
    "resolution.head": f"Règle de résolution ({{rule}}){_NB}: ",
    "resolution.arbitrate": (
        "{head}à arbitrer{_NB}; la règle ne tranche pas entre {first} et {second}. {reason}"
    ).replace("{_NB}", _NB),
    "resolution.why_authority": "autorité {winner} contre {loser}",
    "resolution.why_dated": "daté du {winner} contre {loser}",
    "resolution.review": (
        f"{{head}}à vérifier{_NB}; la règle donnerait raison à {{winner}} ({{why}}), mais "
        "{review}"
    ),
    "resolution.amended_review": (
        "les conditions de {winner} ont pu être modifiées par les documents modificatifs"
        f"{{where}}{_NB}: {{links}}{_NB}; vérifiez-les avant de vous fier à l'une ou l'autre "
        "affirmation."
    ),
    "resolution.where": " de {label}",
    "resolution.prevails": "{head}{winner} l'emporte ({why}).",
    "resolution.undecided": (
        "{head}la règle ne les départage pas (même autorité et pas de dates utilisables)"
        f"{_NB}; vérifiez les deux sources."
    ),
    "links.no_backlinks": "Aucune autre page ne renvoie encore ici.",
    "links.topic.one": "Thème",
    "links.topic.other": "Thèmes",
    "links.view.one": "Vue calculée",
    "links.view.other": "Vues calculées",
    "links.supersedes": "Remplace",
    "links.superseded_by": "Remplacé par",
    "hub.no_phase": "Sans phase",
    "hub.phase": "Phase {phase}",
    "hub.superseded_by": "remplacé par {links}",
    "hub.counts.one": "{count} document, dernier reçu le {date}.",
    "hub.counts.other": "{count} documents, dernier reçu le {date}.",
    "hub.built_by_code": (
        " Page construite par code à partir des dossiers des documents et du pack de domaine"
        f"{_NB}; les faits eux-mêmes sont sur les pages de sources et de thèmes citées."
    ),
    "hub.registry": "Issu du registre du pack de domaine (relu, non lu dans les documents).",
    "hub.attribute_header": "| Attribut | Valeur |",
    "hub.no_registry": "Le registre du pack de domaine n'a pas d'entrée pour {label}.",
    "hub.no_topics": "Aucun thème ne synthétise encore ces documents.",
    "hub.no_entities": "Aucune entité du registre n'est encore citée par ces documents.",
    "hub.view_rows.one": f"{{link}}{_NB}: {{count}} ligne pour ce {{noun}}",
    "hub.view_rows.other": f"{{link}}{_NB}: {{count}} lignes pour ce {{noun}}",
    "hub.no_views": "Aucune vue calculée n'a de ligne pour ce {noun}.",
    "hub.no_contradictions": "Aucune contradiction ouverte dans les thèmes de ce {noun}.",
    "hub.contradiction_count.one": f"- {{topics}}{_NB}: {{count}} contradiction",
    "hub.contradiction_count.other": f"- {{topics}}{_NB}: {{count}} contradictions",
    "hub.contradiction": f"- {{first}} et {{second}}{_NB}: {{subjects}} (dans {{topics}}).",
    "hub.more_subjects": "{_NB}; et {count} autres".replace("{_NB}", _NB),
    "hub.index_intro": (
        "Une page par {noun}, construite par code à partir des dossiers des documents et du "
        "pack de domaine."
    ),
    "hub.index_summary": "La page de chaque {noun}.",
    "dashboard.header": (
        "| {scope_title} | Phase | Contradictions ouvertes | Documents | Dernier document (daté) |"
    ),
    "dashboard.received": "{link} (reçu le {date})",
    "dashboard.every": "Chaque {noun} a sa page{_NB}; voir [tous les {plural}]({href}).".replace(
        "{_NB}", _NB
    ),
    "dashboard.view.one": "{link} ({count} ligne)",
    "dashboard.view.other": "{link} ({count} lignes)",
    "dashboard.views": (
        f"Vues calculées, chiffres calculés par code et chaque ligne citée{_NB}: {{views}} "
        "([toutes les vues calculées]({href}))."
    ),
    "index.skip.insufficient_evidence": "pas encore assez de sources",
    "index.skip.audience": "ses sources dépassent l'audience de cette publication",
    "index.skip.no_current_sources": "aucune source en vigueur ne le couvre",
    "index.log.superseded": "{page} est remplacé par {replacement}",
    "index.log.source_removed": f"Page de source retirée{_NB}: {{reason}}.",
    "index.log.query_removed": f"Réponse de recherche retirée{_NB}: {{reason}}.",
    "index.log.raw_deleted": "le fichier brut a été supprimé",
    "index.log.reason.unprocessed": "la version actuelle n'a pas pu être traitée",
    "index.log.reason.audience": "la source dépasse l'audience de cette publication",
    "index.log.reason.query_checks": "elle ne passe plus les contrôles de cette publication",
    "index.log.title": "Journal",
    "index.log.summary": "Journal des changements de ce wiki, en ajout seul.",
    "index.log.empty": "Aucun changement enregistré pour l'instant.",
    "index.glossary.title": "Glossaire",
    "index.glossary.summary": "Termes avec définitions, synonymes multilingues et liens.",
    "index.glossary.empty": "Aucun terme de glossaire n'est encore défini pour ce wiki.",
    "index.glossary.intro": (
        "Termes du domaine avec leurs définitions, leurs synonymes dans d'autres langues et les "
        "pages liées."
    ),
    "index.glossary.synonyms": f"- Synonymes{_NB}: {{synonyms}}",
    "index.glossary.see_also": f"- Voir aussi{_NB}: {{links}}",
    "index.sources.title": "Sources",
    "index.sources.summary": "Toutes les sources par catégorie, avec statut et sensibilité.",
    "index.sources.empty": "Aucune source n'a encore été compilée.",
    "index.sources.intro.one": "{count} source par catégorie, avec son statut et sa sensibilité.",
    "index.sources.intro.other": (
        "{count} sources par catégorie, avec leur statut et leur sensibilité."
    ),
    "index.sources.superseded_by": "remplacé par {links}",
    "index.entities.title": "Entités",
    "index.entities.summary": "Types d'entités de ce wiki et leurs pages.",
    "index.entities.empty": "Aucune entité du registre n'est encore citée par les sources.",
    "index.entities.pages.one": "{count} page",
    "index.entities.pages.other": "{count} pages",
    "index.entities.type_summary": "Pages d'entités de type {entity_type}.",
    "index.topics.title": "Thèmes",
    "index.topics.summary": "Synthèses de plusieurs sources, sur des thèmes choisis.",
    "index.topics.empty": "Aucun thème n'a encore assez de preuves pour une synthèse.",
    "index.queries.title": "Réponses de recherche",
    "index.queries.summary": "Réponses de recherche versées dans le wiki après approbation.",
    "index.home.summary": (
        f"Accueil{_NB}: objet, navigation, catégories, thèmes, chiffres et changements récents."
    ),
    "index.home.cited": (
        f"Chaque fait de ce wiki est cité{_NB}: les notes renvoient à des fiches de preuve qui "
        "montrent la page, le paragraphe, la diapositive ou les lignes de tableau exacts du "
        "document d'origine."
    ),
    "index.home.nav1": "1. Commencez par les [thèmes]({href}), qui croisent les documents.",
    "index.home.nav2": "2. Parcourez les [entités]({href}) du registre du domaine.",
    "index.home.nav3": (
        f"3. Lisez les [sources]({{href}}){_NB}: une page par document, par catégorie, avec son "
        "statut et sa sensibilité."
    ),
    "index.home.nav4": (
        "4. Utilisez le [glossaire]({href}) pour les sigles et les synonymes multilingues."
    ),
    "index.home.nav5": (
        "5. Consultez le [journal]({log}) pour les changements récents et le "
        "[rapport qualité]({quality}) pour le résultat des contrôles."
    ),
    "index.home.agents": (
        f"Les agents commencent par le [guide des agents]({{href}}){_NB}; `llms.txt` et "
        "`catalog.json` indexent chaque page."
    ),
    "index.home.category.one": "{count} source",
    "index.home.category.other": "{count} sources",
    "index.home.category_superseded": " ({count} remplacées)",
    "index.home.no_topics": "Pas encore de thème.",
    "index.home.stat_sources": (
        f"- Sources{_NB}: {{total}} ({{current}} en vigueur, {{superseded}} remplacées)"
    ),
    "index.home.stat_entities": f"- Entités{_NB}: {{count}}",
    "index.home.stat_topics": f"- Thèmes{_NB}: {{count}}",
    "index.home.stat_glossary": f"- Termes du glossaire{_NB}: {{count}}",
    "index.home.stat_queries": f"- Réponses de recherche versées{_NB}: [{{count}}]({{href}})",
    "index.home.quality_report": (
        f"- [Rapport qualité]({{href}}){_NB}: résultat des contrôles de cette publication"
    ),
    "index.home.run_receipt": (
        f"- [Reçu d'exécution]({{href}}){_NB}: durées, jetons, coûts et versions de l'exécution "
        "qui l'a produite"
    ),
    "view.computed": (
        "Ces chiffres ont été calculés par code, pas par un modèle de langage, à partir de "
        "{rows} ligne(s) de tableau citée(s) de {documents} document(s){_NB}; chaque ligne "
        "renvoie à la preuve de cette ligne exacte, et les totaux sont des sommes des lignes "
        "citées."
    ).replace("{_NB}", _NB),
    "view.document": "Document",
    "view.truncated": "Seules les {count} premières lignes sont affichées et additionnées.",
    "view.no_rows": "Aucune ligne des documents ne correspond à cette vue.",
    "view.summary": (
        "{count} lignes calculées par code à partir des tableaux des documents, citées ligne "
        "par ligne."
    ),
    "view.scope": "Périmètre",
    "view.rows": "Lignes",
    "view.totals_intro": "Sommes calculées par code à partir des lignes citées ci-dessus{per}.",
    "view.totals_per": ", par {scope}",
    "view.all": "**Total**",
    "view.not_summed": f"Non additionnées car ce ne sont pas des nombres{_NB}: {{parts}}.",
    "view.not_summed_part": "{count} cellule(s) de {column}",
    "view.yes": "oui",
    "view.no": "non",
    "views.title": "Vues calculées",
    "views.intro": (
        "Chiffres calculés par code, pas par un modèle de langage, à partir des tableaux des "
        f"documents{_NB}; chaque ligne est citée jusqu'à la ligne du document dont elle vient."
    ),
    "views.summary": (
        f"Toutes les vues calculées{_NB}: chiffres calculés par code, chaque ligne citée."
    ),
    "views.rows.one": f"{{link}}{_NB}: {{count}} ligne",
    "views.rows.other": f"{{link}}{_NB}: {{count}} lignes",
    "mirror.untranslated": (
        f"> **Non traduit{_NB}:** cette page n'a pas pu être traduite de façon fiable{_NB}; "
        "elle est affichée dans sa langue d'origine ({lang})."
    ),
}

CORE_STRINGS: dict[str, dict[str, str]] = {"en": _EN, "fr": _FR}
"""Core tables of the engine, by language."""
CORE_LANGUAGES: tuple[str, ...] = tuple(CORE_STRINGS)

STRUCTURAL_KEYS: frozenset[str] = frozenset(key for key in _EN if key.startswith("heading."))
"""Keys a domain pack cannot override (headings recognised by code in every core language)."""

if set(_EN) != set(_FR):  # pragma: no cover - guards edits of the two tables
    raise RuntimeError(f"i18n tables differ: {sorted(set(_EN) ^ set(_FR))}")


def heading_key(name: str) -> str:
    return name if name.startswith("heading.") else f"heading.{name}"


@cache
def heading_variants(name: str) -> frozenset[str]:
    """Every core rendering of a structural heading (``key_facts`` → ``{Key facts, Faits
    clés}``): code that recognises a generated section accepts any wiki language."""
    key = heading_key(name)
    return frozenset(table[key] for table in CORE_STRINGS.values())


def _base_language(lang: str) -> str:
    return lang.split("-", 1)[0].lower()


class Strings:
    """The string table of one language (core table, then pack overrides)."""

    def __init__(self, lang: str, overrides: Mapping[str, str] | None = None) -> None:
        base = _base_language(lang)
        table = CORE_STRINGS.get(lang) or CORE_STRINGS.get(base) or CORE_STRINGS["en"]
        self.lang = lang
        self.table: dict[str, str] = {**table, **dict(overrides or {})}

    def __call__(self, key: str, /, **fields: Any) -> str:
        try:
            template = self.table[key]
        except KeyError:
            raise KeyError(f"no string {key!r} for language {self.lang!r}") from None
        return template.format(**fields) if fields else template

    def heading(self, name: str) -> str:
        return self(heading_key(name))

    def count(self, key: str, count: int, /, **fields: Any) -> str:
        """The ``.one`` or ``.other`` form of ``key`` (French: 0 and 1 are singular)."""
        singular = count in (0, 1) if _base_language(self.lang) == "fr" else count == 1
        return self(f"{key}.{'one' if singular else 'other'}", count=count, **fields)

    def status(self, value: str) -> str:
        """A page status word (``current``, ``superseded``…), else the value itself."""
        return self.table.get(f"status.{value}", value)


@cache
def core_strings(lang: str = DEFAULT_LANGUAGE) -> Strings:
    """The core table of ``lang`` without pack overrides (English for unknown languages)."""
    return Strings(lang)


MIRRORED_PAGE_TYPES: frozenset[str] = frozenset(
    {"source", "entity", "topic", "view", "hub", "index", "glossary", "log"}
)
"""Page types that have a mirror in every other wiki language (v1.7, ADR 0012): sources,
entities and topics are translated by the ``translate`` stage, the pages built by code (views,
hubs, indexes, glossary, log) are rebuilt in the mirror language. Research answers keep the
language they were filed in and agent files (``meta``) stay canonical."""


_LANGUAGE_NAMES = {
    "en": "English",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "it": "Italian",
    "nl": "Dutch",
    "pt": "Portuguese",
}


def language_name(code: str) -> str:
    """``French (fr)`` for a language code (the code alone when unknown), for the prompts."""
    name = _LANGUAGE_NAMES.get(_base_language(code))
    return f"{name} ({code})" if name else code


def untranslated_marker(lang: str) -> str:
    """The start of the line that marks a mirror page kept untranslated (its translation failed
    the preservation check twice), in the mirror's language."""
    template = Strings(lang)("mirror.untranslated")
    return template.split(":**", 1)[0] + ":**"
