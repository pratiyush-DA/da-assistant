from unittest.mock import patch
from uuid import uuid4

from services.graphrag.retriever import RetrievedChunk
from services.langchain import streaming


def _catalog_chunk() -> RetrievedChunk:
    text = "Table catalog | Tables (3): Alpha, Beta, Gamma"
    return RetrievedChunk(
        id="cat-1",
        chunk_text=text,
        child_text=text,
        section_header="",
        page_number=None,
        document_id="d1",
        source="dict.xlsx",
        score=1.0,
        chunk_type="table_catalog",
    )


def _db_chunk() -> RetrievedChunk:
    return RetrievedChunk(
        id="1",
        chunk_text="Database: Main",
        child_text="Database: Main",
        section_header="",
        page_number=None,
        document_id="d1",
        source="dict.xlsx",
        score=1.0,
        chunk_type="database",
    )


@patch("services.langchain.streaming.fetch_catalog_chunk")
@patch("services.langchain.streaming._retrieve_chunks")
def test_catalog_abstain_when_no_parseable_catalog(mock_retrieve, mock_fetch):
    mock_retrieve.return_value = [_db_chunk()]
    mock_fetch.return_value = None
    context, _, _, _ = streaming.retrieve_and_fit_context(
        str(uuid4()), "List 5 tables in the dataset"
    )
    assert "cannot list tables" in context.lower()


@patch("services.langchain.streaming.fetch_catalog_chunk")
@patch("services.langchain.streaming._retrieve_chunks")
def test_catalog_no_abstain_when_metadata_catalog_exists(mock_retrieve, mock_fetch):
    mock_retrieve.return_value = [_db_chunk()]
    mock_fetch.return_value = _catalog_chunk()
    context, fitted, _, _ = streaming.retrieve_and_fit_context(
        str(uuid4()), "List 5 tables in the dataset"
    )
    assert "cannot list tables" not in context.lower()
    assert "Allowed table names" in context
    assert any(c.chunk_type == "table_catalog" for c in fitted)
