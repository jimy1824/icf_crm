from django.contrib import admin
from .models import Lead, KanbanCard


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'tenant', 'status', 'source', 'created_at')
    list_filter = ('status', 'source', 'opted_out', 'is_suppressed')
    search_fields = ('first_name', 'last_name', 'email')
    readonly_fields = ('id', 'created_at', 'updated_at')
    raw_id_fields = ('tenant',)


@admin.register(KanbanCard)
class KanbanCardAdmin(admin.ModelAdmin):
    list_display = ('lead', 'stage', 'position', 'updated_at')
    list_filter = ('stage',)
    readonly_fields = ('id', 'updated_at')
