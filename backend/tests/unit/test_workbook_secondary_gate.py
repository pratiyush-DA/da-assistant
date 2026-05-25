from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.graphrag.multi_hop import workbook_multi_hop_search
from services.graphrag.retriever import RetrievedChunk


def _chunk(chunk_type: str, text: str = "x", **kwargs) -> RetrievedChunk:
    return RetrievedChunk(
        id=kwargs.get("id", "1"),
        chunk_text=text,
        child_text=text,
        section_header="",
        page_number=None,
        document_id="d1",
        source="data_dictionary.xlsx",
        score=1.0,
        chunk_type=chunk_type,
        table_name=kwargs.get("table_name"),
        column_name=kwargs.get("column_name"),
        sheet_name=kwargs.get("sheet_name", "Tables"),
    )


@patch("services.graphrag.multi_hop.pin_anchor_chunks", side_effect=lambda ranked, anchors, limit: ranked)
@patch("services.graphrag.multi_hop.rerank_chunks", side_effect=lambda q, chunks: chunks)
@patch("services.graphrag.multi_hop.fetch_anchor_chunks")
@patch("services.graphrag.multi_hop.hybrid_search")
def test_table_intent_skips_column_secondary(mock_hybrid, mock_anchors, *_mocks):
    mock_anchors.return_value = [
        _chunk(
            "table_definition",
            "Table: DimTable | Definition: dimension metadata",
            table_name="DimTable",
        )
    ]

    def hybrid_side_effect(client_id, q, **kwargs):
        types = kwargs.get("chunk_types") or []
        if types == ["column"]:
            return [_chunk("column", "wrong", table_name="SectionIVA")] * 5
        if "table_definition" in types:
            return mock_anchors.return_value
        return []

    mock_hybrid.side_effect = hybrid_side_effect

    chunks = workbook_multi_hop_search(
        uuid4(), "What is the purpose of the DimTable table?", limit=12
    )

    column_calls = [
        c
        for c in mock_hybrid.call_args_list
        if c.kwargs.get("chunk_types") == ["column"]
        or c.kwargs.get("chunk_types") == ["column", "code_set"]
    ]
    assert len(column_calls) == 0
    assert any(c.chunk_type == "table_definition" for c in chunks)


@patch("services.graphrag.multi_hop.pin_anchor_chunks", side_effect=lambda ranked, anchors, limit: ranked)
@patch("services.graphrag.multi_hop.rerank_chunks", side_effect=lambda q, chunks: chunks)
@patch("services.graphrag.multi_hop.fetch_anchor_chunks")
@patch("services.graphrag.multi_hop.hybrid_search")
def test_database_intent_skips_column_secondary(mock_hybrid, mock_anchors, *_mocks):
    mock_anchors.return_value = [
        _chunk(
            "database",
            "Database: MainDB | Description: primary metadata store",
            sheet_name="Database",
        )
    ]
    mock_hybrid.return_value = mock_anchors.return_value

    workbook_multi_hop_search(
        uuid4(), "What does the database represent?", limit=12
    )

    column_calls = [
        c
        for c in mock_hybrid.call_args_list
        if c.kwargs.get("chunk_types") == ["column", "code_set"]
    ]
    assert len(column_calls) == 0
