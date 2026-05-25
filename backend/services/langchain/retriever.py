from uuid import UUID

from django.conf import settings
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

from services.graphrag.hybrid_retriever import hybrid_search
from services.graphrag.multi_hop import multi_hop_search
from services.graphrag.retriever import RetrievedChunk, rerank_chunks


def documents_to_retrieved_chunks(docs: list[Document]) -> list[RetrievedChunk]:
    chunks: list[RetrievedChunk] = []
    for doc in docs:
        meta = doc.metadata
        chunks.append(
            RetrievedChunk(
                id=meta.get("id", ""),
                chunk_text=doc.page_content,
                section_header=meta.get("section_header", "") or "",
                page_number=meta.get("page_number"),
                document_id=meta.get("document_id", ""),
                source=meta.get("source", "") or "",
                score=float(meta.get("score", 0.0)),
                chunk_type=meta.get("chunk_type"),
                sheet_name=meta.get("sheet_name"),
                table_name=meta.get("table_name"),
                column_name=meta.get("column_name"),
                child_text=meta.get("child_text"),
            )
        )
    return chunks


def _chunk_to_document(chunk: RetrievedChunk) -> Document:
    return Document(
        page_content=chunk.child_text or chunk.chunk_text,
        metadata={
            "id": chunk.id,
            "section_header": chunk.section_header,
            "page_number": chunk.page_number,
            "document_id": chunk.document_id,
            "source": chunk.source,
            "score": chunk.score,
            "chunk_type": chunk.chunk_type,
            "sheet_name": chunk.sheet_name,
            "table_name": chunk.table_name,
            "column_name": chunk.column_name,
            "child_text": chunk.child_text,
        },
    )


class Neo4jParentChildRetriever(BaseRetriever):
    """Hybrid vector + fulltext search on ChildChunk, returns enriched metadata."""

    client_id: str
    limit: int = 12

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun | None = None,
    ) -> list[Document]:
        if settings.MULTI_HOP_ENABLED:
            chunks = multi_hop_search(self.client_id, query, limit=self.limit)
        else:
            chunks = hybrid_search(self.client_id, query, limit=self.limit)
        reranked = rerank_chunks(query, chunks)
        return [_chunk_to_document(c) for c in reranked]

    @classmethod
    def for_client(cls, client_id: UUID | str, limit: int | None = None) -> "Neo4jParentChildRetriever":
        return cls(
            client_id=str(client_id),
            limit=limit or settings.VECTOR_SEARCH_LIMIT,
        )
