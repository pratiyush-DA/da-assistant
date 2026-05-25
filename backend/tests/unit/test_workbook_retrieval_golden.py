"""Golden substring checks for workbook retrieval (mocked Neo4j hybrid)."""

from unittest.mock import patch
from uuid import uuid4

from services.graphrag.retriever import RetrievedChunk
from services.graphrag.workbook_rag import classify_workbook_query, intent_chunk_types


def _chunk(text: str, chunk_type: str, **kwargs) -> RetrievedChunk:
    return RetrievedChunk(
        id=str(uuid4()),
        chunk_text=text,
        child_text=text,
        section_header=None,
        page_number=None,
        document_id="doc-1",
        source="vector",
        score=1.0,
        chunk_type=chunk_type,
        sheet_name=kwargs.get("sheet_name"),
        table_name=kwargs.get("table_name"),
        column_name=kwargs.get("column_name"),
    )


@patch("services.graphrag.multi_hop.hybrid_search")
def test_workbook_multi_hop_database_intent(mock_search):
    from services.graphrag.multi_hop import workbook_multi_hop_search

    mock_search.return_value = [
        _chunk(
            "Database: MainDB | Description: primary application database",
            "database",
            sheet_name="Database",
        )
    ]
    query = "What does the database represent?"
    assert classify_workbook_query(query) == "database"
    assert "database" in intent_chunk_types("database")

    chunks = workbook_multi_hop_search(uuid4(), query, limit=5)
    assert chunks
    body = chunks[0].child_text or chunks[0].chunk_text
    assert "MainDB" in body or "primary application" in body


@patch("services.graphrag.multi_hop.fetch_catalog_chunk")
@patch("services.graphrag.multi_hop.hybrid_search")
def test_workbook_multi_hop_catalog_intent(mock_search, mock_fetch):
    from services.graphrag.multi_hop import workbook_multi_hop_search

    catalog = _chunk(
        "Table catalog | Tables (42): Customer, Order, SectionI-1",
        "table_catalog",
        sheet_name="Tables",
    )
    mock_fetch.return_value = catalog
    mock_search.return_value = []
    query = "List 5 tables in the dataset"
    assert classify_workbook_query(query) == "catalog"

    chunks = workbook_multi_hop_search(uuid4(), query, limit=5)
    assert any("Customer" in (c.child_text or c.chunk_text) for c in chunks)
