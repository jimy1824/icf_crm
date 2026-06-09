from django.conf import settings
from django.db import models
from apps.common.models import TenantBaseModel


class Notification(TenantBaseModel):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE, related_name='notifications',
    )
    event_type = models.CharField(max_length=100)   # e.g. 'goal.off_track', 'lead.assigned'
    entity_type = models.CharField(max_length=100)
    entity_id = models.CharField(max_length=36)
    channels = models.JSONField(default=list)        # e.g. ['email', 'in_app']
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['tenant', 'recipient', 'is_read']),
        ]

    def __str__(self):
        return f"{self.event_type} → {self.recipient_id} ({'read' if self.is_read else 'unread'})"
