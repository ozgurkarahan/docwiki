"""Build evaluation-only dense vectors for every docs row of an immutable release."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
from typing import Any

import numpy as np

from docwiki.contracts.layout import ReleaseFiles
from docwiki.llm.embed_input import EMBED_INPUT_VERSION, build_embed_input
from docwiki.llm.embeddings import EmbeddingClient
from docwiki.llm.foundry_embeddings import FoundryEmbeddingClient
from docwiki.llm.settings import LlmSettings
from docwiki.mcp.dense import ARTIFACT_FORMAT, index_rows, row_keys
from docwiki.mcp.source import FolderReleaseSource


async def build_vectors(
    release: Path, out: Path, client: EmbeddingClient, *, batch_size: int = 64
) -> dict[str, Any]:
    """Use Gate A's title/section/text rule, preserving row order and complete row coverage."""
    if not 1 <= batch_size <= 2048:
        raise ValueError("batch_size must be in [1, 2048]")
    snap = FolderReleaseSource(release).current()
    try:
        if out.resolve().is_relative_to(snap.reader.root.resolve()):
            raise ValueError("the vector artifact must be outside the immutable release folder")
        rows = index_rows(snap.search)
        info = await client.describe()
        if not info.model_name:
            raise ValueError("embedding deployment must report its model")
        vectors: list[tuple[float, ...]] = []
        tokens = calls = 0
        for start in range(0, len(rows), batch_size):
            texts = [
                build_embed_input(row["title"], row["section"], row["text"]).text
                for row in rows[start : start + batch_size]
            ]
            result = await client.embed(texts, "document", EMBED_INPUT_VERSION)
            if result.dimensions != info.dimensions or result.model != info.model_name:
                raise ValueError("embedding result does not match the described model/dimensions")
            vectors.extend(result.vectors)
            tokens += result.usage.input_tokens
            calls += result.calls
        matrix = np.asarray(vectors, dtype=np.float32).reshape(len(rows), info.dimensions)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        if not np.isfinite(matrix).all() or np.any(norms == 0):
            raise ValueError("embedding result contains non-finite or zero vectors")
        matrix /= norms
        metadata = {
            "format": ARTIFACT_FORMAT,
            "release_id": snap.release_id,
            "model": info.model_name,
            "model_version": info.model_version,
            "dimensions": info.dimensions,
            "input_version": EMBED_INPUT_VERSION,
            "search_sha256": snap.reader.manifest.files[ReleaseFiles.SEARCH_DB].sha256,
        }
        out.parent.mkdir(parents=True, exist_ok=True)
        # A file handle prevents numpy from silently adding ".npz" to the requested filename.
        with out.open("wb") as stream:
            np.savez_compressed(
                stream,
                metadata=np.asarray(json.dumps(metadata, sort_keys=True)),
                rows=np.asarray(json.dumps(row_keys(rows))),
                rowids=np.asarray([row["rowid"] for row in rows], dtype=np.int64),
                matrix=matrix,
            )
        ledger = getattr(client, "ledger", None)
        receipt = ledger.receipt() if ledger is not None else None
        return {
            **metadata,
            "rows": len(rows),
            "tokens": tokens,
            "calls": calls,
            "estimated_cost_usd": receipt.totals.estimated_cost_usd if receipt else None,
            "prices_verified": receipt.prices_verified if receipt else False,
        }
    finally:
        snap.close()


async def _main(args: argparse.Namespace) -> None:
    settings = LlmSettings.from_env()
    if args.batch_size is not None:
        settings = settings.model_copy(update={"embed_batch_size": args.batch_size})
    client = FoundryEmbeddingClient(settings)
    try:
        report = await build_vectors(
            args.release, args.out, client, batch_size=settings.embed_batch_size
        )
        print(json.dumps(report, sort_keys=True))
    finally:
        await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, choices=range(1, 2049), metavar="N")
    asyncio.run(_main(parser.parse_args()))


if __name__ == "__main__":
    main()
