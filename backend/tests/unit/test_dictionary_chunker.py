import json

from services.chunking.dictionary_chunker import DictionaryChunker
from services.parsing.types import ParsedElement


def _row(sheet: str, row_index: int, payload: dict) -> ParsedElement:
    return ParsedElement(
        text=json.dumps({"sheet": sheet, "row": row_index, **payload}),
        category="TableRow",
        sheet_name=sheet,
        row_index=row_index,
    )


def test_dictionary_chunker_table_and_column():
    elements = [
        ParsedElement(text="# Sheet: FOIA Fields", category="SheetTitle", sheet_name="FOIA Fields"),
        _row(
            "FOIA Fields",
            2,
            {
                "Table Name": "SectionI-1",
                "Column Name": "FullNameofPointofContact",
                "ColumnDefinition": "Full name of the point of contact",
            },
        ),
        _row(
            "FOIA Fields",
            3,
            {
                "Table Name": "SectionI-1",
                "Column Name": "TitleOfPointOfContact",
                "ColumnDefinition": "Title of POC",
            },
        ),
    ]
    parents, children = DictionaryChunker().chunk(elements)
    table_parents = [p for p in parents if p.chunk_type == "table"]
    column_children = [c for c in children if c.chunk_type == "column"]
    assert len(table_parents) == 1
    assert table_parents[0].table_name == "SectionI-1"
    assert len(column_children) == 2
    assert any("FullNameofPointofContact" in c.text for c in column_children)
    assert any("FullNameofPointofContact" in c.keywords for c in column_children)


def test_dictionary_chunker_code_set_sheet():
    elements = [
        ParsedElement(text="# Sheet: Code Sets", category="SheetTitle", sheet_name="Code Sets"),
        _row(
            "Code Set",
            2,
            {
                "Code Set (name)": "Region",
                "Permissible Value (list of all possible codes)": "Region 1",
                "Permissible value meaning (list of all possible meanings)": "Northeast",
            },
        ),
    ]
    parents, children = DictionaryChunker().chunk(elements)
    assert any(c.chunk_type == "code_set" for c in children)
    assert any("Region 1" in c.text for c in children)
