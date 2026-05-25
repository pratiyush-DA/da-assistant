from unittest.mock import patch
from uuid import uuid4

from services.graphrag.retrieval_profile import RetrievalProfile
from services.graphrag.retriever import RetrievedChunk
from services.langchain import streaming


def _row_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="r1",
        chunk_text="Pratiyush is a data engineer at Data Axle",
        child_text="Pratiyush is a data engineer at Data Axle",
        section_header="",
        page_number=None,
        document_id="d1",
        source="test_text1.txt",
        score=1.0,
        chunk_type="row",
    )


def _catalog_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="cat",
        chunk_text="catalog",
        child_text="catalog",
        section_header="Catalog (FOIA Tables)",
        page_number=None,
        document_id="d2",
        source="dict.xlsx",
        score=0.5,
        chunk_type="table_catalog",
    )


@patch("services.langchain.streaming.fit_chunks_to_token_budget")
@patch("services.langchain.streaming._retrieve_chunks")
def test_narrative_fit_excludes_catalog_from_citations(mock_retrieve, mock_fit):
    mock_retrieve.return_value = [_row_chunk(), _catalog_chunk()]
    mock_fit.return_value = [_row_chunk(), _catalog_chunk()]

    profile = RetrievalProfile(
        domain="narrative",
        workbook_intent="general",
        is_mixed_client=True,
        has_workbook=True,
        allowed_citation_types=frozenset({"row"}),
        inject_catalog=False,
    )

    with patch(
        "services.langchain.streaming.resolve_retrieval_profile",
        return_value=profile,
    ):
        result = streaming.retrieve_and_fit_context(
            str(uuid4()), "who is data engineer and where does he work?"
        )

    assert all(c.chunk_type == "row" for c in result.citation_chunks)
    assert not any(c.chunk_type == "table_catalog" for c in result.citation_chunks)
