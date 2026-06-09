from rest_framework import serializers
from apps.territories.models import Territory, AdvisorTerritory


class TerritorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Territory
        fields = ['id', 'name', 'description', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class TerritoryCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(default='', allow_blank=True)


class TerritoryUpdateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=200, required=False)
    description = serializers.CharField(allow_blank=True, required=False)


class AdvisorTerritorySerializer(serializers.ModelSerializer):
    advisor_id = serializers.IntegerField(source='advisor.pk', read_only=True)
    advisor_name = serializers.CharField(source='advisor.get_full_name', read_only=True)
    advisor_email = serializers.EmailField(source='advisor.email', read_only=True)
    assigned_by_name = serializers.CharField(
        source='assigned_by.get_full_name', read_only=True, default=None,
    )

    class Meta:
        model = AdvisorTerritory
        fields = [
            'id', 'advisor_id', 'advisor_name', 'advisor_email',
            'assigned_at', 'assigned_by_name',
        ]
        read_only_fields = ['id', 'assigned_at']


class AssignAdvisorSerializer(serializers.Serializer):
    advisor_id = serializers.IntegerField()


class TerritoryMinimalSerializer(serializers.ModelSerializer):
    """Lightweight serializer for embedding in Lead/Campaign responses."""
    class Meta:
        model = Territory
        fields = ['id', 'name', 'is_active']
        read_only_fields = ['id', 'name', 'is_active']
