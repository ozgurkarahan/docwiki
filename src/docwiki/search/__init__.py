"""Release search index ``search.db``: SQLite FTS5 with a pure-Python BM25 fallback."""

from docwiki.search.index import (
    SearchBlock,
    SearchDbInfo,
    SearchHit,
    SearchIndex,
    blocks_from_extracted,
    build_search_db,
    fts5_available,
    make_snippet,
)
from docwiki.search.text import tokenize

__all__ = [
    "SearchBlock",
    "SearchDbInfo",
    "SearchHit",
    "SearchIndex",
    "blocks_from_extracted",
    "build_search_db",
    "fts5_available",
    "make_snippet",
    "tokenize",
]
