import logging

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='notifications',
          name='notifications.dispatch_channel')
def dispatch_notification_channel(self, notification_id: int, channel: str):
    """
    FM-14: dispatch a single notification to the given channel.
    BRU-07/15: channel already validated by NotificationService.notify() —
    only channels the user has enabled reach this task.
    """
    from apps.notifications.models import Notification
    try:
        notification = Notification.objects.select_related('recipient', 'tenant').get(
            pk=notification_id,
        )
    except Notification.DoesNotExist:
        logger.error("Notification %d not found — skipping", notification_id)
        return

    try:
        if channel == 'email':
            _send_email_notification(notification)
        elif channel == 'sms':
            _send_sms_notification(notification)
        elif channel == 'push':
            _send_push_notification(notification)
        else:
            logger.warning("Unknown notification channel '%s' — skipping", channel)
    except Exception as exc:
        logger.exception("Failed to dispatch notification %d via %s", notification_id, channel)
        raise self.retry(exc=exc)


def _send_email_notification(notification):
    from django.core.mail import send_mail
    from django.conf import settings
    recipient = notification.recipient
    if not recipient.email:
        return
    send_mail(
        subject=f"[ICF] {notification.event_type.replace('.', ' ').title()}",
        message=f"Entity: {notification.entity_type} #{notification.entity_id}",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[recipient.email],
        fail_silently=False,
    )


def _send_sms_notification(notification):
    # Placeholder: Twilio dispatch will be wired once TwilioService is available
    logger.info(
        "SMS notification %d queued for %s (not yet wired)",
        notification.pk, notification.recipient_id,
    )


def _send_push_notification(notification):
    # Placeholder: web-push dispatch
    logger.info(
        "Push notification %d queued for %s (not yet wired)",
        notification.pk, notification.recipient_id,
    )

