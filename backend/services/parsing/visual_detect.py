"""Detect whether a narrative document needs supplemental image OCR."""

from dataclasses import dataclass
from pathlib import Path

from django.conf import settings

from .types import FastParseResult, RawElementMarker

_VISUAL_CATEGORIES = frozenset({"Image", "Figure", "Table"})
_IMAGE_CONTENT_PREFIX = "image/"


@dataclass(frozen=True)
class VisualDetectResult:
    needs_ocr: bool
    reason: str
    image_pages: tuple[int, ...] = ()
    use_scanned_fallback: bool = False


def _pdf_embedded_image_count(file_path: str) -> int:
    try:
        from pypdf import PdfReader
    except ImportError:
        return 0

    reader = PdfReader(file_path)
    count = 0
    for page in reader.pages:
        resources = page.get("/Resources")
        if not resources:
            continue
        xobjects = resources.get("/XObject")
        if not xobjects:
            continue
        try:
            items = xobjects.items()
        except AttributeError:
            items = xobjects.get_object().items()
        for _name, ref in items:
            try:
                obj = ref.get_object() if hasattr(ref, "get_object") else ref
                subtype = obj.get("/Subtype")
                if subtype == "/Image":
                    count += 1
            except Exception:
                continue
    return count


def _docx_embedded_image_count(file_path: str) -> int:
    try:
        from docx import Document
    except ImportError:
        return 0

    doc = Document(file_path)
    count = 0
    for rel in doc.part.rels.values():
        if "image" in (rel.reltype or "").lower():
            count += 1
    return count


def _empty_visual_markers(markers: list[RawElementMarker]) -> bool:
    return any(m.category in _VISUAL_CATEGORIES for m in markers)


def _mean_chars_per_page(fast: FastParseResult) -> float:
    if fast.page_count <= 0:
        total_chars = sum(len(e.text) for e in fast.elements)
        return float(total_chars)
    by_page: dict[int, int] = {}
    for el in fast.elements:
        page = el.page_number or 1
        by_page[page] = by_page.get(page, 0) + len(el.text)
    if not by_page:
        return 0.0
    return sum(by_page.values()) / max(fast.page_count, len(by_page))


def needs_supplemental_ocr(file_path: str, fast: FastParseResult) -> VisualDetectResult:
    if not getattr(settings, "PARSER_IMAGE_OCR_ENABLED", True):
        return VisualDetectResult(needs_ocr=False, reason="disabled")

    ext = Path(file_path).suffix.lower()
    if ext == ".txt":
        return VisualDetectResult(needs_ocr=False, reason="text_file")

    min_images = getattr(settings, "PARSER_MIN_IMAGE_COUNT", 1)
    density_min = getattr(settings, "PARSER_TEXT_DENSITY_MIN", 80)

    image_pages: set[int] = set()
    for m in fast.raw_markers:
        if m.category in _VISUAL_CATEGORIES and m.page_number:
            image_pages.add(m.page_number)

    if ext == ".pdf":
        embedded = _pdf_embedded_image_count(file_path)
        if embedded >= min_images:
            return VisualDetectResult(
                needs_ocr=True,
                reason="pdf_embedded_images",
                image_pages=tuple(sorted(image_pages)),
            )
        if _empty_visual_markers(fast.raw_markers):
            return VisualDetectResult(
                needs_ocr=True,
                reason="empty_visual_elements",
                image_pages=tuple(sorted(image_pages)),
            )
        mean_density = _mean_chars_per_page(fast)
        if fast.page_count > 0 and mean_density < density_min:
            return VisualDetectResult(
                needs_ocr=True,
                reason="low_text_density",
                use_scanned_fallback=True,
            )
        return VisualDetectResult(needs_ocr=False, reason="text_only_pdf")

    if ext in (".docx", ".doc"):
        embedded = _docx_embedded_image_count(file_path)
        if embedded >= min_images:
            return VisualDetectResult(needs_ocr=True, reason="docx_embedded_images")
        if _empty_visual_markers(fast.raw_markers):
            return VisualDetectResult(needs_ocr=True, reason="empty_visual_elements")
        return VisualDetectResult(needs_ocr=False, reason="text_only_docx")

    return VisualDetectResult(needs_ocr=False, reason="unsupported")
