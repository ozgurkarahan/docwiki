"""``extract_source``: one raw file → ExtractedDoc, figure images and page renders."""

from __future__ import annotations

import asyncio
import importlib.metadata
import logging
from pathlib import Path, PurePosixPath

from pydantic import ValidationError

from docwiki.contracts import sha256_bytes, source_id_for
from docwiki.contracts.ids import normalize_raw_path
from docwiki.engine_types import ExtractionError, ExtractResult, ExtractSettings
from docwiki.extract._draft import ADAPTER_VERSION, CU_ADAPTER_VERSION, Draft, finalize
from docwiki.extract._text import one_line
from docwiki.extract.cu import extract_with_cu, normalize_endpoint
from docwiki.extract.figures import describe_figures
from docwiki.extract.formats import SUPPORTED_EXTENSIONS, FormatFamily, detect_format
from docwiki.extract.local_csv import extract_csv
from docwiki.extract.local_docx import extract_docx
from docwiki.extract.local_eml import extract_eml
from docwiki.extract.local_image import extract_image
from docwiki.extract.local_pdf import extract_pdf
from docwiki.extract.local_pptx import extract_pptx
from docwiki.extract.local_text import extract_text
from docwiki.extract.local_vtt import extract_vtt
from docwiki.extract.local_xlsx import extract_xlsx
from docwiki.llm import LlmClient

__all__ = [
    "extract_source",
    "extractor_versions",
    "run_local_adapter",
    "uses_content_understanding",
]

logger = logging.getLogger("docwiki.extract")

_LIBRARIES = ("pypdfium2", "python-docx", "openpyxl", "python-pptx", "pillow")


def extractor_versions() -> dict[str, str]:
    """Versions that determine extraction output (for run reports and cache keys)."""
    versions = {"local": ADAPTER_VERSION, "content-understanding": CU_ADAPTER_VERSION}
    for name in _LIBRARIES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:  # pragma: no cover - extra installed
            versions[name] = "missing"
    return versions


def uses_content_understanding(rel_path: str, settings: ExtractSettings) -> bool:
    """True when ``extract_source`` would call Content Understanding for this file."""
    detected = detect_format(rel_path)
    return settings.mode == "azure" and detected is not None and detected[0] in ("pdf", "image")


def _check_settings(settings: ExtractSettings, *, cloud: bool) -> None:
    if settings.max_pages < 1:
        raise ValueError("ExtractSettings.max_pages must be >= 1")
    if not 36 <= settings.page_render_dpi <= 600:
        raise ValueError("ExtractSettings.page_render_dpi must be between 36 and 600")
    if not cloud:
        return
    if settings.cu_mode in ("live", "record"):
        if not settings.cu_endpoint:
            raise ValueError("ExtractSettings.cu_endpoint is required in azure mode")
        normalize_endpoint(settings.cu_endpoint)
    if settings.cu_mode in ("record", "replay") and settings.recordings_dir is None:
        raise ValueError(
            f"ExtractSettings.recordings_dir is required for cu_mode={settings.cu_mode}"
        )


def run_local_adapter(
    family: FormatFamily, media_type: str, data: bytes, settings: ExtractSettings
) -> Draft:
    """Run the deterministic local adapter of ``family`` (synchronous, CPU-bound)."""
    draft = Draft()
    match family:
        case "pdf":
            extract_pdf(data, draft, max_pages=settings.max_pages, dpi=settings.page_render_dpi)
        case "docx":
            extract_docx(data, draft)
        case "xlsx":
            extract_xlsx(data, draft)
        case "csv":
            extract_csv(data, draft, tab_separated=media_type == "text/tab-separated-values")
        case "pptx":
            extract_pptx(data, draft, max_pages=settings.max_pages)
        case "eml":
            extract_eml(data, draft)
        case "vtt":
            extract_vtt(data, draft)
        case "markdown":
            extract_text(data, draft, markdown=True)
        case "text":
            extract_text(data, draft, markdown=False)
        case "image":
            extract_image(data, draft)
    return draft


async def extract_source(
    raw_file: Path,
    *,
    rel_path: str,
    settings: ExtractSettings,
    llm: LlmClient | None = None,
) -> ExtractResult:
    """Extract one source file into the ExtractedDoc evidence contract.

    ``rel_path`` is the raw path relative to the input root (it defines the ``source_id``).
    PDFs and images use Content Understanding when ``settings.mode == "azure"``; every other
    format, and every format in local mode, uses the deterministic local adapters. ``llm`` is
    only used for figure descriptions (``fast`` tier) when ``settings.describe_figures``.

    Raises :class:`~docwiki.engine_types.ExtractionError` when the source cannot be extracted
    (unsupported type, unreadable or damaged file, Content Understanding failure); recoverable
    issues are reported as warnings. Invalid settings raise ``ValueError``.
    """
    source_id = source_id_for(rel_path)
    source_path = normalize_raw_path(rel_path)
    detected = detect_format(source_path)
    if detected is None:
        suffix = PurePosixPath(source_path).suffix.lower() or "(no extension)"
        supported = ", ".join(SUPPORTED_EXTENSIONS)
        raise ExtractionError(source_id, f"unsupported file type {suffix}; supported: {supported}")
    family, media_type = detected
    cloud = settings.mode == "azure" and family in ("pdf", "image")
    _check_settings(settings, cloud=cloud)
    try:
        data = await asyncio.to_thread(Path(raw_file).read_bytes)
    except OSError as exc:
        raise ExtractionError(
            source_id, f"cannot read the file: {exc.strerror or type(exc).__name__}"
        ) from exc

    try:
        if cloud:
            draft = await extract_with_cu(data, fmt=family, settings=settings, source_id=source_id)
        else:
            draft = await asyncio.to_thread(run_local_adapter, family, media_type, data, settings)
    except ExtractionError:
        raise
    except Exception as exc:
        logger.warning("extraction of %s (%s) failed", source_id, family, exc_info=True)
        detail = one_line(str(exc))[:300]
        reason = f"{family} could not be parsed: {type(exc).__name__}" + (
            f": {detail}" if detail else ""
        )
        raise ExtractionError(source_id, reason) from exc

    descriptions: dict[int, str] = {}
    if settings.describe_figures and llm is not None and draft.figures:
        descriptions = await describe_figures(draft.figures, llm, source_id=source_id, draft=draft)
    try:
        doc, figure_png = finalize(
            draft,
            source_id=source_id,
            source_path=source_path,
            source_hash=sha256_bytes(data),
            media_type=media_type,
            descriptions=descriptions,
        )
    except ValidationError as exc:
        first = exc.errors(include_url=False)[0]
        where = ".".join(str(part) for part in first["loc"])
        raise ExtractionError(
            source_id, f"invalid extraction result at {where}: {first['msg']}"
        ) from exc
    return ExtractResult(
        doc=doc,
        figures=figure_png,
        page_images=dict(draft.page_images),
        warnings=list(doc.extraction.warnings),
    )
