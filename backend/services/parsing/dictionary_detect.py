"""Detect Excel data-dictionary layout from parsed table elements."""

import json
import re

from .types import ParsedElement

TABLE_ALIASES = frozenset(
    {
        "table",
        "table name",
        "table_name",
        "tablename",
        "entity",
        "entity name",
        "logical table",
        "database table",
    }
)
COLUMN_ALIASES = frozenset(
    {
        "column",
        "column name",
        "column_name",
        "field",
        "field name",
        "field_name",
        "attribute",
        "attribute name",
        "element name",
    }
)
DEFINITION_ALIASES = frozenset(
    {
        "definition",
        "description",
        "business definition",
        "field definition",
        "column definition",
        "meaning",
        "comments",
        "comment",
    }
)
CODE_ALIASES = frozenset({"code", "code value", "code id", "value", "code description"})
CODE_SET_SHEET_PATTERN = re.compile(r"code", re.I)


def _norm_header(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


def _header_role(header: str) -> str | None:
    h = _norm_header(header)
    if h in TABLE_ALIASES:
        return "table"
    if h in COLUMN_ALIASES:
        return "column"
    if h in DEFINITION_ALIASES:
        return "definition"
    if h in CODE_ALIASES:
        if h in ("code", "code value", "code id"):
            return "code"
        if h == "value":
            return "value"
    if "table" in h and "name" in h:
        return "table"
    if "field" in h or "column" in h:
        return "column"
    if "definition" in h or "description" in h:
        return "definition"
    return None


def _parse_row_payload(text: str) -> dict[str, str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return {
        k: str(v).strip()
        for k, v in data.items()
        if k not in ("sheet", "row") and v is not None and str(v).strip()
    }


def _headers_from_elements(elements: list[ParsedElement]) -> set[str]:
    headers: set[str] = set()
    for el in elements:
        if el.category != "TableRow":
            continue
        headers.update(_parse_row_payload(el.text).keys())
    return headers


def is_code_set_sheet(sheet_name: str, headers: set[str]) -> bool:
    if CODE_SET_SHEET_PATTERN.search(sheet_name or ""):
        return True
    roles = {_header_role(h) for h in headers}
    return "code" in roles and ("value" in roles or "definition" in roles)


def detect_document_kind(elements: list[ParsedElement]) -> str:
    """
    Return 'data_dictionary' when sheets look like table/column/definition metadata,
    else 'generic_table'.
    """
    if not any(el.category == "TableRow" for el in elements):
        return "generic_table"

    headers = _headers_from_elements(elements)
    if not headers:
        return "generic_table"

    roles = {_header_role(h) for h in headers}
    roles.discard(None)
    if "table" in roles and "column" in roles and "definition" in roles:
        return "data_dictionary"
    if "column" in roles and "definition" in roles:
        return "data_dictionary"
    return "generic_table"


def build_header_map(headers: set[str]) -> dict[str, str]:
    """Map canonical role -> original header name."""
    mapping: dict[str, str] = {}
    for h in headers:
        role = _header_role(h)
        if role and role not in mapping:
            mapping[role] = h
    return mapping
