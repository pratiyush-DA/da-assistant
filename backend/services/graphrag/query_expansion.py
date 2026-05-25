"""Rule-based query expansion for data dictionary retrieval (file-agnostic)."""

import re

from services.graphrag.workbook_rag import classify_query_domain, classify_workbook_query

INTENTS_SKIP_COLUMN_SUFFIXES = frozenset({
    "table",
    "table_by_definition",
    "database",
    "catalog",
    "code",
    "column",
})


def _camel_variants(phrase: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", phrase)
    if not words:
        return []
    joined = "".join(w.capitalize() for w in words)
    full = "".join(words)
    compact = "".join(w.lower() for w in words)
    return list(dict.fromkeys([phrase, joined, full, compact, " ".join(words)]))


def expand_query(
    query: str,
    max_queries: int = 6,
    *,
    signals: dict | None = None,
) -> list[str]:
    """Return deduplicated search strings (original first)."""
    seen: set[str] = set()
    out: list[str] = []

    def add(q: str) -> None:
        q = q.strip()
        if not q or q.lower() in seen:
            return
        seen.add(q.lower())
        out.append(q)

    add(query)

    lower = query.lower()
    domain = classify_query_domain(query)
    wb_intent = (
        (signals or {}).get("workbook_intent")
        or classify_workbook_query(query)
    )
    entity_table = (signals or {}).get("entity_table")
    column_name = (signals or {}).get("column_name")
    quoted = (signals or {}).get("quoted_definition")

    if domain == "narrative":
        for variant in _camel_variants(query):
            add(variant)
        return out[:max_queries]

    if wb_intent == "catalog":
        add("table catalog")
        add("list of tables")
    elif wb_intent == "code":
        add("code set")
        add("permissible values")
    elif wb_intent == "database":
        add("database description")
        add("dictionary metadata")
    elif wb_intent == "table_by_definition":
        if quoted:
            add(quoted)
            add(f"Definition: {quoted}")
    elif wb_intent == "column":
        from services.graphrag.query_signals import extract_column_name

        col_token = column_name or extract_column_name(query)
        if col_token:
            add(f"{col_token} definition")
            add(f"{col_token} datatype")
            add(f"Column: {col_token}")
            if entity_table:
                add(f"Table: {entity_table} Column: {col_token}")

    if wb_intent == "table":
        from services.graphrag.query_signals import extract_entity_table_name

        entity = entity_table or extract_entity_table_name(query)
        if entity:
            add(f"Table: {entity}")
            add(f"{entity} table definition")

    skip_column_suffix = (
        wb_intent in INTENTS_SKIP_COLUMN_SUFFIXES
        or domain == "narrative"
        or "column" in lower
        or "field" in lower
        or (entity_table and column_name)
    )
    if not skip_column_suffix:
        add(f"{query} columns")
        add(f"{query} definition")

    if wb_intent != "table_by_definition":
        for variant in _camel_variants(query):
            add(variant)

    return out[:max_queries]
