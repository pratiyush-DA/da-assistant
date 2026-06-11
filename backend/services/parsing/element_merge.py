"""Merge fast text elements with supplemental OCR elements."""

import re

from .types import ParsedElement

_OVERLAP_THRESHOLD = 0.8
_VISUAL_CATEGORIES = frozenset({"Image", "Figure", "Table", "ImageOCR"})


def _normalize_tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]{3,}", text.lower()))


def _token_overlap_ratio(a: str, b: str) -> float:
    ta = _normalize_tokens(a)
    tb = _normalize_tokens(b)
    if not ta or not tb:
        return 0.0
    intersection = ta & tb
    smaller = min(len(ta), len(tb))
    return len(intersection) / smaller if smaller else 0.0


def _is_duplicate_ocr(ocr_el: ParsedElement, fast_elements: list[ParsedElement]) -> bool:
    page = ocr_el.page_number
    for fast in fast_elements:
        if fast.source_kind != "text":
            continue
        if page is not None and fast.page_number is not None and page != fast.page_number:
            continue
        if _token_overlap_ratio(ocr_el.text, fast.text) >= _OVERLAP_THRESHOLD:
            return True
    return False


def _maybe_prefix_figure_text(el: ParsedElement) -> ParsedElement:
    if el.source_kind != "image_ocr":
        return el
    page = el.page_number
    prefix = f"[Figure text, page {page}] " if page is not None else "[Figure text] "
    if el.text.startswith("["):
        return el
    return ParsedElement(
        text=prefix + el.text,
        category=el.category,
        page_number=el.page_number,
        sheet_name=el.sheet_name,
        row_index=el.row_index,
        source_kind=el.source_kind,
        element_index=el.element_index,
    )


def merge_parsed_elements(
    fast: list[ParsedElement],
    ocr: list[ParsedElement],
) -> list[ParsedElement]:
    """Combine fast and OCR elements, dedupe overlaps, sort by reading order."""
    if not ocr:
        return list(fast)

    kept_ocr: list[ParsedElement] = []
    for el in ocr:
        if not (el.text or "").strip():
            continue
        if _is_duplicate_ocr(el, fast):
            continue
        kept_ocr.append(_maybe_prefix_figure_text(el))

    merged = list(fast) + kept_ocr
    merged.sort(key=lambda e: (e.page_number or 0, e.element_index or 0))
    return merged
