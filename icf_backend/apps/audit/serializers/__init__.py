from rest_framework import serializers
from apps.audit.models import AuditEvent


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = [
            'id', 'action', 'entity_type', 'entity_id',
            'actor', 'before_state', 'after_state', 'ip_address', 'timestamp',
        ]
        read_only_fields = fields
