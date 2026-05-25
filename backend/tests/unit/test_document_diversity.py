from services.graphrag.multi_hop import apply_document_diversity
from services.graphrag.retriever import RetrievedChunk


def _c(doc_id: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=f"id-{doc_id}-{score}",
        chunk_text="t",
        section_header="",
        page_number=None,
        document_id=doc_id,
        source=doc_id,
        score=score,
        chunk_type="row",
    )


def test_diversity_includes_multiple_documents():
    chunks = [_c("excel", 1.0)] * 10 + [_c("docx", 0.8)] * 3
    result = apply_document_diversity(chunks, limit=6, min_documents=2)
    doc_ids = {c.document_id for c in result}
    assert len(doc_ids) >= 2
