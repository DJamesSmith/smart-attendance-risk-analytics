from rest_framework import serializers
from .models import User


class UserOutputSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "first_name", "last_name", "email", "role", "email_verified")
        read_only_fields = fields


class APIResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField()
    data = serializers.JSONField(allow_null=True)
    errors = serializers.JSONField(allow_null=True)