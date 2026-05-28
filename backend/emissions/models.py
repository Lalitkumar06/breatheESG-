import uuid
from django.db import models
from django.contrib.auth.models import User
from core.models import Tenant


class EmissionRecord(models.Model):
    SCOPE_CHOICES = [(1, 'Scope 1'), (2, 'Scope 2'), (3, 'Scope 3')]
    CATEGORY_CHOICES = [
        ('FUEL', 'Fuel'),
        ('ELECTRICITY', 'Electricity'),
        ('FLIGHT', 'Flight'),
        ('HOTEL', 'Hotel'),
        ('GROUND', 'Ground Transport'),
        ('PROCUREMENT', 'Procurement'),
    ]
    STATUS_CHOICES = [
        ('PENDING_REVIEW', 'Pending Review'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('FLAGGED', 'Flagged'),
    ]
    SOURCE_CHOICES = [
        ('SAP', 'SAP'),
        ('UTILITY', 'Utility'),
        ('TRAVEL', 'Corporate Travel'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='emission_records')
    ingestion_job = models.ForeignKey(
        'ingestion.IngestionJob', on_delete=models.CASCADE, related_name='records'
    )
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    scope = models.IntegerField(choices=SCOPE_CHOICES)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)

    # Dates
    activity_date = models.DateField(null=True, blank=True)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)

    # Quantities
    quantity = models.FloatField(null=True, blank=True)
    quantity_unit = models.CharField(max_length=50, blank=True)
    quantity_normalized = models.FloatField(null=True, blank=True)
    quantity_normalized_unit = models.CharField(max_length=20, blank=True, default='')

    # Emissions
    emission_factor = models.FloatField(null=True, blank=True)
    emission_factor_unit = models.CharField(max_length=50, blank=True)
    co2e_kg = models.FloatField(null=True, blank=True)

    # Metadata
    location = models.CharField(max_length=255, blank=True)
    vendor = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    # Raw + Status
    raw_data = models.JSONField(default=dict)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING_REVIEW')
    flag_reason = models.TextField(null=True, blank=True)

    # Review
    reviewed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_records'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_notes = models.TextField(blank=True)

    # Audit
    is_edited = models.BooleanField(default=False)
    edit_history = models.JSONField(default=list)
    is_locked = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-activity_date', '-created_at']

    def __str__(self):
        return f"{self.category} | {self.co2e_kg} kg CO2e | {self.status}"
