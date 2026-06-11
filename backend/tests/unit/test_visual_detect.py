from unittest.mock import patch

from django.test import override_settings

from services.parsing.types import FastParseResult, ParsedElement, RawElementMarker
from services.parsing.visual_detect import needs_supplemental_ocr


def _fast_text_only():
    return FastParseResult(
        elements=[
            ParsedElement(text="Hello world " * 20, category="NarrativeText", page_number=1),
        ],
        raw_markers=[],
        page_count=1,
    )


@override_settings(PARSER_IMAGE_OCR_ENABLED=True, PARSER_MIN_IMAGE_COUNT=1)
def test_txt_never_needs_ocr(tmp_path):
    f = tmp_path / "note.txt"
    f.write_text("plain text", encoding="utf-8")
    result = needs_supplemental_ocr(str(f), _fast_text_only())
    assert result.needs_ocr is False
    assert result.reason == "text_file"


@override_settings(PARSER_IMAGE_OCR_ENABLED=False)
def test_disabled_skips_ocr(tmp_path):
    f = tmp_path / "doc.pdf"
    f.write_bytes(b"%PDF-1.4")
    result = needs_supplemental_ocr(str(f), _fast_text_only())
    assert result.needs_ocr is False
    assert result.reason == "disabled"


@override_settings(PARSER_IMAGE_OCR_ENABLED=True, PARSER_MIN_IMAGE_COUNT=1)
@patch("services.parsing.visual_detect._pdf_embedded_image_count", return_value=2)
def test_pdf_with_embedded_images(_mock_count, tmp_path):
    f = tmp_path / "diagram.pdf"
    f.write_bytes(b"%PDF-1.4")
    result = needs_supplemental_ocr(str(f), _fast_text_only())
    assert result.needs_ocr is True
    assert result.reason == "pdf_embedded_images"


@override_settings(
    PARSER_IMAGE_OCR_ENABLED=True,
    PARSER_TEXT_DENSITY_MIN=80,
    PARSER_MIN_IMAGE_COUNT=99,
)
@patch("services.parsing.visual_detect._pdf_embedded_image_count", return_value=0)
def test_pdf_low_text_density_scanned_fallback(_mock_count, tmp_path):
    f = tmp_path / "scan.pdf"
    f.write_bytes(b"%PDF-1.4")
    fast = FastParseResult(elements=[], raw_markers=[], page_count=5)
    result = needs_supplemental_ocr(str(f), fast)
    assert result.needs_ocr is True
    assert result.use_scanned_fallback is True


@override_settings(PARSER_IMAGE_OCR_ENABLED=True)
def test_empty_visual_markers_trigger_ocr(tmp_path):
    f = tmp_path / "mixed.pdf"
    f.write_bytes(b"%PDF-1.4")
    fast = FastParseResult(
        elements=[ParsedElement(text="Some text", category="NarrativeText", page_number=1)],
        raw_markers=[RawElementMarker(category="Image", page_number=2)],
        page_count=2,
    )
    with patch("services.parsing.visual_detect._pdf_embedded_image_count", return_value=0):
        result = needs_supplemental_ocr(str(f), fast)
    assert result.needs_ocr is True
    assert result.reason == "empty_visual_elements"
