"""Load the fictional world bible (``samples/fiction/bible.yaml``)."""

from __future__ import annotations

from functools import cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BIBLE_PATH = REPO_ROOT / "samples" / "fiction" / "bible.yaml"


class World:
    """Read-only accessors over the bible data."""

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
        self._turbines = {t["id"]: t for t in data["turbines"]}
        self._alarms = {a["code"]: a for a in data["alarm_codes"]}
        self._statuses = {s["code"]: s for s in data["status_codes"]}
        self._parts = {p["part_number"]: p for p in data["parts"]}
        self._places = {p["key"]: p for p in data["places"]}
        self._products = {p["key"]: p for p in data["products"]}

    def org(self, key: str) -> dict[str, Any]:
        return self._orgs[key]

    def org_name(self, key: str) -> str:
        return str(self._orgs[key]["name"])

    def person(self, key: str) -> dict[str, Any]:
        return self._people[key]

    def name(self, key: str) -> str:
        return str(self._people[key]["name"])

    def role(self, key: str) -> str:
        return str(self._people[key]["role"])

    def email(self, key: str) -> str:
        return str(self._people[key]["email"])

    def doc(self, doc_id: str) -> dict[str, Any]:
        return self._docs[doc_id]

    @property
    def documents(self) -> list[dict[str, Any]]:
        return list(self.data["documents"])

    @property
    def turbines(self) -> list[dict[str, Any]]:
        return list(self.data["turbines"])

    def turbine(self, turbine_id: str) -> dict[str, Any]:
        return self._turbines[turbine_id]

    def alarm(self, code: str) -> dict[str, Any]:
        return self._alarms[code]

    def status(self, code: str) -> dict[str, Any]:
        return self._statuses[code]

    def part(self, part_number: str) -> dict[str, Any]:
        return self._parts[part_number]

    @property
    def parts(self) -> list[dict[str, Any]]:
        return list(self.data["parts"])

    def place(self, key: str) -> dict[str, Any]:
        return self._places[key]

    def product(self, key: str) -> dict[str, Any]:
        return self._products[key]

    @property
    def site_name(self) -> str:
        return str(self._places["quellmoor-ridge-wind-farm"]["name"])

    @property
    def site_short(self) -> str:
        return str(self._places["quellmoor-ridge-wind-farm"]["short"])


@cache
def load_world(path: Path = BIBLE_PATH) -> World:
    """Parse the bible once per process."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return World(data)
