"""Build the corpus: run every generator, copy the quickstart subset, write MANIFEST.json."""

from __future__ import annotations

import json
import shutil
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from . import (
    gen_csv,
    gen_docx,
    gen_eml,
    gen_images,
    gen_pdf,
    gen_pptx,
    gen_scan,
    gen_text,
    gen_vtt,
    gen_xlsx,
)
from .common import write_bytes, write_text
from .manifest import MANIFEST_NAME, build_manifest
from .world import World, load_world

Generator = Callable[[World], bytes | str]

GENERATORS: dict[str, Generator] = {
    "manual-gbx": gen_pdf.manual_gbx,
    "sb-oil": gen_pdf.sb_oil,
    "sb-pitch-a": gen_pdf.sb_pitch_a,
    "sb-pitch-b": gen_pdf.sb_pitch_b,
    "sop-gbx-a": gen_docx.sop_gbx_a,
    "sop-gbx-b": gen_docx.sop_gbx_b,
    "sop-loto": gen_docx.sop_loto,
    "sop-wah": gen_docx.sop_wah,
    "wi-gen-fr": gen_docx.wi_gen_fr,
    "inc-near-miss": gen_pdf.near_miss,
    "inc-8d": gen_docx.inc_8d,
    "moc-oil": gen_docx.moc_oil,
    "asset-register": gen_xlsx.asset_register,
    "maintenance-plan": gen_xlsx.maintenance_plan,
    "stock": gen_xlsx.spare_parts_stock,
    "scada-log": gen_csv.scada_log,
    "work-orders": gen_csv.work_orders,
    "vibration": gen_csv.vibration,
    "kpi": gen_csv.kpi,
    "oil-lab": gen_pdf.oil_lab,
    "blade-inspection": gen_pdf.blade_inspection,
    "lift-plan-scan": gen_scan.lift_plan_scan,
    "env-permit": gen_pdf.env_permit,
    "grid-instruction": gen_pdf.grid_instruction,
    "safety-audit": gen_pdf.safety_audit,
    "deck-onboarding": gen_pptx.onboarding,
    "deck-gearbox": gen_pptx.gearbox_fundamentals,
    "deck-spl": gen_pptx.spl_oil_level,
    "mail-oem": gen_eml.oem_support,
    "mail-shortage": gen_eml.parts_shortage,
    "photo-checklist": gen_images.checklist_photo,
    "site-plan": gen_images.site_plan,
    "shift-en-1": gen_text.shift_en_1,
    "shift-fr": gen_text.shift_fr,
    "shift-en-2": gen_text.shift_en_2,
    "supplier-de": gen_text.supplier_de,
    "tbt-vtt": gen_vtt.toolbox_talk,
    "minutes-june": gen_docx.minutes_june,
    "rate-card": gen_xlsx.rate_card,
    "it-runbook": gen_docx.it_runbook,
    "it-handbook": gen_text.it_handbook,
    "it-failover": gen_pdf.it_failover,
    "it-postmortem": gen_docx.it_postmortem,
    "it-catalog": gen_csv.it_catalog,
}

# The work-order export imitates a maintenance-system export with a UTF-8 byte order mark.
BOM_DOCUMENTS = frozenset({"work-orders"})
SUBFOLDERS = ("full", "quickstart", "held-back", "it-runbooks")


def quickstart_path(path: str) -> str:
    return "quickstart/" + path.removeprefix("full/")


def build_corpus(
    out: Path, only: Iterable[str] | None = None, write_manifest: bool = True
) -> dict[str, Any] | None:
    """Generate the corpus into ``out``; a full build first removes the generated sub-folders."""
    world = load_world()
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
        data = GENERATORS[doc_id](world)
        path = str(doc["path"])
        if isinstance(data, str):
            written = write_text(out, path, data, bom=doc_id in BOM_DOCUMENTS)
        else:
            written = write_bytes(out, path, data)
        if doc.get("quickstart"):
            write_bytes(out, quickstart_path(path), written.read_bytes())
    if not write_manifest:
        return None
    manifest = build_manifest(out, world)
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    (out / MANIFEST_NAME).write_bytes(text.encode("utf-8"))
    return manifest
