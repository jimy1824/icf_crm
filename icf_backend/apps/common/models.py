from django.db import models
from apps.common.querysets import TenantScopedManager


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True


class TenantBaseModel(BaseModel):
    """
    Abstract base for every tenant-scoped model (BRU-01).
    The TenantScopedManager exposes .for_tenant(tenant) on every subclass,
    used by TenantScopedViewMixin to guarantee no cross-tenant row leakage.
    """

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
    )

    objects = TenantScopedManager()

    class Meta:
        abstract = True
