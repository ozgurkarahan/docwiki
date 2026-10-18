"""Neutral file metadata: Office core/app properties, PDF info, no thumbnails, no EXIF."""

from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path
from typing import Any

from PIL import Image

AUTHOR = "DocWiki sample generator"
_IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf")


def _xml_value(xml: str, tag: str) -> str:
    match = re.search(rf"<{tag}[^>]*>([^<]*)</{tag}>", xml)
    return match.group(1) if match else ""


def _assert_no_exif(data: bytes, label: str) -> None:
    with Image.open(io.BytesIO(data)) as img:
        assert not img.getexif(), f"EXIF in {label}"
        assert "exif" not in img.info, f"EXIF in {label}"
        assert not {"Software", "Author", "Comment", "Description"} & set(img.info), label


def test_office_metadata_is_neutral(
    documents: list[dict[str, Any]], corpus_root: Path, bible: dict[str, Any]
) -> None:
    organisations = {org["key"]: org["name"] for org in bible["organisations"]}
    catalog = {doc["path"]: doc for doc in bible["documents"]}
    office = [e for e in documents if e["format"] in ("docx", "xlsx", "pptx")]
    assert len(office) >= 15
    for entry in office:
        doc = catalog[entry["path"]]
        with zipfile.ZipFile(corpus_root / entry["path"]) as package:
            names = package.namelist()
            assert not any("thumbnail" in name for name in names), entry["path"]
            core = package.read("docProps/core.xml").decode("utf-8")
            app = package.read("docProps/app.xml").decode("utf-8")
            assert _xml_value(core, "dc:creator") == AUTHOR, entry["path"]
            assert _xml_value(core, "cp:lastModifiedBy") == AUTHOR, entry["path"]
            assert _xml_value(core, "cp:revision") == "1", entry["path"]
            assert _xml_value(core, "dcterms:created") == f"{doc['date']}T08:30:00Z"
            assert _xml_value(core, "dcterms:modified") == f"{doc['date']}T16:45:00Z"
            assert _xml_value(app, "Application") == AUTHOR, entry["path"]
            assert _xml_value(app, "Company") == organisations[doc["organisation"]].replace(
                "&", "&amp;"
            )
            for info in package.infolist():
                assert info.date_time[:3] == tuple(int(x) for x in doc["date"].split("-"))
                if info.filename.lower().endswith(_IMAGE_SUFFIXES):
                    _assert_no_exif(package.read(info.filename), f"{entry['path']}:{info.filename}")


def test_python_libraries_metadata_is_gone(documents: list[dict[str, Any]], extracted) -> None:
    for entry in documents:
        if entry["format"] in ("docx", "xlsx", "pptx"):
            metadata = extracted(entry["path"]).metadata
            assert metadata["author"] == AUTHOR and metadata["last_modified_by"] == AUTHOR


def test_pdf_metadata_is_neutral(documents: list[dict[str, Any]], extracted) -> None:
    pdfs = [e for e in documents if e["format"] == "pdf"]
    assert len(pdfs) >= 10
    for entry in pdfs:
        metadata = extracted(entry["path"]).metadata
        for key in ("Author", "Creator", "Producer"):
            assert metadata.get(key) == AUTHOR, f"{entry['path']} {key}"
        assert metadata["CreationDate"].startswith("D:" + entry["date"].replace("-", ""))


def test_images_have_no_exif_or_text_chunks(
    documents: list[dict[str, Any]], corpus_root: Path
) -> None:
    images = [e for e in documents if e["format"] in ("jpg", "png")]
    assert {e["format"] for e in images} == {"jpg", "png"}
    for entry in images:
        data = (corpus_root / entry["path"]).read_bytes()
        _assert_no_exif(data, entry["path"])
        with Image.open(io.BytesIO(data)) as img:
            assert set(img.info) <= {"dpi", "jfif", "jfif_version", "jfif_unit", "jfif_density"}
