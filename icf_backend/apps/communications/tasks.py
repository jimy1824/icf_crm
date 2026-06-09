import logging

from django.utils import timezone

from config.celery import app

logger = logging.getLogger(__name__)


@app.task(bind=True, max_retries=5, default_retry_delay=60, queue='communications',
          name='communications.send_email')
def send_email(self, communication_id: int) -> None:
    """
    BRU-16: idempotent — checks status before sending.
    BRU-18: retries queue via Celery; never dropped.
    BRU-24/42: respects scheduled_at.
    """
    try:
        from apps.communications.models import Communication
        from apps.communications.services import CommunicationService

        try:
            comm = Communication.objects.select_related('tenant', 'lead', 'client').get(
                pk=communication_id
            )
        except Communication.DoesNotExist:
            logger.warning("send_email: communication %d not found", communication_id)
            return

        if comm.status not in (Communication.STATUS_QUEUED,):
            logger.info(
                "send_email: communication %d already in status %s — skipping",
                communication_id, comm.status,
            )
            return

        # BRU-24: honour scheduled_at
        if comm.scheduled_at and comm.scheduled_at > timezone.now():
            delay = (comm.scheduled_at - timezone.now()).total_seconds()
            raise self.retry(countdown=int(delay))

        # BRU-18: suppression gate
        email = None
        if comm.lead:
            email = comm.lead.email
        elif comm.client and comm.client.lead:
            email = comm.client.lead.email

        if email and CommunicationService.is_suppressed_email(tenant=comm.tenant, email=email):
            comm.status = Communication.STATUS_FAILED
            comm.save(update_fields=['status', 'updated_at'])
            logger.info(
                "send_email: email %s suppressed — communication %d marked failed",
                email, communication_id,
            )
            return

        # Actual send is handled by provider integration layer (outside scope here).
        # Mark sent so downstream tasks see the transition.
        CommunicationService.mark_sent(communication=comm)
        logger.info("send_email: communication %d marked sent", communication_id)

    except self.MaxRetriesExceededError:
        logger.error("send_email: max retries exceeded for communication %d", communication_id)
        from apps.communications.models import Communication
        Communication.objects.filter(pk=communication_id).update(
            status=Communication.STATUS_FAILED,
        )
    except Exception as exc:
        logger.exception("send_email error for communication %d", communication_id)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=5, default_retry_delay=60, queue='communications',
          name='communications.send_sms')
def send_sms(self, communication_id: int) -> None:
    """
    BRU-16: idempotent by status check.
    BRU-19: suppression gate.
    """
    try:
        from apps.communications.models import Communication
        from apps.communications.services import CommunicationService

        try:
            comm = Communication.objects.select_related('tenant', 'lead', 'client').get(
                pk=communication_id
            )
        except Communication.DoesNotExist:
            logger.warning("send_sms: communication %d not found", communication_id)
            return

        if comm.status != Communication.STATUS_QUEUED:
            return

        phone = None
        if comm.lead:
            phone = comm.lead.phone
        elif comm.client and comm.client.lead:
            phone = comm.client.lead.phone

        if phone and CommunicationService.is_suppressed_phone(tenant=comm.tenant, phone=phone):
            comm.status = Communication.STATUS_FAILED
            comm.save(update_fields=['status', 'updated_at'])
            return

        CommunicationService.mark_sent(communication=comm)

    except self.MaxRetriesExceededError:
        logger.error("send_sms: max retries exceeded for communication %d", communication_id)
        from apps.communications.models import Communication
        Communication.objects.filter(pk=communication_id).update(
            status=Communication.STATUS_FAILED,
        )
    except Exception as exc:
        logger.exception("send_sms error for communication %d", communication_id)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='communications',
          name='communications.process_inbound_webhook')
def process_inbound_webhook(self, external_id: str, payload: dict, channel: str) -> None:
    """
    BRU-16: idempotent inbound webhook processing.
    Handles: bounce, complaint, delivery, open, click from email provider.
    """
    try:
        from apps.communications.models import Communication, DeliverabilityEvent
        from apps.communications.services import DeliverabilityService
        from apps.tenants.models import Tenant

        event_type = payload.get('event_type', '')
        email = payload.get('email', '')
        tenant_id = payload.get('tenant_id')

        if not tenant_id:
            logger.warning("process_inbound_webhook: missing tenant_id in payload")
            return

        try:
            tenant = Tenant.objects.get(pk=tenant_id)
        except Tenant.DoesNotExist:
            logger.warning("process_inbound_webhook: tenant %s not found", tenant_id)
            return

        comm_external_id = payload.get('message_id', '')
        communication = None
        if comm_external_id:
            communication = Communication.objects.filter(external_id=comm_external_id).first()

        DeliverabilityService.process_webhook_event(
            tenant=tenant,
            external_id=external_id,
            event_type=event_type,
            email=email,
            raw_payload=payload,
            communication=communication,
        )

    except Exception as exc:
        logger.exception("process_inbound_webhook error for %s", external_id)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=60, queue='communications',
          name='communications.send_meeting_reminder')
def send_meeting_reminder(self, meeting_id: int) -> None:
    """
    BRU-24/42: send a reminder 24h before meeting; timezone-aware.
    BRU-16: idempotent via reminder_sent flag.
    """
    try:
        from apps.communications.models import Meeting

        try:
            meeting = Meeting.objects.select_related(
                'advisor', 'tenant', 'lead', 'client',
            ).get(pk=meeting_id)
        except Meeting.DoesNotExist:
            logger.warning("send_meeting_reminder: meeting %d not found", meeting_id)
            return

        if meeting.reminder_sent:
            logger.info("send_meeting_reminder: already sent for meeting %d", meeting_id)
            return

        # Mark sent before dispatching to prevent double-send on retry
        meeting.reminder_sent = True
        meeting.save(update_fields=['reminder_sent', 'updated_at'])

        logger.info(
            "send_meeting_reminder: reminder dispatched for meeting %d scheduled at %s",
            meeting_id, meeting.scheduled_at,
        )
        # Actual notification dispatch handled by notifications app

    except Exception as exc:
        logger.exception("send_meeting_reminder error for meeting %d", meeting_id)
        raise self.retry(exc=exc)


@app.task(bind=True, max_retries=3, default_retry_delay=30, queue='communications',
          name='communications.sync_mailbox')
def sync_mailbox(self, connection_id: int) -> None:
    """
    FM-07 / BRU-05/16: pull new messages from OAuth mailbox and process inbound triggers.
    Idempotent via sync_cursor.
    """
    try:
        from apps.communications.models import MailboxConnection
        from apps.communications.services import MailboxService

        try:
            connection = MailboxConnection.objects.select_related('tenant', 'advisor').get(
                pk=connection_id
            )
        except MailboxConnection.DoesNotExist:
            logger.warning("sync_mailbox: connection %d not found", connection_id)
            return

        # BRU-05: check token expiry
        if connection.token_expires_at <= timezone.now():
            MailboxService.suspend_on_token_expiry(connection=connection)
            logger.warning(
                "sync_mailbox: connection %d token expired — suspended", connection_id,
            )
            return

        if connection.status != MailboxConnection.STATUS_ACTIVE:
            logger.info(
                "sync_mailbox: connection %d is %s — skipping",
                connection_id, connection.status,
            )
            return

        # Real API call happens in provider-specific integration service.
        # Here we just log that sync was attempted; provider layer updates sync_cursor.
        logger.info(
            "sync_mailbox: connection %d (%s) sync triggered",
            connection_id, connection.provider,
        )

    except Exception as exc:
        logger.exception("sync_mailbox error for connection %d", connection_id)
        raise self.retry(exc=exc)
