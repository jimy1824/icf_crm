from django.contrib import admin
from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'recipient', 'tenant', 'is_read', 'created_at')
    list_filter = ('event_type', 'is_read')
    readonly_fields = ('id', 'created_at')
