from rest_framework import serializers
from apps.analytics.models import AnalyticsSnapshot


class AnalyticsSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnalyticsSnapshot
        fields = ['id', 'snapshot_date', 'level', 'entity_id', 'metrics', 'created_at']
        read_only_fields = fields


class AdvisorSummarySerializer(serializers.Serializer):
    """Lightweight advisor record for dashboard filters."""
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField()
    role = serializers.CharField()
    active_lead_count = serializers.IntegerField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class AssignedAdvisorSerializer(serializers.Serializer):
    """Minimal advisor info embedded inside a lead row."""
    id = serializers.IntegerField()
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class TodayLeadRowSerializer(serializers.Serializer):
    """
    One row in the Today's Leads table.
    Includes full lead contact info (name + email + phone) for the Lead Info column.
    Advisors are a list — leads are never duplicated per-advisor.
    BRU-01: serialiser only sees records already filtered by tenant.
    """
    id = serializers.IntegerField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    email = serializers.EmailField()
    phone = serializers.CharField(allow_blank=True)
    territory = serializers.SerializerMethodField()
    territory_id = serializers.SerializerMethodField()
    assigned_advisors = serializers.SerializerMethodField()
    campaign = serializers.SerializerMethodField()
    campaign_id = serializers.SerializerMethodField()
    pipeline_stage = serializers.CharField()
    status = serializers.CharField()
    created_at = serializers.DateTimeField()

    def get_territory(self, obj):
        return obj.territory.name if obj.territory else None

    def get_territory_id(self, obj):
        return obj.territory.id if obj.territory else None

    def get_assigned_advisors(self, obj):
        advisors = obj.assigned_advisors.all()
        return [
            {'id': a.id, 'full_name': f"{a.first_name} {a.last_name}".strip()}
            for a in advisors
        ]

    def get_campaign(self, obj):
        # Uses the prefetched active_enrollments attribute set in selector
        enrollments = getattr(obj, 'active_enrollments', None)
        if enrollments:
            return enrollments[0].campaign.name
        return None

    def get_campaign_id(self, obj):
        enrollments = getattr(obj, 'active_enrollments', None)
        if enrollments:
            return enrollments[0].campaign.id
        return None


class TodayActivityRowSerializer(serializers.Serializer):
    """
    One row in the Today's Scheduled Activities table.
    BRU-01: serialiser only sees records already filtered by tenant.
    """
    id = serializers.IntegerField()
    lead_id = serializers.SerializerMethodField()
    lead_name = serializers.SerializerMethodField()
    lead_email = serializers.SerializerMethodField()
    assigned_advisors = serializers.SerializerMethodField()
    campaign_name = serializers.SerializerMethodField()
    campaign_id = serializers.SerializerMethodField()
    step_order = serializers.IntegerField()
    step_type = serializers.CharField()
    scheduled_at = serializers.DateTimeField()
    status = serializers.CharField()
    failure_reason = serializers.CharField(allow_blank=True)

    def get_lead_id(self, obj):
        return obj.lead.id if obj.lead else None

    def get_lead_name(self, obj):
        if obj.lead:
            return f"{obj.lead.first_name} {obj.lead.last_name}".strip()
        return None

    def get_lead_email(self, obj):
        return obj.lead.email if obj.lead else None

    def get_assigned_advisors(self, obj):
        if not obj.lead:
            return []
        advisors = obj.lead.assigned_advisors.all()
        return [
            {'id': a.id, 'full_name': f"{a.first_name} {a.last_name}".strip()}
            for a in advisors
        ]

    def get_campaign_name(self, obj):
        return obj.campaign.name if obj.campaign else None

    def get_campaign_id(self, obj):
        return obj.campaign.id if obj.campaign else None
