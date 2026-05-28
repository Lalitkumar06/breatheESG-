from django.contrib.auth.models import User
from django.db import models
from core.models import Tenant


class UserProfile(models.Model):
    """Extends Django's User to link them to a Tenant."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} — {self.tenant}"
