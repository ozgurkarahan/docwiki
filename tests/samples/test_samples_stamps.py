"""Every sample document carries the fictional stamp (spec domain-and-corpus.md section 2 rule 4
and the document contract, section 3.4 rule 8)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from openpyxl import load_workbook
from PIL import Image, ImageDraw, ImageFilter

STAMP = "FICTIONAL - NOT FOR OPERATIONAL USE"


def _norm(text: str) -> str:
    return text.replace("\u2014", "-").replace("\u2013", "-")


def _first_last(lines: list[str]) -> tuple[str, str]:
    content = [line.strip() for line in lines if line.strip()]
    return content[0], content[-1]


def test_every_document_is_stamped(documents: list[dict[str, Any]]) -> None:
    modes = {"header-footer", "first-last-line", "image"}
    for entry in documents:
        assert entry["stamp"] in modes, entry["path"]


def test_stamps_are_present(documents: list[dict[str, Any]], extracted, corpus_root: Path) -> None:
    checked = 0
    for entry in documents:
        mode, fmt, path = entry["stamp"], entry["format"], entry["path"]
        content = extracted(path)
        if mode == "header-footer":
            if fmt == "pdf":
                assert content.units, path
                for key, text in content.units:
                    assert _norm(text).count(STAMP) >= 2, f"{path} {key}"
            elif fmt == "docx":
                assert len(content.furniture) >= 2, path
                assert all(STAMP in _norm(text) for text in content.furniture), path
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
            assert fmt == "eml", path
            body = [t for k, t in content.units if k.startswith("msg-body")]
            assert _first_last(body) == (STAMP, STAMP), path
        else:
            assert mode == "image", path
            if fmt == "pdf":
                assert content.metadata.get("Subject") == STAMP, path
            else:
                assert fmt == "jpg", path
                _assert_caption(entry, corpus_root)
        checked += 1
    assert checked == len(documents) == 42


def _assert_caption(entry: dict[str, Any], corpus_root: Path) -> None:
    """The stamp is drawn in white on a darkened band where the generator puts the caption."""
    from samples.generators import gen_images
    from samples.generators.world import load_world

    source = gen_images.source_image(load_world(), entry["id"])
    box, origin, font = gen_images.caption_layout(source.size)
    mask = Image.new("L", source.size, 0)
    ImageDraw.Draw(mask).text(origin, STAMP, font=font, fill=255)
    near_text = np.asarray(mask.filter(ImageFilter.MaxFilter(7))) > 0
    text_core = np.asarray(mask.filter(ImageFilter.MinFilter(3))) == 255
    with Image.open(corpus_root / entry["path"]) as img:
        assert img.size == source.size, entry["path"]
        photo = np.asarray(img.convert("L")).astype(float)
    original = np.asarray(source.convert("L")).astype(float)
    band = np.zeros(photo.shape, dtype=bool)
    band[box[1] : box[3], box[0] : box[2]] = True
    band &= ~near_text
    assert text_core.sum() > 200, entry["path"]
    assert photo[text_core].mean() > 200, entry["path"]
    assert photo[band].mean() < 0.6 * original[band].mean() + 8, entry["path"]
    outside = ~np.zeros(photo.shape, dtype=bool)
    outside[box[1] - 4 : box[3] + 4, box[0] - 4 : box[2] + 4] = False
    assert abs(photo[outside].mean() - original[outside].mean()) < 2, entry["path"]
