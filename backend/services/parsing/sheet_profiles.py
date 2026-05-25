"""Detect per-sheet layout profiles for multi-sheet Excel data dictionaries."""

import json
import re
from enum import Enum

from .types import ParsedElement

TABLE_ROW = "TableRow"


class SheetProfile(str, Enum):
    DATABASE = "database"
    TABLE_CATALOG = "table_catalog"
    FIELD = "field"
    CODE_SET = "code_set"
    OVERVIEW = "overview"
    SKIP = "skip"


def _norm(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().lower())


# Ordered (header_pattern, role) — first match wins per role
PROFILE_ALIASES: dict[SheetProfile, list[tuple[str, str]]] = {
    SheetProfile.DATABASE: [
        ("dictionaryname", "name"),
        ("dictionaryformalname", "formal_name"),
        ("dictionarydescription", "description"),
        ("administrativenotes", "notes"),
        ("stewardorganization", "steward_org"),
        ("stewardcontact", "steward_contact"),
    ],
    SheetProfile.TABLE_CATALOG: [
        ("table name", "table"),
        ("tablename", "table"),
        ("tabledefinition", "definition"),
        ("tableenglishname", "english_name"),
        ("table comment", "comment"),
        ("table owner", "owner"),
    ],
    SheetProfile.FIELD: [
        ("table name", "table"),
        ("column name", "column"),
        ("columndefinition", "definition"),
        ("col_datatype", "datatype"),
        ("columnenglishname", "english_name"),
        ("column comment", "comment"),
    ],
    SheetProfile.CODE_SET: [
        ("code set (name)", "set_name"),
        ("permissible value (list of all possible codes)", "code"),
        ("permissible value meaning (list of all possible meanings)", "meaning"),
    ],
}

CODE_SET_SHEET_RE = re.compile(r"code\s*set", re.I)
DB_SHEET_RE = re.compile(r"\bdb\b|dictionary", re.I)
INTRO_SHEET_RE = re.compile(r"intro|worksheet", re.I)


def _parse_row_keys(text: str) -> set[str]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return set()
    return {k for k in data if k not in ("sheet", "row")}


def _headers_for_sheet(rows: list[ParsedElement]) -> set[str]:
    keys: set[str] = set()
    for el in rows[:8]:
        if el.category != TABLE_ROW:
            continue
        keys.update(_parse_row_keys(el.text))
    return keys


def map_headers(headers: set[str], profile: SheetProfile) -> dict[str, str]:
    """Map canonical role -> original header name using profile-specific ordered aliases."""
    norm_to_original: dict[str, str] = {}
    for h in headers:
        norm_to_original[_norm(h)] = h

    mapping: dict[str, str] = {}
    for pattern, role in PROFILE_ALIASES.get(profile, []):
        if role in mapping:
            continue
        if pattern in norm_to_original:
            mapping[role] = norm_to_original[pattern]
            continue
        for nh, orig in norm_to_original.items():
            if pattern in nh or nh == pattern:
                mapping[role] = orig
                break
    return mapping


def detect_sheet_profile(sheet_name: str, headers: set[str]) -> SheetProfile:
    norms = {_norm(h) for h in headers}

    if CODE_SET_SHEET_RE.search(sheet_name or ""):
        return SheetProfile.CODE_SET
    if "permissible value (list of all possible codes)" in norms:
        return SheetProfile.CODE_SET

    if DB_SHEET_RE.search(sheet_name or "") or "dictionaryname" in norms:
        return SheetProfile.DATABASE

    if INTRO_SHEET_RE.search(sheet_name or ""):
        return SheetProfile.OVERVIEW

    has_table = "table name" in norms or "tablename" in norms
    has_column = "column name" in norms or "columnname" in norms
    has_table_def = "tabledefinition" in norms

    if has_table and has_table_def and not has_column:
        return SheetProfile.TABLE_CATALOG

    if has_table and has_column and "columndefinition" in norms:
        return SheetProfile.FIELD

    if has_column and "columndefinition" in norms:
        return SheetProfile.FIELD

    return SheetProfile.SKIP


def is_workbook_dictionary(elements: list[ParsedElement]) -> bool:
    """True when workbook has at least one recognizable dictionary sheet profile."""
    if not any(el.category == TABLE_ROW for el in elements):
        return False

    sheets: dict[str, list[ParsedElement]] = {}
    for el in elements:
        if el.category != TABLE_ROW:
            continue
        sheets.setdefault(el.sheet_name or "Sheet1", []).append(el)

    for sheet_name, rows in sheets.items():
        headers = _headers_for_sheet(rows)
        profile = detect_sheet_profile(sheet_name, headers)
        if profile != SheetProfile.SKIP:
            return True
    return False


def field_value(row_data: dict[str, str], role: str, header_map: dict[str, str]) -> str:
    key = header_map.get(role)
    if key and key in row_data:
        return str(row_data[key]).strip()
    return ""
