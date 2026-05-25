"""Generic document parsing via unstructured (PDF, DOCX, etc.)."""

from pathlib import Path

from .types import ParsedElement


def parse_document_generic(file_path: str) -> list[ParsedElement]:
    from unstructured.partition.auto import partition

    path = Path(file_path)
    elements = partition(filename=str(path))

    parsed: list[ParsedElement] = []
    for el in elements:
        text = (getattr(el, "text", None) or "").strip()
        if not text:
            continue
        category = getattr(el, "category", None) or type(el).__name__
        metadata = getattr(el, "metadata", None)
        page_number = None
        if metadata is not None:
            page_number = getattr(metadata, "page_number", None)
        parsed.append(
            ParsedElement(
                text=text,
                category=str(category),
                page_number=page_number,
            )
        )
    return parsed
