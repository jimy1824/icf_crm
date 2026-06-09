from django.conf import settings
from django.db import models
from apps.common.models import TenantBaseModel


class Territory(TenantBaseModel):
    """
    A named geographic or business-unit coverage zone within a tenant.
    Soft-delete only: set is_active=False, never hard delete.
    BRU-01: scoped per tenant.
    """

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_territory_name_per_tenant'
            )
        ]
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'is_active']),
            models.Index(fields=['tenant', 'name']),
        ]

    def __str__(self):
        return f"{self.name} ({self.tenant_id})"


class AdvisorTerritory(models.Model):
    """
    M2M through-table: Advisor ↔ Territory assignment with audit trail.
    """

    advisor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='advisor_territories',
        limit_choices_to={'role__in': ['team_lead', 'advisor']},
    )
    territory = models.ForeignKey(
        Territory,
        on_delete=models.CASCADE,
        related_name='advisor_territories',
    )
    assigned_at = models.DateTimeField(auto_now_add=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='territory_assignments_made',
    )

    class Meta:
        unique_together = [('advisor', 'territory')]
        ordering = ['territory__name', 'advisor__last_name']
        indexes = [
            models.Index(fields=['territory', 'advisor']),
        ]

    def __str__(self):
        return f"{self.advisor_id} in {self.territory.name}"
