"""Command line entry point for the sample corpus generators.

Usage (from the repository root)::

    uv run python samples/generators/build.py --out samples/corpus
    uv run python samples/generators/build.py --out .local/corpus --only devis-b mail-fournisseur
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the fictional DocWiki sample corpus.")
    parser.add_argument("--out", type=Path, required=True, help="output folder (samples/corpus)")
    parser.add_argument("--only", nargs="*", help="generate only these bible document ids")
    parser.add_argument("--no-manifest", action="store_true", help="do not write MANIFEST.json")
    args = parser.parse_args(argv)

    if __package__ in (None, ""):
        # Executed as a script: make the repository root importable.
        sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from samples.generators.corpus import build_corpus

    manifest = build_corpus(args.out, only=args.only, write_manifest=not args.no_manifest)
    if manifest is not None:
        totals = manifest["totals"]
        print(
            f"wrote {totals['files']} files ({totals['documents']} documents and "
            f"{totals['held_back']} held back, {totals['bytes'] / 1_000_000:.1f} MB) to {args.out}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
