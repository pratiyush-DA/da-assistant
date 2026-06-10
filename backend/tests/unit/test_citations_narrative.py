from services.graphrag.citations import chunk_display_label, select_citation_chunks
from services.graphrag.retrieval_profile import RetrievalProfile
from services.graphrag.retriever import RetrievedChunk


def _row(page: int | None, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=f"p{page}",
        chunk_text="body",
        section_header=f"Section {page}",
        page_number=page,
        document_id="d1",
        source=f"doc1-p{page}.pdf",
        score=score,
        chunk_type="row",
        child_text="body",
    )


def test_narrative_citations_sort_by_page():
    profile = RetrievalProfile(
        domain="narrative",
        workbook_intent="general",
        is_mixed_client=False,
        has_workbook=False,
        allowed_citation_types=frozenset({"row"}),
    )
    fitted = [_row(12, 1.0), _row(3, 0.9), _row(None, 2.0)]
    cites = select_citation_chunks(fitted, profile)
    pages = [c.page_number for c in cites]
    assert pages == [3, 12, None]


def test_row_display_label_includes_section_and_page():
    label = chunk_display_label(_row(4, 1.0))
    assert "doc1-p4.pdf" in label
    assert "Section 4" in label
    assert "page 4" in label
