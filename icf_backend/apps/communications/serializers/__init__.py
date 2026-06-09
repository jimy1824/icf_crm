from rest_framework import serializers
from apps.communications.models import (
    CallLog,
    Communication,
    ConsentPreference,
    DeliverabilityEvent,
    MailboxConnection,
    Meeting,
    SuppressionRecord,
    TriggerDomain,
)


class MailboxConnectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = MailboxConnection
        fields = [
            'id', 'provider', 'email_address', 'status',
            'last_synced_at', 'token_expires_at', 'created_at',
        ]
        read_only_fields = ['id', 'status', 'last_synced_at', 'created_at']


class MailboxConnectSerializer(serializers.Serializer):
    provider = serializers.ChoiceField(choices=MailboxConnection.PROVIDER_CHOICES)
    email_address = serializers.EmailField()
    access_token_enc = serializers.CharField(write_only=True)
    refresh_token_enc = serializers.CharField(write_only=True)
    token_expires_at = serializers.DateTimeField()


class TriggerDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = TriggerDomain
        fields = ['id', 'domain', 'is_active', 'created_at']
        read_only_fields = ['id', 'created_at']


class CommunicationCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = ['duration_seconds', 'outcome', 'notes', 'recording_consent_captured']


class CommunicationSerializer(serializers.ModelSerializer):
    lead_name = serializers.SerializerMethodField()
    sent_by_name = serializers.SerializerMethodField()
    body_preview = serializers.SerializerMethodField()
    call_log = CommunicationCallLogSerializer(read_only=True)

    def get_lead_name(self, obj):
        if obj.lead_id:
            return obj.lead.full_name if hasattr(obj.lead, 'full_name') else (
                f"{obj.lead.first_name} {obj.lead.last_name}".strip()
            )
        return None

    def get_sent_by_name(self, obj):
        if obj.sent_by_id:
            return obj.sent_by.get_full_name()
        return None

    def get_body_preview(self, obj):
        if obj.body:
            return obj.body[:200]
        return None

    class Meta:
        model = Communication
        fields = [
            'id', 'channel', 'direction', 'status', 'subject',
            'body', 'body_preview',
            'lead', 'lead_name', 'sent_by', 'sent_by_name',
            'external_id', 'is_reply', 'scheduled_at', 'sent_at', 'created_at',
            'call_log',
        ]
        read_only_fields = ['id', 'lead_name', 'sent_by_name', 'body_preview', 'call_log', 'created_at']


class CallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CallLog
        fields = [
            'id', 'communication', 'duration_seconds', 'outcome',
            'recording_consent_captured', 'ringcentral_call_id', 'notes',
        ]
        read_only_fields = ['id']


class LogCallSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField(required=False)
    duration_seconds = serializers.IntegerField(min_value=0, default=0)
    outcome = serializers.ChoiceField(choices=CallLog.OUTCOME_CHOICES, required=False, default='')
    notes = serializers.CharField(required=False, default='')
    recording_consent_captured = serializers.BooleanField(default=False)
    recording_ref = serializers.CharField(required=False, default='')
    ringcentral_call_id = serializers.CharField(required=False, default='')

    def validate(self, data):
        if not data.get('lead_id'):
            raise serializers.ValidationError("lead_id is required.")
        return data


class UpdateCallOutcomeSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=CallLog.OUTCOME_CHOICES)
    notes = serializers.CharField(required=False, default='')


class MeetingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Meeting
        fields = [
            'id', 'advisor', 'lead', 'scheduled_at', 'recipient_timezone',
            'zoom_link', 'zoom_meeting_id', 'calendar_provider', 'calendar_event_id',
            'outcome', 'notes', 'reminder_sent', 'created_at',
        ]
        read_only_fields = ['id', 'reminder_sent', 'created_at']


class ScheduleMeetingSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField(required=False)
    scheduled_at = serializers.DateTimeField()
    recipient_timezone = serializers.CharField(max_length=60, default='UTC')
    zoom_link = serializers.URLField(required=False, default='')
    zoom_meeting_id = serializers.CharField(max_length=100, required=False, default='')
    calendar_provider = serializers.CharField(max_length=20, required=False, default='')
    calendar_event_id = serializers.CharField(max_length=255, required=False, default='')
    notes = serializers.CharField(required=False, default='')

    def validate(self, data):
        if not data.get('lead_id'):
            raise serializers.ValidationError("lead_id is required.")
        return data


class RecordMeetingOutcomeSerializer(serializers.Serializer):
    outcome = serializers.CharField(max_length=100)
    notes = serializers.CharField(required=False, default='')


class SuppressionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuppressionRecord
        fields = ['id', 'email', 'phone', 'channel', 'reason', 'created_at']
        read_only_fields = ['id', 'created_at']


class AddSuppressionSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False, default='')
    phone = serializers.CharField(max_length=30, required=False, default='')
    channel = serializers.ChoiceField(choices=SuppressionRecord.CHANNEL_CHOICES)

    def validate(self, data):
        if not data.get('email') and not data.get('phone'):
            raise serializers.ValidationError("Either email or phone is required.")
        return data


class ConsentPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentPreference
        fields = [
            'id', 'lead', 'channel', 'purpose', 'state',
            'source', 'ip_address', 'is_under_legal_hold', 'created_at',
        ]
        read_only_fields = ['id', 'is_under_legal_hold', 'created_at']


class RecordConsentSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField(required=False)
    channel = serializers.ChoiceField(choices=ConsentPreference.CHANNEL_CHOICES)
    purpose = serializers.CharField(max_length=100)
    state = serializers.ChoiceField(choices=ConsentPreference.STATE_CHOICES)
    source = serializers.CharField(max_length=200)
    ip_address = serializers.IPAddressField(required=False)

    def validate(self, data):
        if not data.get('lead_id'):
            raise serializers.ValidationError("lead_id is required.")
        return data


class SendMessageSerializer(serializers.Serializer):
    """POST /communications/send/ — advisor sends a message to a lead."""
    lead_id = serializers.IntegerField()
    channel = serializers.ChoiceField(choices=Communication.CHANNEL_CHOICES)
    subject = serializers.CharField(max_length=500, allow_blank=True, default='')
    body = serializers.CharField(max_length=50000)

    def validate(self, data):
        if not data.get('lead_id'):
            raise serializers.ValidationError("lead_id is required.")
        return data
