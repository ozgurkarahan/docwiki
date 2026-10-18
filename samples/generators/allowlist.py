"""Generate samples/fiction/allowlist.txt (one term per line, sorted) from the bible.

Usage (from the repository root)::

    uv run python samples/generators/allowlist.py          # write the file
    uv run python samples/generators/allowlist.py --check  # fail if the file is out of date

Lines are proper nouns and role titles of the closed world, letter codes of fictional
identifiers, generic capitalised words used by the samples, the injection canary, and
`re:<regex>` lines for document-number and identifier schemes. This module is standalone (no
package imports) so that it also runs as a plain script.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BIBLE_PATH = REPO_ROOT / "samples" / "fiction" / "bible.yaml"
ALLOWLIST_PATH = REPO_ROOT / "samples" / "fiction" / "allowlist.txt"


def proper_nouns(data: dict[str, Any]) -> list[str]:
    """Organisation, place, product, person, role and asset names, plus technology names."""
    names: set[str] = set()
    for org in data["organisations"]:
        names.add(org["name"])
        names.add(org["short"])
    for place in data["places"]:
        names.add(place["name"])
        if place.get("short"):
            names.add(place["short"])
    for product in data["products"]:
        names.add(product["name"])
    for person in data["people"]:
        names.add(person["name"])
        names.add(person["role"])
        if person.get("ascii_name"):
            names.add(person["ascii_name"])
    for asset in data["other_assets"]:
        names.add(asset["name"])
    names.update(data["vocabulary"]["technology"])
    return sorted(names, key=_sort_key)


def terms(data: dict[str, Any]) -> list[str]:
    """All allowlist lines: names, codes, generic capitalised words and `re:` patterns."""
    lines = set(proper_nouns(data))
    lines.update(data["vocabulary"]["codes"])
    lines.update(data["vocabulary"]["generic"])
    # The canary is a fictional token of the corpus (its letter groups are not names).
    lines.add(data["injection"]["canary"])
    for scheme in data["document_number_schemes"]:
        lines.add("re:" + scheme["regex"])
    for pattern in data["identifier_patterns"]:
        lines.add("re:" + pattern["regex"])
    return sorted(lines, key=_sort_key)


def _sort_key(line: str) -> tuple[str, str]:
    return (line.casefold(), line)


def render(data: dict[str, Any]) -> str:
    return "\n".join(terms(data)) + "\n"


def load_bible(path: Path = BIBLE_PATH) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only check that the file is current")
    args = parser.parse_args(argv)
    expected = render(load_bible())
    if args.check:
        current = ALLOWLIST_PATH.read_text(encoding="utf-8") if ALLOWLIST_PATH.exists() else ""
        if current != expected:
            print("samples/fiction/allowlist.txt is out of date; "
                  "run samples/generators/allowlist.py")
            return 1
        return 0
    ALLOWLIST_PATH.write_bytes(expected.encode("utf-8"))
    print(f"wrote {len(expected.splitlines())} terms to samples/fiction/allowlist.txt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
