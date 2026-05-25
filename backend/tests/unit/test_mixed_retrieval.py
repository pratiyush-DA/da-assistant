from unittest.mock import patch
from uuid import uuid4

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


@patch("services.langchain.streaming.client_is_mixed", return_value=True)
@patch("services.langchain.streaming.classify_query_domain", return_value="narrative")
@patch("services.langchain.streaming.hybrid_search")
def test_mixed_client_narrative_query_uses_row_chunks(mock_hybrid, _domain, _mixed):
    mock_hybrid.return_value = [
        _chunk("row", "doc-arch", "Architecture_Plan.docx", "Phase 1 scope text"),
    ]
    chunks = streaming._retrieve_chunks(str(uuid4()), "what is the phase 1 of the project")
    mock_hybrid.assert_called_once()
    assert mock_hybrid.call_args.kwargs.get("chunk_types") == ["row"]
    assert any(c.chunk_type == "row" for c in chunks)


@patch("services.langchain.streaming.client_is_mixed", return_value=True)
@patch("services.langchain.streaming.classify_query_domain", return_value="general")
@patch("services.langchain.streaming.mixed_document_search")
def test_mixed_client_general_uses_dual_path(mock_mixed, _domain, _is_mixed):
    mock_mixed.return_value = [
        _chunk("row", "doc-arch", "Architecture_Plan.docx", "Phase 1"),
        _chunk("column", "doc-xls", "data_dictionary.xlsx", "OrderId"),
    ]
    chunks = streaming._retrieve_chunks(str(uuid4()), "tell me about the system")
    mock_mixed.assert_called_once()
    assert len(chunks) == 2


@patch("services.langchain.streaming.client_is_mixed", return_value=False)
@patch("services.langchain.streaming.client_has_workbook_chunks", return_value=True)
@patch("services.langchain.streaming.multi_hop_search")
@patch("services.langchain.streaming.settings")
def test_workbook_only_client_unchanged(mock_settings, mock_mh, _wb, _mixed):
    mock_settings.MULTI_HOP_ENABLED = True
    mock_mh.return_value = [
        _chunk("column", "doc-xls", "data_dictionary.xlsx", "Column def"),
    ]
    chunks = streaming._retrieve_chunks(
        str(uuid4()), "What does the database represent?"
    )
    mock_mh.assert_called_once()
    assert chunks[0].chunk_type == "column"
