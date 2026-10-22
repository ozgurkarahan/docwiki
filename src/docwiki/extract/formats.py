"""Supported input formats (moved to :mod:`docwiki.contracts.formats`, which the portal imports
without the extraction libraries)."""

from __future__ import annotations

from docwiki.contracts.formats import FORMATS, SUPPORTED_EXTENSIONS, FormatFamily, detect_format

__all__ = ["FORMATS", "SUPPORTED_EXTENSIONS", "FormatFamily", "detect_format"]
