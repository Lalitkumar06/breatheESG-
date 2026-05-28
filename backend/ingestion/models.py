import uuid
from django.db import models
from django.contrib.auth.models import User
from core.models import Tenant


class DataSource(models.Model):
    SOURCE_CHOICES = [
        ('SAP', 'SAP (Fuel & Procurement)'),
        ('UTILITY', 'Utility (Electricity)'),
        ('TRAVEL', 'Corporate Travel'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='data_sources')
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    display_name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.display_name} ({self.source_type})"


def ingestion_upload_path(instance, filename):
    return f'raw_uploads/{instance.tenant.slug}/{filename}'


class IngestionJob(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETE', 'Complete'),
        ('FAILED', 'Failed'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='ingestion_jobs')
    data_source = models.ForeignKey(
        DataSource, on_delete=models.CASCADE, related_name='jobs', null=True, blank=True
    )
    uploaded_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name='ingestion_jobs'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    filename = models.CharField(max_length=500)
    source_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    row_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    raw_file = models.FileField(upload_to=ingestion_upload_path, null=True, blank=True)
    error_details = models.JSONField(default=list, blank=True)
    processing_log = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.filename} [{self.status}]"

    @property
    def success_count(self):
        return self.row_count - self.error_count
