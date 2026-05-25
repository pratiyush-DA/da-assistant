from unittest.mock import patch
from uuid import uuid4

from services.graphrag.multi_hop import catalog_fallback_anchor, fetch_anchor_chunks


@patch("services.graphrag.multi_hop.hybrid_search", return_value=[])
@patch(
    "services.graphrag.multi_hop.get_distinct_table_names",
    return_value=["Customer", "Order"],
)
def test_catalog_fallback_when_no_table_catalog_chunk(_tables, _search):
    anchor = catalog_fallback_anchor(uuid4())
    assert anchor is not None
    assert anchor.chunk_type == "table_catalog"
    assert "Customer" in (anchor.child_text or anchor.chunk_text)
    assert "Order" in (anchor.child_text or anchor.chunk_text)


@patch("services.graphrag.multi_hop.fetch_catalog_chunk", return_value=None)
@patch("services.graphrag.multi_hop.hybrid_search", return_value=[])
@patch(
    "services.graphrag.multi_hop.get_distinct_table_names",
    return_value=["DimTable"],
)
def test_fetch_anchor_catalog_uses_fallback(_tables, _search, _fetch):
    signals = {"sheet_hint": None}
    anchors = fetch_anchor_chunks(
        uuid4(), "list all tables", "catalog", signals, limit=5
    )
    assert len(anchors) == 1
    assert "DimTable" in (anchors[0].child_text or anchors[0].chunk_text)
