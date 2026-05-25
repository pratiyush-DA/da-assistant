import json

from services.chunking.workbook_chunker import WorkbookDictionaryChunker
from services.parsing.types import ParsedElement


def _row(sheet: str, payload: dict) -> ParsedElement:
    return ParsedElement(
        text=json.dumps({"sheet": sheet, "row": 1, **payload}),
        category="TableRow",
        sheet_name=sheet,
    )


def test_dedupe_keeps_row_with_datatype():
    elements = [
        _row(
            "Fields",
            {
                "Table Name": "OtherDetails",
                "Column Name": "ReportTitle",
                "ColumnDefinition": "weak",
                "Col_Datatype": "",
            },
        ),
        _row(
            "Fields",
            {
                "Table Name": "SectionI-1",
                "Column Name": "ReportTitle",
                "ColumnDefinition": "The heading for the report.",
                "Col_Datatype": "VARCHAR(100)",
            },
        ),
    ]
    _, children = WorkbookDictionaryChunker().chunk(elements)
    report = [
        c
        for c in children
        if c.chunk_type == "column" and c.column_name == "ReportTitle"
    ]
    assert len(report) == 1
    assert report[0].table_name == "SectionI-1"
    assert "VARCHAR(100)" in report[0].text
