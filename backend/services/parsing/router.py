from pathlib import Path

from .csv_parser import parse_csv
from .excel_parser import EXCEL_FILE_TYPES, parse_excel
from .parser import parse_document_generic
from .types import ParsedElement
from .xls_parser import parse_xls


def normalize_file_type(file_type: str) -> str:
    return file_type.lower().lstrip(".")


def parse_document(file_path: str, file_type: str) -> list[ParsedElement]:
    ext = normalize_file_type(file_type)
    if not ext:
        ext = Path(file_path).suffix.lower().lstrip(".")
    if ext in EXCEL_FILE_TYPES:
        return parse_excel(file_path)
    if ext == "xls":
        return parse_xls(file_path)
    if ext == "csv":
        return parse_csv(file_path)
    return parse_document_generic(file_path)
