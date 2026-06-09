from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend

from apps.employees.models import Employee, Role, Permission
from apps.employees.serializers import (
    EmployeeSerializer, EmployeeCreateSerializer, AssignRoleSerializer,
    RoleSerializer, PermissionSerializer,
)
from apps.employees.services import EmployeeService
from apps.employees.selectors import get_employees_for_tenant, get_employee_by_user
from apps.audit.services import AuditService
from apps.common.permissions import IsTenantAdmin, IsAdvisorOrAbove, IsTenantEmployee


class EmployeeViewSet(viewsets.ReadOnlyModelViewSet):
    """
    FM-06: Employee management within a tenant.
    Tenant Admin manages employees; advisors can list/retrieve.
    BRU-01: all queries scoped to tenant.
    """

    serializer_class = EmployeeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    ordering_fields = ['user__last_name', 'created_at']
    ordering = ['user__last_name']

    def get_permissions(self):
        if self.action in ('create', 'assign_role', 'deactivate'):
            return [IsAuthenticated(), IsTenantAdmin()]
        return [IsAuthenticated(), IsAdvisorOrAbove()]

    def get_queryset(self):
        return get_employees_for_tenant(tenant=self.request.user.tenant)

    def create(self, request):
        """POST /api/v1/employees/ — create a new employee (Tenant Admin only)."""
        serializer = EmployeeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        employee = EmployeeService.create_employee(
            tenant=request.user.tenant,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(EmployeeSerializer(employee).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated, IsTenantEmployee])
    def me(self, request):
        """Return the authenticated employee's own profile."""
        employee = get_employee_by_user(user=request.user, tenant=request.user.tenant)
        return Response(EmployeeSerializer(employee).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTenantAdmin])
    def assign_role(self, request, pk=None):
        """POST /api/v1/employees/{id}/assign-role/ — add a role."""
        employee = self.get_object()
        serializer = AssignRoleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        EmployeeService.assign_role(
            employee=employee,
            role_slug=serializer.validated_data['role_slug'],
            actor=request.user,
        )
        employee.refresh_from_db()
        return Response(EmployeeSerializer(employee).data)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsTenantAdmin])
    def deactivate(self, request, pk=None):
        """POST /api/v1/employees/{id}/deactivate/ — deactivate an employee."""
        employee = self.get_object()
        before = {'is_active': employee.is_active}
        EmployeeService.deactivate_employee(employee=employee, actor=request.user)
        AuditService.log_from_request(
            request,
            action='employee.deactivate',
            entity_type='Employee',
            entity_id=employee.pk,
            before_state=before,
            after_state={'is_active': False},
        )
        return Response({'status': 'deactivated'})


class RoleListView(APIView):
    """
    GET /api/v1/employees/roles/  — list all roles for the tenant.
    Available to all tenant employees (advisors need to know role names).
    BRU-01: scoped to request.user.tenant.
    """
    permission_classes = [IsAuthenticated, IsAdvisorOrAbove]

    def get(self, request):
        roles = Role.objects.filter(tenant=request.user.tenant).prefetch_related(
            'role_permissions__permission'
        )
        return Response(RoleSerializer(roles, many=True).data)


class PermissionListView(APIView):
    """
    GET /api/v1/employees/permissions/  — list all available permission codenames.
    Tenant Admin only — used to build the permissions management UI.
    """
    permission_classes = [IsAuthenticated, IsTenantAdmin]

    def get(self, request):
        perms = Permission.objects.all().order_by('codename')
        return Response(PermissionSerializer(perms, many=True).data)
