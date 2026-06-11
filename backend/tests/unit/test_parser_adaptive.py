from unittest.mock import MagicMock, patch

from django.test import override_settings

from services.parsing.parser import parse_document_generic
from services.parsing.types import FastParseResult, ParsedElement


def _fake_fast():
    return FastParseResult(
        elements=[ParsedElement(text="Body text here.", category="NarrativeText", page_number=1)],
        raw_markers=[],
        page_count=1,
    )


@override_settings(PARSER_IMAGE_OCR_ENABLED=True)
@patch("services.parsing.parser.merge_parsed_elements")
@patch("services.parsing.parser.run_supplemental_ocr")
@patch("services.parsing.parser.needs_supplemental_ocr")
@patch("services.parsing.parser._parse_fast")
def test_text_only_skips_ocr(mock_fast, mock_detect, mock_ocr, mock_merge, tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    mock_fast.return_value = _fake_fast()
    mock_detect.return_value = MagicMock(needs_ocr=False)

    result = parse_document_generic(str(f))

    mock_ocr.assert_not_called()
    mock_merge.assert_not_called()
    assert len(result) == 1
    assert result[0].text == "Body text here."


@override_settings(PARSER_IMAGE_OCR_ENABLED=True)
@patch("services.parsing.parser.merge_parsed_elements")
@patch("services.parsing.parser.run_supplemental_ocr")
@patch("services.parsing.parser.needs_supplemental_ocr")
@patch("services.parsing.parser._parse_fast")
def test_image_doc_triggers_supplemental_ocr(
    mock_fast, mock_detect, mock_ocr, mock_merge, tmp_path
):
    f = tmp_path / "diagram.pdf"
    f.write_bytes(b"%PDF-1.4")
    mock_fast.return_value = _fake_fast()
    mock_detect.return_value = MagicMock(
        needs_ocr=True,
        reason="pdf_embedded_images",
        use_scanned_fallback=False,
    )
    ocr_el = ParsedElement(
        text="Diagram label text",
        category="ImageOCR",
        page_number=2,
        source_kind="image_ocr",
    )
    mock_ocr.return_value = [ocr_el]
    mock_merge.return_value = _fake_fast().elements + [ocr_el]

    result = parse_document_generic(str(f))

    mock_ocr.assert_called_once()
    mock_merge.assert_called_once()
    assert any(e.source_kind == "image_ocr" for e in result)


@override_settings(PARSER_IMAGE_OCR_ENABLED=True)
@patch("services.parsing.parser.enrich_pdf_scanned_ocr")
@patch("services.parsing.parser.needs_supplemental_ocr")
@patch("services.parsing.parser._parse_fast")
def test_scanned_fallback_replaces_fast(mock_fast, mock_detect, mock_scanned, tmp_path):
    f = tmp_path / "scan.pdf"
    f.write_bytes(b"%PDF-1.4")
    mock_fast.return_value = FastParseResult(elements=[], raw_markers=[], page_count=3)
    mock_detect.return_value = MagicMock(
        needs_ocr=True,
        reason="low_text_density",
        use_scanned_fallback=True,
    )
    mock_scanned.return_value = [
        ParsedElement(text="Scanned page text", category="NarrativeText", page_number=1),
    ]

    result = parse_document_generic(str(f))

    mock_scanned.assert_called_once()
    assert result[0].text == "Scanned page text"
