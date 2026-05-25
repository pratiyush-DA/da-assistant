"""Spreadsheet file type helpers (isolated from PDF/DOCX/TXT document path)."""

from services.parsing.excel_parser import EXCEL_FILE_TYPES

SPREADSHEET_TYPES = frozenset({"xlsx", "xlsm", "xls", "csv"})


def is_spreadsheet_type(file_type: str) -> bool:
    ext = file_type.lower().lstrip(".")
    return ext in SPREADSHEET_TYPES or ext in EXCEL_FILE_TYPES
