from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class Tenant(models.Model):
    import uuid as _uuid
    id = models.UUIDField(primary_key=True, default=_uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class UserProfile(models.Model):
    """Links a Django User to a Tenant."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} — {self.tenant}"


class AuditLog(models.Model):
    import uuid as _uuid
    id = models.UUIDField(primary_key=True, default=_uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name='audit_logs')
    record = models.ForeignKey(
        'emissions.EmissionRecord',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
    )
    action = models.CharField(max_length=100)
    performed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='audit_logs',
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    notes = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.action} on record {self.record_id} by {self.performed_by}"
