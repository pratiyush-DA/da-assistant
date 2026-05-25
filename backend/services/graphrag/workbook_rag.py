"""Workbook-specific retrieval helpers (spreadsheet dictionary clients only)."""

import re
from uuid import UUID

from django.conf import settings

from services.neo4j.driver import get_driver

WORKBOOK_CHUNK_TYPES = frozenset({
    "database",
    "table_definition",
    "table_catalog",
    "column",
    "code_set",
    "overview",
    "table",
})

NARRATIVE_CHUNK_TYPES = frozenset({"row"})

NARRATIVE_QUERY_PATTERN = re.compile(
    r"\b("
    r"phase\s*\d|project|architecture|scope|requirement|roadmap|"
    r"milestone|frd|documentation|implementation|deliverable|"
    r"business\s+plan|system\s+design|ingestion|design\s+document"
    r")\b",
    re.I,
)

WORKBOOK_QUERY_PATTERN = re.compile(
    r"\b("
    r"column|field|datatype|data\s*type|code\s*set|"
    r"permissible|lookup|enumerat|table\s*catalog|"
    r"table\s*purpose|purpose\s+of\s+the\s+\w+\s+table|"
    r"list.*tables|tables\s+in|meaning\s+of|"
    r"database|dictionary\s*metadata|\bdb\b"
    r")\b",
    re.I,
)

INTENT_CHUNK_TYPES: dict[str, list[str]] = {
    "database": ["database", "overview"],
    "table": ["table_definition", "table_catalog"],
    "column": ["column"],
    "code": ["code_set"],
    "catalog": ["table_catalog"],
    "general": [
        "table_definition",
        "database",
        "table_catalog",
        "column",
        "code_set",
        "overview",
    ],
}

NO_COLUMN_SECONDARY_INTENTS = frozenset({"table", "database", "catalog", "code"})

NARRATIVE_SIGNAL_PATTERN = re.compile(
    r"\b(phase\s*\d|architecture|ingestion|requirements?|implementation|"
    r"roadmap|scope|design\s+document|frd)\b",
    re.I,
)
WORKBOOK_SIGNAL_PATTERN = re.compile(
    r"\b(dictionary|spreadsheet|excel|workbook|metadata|"
    r"data\s+dictionary|column|table\s+definition|code\s+set|schema)\b",
    re.I,
)


def client_has_narrative_chunks(client_id: UUID | str) -> bool:
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        record = session.run(
            """
            MATCH (cc:ChildChunk {client_id: $client_id})
            WHERE cc.chunk_type IN $types
            RETURN cc LIMIT 1
            """,
            client_id=str(client_id),
            types=list(NARRATIVE_CHUNK_TYPES),
        ).single()
        return record is not None


def client_is_mixed(client_id: UUID | str) -> bool:
    return client_has_workbook_chunks(client_id) and client_has_narrative_chunks(client_id)


def client_has_workbook_chunks(client_id: UUID | str) -> bool:
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        record = session.run(
            """
            MATCH (cc:ChildChunk {client_id: $client_id})
            WHERE cc.chunk_type IN $types
            RETURN cc LIMIT 1
            """,
            client_id=str(client_id),
            types=list(WORKBOOK_CHUNK_TYPES),
        ).single()
        return record is not None


def classify_workbook_query(query: str) -> str:
    q = query.lower()
    if re.search(r"\b(list|how many|name.*tables|tables in)\b", q):
        return "catalog"
    if re.search(r"\b(code\s*set|permissible|lookup|enumerat|meaning of)\b", q):
        return "code"
    if re.search(
        r"\b(database|dictionary\s*metadata|what\s+does.*\b(db|database)\b|represent)\b", q
    ):
        return "database"
    if re.search(r"\b(purpose of|table purpose|what is the .+ table)\b", q):
        return "table"
    if re.search(r"\b(column|field|datatype|data type|definition of)\b", q):
        return "column"
    if re.search(r"\b(relationship|ontology|intro|overview)\b", q):
        return "database"
    return "general"


def intent_chunk_types(intent: str) -> list[str]:
    return INTENT_CHUNK_TYPES.get(intent, INTENT_CHUNK_TYPES["general"])


def _workbook_query_strength(query: str) -> int:
    q = query.lower()
    score = 0
    if WORKBOOK_QUERY_PATTERN.search(q):
        score += 2
    if classify_workbook_query(query) != "general":
        score += 2
    return score


def _narrative_query_strength(query: str) -> int:
    q = query.lower()
    score = 0
    if NARRATIVE_QUERY_PATTERN.search(q):
        score += 2
    if re.search(r"phase\s*\d", q, re.I):
        score += 2
    if "project" in q and "table" not in q:
        score += 1
    return score


def _query_spans_both_domains(query: str) -> bool:
    has_narr = bool(NARRATIVE_SIGNAL_PATTERN.search(query))
    has_wb = bool(WORKBOOK_SIGNAL_PATTERN.search(query))
    if re.search(r"phase\s*\d", query, re.I) and re.search(
        r"\b(dictionary|spreadsheet|metadata)\b", query, re.I
    ):
        return True
    return has_narr and has_wb


def classify_query_domain(query: str) -> str:
    if _query_spans_both_domains(query):
        return "general"

    wb = _workbook_query_strength(query)
    narr = _narrative_query_strength(query)
    if wb > narr and wb >= 2:
        return "workbook"
    if narr > wb and narr >= 2:
        return "narrative"
    if wb >= 2 and narr >= 2:
        return "general"
    if narr >= 2:
        return "narrative"
    if wb >= 2:
        return "workbook"
    return "general"


def resolve_budget_mode(client_id: UUID | str, query: str) -> str:
    intent = classify_workbook_query(query)
    intent_modes = {
        "table": "workbook_table",
        "database": "workbook_database",
        "catalog": "workbook_catalog",
        "column": "workbook_column",
        "code": "workbook_code",
    }
    if client_is_mixed(client_id):
        domain = classify_query_domain(query)
        if domain == "narrative":
            return "narrative"
        if domain == "workbook":
            return intent_modes.get(intent, "workbook")
        return "mixed"
    if client_has_workbook_chunks(client_id):
        return intent_modes.get(intent, "workbook")
    return "default"


def resolve_use_dictionary_prompt(client_id: UUID | str, query: str) -> bool:
    if not client_has_workbook_chunks(client_id):
        return False
    if client_is_mixed(client_id):
        return classify_query_domain(query) == "workbook"
    return True
