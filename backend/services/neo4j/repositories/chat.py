import json
import uuid
from datetime import datetime, timezone

from django.conf import settings

from services.neo4j.driver import get_driver


class ChatRepository:
    def create_message(
        self,
        client_id: str,
        role: str,
        content: str,
        sources: list[dict] | None = None,
    ) -> dict:
        message_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        sources_json = json.dumps(sources or [])
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (c:Client {id: $client_id})
                CREATE (m:ChatMessage {
                    id: $id,
                    role: $role,
                    content: $content,
                    sources: $sources,
                    created_at: $created_at
                })
                CREATE (c)-[:HAS_MESSAGE]->(m)
                """,
                client_id=client_id,
                id=message_id,
                role=role,
                content=content,
                sources=sources_json,
                created_at=now,
            )
        return {
            "id": message_id,
            "client": client_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "created_at": now,
        }

    def list_by_client(self, client_id: str, limit: int = 100) -> list[dict]:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(
                """
                MATCH (c:Client {id: $client_id})-[:HAS_MESSAGE]->(m:ChatMessage)
                RETURN m.id AS id,
                       $client_id AS client,
                       m.role AS role,
                       m.content AS content,
                       m.sources AS sources,
                       m.created_at AS created_at
                ORDER BY m.created_at ASC
                LIMIT $limit
                """,
                client_id=client_id,
                limit=limit,
            )
            messages = []
            for record in result:
                sources_raw = record["sources"]
                if isinstance(sources_raw, str):
                    try:
                        sources = json.loads(sources_raw)
                    except json.JSONDecodeError:
                        sources = []
                else:
                    sources = sources_raw or []
                messages.append(
                    {
                        "id": record["id"],
                        "client": record["client"],
                        "role": record["role"],
                        "content": record["content"],
                        "sources": sources,
                        "created_at": record["created_at"],
                    }
                )
            return messages
