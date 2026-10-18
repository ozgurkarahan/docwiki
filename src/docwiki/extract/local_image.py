"""Images (scans, photos): the whole image as a figure plus an OCR block (local adapter).

Local extraction has no OCR engine, so the ``ocr-line`` block is empty and a ``needs-ocr``
warning is recorded; Azure mode replaces it with Content Understanding OCR regions.
"""

from __future__ import annotations

from docwiki.contracts.locators import ImageRegionLocator
from docwiki.extract._draft import Draft
from docwiki.extract._images import decode_image, png_bytes

__all__ = ["FULL_IMAGE", "extract_image", "load_page_image"]

FULL_IMAGE = [0.0, 0.0, 1.0, 1.0]


def load_page_image(data: bytes, draft: Draft) -> bytes:
    """PNG of the first frame (EXIF orientation applied); warns about extra frames."""
    image, frames = decode_image(data)
    if frames > 1:
        draft.warn("image-frames", f"only the first of {frames} frames is extracted")
    return png_bytes(image)


def extract_image(data: bytes, draft: Draft) -> None:
    png = load_page_image(data, draft)
    draft.page_images[1] = png
    draft.page_count = 1
    draft.warn("needs-ocr", "the image has no text layer (local extraction does not run OCR)")
    locator = ImageRegionLocator(region=1, bbox=list(FULL_IMAGE))
    draft.block("ocr-line", "", locator, "ocr")
    draft.figure(locator, png, bbox=list(FULL_IMAGE))
