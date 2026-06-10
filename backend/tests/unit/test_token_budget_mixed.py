from django.test import override_settings

from services.graphrag.retriever import RetrievedChunk
from services.langchain.prompts import SYSTEM_PROMPT
from services.llm.token_budget import fit_chunks_to_token_budget


def _chunk(chunk_type: str, text: str, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=f"{chunk_type}-{score}",
        chunk_text=text,
        section_header="",
        page_number=1,
        document_id="d1",
        source="doc.pdf" if chunk_type == "row" else "dict.xlsx",
        score=score,
        chunk_type=chunk_type,
        child_text=text,
    )


@override_settings(
    LLM_MAX_REQUEST_TOKENS=1200,
    LLM_MAX_COMPLETION_TOKENS=100,
    MIXED_NARRATIVE_TOKEN_FLOOR_RATIO=0.4,
    VECTOR_SEARCH_LIMIT=10,
)
def test_mixed_budget_includes_row_chunks_when_workbook_scores_higher():
    row = _chunk("row", "narrative " * 40, 0.5)
    wb = _chunk("column", "workbook " * 200, 2.0)
    fitted = fit_chunks_to_token_budget(
        [wb, row], "question", SYSTEM_PROMPT, budget_mode="mixed"
    )
    types = {c.chunk_type for c in fitted}
    assert "row" in types
