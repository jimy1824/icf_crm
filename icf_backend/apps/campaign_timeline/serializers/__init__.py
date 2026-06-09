from rest_framework import serializers

from apps.campaign_timeline.models import CampaignExecutionTimeline


class TimelineEntrySerializer(serializers.ModelSerializer):
    lead_name = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()

    class Meta:
        model = CampaignExecutionTimeline
        fields = [
            'id', 'enrollment_id', 'campaign_id', 'campaign_name',
            'lead_id', 'lead_name', 'step_order', 'step_type',
            'subject_snapshot', 'scheduled_at', 'executed_at',
            'status', 'failure_reason',
            'was_office_hour_shifted', 'original_scheduled_at',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields

    def get_lead_name(self, obj) -> str:
        if obj.lead:
            return f"{obj.lead.first_name} {obj.lead.last_name}"
        return ''

    def get_campaign_name(self, obj) -> str:
        if obj.campaign:
            return obj.campaign.name
        return ''


class TimelineDashboardSerializer(serializers.Serializer):
    pending_now = serializers.IntegerField()
    scheduled_today = serializers.IntegerField()
    executed_today = serializers.IntegerField()
    failed_today = serializers.IntegerField()
    office_hour_shifts = serializers.IntegerField()
