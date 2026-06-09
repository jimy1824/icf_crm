"""
Portal serializers.
Rules:
- Never expose is_private=True content.
- Never expose internal advisor fields (notes, internal metadata).
- Financial profile is READ-ONLY for portal consumers (BRU-14).
- Only client-editable Lead fields: phone, preferred_timezone (BRU-14).
"""

from rest_framework import serializers

from apps.communications.models import Communication, Meeting
from apps.documents.models import Document
from apps.financials.models import FinancialAccount, FinancialGoal, FinancialProfile, GoalMilestone, InsurancePolicy
from apps.leads.models import ActivityNote, ConsentRecord, Household, HouseholdMembership, Lead
from apps.notifications.models import Notification
from apps.users.models import CustomerAccount


# ---------------------------------------------------------------------------
# Lead / Profile
# ---------------------------------------------------------------------------

class PortalLeadProfileSerializer(serializers.ModelSerializer):
    """
    BRU-14: only client-editable fields are writable (phone, preferred_timezone).
    All other fields are read-only.
    """

    full_name = serializers.SerializerMethodField()

    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email',
            'phone', 'preferred_timezone', 'status', 'source',
        ]
        read_only_fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email',
            'status', 'source',
        ]

    def get_full_name(self, obj):
        return obj.full_name


class PortalMeSerializer(serializers.ModelSerializer):
    """CustomerAccount + embedded lead profile for GET /portal/me/"""

    lead = PortalLeadProfileSerializer(read_only=True)

    class Meta:
        model = CustomerAccount
        fields = ['id', 'email', 'is_active', 'date_joined', 'lead', 'user_type']
        read_only_fields = ['id', 'email', 'is_active', 'date_joined', 'user_type']

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data['user_type'] = 'customer'
        return data


class PortalMeUpdateSerializer(serializers.ModelSerializer):
    """
    PATCH /portal/me/ — only phone and preferred_timezone are writable (BRU-14).
    """

    class Meta:
        model = Lead
        fields = ['phone', 'preferred_timezone']


# ---------------------------------------------------------------------------
# Financial Profile (read-only — BRU-14)
# ---------------------------------------------------------------------------

class PortalFinancialAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialAccount
        fields = [
            'id', 'account_type', 'institution', 'account_name',
            'value', 'currency', 'as_of_date',
        ]
        read_only_fields = fields


class PortalInsurancePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = InsurancePolicy
        fields = [
            'id', 'policy_type', 'provider', 'coverage_amount',
            'currency', 'as_of_date', 'premium_annual', 'expires_on',
        ]
        read_only_fields = fields


class PortalFinancialSummarySerializer(serializers.ModelSerializer):
    """BRU-14: all financial profile fields are read-only for portal consumers."""

    net_worth = serializers.DecimalField(
        max_digits=14, decimal_places=2, read_only=True
    )
    accounts = PortalFinancialAccountSerializer(many=True, read_only=True)
    insurance_policies = PortalInsurancePolicySerializer(many=True, read_only=True)

    class Meta:
        model = FinancialProfile
        fields = [
            'id',
            'annual_income', 'income_currency', 'income_as_of',
            'annual_expenses', 'expenses_currency', 'expenses_as_of',
            'total_assets', 'assets_currency', 'assets_as_of',
            'total_liabilities', 'liabilities_currency', 'liabilities_as_of',
            'net_worth',
            'risk_tolerance',
            'accounts',
            'insurance_policies',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Goals (read-only)
# ---------------------------------------------------------------------------

class PortalGoalMilestoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalMilestone
        fields = [
            'id', 'title', 'target_amount', 'target_date',
            'is_achieved', 'achieved_at',
        ]
        read_only_fields = fields


class PortalGoalSerializer(serializers.ModelSerializer):
    milestones = PortalGoalMilestoneSerializer(many=True, read_only=True)

    class Meta:
        model = FinancialGoal
        fields = [
            'id', 'goal_type', 'title', 'target_amount', 'target_currency',
            'target_date', 'current_value', 'progress_pct', 'is_off_track',
            'notes', 'milestones',
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

class PortalDocumentSerializer(serializers.ModelSerializer):
    """For listing/uploading documents. uploaded_by is read-only (set by portal logic)."""

    class Meta:
        model = Document
        fields = [
            'id', 'doc_type', 'kyc_status', 'storage_ref',
            'version', 'uploaded_at',
        ]
        read_only_fields = ['id', 'kyc_status', 'version', 'uploaded_at']


class PortalDocumentUploadSerializer(serializers.ModelSerializer):
    """
    POST /portal/documents/ — customer uploads a document.
    storage_ref is provided by the caller (pre-signed URL reference).
    """

    class Meta:
        model = Document
        fields = ['doc_type', 'storage_ref']


# ---------------------------------------------------------------------------
# Meetings
# ---------------------------------------------------------------------------

class PortalAdvisorPublicSerializer(serializers.Serializer):
    """Public advisor info only — never internal notes or metadata."""
    id = serializers.IntegerField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    full_name = serializers.SerializerMethodField()

    def get_full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}".strip()


class PortalMeetingSerializer(serializers.ModelSerializer):
    advisor = PortalAdvisorPublicSerializer(read_only=True)

    class Meta:
        model = Meeting
        fields = [
            'id', 'advisor', 'scheduled_at', 'recipient_timezone',
            'zoom_link', 'outcome', 'notes',
        ]
        read_only_fields = fields


class PortalMeetingRSVPSerializer(serializers.Serializer):
    """PATCH /portal/meetings/<pk>/rsvp/"""
    RSVP_ACCEPT = 'accepted'
    RSVP_DECLINE = 'declined'
    RSVP_CHOICES = [(RSVP_ACCEPT, 'Accepted'), (RSVP_DECLINE, 'Declined')]

    rsvp = serializers.ChoiceField(choices=RSVP_CHOICES)


# ---------------------------------------------------------------------------
# Communications (messages)
# ---------------------------------------------------------------------------

class PortalCommunicationSerializer(serializers.ModelSerializer):
    body_preview = serializers.SerializerMethodField()

    def get_body_preview(self, obj):
        if obj.body:
            return obj.body[:200]
        return None

    class Meta:
        model = Communication
        fields = [
            'id', 'channel', 'direction', 'status',
            'subject', 'body', 'body_preview', 'sent_at', 'created_at',
        ]
        read_only_fields = fields


class PortalSendMessageSerializer(serializers.Serializer):
    """POST /portal/messages/ — customer sends a message to advisor.
    Channel is always 'email' (inbound portal message); customer never picks it.
    """
    subject = serializers.CharField(max_length=500, allow_blank=True, default='')
    body = serializers.CharField(max_length=10000)


# ---------------------------------------------------------------------------
# Consent
# ---------------------------------------------------------------------------

class PortalConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ['id', 'channel', 'purpose', 'state', 'source', 'recorded_at']
        read_only_fields = fields


class PortalConsentUpdateSerializer(serializers.ModelSerializer):
    """POST /portal/consent/ — customer updates consent (BRU-07/15)."""

    class Meta:
        model = ConsentRecord
        fields = ['channel', 'purpose', 'state', 'source']

    def validate_state(self, value):
        allowed = {ConsentRecord.STATE_GRANTED, ConsentRecord.STATE_REVOKED}
        if value not in allowed:
            raise serializers.ValidationError(
                f"Portal consent state must be one of: {', '.join(allowed)}"
            )
        return value


# ---------------------------------------------------------------------------
# Household (BRU-28 — consent-gated)
# ---------------------------------------------------------------------------

class PortalHouseholdMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lead
        fields = ['id', 'first_name', 'last_name', 'email', 'status']
        read_only_fields = fields


class PortalHouseholdMembershipSerializer(serializers.ModelSerializer):
    lead = PortalHouseholdMemberSerializer(read_only=True)

    class Meta:
        model = HouseholdMembership
        fields = ['id', 'lead', 'relationship']
        read_only_fields = fields


class PortalHouseholdSerializer(serializers.ModelSerializer):
    memberships = PortalHouseholdMembershipSerializer(many=True, read_only=True)

    class Meta:
        model = Household
        fields = ['id', 'name', 'memberships']
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class PortalNotificationSerializer(serializers.ModelSerializer):
    title = serializers.SerializerMethodField()
    body  = serializers.SerializerMethodField()

    def get_title(self, obj):
        from apps.notifications.serializers import _EVENT_LABELS
        return _EVENT_LABELS.get(obj.event_type, obj.event_type.replace('.', ' ').replace('_', ' ').title())

    def get_body(self, obj):
        return f"{obj.entity_type.replace('_', ' ').title()} · {obj.entity_id}" if obj.entity_id else None

    class Meta:
        model = Notification
        fields = [
            'id', 'event_type', 'entity_type', 'entity_id',
            'channels', 'is_read', 'title', 'body', 'created_at',
        ]
        read_only_fields = [
            'id', 'event_type', 'entity_type', 'entity_id',
            'channels', 'title', 'body', 'created_at',
        ]


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

class PortalDashboardSerializer(serializers.Serializer):
    lead_status = serializers.CharField()
    goals_count = serializers.IntegerField()
    off_track_goals = serializers.IntegerField()
    documents_count = serializers.IntegerField()
    upcoming_meetings_count = serializers.IntegerField()
    unread_notifications_count = serializers.IntegerField()
    net_worth = serializers.DecimalField(
        max_digits=14, decimal_places=2, allow_null=True
    )
