from services.chunking.parent_child import ParentChildChunker, _looks_like_section_header
from services.parsing.types import ParsedElement


def test_looks_like_section_header_patterns():
    assert _looks_like_section_header("Section 4 Objectives")
    assert _looks_like_section_header("3.2 Migration Scope")
    assert not _looks_like_section_header("This is a normal sentence.")


def test_narrative_chunker_captures_structural_section_header():
    chunker = ParentChildChunker(parent_tokens=500, child_tokens=200)
    elements = [
        ParsedElement(text="Section 4 Objectives", category="NarrativeText", page_number=2),
        ParsedElement(
            text="The primary goal is to upgrade the edge pipeline.",
            category="NarrativeText",
            page_number=2,
        ),
    ]
    parents, _children = chunker.chunk_elements(elements)
    assert parents
    assert "Section 4" in parents[0].section_header
