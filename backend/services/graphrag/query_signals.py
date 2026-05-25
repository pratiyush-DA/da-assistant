"""Lightweight query parsing for metadata-aware retrieval (file-agnostic)."""

import re
from uuid import UUID

from services.graphrag.metadata_lookup import normalize_column_identifier
from services.graphrag.workbook_rag import classify_workbook_query

CODE_SET_PATTERN = re.compile(r"code\s*sets?|lookup|enumerat", re.I)
TABLE_PATTERN = re.compile(
    r"\b(section\s*[a-z0-9\-]+|table\s+[a-z0-9\-]+)\b", re.I
)
ENTITY_TABLE_PATTERN = re.compile(
    r"\b(?:purpose\s+of\s+(?:the\s+)?|what\s+is\s+(?:the\s+)?)([A-Za-z][A-Za-z0-9_]*)\s+table\b",
    re.I,
)
SIMPLE_TABLE_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z0-9_]*)\s+table\b",
    re.I,
)
COLUMN_OF_PATTERN = re.compile(
    r"(?:definition|datatype|data\s*type).*(?:of|for)\s+([A-Za-z][A-Za-z0-9_]+)",
    re.I,
)
COLUMN_BEFORE_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z0-9_]+)\s+.*(?:definition|datatype|data\s*type)\b",
    re.I,
)
COLUMN_FIELD_PATTERN = re.compile(
    r"\b(?:column|field)\s+([A-Za-z][A-Za-z0-9_]*)\b",
    re.I,
)
TABLE_NAME_STOPWORDS = frozenset(
    {"the", "a", "what", "which", "list", "all", "any", "some", "this", "that"}
)
COLUMN_STOPWORDS = frozenset(
    {
        "definition",
        "datatype",
        "data",
        "type",
        "column",
        "field",
        "what",
        "the",
        "and",
        "for",
        "of",
    }
)


def extract_entity_table_name(query: str) -> str | None:
    m = ENTITY_TABLE_PATTERN.search(query)
    if m:
        return m.group(1).strip()
    m = SIMPLE_TABLE_PATTERN.search(query)
    if m:
        name = m.group(1).strip()
        if name.lower() not in TABLE_NAME_STOPWORDS:
            return name
    return None


def _pick_best_column_token(candidates: list[str]) -> str | None:
    filtered = [
        c
        for c in candidates
        if c.lower() not in COLUMN_STOPWORDS and len(c) >= 2
    ]
    if not filtered:
        return None
    return max(filtered, key=lambda t: (bool(re.search(r"[A-Z]", t[1:])), len(t)))


def extract_column_name(query: str) -> str | None:
    q = query.strip()
    candidates: list[str] = []

    patterns = [
        re.compile(
            r"\b(?:definition|datatype|data\s*type)\s+(?:of|for)\s+([A-Za-z][A-Za-z0-9_]*)\b",
            re.I,
        ),
        COLUMN_OF_PATTERN,
        COLUMN_BEFORE_PATTERN,
        COLUMN_FIELD_PATTERN,
    ]
    for pattern in patterns:
        m = pattern.search(q)
        if m:
            candidates.append(m.group(1))

    tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]+", q)
    for tok in tokens:
        if len(tok) >= 4 and tok[0].isupper():
            candidates.append(tok)

    best = _pick_best_column_token(candidates)
    return best


def extract_sheet_hint(query: str, client_id: UUID | str | None = None) -> str | None:
    if client_id is not None:
        from services.graphrag.client_catalog import get_sheet_index, sheet_hint_from_query

        return sheet_hint_from_query(query, get_sheet_index(client_id))
    return None


def extract_table_hint(query: str) -> str | None:
    entity = extract_entity_table_name(query)
    if entity:
        return entity
    m = TABLE_PATTERN.search(query)
    if m:
        return m.group(1).strip()
    return None


def wants_code_sets(query: str) -> bool:
    return bool(CODE_SET_PATTERN.search(query))


def parse_query_signals(query: str, client_id: UUID | str | None = None) -> dict:
    intent = classify_workbook_query(query)
    col = extract_column_name(query)
    return {
        "sheet_hint": extract_sheet_hint(query, client_id),
        "table_hint": extract_table_hint(query),
        "entity_table": extract_entity_table_name(query),
        "column_name": col,
        "column_name_norm": normalize_column_identifier(col) if col else None,
        "workbook_intent": intent,
        "wants_code_sets": wants_code_sets(query),
    }
