"""Generic document parsing via unstructured (PDF, DOCX, etc.) with adaptive image OCR."""

import logging
from pathlib import Path

from django.conf import settings

from .element_merge import merge_parsed_elements
from .ocr_enrichment import enrich_pdf_scanned_ocr, run_supplemental_ocr
from .types import FastParseResult, ParsedElement, RawElementMarker
from .visual_detect import needs_supplemental_ocr

logger = logging.getLogger(__name__)

_VISUAL_MARKER_CATEGORIES = frozenset({"Image", "Figure", "Table"})


def _element_page_number(el) -> int | None:
    metadata = getattr(el, "metadata", None)
    if metadata is None:
        return None
    return getattr(metadata, "page_number", None)


def _pdf_page_count(file_path: str) -> int:
    try:
        from pypdf import PdfReader

        return len(PdfReader(file_path).pages)
    except Exception:
        return 0


def _map_raw_to_marker(el, index: int) -> RawElementMarker | None:
    category = str(getattr(el, "category", None) or type(el).__name__)
    if category not in _VISUAL_MARKER_CATEGORIES:
        return None
    text = (getattr(el, "text", None) or "").strip()
    if text:
        return None
    return RawElementMarker(
        category=category,
        page_number=_element_page_number(el),
        element_index=index,
    )


def _map_raw_to_parsed(el, index: int) -> ParsedElement | None:
    text = (getattr(el, "text", None) or "").strip()
    if not text:
        return None
    category = getattr(el, "category", None) or type(el).__name__
    return ParsedElement(
        text=text,
        category=str(category),
        page_number=_element_page_number(el),
        source_kind="text",
        element_index=index,
    )


def _parse_fast(file_path: str) -> FastParseResult:
    path = Path(file_path)
    ext = path.suffix.lower()

    if ext == ".pdf":
        from unstructured.partition.pdf import partition_pdf

        raw = partition_pdf(filename=str(path), strategy="fast")
        page_count = _pdf_page_count(file_path)
    else:
        from unstructured.partition.auto import partition

        raw = partition(filename=str(path))
        page_count = 0

    elements: list[ParsedElement] = []
    markers: list[RawElementMarker] = []
    for i, el in enumerate(raw):
        marker = _map_raw_to_marker(el, i)
        if marker:
            markers.append(marker)
        parsed = _map_raw_to_parsed(el, i)
        if parsed:
            elements.append(parsed)

    if page_count == 0 and elements:
        pages = {e.page_number for e in elements if e.page_number}
        page_count = max(pages) if pages else 1

    return FastParseResult(
        elements=elements,
        raw_markers=markers,
        page_count=page_count,
    )


def parse_document_generic(file_path: str) -> list[ParsedElement]:
    fast = _parse_fast(file_path)
    detection = needs_supplemental_ocr(file_path, fast)
    if not detection.needs_ocr:
        if not fast.elements and not fast.raw_markers:
            return []
        return fast.elements

    logger.info(
        "Supplemental OCR for %s (reason=%s, scanned_fallback=%s)",
        file_path,
        detection.reason,
        detection.use_scanned_fallback,
    )

    if detection.use_scanned_fallback:
        scanned = enrich_pdf_scanned_ocr(file_path)
        return scanned if scanned else fast.elements

    ocr_elements = run_supplemental_ocr(
        file_path,
        detect_reason=detection.reason,
        use_scanned_fallback=detection.use_scanned_fallback,
    )
    return merge_parsed_elements(fast.elements, ocr_elements)
