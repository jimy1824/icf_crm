from django.db import models
from apps.common.models import TenantBaseModel


class AnalyticsSnapshot(TenantBaseModel):
    """
    FM-12/FM-26: pre-aggregated analytics per tenant per day.
    Computed by Celery beat; append-only (one record per tenant/level/date).
    BRU-01: scoped per tenant.
    """
    LEVEL_PLATFORM = 'platform'
    LEVEL_FIRM = 'firm'
    LEVEL_ADVISOR = 'advisor'
    LEVEL_CLIENT = 'client'
    LEVEL_CHOICES = [
        (LEVEL_PLATFORM, 'Platform'),
        (LEVEL_FIRM, 'Firm'),
        (LEVEL_ADVISOR, 'Advisor'),
        (LEVEL_CLIENT, 'Client'),
    ]

    snapshot_date = models.DateField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES)
    entity_id = models.CharField(max_length=50, blank=True)
    metrics = models.JSONField()

    class Meta:
        unique_together = [('tenant', 'snapshot_date', 'level', 'entity_id')]
        ordering = ['-snapshot_date']
        indexes = [
            models.Index(fields=['tenant', 'level', 'snapshot_date']),
        ]

    def __str__(self):
        return f"{self.tenant_id} {self.level} {self.snapshot_date}"
