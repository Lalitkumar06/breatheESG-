from rest_framework import serializers
from .models import EmissionRecord
from core.serializers import AuditLogSerializer


class EmissionRecordSerializer(serializers.ModelSerializer):
    reviewed_by_username = serializers.CharField(source='reviewed_by.username', read_only=True)
    scope_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'tenant', 'ingestion_job', 'source_type', 'scope', 'scope_label', 'category',
            'activity_date', 'period_start', 'period_end',
            'quantity', 'quantity_unit', 'quantity_normalized', 'quantity_normalized_unit',
            'emission_factor', 'emission_factor_unit', 'co2e_kg',
            'location', 'vendor', 'description',
            'raw_data', 'status', 'status_display', 'flag_reason',
            'reviewed_by', 'reviewed_by_username', 'reviewed_at', 'review_notes',
            'is_edited', 'edit_history', 'is_locked',
            'created_at', 'updated_at',
        ]
        read_only_fields = [
            'id', 'tenant', 'ingestion_job', 'source_type', 'scope', 'raw_data',
            'reviewed_by', 'reviewed_at', 'is_locked', 'created_at', 'updated_at',
        ]

    def get_scope_label(self, obj):
        return {1: 'Scope 1', 2: 'Scope 2', 3: 'Scope 3'}.get(obj.scope, 'Unknown')

    def update(self, instance, validated_data):
        if instance.is_locked:
            raise serializers.ValidationError("Cannot edit a locked record.")

        # Track edit history
        before = {
            'quantity': instance.quantity,
            'quantity_unit': instance.quantity_unit,
            'activity_date': str(instance.activity_date),
            'co2e_kg': instance.co2e_kg,
        }
        instance = super().update(instance, validated_data)
        after = {
            'quantity': instance.quantity,
            'quantity_unit': instance.quantity_unit,
            'activity_date': str(instance.activity_date),
            'co2e_kg': instance.co2e_kg,
        }
        instance.is_edited = True
        instance.edit_history = instance.edit_history + [{
            'before': before,
            'after': after,
            'timestamp': str(instance.updated_at),
        }]
        instance.save(update_fields=['is_edited', 'edit_history'])
        return instance


class EmissionRecordListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list view."""
    scope_label = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = EmissionRecord
        fields = [
            'id', 'source_type', 'scope', 'scope_label', 'category',
            'activity_date', 'quantity_normalized', 'quantity_normalized_unit',
            'co2e_kg', 'status', 'status_display', 'flag_reason', 'location', 'is_locked',
        ]

    def get_scope_label(self, obj):
        return {1: 'Scope 1', 2: 'Scope 2', 3: 'Scope 3'}.get(obj.scope, 'Unknown')
