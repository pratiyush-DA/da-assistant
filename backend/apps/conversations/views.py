from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from services.neo4j.repositories.conversation import ConversationRepository

from .serializers import (
    ConversationCreateSerializer,
    ConversationMessageSerializer,
    ConversationSerializer,
)


class ConversationListCreateView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request):
        user_id = request.query_params.get("user_id")
        client_id = request.query_params.get("client_id")
        if not user_id or not client_id:
            return Response(
                {"detail": "user_id and client_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        convos = ConversationRepository().list_for_user_client(
            str(user_id), str(client_id)
        )
        return Response(ConversationSerializer(convos, many=True).data)

    def post(self, request):
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conv = ConversationRepository().create(
            user_id=str(serializer.validated_data["user_id"]),
            client_id=str(serializer.validated_data["client_id"]),
            title=serializer.validated_data.get("title") or "New chat",
        )
        return Response(ConversationSerializer(conv).data, status=status.HTTP_201_CREATED)


class ConversationMessagesView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, pk):
        repo = ConversationRepository()
        if not repo.get(str(pk)):
            return Response(status=status.HTTP_404_NOT_FOUND)
        messages = repo.list_messages(str(pk))
        return Response(ConversationMessageSerializer(messages, many=True).data)


class ConversationDetailView(APIView):
    authentication_classes = []
    permission_classes = []

    def delete(self, request, pk):
        if ConversationRepository().delete(str(pk)):
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(status=status.HTTP_404_NOT_FOUND)
