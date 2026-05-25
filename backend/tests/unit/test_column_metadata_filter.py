from unittest.mock import patch
from uuid import uuid4

from services.graphrag.multi_hop import workbook_multi_hop_search


@patch("services.graphrag.multi_hop.pin_anchor_chunks", side_effect=lambda r, a, l: a + r)
@patch("services.graphrag.multi_hop.rerank_chunks", side_effect=lambda q, c: c)
@patch("services.graphrag.multi_hop.fetch_anchor_chunks", return_value=[])
@patch("services.graphrag.multi_hop.hybrid_search")
def test_column_intent_passes_column_names(mock_hybrid, *_):
    mock_hybrid.return_value = []
    workbook_multi_hop_search(
        uuid4(), "What is the datatype of OrderId?", limit=12
    )
    column_calls = [
        c for c in mock_hybrid.call_args_list if c.kwargs.get("column_names")
    ]
    assert column_calls
    assert "OrderId" in column_calls[0].kwargs["column_names"]
