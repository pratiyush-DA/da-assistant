import redis
from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

from services.neo4j import verify_connectivity


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
