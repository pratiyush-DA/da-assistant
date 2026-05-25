from rest_framework import serializers

from services.neo4j.repositories import ClientRepository
from services.neo4j.repositories.conversation import ConversationRepository
from services.neo4j.repositories.user import UserRepository


class ChatRequestSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    user_id = serializers.UUIDField()
    conversation_id = serializers.UUIDField(required=False, allow_null=True)
    message = serializers.CharField(max_length=16000)

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
        return attrs


class ChatMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    conversation_id = serializers.UUIDField(read_only=True, required=False)
    client = serializers.UUIDField(read_only=True, required=False)
    role = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    sources = serializers.ListField(read_only=True)
    created_at = serializers.CharField(read_only=True)
