from rest_framework import serializers

from services.neo4j.repositories import ClientRepository, DocumentRepository
from services.neo4j.repositories.conversation import ConversationRepository
from services.neo4j.repositories.user import UserRepository


class ChatRequestSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(max_length=16000)
    document_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        allow_empty=True,
        max_length=50,
    )
    focus_document_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_client_id(self, value):
        if not ClientRepository().exists(str(value)):
            raise serializers.ValidationError("Client not found.")
        return value

    def validate_user_id(self, value):
        if not UserRepository().exists(str(value)):
            raise serializers.ValidationError("User not found.")
        return value

    def validate(self, attrs):
        conv_id = attrs.get("conversation_id")
        if conv_id:
            conv = ConversationRepository().get(str(conv_id))
            if not conv:
                raise serializers.ValidationError(
                    {"conversation_id": "Conversation not found."}
                )
            if str(conv["client_id"]) != str(attrs["client_id"]):
                raise serializers.ValidationError(
                    {"conversation_id": "Conversation does not match client."}
                )
            if str(conv["user_id"]) != str(attrs["user_id"]):
                raise serializers.ValidationError(
                    {"conversation_id": "Conversation does not match user."}
                )
        client_id = str(attrs["client_id"])
        doc_repo = DocumentRepository()
        for doc_id in attrs.get("document_ids") or []:
            if not doc_repo.belongs_to_client(str(doc_id), client_id):
                raise serializers.ValidationError(
                    {"document_ids": f"Document {doc_id} not found for this client."}
                )
        focus = attrs.get("focus_document_id")
        if focus and not doc_repo.belongs_to_client(str(focus), client_id):
            raise serializers.ValidationError(
                {"focus_document_id": "Document not found for this client."}
            )
        return attrs


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    conversation_id = serializers.UUIDField(read_only=True, required=False)
    client = serializers.UUIDField(read_only=True, required=False)
    role = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    sources = serializers.ListField(read_only=True)
    created_at = serializers.CharField(read_only=True)
