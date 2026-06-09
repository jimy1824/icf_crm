from apps.tenants.models import Tenant, TenantSubscription


def get_tenant_by_id(*, tenant_id):
    return Tenant.objects.get(id=tenant_id)


def get_active_tenants():
    return Tenant.objects.filter(status=Tenant.STATUS_ACTIVE)


def get_tenant_subscription(*, tenant):
    return TenantSubscription.objects.select_related('plan').get(tenant=tenant)
