"""The Documents register grouped by scope, then phase, then type (v1.7, ADR 0011).

Pure functions over the ``sources`` of ``docwiki-site.json``: the overlay's ``Documents``
component renders the groups as they come. A release whose sources have no scope gets no groups
and keeps the flat register.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from docwiki.contracts.catalog import Catalog

__all__ = ["explorer_settings", "hub_folders", "register_groups", "scope_info"]

_LAST = "￿"
"""Sorts missing values after every real one."""


def scope_info(catalog: Catalog) -> dict[str, dict[str, str | None]]:
    """``{value: {title, hub}}`` for every scope value of the release: the title of its hub page
    (``Chantier Moreau``) and the hub's content slug (``chantiers/moreau``); a scope without a
    hub (the default scope) is titled by its value capitalised (``Entreprise``)."""
    info: dict[str, dict[str, str | None]] = {
        page.scope: {"title": page.title, "hub": page.path.removesuffix(".md")}
        for page in catalog.pages
        if page.type == "hub" and page.scope
    }
    values = {page.scope for page in catalog.pages if page.scope}
    values |= {source.scope for source in catalog.sources if source.scope}
    for value in values - set(info):
        info[value] = {"title": value.replace("-", " ").capitalize(), "hub": None}
    return dict(sorted(info.items()))


def hub_folders(catalog: Catalog) -> list[str]:
    """Wiki folders of the hub pages (``chantiers``), from the hubs indexes."""
    return sorted(
        page.id.removeprefix("index:hubs/")
        for page in catalog.pages
        if page.type == "index" and page.id.startswith("index:hubs/")
    )


def explorer_settings(catalog: Catalog) -> dict[str, Any]:
    """What the explorer needs: the hub folders to show first, when the wiki has scopes the
    name the ``entities`` folder takes there (the default scope's title, ``Entreprise``), and the
    title of each per-scope topics folder (``topics/moreau`` → ``Chantier Moreau``)."""
    info = scope_info(catalog)
    unhubbed = [value for value, item in info.items() if not item["hub"]]
    topic_paths = [page.path for page in catalog.pages if page.type == "topic"]
    return {
        "hubFolders": hub_folders(catalog),
        "entitiesTitle": info[unhubbed[0]]["title"] if len(unhubbed) == 1 else None,
        "folderTitles": {
            f"topics/{value}": item["title"]
            for value, item in info.items()
            if any(path.startswith(f"topics/{value}/") for path in topic_paths)
        },
    }


def _type_title(doc_type: str | None, label: str | None = None) -> str:
    """The pack's label of a doc type (``docTypeLabel``); a release built before the labels
    shows its key in words."""
    if label:
        return label
    if not doc_type:
        return "Other documents"
    text = doc_type.replace("-", " ")
    return text[:1].upper() + text[1:]


def _source_key(item: tuple[str, Mapping[str, Any]]) -> tuple[str, ...]:
    """Within a type: n° and indice (revisions together), then date, then title."""
    _, source = item
    return (
        str(source.get("docNumber") or _LAST),
        str(source.get("revision") or ""),
        str(source.get("date") or ""),
        str(source.get("title") or "").casefold(),
    )


def register_groups(
    sources: Mapping[str, Mapping[str, Any]], scopes: Mapping[str, Mapping[str, str | None]]
) -> list[dict[str, Any]] | None:
    """Sources grouped by scope (hub title), then phase, then type; ``None`` when no source has
    a scope.

    Scope groups: scopes with a hub first (by title), then the others (the default scope), then
    sources without a scope. Phases in key order (``0`` … ``5``), sources without a phase
    last; types alphabetically, untyped last.
    """
    if not any(source.get("scope") for source in sources.values()):
        return None
    by_scope: dict[str | None, list[tuple[str, Mapping[str, Any]]]] = {}
    for source_id, source in sources.items():
        by_scope.setdefault(source.get("scope") or None, []).append((source_id, source))

    def title(scope: str | None) -> str:
        if scope is None:
            return "Other documents"
        return str((scopes.get(scope) or {}).get("title") or scope)

    def scope_order(scope: str | None) -> tuple[int, str]:
        if scope is None:
            return (2, "")
        return (0 if (scopes.get(scope) or {}).get("hub") else 1, title(scope).casefold())

    return [
        {
            "scope": scope,
            "title": title(scope),
            "hub": (scopes.get(scope) or {}).get("hub") if scope else None,
            "count": len(by_scope[scope]),
            "phases": _phases(by_scope[scope]),
        }
        for scope in sorted(by_scope, key=scope_order)
    ]


def _type_label(items: Iterable[tuple[str, Mapping[str, Any]]]) -> str | None:
    return next((str(item["docTypeLabel"]) for _, item in items if item.get("docTypeLabel")), None)


def _phases(items: Iterable[tuple[str, Mapping[str, Any]]]) -> list[dict[str, Any]]:
    by_phase: dict[str | None, list[tuple[str, Mapping[str, Any]]]] = {}
    for item in items:
        by_phase.setdefault(item[1].get("phase") or None, []).append(item)
    phases: list[dict[str, Any]] = []
    for phase in sorted(by_phase, key=lambda value: (value is None, value or "")):
        by_type: dict[str | None, list[tuple[str, Mapping[str, Any]]]] = {}
        for item in by_phase[phase]:
            by_type.setdefault(item[1].get("docType") or None, []).append(item)
        phases.append(
            {
                "phase": phase,
                "title": f"Phase {phase}" if phase else "No phase",
                "types": [
                    {
                        "type": doc_type,
                        "title": _type_title(doc_type, _type_label(by_type[doc_type])),
                        "sources": [
                            source_id for source_id, _ in sorted(by_type[doc_type], key=_source_key)
                        ],
                    }
                    for doc_type in sorted(by_type, key=lambda value: (value is None, value or ""))
                ],
            }
        )
    return phases
