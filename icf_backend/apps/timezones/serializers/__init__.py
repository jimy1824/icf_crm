from rest_framework import serializers

from apps.timezones.models import AdvisorTimeZone, TenantTimeZone


class TenantTimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantTimeZone
        fields = ['id', 'timezone', 'office_start', 'office_end', 'working_days', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class TenantTimeZoneUpdateSerializer(serializers.Serializer):
    timezone = serializers.CharField(max_length=100, required=False)
    office_start = serializers.TimeField(required=False)
    office_end = serializers.TimeField(required=False)
    working_days = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=6),
        required=False,
    )


class AdvisorTimeZoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdvisorTimeZone
        fields = ['id', 'timezone', 'updated_at']
        read_only_fields = ['id', 'updated_at']


class AdvisorTimeZoneWriteSerializer(serializers.Serializer):
    timezone = serializers.CharField(max_length=100)
