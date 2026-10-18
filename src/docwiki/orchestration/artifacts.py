"""Content-addressed stage artifacts ``work/artifacts/<stage>/<cache_key>/…`` (architecture §5).

An artifact is a set of files written under its prefix followed by ``_complete.json`` listing
every file with its SHA-256. Only complete artifacts are reused, and their files are verified on
load, so a crash in the middle of a write can never be mistaken for a cache hit.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from docwiki.contracts._base import sha256_hex
from docwiki.contracts.layout import artifact_prefix
from docwiki.contracts.storage import KeyNotFoundError, Storage, validate_key

__all__ = ["COMPLETE_MARKER", "Artifact", "ArtifactStore"]

COMPLETE_MARKER = "_complete.json"
logger = logging.getLogger("docwiki.engine")


class Artifact:
    """A loaded, verified artifact: ``files`` maps relative names to bytes."""

    def __init__(self, stage: str, key: str, files: dict[str, bytes]) -> None:
        self.stage = stage
        self.key = key
        self.files = files

    def bytes(self, name: str) -> bytes:
        return self.files[name]

    def text(self, name: str) -> str:
        return self.files[name].decode("utf-8")

    def json(self, name: str) -> Any:
        return json.loads(self.text(name))

    def names(self, prefix: str = "") -> list[str]:
        return sorted(name for name in self.files if name.startswith(prefix))


class ArtifactStore:
    """Read and write artifacts on a :class:`~docwiki.contracts.storage.Storage`."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage

    @staticmethod
    def prefix(stage: str, key: str) -> str:
        return artifact_prefix(stage, key)

    def exists(self, stage: str, key: str) -> bool:
        return self.storage.exists(self.prefix(stage, key) + COMPLETE_MARKER)

    def load(self, stage: str, key: str) -> Artifact | None:
        """The verified artifact, or ``None`` when it is missing or damaged."""
        base = self.prefix(stage, key)
        try:
            manifest = json.loads(self.storage.read_bytes(base + COMPLETE_MARKER))
        except KeyNotFoundError:
            return None
        except ValueError:
            logger.warning("artifact %s/%s has an unreadable marker; recomputing", stage, key)
            return None
        files: dict[str, bytes] = {}
        for name, digest in dict(manifest.get("files", {})).items():
            try:
                data = self.storage.read_bytes(base + name)
            except KeyNotFoundError:
                logger.warning("artifact %s/%s lacks %s; recomputing", stage, key, name)
                return None
            if sha256_hex(data) != digest:
                logger.warning("artifact %s/%s file %s is damaged; recomputing", stage, key, name)
                return None
            files[name] = data
        return Artifact(stage, key, files)

    def save(self, stage: str, key: str, files: Mapping[str, bytes]) -> Artifact:
        """Write ``files`` then the completion marker (last)."""
        base = self.prefix(stage, key)
        digests: dict[str, str] = {}
        for name, data in sorted(files.items()):
            if name == COMPLETE_MARKER:
                raise ValueError(f"{COMPLETE_MARKER} is reserved")
            validate_key(base + name)
            self.storage.write_bytes(base + name, data)
            digests[name] = sha256_hex(data)
        marker = {
            "stage": stage,
            "cache_key": key,
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "files": digests,
        }
        self.storage.write_bytes(
            base + COMPLETE_MARKER,
            (json.dumps(marker, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        )
        return Artifact(stage, key, dict(files))
