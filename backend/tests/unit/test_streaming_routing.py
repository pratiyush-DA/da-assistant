from unittest.mock import MagicMock, patch
from uuid import uuid4

from django.test import override_settings

from services.graphrag.retrieval_profile import RetrievalProfile
from services.graphrag.retriever import RetrievedChunk
from services.langchain import streaming


def _profile(**kwargs) -> RetrievalProfile:
    defaults = dict(
        domain="general",
        workbook_intent="general",
        is_mixed_client=True,
        has_workbook=True,
        document_affinity={"d1": 0.8},
        workbook_confidence=1.0,
        focus_document_ids=(),
    )
    defaults.update(kwargs)
    return RetrievalProfile(**defaults)


@patch("services.langchain.streaming.hybrid_search")
@patch("services.langchain.streaming.mixed_document_search")
def test_mixed_client_general_uses_mixed_search(mock_mixed, mock_hybrid):
    mock_mixed.return_value = []
    profile = _profile(domain="general")
    streaming._retrieve_chunks(str(uuid4()), "question", profile)
    mock_mixed.assert_called_once()
    mock_hybrid.assert_not_called()


@patch("services.langchain.streaming.hybrid_search")
@patch("services.langchain.streaming.workbook_multi_hop_search")
@override_settings(RAG_WORKBOOK_MIN_SCORE=2.0)
def test_workbook_empty_falls_back_to_narrative_hybrid(mock_wb, mock_hybrid):
    mock_wb.return_value = []
    mock_hybrid.return_value = [MagicMock(spec=RetrievedChunk)]
    profile = _profile(domain="workbook", workbook_confidence=3.0)
    streaming._retrieve_chunks(str(uuid4()), "column datatype for TABLE_A", profile)
    mock_wb.assert_called_once()
    mock_hybrid.assert_called_once()
    assert mock_hybrid.call_args.kwargs.get("chunk_types") == ["row"]


@patch("services.langchain.streaming.fit_chunks_to_token_budget")
@patch("services.langchain.streaming._retrieve_chunks")
def test_narrative_abstain_empty_citations(mock_retrieve, mock_fit):
    mock_retrieve.return_value = []
    mock_fit.return_value = []
    profile = _profile(domain="narrative", allowed_citation_types=frozenset({"row"}))
    with patch(
        "services.langchain.streaming.resolve_retrieval_profile",
        return_value=profile,
    ):
        result = streaming.retrieve_and_fit_context(str(uuid4()), "What is the deadline?")
    assert result.context.startswith("No matching content")
    assert result.citation_chunks == []
