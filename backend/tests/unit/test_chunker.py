from services.chunking import ParentChildChunker
from services.parsing.types import ParsedElement


def test_parent_child_chunker_produces_children():
    elements = [
        ParsedElement(text="Section One", category="Title"),
        ParsedElement(
            text="This is a test sentence. " * 50,
            category="NarrativeText",
            page_number=1,
        ),
    ]
    chunker = ParentChildChunker(parent_tokens=100, child_tokens=30)
    parents, children = chunker.chunk_elements(elements)
    assert len(parents) >= 1
    assert len(children) >= 1
    parent_ids = {p.id for p in parents}
    assert all(c.parent_id in parent_ids for c in children)
