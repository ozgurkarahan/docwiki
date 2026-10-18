"""Make Office Open XML packages (DOCX, XLSX, PPTX) neutral and reproducible.

python-docx, openpyxl and python-pptx stamp the current time, their own names and template
thumbnails into the package. This module rewrites the package with:

* neutral core properties (author and last-modified-by "DocWiki sample generator"),
* extended properties naming the organisation from the bible as company,
* no template thumbnail,
* fixed ZIP entry timestamps and attributes.
"""

from __future__ import annotations

import io
import re
import zipfile
from datetime import datetime
from xml.sax.saxutils import escape

from .common import GENERATOR_AUTHOR, DocMeta

_CORE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
    'core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" '
    'xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
    "<dc:title>{title}</dc:title>"
    "<dc:subject>{subject}</dc:subject>"
    "<dc:creator>{author}</dc:creator>"
    "<cp:keywords>{keywords}</cp:keywords>"
    "<dc:description>{subject}</dc:description>"
    "<cp:lastModifiedBy>{author}</cp:lastModifiedBy>"
    "<cp:revision>1</cp:revision>"
    "<dc:language>{lang}</dc:language>"
    '<dcterms:created xsi:type="dcterms:W3CDTF">{created}</dcterms:created>'
    '<dcterms:modified xsi:type="dcterms:W3CDTF">{modified}</dcterms:modified>'
    "</cp:coreProperties>"
)

_APP = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
    'extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/'
    'docPropsVTypes">'
    "<Application>{author}</Application>"
    "<Company>{company}</Company>"
    "<DocSecurity>0</DocSecurity>"
    "</Properties>"
)

_THUMB_REL = re.compile(r"<Relationship[^>]*Target=\"/?docProps/thumbnail\.jpeg\"[^>]*/>")
_THUMB_OVERRIDE = re.compile(r"<Override[^>]*PartName=\"/docProps/thumbnail\.jpeg\"[^>]*/>")
_LANG_CODES = {"en": "en-GB", "fr": "fr-FR", "de": "de-DE"}


def _w3c(value: datetime) -> str:
    return value.replace(tzinfo=None).isoformat(timespec="seconds") + "Z"


def finalize_package(data: bytes, meta: DocMeta) -> bytes:
    """Return a rewritten OOXML package with neutral metadata and fixed ZIP timestamps."""
    core = _CORE.format(
        title=escape(meta.title),
        subject=escape(meta.subject),
        author=GENERATOR_AUTHOR,
        keywords=escape(meta.keywords),
        lang=_LANG_CODES.get(meta.lang, meta.lang),
        created=_w3c(meta.created),
        modified=_w3c(meta.modified),
    ).encode("utf-8")
    app = _APP.format(author=GENERATOR_AUTHOR, company=escape(meta.organisation)).encode("utf-8")

    source = zipfile.ZipFile(io.BytesIO(data))
    entries: list[tuple[str, bytes]] = []
    for info in source.infolist():
        name = info.filename
        if name == "docProps/thumbnail.jpeg":
            continue
        content = source.read(name)
        if name == "docProps/core.xml":
            content = core
        elif name == "docProps/app.xml":
            content = app
        elif name == "_rels/.rels":
            content = _THUMB_REL.sub("", content.decode("utf-8")).encode("utf-8")
        elif name == "[Content_Types].xml":
            content = _THUMB_OVERRIDE.sub("", content.decode("utf-8")).encode("utf-8")
        entries.append((name, content))
    names = {name for name, _ in entries}
    if "docProps/core.xml" not in names or "docProps/app.xml" not in names:
        raise ValueError("OOXML package without core or extended properties part")

    stamp = meta.modified
    date_time = (stamp.year, stamp.month, stamp.day, stamp.hour, stamp.minute, 0)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as target:
        for name, content in entries:
            info = zipfile.ZipInfo(name, date_time=date_time)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 0
            info.external_attr = 0
            target.writestr(info, content, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    return out.getvalue()
