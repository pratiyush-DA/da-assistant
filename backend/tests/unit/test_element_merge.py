from services.parsing.element_merge import merge_parsed_elements
from services.parsing.types import ParsedElement


def test_merge_keeps_fast_and_adds_non_duplicate_ocr():
    fast = [
        ParsedElement(text="Objective of the change request.", category="NarrativeText", page_number=1),
    ]
    ocr = [
        ParsedElement(
            text="Flowchart step A to step B",
            category="ImageOCR",
            page_number=3,
            source_kind="image_ocr",
        ),
    ]
    merged = merge_parsed_elements(fast, ocr)
    assert len(merged) == 2
    assert merged[1].text.startswith("[Figure text, page 3]")


def test_merge_dedupes_overlapping_ocr():
    fast = [
        ParsedElement(
            text="The primary objective is upgrade monetary detail columns.",
            category="NarrativeText",
            page_number=2,
        ),
    ]
    ocr = [
        ParsedElement(
            text="primary objective upgrade monetary detail",
            category="ImageOCR",
            page_number=2,
            source_kind="image_ocr",
        ),
    ]
    merged = merge_parsed_elements(fast, ocr)
    assert len(merged) == 1
