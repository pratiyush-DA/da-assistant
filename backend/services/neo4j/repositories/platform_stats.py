from django.conf import settings

from services.neo4j.driver import get_driver


class PlatformStatsRepository:
    def get_platform_stats(self) -> dict:
        with get_driver().session(database=settings.NEO4J_DATABASE) as session:
            record = session.run(
                """
                OPTIONAL MATCH (c:Client)
                WITH count(c) AS client_count
                OPTIONAL MATCH (d:Document)
                WITH client_count,
                     count(d) AS documents_total,
                     coalesce(sum(CASE WHEN d.status = 'ready' THEN 1 ELSE 0 END), 0)
                         AS documents_ready,
                     coalesce(sum(CASE WHEN d.status = 'processing' THEN 1 ELSE 0 END), 0)
                         AS documents_processing
                OPTIONAL MATCH (u:User)
                WITH client_count, documents_total, documents_ready, documents_processing,
                     count(u) AS user_count
                OPTIONAL MATCH (conv:Conversation)
                RETURN client_count,
                       documents_ready,
                       user_count,
                       documents_total,
                       documents_processing,
                       count(conv) AS conversation_count
                """
            ).single()
            if not record:
                return {
                    "client_count": 0,
                    "documents_ready": 0,
                    "user_count": 0,
                    "documents_total": 0,
                    "documents_processing": 0,
                    "conversation_count": 0,
                }
            return {
                "client_count": int(record["client_count"]),
                "documents_ready": int(record["documents_ready"]),
                "user_count": int(record["user_count"]),
                "documents_total": int(record["documents_total"]),
                "documents_processing": int(record["documents_processing"]),
                "conversation_count": int(record["conversation_count"]),
            }
