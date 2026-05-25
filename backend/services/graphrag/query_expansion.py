"""Rule-based query expansion for data dictionary retrieval (file-agnostic)."""

import re

from services.graphrag.workbook_rag import classify_query_domain, classify_workbook_query

INTENTS_SKIP_COLUMN_SUFFIXES = frozenset({"table", "database", "catalog", "code"})


def _camel_variants(phrase: str) -> list[str]:
    words = re.findall(r"[A-Za-z0-9]+", phrase)
    if not words:
        return []
    joined = "".join(w.capitalize() for w in words)
    full = "".join(words)
    compact = "".join(w.lower() for w in words)
    return list(dict.fromkeys([phrase, joined, full, compact, " ".join(words)]))


def expand_query(query: str, max_queries: int = 6) -> list[str]:
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
    wb_intent = classify_workbook_query(query)

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

    col_token = None
    if wb_intent == "column":
        from services.graphrag.query_signals import extract_column_name

        col_token = extract_column_name(query)
        if col_token:
            add(f"{col_token} definition")
            add(f"{col_token} datatype")
            add(f"Column: {col_token}")

    if (
        wb_intent not in INTENTS_SKIP_COLUMN_SUFFIXES
        and domain != "narrative"
        and "column" not in lower
        and "field" not in lower
    ):
        add(f"{query} columns")
        add(f"{query} definition")

    if wb_intent == "table":
        from services.graphrag.query_signals import extract_entity_table_name

        entity = extract_entity_table_name(query)
        if entity:
            add(f"Table: {entity}")
            add(f"{entity} table definition")

    for variant in _camel_variants(query):
        add(variant)

    return out[:max_queries]
