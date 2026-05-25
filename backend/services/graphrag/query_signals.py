"""Lightweight query parsing for metadata-aware retrieval (file-agnostic)."""

import re
from uuid import UUID

from services.graphrag.metadata_lookup import normalize_column_identifier

CODE_SET_PATTERN = re.compile(r"code\s*sets?|lookup|enumerat", re.I)
TABLE_FOR_COLUMN_PATTERN = re.compile(
    r"\b(?:for|in|on)\s+table\s+([A-Za-z][A-Za-z0-9_\-]+)\b",
    re.I,
)
TABLE_NAME_INLINE_PATTERN = re.compile(
    r"\btable\s+([A-Za-z][A-Za-z0-9_\-]+)\s*[,?]",
    re.I,
)
SECTION_TABLE_PATTERN = re.compile(r"\b(section\s*[a-z0-9\-]+)\b", re.I)
ENTITY_TABLE_PATTERN = re.compile(
    r"\b(?:purpose\s+of\s+(?:the\s+)?|what\s+is\s+(?:the\s+)?)([A-Za-z][A-Za-z0-9_]*)\s+table\b",
    re.I,
)
SIMPLE_TABLE_PATTERN = re.compile(
    r"\b([A-Za-z][A-Za-z0-9_]*)\s+table\b",
    re.I,
)
COLUMN_OF_PATTERN = re.compile(
    r"(?:definition|datatype|data\s*type).*(?:of|for)\s+(?:the\s+)?(?:column\s+)?([A-Za-z][A-Za-z0-9_]+)",
    re.I,
)
COLUMN_BEFORE_PATTERN = re.compile(
    r"\b(?:column|field)\s+([A-Za-z][A-Za-z0-9_]+)\b",
    re.I,
)
COLUMN_FIELD_PATTERN = re.compile(
    r"\b(?:column|field)\s+([A-Za-z][A-Za-z0-9_]*)\b",
    re.I,
)
COLUMNDEF_PATTERN = re.compile(
    r"\b(?:columndefinition|column\s+definition)\s+(?:of|for)\s+(?:the\s+)?(?:column\s+)?([A-Za-z][A-Za-z0-9_]+)",
    re.I,
)
QUOTED_TEXT_PATTERN = re.compile(r'"([^"]+)"|\'([^\']+)\'')
TABLE_BY_DEF_PATTERN = re.compile(
    r"\b(?:which\s+table\s+name|table\s+has\s+the\s+following\s+table\s+definition|"
    r"following\s+table\s+definition)\b",
    re.I,
)
TABLE_NAME_STOPWORDS = frozenset(
    {"the", "a", "what", "which", "list", "all", "any", "some", "this", "that", "table"}
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
        "sheet",
        "tables",
        "table",
    }
)


def extract_quoted_definition(query: str) -> str | None:
    """Extract quoted phrase when question is about matching a table definition."""
    if not TABLE_BY_DEF_PATTERN.search(query) and not re.search(
        r"\btable\s+definition\b", query, re.I
    ):
        return None
    for m in QUOTED_TEXT_PATTERN.finditer(query):
        text = (m.group(1) or m.group(2) or "").strip()
        if len(text) >= 12:
            return text
    return None


def extract_table_for_column(query: str) -> str | None:
    """Parse explicit table reference for column questions."""
    m = TABLE_FOR_COLUMN_PATTERN.search(query)
    if m:
        return m.group(1).strip()
    m = TABLE_NAME_INLINE_PATTERN.search(query)
    if m:
        return m.group(1).strip()
    m = SECTION_TABLE_PATTERN.search(query)
    if m:
        return m.group(1).strip()
    return None


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


def resolve_entity_table(query: str, client_id: UUID | str | None) -> str | None:
    """Best table name: explicit for-table > purpose patterns > client catalog match."""
    for extractor in (extract_table_for_column, extract_entity_table_name):
        raw = extractor(query)
        if not raw:
            continue
        if client_id is not None:
            from services.graphrag.client_catalog import (
                get_distinct_table_names,
                resolve_table_name,
            )

            known = get_distinct_table_names(client_id)
            resolved = resolve_table_name(raw, known)
            if resolved:
                return resolved
        return raw
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
        COLUMNDEF_PATTERN,
        re.compile(
            r"\b(?:definition|datatype|data\s*type)\s+(?:of|for)\s+(?:the\s+)?(?:column\s+)?([A-Za-z][A-Za-z0-9_]+)\b",
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

    return _pick_best_column_token(candidates)


def extract_sheet_hint(query: str, client_id: UUID | str | None = None) -> str | None:
    if client_id is not None:
        from services.graphrag.client_catalog import get_sheet_index, resolve_sheet_hint

        return resolve_sheet_hint(query, get_sheet_index(client_id))
    return None


def extract_table_hint(query: str, client_id: UUID | str | None = None) -> str | None:
    return resolve_entity_table(query, client_id)


def wants_code_sets(query: str) -> bool:
    return bool(CODE_SET_PATTERN.search(query))


def parse_query_signals(query: str, client_id: UUID | str | None = None) -> dict:
    from services.graphrag.workbook_rag import classify_workbook_query

    col = extract_column_name(query)
    quoted = extract_quoted_definition(query)
    entity_table = resolve_entity_table(query, client_id)
    sheet_hint = extract_sheet_hint(query, client_id)
    intent = classify_workbook_query(
        query,
        quoted_definition=quoted,
        entity_table=entity_table,
        column_name=col,
        sheet_hint=sheet_hint,
    )
    return {
        "sheet_hint": sheet_hint,
        "table_hint": entity_table or extract_table_for_column(query),
        "entity_table": entity_table,
        "column_name": col,
        "column_name_norm": normalize_column_identifier(col) if col else None,
        "quoted_definition": quoted,
        "workbook_intent": intent,
        "wants_code_sets": wants_code_sets(query),
    }
