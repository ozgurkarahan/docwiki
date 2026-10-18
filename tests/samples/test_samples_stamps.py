"""Every procedure-like sample document carries the fictional stamp."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook

STAMP = "FICTIONAL - NOT FOR OPERATIONAL USE"


def _norm(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-")


def _first_last(lines: list[str]) -> tuple[str, str]:
    content = [line.strip() for line in lines if line.strip()]
    return content[0], content[-1]


def test_procedure_like_documents_are_stamped(documents: list[dict[str, Any]]) -> None:
    for entry in documents:
        if entry["procedure_like"]:
            assert entry["stamp"] != "none", entry["path"]


def test_stamps_are_present(documents: list[dict[str, Any]], extracted, corpus_root: Path) -> None:
    checked = 0
    for entry in documents:
        mode, fmt, path = entry["stamp"], entry["format"], entry["path"]
        content = extracted(path)
        if mode == "header-footer":
            if fmt == "pdf":
                for key, text in content.units:
                    assert _norm(text).count(STAMP) >= 2, f"{path} {key}"
            elif fmt == "docx":
                assert len(content.furniture) >= 2, path
                assert all(STAMP in _norm(text) for text in content.furniture), path
            elif fmt == "pptx":
                for key, text in content.units:
                    assert STAMP in _norm(text), f"{path} {key}"
            elif fmt == "xlsx":
                workbook = load_workbook(corpus_root / path)
                for sheet in workbook.worksheets:
                    header = sheet.oddHeader.left.text or ""
                    header += sheet.oddHeader.center.text or ""
                    header += sheet.oddHeader.right.text or ""
                    assert STAMP in header and STAMP in (sheet.oddFooter.center.text or ""), path
            else:
                raise AssertionError(f"unexpected header-footer format {path}")
        elif mode == "first-last-line":
            if fmt == "eml":
                body = [t for k, t in content.units if k.startswith("msg-body")]
                assert _first_last(body) == (STAMP, STAMP), path
            elif fmt == "vtt":
                assert content.units[0][1] == STAMP and content.units[-1][1] == STAMP, path
            else:
                assert _first_last([t for _, t in content.units]) == (STAMP, STAMP), path
        elif mode == "image":
            if fmt == "pdf":
                assert content.metadata.get("Subject") == STAMP, path
            else:
                assert fmt in ("jpg", "png"), path
        else:
            assert mode == "none" and fmt == "csv", path
            continue
        checked += 1
    assert checked >= 35
