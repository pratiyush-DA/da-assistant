import uuid
from datetime import datetime, timezone

from django.conf import settings

from services.neo4j.driver import get_driver


class DocumentRepository:
    def list_by_client(self, client_id: str) -> list[dict]:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(
                """
                MATCH (cl:Client {id: $client_id})-[:OWNS]->(d:Document)
                OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
                RETURN d.id AS id,
                       d.filename AS filename,
                       d.file_type AS file_type,
                       d.file_size_bytes AS file_size_bytes,
                       d.status AS status,
                       d.error_message AS error_message,
                       d.uploaded_at AS uploaded_at,
                       d.updated_at AS updated_at,
                       count(c) AS chunk_count
                ORDER BY d.uploaded_at DESC
                """,
                client_id=client_id,
            )
            rows = []
            for record in result:
                rows.append(
                    {
                        "id": record["id"],
                        "filename": record["filename"],
                        "file_type": record["file_type"],
                        "file_size_bytes": record["file_size_bytes"],
                        "status": record["status"],
                        "error_message": record["error_message"],
                        "uploaded_at": record["uploaded_at"],
                        "updated_at": record["updated_at"],
                        "chunk_count": record["chunk_count"] or 0,
                    }
                )
            return rows

    def get(self, document_id: str) -> dict | None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                MATCH (d:Document {id: $id})
                OPTIONAL MATCH (cl:Client)-[:OWNS]->(d)
                OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
                RETURN d.id AS id,
                       d.filename AS filename,
                       d.file_type AS file_type,
                       d.file_size_bytes AS file_size_bytes,
                       d.status AS status,
                       d.error_message AS error_message,
                       d.file_path AS file_path,
                       d.uploaded_at AS uploaded_at,
                       d.updated_at AS updated_at,
                       cl.id AS client_id,
                       count(c) AS chunk_count
                """,
                id=document_id,
            ).single()
            if not record:
                return None
            return dict(record)

    def create(
        self,
        client_id: str,
        filename: str,
        file_type: str,
        file_path: str,
        file_size_bytes: int | None = None,
    ) -> dict:
        document_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (cl:Client {id: $client_id})
                CREATE (d:Document {
                    id: $id,
                    filename: $filename,
                    file_type: $file_type,
                    file_path: $file_path,
                    file_size_bytes: $file_size_bytes,
                    status: 'processing',
                    error_message: null,
                    uploaded_at: $now,
                    updated_at: $now
                })
                CREATE (cl)-[:OWNS]->(d)
                """,
                client_id=client_id,
                id=document_id,
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                now=now,
            )
        return {
            "id": document_id,
            "filename": filename,
            "file_type": file_type,
            "file_size_bytes": file_size_bytes,
            "file_path": file_path,
            "status": "processing",
            "error_message": None,
            "uploaded_at": now,
            "updated_at": now,
            "chunk_count": 0,
        }

    def update_file(
        self,
        document_id: str,
        filename: str,
        file_type: str,
        file_path: str,
        file_size_bytes: int | None = None,
    ) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                MATCH (d:Document {id: $id})
                SET d.filename = $filename,
                    d.file_type = $file_type,
                    d.file_path = $file_path,
                    d.file_size_bytes = $file_size_bytes,
                    d.status = 'processing',
                    d.error_message = null,
                    d.updated_at = $now
                RETURN d.id AS id, d.filename AS filename, d.file_type AS file_type,
                       d.status AS status, d.error_message AS error_message,
                       d.uploaded_at AS uploaded_at, d.updated_at AS updated_at
                """,
                id=document_id,
                filename=filename,
                file_type=file_type,
                file_path=file_path,
                file_size_bytes=file_size_bytes,
                now=now,
            ).single()
            return dict(record) if record else None

    def set_status(
        self,
        document_id: str,
        status: str,
        error_message: str | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (d:Document {id: $id})
                SET d.status = $status,
                    d.error_message = $error_message,
                    d.updated_at = $now
                """,
                id=document_id,
                status=status,
                error_message=error_message,
                now=now,
            )

    def delete_cascade(self, document_id: str) -> bool:
        if not self.get(document_id):
            return False
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (d:Document {id: $id})
                OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
                OPTIONAL MATCH (c)<-[:PART_OF]-(cc:ChildChunk)
                DETACH DELETE d, c, cc
                """,
                id=document_id,
            )
        return True

    def chunk_count(self, document_id: str) -> int:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                MATCH (d:Document {id: $id})-[:HAS_CHUNK]->(c:Chunk)
                RETURN count(c) AS cnt
                """,
                id=document_id,
            ).single()
            return int(record["cnt"]) if record else 0
