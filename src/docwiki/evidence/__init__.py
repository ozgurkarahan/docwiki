"""Evidence sidecars (evidence-contract §5): what a citation points to, rendered for humans."""

from docwiki.evidence.builder import (
    MAX_SIDECAR_ROWS,
    PROVENANCE_NOTES,
    PROVENANCE_ORDER,
    build_evidence,
)
from docwiki.evidence.escape import escape_text, plain_text, quote_block, table_cell
from docwiki.evidence.guard import (
    CANARY_PLACEHOLDER,
    INJECTION_PLACEHOLDER,
    TextGuard,
    neutralize_sentences,
)
from docwiki.evidence.images import draw_highlights

__all__ = [
    "CANARY_PLACEHOLDER",
    "INJECTION_PLACEHOLDER",
    "MAX_SIDECAR_ROWS",
    "PROVENANCE_NOTES",
    "PROVENANCE_ORDER",
    "TextGuard",
    "build_evidence",
    "draw_highlights",
    "escape_text",
    "neutralize_sentences",
    "plain_text",
    "quote_block",
    "table_cell",
]
