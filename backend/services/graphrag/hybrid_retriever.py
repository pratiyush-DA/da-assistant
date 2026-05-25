"""Hybrid vector + fulltext retrieval with RRF fusion."""

import re
from uuid import UUID

from django.conf import settings

from services.graphrag.metadata_lookup import column_name_variants
from services.graphrag.query_signals import parse_query_signals
from services.graphrag.retriever import RetrievedChunk, rerank_chunks
from services.langchain.embeddings import get_embeddings
from services.neo4j.driver import get_driver


def _escape_lucene(q: str) -> str:
    special = r'+-&&||!(){}[]^"~*?:\/'
    out = []
    for ch in q:
        if ch in special:
            out.append("\\" + ch)
        else:
            out.append(ch)
    return "".join(out)


def _chunk_key(record: dict) -> str:
    return (
        f"{record.get('document_id')}:{record.get('chunk_type')}:"
        f"{record.get('table_name')}:{record.get('column_name')}:"
        f"{record.get('id')}"
    )


def _column_filter_clause(column_names: list[str] | None, params: dict) -> str:
    if not column_names:
        return ""
    variants: list[str] = []
    for name in column_names:
        variants.extend(column_name_variants(name))
    variants = list(dict.fromkeys(variants))
    if not variants:
        return ""
    params["column_names"] = variants
    params["column_names_lower"] = [v.lower() for v in variants]
    return (
        " AND (node.column_name IN $column_names "
        "OR toLower(node.column_name) IN $column_names_lower)"
    )


def _record_to_chunk(record: dict, score: float) -> RetrievedChunk:
    return RetrievedChunk(
        id=record["id"],
        chunk_text=record["chunk_text"],
        section_header=record.get("section_header") or "",
        page_number=record.get("page_number"),
        document_id=record.get("document_id", ""),
        source=record.get("source") or "",
        score=score,
        chunk_type=record.get("chunk_type"),
        sheet_name=record.get("sheet_name"),
        table_name=record.get("table_name"),
        column_name=record.get("column_name"),
        child_text=record.get("child_text"),
    )


def _vector_search(
    session,
    client_id: str,
    query_vector: list[float],
    limit: int,
    chunk_types: list[str] | None,
    table_names: list[str] | None,
    sheet_hint: str | None,
    column_names: list[str] | None,
) -> list[dict]:
    type_filter = ""
    params: dict = {
        "index_name": settings.VECTOR_INDEX_NAME,
        "limit": limit,
        "embedding": query_vector,
        "client_id": client_id,
    }
    if chunk_types:
        type_filter = "AND node.chunk_type IN $chunk_types"
        params["chunk_types"] = chunk_types
    if table_names:
        type_filter += " AND node.table_name IN $table_names"
        params["table_names"] = table_names
    if sheet_hint:
        type_filter += " AND node.sheet_name CONTAINS $sheet_hint"
        params["sheet_hint"] = sheet_hint
    type_filter += _column_filter_clause(column_names, params)

    cypher = f"""
    CALL db.index.vector.queryNodes($index_name, $limit, $embedding)
    YIELD node, score
    WHERE node:ChildChunk AND node.client_id = $client_id
    {type_filter}
    WITH node, score
    ORDER BY score DESC
    LIMIT $limit
    MATCH (node)-[:PART_OF]->(parent:Chunk)
    MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
    RETURN node.id AS id,
           parent.text AS chunk_text,
           node.text AS child_text,
           parent.section_header AS section_header,
           parent.page_number AS page_number,
           parent.document_id AS document_id,
           doc.filename AS source,
           node.chunk_type AS chunk_type,
           node.sheet_name AS sheet_name,
           node.table_name AS table_name,
           node.column_name AS column_name,
           score
    ORDER BY score DESC
    """
    result = session.run(cypher, **params)
    return [dict(r) for r in result]


def _fulltext_search(
    session,
    client_id: str,
    query: str,
    limit: int,
    chunk_types: list[str] | None,
    table_names: list[str] | None,
    sheet_hint: str | None,
    column_names: list[str] | None,
) -> list[dict]:
    lucene_q = _escape_lucene(query)
    if not lucene_q.strip():
        return []

    type_filter = ""
    params: dict = {
        "index_name": settings.FULLTEXT_INDEX_NAME,
        "query": lucene_q,
        "limit": limit,
        "client_id": client_id,
    }
    if chunk_types:
        type_filter = "AND node.chunk_type IN $chunk_types"
        params["chunk_types"] = chunk_types
    if table_names:
        type_filter += " AND node.table_name IN $table_names"
        params["table_names"] = table_names
    if sheet_hint:
        type_filter += " AND node.sheet_name CONTAINS $sheet_hint"
        params["sheet_hint"] = sheet_hint
    type_filter += _column_filter_clause(column_names, params)

    cypher = f"""
    CALL db.index.fulltext.queryNodes($index_name, $query)
    YIELD node, score
    WHERE node:ChildChunk AND node.client_id = $client_id
    {type_filter}
    WITH node, score
    ORDER BY score DESC
    LIMIT $limit
    MATCH (node)-[:PART_OF]->(parent:Chunk)
    MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
    RETURN node.id AS id,
           parent.text AS chunk_text,
           node.text AS child_text,
           parent.section_header AS section_header,
           parent.page_number AS page_number,
           parent.document_id AS document_id,
           doc.filename AS source,
           node.chunk_type AS chunk_type,
           node.sheet_name AS sheet_name,
           node.table_name AS table_name,
           node.column_name AS column_name,
           score
    ORDER BY score DESC
    """
    try:
        result = session.run(cypher, **params)
        return [dict(r) for r in result]
    except Exception:
        return []


def rrf_merge(
    ranked_lists: list[list[dict]],
    k: int | None = None,
) -> list[RetrievedChunk]:
    k = k or settings.RRF_K
    scores: dict[str, float] = {}
    records: dict[str, dict] = {}

    for result_list in ranked_lists:
        for rank, rec in enumerate(result_list):
            key = _chunk_key(rec)
            scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
            records[key] = rec

    sorted_keys = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
    return [_record_to_chunk(records[key], scores[key]) for key in sorted_keys]


def hybrid_search(
    client_id: UUID | str,
    query: str,
    *,
    limit: int | None = None,
    chunk_types: list[str] | None = None,
    table_names: list[str] | None = None,
    sheet_hint: str | None = None,
    column_names: list[str] | None = None,
    vector_only: bool = False,
) -> list[RetrievedChunk]:
    limit = limit or settings.VECTOR_SEARCH_LIMIT
    client_id = str(client_id)
    signals = parse_query_signals(query, client_id)
    if sheet_hint is None and signals.get("sheet_hint"):
        sheet_hint = signals["sheet_hint"]
    if chunk_types is None and signals.get("wants_code_sets"):
        chunk_types = ["code_set", "column", "table"]

    query_vector = get_embeddings().embed_query(query)
    fetch_limit = max(limit * 2, settings.FULLTEXT_SEARCH_LIMIT)

    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        vector_hits = _vector_search(
            session,
            client_id,
            query_vector,
            fetch_limit,
            chunk_types,
            table_names,
            sheet_hint,
            column_names,
        )
        if settings.HYBRID_SEARCH_ENABLED and not vector_only:
            ft_hits = _fulltext_search(
                session,
                client_id,
                query,
                settings.FULLTEXT_SEARCH_LIMIT,
                chunk_types,
                table_names,
                sheet_hint,
                column_names,
            )
            merged = rrf_merge([vector_hits, ft_hits])
        else:
            merged = rrf_merge([vector_hits])

    seen: set[str] = set()
    deduped: list[RetrievedChunk] = []
    for chunk in merged:
        key = f"{chunk.document_id}:{chunk.chunk_type}:{chunk.table_name}:{chunk.column_name}:{chunk.id}"
        if key in seen:
            continue
        seen.add(key)
        deduped.append(chunk)
        if len(deduped) >= limit:
            break

    return rerank_chunks(query, deduped)
