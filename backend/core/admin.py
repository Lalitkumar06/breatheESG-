from django.contrib import admin
from .models import Tenant, AuditLog


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'created_at']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['action', 'record', 'performed_by', 'timestamp']
    list_filter = ['action', 'tenant']
    readonly_fields = ['before_state', 'after_state', 'timestamp']
