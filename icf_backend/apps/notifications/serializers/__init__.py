from rest_framework import serializers
from apps.notifications.models import Notification

# Human-readable labels for each event_type
_EVENT_LABELS = {
    'goal.off_track':       'Goal Off Track',
    'goal.achieved':        'Goal Achieved',
    'lead.assigned':        'Lead Assigned',
    'lead.stage_changed':   'Lead Stage Updated',
    'message.received':     'New Message',
    'meeting.scheduled':    'Meeting Scheduled',
    'meeting.reminder':     'Meeting Reminder',
    'document.uploaded':    'Document Uploaded',
    'document.approved':    'Document Approved',
    'campaign.enrolled':    'Campaign Enrolled',
}


class NotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body  = serializers.SerializerMethodField()

    def get_title(self, obj):
        return _EVENT_LABELS.get(obj.event_type, obj.event_type.replace('.', ' ').replace('_', ' ').title())

    def get_body(self, obj):
        return f"{obj.entity_type.replace('_', ' ').title()} · {obj.entity_id}" if obj.entity_id else None

    class Meta:
        model = Notification
        fields = [
            'id', 'event_type', 'entity_type', 'entity_id',
            'channels', 'is_read', 'title', 'body', 'created_at',
        ]
        read_only_fields = ['id', 'event_type', 'entity_type', 'entity_id', 'channels', 'title', 'body', 'created_at']
