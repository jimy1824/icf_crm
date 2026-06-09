from django.db import models


class TenantScopedQuerySet(models.QuerySet):
    """
    Base queryset that enforces BRU-01 tenant isolation.
    Always filter by tenant before returning rows.
    """

    def for_tenant(self, tenant):
        return self.filter(tenant=tenant)


class TenantScopedManager(models.Manager):
    def get_queryset(self):
        return TenantScopedQuerySet(self.model, using=self._db)

    def for_tenant(self, tenant):
        return self.get_queryset().for_tenant(tenant)
