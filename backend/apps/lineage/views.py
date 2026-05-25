from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

PHASE2_DETAIL = "Phase 2 — SQL Lineage Explorer"


class LineageIngestView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        return Response({"detail": PHASE2_DETAIL}, status=status.HTTP_501_NOT_IMPLEMENTED)


class LineageTableView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, table):
        return Response({"detail": PHASE2_DETAIL}, status=status.HTTP_501_NOT_IMPLEMENTED)


class LineageChatView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        return Response({"detail": PHASE2_DETAIL}, status=status.HTTP_501_NOT_IMPLEMENTED)
