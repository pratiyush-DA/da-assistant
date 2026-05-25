from rest_framework import serializers


class ClientSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    name = serializers.CharField(max_length=255)
    slug = serializers.CharField(read_only=True)
    created_at = serializers.CharField(read_only=True)
