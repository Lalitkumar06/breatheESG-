from django.contrib.auth.models import User
from rest_framework import serializers
from .models import Tenant, AuditLog


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ['id', 'name', 'slug', 'created_at']


class UserSerializer(serializers.ModelSerializer):
    tenant = serializers.SerializerMethodField()
    is_superuser = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_superuser', 'tenant']

    def get_tenant(self, obj):
        profile = getattr(obj, 'userprofile', None)
        if profile and profile.tenant:
            return TenantSerializer(profile.tenant).data
        return None


class AuditLogSerializer(serializers.ModelSerializer):
    performed_by_username = serializers.CharField(source='performed_by.username', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'action', 'performed_by', 'performed_by_username',
            'timestamp', 'before_state', 'after_state', 'notes',
        ]
