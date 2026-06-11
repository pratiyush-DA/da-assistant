"""Supplemental OCR for images and diagrams in PDF/DOCX narrative documents."""

import io
import logging
import os
import shutil
from pathlib import Path

from django.conf import settings

from .types import ParsedElement

logger = logging.getLogger(__name__)

_OCR_VISUAL_CATEGORIES = frozenset({"Image", "Figure", "Table"})
_IMAGE_OCR_CATEGORY = "ImageOCR"


def _ocr_languages() -> list[str]:
    raw = getattr(settings, "PARSER_OCR_LANGUAGES", "eng")
    if isinstance(raw, str):
        return [lang.strip() for lang in raw.split(",") if lang.strip()]
    return list(raw)


def cleanup_figure_artifacts() -> None:
    """Remove unstructured hi_res figure crops; safe after OCR text is extracted."""
    figures_dir = Path.cwd() / "figures"
    if not figures_dir.is_dir():
        return
    shutil.rmtree(figures_dir, ignore_errors=True)


def _apply_ocr_padding_env() -> None:
    os.environ["EXTRACT_IMAGE_BLOCK_CROP_HORIZONTAL_PAD"] = str(
        getattr(settings, "PARSER_OCR_IMAGE_PAD_H", 20)
    )
    os.environ["EXTRACT_IMAGE_BLOCK_CROP_VERTICAL_PAD"] = str(
        getattr(settings, "PARSER_OCR_IMAGE_PAD_V", 10)
    )


def _element_page_number(el) -> int | None:
    metadata = getattr(el, "metadata", None)
    if metadata is None:
        return None
    return getattr(metadata, "page_number", None)


def _map_unstructured_element(el, index: int, *, source_kind: str) -> ParsedElement | None:
    text = (getattr(el, "text", None) or "").strip()
    if not text:
        return None
    category = getattr(el, "category", None) or type(el).__name__
    if source_kind == "image_ocr":
        category = _IMAGE_OCR_CATEGORY
    return ParsedElement(
        text=text,
        category=str(category),
        page_number=_element_page_number(el),
        source_kind=source_kind,
        element_index=index,
    )


def enrich_pdf_with_image_ocr(file_path: str) -> list[ParsedElement]:
    """hi_res pass for image/table blocks; returns OCR ParsedElements only."""
    from unstructured.partition.pdf import partition_pdf

    _apply_ocr_padding_env()
    languages = _ocr_languages()
    out: list[ParsedElement] = []
    try:
        try:
            raw = partition_pdf(
                filename=str(file_path),
                strategy="hi_res",
                extract_image_block_types=["Image", "Table"],
                extract_image_block_to_payload=True,
                languages=languages,
            )
        except Exception as exc:
            logger.warning("PDF hi_res OCR failed for %s: %s", file_path, exc)
            return []

        for i, el in enumerate(raw):
            cat = str(getattr(el, "category", "") or "")
            if cat not in _OCR_VISUAL_CATEGORIES:
                continue
            mapped = _map_unstructured_element(el, i, source_kind="image_ocr")
            if mapped:
                out.append(mapped)
        return out
    finally:
        cleanup_figure_artifacts()


def enrich_pdf_scanned_ocr(file_path: str) -> list[ParsedElement]:
    """Full-page OCR for scanned PDFs with low text density."""
    from unstructured.partition.pdf import partition_pdf

    languages = _ocr_languages()
    try:
        raw = partition_pdf(
            filename=str(file_path),
            strategy="ocr_only",
            languages=languages,
        )
    except Exception as exc:
        logger.warning("PDF ocr_only failed for %s: %s", file_path, exc)
        return []

    out: list[ParsedElement] = []
    for i, el in enumerate(raw):
        mapped = _map_unstructured_element(el, i, source_kind="text")
        if mapped:
            out.append(mapped)
    return out


def enrich_docx_with_image_ocr(file_path: str) -> list[ParsedElement]:
    """OCR embedded images from DOCX via python-docx + pytesseract."""
    try:
        from docx import Document
        import pytesseract
        from PIL import Image
    except ImportError as exc:
        logger.warning("DOCX OCR dependencies missing: %s", exc)
        return []

    max_images = getattr(settings, "PARSER_MAX_OCR_IMAGES", 30)
    doc = Document(file_path)
    out: list[ParsedElement] = []
    index = 0

    for rel in doc.part.rels.values():
        if "image" not in (rel.reltype or "").lower():
            continue
        if len(out) >= max_images:
            break
        try:
            blob = rel.target_part.blob
            image = Image.open(io.BytesIO(blob))
            text = pytesseract.image_to_string(image, lang="+".join(_ocr_languages()))
            text = text.strip()
            if not text:
                continue
            out.append(
                ParsedElement(
                    text=text,
                    category=_IMAGE_OCR_CATEGORY,
                    page_number=None,
                    source_kind="image_ocr",
                    element_index=index,
                )
            )
            index += 1
        except Exception as exc:
            logger.debug("DOCX image OCR skip: %s", exc)
            continue

    return out


def run_supplemental_ocr(
    file_path: str,
    detect_reason: str,
    use_scanned_fallback: bool,
) -> list[ParsedElement]:
    """Run the appropriate supplemental OCR strategy for file type."""
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        if use_scanned_fallback or detect_reason == "low_text_density":
            return enrich_pdf_scanned_ocr(file_path)
        return enrich_pdf_with_image_ocr(file_path)

    if ext in (".docx", ".doc"):
        return enrich_docx_with_image_ocr(file_path)

    return []
