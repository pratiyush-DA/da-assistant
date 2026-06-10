from unittest.mock import patch
from uuid import uuid4

from services.graphrag.retrieval_profile import RetrievalProfile
from services.graphrag.retriever import RetrievedChunk
from services.langchain import streaming


def _chunk(chunk_type: str, doc_id: str, source: str, text: str) -> RetrievedChunk:
    return RetrievedChunk(
        id="c1",
        chunk_text=text,
        child_text=text,
        section_header="Phase 1",
        page_number=1,
        document_id=doc_id,
        source=source,
        score=0.9,
        chunk_type=chunk_type,
    )


def _profile(domain: str, wb_intent: str = "general") -> RetrievalProfile:
    if domain == "narrative":
        return RetrievalProfile(
            domain="narrative",
            workbook_intent=wb_intent,
            is_mixed_client=True,
            has_workbook=True,
            allowed_citation_types=frozenset({"row"}),
            narrative_limit_ratio=1.0,
            workbook_limit_ratio=0.0,
        )
    if domain == "mixed":
        return RetrievalProfile(
            domain="mixed",
            workbook_intent=wb_intent,
            is_mixed_client=True,
            has_workbook=True,
            allowed_citation_types=frozenset({"row", "column"}),
            narrative_limit_ratio=0.75,
            workbook_limit_ratio=0.25,
        )
    return RetrievalProfile(
        domain="workbook",
        workbook_intent=wb_intent,
        is_mixed_client=False,
        has_workbook=True,
        allowed_citation_types=frozenset({"database"}),
        workbook_confidence=3.0,
    )


@patch("services.langchain.streaming.hybrid_search")
def test_mixed_client_narrative_query_uses_row_chunks(mock_hybrid):
    mock_hybrid.return_value = [
        _chunk("row", "doc-arch", "Architecture_Plan.docx", "Phase 1 scope text"),
    ]
    profile = _profile("narrative")
    chunks = streaming._retrieve_chunks(
        str(uuid4()), "what is the phase 1 of the project", profile
    )
    mock_hybrid.assert_called_once()
    assert mock_hybrid.call_args.kwargs.get("chunk_types") == ["row"]
    assert any(c.chunk_type == "row" for c in chunks)


@patch("services.langchain.streaming.mixed_document_search")
def test_mixed_client_general_uses_dual_path(mock_mixed):
    mock_mixed.return_value = [
        _chunk("row", "doc-arch", "Architecture_Plan.docx", "Phase 1"),
        _chunk("column", "doc-xls", "data_dictionary.xlsx", "OrderId"),
    ]
    profile = _profile("mixed")
    chunks = streaming._retrieve_chunks(str(uuid4()), "tell me about the system", profile)
    mock_mixed.assert_called_once()
    assert mock_mixed.call_args.kwargs.get("profile") == profile
    assert len(chunks) == 2


@patch("services.langchain.streaming.workbook_multi_hop_search")
def test_workbook_only_client_unchanged(mock_wb):
    mock_wb.return_value = [
        _chunk("column", "doc-xls", "data_dictionary.xlsx", "Column def"),
    ]
    profile = _profile("workbook", wb_intent="database")
    chunks = streaming._retrieve_chunks(
        str(uuid4()), "What does the database represent?", profile
    )
    mock_wb.assert_called_once()
    assert chunks[0].chunk_type == "column"
