"""Shared row-to-element conversion for sheet-aware table documents."""

import json

from .types import ParsedElement


def cell_str(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_headers(raw: list[str]) -> list[str]:
    headers: list[str] = []
    seen: dict[str, int] = {}
    for i, h in enumerate(raw):
        name = h if h else f"column_{i + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 1
        headers.append(name)
    return headers


def row_is_empty(cells: list[str]) -> bool:
    return not any(cells)


def row_to_json(sheet_name: str, row_index: int, headers: list[str], values: list[str]) -> str:
    payload: dict = {"sheet": sheet_name, "row": row_index}
    for header, value in zip(headers, values):
        if value:
            payload[header] = value
    return json.dumps(payload, ensure_ascii=False)


def row_to_markdown(headers: list[str], values: list[str]) -> str:
    header_line = "| " + " | ".join(headers) + " |"
    value_line = "| " + " | ".join(values) + " |"
    return f"{header_line}\n{value_line}"


def rows_to_sheet_elements(
    sheet_name: str,
    rows_raw: list[list[str]],
    *,
    row_format: str = "json",
) -> list[ParsedElement]:
    """
    Convert raw rows into SheetTitle -> TableHeader -> TableRow elements.
    First non-empty row is treated as the header row.
    """
    while rows_raw and row_is_empty(rows_raw[-1]):
        rows_raw.pop()
    if not rows_raw:
        return []

    elements: list[ParsedElement] = []
    elements.append(
        ParsedElement(
            text=f"# Sheet: {sheet_name}",
            category="SheetTitle",
            sheet_name=sheet_name,
        )
    )

    header_idx = next((i for i, r in enumerate(rows_raw) if not row_is_empty(r)), None)
    if header_idx is None:
        return elements

    headers = normalize_headers(rows_raw[header_idx])
    header_md = row_to_markdown(headers, headers)
    elements.append(
        ParsedElement(
            text=header_md,
            category="TableHeader",
            sheet_name=sheet_name,
            row_index=header_idx + 1,
        )
    )

    for row_offset, row_cells in enumerate(rows_raw[header_idx + 1 :], start=1):
        if row_is_empty(row_cells):
            continue
        data_row = header_idx + 1 + row_offset
        padded = list(row_cells) + [""] * max(0, len(headers) - len(row_cells))
        values = padded[: len(headers)]
        if row_format == "markdown":
            text = row_to_markdown(headers, values)
        else:
            text = row_to_json(sheet_name, data_row, headers, values)
        elements.append(
            ParsedElement(
                text=text,
                category="TableRow",
                sheet_name=sheet_name,
                row_index=data_row,
            )
        )

    return elements
