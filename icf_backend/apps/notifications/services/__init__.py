import logging

from django.db import transaction

from apps.notifications.models import Notification

logger = logging.getLogger(__name__)


class NotificationService:
    """
    FM-14: consent-aware notification dispatch.
    BRU-07/15: preference gate suppresses channels the user has disabled.
    """

    @staticmethod
    @transaction.atomic
    def notify(
        *, tenant, recipient, event_type, entity_type, entity_id, channels=None,
    ) -> Notification:
        """
        BRU-07/15: channels gated by user's NotificationPreference.
        If no preference exists, defaults to ['in_app'].
        """
        effective_channels = _resolve_channels(
            recipient=recipient,
            event_type=event_type,
            requested_channels=channels or ['in_app'],
        )
        notification = Notification.objects.create(
            tenant=tenant,
            recipient=recipient,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=str(entity_id),
            channels=effective_channels,
        )
        # Dispatch non-in_app channels to Celery
        for channel in effective_channels:
            if channel != 'in_app':
                from apps.notifications.tasks import dispatch_notification_channel
                dispatch_notification_channel.delay(notification.pk, channel)
        return notification

    @staticmethod
    @transaction.atomic
    def mark_read(*, notification: Notification) -> Notification:
        notification.is_read = True
        notification.save(update_fields=['is_read', 'updated_at'])
        return notification

    @staticmethod
    @transaction.atomic
    def mark_all_read(*, tenant, recipient) -> int:
        count = Notification.objects.filter(
            tenant=tenant, recipient=recipient, is_read=False,
        ).update(is_read=True)
        return count

    @staticmethod
    def unread_count(*, tenant, recipient) -> int:
        return Notification.objects.filter(
            tenant=tenant, recipient=recipient, is_read=False,
        ).count()


# Backward-compatible function form used by Phase 1–3 event handlers
def notify(*, tenant, recipient, event_type, entity_type, entity_id, channels=None):
    return NotificationService.notify(
        tenant=tenant, recipient=recipient, event_type=event_type,
        entity_type=entity_type, entity_id=entity_id, channels=channels,
    )


def mark_read(*, notification):
    return NotificationService.mark_read(notification=notification)


def _resolve_channels(*, recipient, event_type, requested_channels) -> list:
    """Gate channels through NotificationPreference (BRU-07/15)."""
    try:
        from apps.tenants.services import NotificationPreferenceService
        enabled = NotificationPreferenceService.enabled_channels(
            user=recipient, event_type=event_type,
        )
        # Return intersection of requested + enabled, preserving at least in_app
        result = [c for c in requested_channels if c in enabled]
        return result if result else ['in_app']
    except Exception:
        logger.exception("Error resolving notification channels — defaulting to in_app")
        return ['in_app']
