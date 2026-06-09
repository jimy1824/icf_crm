from rest_framework import viewsets, filters
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend

from apps.audit.models import AuditEvent
from apps.audit.selectors import get_audit_trail
from apps.audit.serializers import AuditEventSerializer
from apps.common.permissions import IsComplianceOfficer


class AuditEventViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only. Super Admin sees all tenants. Compliance Officer and
    Tenant Admin see their own firm only. BRU-33, BRU-01.
    """

    serializer_class = AuditEventSerializer
    permission_classes = [IsAuthenticated, IsComplianceOfficer]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['action', 'entity_type', 'entity_id', 'actor']
    ordering_fields = ['timestamp']
    ordering = ['-timestamp']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return AuditEvent.objects.select_related('actor', 'tenant').all()
        return get_audit_trail(tenant=user.tenant).select_related('actor', 'tenant')
