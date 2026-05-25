"""Direct Neo4j metadata lookups (before vector search)."""

import re
from uuid import UUID

from django.conf import settings

from services.graphrag.context_extractors import (
    catalog_chunk_has_parseable_names,
    extract_definition_from_table_chunk,
)
from services.graphrag.retriever import RetrievedChunk
from services.neo4j.driver import get_driver

_CHILD_RETURN = """
            RETURN cc.id AS id,
                   parent.text AS chunk_text,
                   cc.text AS child_text,
                   parent.section_header AS section_header,
                   parent.page_number AS page_number,
                   parent.document_id AS document_id,
                   doc.filename AS source,
                   cc.chunk_type AS chunk_type,
                   cc.sheet_name AS sheet_name,
                   cc.table_name AS table_name,
                   cc.column_name AS column_name
"""


def normalize_text_phrase(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def normalize_column_identifier(name: str) -> str:
    """Collapse spaces/underscores for case-insensitive column matching."""
    return re.sub(r"[\s_]+", "", name).lower()


def column_name_variants(name: str) -> list[str]:
    """Original + normalized forms for Cypher IN clauses."""
    variants = {name.strip(), name.strip().replace(" ", "")}
    compact = normalize_column_identifier(name)
    if compact:
        variants.add(compact)
    return [v for v in variants if v]


def _definition_similarity(phrase: str, chunk_definition: str | None) -> float:
    if not phrase or not chunk_definition:
        return 0.0
    norm_p = normalize_text_phrase(phrase)
    norm_d = normalize_text_phrase(chunk_definition)
    if norm_p == norm_d:
        return 1.0
    if norm_p in norm_d or norm_d in norm_p:
        return 0.95
    p_tokens = set(norm_p.split())
    d_tokens = set(norm_d.split())
    if not p_tokens:
        return 0.0
    overlap = len(p_tokens & d_tokens) / len(p_tokens)
    return overlap


def _record_to_chunk(record: dict, score: float = 1.0) -> RetrievedChunk:
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


def fetch_catalog_chunk(client_id: UUID | str) -> RetrievedChunk | None:
    """Load table_catalog chunk by metadata (no vector search)."""
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            f"""
            MATCH (cc:ChildChunk {{client_id: $client_id, chunk_type: 'table_catalog'}})
            MATCH (cc)-[:PART_OF]->(parent:Chunk)
            MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
            {_CHILD_RETURN}
            LIMIT 1
            """,
            client_id=str(client_id),
        )
        row = result.single()
    if not row:
        return None
    chunk = _record_to_chunk(dict(row), score=1.0)
    if catalog_chunk_has_parseable_names(chunk):
        return chunk
    return None


def fetch_table_definition(
    client_id: UUID | str,
    table_name: str,
    *,
    sheet_name: str | None = None,
) -> RetrievedChunk | None:
    """Load table_definition for an exact table name (case-insensitive)."""
    if not table_name:
        return None
    sheet_filter = ""
    params: dict = {
        "client_id": str(client_id),
        "table_name": table_name,
    }
    if sheet_name:
        sheet_filter = " AND cc.sheet_name = $sheet_name"
        params["sheet_name"] = sheet_name

    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            f"""
            MATCH (cc:ChildChunk {{client_id: $client_id, chunk_type: 'table_definition'}})
            WHERE toLower(cc.table_name) = toLower($table_name)
            {sheet_filter}
            MATCH (cc)-[:PART_OF]->(parent:Chunk)
            MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
            {_CHILD_RETURN}
            LIMIT 3
            """,
            **params,
        )
        rows = [dict(r) for r in result]
    if not rows:
        return None
    return _record_to_chunk(rows[0], score=1.0)


def lookup_table_by_definition(
    client_id: UUID | str,
    definition_phrase: str,
    *,
    sheet_name: str | None = None,
    limit: int = 3,
) -> list[RetrievedChunk]:
    """Find table_definition chunks matching a definition phrase."""
    norm = normalize_text_phrase(definition_phrase)
    if len(norm) < 8:
        return []

    sheet_filter = ""
    params: dict = {
        "client_id": str(client_id),
        "norm": norm,
        "fetch_limit": limit * 8,
    }
    if sheet_name:
        sheet_filter = " AND cc.sheet_name = $sheet_name"
        params["sheet_name"] = sheet_name

    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            f"""
            MATCH (cc:ChildChunk {{client_id: $client_id, chunk_type: 'table_definition'}})
            WHERE toLower(cc.text) CONTAINS $norm
            {sheet_filter}
            MATCH (cc)-[:PART_OF]->(parent:Chunk)
            MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
            {_CHILD_RETURN}
            LIMIT $fetch_limit
            """,
            **params,
        )
        rows = [dict(r) for r in result]

    scored: list[tuple[RetrievedChunk, float]] = []
    for row in rows:
        chunk = _record_to_chunk(row)
        def_text = extract_definition_from_table_chunk(chunk)
        sim = _definition_similarity(definition_phrase, def_text)
        if sim >= 0.55:
            scored.append((chunk, sim))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:limit]]


def lookup_column_chunks(
    client_id: UUID | str,
    column_name: str,
    limit: int = 5,
    *,
    table_name: str | None = None,
    sheet_name: str | None = None,
) -> list[RetrievedChunk]:
    """Fetch column chunks by metadata / body match before vector search."""
    variants = column_name_variants(column_name)
    if not variants:
        return []

    norm_target = normalize_column_identifier(column_name)
    extra_filters = ""
    params: dict = {
        "client_id": str(client_id),
        "variants": variants,
        "variants_lower": [v.lower() for v in variants],
        "norm": norm_target,
        "fetch_limit": limit * 5,
    }
    if table_name:
        extra_filters += " AND toLower(cc.table_name) = toLower($table_name)"
        params["table_name"] = table_name
    if sheet_name:
        extra_filters += " AND cc.sheet_name = $sheet_name"
        params["sheet_name"] = sheet_name

    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            f"""
            MATCH (cc:ChildChunk {{client_id: $client_id}})
            WHERE cc.chunk_type = 'column'
              AND (
                cc.column_name IN $variants
                OR toLower(cc.column_name) IN $variants_lower
                OR replace(toLower(cc.column_name), ' ', '') = $norm
              )
            {extra_filters}
            MATCH (cc)-[:PART_OF]->(parent:Chunk)
            MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
            {_CHILD_RETURN}
            LIMIT $fetch_limit
            """,
            **params,
        )
        rows = [dict(r) for r in result]

    scored: list[tuple[RetrievedChunk, int]] = []
    for row in rows:
        chunk = _record_to_chunk(row)
        score = score_column_chunk(
            column_name,
            chunk,
            required_table_name=table_name,
            required_sheet_name=sheet_name,
        )
        if score >= 0:
            scored.append((chunk, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:limit]]


def score_column_chunk(
    column_name: str,
    chunk: RetrievedChunk,
    *,
    required_table_name: str | None = None,
    required_sheet_name: str | None = None,
) -> int:
    """Rank column chunks: identifier match, table/sheet binding, datatype, definition."""
    body = chunk.child_text or chunk.chunk_text or ""
    body_l = body.lower()
    norm_target = normalize_column_identifier(column_name)
    col_meta = normalize_column_identifier(chunk.column_name or "")
    if col_meta == norm_target:
        score = 300
    elif norm_target in body_l.replace(" ", ""):
        score = 150
    else:
        return -1

    if required_table_name:
        req = required_table_name.strip().lower()
        got = (chunk.table_name or "").strip().lower()
        if got == req:
            score += 500
        else:
            score -= 400

    if required_sheet_name:
        req_s = required_sheet_name.strip().lower()
        got_s = (chunk.sheet_name or "").strip().lower()
        if got_s == req_s:
            score += 200
        elif req_s not in got_s:
            score -= 150

    if "definition:" in body_l:
        def_part = body_l.split("definition:", 1)[-1].split("|")[0].strip()
        if def_part and def_part not in ("", "n/a", "none"):
            score += 80 + min(len(def_part), 80)

    if "datatype:" in body_l:
        dt = body_l.split("datatype:", 1)[-1].split("|")[0].strip()
        if dt and dt not in ("", "n/a", "none"):
            score += 120

    return score


def _score_column_match(column_name: str, chunk: RetrievedChunk) -> int:
    return score_column_chunk(column_name, chunk)
