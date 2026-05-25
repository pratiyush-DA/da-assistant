from unittest.mock import MagicMock, patch

from apps.documents import tasks


@patch("apps.documents.tasks.WorkbookDictionaryChunker")
@patch("apps.documents.tasks.is_workbook_dictionary")
@patch("apps.documents.tasks.is_spreadsheet_type", return_value=False)
@patch("apps.documents.tasks.parse_document")
@patch("apps.documents.tasks.get_storage_backend")
@patch("apps.documents.tasks.DocumentRepository")
def test_pdf_uses_parent_child_not_workbook(
    mock_doc_repo,
    mock_storage,
    mock_parse,
    mock_is_sheet,
    mock_is_wb,
    mock_wb_chunker,
):
    document = {
        "client_id": "c1",
        "file_path": "docs/a.pdf",
        "filename": "a.pdf",
        "file_type": "pdf",
    }
    mock_doc_repo.return_value.get.return_value = document
    mock_storage.return_value.open.return_value.__enter__ = MagicMock(
        return_value=MagicMock(read=lambda: b"pdf")
    )
    mock_storage.return_value.open.return_value.__exit__ = MagicMock(return_value=False)

    elements = [MagicMock(category="NarrativeText", text="Section 1")]
    mock_parse.return_value = elements

    parent = MagicMock(id="p1", text="t", chunk_index=0)
    child = MagicMock(id="c1", text="row text", parent_id="p1", child_index=0)
    child.chunk_type = "row"
    parent.chunk_type = "row"

    with patch.object(tasks.ParentChildChunker, "chunk_elements", return_value=([parent], [child])) as mock_pc:
        with patch("apps.documents.tasks.IngestionRepository") as mock_ingest_cls:
            with patch("apps.documents.tasks.embed_texts", return_value=[[0.1]]):
                mock_ingest_cls.return_value.clear_document_chunks = MagicMock()
                mock_ingest_cls.return_value.store_chunks = MagicMock()
                tasks.ingest_document.run("doc-1")

    mock_is_wb.assert_not_called()
    mock_wb_chunker.assert_not_called()
    mock_pc.assert_called_once_with(elements)
    assert child.chunk_type == "row"
