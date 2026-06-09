from rest_framework import serializers
from apps.leads.models import Lead, KanbanCard, ActivityNote, Household, ConsentRecord
from apps.territories.serializers import TerritoryMinimalSerializer


class KanbanCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = KanbanCard
        fields = ['id', 'stage', 'position', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class ActivityNoteSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)

    class Meta:
        model = ActivityNote
        fields = [
            'id', 'activity_type', 'body', 'is_private',
            'author', 'author_name', 'created_at',
        ]
        read_only_fields = ['id', 'author', 'author_name', 'created_at']


class ActivityNoteCreateSerializer(serializers.Serializer):
    body = serializers.CharField()
    activity_type = serializers.ChoiceField(
        choices=ActivityNote.TYPE_CHOICES,
        default=ActivityNote.TYPE_NOTE,
    )
    is_private = serializers.BooleanField(default=True)


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = Household
        fields = ['id', 'name', 'created_at']
        read_only_fields = ['id', 'created_at']


class ConsentRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConsentRecord
        fields = ['id', 'channel', 'purpose', 'state', 'source', 'recorded_at']
        read_only_fields = ['id', 'recorded_at']


class LeadSerializer(serializers.ModelSerializer):
    assigned_advisors = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    assigned_advisor_names = serializers.SerializerMethodField()
    kanban_card = KanbanCardSerializer(read_only=True)
    territory = TerritoryMinimalSerializer(read_only=True)
    full_name = serializers.CharField(read_only=True)
    is_client = serializers.BooleanField(read_only=True)

    def get_assigned_advisor_names(self, obj):
        return [a.get_full_name() for a in obj.assigned_advisors.all()]

    class Meta:
        model = Lead
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'email', 'phone',
            'source', 'status', 'is_client', 'pipeline_stage',
            'territory', 'household',
            'assigned_advisors', 'assigned_advisor_names', 'kanban_card',
            'opted_out', 'is_suppressed', 'portal_enabled',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'status', 'is_client', 'created_at', 'updated_at']


class LeadCreateSerializer(serializers.ModelSerializer):
    territory_name = serializers.CharField(max_length=200, default='', allow_blank=True)

    class Meta:
        model = Lead
        fields = ['first_name', 'last_name', 'email', 'phone', 'source', 'territory_name']

    def validate_source(self, value):
        request = self.context.get('request')
        if value == Lead.SOURCE_EMAIL_TRIGGER and request:
            if not (request.user.role in {'service', 'super_admin'}):
                raise serializers.ValidationError(
                    "email_trigger source is reserved for integration accounts (BRU-02)."
                )
        return value


class AssignAdvisorsSerializer(serializers.Serializer):
    advisor_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )


class MoveStageSerializer(serializers.Serializer):
    stage = serializers.ChoiceField(choices=Lead.STAGE_CHOICES)
    position = serializers.IntegerField(default=0, min_value=0)


class StatusTransitionSerializer(serializers.Serializer):
    """For explicit status transitions outside the kanban (e.g. deceased, former_client)."""
    status = serializers.ChoiceField(choices=Lead.STATUS_CHOICES)
