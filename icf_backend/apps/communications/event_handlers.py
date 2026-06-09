"""
Communications event handlers — subscribed in CommunicationsConfig.ready().
BRU-07: consent.revoked — auto-suppress the channel.
BRU-05: mailbox.token_expired — alert advisor.
"""
import logging

from apps.common.events import event_bus
from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='communications',
          name='communications.handle_consent_revoked')
def handle_consent_revoked(self, *, event_name, tenant_id, channel, lead_id=None,
                            client_id=None, **kwargs) -> None:
    """BRU-07: consent revoked — suppress the channel for this subject."""
    try:
        from apps.communications.models import SuppressionRecord
        from apps.leads.models import Lead
        from apps.tenants.models import Tenant

        tenant = Tenant.objects.filter(pk=tenant_id).first()
        if not tenant:
            return

        # client_id is a legacy param — treat it as lead_id if lead_id not provided
        resolved_lead_id = lead_id or client_id
        lead = Lead.objects.filter(pk=resolved_lead_id).first() if resolved_lead_id else None

        email = lead.email or '' if lead else ''
        phone = getattr(lead, 'phone', '') or '' if lead else ''

        if channel in ('email', 'all') and email:
            SuppressionRecord.objects.get_or_create(
                tenant=tenant, email=email, channel=SuppressionRecord.CHANNEL_EMAIL,
                defaults={'reason': SuppressionRecord.REASON_MANUAL},
            )
        if channel in ('sms', 'all') and phone:
            SuppressionRecord.objects.get_or_create(
                tenant=tenant, phone=phone, channel=SuppressionRecord.CHANNEL_SMS,
                defaults={'reason': SuppressionRecord.REASON_MANUAL},
            )
        logger.info(
            "handle_consent_revoked: channel=%s lead=%s suppressed",
            channel, resolved_lead_id,
        )
    except Exception as exc:
        logger.exception("handle_consent_revoked error")
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='communications',
          name='communications.handle_mailbox_token_expired')
def handle_mailbox_token_expired(self, *, event_name, tenant_id, connection_id,
                                  advisor_id, **kwargs) -> None:
    """BRU-05: token expired — notify advisor to reconnect."""
    try:
        from apps.notifications.models import Notification
        from apps.tenants.models import Tenant
        from apps.users.models import CustomUser

        tenant = Tenant.objects.filter(pk=tenant_id).first()
        advisor = CustomUser.objects.filter(pk=advisor_id).first()
        if not tenant or not advisor:
            return

        Notification.objects.create(
            tenant=tenant,
            recipient=advisor,
            event_type='mailbox_token_expired',
            entity_type='MailboxConnection',
            entity_id=connection_id,
            channels=['in_app'],
        )
        logger.info(
            "handle_mailbox_token_expired: notification created for advisor %d", advisor_id,
        )
    except Exception as exc:
        logger.exception("handle_mailbox_token_expired error")
        raise self.retry(exc=exc)


event_bus.subscribe('consent.revoked', handle_consent_revoked)
event_bus.subscribe('mailbox.token_expired', handle_mailbox_token_expired)
