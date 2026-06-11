import sys
from unittest.mock import MagicMock, patch

from services.parsing.ocr_enrichment import enrich_pdf_with_image_ocr


def _mock_unstructured_partition(mock_partition):
    mock_pdf_mod = MagicMock(partition_pdf=mock_partition)
    mock_partition_mod = MagicMock(pdf=mock_pdf_mod)
    mock_unstructured = MagicMock(partition=mock_partition_mod)
    return {
        "unstructured": mock_unstructured,
        "unstructured.partition": mock_partition_mod,
        "unstructured.partition.pdf": mock_pdf_mod,
    }


def test_hi_res_ocr_uses_in_memory_image_payload(tmp_path):
    pdf = tmp_path / "diagram.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    el = MagicMock()
    el.category = "Image"
    el.text = "Flowchart step label"
    el.metadata = MagicMock(page_number=2)

    mock_partition = MagicMock(return_value=[el])

    with patch.dict(sys.modules, _mock_unstructured_partition(mock_partition)):
        result = enrich_pdf_with_image_ocr(str(pdf))

    mock_partition.assert_called_once()
    _, kwargs = mock_partition.call_args
    assert kwargs["extract_image_block_to_payload"] is True
    assert kwargs["strategy"] == "hi_res"
    assert len(result) == 1
    assert result[0].text == "Flowchart step label"
    assert result[0].source_kind == "image_ocr"


def test_hi_res_ocr_cleans_up_figures_dir(tmp_path, monkeypatch):
    pdf = tmp_path / "diagram.pdf"
    pdf.write_bytes(b"%PDF-1.4")

    work_dir = tmp_path / "work"
    work_dir.mkdir()
    figures_dir = work_dir / "figures"
    figures_dir.mkdir()
    (figures_dir / "figure-1-1.jpg").write_bytes(b"fake-image")
    monkeypatch.chdir(work_dir)

    el = MagicMock()
    el.category = "Image"
    el.text = "Diagram text"
    el.metadata = MagicMock(page_number=1)
    mock_partition = MagicMock(return_value=[el])

    with patch.dict(sys.modules, _mock_unstructured_partition(mock_partition)):
        enrich_pdf_with_image_ocr(str(pdf))

    assert not figures_dir.exists()
