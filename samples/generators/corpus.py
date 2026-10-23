"""Build the corpus: check the bible arithmetic, run every generator, write MANIFEST.json."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from . import (
    gen_docx,
    gen_ecole,
    gen_eml,
    gen_entreprise,
    gen_images,
    gen_nacrines,
    gen_pdf,
    gen_scan,
    gen_xlsx,
)
from .common import write_bytes, write_text
from .datasets import check_world
from .datasets_f import check_world_f
from .manifest import MANIFEST_NAME, build_manifest
from .world import World, load_world

Generator = Callable[[World], bytes | str]

GENERATORS: dict[str, Generator] = {
    # chantier Moreau
    "devis-a": gen_pdf.devis_a,
    "devis-b": gen_pdf.devis_b,
    "contrat": gen_docx.contrat,
    "avenant": gen_docx.avenant,
    "planning-a": gen_xlsx.planning_a,
    "facture": gen_pdf.facture,
    "bl-scan": gen_scan.bl_scan,
    "cr3": gen_docx.compte_rendu,
    "mail-client": gen_eml.mail_client,
    "mail-fournisseur": gen_eml.mail_fournisseur,
    "photo-dalle": gen_images.photo_dalle,
    "photo-palettes": gen_images.photo_palettes,
    "etude-prix": gen_xlsx.etude_prix,
    "planning-b": gen_xlsx.planning_b,
    # chantier résidence Les Nacrines
    "nac-marche": gen_nacrines.marche,
    "nac-sous-traitance": gen_nacrines.sous_traitance,
    "nac-dc4": gen_nacrines.dc4,
    "nac-os1": gen_nacrines.os1,
    "nac-facture": gen_nacrines.facture,
    "nac-situation4": gen_nacrines.situation4,
    "nac-cr12": gen_nacrines.compte_rendu,
    "nac-pv": gen_nacrines.pv_scan,
    "nac-reserves": gen_nacrines.reserves,
    "nac-mail-vanarsdel": gen_nacrines.mail_vanarsdel,
    # chantier école de Montferrine
    "eco-ccap": gen_ecole.ccap,
    "eco-dpgf-a": gen_ecole.dpgf_a,
    "eco-dpgf-b": gen_ecole.dpgf_b,
    "eco-ae": gen_ecole.acte_engagement,
    "eco-bc-vanarsdel": gen_ecole.bon_de_commande,
    "eco-planning": gen_ecole.planning,
    "eco-cr-prep": gen_ecole.compte_rendu,
    "eco-mail-mairie": gen_ecole.mail_mairie,
    "eco-ppsps": gen_ecole.ppsps,
    # entreprise
    "ent-cgv": gen_entreprise.conditions_generales,
    "ent-organigramme": gen_entreprise.organigramme,
    "ent-contrat-cadre": gen_entreprise.contrat_cadre,
    "ent-tarif": gen_entreprise.tarif,
    "ent-planning-equipes": gen_entreprise.planning_equipes,
    "ent-registre-materiel": gen_entreprise.registre_materiel,
    "ent-registre-attestations": gen_entreprise.registre_attestations,
    "ent-suivi-facturation": gen_entreprise.suivi_facturation,
    "ent-marges": gen_entreprise.tableau_marges,
}

# Top-level folders of the corpus; a full build replaces them.
SUBFOLDERS = ("full", "held-back")


def build_corpus(
    out: Path, only: Iterable[str] | None = None, write_manifest: bool = True
) -> dict[str, Any] | None:
    """Generate the corpus into ``out``; a full build first removes the generated sub-folders."""
    world = load_world()
    check_world(world)
    check_world_f(world)
    ids = [str(doc["id"]) for doc in world.documents]
    missing = sorted(set(ids) - GENERATORS.keys())
    unknown = sorted(GENERATORS.keys() - set(ids))
    if missing or unknown:
        raise ValueError(f"generator mapping mismatch: missing={missing} unknown={unknown}")
    selected = set(only) if only else None
    if selected is not None and selected - set(ids):
        raise ValueError(f"unknown document ids: {sorted(selected - set(ids))}")
    out.mkdir(parents=True, exist_ok=True)
    if selected is None:
        for sub in SUBFOLDERS:
            target = out / sub
            if target.exists():
                shutil.rmtree(target)
    for doc in world.documents:
        doc_id = str(doc["id"])
        if selected is not None and doc_id not in selected:
            continue
        path = str(doc["path"])
        if path.split("/", 1)[0] not in SUBFOLDERS:
            raise ValueError(f"{doc_id}: path outside {SUBFOLDERS}: {path}")
        data = GENERATORS[doc_id](world)
        if isinstance(data, str):
            write_text(out, path, data)
        else:
            write_bytes(out, path, data)
    if not write_manifest:
        return None
    manifest = build_manifest(out, world)
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (out / MANIFEST_NAME).write_bytes(text.encode("utf-8"))
    return manifest
