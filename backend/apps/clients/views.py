from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.neo4j.repositories import ClientRepository

from .serializers import ClientSerializer


class ClientListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        repo = ClientRepository()
        clients = repo.list_all()
        serializer = ClientSerializer(clients, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        repo = ClientRepository()
        client = repo.create(name=serializer.validated_data["name"])
        return Response(ClientSerializer(client).data, status=status.HTTP_201_CREATED)
