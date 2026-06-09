from apps.employees.models import Employee, Role


def get_employees_for_tenant(*, tenant, role_slug=None, is_active=True):
    """BRU-01: always scoped to tenant."""
    qs = (
        Employee.objects
        .filter(tenant=tenant, is_active=is_active)
        .select_related('user', 'tenant')
        .prefetch_related('roles')
    )
    if role_slug:
        qs = qs.filter(roles__slug=role_slug)
    return qs


def get_advisors_for_tenant(*, tenant):
    """Return active advisor and team_lead employees for a tenant."""
    return (
        Employee.objects
        .filter(
            tenant=tenant,
            is_active=True,
            roles__slug__in=[Role.SLUG_ADVISOR, Role.SLUG_TEAM_LEAD],
        )
        .select_related('user')
        .distinct()
    )


def get_employee_by_user(*, user, tenant):
    """Fetch an employee record for a given CustomUser within a tenant."""
    return Employee.objects.select_related('user', 'tenant').get(
        user=user, tenant=tenant
    )
