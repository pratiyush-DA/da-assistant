"""Parse legacy .xls workbooks into sheet-aware table elements."""

from pathlib import Path

import xlrd

from .table_rows import cell_str, rows_to_sheet_elements
from .types import ParsedElement


def parse_xls(
    file_path: str,
    *,
    row_format: str = "json",
) -> list[ParsedElement]:
    """Parse .xls (BIFF) using xlrd."""
    path = Path(file_path)
    if path.suffix.lower() != ".xls":
        raise ValueError(f"Unsupported legacy Excel type: {path.suffix}")

    wb = xlrd.open_workbook(str(path))
    elements: list[ParsedElement] = []

    for sheet_idx in range(wb.nsheets):
        ws = wb.sheet_by_index(sheet_idx)
        sheet_name = ws.name
        rows_raw: list[list[str]] = []
        for row_idx in range(ws.nrows):
            row_cells = []
            for col_idx in range(ws.ncols):
                cell = ws.cell(row_idx, col_idx)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    row_cells.append(cell_str(cell.value))
                elif cell.ctype == xlrd.XL_CELL_EMPTY:
                    row_cells.append("")
                elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                    row_cells.append("TRUE" if cell.value else "FALSE")
                else:
                    row_cells.append(cell_str(cell.value))
            rows_raw.append(row_cells)

        elements.extend(
            rows_to_sheet_elements(sheet_name, rows_raw, row_format=row_format)
        )

    return elements
