from django.contrib import admin
from .models import Communication, Meeting


@admin.register(Communication)
class CommunicationAdmin(admin.ModelAdmin):
    list_display = ('channel', 'direction', 'status', 'tenant', 'sent_at', 'created_at')
    list_filter = ('channel', 'direction', 'status')
    search_fields = ('external_id', 'subject')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(Meeting)
class MeetingAdmin(admin.ModelAdmin):
    list_display = ('advisor', 'scheduled_at', 'outcome', 'tenant')
    list_filter = ('outcome',)
    readonly_fields = ('id', 'created_at', 'updated_at')
