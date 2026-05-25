from rest_framework import serializers

from .file_types import validate_upload_filename


class DocumentSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    filename = serializers.CharField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    file_size_bytes = serializers.IntegerField(read_only=True, allow_null=True)
    status = serializers.CharField(read_only=True)
    error_message = serializers.CharField(read_only=True, allow_null=True)
    uploaded_at = serializers.CharField(read_only=True, allow_null=True)
    updated_at = serializers.CharField(read_only=True, allow_null=True)
    chunk_count = serializers.IntegerField(read_only=True, default=0)


class DocumentUploadSerializer(serializers.Serializer):
    client_id = serializers.UUIDField()
    file = serializers.FileField()

    def validate_file(self, value):
        try:
            validate_upload_filename(value.name)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
        return value


class DocumentStatusSerializer(serializers.Serializer):
    status = serializers.CharField()
    error_message = serializers.CharField(allow_null=True)
    chunk_count = serializers.IntegerField()
