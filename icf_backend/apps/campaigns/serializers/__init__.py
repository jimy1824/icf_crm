from rest_framework import serializers
from apps.campaigns.models import Campaign, CampaignStep, CampaignEnrollment


class CampaignStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignStep
        fields = ['id', 'step_number', 'channel', 'subject', 'content_template', 'delay_days']
        read_only_fields = ['id']


class CampaignStepCreateSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=CampaignStep.CHANNEL_CHOICES)
    subject = serializers.CharField(max_length=500, required=False, default='')
    content_template = serializers.CharField()
    delay_days = serializers.IntegerField(min_value=0, default=0)


class CampaignSerializer(serializers.ModelSerializer):
    steps = CampaignStepSerializer(many=True, read_only=True)

    class Meta:
        model = Campaign
        fields = ['id', 'name', 'status', 'created_at', 'steps']
        read_only_fields = ['id', 'created_at', 'status']


class CampaignCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    steps = CampaignStepCreateSerializer(many=True, required=False)


class CampaignEnrollmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = CampaignEnrollment
        fields = [
            'id', 'campaign', 'lead',
            'status', 'current_step', 'stopped_reason', 'enrolled_at',
        ]
        read_only_fields = ['id', 'enrolled_at', 'status', 'current_step']


class EnrollSubjectSerializer(serializers.Serializer):
    lead_id = serializers.IntegerField()

    def validate_lead_id(self, value):
        if not value:
            raise serializers.ValidationError("lead_id is required.")
        return value


class StopEnrollmentSerializer(serializers.Serializer):
    reason = serializers.ChoiceField(choices=[
        ('response', 'Response'),
        ('opt_out', 'Opt Out'),
        ('manual', 'Manual'),
    ])
