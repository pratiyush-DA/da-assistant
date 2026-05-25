"""Parse CSV files into sheet-aware table elements (single logical sheet)."""

import csv
from pathlib import Path

from .table_rows import cell_str, rows_to_sheet_elements
from .types import ParsedElement


def _read_csv_rows(file_path: str) -> list[list[str]]:
    path = Path(file_path)
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")

    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel

    reader = csv.reader(text.splitlines(), dialect=dialect)
    return [[cell_str(c) for c in row] for row in reader]


def parse_csv(
    file_path: str,
    *,
    row_format: str = "json",
) -> list[ParsedElement]:
    """Parse .csv as one sheet named after the file stem."""
    sheet_name = Path(file_path).stem or "Sheet1"
    rows_raw = _read_csv_rows(file_path)
    return rows_to_sheet_elements(sheet_name, rows_raw, row_format=row_format)
