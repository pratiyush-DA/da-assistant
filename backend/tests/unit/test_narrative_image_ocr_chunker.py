from services.chunking.parent_child import ParentChildChunker
from services.parsing.types import ParsedElement


def test_image_ocr_gets_figure_section_header():
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=200)
    elements = [
        ParsedElement(
            text="Step one connects to step two in the workflow.",
            category="ImageOCR",
            page_number=4,
            source_kind="image_ocr",
        ),
    ]
    parents, children = chunker.chunk_elements(elements)
    assert parents
    assert "Figure (page 4)" in parents[0].section_header
