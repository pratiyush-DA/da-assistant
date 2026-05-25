from django.test import override_settings

from services.graphrag.retriever import RetrievedChunk
from services.langchain.prompts import SYSTEM_PROMPT
from services.llm.token_budget import count_tokens, fit_chunks_to_token_budget


def _chunk(text: str, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        id="c1",
        chunk_text=text,
        section_header="Sec",
        page_number=1,
        document_id="d1",
        source="doc.pdf",
        score=score,
    )


@override_settings(
    LLM_MAX_REQUEST_TOKENS=600,
    LLM_MAX_COMPLETION_TOKENS=100,
    PARENT_CHUNK_TOKENS=2000,
)
def test_fit_chunks_drops_and_truncates_under_budget():
    big = "word " * 500
    chunks = [_chunk(big, 1.0), _chunk(big, 0.5), _chunk(big, 0.1)]
    fitted = fit_chunks_to_token_budget(chunks, "What is X?", SYSTEM_PROMPT)
    assert len(fitted) < len(chunks)
    context = "\n\n---\n\n".join(c.chunk_text for c in fitted)
    user_content = f"Context:\n{context}\n\nQuestion: What is X?"
    est = count_tokens(SYSTEM_PROMPT) + count_tokens(user_content) + 8 + 100
    assert est <= 600 + 64
