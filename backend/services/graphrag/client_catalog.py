"""Client-scoped sheet metadata from Neo4j (no hardcoded sheet names)."""

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
