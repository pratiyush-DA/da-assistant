from rest_framework import serializers

from services.neo4j.repositories import ClientRepository
from services.neo4j.repositories.user import UserRepository


class ConversationSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    user_id = serializers.UUIDField(read_only=True)
    client_id = serializers.UUIDField(read_only=True)
    title = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)


class ConversationCreateSerializer(serializers.Serializer):
    user_id = serializers.UUIDField()
    client_id = serializers.UUIDField()
    title = serializers.CharField(max_length=120, required=False, default="New chat")

    def validate_user_id(self, value):
        if not UserRepository().exists(str(value)):
            raise serializers.ValidationError("User not found.")
        return value

    def validate_client_id(self, value):
        if not ClientRepository().exists(str(value)):
            raise serializers.ValidationError("Client not found.")
        return value


class ConversationMessageSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    conversation_id = serializers.UUIDField(read_only=True)
    role = serializers.CharField(read_only=True)
    content = serializers.CharField(read_only=True)
    sources = serializers.ListField(read_only=True)
    created_at = serializers.CharField(read_only=True)
