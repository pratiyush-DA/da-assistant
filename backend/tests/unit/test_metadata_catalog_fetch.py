from unittest.mock import MagicMock, patch
from uuid import uuid4

from services.graphrag.metadata_lookup import fetch_catalog_chunk
from services.graphrag.retriever import RetrievedChunk


@patch("services.graphrag.metadata_lookup.get_driver")
def test_fetch_catalog_chunk_returns_parseable(mock_driver):
    mock_session = MagicMock()
    mock_driver.return_value.session.return_value.__enter__.return_value = mock_session
    mock_session.run.return_value.single.return_value = {
        "id": "cat-1",
        "chunk_text": "parent",
        "child_text": "Table catalog | Tables (3): Alpha, Beta, Gamma",
        "section_header": "Catalog",
        "page_number": None,
        "document_id": "doc-1",
        "source": "dict.xlsx",
        "chunk_type": "table_catalog",
        "sheet_name": "Tables",
        "table_name": None,
        "column_name": None,
    }

    chunk = fetch_catalog_chunk(uuid4())
    assert chunk is not None
    assert chunk.chunk_type == "table_catalog"
    assert "Alpha" in (chunk.child_text or "")
