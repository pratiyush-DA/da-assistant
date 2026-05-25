import re
import uuid
from datetime import datetime, timezone

from django.conf import settings

from services.neo4j.driver import get_driver


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
