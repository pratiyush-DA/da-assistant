from services.langchain.embeddings import get_embeddings


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed document texts (ingest). Uses LangChain HuggingFace embeddings."""
    if not texts:
        return []
    return get_embeddings().embed_documents(texts)


def embed_query(text: str) -> list[float]:
    """Embed a search query (BGE query prompt applied)."""
    return get_embeddings().embed_query(text)
