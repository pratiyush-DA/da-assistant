import uuid
from datetime import datetime, timezone

from django.conf import settings

from services.neo4j.driver import get_driver


class UserRepository:
    def list_all(self, query: str | None = None) -> list[dict]:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            if query:
                q = query.strip().lower()
                result = session.run(
                    """
                    MATCH (u:User)
                    WHERE toLower(u.email) CONTAINS $q OR toLower(u.display_name) CONTAINS $q
                    RETURN u.id AS id, u.email AS email, u.display_name AS display_name,
                           u.external_id AS external_id, u.created_at AS created_at,
                           u.updated_at AS updated_at
                    ORDER BY u.display_name ASC
                    LIMIT 100
                    """,
                    q=q,
                )
            else:
                result = session.run(
                    """
                    MATCH (u:User)
                    RETURN u.id AS id, u.email AS email, u.display_name AS display_name,
                           u.external_id AS external_id, u.created_at AS created_at,
                           u.updated_at AS updated_at
                    ORDER BY u.display_name ASC
                    """
                )
            return [dict(r) for r in result]

    def search(self, query: str, limit: int = 20) -> list[dict]:
        q = query.strip().lower()
        if not q:
            return self.list_all()[:limit]
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            result = session.run(
                """
                MATCH (u:User)
                WHERE toLower(u.email) CONTAINS $q OR toLower(u.display_name) CONTAINS $q
                RETURN u.id AS id, u.email AS email, u.display_name AS display_name,
                       u.external_id AS external_id, u.created_at AS created_at,
                       u.updated_at AS updated_at,
                       CASE
                         WHEN toLower(u.email) STARTS WITH $q THEN 0
                         WHEN toLower(u.display_name) STARTS WITH $q THEN 1
                         ELSE 2
                       END AS rank
                ORDER BY rank ASC, u.display_name ASC
                LIMIT $limit
                """,
                q=q,
                limit=limit,
            )
            return [dict(r) for r in result]

    def get(self, user_id: str) -> dict | None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                MATCH (u:User {id: $id})
                RETURN u.id AS id, u.email AS email, u.display_name AS display_name,
                       u.external_id AS external_id, u.created_at AS created_at,
                       u.updated_at AS updated_at
                """,
                id=user_id,
            ).single()
            return dict(record) if record else None

    def exists(self, user_id: str) -> bool:
        return self.get(user_id) is not None

    def get_by_email(self, email: str) -> dict | None:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                MATCH (u:User {email: $email})
                RETURN u.id AS id, u.email AS email, u.display_name AS display_name,
                       u.external_id AS external_id, u.created_at AS created_at,
                       u.updated_at AS updated_at
                """,
                email=email.lower(),
            ).single()
            return dict(record) if record else None

    def create(
        self,
        email: str,
        display_name: str,
        external_id: str | None = None,
    ) -> dict:
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        email_norm = email.strip().lower()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            session.run(
                """
                CREATE (u:User {
                    id: $id,
                    email: $email,
                    display_name: $display_name,
                    external_id: $external_id,
                    created_at: $now,
                    updated_at: $now
                })
                """,
                id=user_id,
                email=email_norm,
                display_name=display_name.strip(),
                external_id=external_id,
                now=now,
            )
        return {
            "id": user_id,
            "email": email_norm,
            "display_name": display_name.strip(),
            "external_id": external_id,
            "created_at": now,
            "updated_at": now,
        }

    def update(
        self,
        user_id: str,
        *,
        email: str | None = None,
        display_name: str | None = None,
    ) -> dict | None:
        now = datetime.now(timezone.utc).isoformat()
        sets = ["u.updated_at = $now"]
        params: dict = {"id": user_id, "now": now}
        if email is not None:
            sets.append("u.email = $email")
            params["email"] = email.strip().lower()
        if display_name is not None:
            sets.append("u.display_name = $display_name")
            params["display_name"] = display_name.strip()
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                f"""
                MATCH (u:User {{id: $id}})
                SET {", ".join(sets)}
                RETURN u.id AS id, u.email AS email, u.display_name AS display_name,
                       u.external_id AS external_id, u.created_at AS created_at,
                       u.updated_at AS updated_at
                """,
                **params,
            ).single()
            return dict(record) if record else None
