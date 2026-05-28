from rest_framework import serializers
from .models import DataSource, IngestionJob


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = ['id', 'source_type', 'display_name', 'created_at']


class IngestionJobSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    success_count = serializers.IntegerField(read_only=True)
    record_summary = serializers.SerializerMethodField()

    class Meta:
        model = IngestionJob
        fields = [
            'id', 'tenant', 'data_source', 'uploaded_by', 'uploaded_by_username',
            'uploaded_at', 'filename', 'source_type', 'status',
            'row_count', 'error_count', 'success_count', 'error_details',
            'processing_log', 'record_summary',
        ]
        read_only_fields = ['id', 'tenant', 'uploaded_by', 'uploaded_at', 'status']

    def get_record_summary(self, obj):
        from emissions.models import EmissionRecord
        records = EmissionRecord.objects.filter(ingestion_job=obj)
        return {
            'total': records.count(),
            'pending': records.filter(status='PENDING_REVIEW').count(),
            'approved': records.filter(status='APPROVED').count(),
            'rejected': records.filter(status='REJECTED').count(),
            'flagged': records.filter(status='FLAGGED').count(),
        }
