import json
from pathlib import Path

import pytest

from services.chunking.workbook_chunker import WorkbookDictionaryChunker
from services.parsing.excel_parser import parse_excel
from services.parsing.types import ParsedElement

FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "tests"
    / "fixtures"
    / "data_dictionary_2009_1_xlsx.xlsx"
)
REPO_FIXTURE = (
    Path(__file__).resolve().parents[3]
    / "testing_data"
    / "data_dictionary_2009_1_xlsx.xlsx"
)


def _row(sheet: str, row_index: int, payload: dict) -> ParsedElement:
    return ParsedElement(
        text=json.dumps({"sheet": sheet, "row": row_index, **payload}),
        category="TableRow",
        sheet_name=sheet,
    )


def test_field_chunk_includes_definition_and_datatype():
    elements = [
        _row(
            "Fields",
            2,
            {
                "Table Name": "SectionI-1",
                "Column Name": "OrderId",
                "ColumnDefinition": "The primary key for the order.",
                "Col_Datatype": "VARCHAR(100)",
                "ColumnEnglishName": "Order Id",
            },
        ),
    ]
    _, children = WorkbookDictionaryChunker().chunk(elements)
    col = [c for c in children if c.chunk_type == "column"]
    assert len(col) == 1
    assert "The primary key for the order." in col[0].text
    assert "VARCHAR(100)" in col[0].text
    assert "OrderId" in col[0].text


def test_table_definition_and_catalog():
    elements = [
        _row(
            "Tables",
            2,
            {
                "Table Name": "Customer",
                "TableDefinition": "Customer contact information",
            },
        ),
        _row(
            "Tables",
            3,
            {"Table Name": "Order", "TableDefinition": "Sales orders"},
        ),
    ]
    _, children = WorkbookDictionaryChunker().chunk(elements)
    defs = [c for c in children if c.chunk_type == "table_definition"]
    catalogs = [c for c in children if c.chunk_type == "table_catalog"]
    assert len(defs) == 2
    assert any("Customer contact" in c.text for c in defs)
    assert len(catalogs) == 1
    assert "Customer" in catalogs[0].text
    assert "Order" in catalogs[0].text


def test_code_set_region_mapping():
    elements = [
        _row(
            "Code Set",
            2,
            {
                "Code Set (name)": "Region",
                "Permissible Value (list of all possible codes)": "R1",
                "Permissible value meaning (list of all possible meanings)": "East region",
            },
        ),
    ]
    _, children = WorkbookDictionaryChunker().chunk(elements)
    codes = [c for c in children if c.chunk_type == "code_set"]
    assert len(codes) == 1
    assert "R1" in codes[0].text
    assert "East region" in codes[0].text


def test_database_chunk():
    elements = [
        _row(
            "Database",
            2,
            {
                "DictionaryName": "MainDB",
                "DictionaryDescription": "Primary application database",
            },
        ),
    ]
    _, children = WorkbookDictionaryChunker().chunk(elements)
    db = [c for c in children if c.chunk_type == "database"]
    assert len(db) == 1
    assert "Primary application" in db[0].text


@pytest.mark.skipif(
    not FIXTURE.exists() and not REPO_FIXTURE.exists(),
    reason="workbook fixture not present",
)
def test_workbook_fixture_counts():
    path = FIXTURE if FIXTURE.exists() else REPO_FIXTURE
    elements = parse_excel(str(path))
    _, children = WorkbookDictionaryChunker().chunk(elements)
    types = [c.chunk_type for c in children]
    assert types.count("table_definition") >= 40
    assert types.count("code_set") >= 20
    assert types.count("database") >= 1
    assert types.count("column") >= 100
    assert types.count("table_catalog") >= 1
