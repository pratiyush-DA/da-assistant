from unittest.mock import patch
from uuid import uuid4

from services.graphrag.retrieval_profile import RetrievalProfile
from services.graphrag.retriever import RetrievedChunk
from services.langchain import streaming


def _row_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="r1",
        chunk_text="Five key requirements include incremental load and validation rules.",
        child_text="Five key requirements include incremental load and validation rules.",
        section_header="Section 2",
        page_number=3,
        document_id="d1",
        source="upgrade_plan.pdf",
        score=1.0,
        chunk_type="row",
    )


@patch("services.langchain.streaming.fit_chunks_to_token_budget")
@patch("services.langchain.streaming._retrieve_chunks")
def test_narrative_list_question_does_not_catalog_abstain(mock_retrieve, mock_fit):
    mock_retrieve.return_value = [_row_chunk()]
    mock_fit.return_value = [_row_chunk()]

    profile = RetrievalProfile(
        domain="mixed",
        workbook_intent="general",
        is_mixed_client=True,
        has_workbook=True,
        allowed_citation_types=frozenset({"row", "column"}),
        inject_catalog=False,
    )

    with patch(
        "services.langchain.streaming.resolve_retrieval_profile",
        return_value=profile,
    ):
        result = streaming.retrieve_and_fit_context(
            str(uuid4()),
            "List the five key client requirements defined in the change request",
        )

    assert "cannot list tables" not in result.context.lower()
    assert len(result.citation_chunks) > 0


@patch("services.langchain.streaming.fit_chunks_to_token_budget")
@patch("services.langchain.streaming._retrieve_chunks")
def test_catalog_intent_with_pdf_rows_skips_abstain(mock_retrieve, mock_fit):
    mock_retrieve.return_value = [_row_chunk()]
    mock_fit.return_value = [_row_chunk()]

    profile = RetrievalProfile(
        domain="mixed",
        workbook_intent="catalog",
        is_mixed_client=True,
        has_workbook=True,
        inject_catalog=True,
    )

    with patch(
        "services.langchain.streaming.resolve_retrieval_profile",
        return_value=profile,
    ):
        result = streaming.retrieve_and_fit_context(
            str(uuid4()), "How many new fields are in the promotional history tables?"
        )

    assert "cannot list tables" not in result.context.lower()
