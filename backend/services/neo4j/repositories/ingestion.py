from django.conf import settings

from services.neo4j.driver import get_driver


def _meta(value) -> str | None:
    if value is None or value == "":
        return None
    return str(value)


class IngestionRepository:
    def clear_document_chunks(self, document_id: str) -> None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
                OPTIONAL MATCH (c)<-[:PART_OF]-(cc:ChildChunk)
                DETACH DELETE c, cc
                """,
                doc_id=document_id,
            )

    def write_chunks(
        self,
        document_id: str,
        client_id: str,
        parents: list[dict],
        children: list[dict],
    ) -> None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            for p in parents:
                session.run(
                    """
                    MATCH (d:Document {id: $doc_id})
                    CREATE (chunk:Chunk {
                        id: $id,
                        text: $text,
                        client_id: $client_id,
                        document_id: $doc_id,
                        chunk_index: $chunk_index,
                        page_number: $page_number,
                        section_header: $section_header,
                        token_count: $token_count,
                        chunk_type: $chunk_type,
                        sheet_name: $sheet_name,
                        table_name: $table_name,
                        column_name: $column_name,
                        keywords: $keywords
                    })
                    CREATE (d)-[:HAS_CHUNK]->(chunk)
                    """,
                    doc_id=document_id,
                    client_id=client_id,
                    id=p["id"],
                    text=p["text"],
                    chunk_index=p["chunk_index"],
                    page_number=p.get("page_number"),
                    section_header=p.get("section_header", ""),
                    token_count=p.get("token_count", 0),
                    chunk_type=p.get("chunk_type") or "row",
                    sheet_name=_meta(p.get("sheet_name")),
                    table_name=_meta(p.get("table_name")),
                    column_name=_meta(p.get("column_name")),
                    keywords=p.get("keywords") or "",
                )

            for i in range(len(parents) - 1):
                session.run(
                    """
                    MATCH (c1:Chunk {id: $id1}), (c2:Chunk {id: $id2})
                    CREATE (c1)-[:NEXT {position: $pos}]->(c2)
                    """,
                    id1=parents[i]["id"],
                    id2=parents[i + 1]["id"],
                    pos=i,
                )

            if children:
                session.run(
                    """
                    UNWIND $children AS ch
                    MATCH (parent:Chunk {id: ch.parent_id})
                    CREATE (cc:ChildChunk {
                        id: ch.id,
                        text: ch.text,
                        embedding: ch.embedding,
                        client_id: $client_id,
                        document_id: $doc_id,
                        child_index: ch.child_index,
                        chunk_type: ch.chunk_type,
                        sheet_name: ch.sheet_name,
                        table_name: ch.table_name,
                        column_name: ch.column_name,
                        keywords: ch.keywords
                    })
                    CREATE (cc)-[:PART_OF]->(parent)
                    """,
                    children=children,
                    client_id=client_id,
                    doc_id=document_id,
                )
