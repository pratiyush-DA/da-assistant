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


@patch("services.graphrag.multi_hop.lookup_column_chunks")
@patch("services.graphrag.multi_hop.hybrid_search")
def test_column_intent_pins_table_scoped_anchor(mock_search, mock_lookup):
    from services.graphrag.multi_hop import workbook_multi_hop_search

    section_i1 = _chunk(
        "Table: SectionI-1 | Column: FullNameofPointofContact | "
        "Definition: The complete name of the individual who handles report distribution.",
        "column",
        sheet_name="FOIA Fields",
        table_name="SectionI-1",
        column_name="FullNameofPointofContact",
    )
    mock_lookup.return_value = [section_i1]
    mock_search.return_value = []

    query = (
        "On the FOIA Fields sheet, for table SectionI-1, what is the "
        "ColumnDefinition for the column FullNameofPointofContact?"
    )
    chunks = workbook_multi_hop_search(uuid4(), query, limit=5)
    assert chunks
    assert chunks[0].table_name == "SectionI-1"
    mock_lookup.assert_called_once()
    call_kw = mock_lookup.call_args.kwargs
    assert call_kw.get("table_name") == "SectionI-1"


@patch("services.graphrag.multi_hop.lookup_table_by_definition")
@patch("services.graphrag.multi_hop.hybrid_search")
def test_table_by_definition_intent_uses_metadata(mock_search, mock_lookup):
    from services.graphrag.multi_hop import workbook_multi_hop_search

    agency = _chunk(
        "Table: Agency | Definition: Organization responsible for issuing "
        "the FOIA annual report | Sheet: FOIA Tables",
        "table_definition",
        sheet_name="FOIA Tables",
        table_name="Agency",
    )
    mock_lookup.return_value = [agency]
    mock_search.return_value = []

    query = (
        'which table name has the following table definition '
        '"Organization responsible for issuing the FOIA annual report"'
    )
    chunks = workbook_multi_hop_search(uuid4(), query, limit=5)
    assert chunks
    assert chunks[0].table_name == "Agency"
