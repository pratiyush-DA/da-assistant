import redis
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from services.neo4j import verify_connectivity
from services.neo4j.repositories import PlatformStatsRepository


class HealthView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        neo4j_ok = False
        redis_ok = False
        try:
            verify_connectivity()
            neo4j_ok = True
        except Exception:
            pass
        try:
            r = redis.from_url(settings.REDIS_URL)
            redis_ok = r.ping()
        except Exception:
            pass
        status = "ok" if neo4j_ok and redis_ok else "degraded"
        return Response(
            {
                "status": status,
                "neo4j": neo4j_ok,
                "redis": redis_ok,
            }
        )


class PlatformStatsView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        stats = PlatformStatsRepository().get_platform_stats()
        return Response(
            {
                "client_count": stats["client_count"],
                "documents_ready": stats["documents_ready"],
                "user_count": stats["user_count"],
                "documents_total": stats["documents_total"],
                "documents_processing": stats["documents_processing"],
                "conversation_count": stats["conversation_count"],
            }
        )
