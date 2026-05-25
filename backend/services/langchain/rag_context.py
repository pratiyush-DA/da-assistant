"""RAG context assembly result types."""

from dataclasses import dataclass

from services.graphrag.retriever import RetrievedChunk


@dataclass
class RAGFitResult:
    context: str
    fitted_chunks: list[RetrievedChunk]
    citation_chunks: list[RetrievedChunk]
    use_dictionary: bool
    use_mixed: bool
