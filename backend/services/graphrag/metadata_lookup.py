"""Direct Neo4j metadata lookups (before vector search)."""

import re
from uuid import UUID

from django.conf import settings

from services.graphrag.context_extractors import catalog_chunk_has_parseable_names
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
) -> RetrievedChunk | None:
    """Load table_definition for an exact table name (case-insensitive)."""
    if not table_name:
        return None
    with get_driver().session(database=settings.NEO4J_DATABASE) as session:
        result = session.run(
            f"""
            MATCH (cc:ChildChunk {{client_id: $client_id, chunk_type: 'table_definition'}})
            WHERE toLower(cc.table_name) = toLower($table_name)
            MATCH (cc)-[:PART_OF]->(parent:Chunk)
            MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
            {_CHILD_RETURN}
            LIMIT 3
            """,
            client_id=str(client_id),
            table_name=table_name,
        )
        rows = [dict(r) for r in result]
    if not rows:
        return None
    return _record_to_chunk(rows[0], score=1.0)


def lookup_column_chunks(
    client_id: UUID | str,
    column_name: str,
    limit: int = 5,
) -> list[RetrievedChunk]:
    """Fetch column chunks by metadata / body match before vector search."""
    variants = column_name_variants(column_name)
    if not variants:
        return []

    norm_target = normalize_column_identifier(column_name)
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
            MATCH (cc)-[:PART_OF]->(parent:Chunk)
            MATCH (parent)<-[:HAS_CHUNK]-(doc:Document)
            {_CHILD_RETURN}
            LIMIT $fetch_limit
            """,
            client_id=str(client_id),
            variants=variants,
            variants_lower=[v.lower() for v in variants],
            norm=norm_target,
            fetch_limit=limit * 5,
        )
        rows = [dict(r) for r in result]

    scored: list[tuple[RetrievedChunk, int]] = []
    for row in rows:
        chunk = _record_to_chunk(row)
        score = score_column_chunk(column_name, chunk)
        if score >= 0:
            scored.append((chunk, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored[:limit]]


def score_column_chunk(column_name: str, chunk: RetrievedChunk) -> int:
    """Rank column chunks: identifier match, datatype, definition length."""
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

    if "definition:" in body_l:
        def_part = body_l.split("definition:", 1)[-1].split("|")[0].strip()
        if def_part and def_part not in ("", "n/a", "none"):
            score += 80 + min(len(def_part), 120)

    if "datatype:" in body_l:
        dt = body_l.split("datatype:", 1)[-1].split("|")[0].strip()
        if dt and dt not in ("", "n/a", "none"):
            score += 120

    return score


def _score_column_match(column_name: str, chunk: RetrievedChunk) -> int:
    return score_column_chunk(column_name, chunk)
