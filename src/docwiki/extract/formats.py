"""Supported input formats: file extension → (format family, media type)."""

from __future__ import annotations

from pathlib import PurePosixPath
from typing import Literal

__all__ = ["FORMATS", "SUPPORTED_EXTENSIONS", "FormatFamily", "detect_format"]

FormatFamily = Literal[
    "pdf", "docx", "xlsx", "csv", "pptx", "eml", "vtt", "markdown", "text", "image"
]

FORMATS: dict[str, tuple[FormatFamily, str]] = {
    ".pdf": ("pdf", "application/pdf"),
    ".docx": ("docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    ".xlsx": ("xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    ".xlsm": ("xlsx", "application/vnd.ms-excel.sheet.macroenabled.12"),
    ".csv": ("csv", "text/csv"),
    ".tsv": ("csv", "text/tab-separated-values"),
    ".pptx": (
        "pptx",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ),
    ".eml": ("eml", "message/rfc822"),
    ".vtt": ("vtt", "text/vtt"),
    ".md": ("markdown", "text/markdown"),
    ".markdown": ("markdown", "text/markdown"),
    ".txt": ("text", "text/plain"),
    ".png": ("image", "image/png"),
    ".jpg": ("image", "image/jpeg"),
    ".jpeg": ("image", "image/jpeg"),
    ".tif": ("image", "image/tiff"),
    ".tiff": ("image", "image/tiff"),
    ".bmp": ("image", "image/bmp"),
    ".gif": ("image", "image/gif"),
    ".webp": ("image", "image/webp"),
}

SUPPORTED_EXTENSIONS: tuple[str, ...] = tuple(sorted(FORMATS))


def detect_format(rel_path: str) -> tuple[FormatFamily, str] | None:
    """Format family and media type from the file extension (case-insensitive), else None."""
    return FORMATS.get(PurePosixPath(rel_path).suffix.lower())
