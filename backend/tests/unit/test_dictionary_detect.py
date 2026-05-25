import json

from services.parsing.dictionary_detect import detect_document_kind
from services.parsing.types import ParsedElement


def _row(sheet: str, row_index: int, payload: dict) -> ParsedElement:
    return ParsedElement(
        text=json.dumps({"sheet": sheet, "row": row_index, **payload}),
        category="TableRow",
        sheet_name=sheet,
        row_index=row_index,
    )


def test_detect_data_dictionary():
    elements = [
        ParsedElement(text="# Sheet: Fields", category="SheetTitle", sheet_name="Fields"),
        _row(
            "Fields",
            2,
            {
                "Table Name": "SectionI-1",
                "Column Name": "FullNameofPointofContact",
                "Definition": "Full name of POC",
            },
        ),
    ]
    assert detect_document_kind(elements) == "data_dictionary"


def test_detect_generic_table():
    elements = [
        _row("Data", 2, {"ID": "1", "Amount": "100", "Date": "2024-01-01"}),
    ]
    assert detect_document_kind(elements) == "generic_table"
