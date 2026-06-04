import json
import uuid
from datetime import datetime, timezone

from django.conf import settings

from services.neo4j.driver import get_driver


class ConversationRepository:
    def create(
        self,
        user_id: str,
        client_id: str,
        title: str = "New chat",
    ) -> dict:
        conv_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (u:User {id: $user_id}), (cl:Client {id: $client_id})
                CREATE (conv:Conversation {
                    id: $id,
                    title: $title,
                    created_at: $now,
                    updated_at: $now
                })
                CREATE (u)-[:STARTED]->(conv)
                CREATE (conv)-[:FOR_CLIENT]->(cl)
                """,
                user_id=user_id,
                client_id=client_id,
                id=conv_id,
                title=title,
                now=now,
            )
        return {
            "id": conv_id,
            "user_id": user_id,
            "client_id": client_id,
            "title": title,
            "created_at": now,
            "updated_at": now,
        }

    def list_for_user_client(self, user_id: str, client_id: str) -> list[dict]:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(
                """
                MATCH (conv:Conversation)-[:FOR_CLIENT]->(cl:Client {id: $client_id})
                OPTIONAL MATCH (starter:User)-[:STARTED]->(conv)
                WITH conv, starter
                WHERE starter IS NULL OR starter.id = $user_id
                RETURN conv.id AS id, $user_id AS user_id, $client_id AS client_id,
                       conv.title AS title, conv.created_at AS created_at,
                       conv.updated_at AS updated_at
                ORDER BY conv.updated_at DESC
                """,
                user_id=user_id,
                client_id=client_id,
            )
            return [dict(r) for r in result]

    def get(self, conversation_id: str) -> dict | None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                MATCH (u:User)-[:STARTED]->(conv:Conversation {id: $id})-[:FOR_CLIENT]->(cl:Client)
                RETURN conv.id AS id, u.id AS user_id, cl.id AS client_id,
                       conv.title AS title, conv.created_at AS created_at,
                       conv.updated_at AS updated_at
                """,
                id=conversation_id,
            ).single()
            return dict(record) if record else None

    def touch(self, conversation_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (conv:Conversation {id: $id})
                SET conv.updated_at = $now
                """,
                id=conversation_id,
                now=now,
            )

    def set_title(self, conversation_id: str, title: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (conv:Conversation {id: $id})
                SET conv.title = $title, conv.updated_at = $now
                """,
                id=conversation_id,
                title=title[:120],
                now=now,
            )

    def delete(self, conversation_id: str) -> bool:
        if not self.get(conversation_id):
            return False
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (conv:Conversation {id: $id})
                OPTIONAL MATCH (conv)-[:HAS_MESSAGE]->(m:ChatMessage)
                DETACH DELETE conv, m
                """,
                id=conversation_id,
            )
        return True

    def delete_by_client(self, client_id: str) -> None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                MATCH (conv:Conversation)-[:FOR_CLIENT]->(cl:Client {id: $client_id})
                OPTIONAL MATCH (conv)-[:HAS_MESSAGE]->(m:ChatMessage)
                DETACH DELETE conv, m
                """,
                client_id=client_id,
            )

    def create_message(
        self,
        conversation_id: str,
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
                MATCH (conv:Conversation {id: $conv_id})
                CREATE (m:ChatMessage {
                    id: $id,
                    role: $role,
                    content: $content,
                    sources: $sources,
                    created_at: $created_at
                })
                CREATE (conv)-[:HAS_MESSAGE]->(m)
                SET conv.updated_at = $created_at
                """,
                conv_id=conversation_id,
                id=message_id,
                role=role,
                content=content,
                sources=sources_json,
                created_at=now,
            )
        return {
            "id": message_id,
            "conversation_id": conversation_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "created_at": now,
        }

    def list_messages(self, conversation_id: str, limit: int = 200) -> list[dict]:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(
                """
                MATCH (conv:Conversation {id: $conv_id})-[:HAS_MESSAGE]->(m:ChatMessage)
                RETURN m.id AS id, conv.id AS conversation_id,
                       m.role AS role, m.content AS content,
                       m.sources AS sources, m.created_at AS created_at
                ORDER BY m.created_at ASC
                LIMIT $limit
                """,
                conv_id=conversation_id,
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
                        "conversation_id": record["conversation_id"],
                        "role": record["role"],
                        "content": record["content"],
                        "sources": sources,
                        "created_at": record["created_at"],
                    }
                )
            return messages
