"""Client-scoped sheet metadata from Neo4j (no hardcoded sheet names)."""

import re
from difflib import SequenceMatcher
from uuid import UUID

from django.conf import settings

from services.neo4j.driver import get_driver

_sheet_index_cache: dict[str, dict[str, frozenset[str]]] = {}


def get_sheet_index(client_id: UUID | str) -> dict[str, frozenset[str]]:
    """Return sheet_name -> chunk_types present for this client."""
    key = str(client_id)
    if key in _sheet_index_cache:
        return _sheet_index_cache[key]

    index: dict[str, frozenset[str]] = {}
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (cc:ChildChunk {client_id: $client_id})
            WHERE cc.sheet_name IS NOT NULL AND cc.sheet_name <> ''
            RETURN cc.sheet_name AS sheet_name, collect(DISTINCT cc.chunk_type) AS types
            """,
            client_id=key,
        )
        for record in result:
            name = record["sheet_name"]
            types = record["types"] or []
            index[name] = frozenset(t for t in types if t)

    _sheet_index_cache[key] = index
    return index


def clear_sheet_index_cache(client_id: UUID | str | None = None) -> None:
    if client_id is None:
        _sheet_index_cache.clear()
    else:
        _sheet_index_cache.pop(str(client_id), None)


def _normalize_sheet_phrase(phrase: str) -> str:
    return re.sub(r"\s+", " ", phrase.strip().lower())


def _query_sheet_phrases(query: str) -> list[str]:
    """Extract candidate sheet references from the query."""
    phrases: list[str] = []
    q = query.strip()
    for m in re.finditer(
        r"(?:on|in|from|for)\s+(?:the\s+)?([A-Za-z][A-Za-z0-9\s]{2,}?)\s+sheet\b",
        q,
        re.I,
    ):
        phrases.append(m.group(1).strip())
    for m in re.finditer(
        r"\b([A-Za-z][A-Za-z0-9]*(?:\s+[A-Za-z][A-Za-z0-9]*)*)\s+sheet\b",
        q,
        re.I,
    ):
        phrases.append(m.group(1).strip())
    return list(dict.fromkeys(phrases))


def _preferred_chunk_types_for_query(query: str) -> frozenset[str] | None:
    q = query.lower()
    if re.search(r"\b(column|field|columndefinition|datatype|data\s*type)\b", q):
        return frozenset({"column"})
    if re.search(r"\b(table\s*definition|tabledefinition|table\s*purpose)\b", q):
        return frozenset({"table_definition", "table_catalog"})
    if re.search(r"\b(code\s*set|permissible)\b", q):
        return frozenset({"code_set"})
    if re.search(r"\b(database|dictionary)\b", q):
        return frozenset({"database"})
    return None


def resolve_sheet_hint(
    query: str,
    sheet_index: dict[str, frozenset[str]],
) -> str | None:
    """
    Resolve a sheet name from the query: exact substring first, then fuzzy token match.
    """
    if not sheet_index:
        return None

    exact = sheet_hint_from_query(query, sheet_index)
    if exact:
        return exact

    preferred = _preferred_chunk_types_for_query(query)
    phrases = _query_sheet_phrases(query)
    if not phrases:
        phrases = [query]

    best_name: str | None = None
    best_score = 0.0

    for phrase in phrases:
        norm_phrase = _normalize_sheet_phrase(phrase)
        if len(norm_phrase) < 3:
            continue
        for sheet_name, chunk_types in sheet_index.items():
            norm_sheet = _normalize_sheet_phrase(sheet_name)
            ratio = SequenceMatcher(None, norm_phrase, norm_sheet).ratio()
            if norm_phrase in norm_sheet or norm_sheet in norm_phrase:
                ratio = max(ratio, 0.85)
            if preferred and preferred & chunk_types:
                ratio += 0.08
            if ratio > best_score:
                best_score = ratio
                best_name = sheet_name

    if best_score >= 0.72:
        return best_name
    return None


def sheet_hint_from_query(query: str, sheet_index: dict[str, frozenset[str]]) -> str | None:
    """If the query mentions a known sheet name substring, return the longest match."""
    if not sheet_index:
        return None
    q_lower = query.lower()
    matches: list[tuple[int, str]] = []
    for sheet_name in sheet_index:
        sn_lower = sheet_name.lower()
        if len(sn_lower) < 3:
            continue
        if sn_lower in q_lower:
            matches.append((len(sheet_name), sheet_name))
    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def get_distinct_table_names(client_id: UUID | str) -> list[str]:
    """Distinct logical table names from table_definition chunks (catalog fallback)."""
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            """
            MATCH (cc:ChildChunk {client_id: $client_id})
            WHERE cc.chunk_type = 'table_definition'
              AND cc.table_name IS NOT NULL AND cc.table_name <> ''
            RETURN DISTINCT cc.table_name AS name
            ORDER BY name
            """,
            client_id=str(client_id),
        )
        return [r["name"] for r in result if r.get("name")]


def resolve_table_name(candidate: str, known_tables: list[str]) -> str | None:
    """Match a parsed table token to a known table name (case-insensitive)."""
    if not candidate or not known_tables:
        return None
    cand = candidate.strip()
    cand_lower = cand.lower()
    if cand_lower.startswith("table "):
        cand = cand[6:].strip()
        cand_lower = cand.lower()
    for name in known_tables:
        if name.lower() == cand_lower:
            return name
    best: str | None = None
    best_score = 0.0
    for name in known_tables:
        ratio = SequenceMatcher(None, cand_lower, name.lower()).ratio()
        if cand_lower in name.lower() or name.lower() in cand_lower:
            ratio = max(ratio, 0.9)
        if ratio > best_score:
            best_score = ratio
            best = name
    if best_score >= 0.85:
        return best
    return None
