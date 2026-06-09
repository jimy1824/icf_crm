from rest_framework import serializers
from apps.compliance.models import RetentionPolicy, RetentionRecord, SupervisionRule, SupervisionReview


class RetentionPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = RetentionPolicy
        fields = ['id', 'entity_type', 'retention_years', 'description', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class RetentionRecordSerializer(serializers.ModelSerializer):
    is_deletable = serializers.SerializerMethodField()

    class Meta:
        model = RetentionRecord
        fields = [
            'id', 'entity_type', 'entity_id', 'retained_until',
            'is_under_legal_hold', 'hold_placed_by', 'hold_placed_at',
            'hold_reason', 'cleared_for_deletion_at', 'is_deletable',
            'created_at',
        ]
        read_only_fields = fields

    def get_is_deletable(self, obj) -> bool:
        from datetime import date
        if obj.is_under_legal_hold:
            return False
        return date.today() > obj.retained_until


class LegalHoldPlaceSerializer(serializers.Serializer):
    entity_type = serializers.CharField(max_length=100)
    entity_id = serializers.CharField(max_length=36)
    reason = serializers.CharField()


class LegalHoldLiftSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, default='')


class RetentionPolicyConfigSerializer(serializers.Serializer):
    entity_type = serializers.ChoiceField(choices=RetentionPolicy.ENTITY_CHOICES)
    retention_years = serializers.IntegerField(min_value=1, max_value=99)


class SupervisionRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupervisionRule
        fields = [
            'id', 'applies_to_advisor', 'channel', 'review_mode',
            'supervisor', 'description', 'is_active', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']


class SupervisionReviewSerializer(serializers.ModelSerializer):
    communication_channel = serializers.CharField(
        source='communication.channel', read_only=True,
    )
    reviewed_by_name = serializers.CharField(
        source='reviewed_by.get_full_name', read_only=True,
    )

    class Meta:
        model = SupervisionReview
        fields = [
            'id', 'communication', 'communication_channel', 'rule', 'supervisor',
            'status', 'review_notes', 'reviewed_at', 'reviewed_by', 'reviewed_by_name',
            'created_at',
        ]
        read_only_fields = fields


class ReviewActionSerializer(serializers.Serializer):
    notes = serializers.CharField(required=False, default='')


class ReviewRejectSerializer(serializers.Serializer):
    notes = serializers.CharField()
