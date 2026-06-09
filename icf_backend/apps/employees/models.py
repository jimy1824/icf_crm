"""
FM-06: Employee RBAC models.

Structure:
  Employee       — internal user record for one advisory firm
  Role           — named set of permissions (e.g. 'advisor', 'team_lead')
  Permission     — a single named capability (e.g. 'leads.assign')
  EmployeeRole   — M2M: which roles an employee holds
  RolePermission — M2M: which permissions a role grants

An Employee is a thin wrapper around CustomUser that carries tenant-specific
employee metadata and the M2M role assignments. CustomUser remains the
authentication identity (password, JWT). The Employee record is the business
identity within a tenant.

BRU-01: every Employee belongs to exactly one Tenant.
"""

from django.conf import settings
from django.db import models
from apps.common.models import TenantBaseModel, BaseModel


class Permission(BaseModel):
    """
    A single named capability. Seeded at startup, never user-created.
    Examples: 'leads.view_own', 'leads.view_all', 'leads.assign',
              'financials.view', 'campaigns.manage', 'users.manage'
    """
    codename = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['codename']

    def __str__(self):
        return self.codename


class Role(TenantBaseModel):
    """
    A named role within a tenant. Each tenant may customise display names.
    Core slugs are seeded: tenant_admin, team_lead, advisor.
    Platform roles (super_admin, support, compliance_officer) are NOT stored
    here — they are handled by CustomUser.user_type='platform_staff'.

    BRU-01: roles belong to a tenant.
    """
    SLUG_TENANT_ADMIN = 'tenant_admin'
    SLUG_TEAM_LEAD = 'team_lead'
    SLUG_ADVISOR = 'advisor'
    CORE_SLUGS = {SLUG_TENANT_ADMIN, SLUG_TEAM_LEAD, SLUG_ADVISOR}

    slug = models.CharField(max_length=50)
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(
        Permission,
        through='RolePermission',
        blank=True,
        related_name='roles',
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'slug'], name='unique_role_slug_per_tenant'
            )
        ]
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.tenant})"


class RolePermission(BaseModel):
    """Through table: which permissions a role grants."""
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='role_permissions')
    permission = models.ForeignKey(Permission, on_delete=models.CASCADE, related_name='role_permissions')

    class Meta:
        unique_together = [('role', 'permission')]

    def __str__(self):
        return f"{self.role.slug} → {self.permission.codename}"


class Employee(TenantBaseModel):
    """
    Internal employee record for a tenant.

    Linked 1-to-1 with CustomUser (the authentication identity).
    The Employee record carries tenant-specific metadata and role assignments.

    An employee's effective permissions = union of permissions from all their roles.
    BRU-01: always scoped to one tenant.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='employee_profile',
    )
    roles = models.ManyToManyField(
        Role,
        through='EmployeeRole',
        blank=True,
        related_name='employees',
    )
    job_title = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['user__last_name', 'user__first_name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user'], name='unique_employee_per_tenant'
            )
        ]

    def __str__(self):
        return f"{self.user.get_full_name()} @ {self.tenant.firm_name}"

    def has_permission(self, codename: str) -> bool:
        """Check if this employee holds any role that grants codename."""
        return self.roles.filter(
            role_permissions__permission__codename=codename
        ).exists()

    def get_primary_role_slug(self) -> str:
        """Return the highest-authority role slug the employee holds."""
        priority = [Role.SLUG_TENANT_ADMIN, Role.SLUG_TEAM_LEAD, Role.SLUG_ADVISOR]
        held = set(self.roles.values_list('slug', flat=True))
        for slug in priority:
            if slug in held:
                return slug
        return ''


class EmployeeRole(BaseModel):
    """Through table: which roles an employee holds within a tenant."""
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='employee_roles')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, related_name='employee_roles')
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='role_assignments_made',
    )

    class Meta:
        unique_together = [('employee', 'role')]

    def __str__(self):
        return f"{self.employee} → {self.role.slug}"
