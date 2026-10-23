"""Load the fictional world bible (``samples/fiction/bible.yaml``)."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BIBLE_PATH = REPO_ROOT / "samples" / "fiction" / "bible.yaml"


class World:
    """Read-only accessors over the bible data. Every printed name and number comes from here."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.data = data
        world = data["world"]
        self.stamp: str = world["stamp"]
        self.stamp_variants: list[str] = list(world["stamp_variants"])
        self.author: str = world["generator"]["author"]
        self.seed: int = int(world["generator"]["seed"])
        self.canary: str = data["injection"]["canary"]
        self._orgs = {o["key"]: o for o in data["organisations"]}
        self._people = {p["key"]: p for p in data["people"]}
        self._docs = {d["id"]: d for d in data["documents"]}
        self._places = {p["key"]: p for p in data["places"]}
        self._products = {p["key"]: p for p in data["products"]}
        self._lots = {int(p["lot"]): p for p in data["work_packages"]}

    # -- organisations and people -------------------------------------------------------------
    def org(self, key: str) -> dict[str, Any]:
        return self._orgs[key]

    def org_name(self, key: str) -> str:
        return str(self._orgs[key]["name"])

    def org_by_role(self, role: str) -> dict[str, Any]:
        matches = [org for org in self._orgs.values() if org["role"] == role]
        if len(matches) != 1:
            raise ValueError(f"expected one organisation with role {role!r}")
        return matches[0]

    def person(self, key: str) -> dict[str, Any]:
        return self._people[key]

    def name(self, key: str) -> str:
        return str(self._people[key]["name"])

    def role(self, key: str) -> str:
        return str(self._people[key]["role"])

    def email(self, key: str) -> str:
        return str(self._people[key]["email"])

    def legal_line(self, *keys: str) -> str:
        """The fictional legal identity line of one or more organisations (all-zero format)."""
        identity = str(self.data["world"]["legal_identity"])
        return " ; ".join(f"{self.org_name(key)} - {identity}" for key in keys)

    def label(self, key: str) -> str:
        """Name of a person or of an organisation key."""
        if key in self._people:
            return self.name(key)
        return self.org_name(key)

    # -- places, products, work packages ------------------------------------------------------
    def place(self, key: str) -> dict[str, Any]:
        return self._places[key]

    def product(self, key: str) -> dict[str, Any]:
        return self._products[key]

    def lot(self, number: int) -> dict[str, Any]:
        return self._lots[int(number)]

    @property
    def lots(self) -> list[dict[str, Any]]:
        return [self._lots[number] for number in sorted(self._lots)]

    # -- documents and facts ------------------------------------------------------------------
    def doc(self, doc_id: str) -> dict[str, Any]:
        return self._docs[doc_id]

    @property
    def documents(self) -> list[dict[str, Any]]:
        return list(self.data["documents"])

    @property
    def facts(self) -> dict[str, Any]:
        return self.data["facts"]

    @property
    def builder(self) -> dict[str, Any]:
        return self.org_by_role("builder")

    @property
    def client(self) -> dict[str, Any]:
        return self.org_by_role("client")

    @property
    def town(self) -> str:
        return str(self._places["valbrise"]["name"])


@cache
def load_world(path: Path = BIBLE_PATH) -> World:
    """Parse the bible once per process."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return World(data)
