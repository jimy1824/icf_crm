from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from apps.users.models import CustomUser
from apps.users.serializers import UserSerializer, UserCreateSerializer
from apps.users.services import create_tenant_user, deactivate_user
from apps.audit.services import AuditService
from apps.common.permissions import IsTenantAdmin, IsTeamLeadOrAbove


class UserViewSet(viewsets.ModelViewSet):
    """
    Tenant Admin manages users within their own firm. BRU-01.
    Team Lead can list/retrieve their own team. BRU-08.
    """

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['role', 'is_active']
    search_fields = ['email', 'first_name', 'last_name']
    ordering_fields = ['date_joined', 'last_name']
    ordering = ['last_name']

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        if self.action in ('list', 'retrieve', 'me'):
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsTenantAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return CustomUser.objects.select_related('tenant').all()
        if user.tenant_id is None:
            return CustomUser.objects.none()
        # BRU-01: always filter by tenant
        return CustomUser.objects.filter(tenant=user.tenant).select_related('tenant')

    def perform_create(self, serializer):
        user = self.request.user
        new_user = create_tenant_user(
            tenant=user.tenant,
            email=serializer.validated_data['email'],
            password=serializer.validated_data['password'],
            first_name=serializer.validated_data['first_name'],
            last_name=serializer.validated_data['last_name'],
            role=serializer.validated_data['role'],
        )
        AuditService.log_from_request(
            self.request,
            action='user.create',
            entity_type='CustomUser',
            entity_id=new_user.pk,
            after_state={'email': new_user.email, 'role': new_user.role},
        )

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """Return the authenticated user's own profile."""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTenantAdmin])
    def deactivate(self, request, pk=None):
        """Deactivate a user account without deletion."""
        target = self.get_object()
        before = {'is_active': target.is_active}
        deactivate_user(user=target)
        AuditService.log_from_request(
            request,
            action='user.deactivate',
            entity_type='CustomUser',
            entity_id=target.pk,
            before_state=before,
            after_state={'is_active': False},
        )
        return Response({'status': 'deactivated'})
