from apps.users.models import CustomUser


def get_tenant_users(*, tenant):
    # BRU-01: always scoped to tenant
    return CustomUser.objects.filter(tenant=tenant, is_active=True)


def get_tenant_advisors(*, tenant):
    return CustomUser.objects.filter(
        tenant=tenant,
        role__in=[CustomUser.ROLE_ADVISOR, CustomUser.ROLE_TEAM_LEAD],
        is_active=True,
    )


def get_user_by_id(*, user_id, tenant):
    return CustomUser.objects.get(id=user_id, tenant=tenant)
