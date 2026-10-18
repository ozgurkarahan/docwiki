"""Extraction: raw files → the ExtractedDoc evidence contract (evidence-contract §1–§2, §6).

Two adapters produce the same structure: deterministic local parsers for every format, and
Azure Content Understanding (``mode="azure"``) for PDFs and images only. See ``README.md``.
"""

from docwiki.extract._draft import ADAPTER_VERSION, CU_ADAPTER_VERSION, CU_API_VERSION
from docwiki.extract.core import (
    extract_source,
    extractor_versions,
    run_local_adapter,
    uses_content_understanding,
)
from docwiki.extract.cu import ContentUnderstandingError
from docwiki.extract.figures import FIGURE_PROMPT_VERSION, FIGURE_SCHEMA_NAME
from docwiki.extract.formats import FORMATS, SUPPORTED_EXTENSIONS, detect_format

__all__ = [
    "ADAPTER_VERSION",
    "CU_ADAPTER_VERSION",
    "CU_API_VERSION",
    "FIGURE_PROMPT_VERSION",
    "FIGURE_SCHEMA_NAME",
    "FORMATS",
    "SUPPORTED_EXTENSIONS",
    "ContentUnderstandingError",
    "detect_format",
    "extract_source",
    "extractor_versions",
    "run_local_adapter",
    "uses_content_understanding",
]
