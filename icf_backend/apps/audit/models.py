from django.conf import settings
from django.db import models


class AuditEvent(models.Model):
    # BRU-33: append-only, tamper-evident — intentionally does NOT extend BaseModel
    # (no updated_at, no is_active, no soft-delete semantics)
    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.SET_NULL, null=True,
        related_name='audit_events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name='audit_events',
    )
    action = models.CharField(max_length=100)        # e.g. 'lead.create', 'document.verify'
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=36)      # UUID of affected record
    before_state = models.JSONField(null=True, blank=True)
    after_state = models.JSONField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['tenant', 'timestamp']),
            models.Index(fields=['entity_type', 'entity_id']),
            models.Index(fields=['actor', 'timestamp']),
        ]

    def save(self, *args, **kwargs):
        if self._state.adding is False:
            raise PermissionError("AuditEvent records are immutable and cannot be modified.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("AuditEvent records cannot be deleted.")

    def __str__(self):
        return f"{self.action} on {self.entity_type}/{self.entity_id} @ {self.timestamp:%Y-%m-%d %H:%M}"
