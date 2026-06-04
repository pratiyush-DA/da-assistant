import re
import uuid
from datetime import datetime, timezone

from django.conf import settings

from services.graphrag.client_catalog import clear_sheet_index_cache
from services.neo4j.driver import get_driver
from services.neo4j.repositories.conversation import ConversationRepository
from services.neo4j.repositories.document import DocumentRepository
from services.storage import get_storage_backend


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "client"


class ClientRepository:
    def list_all(self) -> list[dict]:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(
                """
                MATCH (c:Client)
                RETURN c.id AS id, c.name AS name, c.slug AS slug, c.created_at AS created_at
                ORDER BY c.name
                """
            )
            return [dict(record) for record in result]

    def get(self, client_id: str) -> dict | None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                MATCH (c:Client {id: $id})
                RETURN c.id AS id, c.name AS name, c.slug AS slug, c.created_at AS created_at
                """,
                id=client_id,
            ).single()
            return dict(record) if record else None

    def exists(self, client_id: str) -> bool:
        return self.get(client_id) is not None

    def create(self, name: str) -> dict:
        client_id = str(uuid.uuid4())
        slug = _slugify(name)
        now = datetime.now(timezone.utc).isoformat()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                CREATE (c:Client {
                    id: $id,
                    name: $name,
                    slug: $slug,
                    created_at: $created_at
                })
                """,
                id=client_id,
                name=name,
                slug=slug,
                created_at=now,
            )
        return {"id": client_id, "name": name, "slug": slug, "created_at": now}

    def delete_cascade(self, client_id: str) -> bool:
        if not self.exists(client_id):
            return False

        doc_repo = DocumentRepository()
        storage = get_storage_backend()
        for doc in doc_repo.list_by_client(client_id):
            if doc.get("file_path"):
                storage.delete(doc["file_path"])
            doc_repo.delete_cascade(doc["id"])

        ConversationRepository().delete_by_client(client_id)

        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (cl:Client {id: $id})
                OPTIONAL MATCH (cl)-[:HAS_MESSAGE]->(m:ChatMessage)
                DETACH DELETE m, cl
                """,
                id=client_id,
            )

        clear_sheet_index_cache(client_id)
        return True
