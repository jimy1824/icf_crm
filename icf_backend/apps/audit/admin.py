from django.contrib import admin
from .models import AuditEvent


@admin.register(AuditEvent)
class AuditEventAdmin(admin.ModelAdmin):
    list_display = ('action', 'entity_type', 'entity_id', 'actor', 'tenant', 'timestamp')
    list_filter = ('action', 'entity_type')
    search_fields = ('entity_id', 'action')
    readonly_fields = (
        'id', 'tenant', 'actor', 'action', 'entity_type', 'entity_id',
        'before_state', 'after_state', 'ip_address', 'timestamp',
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
