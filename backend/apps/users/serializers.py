from rest_framework import serializers

from .validators import validate_data_axle_email


class UserSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField()
    display_name = serializers.CharField(max_length=200)
    external_id = serializers.CharField(required=False, allow_null=True, read_only=True)
    created_at = serializers.CharField(read_only=True)
    updated_at = serializers.CharField(read_only=True)

    def validate_email(self, value):
        try:
            return validate_data_axle_email(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc


class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    display_name = serializers.CharField(max_length=200, required=False)

    def validate_email(self, value):
        if value is None:
            return value
        try:
            return validate_data_axle_email(value)
        except ValueError as exc:
            raise serializers.ValidationError(str(exc)) from exc
