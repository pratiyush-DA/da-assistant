from dataclasses import dataclass, field
from uuid import UUID

from django.conf import settings

from services.embedding import embed_query
from services.neo4j.driver import get_driver


@dataclass
class RetrievedChunk:
    id: str
    chunk_text: str
    section_header: str
    page_number: int | None
    document_id: str
    source: str
    score: float
    chunk_type: str | None = None
    sheet_name: str | None = None
    table_name: str | None = None
    column_name: str | None = None
    child_text: str | None = None


def rerank_chunks(query: str, chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    if not settings.RERANK_ENABLED or not chunks:
        return chunks
    try:
        from sentence_transformers import CrossEncoder

        model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
        pairs = [(query, c.child_text or c.chunk_text) for c in chunks]
        scores = model.predict(pairs)
        ranked = sorted(zip(chunks, scores), key=lambda x: x[1], reverse=True)
        return [c for c, _ in ranked]
    except Exception:
        return chunks


def search_similar_chunks(
    client_id: UUID | str,
    query: str,
    limit: int | None = None,
) -> list[RetrievedChunk]:
    """Legacy vector-only search; prefer hybrid_search from hybrid_retriever."""
    from services.graphrag.hybrid_retriever import hybrid_search

    return hybrid_search(client_id, query, limit=limit)
