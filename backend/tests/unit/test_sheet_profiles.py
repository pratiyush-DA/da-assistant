import json

from services.parsing.sheet_profiles import (
    SheetProfile,
    detect_sheet_profile,
    is_workbook_dictionary,
)
from services.parsing.types import ParsedElement


def _row(sheet: str, payload: dict) -> ParsedElement:
    return ParsedElement(
        text=json.dumps({"sheet": sheet, "row": 1, **payload}),
        category="TableRow",
        sheet_name=sheet,
    )


def test_detect_field_profile():
    headers = {"Table Name", "Column Name", "ColumnDefinition", "Col_Datatype"}
    assert detect_sheet_profile("Fields", headers) == SheetProfile.FIELD


def test_detect_table_catalog_profile():
    headers = {"Table Name", "TableDefinition", "TableEnglishName"}
    assert detect_sheet_profile("Tables", headers) == SheetProfile.TABLE_CATALOG


def test_detect_database_profile():
    headers = {"DictionaryName", "DictionaryDescription"}
    assert detect_sheet_profile("Database", headers) == SheetProfile.DATABASE


def test_detect_code_set_profile():
    headers = {
        "Code Set (name)",
        "Permissible Value (list of all possible codes)",
        "Permissible value meaning (list of all possible meanings)",
    }
    assert detect_sheet_profile("Code Set", headers) == SheetProfile.CODE_SET


def test_is_workbook_dictionary_true():
    elements = [
        _row("Database", {"DictionaryName": "Main", "DictionaryDescription": "DB"}),
        _row(
            "Fields",
            {
                "Table Name": "Customer",
                "Column Name": "OrderId",
                "ColumnDefinition": "primary key",
            },
        ),
    ]
    assert is_workbook_dictionary(elements) is True
